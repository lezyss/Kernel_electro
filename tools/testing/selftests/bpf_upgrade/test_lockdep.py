#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Dynamic key registry/retirement functions; not a concurrent lockdep test."""
import argparse
from pathlib import Path
import resource
import subprocess
import tempfile
from test_jmp32 import ROOT, HERE, function, once


def source(negative=None):
    text=(ROOT/'kernel/locking/lockdep.c').read_text()
    code='\n'.join(function(text,s) for s in ('static inline struct hlist_head *keyhashentry(',
        'void lockdep_register_key(', 'static bool is_dynamic_key(', 'void lockdep_unregister_key('))
    if negative=='unregistered': code=once(code,'return found;','(void)found; return true;')
    if negative=='retirement-range': code=once(code,'lockdep_free_key_range(key, sizeof(*key));','lockdep_free_key_range(key, 1);')
    if negative=='grace-period': code=once(code,'synchronize_rcu();',';')
    return (HERE/'lockdep_model.c').read_text().replace('/* EXTRACTED */',code)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asan',action='store_true');p.add_argument('--self-test-negatives',action='store_true');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='bpf-lockdep-') as tmp:
        d=Path(tmp);c=d/'test.c';binary=d/'test'
        flags=['gcc','-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-fno-pie','-no-pie',
               '-fsanitize='+('address,undefined' if a.asan else 'undefined'),'-fno-sanitize-recover=all']
        for negative in [None]+(['unregistered','retirement-range','grace-period'] if a.self_test_negatives else []):
            c.write_text(source(negative));subprocess.run(flags+[str(c),'-o',str(binary)],check=True)
            r=subprocess.run([str(binary)],capture_output=True,text=True,preexec_fn=lambda:resource.setrlimit(resource.RLIMIT_CORE,(0,0)))
            if negative:
                assert r.returncode and 'Assertion' in r.stderr,(negative,r.stderr)
                print('PASS: rejected '+negative,flush=True)
            else:
                assert not r.returncode,r.stderr
                print(r.stdout.strip(),flush=True)


if __name__=='__main__':main()
