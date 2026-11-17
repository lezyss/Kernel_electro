#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Compile real recency/fadvise/rmap functions against host stubs, not a kernel.

No system calls target the running host kernel. --negative-controls mutates
throwaway source copies to check the regression assertions are effective.
"""
import argparse
import itertools
import os
from pathlib import Path
import re
import resource
import shlex
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
SOURCES = ('include/linux/fs.h', 'include/linux/mm_inline.h', 'mm/fadvise.c',
           'mm/memory.c', 'mm/rmap.c', 'mm/vmscan.c')


def function(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def generate(root):
    src = {n: (root / n).read_text() for n in SOURCES}
    fs, header, advice, memory, rmap, scan = (src[n] for n in SOURCES)
    fmode = '\n'.join(line for line in fs.splitlines() if line.startswith('#define FMODE_'))
    # No bit collision with any other FMODE declaration in the real header.
    values = re.findall(r'^#define\s+(FMODE_\w+)\s+\(\(__force fmode_t\)(0x[0-9a-fA-F]+)\)', fs, re.M)
    assert len(values) >= 20 and len({int(v, 16) for _, v in values}) == len(values)
    assert dict(values)['FMODE_NOREUSE'] == '0x800000'
    ref = function(rmap, 'int page_referenced(struct page *page,')
    # This callback must run during GLOBAL reclaim too, not just memcg reclaim.
    assert '.invalid_vma = invalid_page_referenced_vma,' in ref
    assert 'rwc.invalid_vma =' not in ref
    assert '.anon_lock = page_lock_anon_vma_read,' in ref
    assert 'trylock_page(page)' in ref and 'unlock_page(page)' in ref
    for name in ('mm/memory.c', 'mm/rmap.c', 'mm/vmscan.c'):
        assert '#include <linux/mm_inline.h>' in src[name], name
    # Do not silently resurrect the old ad hoc policy in any of the wired sites.
    for sig, text in [('static bool page_referenced_one(', rmap),
                      ('static int should_skip_vma(', scan),
                      ('static void lru_gen_enter_fault(', memory)]:
        assert 'vma_has_recency(vma)' in function(text, sig), sig
    assert 'pte_dirty(ptent)' in memory and 'set_page_dirty(page)' in memory
    zap = re.search(r'if \(pte_young\(ptent\) &&\s+likely\(vma_has_recency\(vma\)\)\)\s+mark_page_accessed\(page\);', memory)
    assert zap, 'zap_pte_range recency wiring'
    arg = re.search(r'struct page_referenced_arg \{.*?\n\};', rmap, re.S).group()
    start = memory.index('#ifdef CONFIG_LRU_GEN\nstatic void lru_gen_enter_fault(')
    end = memory.index('#endif /* CONFIG_LRU_GEN */', start) + len('#endif /* CONFIG_LRU_GEN */')
    production = '\n\n'.join([
        fmode, function(header, 'static inline bool vma_has_recency('),
        function(advice, 'int ksys_fadvise64_64('), arg,
        function(rmap, 'static bool page_referenced_one('),
        function(rmap, 'static bool invalid_page_referenced_vma('), ref,
        memory[start:end],
        '#ifdef CONFIG_LRU_GEN\n' + function(scan, 'static int should_skip_vma(') + '\n#endif',
        'static void unmap_reference(struct vm_area_struct *vma, pte_t ptent, struct page *page)\n{\n' + zap.group() + '\n}',
    ])
    return Path(__file__).with_name('model.c').read_text().replace('/* PRODUCTION */', production)


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(root, cc, profiles, quiet=False):
    text = generate(root)
    with tempfile.TemporaryDirectory(prefix='mm-recency-model-') as tmp:
        tmp = Path(tmp)
        source, binary = tmp / 'test.c', tmp / 'test'
        source.write_text(text)
        for gen, memcg, thp in profiles:
            flags = ['-DCONFIG_MEMCG=' + str(memcg),
                     '-DCONFIG_TRANSPARENT_HUGEPAGE=' + str(thp)]
            if gen:
                flags += ['-DCONFIG_LRU_GEN=1']
            subprocess.run([*cc, '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                            *flags, str(source), '-o', str(binary)], check=True,
                           stdout=subprocess.PIPE if quiet else None,
                           stderr=subprocess.PIPE if quiet else None)
            subprocess.run([str(binary)], check=True, cwd=tmp, preexec_fn=no_core,
                           stdout=subprocess.PIPE if quiet else None,
                           stderr=subprocess.PIPE if quiet else None)
            if not quiet:
                print('PASS: extracted production functions; MGLRU/MEMCG/THP =',
                      gen, memcg, thp, flush=True)


def negatives(root, cc):
    mutations = [
        ('set hint', 'mm/fadvise.c', 'f.file->f_mode |= FMODE_NOREUSE;', 'f.file->f_mode |= 0;'),
        ('reset hint', 'mm/fadvise.c', '~(FMODE_RANDOM | FMODE_NOREUSE)', '~FMODE_RANDOM'),
        ('set locking', 'mm/fadvise.c', 'case POSIX_FADV_NOREUSE:\n\t\tspin_lock(&f.file->f_lock);', 'case POSIX_FADV_NOREUSE:'),
        ('file predicate', 'include/linux/mm_inline.h', 'READ_ONCE(vma->vm_file->f_mode) & FMODE_NOREUSE', 'READ_ONCE(vma->vm_file->f_mode) & 0'),
        ('random predicate', 'include/linux/mm_inline.h', '(VM_SEQ_READ | VM_RAND_READ)', '(VM_SEQ_READ)'),
        ('memcg isolation', 'mm/rmap.c', 'memcg && !mm_match_cgroup', 'memcg && mm_match_cgroup'),
        ('global callback', 'mm/rmap.c', '.invalid_vma = invalid_page_referenced_vma,', '/* callback removed */'),
        ('fault policy', 'mm/memory.c', 'current->in_lru_fault = vma_has_recency(vma);', 'current->in_lru_fault = true;'),
        ('unmap policy', 'mm/memory.c', 'likely(vma_has_recency(vma))', 'likely(true)'),
        ('aging policy', 'mm/vmscan.c', 'if (!vma_has_recency(vma) ||', 'if (false ||'),
        ('look-around policy', 'mm/rmap.c', 'vma_has_recency(vma)) {', 'true) {'),
    ]
    with tempfile.TemporaryDirectory(prefix='mm-recency-negative-') as tmp:
        tmp = Path(tmp)
        for n in SOURCES:
            p = tmp / n
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / n, p)
        for label, name, old, new in mutations:
            p = tmp / name
            before = p.read_text()
            assert before.count(old) == 1, label
            p.write_text(before.replace(old, new, 1))
            try:
                run(tmp, cc, [(1, 1, 1)], quiet=True)
            except (AssertionError, subprocess.CalledProcessError):
                print('PASS: negative control rejected:', label, flush=True)
            else:
                raise AssertionError('mutation accepted: ' + label)
            finally:
                p.write_text(before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--negative-controls', action='store_true')
    args = parser.parse_args()
    cc = shlex.split(args.cc)
    run(args.root, cc, itertools.product((0, 1), repeat=3))
    if args.negative_controls:
        negatives(args.root, cc)
    print('LIMITS: host stubs and source wiring guards; not kernel reclaim/concurrency or performance proof.')


if __name__ == '__main__':
    main()
