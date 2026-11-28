#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Negative controls for the explicit restoration replay, not runtime tests."""
from pathlib import Path
import shutil
import tempfile

from lz4_overlay import DOC, Overlay

ROOT = Path(__file__).resolve().parents[4]


def rejected(root, marker):
    try:
        Overlay(root).verify_current()
    except AssertionError as error:
        assert marker in str(error), str(error)
    else:
        raise AssertionError('corruption was accepted: ' + marker)


def main():
    overlay = Overlay(ROOT)
    overlay.verify_current()
    with tempfile.TemporaryDirectory(prefix='lz4-overlay-negative-') as tmp:
        tmp = Path(tmp)
        shutil.copytree(ROOT / DOC, tmp / DOC)
        for name in overlay.paths:
            p = tmp / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, p)
            shutil.copymode(ROOT / name, p)
        name = 'lib/lz4/lz4.c'
        p = tmp / name
        data = p.read_bytes()
        p.write_bytes(data + b'\n/* unreviewed change */\n')
        rejected(tmp, 'not the replayed restoration')
        p.write_bytes(data)
        p = tmp / DOC / 'preimages' / (name + '.preimage')
        data = p.read_bytes()
        p.write_bytes(data + b'\n')
        rejected(tmp, 'restoration preimage hash')
        p.write_bytes(data)
        p = tmp / DOC / 'restoration.patch'
        data = p.read_bytes()
        p.write_bytes(data + b'\n')
        rejected(tmp, 'restoration patch hash')
        p.write_bytes(data)
        name = next(iter(overlay.receipt['evidence_sha256']))
        p = tmp / name
        p.write_bytes(p.read_bytes() + b'\n')
        rejected(tmp, 'restoration evidence')
    print('PASS: four restoration negative controls (current source, preimage, patch, evidence) rejected')


if __name__ == '__main__':
    main()
