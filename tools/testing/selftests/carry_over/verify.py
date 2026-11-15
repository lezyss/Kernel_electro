#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Verify ordered carry-over source overlays without resealing earlier receipts.

Requires pinned16 and previous Electro Git objects. Source/provenance checking
only: successful replay is not semantic, target-build or device proof.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
DOC = ROOT / 'Documentation/dev-tools/carry-over'
BASE = '766a32ab1c8b889ac049ccd367e82786e5953bc0'
OLD = '402566a8597ae7f0ecf3f87054b77aa7c18acdf0'

from lz4_overlay import Overlay

RESTORATION = Overlay(ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def tree(commit):
    records = {}
    for entry in git('ls-tree', '-rz', commit).split(b'\0'):
        if not entry:
            continue
        info, name = entry.split(b'\t', 1)
        mode, kind, oid = info.decode().split()
        assert kind == 'blob', name
        records[name.decode()] = mode, oid
    return records


def file_data(name):
    # Verify the historical view against its UNCHANGED receipts. The overlay
    # below separately checks every current postimage by ordered patch replay.
    if name in RESTORATION.preimages:
        return RESTORATION.preimages[name]
    p = ROOT / name
    if p.is_symlink():
        return os.readlink(p).encode(), '120000'
    assert p.is_file(), 'missing source/evidence: ' + name
    return p.read_bytes(), '100755' if p.stat().st_mode & 0o111 else '100644'


def check_hashes(records):
    for name, digest in records.items():
        data, _ = file_data(name)
        assert sha(data) == digest, 'source/evidence hash mismatch: ' + name


def main():
    progress = json.loads((DOC / 'progress.json').read_text())
    assert progress['foundation'] == BASE
    foundation = json.loads((ROOT / 'Documentation/dev-tools/foundation-repair/manifest.json').read_text())
    assert foundation['foundation'] == BASE
    base = tree(BASE)
    batches = [json.loads((DOC / name).read_text()) for name in progress['ordered_batches']]
    all_paths = set().union(*(m['postimage_sha256'] for m in batches))
    # These first batches do not modify the repaired codec/build paths. A later
    # batch overlapping them needs a reproducible repaired-baseline preimage;
    # never silently treat a changed working file as its own trusted baseline.
    assert not all_paths & (foundation['modified_base'].keys() | foundation['added_source'].keys())
    applied = set()
    additions = {}
    for batch in batches:
        for name in batch.get('added_paths', []):
            assert name not in base and name not in additions, 'invalid/duplicate source addition: ' + name
            additions[name] = batch.get('addition_modes', {}).get(name, '100644')
    with tempfile.TemporaryDirectory(prefix='carry-over-replay-') as tmp:
        tmp = Path(tmp)
        for name in all_paths:
            assert name in base or name in additions, 'undeclared source addition: ' + name
            p = tmp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            if name in base:
                p.write_bytes(git('show', BASE + ':' + name))
        for batch in batches:
            assert batch['foundation'] == BASE and batch['previous_electro'] == OLD
            assert not applied & set(batch['ids']), 'duplicate applied inventory IDs'
            applied.update(batch['ids'])
            assert set(batch['preimage_sha256']) == set(batch['postimage_sha256'])
            for name, digest in batch['preimage_sha256'].items():
                assert sha((tmp / name).read_bytes() if (tmp / name).exists() else b'') == digest, 'overlay preimage mismatch: ' + name
            patch = ROOT / batch['patch']
            assert sha(patch.read_bytes()) == batch['patch_sha256'], patch
            subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patch)], cwd=tmp, check=True)
            for name, digest in batch['postimage_sha256'].items():
                assert sha((tmp / name).read_bytes()) == digest, 'overlay postimage mismatch: ' + name
            for local, original in batch['historical_source'].items():
                assert (ROOT / local).read_bytes() == git('show', OLD + ':' + original), local
            for local, origin in batch.get('historical_git_source', {}).items():
                assert (ROOT / local).read_bytes() == git('show', origin['commit'] + ':' + origin['path']), local
        expected = {name: (tmp / name).read_bytes() for name in all_paths}
        for name, mode in additions.items():
            data, actual_mode = file_data(name)
            assert data == expected[name] and mode == actual_mode, 'source addition bytes/mode: ' + name

    for name, (mode, oid) in base.items():
        data, actual_mode = file_data(name)
        assert mode == actual_mode, 'base mode changed: ' + name
        if name in expected:
            assert data == expected[name], 'not the reviewed ordered overlay: ' + name
        elif name in foundation['modified_base']:
            record = foundation['modified_base'][name]
            assert record['base_blob'] == oid and sha(data) == record['sha256'], name
        else:
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            assert actual == oid, 'unreviewed base change: ' + name
    for name, record in foundation['added_source'].items():
        data, mode = file_data(name)
        assert mode == record['mode'] and sha(data) == record['sha256'], name
    # All old base-audit/foundation-repair evidence remains unchanged.
    check_hashes(foundation['evidence_sha256'])
    checkpoint_path = ROOT / 'Documentation/dev-tools/base-sync-16/checkpoint.json'
    assert sha(checkpoint_path.read_bytes()) == foundation['historical_checkpoint_sha256']
    checkpoint = json.loads(checkpoint_path.read_text())
    check_hashes(checkpoint['artifacts_sha256'])
    index = json.loads((DOC / 'validation.json').read_text())
    check_hashes(index['artifacts_sha256'])
    for name, record in index['added_source'].items():
        data, mode = file_data(name)
        assert sha(data) == record['sha256'] and mode == record['mode'], name

    assert set(RESTORATION.preimages) <= (set(base) | set(foundation['added_source']) |
                                          set(index['added_source']) | set(additions))
    assert not RESTORATION.additions & (set(base) | set(foundation['added_source']) |
                                       set(index['added_source']) | set(additions))
    RESTORATION.verify_current()

    original_rows = json.loads((ROOT / 'Documentation/dev-tools/base-sync-16/audit.json').read_text())['rows']
    rows = {r['id']: r for r in progress['items']}
    assert len(rows) == len(progress['items']) == len(original_rows) == 143
    for row in original_rows:
        assert rows[row['id']]['sha'] == row['sha'], row['id']
    assert applied == {k for k, r in rows.items() if r['status'] == 'applied-bounded-validation'}
    assert rows['E143']['status'] == 'native-equivalent-reference-unresolved'
    assert '__SK_PASS,' in git('show', BASE + ':include/linux/skmsg.h').decode()
    assert '__SK_PASS,' in (ROOT / 'include/linux/skmsg.h').read_text()
    assert not any(r['status'] in ('pending-review', 'integrated-validation-pending') for r in rows.values())
    assert rows['E115']['status'] == 'superseded-by-foundation-lz4-1.11.1'
    assert rows['E118']['status'] == 'excluded-bbrplus'
    forbidden = ('net/ipv4/tcp_bbrplus.c',)
    for name in forbidden:
        p = ROOT / name
        assert not p.exists() or p.is_dir() and not any(
            q.is_file() or q.is_symlink() for q in p.rglob('*')), name
    # Reject unrelated historical files, while allowing only these source/test
    # additions and unchanged historical evidence. No wholesale old-tree import.
    allowed = (set(additions) | set(index['added_source']) | set(foundation['added_source']) |
               set(checkpoint['artifacts_sha256']) |
               RESTORATION.additions |
               {'Documentation/dev-tools/base-sync-16/checkpoint.json'})
    for name in tree(OLD).keys() - base.keys() - allowed:
        assert not (ROOT / name).exists(), 'unreviewed old carry-over: ' + name
    config = (ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    assert 'CONFIG_TCP_CONG_BBRPLUS=y' not in config
    print(f'PASS: {len(base)} base paths/modes checked; {len(all_paths)} carried source paths '
          'reproduced by ordered patch replay; historical foundation receipts unchanged; explicit LZ4 overlay checked above.')
    print(f'PASS: {len(applied)} inventory references covered; '
          f'{sum(r["status"] == "pending-review" for r in rows.values())} pending; E143 native equivalent (reference unresolved); '
          'LZ4 codec superseded by 1.11.1, ARM64 accelerator restored separately; BBRplus excluded.')
    print('PASS: historical receipts, batch evidence, new test hashes and no-unreviewed-old-carry-over checks.')
    print('LIMITS: source/provenance only; no whole-image, device, concurrency or performance qualification.')


if __name__ == '__main__':
    main()
