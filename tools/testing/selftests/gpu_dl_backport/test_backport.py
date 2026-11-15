#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted KGSL locking and DEADLINE/cpuset checks, not device stress tests."""
import argparse
import os
from pathlib import Path
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
NEGATIVES = ('gpu-plain-locks', 'count-inactive-cpus', 'configured-mask',
             'lose-no-setaffinity', 'missing-destination-check',
             'missing-zero-cpu-check', 'reserve-on-overflow')


def function(text, signature, start=0):
    begin = text.index(signature, start)
    end = text.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin:end]


def sources(negative=None):
    dl = (ROOT / 'kernel/sched/deadline.c').read_text()
    core = (ROOT / 'kernel/sched/core.c').read_text()
    cpuset = (ROOT / 'kernel/cgroup/cpuset.c').read_text()
    sched = (ROOT / 'kernel/sched/sched.h').read_text()
    gpu = (ROOT / 'drivers/gpu/msm/kgsl_sync.c').read_text()
    dl_names = ('static inline struct dl_bw *dl_bw_of(',
                'static inline int dl_bw_cpus(', 'int dl_task_can_attach(')
    # The unchanged legacy overflow helper compares u64 bw with signed -1.
    code = '#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wsign-compare"\n'
    code += '\n'.join(function(sched, n) for n in (
        'static inline\nvoid __dl_add(', 'static inline\nbool __dl_overflow('))
    code += '\n#pragma GCC diagnostic pop\n'
    code += '\n' + '\n'.join(function(dl, n) for n in dl_names)
    code += '\n' + function(core, 'int task_can_attach(')
    code += '\n' + function(cpuset, 'static int cpuset_can_attach(')
    gcode = '\n'.join(function(gpu, n) for n in (
        'static void kgsl_syncsource_cleanup(',
        'long kgsl_ioctl_syncsource_create_fence(',
        'static int kgsl_syncsource_signal('))
    if negative == 'gpu-plain-locks':
        assert gcode.count('spin_lock_irqsave(&syncsource->lock, flags);') == 3
        gcode = gcode.replace('spin_lock_irqsave(&syncsource->lock, flags);',
                              'flags = irq_disabled; spin_lock(&syncsource->lock);')
        gcode = gcode.replace('spin_unlock_irqrestore(&syncsource->lock, flags);',
                              'spin_unlock(&syncsource->lock); irq_disabled = flags;')
    elif negative == 'count-inactive-cpus':
        code = code.replace('cpumask_subset(rd->span, cpu_active_mask)', 'true')
    elif negative == 'configured-mask':
        code = code.replace('task_can_attach(task, cs->effective_cpus)',
                            'task_can_attach(task, cs->cpus_allowed)')
    elif negative == 'lose-no-setaffinity':
        code = code.replace('if (p->flags & PF_NO_SETAFFINITY)',
                            'if (false && (p->flags & PF_NO_SETAFFINITY))')
    elif negative == 'missing-destination-check':
        code = code.replace('if (unlikely(dest_cpu >= nr_cpu_ids))',
                            'if (false && unlikely(dest_cpu >= nr_cpu_ids))')
    elif negative == 'missing-zero-cpu-check':
        code = code.replace('if (unlikely(!cpus))', 'if (false && unlikely(!cpus))')
    elif negative == 'reserve-on-overflow':
        code = code.replace('if (overflow)', 'if (false && overflow)')
    up = function(dl, 'static inline int dl_bw_cpus(',
                  dl.index('static inline int dl_bw_cpus(') + 1)
    return {'deadline': (HERE/'deadline_model.c').read_text().replace('/* FUNCTIONS */', code),
            'gpu': (HERE/'gpu_model.c').read_text().replace('/* FUNCTIONS */', gcode),
            'up': '#include <assert.h>\n' + up + '\nint main(void) { assert(dl_bw_cpus(0) == 1); return 0; }\n'}


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    p.add_argument('--asan', action='store_true')
    p.add_argument('--self-test-negatives', action='store_true')
    args = p.parse_args()
    cc = shlex.split(args.cc)
    flags = ['-std=gnu11', '-O2', '-g', '-UNDEBUG', '-Wall', '-Wextra', '-Werror',
             '-Wno-unused-parameter', '-fsanitize=' + ('address,undefined' if args.asan else 'undefined'),
             '-fno-sanitize-recover=all', '-fno-pie', '-no-pie']
    with tempfile.TemporaryDirectory(prefix='gpu-dl-test-') as tmp:
        tmp = Path(tmp)
        # Reject a compiler that silently omits undefined-behaviour checking.
        probe = tmp/'probe.c'
        probe.write_text('int main(void) { volatile int a = 2147483647; volatile int b = a + 1; (void)b; return 0; }\n')
        subprocess.run([*cc, *flags, str(probe), '-o', str(tmp/'probe')], check=True)
        result = subprocess.run([str(tmp/'probe')], capture_output=True, text=True, preexec_fn=no_core)
        assert result.returncode != 0 and 'overflow' in result.stderr, 'UBSan probe failed'
        if args.asan:
            probe.write_text('#include <stdlib.h>\n__attribute__((noinline)) static void release(void *p) { free(p); }\nint main(void) { volatile int *p = malloc(sizeof(int)); release((void *)p); return *p; }\n')
            subprocess.run([*cc, *flags, str(probe), '-o', str(tmp/'probe')], check=True)
            result = subprocess.run([str(tmp/'probe')], capture_output=True, text=True, preexec_fn=no_core)
            assert result.returncode != 0 and 'heap-use-after-free' in result.stderr, 'ASan probe failed'
        variants = [None, *NEGATIVES] if args.self_test_negatives else [None]
        for negative in variants:
            parts = sources(negative)
            names = ('gpu',) if negative == 'gpu-plain-locks' else (('deadline',) if negative else ('deadline', 'gpu', 'up'))
            for name in names:
                label = negative or name
                src, exe = tmp/(label+'.c'), tmp/label
                src.write_text(parts[name])
                subprocess.run([*cc, *flags, str(src), '-o', str(exe)], check=True)
                result = subprocess.run([str(exe)], capture_output=True, text=True, preexec_fn=no_core)
                if negative:
                    assert result.returncode != 0, 'mutant survived: ' + negative
                    assert 'Assertion' in result.stderr or 'runtime error:' in result.stderr, result.stderr
                    print('PASS: rejected ' + negative, flush=True)
                else:
                    assert result.returncode == 0, result.stdout + result.stderr
                    print(result.stdout.strip() or 'PASS: non-SMP CPU-count helper', flush=True)


if __name__ == '__main__':
    main()
