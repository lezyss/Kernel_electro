#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Compile current scheduler helpers in a mocked, sanitizer-checked host context."""
import argparse
import os
from pathlib import Path
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
NEGATIVES = ('min-margin', 'max-margin', 'plain-cpu-read', 'plain-cpu-write',
             'missing-wmb', 'plain-migrating-read', 'plain-migrating-write',
             'late-irq-disable', 'protected-tick', 'empty-cfs-source')


def function(text, signature, start=0):
    begin = text.index(signature, start)
    end = text.index('{', begin) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin:end]


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def source(smp, negative=None):
    fair = (ROOT / 'kernel/sched/fair.c').read_text()
    sched = (ROOT / 'kernel/sched/sched.h').read_text()
    public = (ROOT / 'include/linux/sched.h').read_text()
    core = (ROOT / 'kernel/sched/core.c').read_text()
    idle = function((ROOT / 'kernel/sched/idle.c').read_text(), 'static void do_idle(')
    tick = (ROOT / 'include/linux/tick.h').read_text()
    queue = '\n'.join(function(fair, n) for n in (
        'static inline bool\ngroup_smaller_min_cpu_capacity(',
        'static inline bool\ngroup_smaller_max_cpu_capacity(',
        'static struct rq *find_busiest_queue('))
    get_cpu = 'static inline unsigned int task_cpu('
    start = 0 if smp else public.index(get_cpu) + 1
    migration = '\n'.join((function(public, get_cpu, start),
                           function(sched, 'static inline void __set_task_cpu('),
                           function(sched, 'static inline int task_on_rq_migrating(')))
    move = function(core, 'static struct rq *move_queued_task(')
    begin = move.index('WRITE_ONCE(p->on_rq, TASK_ON_RQ_MIGRATING);')
    end = move.index('#ifdef CONFIG_SCHED_WALT', begin)
    migration += '\nstatic void move_prefix(struct rq *rq, struct task_struct *p)\n{\n'
    migration += move[begin:end] + '}\n'
    begin = idle.index('local_irq_disable();', idle.index('check_pgt_cache();'))
    end = idle.index('arch_cpu_idle_enter();', begin) + len('arch_cpu_idle_enter();')
    prefix = idle[begin:end]
    assert prefix.count('local_irq_disable();') == 1
    assert 'tick_nohz_idle_stop_tick_protected' not in prefix
    wrapper_sig = 'static inline void tick_nohz_idle_stop_tick_protected('
    wrapper = '#ifdef CONFIG_NO_HZ_COMMON\n' + function(tick, wrapper_sig)
    wrapper += '\n#else\n' + function(tick, wrapper_sig, tick.index(wrapper_sig) + 1) + '\n#endif\n'
    if negative == 'min-margin':
        queue = replace_once(queue, 'return sg->sgc->min_capacity <',
                             'return sg->sgc->min_capacity * 1735 / 1024 <')
    elif negative == 'max-margin':
        queue = replace_once(queue, 'return sg->sgc->max_capacity <',
                             'return sg->sgc->max_capacity * 1735 / 1024 <')
    elif negative == 'plain-cpu-read':
        migration = replace_once(migration, 'READ_ONCE(p->cpu)', 'p->cpu')
    elif negative == 'plain-cpu-write':
        migration = replace_once(migration, 'WRITE_ONCE(p->cpu, cpu);', 'p->cpu = cpu;')
    elif negative == 'missing-wmb':
        migration = replace_once(migration, 'smp_wmb();', '/* removed */')
    elif negative == 'plain-migrating-read':
        migration = replace_once(migration, 'READ_ONCE(p->on_rq)', 'p->on_rq')
    elif negative == 'plain-migrating-write':
        migration = replace_once(migration, 'WRITE_ONCE(p->on_rq, TASK_ON_RQ_MIGRATING);',
                                 'p->on_rq = TASK_ON_RQ_MIGRATING;')
    elif negative == 'late-irq-disable':
        prefix = replace_once(prefix, 'local_irq_disable();', '')
        prefix = replace_once(prefix, 'arch_cpu_idle_enter();',
                              'local_irq_disable();\narch_cpu_idle_enter();')
    elif negative == 'protected-tick':
        prefix = replace_once(prefix, 'tick_nohz_idle_stop_tick();',
                              'tick_nohz_idle_stop_tick_protected();')
    elif negative == 'empty-cfs-source':
        queue = replace_once(queue, 'if (!rq->cfs.h_nr_running)', 'if (false)')
    model = (HERE / 'model.c').read_text()
    for marker, code in [('CAPACITY_AND_QUEUE', queue), ('MIGRATION', migration),
                         ('PROTECTED_WRAPPER', wrapper), ('IDLE_PREFIX', prefix)]:
        model = replace_once(model, '/* ' + marker + ' */', code)
    return model


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--asan', action='store_true')
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    cc = shlex.split(args.cc)
    flags = ['-std=gnu11', '-O2', '-g', '-UNDEBUG', '-Wall', '-Wextra', '-Werror',
             '-Wno-unused-parameter', '-fno-pie', '-no-pie',
             '-fsanitize=' + ('address,undefined' if args.asan else 'undefined'),
             '-fno-sanitize-recover=all']
    with tempfile.TemporaryDirectory(prefix='sched-correctness-') as directory:
        directory = Path(directory)
        probe = directory / 'probe.c'
        probe.write_text('int main(void) { volatile int x = 2147483647; volatile int y = x + 1; return y; }\n')
        binary = directory / 'probe'
        subprocess.run(cc + flags + [str(probe), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
        assert result.returncode != 0 and b'runtime error' in result.stderr, result.stderr
        if args.asan:
            probe.write_text('#include <stdlib.h>\n__attribute__((noinline)) void store(volatile int *p, int n) { p[n] = 7; }\nint main(int n, char **v) { (void)v; volatile int *p = malloc(sizeof(int)); store(p, n); free((void *)p); return 0; }\n')
            subprocess.run(cc + flags + [str(probe), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
            assert result.returncode != 0 and b'AddressSanitizer' in result.stderr, result.stderr
        print('PASS: sanitizer runtime probes', flush=True)
        for smp, thread, nohz in [(1, t, h) for t in (0, 1) for h in (0, 1)] + [(0, 0, 0), (0, 0, 1)]:
            name = f'smp{smp}-thread{thread}-nohz{nohz}'
            path = directory / (name + '.c')
            path.write_text(source(smp))
            defines = ([ '-DCONFIG_SMP' ] if smp else [])
            defines += ([ '-DCONFIG_THREAD_INFO_IN_TASK' ] if thread else [])
            defines += ([ '-DCONFIG_NO_HZ_COMMON' ] if nohz else [])
            binary = directory / name
            subprocess.run(cc + flags + defines + [str(path), '-o', str(binary)], check=True)
            print(name + ':', flush=True)
            subprocess.run([str(binary)], check=True, preexec_fn=no_core)
        if args.self_test_negatives:
            for negative in NEGATIVES:
                path = directory / (negative + '.c')
                path.write_text(source(1, negative))
                binary = directory / negative
                subprocess.run(cc + flags + ['-DCONFIG_SMP', '-DCONFIG_THREAD_INFO_IN_TASK',
                                             '-DCONFIG_NO_HZ_COMMON', str(path), '-o', str(binary)], check=True)
                result = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
                assert result.returncode != 0 and b'Assertion' in result.stderr, (negative, result.stderr)
                print('PASS: rejected ' + negative, flush=True)


if __name__ == '__main__':
    main()
