#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Check the explicit base-swap checkpoint, NOT kernel build/runtime health."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
BASE = '766a32ab1c8b889ac049ccd367e82786e5953bc0'
OLD = '402566a8597ae7f0ecf3f87054b77aa7c18acdf0'
EXTRA = {
    'Documentation/dev-tools/electro-change-inventory-no-sm8150-phoenix.md',
}
PREFIXES = ('Documentation/dev-tools/base-sync-16/', 'tools/testing/selftests/base_sync/')


def tree(commit):
    raw = subprocess.check_output(['git', 'ls-tree', '-rz', commit], cwd=ROOT)
    result = {}
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        info, name = entry.split(b'\t', 1)
        mode, kind, sha = info.decode().split()
        assert kind == 'blob', (name, kind)
        result[name.decode()] = (mode, sha)
    return result


def main():
    base, old = tree(BASE), tree(OLD)
    for name, (mode, sha) in base.items():
        p = ROOT / name
        if mode == '120000':
            assert p.is_symlink(), name
            data = os.readlink(p).encode()
        else:
            assert p.is_file() and not p.is_symlink(), name
            data = p.read_bytes()
            assert bool(p.stat().st_mode & 0o111) == (mode == '100755'), name
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual == sha, 'not exact pinned foundation: ' + name
    for name in old.keys() - base.keys():
        if name in EXTRA or name.startswith(PREFIXES):
            continue
        assert not (ROOT / name).exists(), 'unreviewed old carry-over: ' + name
    for name in ['net/ipv4/tcp_bbrplus.c', 'drivers/kernelsu', 'fs/nomount', 'fs/susfs.c']:
        p = ROOT / name
        # Empty former directories are not an imported integration.
        assert not p.exists() or (p.is_dir() and not any(
            q.is_file() or q.is_symlink() for q in p.rglob('*'))), name
    config = (ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    assert 'CONFIG_TCP_CONG_BBRPLUS=y' not in config
    manifest = json.loads((ROOT / 'Documentation/dev-tools/base-sync-16/audit.json').read_text())
    assert manifest['foundation'] == BASE and manifest['previous_electro'] == OLD
    rows = manifest['rows']
    assert len(rows) == 143 and len({r['sha'] for r in rows}) == 143
    excluded = [r for r in rows if r['status'] == 'excluded-bbrplus']
    assert len(excluded) == 1 and excluded[0]['sha'].startswith('40213eb4')
    print(f'PASS: all{len(base)} pinned foundation files/modes match; no unreviewed old files or BBRplus carried over.')
    print('PASS:143 inventory references accounted for; BBRplus explicitly excluded.')
    print('LIMITS: base-only audit checkpoint, missing integrations NOT restored; known CI/LZ4 blockers; NOT ready to flash.')


if __name__ == '__main__':
    main()
