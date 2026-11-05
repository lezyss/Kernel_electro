#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted softirq timer foundation checks with mocked queues/platform context."""
import argparse
import os
from pathlib import Path
import re
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
NEGATIVES = ('hard-clock-base', 'wrong-expiry-mask', 'lose-pinned',
             'exclude-mutates-cache', 'hardirq-soft-callback', 'migrate-pinned',
             'migrate-running-soft', 'unconditional-bh-enable', 'stale-soft-deadline',
             'pin-only-active', 'cpu-reset-seq', 'clock-expiry-cache')


def function(text, sig, last=False):
    start = text.rindex(sig) if last else text.index(sig)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def source(negative=None):
    text = (ROOT / 'kernel/time/hrtimer.c').read_text()
    header = (ROOT / 'include/linux/hrtimer.h').read_text()
    mode = header[header.index('enum hrtimer_mode {'):header.index('\n};', header.index('enum hrtimer_mode {')) + 3]
    start = header.index('enum  hrtimer_base_type {')
    bases = header[start:header.index('\n};', start) + 3]
    functions = '\n'.join(function(text, sig) for sig in (
        'static struct hrtimer_clock_base *\n__next_base(',
        'static ktime_t __hrtimer_next_event_base(',
        'static ktime_t\n__hrtimer_get_next_event(',
        'static ktime_t hrtimer_update_next_event(',
        'static inline ktime_t hrtimer_update_base(',
        'static void\nhrtimer_force_reprogram(',
        'static void hrtimer_reprogram(',
        'static void\nhrtimer_update_softirq_timer(',
        'static int enqueue_hrtimer(',
        'static void __remove_hrtimer(',
        'bool hrtimer_active(',
        'int hrtimers_prepare_cpu(',
        'static void __run_hrtimer(',
        'static void __hrtimer_run_queues(',
        'static __latent_entropy void hrtimer_run_softirq(',
        'static void migrate_hrtimer_list(',
        'static void __migrate_hrtimers('))
    functions += '\n' + function(text, 'static void __hrtimer_init(', last=True)
    # The queue, expiry, dispatch, reprogram and migration functions above are
    # extracted verbatim; only their platform/queue primitives are mocked.
    if negative == 'hard-clock-base':
        functions = once(functions, 'int base = softtimer ? HRTIMER_MAX_CLOCK_BASES / 2 : 0;', 'int base = 0;')
    elif negative == 'wrong-expiry-mask':
        functions = once(functions, '__hrtimer_run_queues(cpu_base, now, flags, HRTIMER_ACTIVE_SOFT);',
                         '__hrtimer_run_queues(cpu_base, now, flags, HRTIMER_ACTIVE_HARD);')
    elif negative == 'lose-pinned':
        functions = once(functions, 'newstate | (state & HRTIMER_STATE_PINNED)', 'newstate')
    elif negative == 'exclude-mutates-cache':
        functions = once(functions, 'if (exclude)\n\t\t\t\tcontinue;', 'if (false)\n\t\t\t\tcontinue;')
    elif negative == 'hardirq-soft-callback':
        functions = once(functions, 'raw_spin_unlock_irqrestore(&cpu_base->lock, flags);\n\ttrace_hrtimer_expire_entry',
                         'raw_spin_unlock_irqrestore(&cpu_base->lock, flags); irq_disabled = true;\n\ttrace_hrtimer_expire_entry')
    elif negative == 'migrate-pinned':
        functions = once(functions, 'if (!remove_pinned &&', 'if (false && !remove_pinned &&')
    elif negative == 'migrate-running-soft':
        functions = once(functions, '(is_pinned || hrtimer_callback_running(timer))', '(is_pinned)')
    elif negative == 'unconditional-bh-enable':
        functions = once(functions, 'bool disable_bh = !in_interrupt();', 'bool disable_bh = true;')
    elif negative == 'stale-soft-deadline':
        functions = once(functions, '/* Drop the old deadline even when removal/migration emptied the queue. */\n\tcpu_base->softirq_expires_next = KTIME_MAX;', ';')
    elif negative == 'pin-only-active':
        functions = once(functions, '(READ_ONCE(timer->state) & ~HRTIMER_STATE_PINNED)', 'READ_ONCE(timer->state)')
    elif negative == 'cpu-reset-seq':
        functions = once(functions, 'seqcount_init(&cpu_base->clock_base[i].seq);', ';')
    elif negative == 'clock-expiry-cache':
        functions = once(functions, 'cpu_base->softirq_expires_next = soft;', ';')
    table = text[text.index('static const int hrtimer_clock_to_base_table['):text.index('\n};', text.index('static const int hrtimer_clock_to_base_table[')) + 3]
    code = (HERE / 'softirq_model.c').read_text()
    code = code.replace('/* ENUMS */', mode + '\n' + bases)
    code = code.replace('/* FUNCTIONS */', table + '\n' + functions)
    return code


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--asan', action='store_true')
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    cc = shlex.split(args.cc)
    flags = ['-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-UNDEBUG',
             '-Wno-unused-parameter', '-Wno-override-init', '-fno-pie', '-no-pie',
             '-fsanitize=' + ('address,undefined' if args.asan else 'undefined'), '-fno-sanitize-recover=all']
    with tempfile.TemporaryDirectory(prefix='bpf-softirq-') as directory:
        directory = Path(directory)
        probe = directory / 'probe.c'
        probe.write_text('int main(void){volatile int x=2147483647;volatile int y=x+1;return y;}\n')
        binary = directory / 'probe'
        subprocess.run(cc + flags + [str(probe), '-o', str(binary)], check=True)
        r = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
        assert r.returncode and b'runtime error' in r.stderr
        if args.asan:
            probe.write_text('#include <stdlib.h>\n__attribute__((noinline)) void f(volatile int *p,int n){p[n]=1;}\nint main(int n,char **v){(void)v;int *p=malloc(4);f(p,n);free(p);return 0;}\n')
            subprocess.run(cc + flags + [str(probe), '-o', str(binary)], check=True)
            r = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
            assert r.returncode and b'AddressSanitizer' in r.stderr
        print('PASS: requested sanitizer runtime probes', flush=True)
        for negative in [None] + (list(NEGATIVES) if args.self_test_negatives else []):
            path = directory / ((negative or 'current') + '.c')
            path.write_text(source(negative))
            binary = path.with_suffix('')
            subprocess.run(cc + flags + [str(path), '-o', str(binary)], check=True)
            r = subprocess.run([str(binary)], capture_output=True, text=True, preexec_fn=no_core)
            if negative:
                assert r.returncode != 0 and 'Assertion' in r.stderr, (negative, r.stderr)
                print('PASS: rejected ' + negative, flush=True)
            else:
                assert r.returncode == 0, r.stderr
                print(r.stdout.strip(), flush=True)


if __name__ == '__main__':
    main()
