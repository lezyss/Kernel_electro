#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Verify the scoped repair over pinned16 without rewriting the base-only audit.

This checks source/modes and historical evidence, NOT build/runtime health.
The separate repair manifest is a review receipt, not a signed attestation.
"""
import hashlib
import json
import os

from verify_foundation import BASE, OLD, ROOT, tree


def data_and_mode(name):
    p = ROOT / name
    if p.is_symlink():
        return os.readlink(p).encode(), '120000'
    assert p.is_file(), 'missing file: ' + name
    return p.read_bytes(), '100755' if p.stat().st_mode & 0o111 else '100644'


def main():
    receipt = ROOT / 'Documentation/dev-tools/foundation-repair/manifest.json'
    manifest = json.loads(receipt.read_text())
    assert manifest['foundation'] == BASE
    base, old = tree(BASE), tree(OLD)
    changed = manifest['modified_base']
    added = manifest['added_source']
    assert not added.keys() & base.keys()
    assert changed.keys() <= base.keys()
    for name, (mode, sha) in base.items():
        data, actual_mode = data_and_mode(name)
        assert actual_mode == mode, 'base mode changed: ' + name
        if name in changed:
            assert hashlib.sha256(data).hexdigest() == changed[name]['sha256'], name
            assert changed[name]['base_blob'] == sha, name
        else:
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            assert actual == sha, 'unreviewed foundation change: ' + name
    for name, record in added.items():
        data, mode = data_and_mode(name)
        assert hashlib.sha256(data).hexdigest() == record['sha256'], name
        assert mode == record['mode'], name
    checkpoint = 'Documentation/dev-tools/base-sync-16/checkpoint.json'
    data, _ = data_and_mode(checkpoint)
    assert hashlib.sha256(data).hexdigest() == manifest['historical_checkpoint_sha256']
    historical = json.loads(data)['artifacts_sha256']
    for name, digest in historical.items():
        data, _ = data_and_mode(name)
        assert hashlib.sha256(data).hexdigest() == digest, 'historical artifact changed: ' + name
    for name, digest in manifest['evidence_sha256'].items():
        data, _ = data_and_mode(name)
        assert hashlib.sha256(data).hexdigest() == digest, 'repair evidence changed: ' + name
    allowed = set(added) | set(historical) | {checkpoint}
    for name in old.keys() - base.keys() - allowed:
        assert not (ROOT / name).exists(), 'unreviewed old carry-over: ' + name
    for name in ('net/ipv4/tcp_bbrplus.c', 'drivers/kernelsu', 'fs/nomount', 'fs/susfs.c'):
        p = ROOT / name
        assert not p.exists() or (p.is_dir() and not any(
            q.is_file() or q.is_symlink() for q in p.rglob('*'))), name
    config = (ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    assert 'CONFIG_TCP_CONG_BBRPLUS=y' not in config
    print(f'PASS: {len(base)} base paths/modes checked: {len(changed)} scoped repairs, '
          f'{len(base) - len(changed)} byte-identical to pinned16.')
    print(f'PASS: {len(added)} added source/test files match repair receipt; '
          'historical base-only audit unchanged; no unreviewed old carry-over or BBRplus.')
    print('LIMITS: source verification only; no full image/boot/device qualification.')


if __name__ == '__main__':
    main()
