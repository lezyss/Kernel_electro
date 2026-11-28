#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Verify current MM recency overlay, then unchanged predecessor receipts.

Current postimages are checked independently before projecting explicit, Git-
anchored preimages for the historical carry-over verifier. This is not a source
exception or a reseal of earlier manifests. No build/runtime proof is implied.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
DOC = 'Documentation/dev-tools/mm-recency'
BASE = 'a4f0c77b8d9d01e147aad1d1c9b3261f2ba04bce'
DONORS = ['9933074572034a9353fbed9fd75761164b5d42e4',
          '13b6149f8f0ccff490045990190655c1b284c24c']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def data_mode(p):
    if p.is_symlink():
        return os.readlink(p).encode(), '120000'
    assert p.is_file(), 'missing source/evidence: ' + str(p)
    return p.read_bytes(), '100755' if p.stat().st_mode & 0o111 else '100644'


def check_overlay(root):
    doc = root / DOC
    receipt = json.loads((doc / 'manifest.json').read_text())
    assert receipt['predecessor'] == BASE and receipt['ordered_donors'] == DONORS
    paths, preimages = receipt['paths'], {}
    patch = doc / 'adaptation.diff'
    assert sha(patch.read_bytes()) == receipt['patch_sha256'], 'overlay patch hash'
    with tempfile.TemporaryDirectory(prefix='mm-recency-replay-') as tmp:
        tmp = Path(tmp)
        for name, record in paths.items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts, name
            if record['preimage'] is None:
                assert record['preimage_mode'] is None
                continue
            data = (doc / 'preimages' / (name + '.preimage')).read_bytes()
            assert sha(data) == record['preimage'], 'overlay preimage hash: ' + name
            preimages[name] = data, record['preimage_mode']
            p = tmp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            p.chmod(0o755 if record['preimage_mode'] == '100755' else 0o644)
        subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patch.resolve())],
                       cwd=tmp, check=True)
        actual_paths = {p.relative_to(tmp).as_posix() for p in tmp.rglob('*') if p.is_file()}
        assert actual_paths == set(paths), 'overlay patch path set'
        for name, record in paths.items():
            data, mode = data_mode(root / name)
            assert data == (tmp / name).read_bytes(), 'not replayed current source: ' + name
            assert sha(data) == record['postimage'] and mode == record['mode'], name
        for name, digest in receipt['evidence_sha256'].items():
            assert sha((root / name).read_bytes()) == digest, 'overlay evidence hash: ' + name
    donors = [json.loads((doc / 'donors' / (s + '.json')).read_text()) for s in DONORS]
    assert [d['sha'] for d in donors] == DONORS
    assert donors[1]['parents'][0]['sha'] == DONORS[0], 'donor dependency order'
    return receipt, preimages


def check_predecessor(receipt, preimages):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT)
    base = {}
    for entry in git('ls-tree', '-rz', BASE).split(b'\0'):
        if not entry:
            continue
        info, name = entry.split(b'\t', 1)
        mode, kind, oid = info.decode().split()
        assert kind == 'blob'
        base[name.decode()] = mode, oid
    assert set(preimages) <= set(base)
    assert not (set(receipt['paths']) - set(preimages)) & set(base)
    for name, (data, mode) in preimages.items():
        assert mode == base[name][0] and data == git('show', BASE + ':' + name), 'not published preimage: ' + name
    for name, (mode, oid) in base.items():
        if name in preimages:
            continue  # current postimage and anchored preimage were BOTH checked above
        data, actual_mode = data_mode(ROOT / name)
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual == oid and actual_mode == mode, 'unrelated predecessor drift: ' + name
    print('PASS:', len(base), 'published predecessor paths/modes; only six declared MM source changes')


def historical_receipts(preimages):
    path = ROOT / 'tools/testing/selftests/carry_over/verify.py'
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location('recency_predecessor_verifier', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.file_data
    module.file_data = lambda name: preimages[name] if name in preimages else original(name)
    print('Checking UNCHANGED historical receipts against explicit published MM preimages;')
    print('CURRENT MM source bytes were independently verified by overlay replay above.')
    module.main()


def negative_controls():
    receipt, _ = check_overlay(ROOT)
    with tempfile.TemporaryDirectory(prefix='mm-recency-provenance-negative-') as tmp:
        tmp = Path(tmp)
        shutil.copytree(ROOT / DOC, tmp / DOC)
        for name in receipt['paths']:
            p = tmp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, p)
        cases = [
            ('mm/fadvise.c', 'not replayed current source'),
            (DOC + '/preimages/mm/rmap.c.preimage', 'overlay preimage hash'),
            (DOC + '/adaptation.diff', 'overlay patch hash'),
            (next(iter(receipt['evidence_sha256'])), 'overlay evidence hash'),
        ]
        for name, marker in cases:
            p = tmp / name
            original = p.read_bytes()
            p.write_bytes(original + b'\n/* corruption */\n')
            try:
                check_overlay(tmp)
            except AssertionError as error:
                assert marker in str(error), str(error)
            else:
                raise AssertionError('accepted corrupted ' + name)
            finally:
                p.write_bytes(original)
    print('PASS: four overlay negative controls (current source, preimage, patch, evidence)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--negative-controls', action='store_true')
    args = parser.parse_args()
    receipt, preimages = check_overlay(ROOT)
    assert len(preimages) == 6
    check_predecessor(receipt, preimages)
    historical_receipts(preimages)
    if args.negative_controls:
        negative_controls()
    print('PASS: current MM recency overlay, donor dependency order, evidence, modes and predecessor receipt chain')
    print('LIMITS: source/provenance only; not image, device, concurrency or performance qualification.')


if __name__ == '__main__':
    main()
