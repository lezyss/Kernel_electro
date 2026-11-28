#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Explicit post-reconciliation LZ4 overlay; never reseal historical receipts.

The caller checks returned preimages against the original foundation/batch
receipts. This module independently replays the overlay and checks CURRENT
files, modes and evidence. Neither manifest is a signed attestation.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

DOC = 'Documentation/dev-tools/lz4-arm64-restore'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Overlay:
    def __init__(self, root):
        self.root = root
        self.doc = root / DOC
        self.receipt = json.loads((self.doc / 'manifest.json').read_text())
        assert self.receipt['donor'] == '1a206aea00ea8e1788f12639251304de28083659'
        assert self.receipt['lz4_upstream'] == 'aa4647fad575d01a874aaaadcdbe8e6a40e072f5'
        self.paths = self.receipt['paths']
        self.preimages = {}
        for name, record in self.paths.items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts, name
            if record['preimage'] is not None:
                p = self.doc / 'preimages' / (name + '.preimage')
                data = p.read_bytes()
                assert sha(data) == record['preimage'], 'restoration preimage hash: ' + name
                self.preimages[name] = data, record['preimage_mode']
            else:
                assert record['preimage_mode'] is None

    @property
    def additions(self):
        return set(self.paths) - set(self.preimages)

    def verify_current(self):
        patch = self.doc / 'restoration.patch'
        assert sha(patch.read_bytes()) == self.receipt['patch_sha256'], 'restoration patch hash'
        with tempfile.TemporaryDirectory(prefix='lz4-overlay-replay-') as tmp:
            tmp = Path(tmp)
            for name, (data, mode) in self.preimages.items():
                p = tmp / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                p.chmod(0o755 if mode == '100755' else 0o644)
            subprocess.run(['git', 'apply', '--whitespace=nowarn', str(patch.resolve())],
                           cwd=tmp, check=True)
            actual_paths = {p.relative_to(tmp).as_posix() for p in tmp.rglob('*') if p.is_file()}
            assert actual_paths == set(self.paths), 'restoration patch path set'
            for name, record in self.paths.items():
                p = self.root / name
                assert p.is_file() and not p.is_symlink(), 'missing restoration source: ' + name
                data = p.read_bytes()
                assert data == (tmp / name).read_bytes(), 'not the replayed restoration: ' + name
                assert sha(data) == record['postimage'], 'restoration postimage hash: ' + name
                mode = '100755' if p.stat().st_mode & 0o111 else '100644'
                assert mode == record['mode'], 'restoration mode: ' + name
            for name, digest in self.receipt['evidence_sha256'].items():
                assert sha((self.root / name).read_bytes()) == digest, 'restoration evidence: ' + name
        for name, donor_path in self.receipt['unchanged_donor_sources'].items():
            data = subprocess.check_output(['git', 'show', self.receipt['donor'] + ':' + donor_path],
                                           cwd=self.root)
            assert data == (self.root / name).read_bytes(), 'changed repaired donor glue/assembly: ' + name
        print('PASS: LZ4 1.11.1 ARM64 restoration replay, current sources/modes and evidence;',
              len(self.preimages), 'explicit historical preimages;', len(self.additions), 'additions.')


if __name__ == '__main__':
    Overlay(Path(__file__).resolve().parents[4]).verify_current()
