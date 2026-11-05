#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted-source MM backport models, not running-kernel stress tests."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def braced(text, start):
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end], end


def function(text, signature):
    return braced(text, text.index(signature))[0]


def guard(text, start):
    first, end = braced(text, start)
    assert text[end:end + 7] == ' else {'
    second, _ = braced(text, end + 1)
    return first + ' ' + second


def sources(root, negative):
    def read(name):
        return (root / name).read_text()

    filemap = read('mm/filemap.c')
    marker = 'if (unlikely(!mapping->a_ops || !mapping->a_ops->readpage))'
    first = filemap.index(marker)
    second = filemap.index(marker, first + 1)
    buffered = guard(filemap, first)
    fault = guard(filemap, second)
    swap = function(read('mm/page_io.c'), 'int swap_readpage(')
    if negative == 'donor-psi':
        old = 'if (workingset)\n\t\tpsi_memstall_leave(&pflags);'
        assert old in swap
        swap = swap.replace(old, 'psi_memstall_leave(&pflags);')
    compaction = read('include/linux/compaction.h')
    enums = '\n'.join(function(compaction, 'enum ' + name) + ';'
                      for name in ['compact_priority', 'compact_result'])
    helpers = '\n'.join(function(compaction, 'static inline bool ' + name + '(')
                        for name in ['compaction_made_progress', 'compaction_failed',
                                     'compaction_needs_reclaim', 'compaction_withdrawn'])
    flags = read('include/trace/events/mmflags.h')
    feedback = flags[flags.index('#define COMPACTION_FAILED'):
                     flags.index('#define COMPACTION_FEEDBACK')]
    if negative == 'old-trace':
        old = 'compaction_needs_reclaim(__result) || \\\n\t\t '
        assert old in feedback
        feedback = feedback.replace(old, '')
    shrink = function(read('mm/vmscan.c'), 'static unsigned long do_shrink_slab(')
    if negative == 'old-shrinker':
        start = shrink.index('if (shrinker->seeks)')
        branch = guard(shrink, start)
        shrink = shrink.replace(branch, 'delta = freeable >> priority;\n'
                                'delta *= 4;\ndo_div(delta, shrinker->seeks);')
    retry = function(read('mm/page_alloc.c'), 'static inline bool\nshould_compact_retry(')
    if negative == 'old-retry':
        old = 'if (compaction_withdrawn(compact_result)) {\n\t\tgoto check_priority;\n\t}'
        assert old in retry
        retry = retry.replace(old, 'if (compaction_withdrawn(compact_result)) {\n'
                              '\t\tret = compaction_zonelist_suitable(ac, order, alloc_flags);\n'
                              '\t\tgoto out;\n\t}')
    return {'BUFFERED': buffered, 'FAULT': fault, 'SWAP': swap,
            'READAHEAD': function(read('mm/readahead.c'), 'static int read_pages('),
            'ENUMS': enums, 'HELPERS': helpers, 'FEEDBACK': feedback,
            'RETRY': retry,
            'SHRINK': shrink,
            'QUIET': function(read('mm/vmstat.c'), 'void quiet_vmstat(')}


def source_guards(root):
    def read(name):
        return (root / name).read_text()

    for name, marker in [('fs/proc/inode.c', 's->s_shrink.seeks = 0;'),
                         ('fs/kernfs/mount.c', 'sb->s_shrink.seeks = 0;')]:
        assert marker in read(name), name
    ws = read('mm/workingset.c')
    assert '.seeks = 0, /* ->count reports only fully expendable nodes */' in ws
    assert 'if (nodes <= max_nodes)\n\t\treturn 0;' in ws
    assert 'return nodes - max_nodes;' in ws
    assert 'lru_gen_refault(page, shadow);' in ws
    swap = read('mm/swap_state.c')
    assert 'if (!lru_gen_enabled())\n\t\t\t\tSetPageWorkingset(new_page);' in swap
    assert 'else if (shadow)\n\t\t\t\tlru_gen_refault(new_page, shadow);' in swap
    vmstat = function(read('mm/vmstat.c'), 'void quiet_vmstat(')
    assert 'unlikely(system_state != SYSTEM_RUNNING)' in vmstat
    assert 'likely(!need_update(smp_processor_id()))' in vmstat
    # Explicitly retain the local LMK retry gate and all untaken policy defaults.
    assert 'if (should_compact_lmk_retry(ac, order, alloc_flags))' in read('mm/page_alloc.c')
    assert 'int watermark_scale_factor = 35;' in read('mm/page_alloc.c')
    assert 'int sysctl_extfrag_threshold = 500;' in read('mm/compaction.c')
    assert 'sysctl_compact_unevictable_allowed __read_mostly = 1;' in read('mm/compaction.c')
    assert 'int sysctl_stat_interval __read_mostly = HZ;' in read('mm/vmstat.c')
    assert 'vm_dirty_ratio = 20;' in read('mm/page-writeback.c')
    assert 'dirty_writeback_interval = 5 * 100;' in read('mm/page-writeback.c')
    assert 'static long ratelimit_pages = 32;' in read('mm/page-writeback.c')
    assert 'sysctl_overcommit_memory __read_mostly = OVERCOMMIT_GUESS;' in read('mm/util.c')
    assert 'sysctl_overcommit_ratio __read_mostly = 50;' in read('mm/util.c')
    print('Integration/default source guards: PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--negative', choices=['donor-psi', 'old-trace', 'old-shrinker', 'old-retry'])
    args = parser.parse_args()
    template = Path(__file__).with_name('model.c').read_text()
    for name, value in sources(args.source_root, args.negative).items():
        marker = '/* PRODUCTION_' + name + ' */'
        assert template.count(marker) == 1, marker
        template = template.replace(marker, value)
    with tempfile.TemporaryDirectory(prefix='mm-backport-') as tmp:
        source, binary = Path(tmp) / 'model.c', Path(tmp) / 'model'
        source.write_text(template)
        subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2', '-Wall', '-Wextra',
                       '-Werror', '-Wno-unused-parameter', '-Wno-sign-compare', str(source), '-o', str(binary)],
                       check=True)
        subprocess.run([str(binary)], check=True)
    source_guards(args.source_root)


if __name__ == '__main__':
    main()
