#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Closed, replayable SUSFS 2.4 successor; historical import seals stay intact."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

BASE = 'Documentation/filesystems/susfs/backport-2.4.0'
MANIFEST_SHA256 = '56cb00f9efa712bbbea16ca68aa633f19264630ebe4dac4e0dce80db7432e10d'
SCOPE = {
    'block/ioprio.c', 'drivers/kernelsu/Kconfig',
    'drivers/kernelsu/feature/kernel_umount.c',
    'drivers/kernelsu/feature/selinux_hide.c',
    'drivers/kernelsu/feature/sucompat.c',
    'drivers/kernelsu/hook/syscall_table_hook_arm64.c',
    'drivers/kernelsu/selinux/sepolicy.c',
    'drivers/kernelsu/supercall/supercall.c',
    'fs/namei.c', 'fs/namespace.c', 'fs/statfs.c', 'fs/susfs.c',
    'include/linux/susfs.h', 'include/linux/susfs_def.h', 'kernel/sys.c',
    'security/selinux/avc.c', 'security/selinux/hooks.c',
    'security/selinux/include/security.h', 'security/selinux/selinuxfs.c',
    'security/selinux/ss/services.c',
}


def require(ok, message):
    if not ok:
        raise ValueError('SUSFS 2.4 successor: ' + message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reviewed_preimages(root):
    """Validate current sources and replay, returning the exact pre-2.4 bytes.

    Older KSU/SUSFS/Phoenix checkers must still check these bytes against their
    own immutable seals. This is not permission to skip or reseal old checks.
    """
    root = Path(root)
    raw = (root / (BASE + '.json')).read_bytes()
    require(sha(raw) == MANIFEST_SHA256, 'manifest changed without review')
    manifest = json.loads(raw)
    require(manifest['schema'] == 1 and manifest['version'] == '2.4.0' and
            manifest['repository'] == 'https://gitlab.com/simonpunk/susfs4ksu' and
            manifest['commit'] == '45a057536ddba12fd59fb583a8f5375f83be703e' and
            manifest['tree'] == 'a90aee9a6a867ce1954b89bb4dd95d77872b0193',
            'wrong original-source pin')
    require(set(manifest['base_sha256']) == set(manifest['postimage_sha256']) == SCOPE,
            'scope changed')
    require(manifest['patch'] == BASE + '.diff', 'unsafe patch path')
    patch = (root / manifest['patch']).read_bytes()
    require(sha(patch) == manifest['patch_sha256'], 'patch changed')
    pairs = re.findall(rb'^diff --git a/(\S+) b/(\S+)$', patch, re.M)
    require(len(pairs) == len(SCOPE) and
            {a.decode() for a, b in pairs if a == b} == SCOPE,
            'patch has unexpected paths')
    current = {}
    for name in SCOPE:
        file = root / name
        require(file.is_file() and not file.is_symlink(), 'missing regular source: ' + name)
        current[name] = file.read_bytes()
        require(sha(current[name]) == manifest['postimage_sha256'][name],
                'source changed: ' + name)
    try:
        with tempfile.TemporaryDirectory(prefix='susfs-240-replay-') as directory:
            tree = Path(directory)
            for name, data in current.items():
                file = tree / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data)
            subprocess.run(['git', 'apply', '--reverse', '--whitespace=nowarn', '-'],
                           input=patch, cwd=tree, check=True, capture_output=True)
            before = {name: (tree / name).read_bytes() for name in SCOPE}
            for name, data in before.items():
                require(sha(data) == manifest['base_sha256'][name],
                        'broken preimage: ' + name)
            subprocess.run(['git', 'apply', '--whitespace=nowarn', '-'],
                           input=patch, cwd=tree, check=True, capture_output=True)
            require(all((tree / name).read_bytes() == data for name, data in current.items()),
                    'forward replay differs')
    except subprocess.CalledProcessError as error:
        raise ValueError('SUSFS 2.4 successor replay failed') from error
    return before
