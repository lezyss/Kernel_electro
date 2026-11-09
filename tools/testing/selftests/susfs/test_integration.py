#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Offline SUSFS provenance/configuration checks and extracted-source models."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

from provenance_240 import reviewed_preimages

ROOT = Path(__file__).resolve().parents[4]
PIN = 'c931cae8ca19e4b738e3d9eda8fec4cdb7947473'
BRIDGE = 'fcd50c8f367c470fa8e17eb64fbb8c7ce7527061'
FEATURES = ['SUS_PATH', 'SUS_MOUNT', 'SUS_KSTAT', 'TRY_UMOUNT', 'SPOOF_UNAME',
            'ENABLE_LOG', 'HIDE_KSU_SUSFS_SYMBOLS', 'SPOOF_CMDLINE_OR_BOOTCONFIG',
            'OPEN_REDIRECT', 'SUS_MAP']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check(root, config, profile):
    previous = reviewed_preimages(root)
    manifest = json.loads((root / 'Documentation/filesystems/susfs/UPSTREAM.json').read_text())
    require(manifest['kernel_commit'] == PIN and manifest['ksu_bridge_commit'] == BRIDGE,
            'unexpected SUSFS/bridge revision; review updates explicitly')
    require(len(manifest['postimage_sha256']) == 32, 'incomplete hook manifest')
    # SUSFS's original postimages/patch remain immutable. One reviewed later
    # manager overlay touches dispatch.c; verify its preimage chain explicitly.
    overlay_path = root / 'Documentation/dev-tools/finasu-manager.json'
    overlay = json.loads(overlay_path.read_text()) if overlay_path.is_file() else None
    shared = set()
    if overlay:
        shared = set(overlay['postimage_sha256']) & set(manifest['postimage_sha256'])
        require(overlay['manager_review_commit'] ==
                '2d5786b9129a254a87ac358c8bec0203ccd53351' and
                shared == {'drivers/kernelsu/supercall/dispatch.c'},
                'unexpected FinaSU/SUSFS overlay overlap')
    # Later approved task-header changes must form an explicit, narrow chain.
    # Do not rewrite the immutable SUSFS manifest or skip its source checks.
    bpf_path = root / 'Documentation/bpf/susfs-compat-overlay.json'
    bpf_overlay = json.loads(bpf_path.read_text()) if bpf_path.is_file() else None
    bpf_shared = set()
    if bpf_overlay:
        bpf_shared = set(bpf_overlay['postimage_sha256'])
        require(bpf_overlay['schema'] == 1 and
                bpf_overlay['susfs_kernel_commit'] == PIN and
                bpf_overlay['bpf_reference_commit'] ==
                '2a58cdc0636e8eedba246338dd565bbfffc84837',
                'unexpected BPF/SUSFS overlay revision')
        require(bpf_shared == {'include/linux/sched.h'} and
                set(bpf_overlay['base_sha256']) == bpf_shared and
                set(bpf_overlay['pre_bpf_sha256']) == bpf_shared and
                not bpf_shared & shared,
                'unexpected BPF/SUSFS overlay scope')
        require(bpf_overlay['patch'] == 'Documentation/bpf/susfs-compat-overlay.diff',
                'unexpected BPF/SUSFS patch path')
        patch = root / bpf_overlay['patch']
        require(hashlib.sha256(patch.read_bytes()).hexdigest() ==
                bpf_overlay['patch_sha256'], 'BPF/SUSFS overlay patch changed')
        bpf_manifest = json.loads((root / 'Documentation/bpf/bpf-5.15-upgrade.json').read_text())
        records = [record for record in bpf_manifest['source_delta_records']
                   if record['path'] in bpf_shared]
        require(len(records) == 1, 'missing or duplicate BPF task-header record')
        record = records[0]
        name = record['path']
        require(bpf_overlay['base_sha256'][name] == manifest['postimage_sha256'][name],
                'broken SUSFS to task-header preimage chain')
        require(bpf_overlay['pre_bpf_sha256'][name] == record['before_sha256'] and
                bpf_overlay['postimage_sha256'][name] == record['after_sha256'],
                'broken task-header to BPF postimage chain')
    # Phoenix helper refactors retain the original SUSFS import and add a narrow
    # replayable after-image overlay. Never broaden the old BPF/manager overlays.
    phoenix_base = 'Documentation/dev-tools/phoenix-review/implementation/susfs-syscall-overlay'
    phoenix_path = root / (phoenix_base + '.json')
    phoenix = json.loads(phoenix_path.read_text()) if phoenix_path.is_file() else None
    phoenix_shared = set()
    if phoenix:
        phoenix_shared = set(phoenix['postimage_sha256'])
        require(phoenix['schema'] == 1 and phoenix['phase'] == 'PHX-IMPLEMENTATION-03' and
                phoenix['susfs_kernel_commit'] == PIN, 'unexpected Phoenix/SUSFS revision')
        require(phoenix_shared == {'fs/namei.c', 'fs/namespace.c', 'fs/open.c',
                                   'fs/readdir.c', 'fs/stat.c', 'kernel/sys.c'} and
                set(phoenix['base_sha256']) == phoenix_shared and
                not phoenix_shared & (shared | bpf_shared), 'unexpected Phoenix/SUSFS scope')
        require(phoenix['patch'] == phoenix_base + '.diff', 'unsafe Phoenix/SUSFS patch path')
        require(hashlib.sha256((root / phoenix['patch']).read_bytes()).hexdigest() ==
                phoenix['patch_sha256'], 'Phoenix/SUSFS patch changed')
        for name in phoenix_shared:
            require(phoenix['base_sha256'][name] == manifest['postimage_sha256'][name],
                    'broken SUSFS to Phoenix preimage chain')
    # KSU tag update: Makefile plus honest version labels after the FinaSU stage.
    ksu_base = 'Documentation/dev-tools/kernelsu-updates/v3.3.1-38'
    ksu_update = json.loads((root / (ksu_base + '.json')).read_text())
    ksu_shared = {'drivers/kernelsu/Makefile', 'drivers/kernelsu/supercall/dispatch.c'}
    require(ksu_update['schema'] == 1 and ksu_update['tag'] == 'v3.3.1-38' and
            ksu_update['old_commit'] == 'cbc0b49908066e9c7f778737f65a216f50b203ba' and
            ksu_update['commit'] == 'feeec8e4059e3bb0ecdd1827b687b69f1cf4a2fb',
            'unexpected KSU update revision')
    require(set(ksu_update['base_sha256']) == ksu_shared and
            set(ksu_update['postimage_sha256']) == ksu_shared,
            'unexpected KSU/SUSFS overlap scope')
    require(ksu_update['patch'] == ksu_base + '.diff', 'unsafe KSU update patch path')
    require(hashlib.sha256((root / ksu_update['patch']).read_bytes()).hexdigest() ==
            ksu_update['patch_sha256'], 'KSU update patch changed')
    for name in ksu_shared:
        expected_base = (overlay['postimage_sha256'][name] if name in shared
                         else manifest['postimage_sha256'][name])
        require(ksu_update['base_sha256'][name] == expected_base,
                'broken SUSFS to KSU update preimage chain')
    for name, digest in manifest['postimage_sha256'].items():
        if name in bpf_shared:
            digest = bpf_overlay['postimage_sha256'][name]
        if name in shared:
            require(overlay['base_sha256'][name] == digest, 'broken SUSFS to FinaSU preimage chain')
            digest = overlay['postimage_sha256'][name]
        if name in phoenix_shared:
            digest = phoenix['postimage_sha256'][name]
        if name in ksu_shared:
            digest = ksu_update['postimage_sha256'][name]
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe manifest path')
        file = root / name
        require(file.is_file() and not file.is_symlink(), 'missing regular source: ' + name)
        require(hashlib.sha256(previous.get(name, file.read_bytes())).hexdigest() == digest,
                'SUSFS source/hook changed without provenance review: ' + name)
    require({'fs/susfs.c', 'include/linux/susfs.h', 'include/linux/susfs_def.h'} <=
            set(manifest['postimage_sha256']), 'incomplete import')
    require((root / 'fs/Makefile').read_text().count('obj-$(CONFIG_KSU_SUSFS) += susfs.o') == 1,
            'SUSFS must be wired exactly once')
    require('depends on KSU = y' in (root / 'drivers/kernelsu/Kconfig').read_text(),
            'SUSFS needs built-in KSU')
    require('ARM64 && THREAD_INFO_IN_TASK && FSNOTIFY' in
            (root / 'drivers/kernelsu/Kconfig').read_text(), 'missing platform dependencies')
    values = dict(line.split('=', 1) for line in config.read_text().splitlines()
                  if line.startswith('CONFIG_') and '=' in line)
    expected = 'n' if profile == 'disabled' else 'y'
    require(values.get('CONFIG_KSU_SUSFS', 'n') == expected, 'wrong CONFIG_KSU_SUSFS')
    for feature in FEATURES:
        require(values.get('CONFIG_KSU_SUSFS_' + feature, 'n') ==
                ('y' if profile == 'full' else 'n'), 'wrong feature: ' + feature)
    require(values.get('CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER', 'n') ==
            ('y' if profile == 'full' else 'n'),
            'wrong priority UID filter setting for ' + profile + ' profile')
    if profile != 'disabled':
        for feature in ['KSU', 'ARM64', 'THREAD_INFO_IN_TASK', 'FSNOTIFY']:
            # THREAD_INFO_IN_TASK is selected by ARM64, not written in defconfig.
            if config.name != '.config' and feature in ['ARM64', 'THREAD_INFO_IN_TASK', 'FSNOTIFY']:
                continue
            require(values.get('CONFIG_' + feature) == 'y', 'missing ' + feature)
    print('SUSFS pinned source/hooks and ' + profile + ' configuration: PASS', flush=True)


def extract(source, name):
    match = re.search(r'^[^\n;{}]*?\b' + re.escape(name) + r'\([^;{}]*\)\s*\{', source, re.M)
    require(match is not None, 'missing function: ' + name)
    end, depth = match.end(), 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]


def models(root, cc, negative):
    driver = root / 'drivers/kernelsu'
    susfs = (root / 'fs/susfs.c').read_text()
    defs = (root / 'include/linux/susfs_def.h').read_text()
    allow = (driver / 'policy/allowlist.h').read_text()
    reboot = extract((driver / 'supercall/supercall.c').read_text(), 'ksu_handle_sys_reboot')
    commands = re.findall(r'if \(cmd == (CMD_SUSFS_\w+)\) \{\s*(susfs_\w+)\(arg\);', reboot)
    require(len(commands) == 17, 'incomplete SUSFS dispatch')
    stubs = '\n'.join('static void ' + name + '(void **arg) { payload_calls++; last_cmd = ' + cmd + '; }'
                      for name, cmd in {name: cmd for cmd, name in commands}.items())
    constants = '\n'.join(line for text in [defs, allow,
                          (driver / 'include/uapi/supercall.h').read_text()]
                          for line in text.splitlines() if re.match(
                              r'#define (CMD_SUSFS_|SUSFS_MAGIC|TIF_PROC_|AS_FLAGS_|KSU_INSTALL_MAGIC|'
                              r'PER_USER_RANGE|WEBVIEW_ZYGOTE_UID|FIRST_APPLICATION_UID|LAST_APPLICATION_UID|'
                              r'FIRST_ISOLATED_UID|LAST_ISOLATED_UID)', line))
    constants += '\n' + defs[defs.index('#define SUSFS_IS_INODE_SUS_MAP'):defs.rindex('#endif')]
    bodies = '\n'.join(extract(allow, name) for name in ['is_appuid', 'is_isolated_process'])
    bodies += '\n' + '\n'.join(extract(defs, name) for name in
                               ['susfs_is_current_app_uid', 'susfs_is_current_proc_umounted',
                                'susfs_set_current_proc_umounted', 'susfs_is_current_proc_umounted_app'])
    bodies += '\n' + extract((driver / 'feature/kernel_umount.c').read_text(), 'ksu_handle_umount')
    bodies += '\n' + extract((driver / 'hook/setuid_hook.c').read_text(), 'ksu_handle_setresuid_cred')
    bodies += '\n' + reboot
    bodies += '\n' + extract(susfs, 'susfs_open_redirect_spoof_vfs_readlink')
    bodies += '\n' + extract((root / 'fs/proc/task_mmu.c').read_text(), 'susfs_pagemap_hidden_range')
    bodies += '\n' + extract((root / 'fs/namespace.c').read_text(), 'mnt_free_id')
    if negative:
        before = bodies
        if negative == 'no-auth':
            bodies = bodies.replace('uid_eq(current_uid(), GLOBAL_ROOT_UID) &&\n        capable(CAP_SYS_ADMIN)', 'true')
        elif negative == 'no-zygote-guard':
            bodies = bodies.replace('if (!is_zygote_child)', 'if (false)')
        elif negative == 'readlink-zero-count':
            bodies = bodies.replace('return len;', 'return 0;')
        elif negative == 'hash-collision':
            bodies = bodies.replace('if (entry->target_ino != inode->i_ino)\n\t\t\tcontinue;', '')
        elif negative == 'early-hide':
            bodies = bodies.replace('const struct cred *saved = override_creds(ksu_cred);',
                                    'susfs_set_current_proc_umounted();\n\tconst struct cred *saved = override_creds(ksu_cred);')
        elif negative == 'free-borrowed-id':
            bodies = bodies.replace('if (mnt->mnt.mnt_flags & VFSMOUNT_MNT_FLAGS_KSU_UNSHARED_MNT)', 'if (false)')
        require(bodies != before, 'negative control did not mutate code')
    code = Path(__file__).with_name('model.c').read_text()
    code = code.replace('/* CONSTANTS */', constants).replace('/* STUBS */', stubs)
    code = code.replace('/* FUNCTIONS */', bodies)
    code = code.replace('/* COMMANDS */', ', '.join(cmd for cmd, _ in commands))
    with tempfile.TemporaryDirectory(prefix='susfs-host-') as temp:
        temp = Path(temp)
        (temp / 'model.c').write_text(code)
        subprocess.run(shlex.split(cc) + ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-unused-variable',
                       '-Wno-sign-compare', str(temp / 'model.c'), '-o', str(temp / 'model')], check=True)
        subprocess.run([str(temp / 'model')], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--config', type=Path,
                        default=Path('arch/arm64/configs/vendor/xiaomi/miatoll_defconfig'))
    parser.add_argument('--profile', choices=['full', 'minimal', 'disabled'], default='full')
    parser.add_argument('--host-tests', action='store_true')
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'clang'))
    parser.add_argument('--negative', choices=['no-auth', 'no-zygote-guard', 'readlink-zero-count',
                                             'hash-collision', 'free-borrowed-id', 'early-hide'])
    args = parser.parse_args()
    config = args.config if args.config.is_absolute() else args.source_root / args.config
    try:
        check(args.source_root, config, args.profile)
        if args.host_tests or args.negative:
            models(args.source_root, args.cc, args.negative)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print('SUSFS check FAILED: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
