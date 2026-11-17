#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted-source vmalloc models; not running-kernel concurrency tests."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def function(text, name):
    matches = re.finditer(r'^(?:[A-Za-z_][^\n;]*?[ \t]+\**)?' +
                          re.escape(name) + r'\(', text, re.M)
    for match in matches:
        opening = text.index('{', match.end())
        semi = text.find(';', match.end())
        if semi < 0 or opening < semi:
            break
    else:
        raise ValueError(name)
    start = match.start()
    previous = text[:start].splitlines()[-1] if start else ''
    if previous.startswith('static '):
        start -= len(previous) + 1
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def no_includes(text):
    return re.sub(r'^#include[^\n]*\n', '', text, flags=re.M)


def guards(root):
    s = (root / 'mm/vmalloc.c').read_text()
    assert 'static atomic_long_t vmap_lazy_nr' in s
    assert 'length = size + align - 1;' not in s
    assert 'kmem_cache_alloc_node(vmap_area_cachep, gfp_mask, node)' in s
    assert 'gfp_mask = gfp_mask & GFP_RECLAIM_MASK;' in s
    assert 'get_cpu_var(vmap_block_queue)' in s  # #17 intentionally omitted
    assert 'vmalloc_user_node_flags(' in s
    assert 'free_vmap_cache' not in s and 'kfree_rcu(va, rcu_head)' not in s
    for name in ['vmalloc_user', 'vmalloc_32_user', 'vmalloc_user_node_flags']:
        f = function(s, name)
        assert 'SHMLBA' in f and 'VM_USERMAP' in f and '__GFP_ZERO' in f
    stop = function(s, 's_stop')
    assert stop.index('spin_unlock') < stop.index('mutex_unlock')
    assert '__releases(&vmap_purge_lock)' in stop
    init = function(s, 'vmalloc_init')
    assert 'panic("vmalloc: cannot reserve early area' in init
    assert 'continue;' not in init
    h = (root / 'include/linux/vmalloc.h').read_text()
    assert 'union {' in h and 'struct rcu_head rcu_head;' not in h
    assert 'in "free" tree (root is free_vmap_area_root)' in h
    print('Vmalloc integration guards: PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--negative', choices=['donor-search', 'missing-unlock',
                                             'boot-skip', 'wrong-gfp', 'early-reuse'])
    args = parser.parse_args()
    root = args.source_root
    s = (root / 'mm/vmalloc.c').read_text()
    names = ['va_size', 'get_subtree_max_size', 'compute_subtree_max_size',
             'find_va_links', 'get_va_next_sibling', 'link_va', 'unlink_va',
             'augment_tree_propagate_from', 'insert_vmap_area',
             'insert_vmap_area_augment', 'merge_or_add_vmap_area',
             'is_within_this_va', 'find_vmap_lowest_match',
             'classify_va_fit_type', 'adjust_va_to_fit_type', '__alloc_vmap_area',
             '__find_vmap_area', 'alloc_vmap_area', 'free_vmap_area',
             '__purge_vmap_area_lazy', 'try_purge_vmap_area_lazy',
             'purge_vmap_area_lazy', 'free_vmap_area_noflush',
             'vmap_init_free_space', 'vmalloc_init', 'setup_vmalloc_vm_locked',
             'node_to_va', 'pvm_find_va_enclose_addr',
             'pvm_determine_end_from_reverse', 'pcpu_get_vm_areas',
             's_start', 's_next', 's_stop', 'show_purge_info', 's_show']
    funcs = {n: function(s, n) for n in names}
    original = funcs.copy()
    if args.negative == 'donor-search':
        # Reintroduce unsafe worst-case-padding pruning without changing the tree.
        f = funcs['find_vmap_lowest_match']
        f = f.replace('>= size', '>= size + align - 1')
        funcs['find_vmap_lowest_match'] = f
    if args.negative == 'missing-unlock':
        funcs['s_stop'] = funcs['s_stop'].replace('mutex_unlock(&vmap_purge_lock);', '')
    if args.negative == 'boot-skip':
        funcs['vmalloc_init'] = re.sub(r'panic\("vmalloc: cannot reserve early area[^;]*;',
                                      'continue;', funcs['vmalloc_init'])
    if args.negative == 'wrong-gfp':
        funcs['alloc_vmap_area'] = funcs['alloc_vmap_area'].replace(
            'pva = kmem_cache_alloc_node(vmap_area_cachep, gfp_mask, node)',
            'pva = kmem_cache_alloc_node(vmap_area_cachep, GFP_KERNEL, node)')
    if args.negative == 'early-reuse':
        f = funcs['__purge_vmap_area_lazy']
        f = f.replace('flush_tlb_kernel_range(start, end);', '')
        f = f.replace('return true;', 'flush_tlb_kernel_range(start, end);\n\treturn true;')
        funcs['__purge_vmap_area_lazy'] = f
    if args.negative:
        assert funcs != original, 'negative control did not modify extracted source'
    rb = '\n'.join(no_includes((root / p).read_text()) for p in [
        'include/linux/rbtree.h', 'include/linux/rbtree_augmented.h', 'lib/rbtree.c'])
    h = (root / 'include/linux/vmalloc.h').read_text()
    start = h.index('struct vmap_area {')
    end = h.index('\n};', start) + 3
    layout = h[start:end]
    start = s.index('RB_DECLARE_CALLBACKS(')
    callback = s[start:s.index(')', start) + 1] + ';'
    enum = s[s.index('enum fit_type {'):s.index('\n};', s.index('enum fit_type {')) + 3]
    first = '\n'.join(funcs[n] for n in names[:3]) + '\n' + callback
    rest = '\n'.join(funcs[n] for n in names[3:])
    seq = (root / 'fs/seq_file.c').read_text()
    seq_functions = '\n'.join(function(seq, n) for n in [
        'seq_list_start', 'seq_list_start_head', 'seq_list_next'])
    model = Path(__file__).with_name('model.c').read_text()
    for name, code in {'RB': rb, 'LIST': no_includes((root / 'include/linux/list.h').read_text()),
                       'LAYOUT': layout, 'FIRST': first, 'ENUM': enum,
                       'FUNCTIONS': rest, 'SEQ': seq_functions}.items():
        marker = '/* PRODUCTION_' + name + ' */'
        assert model.count(marker) == 1, marker
        model = model.replace(marker, code)
    with tempfile.TemporaryDirectory(prefix='vmalloc-test-') as tmp:
        source, binary = Path(tmp) / 'model.c', Path(tmp) / 'model'
        source.write_text(model)
        subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2', '-Wall', '-Wextra',
                       '-Werror', '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-sign-compare',
                       str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    guards(root)


if __name__ == '__main__':
    main()
