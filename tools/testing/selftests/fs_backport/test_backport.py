#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted-source filesystem lifetime/locking models, not kernel stress tests."""
import argparse
import os
from pathlib import Path
import re
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
    return text[start:end]


def function(text, name, last=False):
    matches = re.finditer(r'^(?:[A-Za-z_][^\n;]*?[ \t]+\**)?' +
                          re.escape(name) + r'\(', text, re.M)
    found = []
    for match in matches:
        opening = text.index('{', match.end())
        semi = text.find(';', match.end())
        if semi >= 0 and semi < opening:
            continue
        start = match.start()
        prev = text[:start].splitlines()[-1] if start else ''
        if prev.startswith('static ') or prev == 'int':
            start -= len(prev) + 1
        found.append(braced(text, start))
    assert found, name
    return found[-1 if last else 0]


def integration(root):
    f = (root / 'fs/f2fs/file.c').read_text()
    for name in ['f2fs_move_file_range', 'f2fs_ioc_set_pin_file']:
        body = function(f, name)
        assert body.index('inode_lock(') < body.index('if (f2fs_is_atomic_file(')
    assert 'f2fs_is_atomic_file(inode)' in function(f, 'f2fs_ioc_defragment')
    gc = function((root / 'fs/f2fs/gc.c').read_text(), 'gc_data_segment')
    assert gc.index('if (f2fs_has_inline_data(inode))') < gc.index('if (!down_write_trylock(')
    ep = (root / 'fs/eventpoll.c').read_text()
    assert 'kfree_rcu(ep,' not in ep and 'kfree(ep);' in function(ep, 'ep_free')
    h = (root / 'fs/f2fs/segment.h').read_text()
    assert re.search(r'DEF_RECLAIM_PREFREE_SEGMENTS\s+5\b', h)
    assert re.search(r'DEF_MAX_RECLAIM_PREFREE_SEGMENTS\s+4096\b', h)
    assert 'set_opt(sbi, ATGC)' not in (root / 'fs/f2fs/super.c').read_text()
    wb = (root / 'fs/fs-writeback.c').read_text()
    mark = function(wb, '__mark_inode_dirty')
    assert 'dirtytime && (inode->i_state & I_DIRTY_INODE)' in mark
    assert 'if (inode->i_state & (I_WILL_FREE | I_FREEING))' in mark
    cfg = (root / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    assert 'CONFIG_F2FS_FS_COMPRESSION=y' not in cfg
    print('Selected fixes/skipped policy integration guards: PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'clang'))
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--negative', choices=['no-file-pin', 'missing-fput',
                        'donor-freeing', 'late-freeing', 'no-cp-lock',
                        'gc-after-iput', 'atomic-bypass'])
    args = parser.parse_args()
    root = args.source_root
    ep = (root / 'fs/eventpoll.c').read_text()
    poll = (root / 'include/linux/poll.h').read_text()
    wb = (root / 'fs/fs-writeback.c').read_text()
    f2 = (root / 'fs/f2fs/file.c').read_text()
    gc = function((root / 'fs/f2fs/gc.c').read_text(), 'gc_data_segment')
    gc_guard = braced(gc, gc.index('if (f2fs_has_inline_data(inode))'))
    move = function(f2, 'f2fs_move_file_range')
    move_prefix = move[move.index('\tinode_lock(src);'):
                       move.index('\tret = -EINVAL;\n\tif (pos_in + len')]
    move_suffix = move[move.index('out_unlock:'):move.rindex('}')]
    pin = function(f2, 'f2fs_ioc_set_pin_file')
    pin_guard = braced(pin, pin.index('if (f2fs_is_atomic_file(inode))'))
    pin_cleanup = pin[pin.index('out:'):pin.rindex('}')]
    code = {
        'EPOLL': '\n'.join([function(poll, 'vfs_poll'), function(ep, 'epi_fget'),
                            function(ep, 'ep_item_poll')]),
        'WRITEBACK': '\n'.join([
            '#if CGWB', function(wb, 'locked_inode_to_wb_and_lock_list'),
            function(wb, 'inode_to_wb_and_lock_list'), '#else',
            function(wb, 'locked_inode_to_wb_and_lock_list', last=True),
            function(wb, 'inode_to_wb_and_lock_list', last=True), '#endif',
            function(wb, 'writeback_single_inode'), function(wb, '__mark_inode_dirty')]),
        'RELEASE': braced(function(f2, 'f2fs_release_compress_blocks'),
                          function(f2, 'f2fs_release_compress_blocks').index('while (page_idx < last_idx)')),
        'RESERVE': braced(function(f2, 'f2fs_reserve_compress_blocks'),
                          function(f2, 'f2fs_reserve_compress_blocks').index('while (page_idx < last_idx)')),
        'GC': gc_guard, 'MOVE_PREFIX': move_prefix, 'MOVE_SUFFIX': move_suffix,
        'PIN': pin_guard, 'PIN_CLEANUP': pin_cleanup,
    }
    original = code.copy()
    if args.negative == 'no-file-pin':
        code['EPOLL'] = code['EPOLL'].replace('if (!atomic_long_inc_not_zero(&file->f_count))',
                                            'if (false)')
    if args.negative == 'missing-fput':
        code['EPOLL'] = code['EPOLL'].replace('fput(file);', '')
    if args.negative == 'donor-freeing':
        code['WRITEBACK'] = code['WRITEBACK'].replace(
            'if (!(inode->i_state & (I_FREEING | I_DIRTY_ALL)))',
            'if (!(inode->i_state & I_DIRTY_ALL) || (inode->i_state & I_FREEING))')
    if args.negative == 'late-freeing':
        text = code['WRITEBACK']
        start = text.index('wakeup_bdi = inode_io_list_move_locked')
        end = text.index(';', start) + 1
        call = text[start:end]
        guard = text.rindex('if (inode->i_state & (I_WILL_FREE | I_FREEING))')
        text = text[:start] + text[end:]
        text = text[:guard] + call + '\n' + text[guard:]
        code['WRITEBACK'] = text
    if args.negative == 'no-cp-lock':
        for name in ['RELEASE', 'RESERVE']:
            code[name] = code[name].replace('f2fs_lock_op(sbi);', '').replace('f2fs_unlock_op(sbi);', '')
    if args.negative == 'gc-after-iput':
        code['GC'] = code['GC'].replace('iput(inode);', '').replace(
            'set_sbi_flag(sbi, SBI_NEED_FSCK);', 'iput(inode);\nset_sbi_flag(sbi, SBI_NEED_FSCK);')
    if args.negative == 'atomic-bypass':
        code['MOVE_PREFIX'] = code['MOVE_PREFIX'].replace(
            'f2fs_is_atomic_file(src) || f2fs_is_atomic_file(dst)', 'false')
        code['PIN'] = code['PIN'].replace('f2fs_is_atomic_file(inode)', 'false')
    if args.negative:
        assert code != original, 'negative control made no source change'
    template = Path(__file__).with_name('model.c').read_text()
    for name, value in code.items():
        marker = '/* PRODUCTION_' + name + ' */'
        assert template.count(marker) == 1, marker
        template = template.replace(marker, value)
    with tempfile.TemporaryDirectory(prefix='fs-backport-') as tmp:
        source = Path(tmp) / 'model.c'
        source.write_text(template)
        for cgwb in [0, 1]:
            binary = Path(tmp) / ('model-' + str(cgwb))
            subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2', '-Wall', '-Wextra',
                           '-Werror', '-Wno-unused-parameter', '-Wno-unused-function',
                           '-Wno-sign-compare', '-DCGWB=' + str(cgwb), str(source),
                           '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
    integration(root)


if __name__ == '__main__':
    main()
