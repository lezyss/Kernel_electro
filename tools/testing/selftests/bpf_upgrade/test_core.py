#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted build-ID, pidfd, tnum and scalar-bound regression checks."""
import argparse
from pathlib import Path
import resource
import subprocess
import tempfile
from test_jmp32 import ROOT, HERE, function, once


def source(negative=None):
    buildid = (ROOT / 'lib/buildid.c').read_text()
    pid = (ROOT / 'kernel/pid.c').read_text()
    verifier = (ROOT / 'kernel/bpf/verifier.c').read_text()
    tnum = (ROOT / 'kernel/bpf/tnum.c').read_text()
    tnum = '\n'.join(l for l in tnum.splitlines() if not l.startswith('#include'))
    pieces = [function(buildid, sig) for sig in ['static inline int parse_build_id(', 'static int get_build_id_32(', 'static int get_build_id_64(']]
    pieces.append(function(pid, 'struct pid *pidfd_get_pid('))
    pieces += [function(verifier, sig) for sig in (
        'static bool signed_add_overflows(', 'static bool signed_add32_overflows(',
        'static bool signed_sub_overflows(', 'static bool signed_sub32_overflows(',
        'static void scalar32_min_max_add(', 'static void scalar_min_max_add(',
        'static void scalar32_min_max_sub(', 'static void scalar_min_max_sub(')]
    text = tnum + '\n' + '\n'.join(pieces)
    if negative == 'note-bounds':
        text = once(text, 'if (names > remain || descs > remain - names)', 'if (false && (names > remain || descs > remain - names))')
    elif negative == 'gnu-name':
        text = once(text, '!memcmp(name, "GNU", sizeof("GNU"))', 'true')
    elif negative == 'pidfd-type':
        text = once(text, 'if (f.file->f_op == &pidfd_fops)', 'if (true)')
    elif negative == 'pidfd-reference':
        text = once(text, 'pid = get_pid(f.file->private_data);', 'pid = f.file->private_data;')
    elif negative == 'tnum-mask':
        text = once(text, 'return TNUM(sv & ~mu, mu);', 'return TNUM(sv & ~mu, 0);')
    elif negative == 'scalar-bound':
        text = once(text, 'dst_reg->umax_value += umax_val;', 'dst_reg->umax_value = 0;')
    return (HERE / 'core_model.c').read_text().replace('/* EXTRACTED */', text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asan', action='store_true')
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    assert (ROOT / 'include/uapi/linux/bpf.h').read_bytes() == (ROOT / 'tools/include/uapi/linux/bpf.h').read_bytes(), 'kernel/tools BPF UAPI drift'
    print('PASS: kernel/tools BPF UAPI byte-identical (including timer helper IDs)', flush=True)
    with tempfile.TemporaryDirectory(prefix='bpf-core-check-') as tmp:
        d = Path(tmp); (d / 'linux').mkdir()
        (d / 'linux/tnum.h').write_text((ROOT / 'include/linux/tnum.h').read_text())
        (d / 'linux/types.h').write_text('''#pragma once
#include <stdbool.h>
#include <stddef.h>
typedef unsigned long long u64;typedef long long s64;
typedef unsigned int u32,__u32;typedef int s32;typedef unsigned char u8;
''')
        flags = ['gcc', '-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-fno-pie', '-no-pie',
                 '-fsanitize='+('address,undefined' if args.asan else 'undefined'), '-fno-sanitize-recover=all', '-I'+tmp]
        negatives = ['note-bounds', 'gnu-name', 'pidfd-type', 'pidfd-reference', 'tnum-mask', 'scalar-bound']
        for negative in [None] + (negatives if args.self_test_negatives else []):
            c = d / 'test.c'; binary = d / 'test'; c.write_text(source(negative))
            subprocess.run(flags + [str(c), '-o', str(binary)], check=True)
            r = subprocess.run([str(binary)], capture_output=True, text=True,
                               preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if negative:
                assert r.returncode and ('Assertion' in r.stderr or 'runtime error:' in r.stderr or 'AddressSanitizer' in r.stderr), (negative, r.stderr)
                print('PASS: rejected '+negative, flush=True)
            else:
                assert not r.returncode, r.stderr
                print(r.stdout.strip(), flush=True)


if __name__ == '__main__':
    main()
