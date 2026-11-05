#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted BPF timer helpers with mocked hrtimers/locks/map/prog references."""
import argparse
import resource
import subprocess
import tempfile
from pathlib import Path
from test_jmp32 import ROOT, HERE, function, once


def source(negative=None):
    text = (ROOT / 'kernel/bpf/helpers.c').read_text()
    header = (ROOT / 'include/linux/hrtimer.h').read_text()
    a = header.index('enum hrtimer_mode {'); modes = header[a:header.index('\n};', a)+3]
    structs = function(text, 'struct bpf_hrtimer {')+';\n'+function(text, 'struct bpf_timer_kern {')+' __attribute__((aligned(8)));\n'
    funcs = '\n'.join(function(text, sig) for sig in (
        'static enum hrtimer_restart bpf_timer_cb(', 'int bpf_map_charge_timers(',
        'BPF_CALL_3(bpf_timer_init,', 'BPF_CALL_3(bpf_timer_set_callback,',
        'BPF_CALL_3(bpf_timer_start,', 'static void drop_prog_refcnt(',
        'BPF_CALL_1(bpf_timer_cancel,', 'void bpf_timer_cancel_and_free('))
    if negative == 'hard-mode': funcs = funcs.replace('HRTIMER_MODE_REL_SOFT', 'HRTIMER_MODE_REL')
    elif negative == 'self-cancel': funcs = once(funcs, 'if (this_cpu_read(hrtimer_running) == t)', 'if (false)')
    elif negative == 'prog-reference': funcs = once(funcs, 'bpf_prog_put(prog);', '(void)prog;')
    elif negative == 'self-free': funcs = once(funcs, 'if (this_cpu_read(hrtimer_running) != t)', 'if (true)')
    elif negative == 'timer-charge': funcs = once(funcs, 'if (map->timer_off < 0)', 'if (true)')
    return (HERE / 'timer_lifetime_model.c').read_text().replace('/* MODES */', modes).replace('/* STRUCTS */', structs).replace('/* EXTRACTED */', funcs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asan', action='store_true')
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='bpf-timer-lifetime-') as tmp:
        d=Path(tmp); c=d/'test.c'; binary=d/'test'
        flags=['gcc','-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fno-pie','-no-pie',
               '-fsanitize='+('address,undefined' if args.asan else 'undefined'),'-fno-sanitize-recover=all']
        for negative in [None]+(['hard-mode','self-cancel','prog-reference','self-free','timer-charge'] if args.self_test_negatives else []):
            c.write_text(source(negative));subprocess.run(flags+[str(c),'-o',str(binary)],check=True)
            r=subprocess.run([str(binary)],capture_output=True,text=True,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if negative:
                assert r.returncode and 'Assertion' in r.stderr,(negative,r.stderr)
                print('PASS: rejected '+negative,flush=True)
            else:
                assert not r.returncode,r.stderr
                print(r.stdout.strip(),flush=True)


if __name__=='__main__': main()
