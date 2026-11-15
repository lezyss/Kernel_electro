#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted-source host checks, not a running-kernel procfs test."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def block(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--donor-padding', action='store_true',
                        help='restore the donor single-digit bug; must fail')
    parser.add_argument('--donor-locked-pss', action='store_true',
                        help='restore double/cumulative locked PSS; must fail')
    args = parser.parse_args()
    seq = (ROOT / 'fs/seq_file.c').read_text()
    mmu = (ROOT / 'fs/proc/task_mmu.c').read_text()
    lib = (ROOT / 'lib/vsprintf.c').read_text()
    chunks = [block(lib, 'static const u16 decpair[100]') + ';']
    for sig in ['char *put_dec_trunc8(', 'char *put_dec_full8(',
                'char *put_dec(', 'int num_to_str(']:
        chunks.append(block(lib, sig))
    for sig in ['void seq_putc(', 'void seq_puts(',
                'void seq_put_decimal_ull_width(', 'void seq_put_decimal_ull(',
                'void seq_put_hex_ll(']:
        chunks.append(block(seq, sig))
    chunks += [block(mmu, 'struct mem_size_stats {') + ';',
               block(mmu, 'static void smaps_page_accumulate('),
               block(mmu, 'static void smaps_account(')]
    chunks += ['#define SEQ_PUT_DEC(s, v) '
               'seq_put_decimal_ull_width(m, s, (v) << (PAGE_SHIFT - 10), 8)',
               block(mmu, 'void task_mem('), '#undef SEQ_PUT_DEC',
               '#define SEQ_PUT_DEC(s, v) '
               'seq_put_decimal_ull_width(m, s, (v) >> 10, 8)',
               block(mmu, 'static void __show_smap('), '#undef SEQ_PUT_DEC',
               block(mmu, 'static void show_vma_header_prefix(')]
    model = Path(__file__).with_name('model.c').read_text()
    source = model.replace('/* EXTRACTED_HELPERS */', '\n\n'.join(chunks))
    gather = block(mmu, 'static void smap_gather_stats(')
    if args.donor_locked_pss:
        gather = gather[:-1] + ('if (vma->vm_flags & VM_LOCKED)\n'
                               'mss->pss_locked += mss->pss;\n}')
    source = source.replace('/* EXTRACTED_GATHER */', gather)
    source = source.replace('/* EXTRACTED_ROLLUP */',
                            block(mmu, 'static int show_smaps_rollup('))
    if args.donor_padding:
        source = source.replace('num < 10 && width == 1', 'num < 10')
    with tempfile.TemporaryDirectory(prefix='procfs-test-') as tmp:
        src, exe = Path(tmp) / 'test.c', Path(tmp) / 'test'
        src.write_text(source)
        subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2',
                       '-fno-strict-aliasing', '-Wall', '-Wextra', '-Werror',
                       '-Wno-unused-parameter', '-Wno-sign-compare', str(src), '-o', str(exe)],
                       check=True)
        subprocess.run([str(exe)], check=True)
    gather = block(mmu, 'static void smap_gather_stats(')
    assert 'pss_locked +=' not in gather
    assert 'single_open(file, show_smaps_rollup, priv)' in mmu
    assert 'single_release(inode, file)' in mmu
    assert 'sched_migrate_to_cpumask' not in mmu
    assert 'print_vma_hex10' not in mmu
    assert 'seq_file_path(m, file, "\\n")' in mmu
    assert 'Name:           ' in mmu and 'seq_print_vma_name' in mmu
    assert 'd_path_outlen' not in (ROOT / 'fs/dcache.c').read_text()
    print('Source integration guards: PASS')


if __name__ == '__main__':
    main()
