#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Ensure the reviewed BPF/SUSFS provenance overlay cannot bypass hook checks."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile

from test_integration import ROOT, check


OVERLAY = 'Documentation/bpf/susfs-compat-overlay.json'
BPF = 'Documentation/bpf/bpf-5.15-upgrade.json'
PATCH = 'Documentation/bpf/susfs-compat-overlay.diff'
HEADER = 'include/linux/sched.h'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path,
                        default=ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig')
    args = parser.parse_args()
    manifest_path = 'Documentation/filesystems/susfs/UPSTREAM.json'
    fina_path = 'Documentation/dev-tools/finasu-manager.json'
    manifest = json.loads((ROOT / manifest_path).read_text())
    fina = json.loads((ROOT / fina_path).read_text())
    paths = set(manifest['postimage_sha256']) | set(fina['postimage_sha256'])
    paths |= {manifest_path, fina_path, OVERLAY, BPF, PATCH,
              'fs/Makefile', 'drivers/kernelsu/Kconfig'}
    phoenix = 'Documentation/dev-tools/phoenix-review/implementation/susfs-syscall-overlay'
    paths |= {phoenix + '.json', phoenix + '.diff'}
    original = {name: (ROOT / name).read_bytes() for name in paths}
    with tempfile.TemporaryDirectory(prefix='susfs-overlay-') as tmp:
        root = Path(tmp)
        for name, data in original.items():
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        config = root / args.config.name
        shutil.copyfile(args.config, config)

        def validate():
            with contextlib.redirect_stdout(io.StringIO()):
                check(root, config, 'full')

        def edit_json(name, change):
            file = root / name
            data = json.loads(file.read_text())
            change(data)
            file.write_text(json.dumps(data))

        def append(name):
            file = root / name
            file.write_bytes(file.read_bytes() + b'\n/* unreviewed change */\n')

        def change_record(data):
            for record in data['source_delta_records']:
                if record['path'] == HEADER:
                    record['after_sha256'] = '0' * 64

        def duplicate_record(data):
            record = next(record for record in data['source_delta_records']
                          if record['path'] == HEADER)
            data['source_delta_records'].append(record.copy())

        cases = [
            ('header tamper', lambda: append(HEADER)),
            ('broken SUSFS preimage', lambda: edit_json(OVERLAY, lambda d:
                d['base_sha256'].update({HEADER: '0' * 64}))),
            ('broken pre-BPF chain', lambda: edit_json(OVERLAY, lambda d:
                d['pre_bpf_sha256'].update({HEADER: '0' * 64}))),
            ('broadened overlay scope', lambda: edit_json(OVERLAY, lambda d:
                d['postimage_sha256'].update({'fs/namespace.c': '0' * 64}))),
            ('patch tamper', lambda: append(PATCH)),
            ('unsafe patch path', lambda: edit_json(OVERLAY, lambda d:
                d.update(patch='../../outside.diff'))),
            ('missing overlay', lambda: (root / OVERLAY).unlink()),
            ('missing BPF manifest', lambda: (root / BPF).unlink()),
            ('duplicate BPF record', lambda: edit_json(BPF, duplicate_record)),
            ('changed BPF postimage', lambda: edit_json(BPF, change_record)),
            ('unrelated SUSFS hook tamper', lambda: append('fs/namespace.c')),
            ('FinaSU dispatch tamper', lambda: append('drivers/kernelsu/supercall/dispatch.c')),
            ('wrong reference revision', lambda: edit_json(OVERLAY, lambda d:
                d.update(bpf_reference_commit='0' * 40))),
        ]
        cases += [
            ('missing Phoenix overlay', lambda: (root / (phoenix + '.json')).unlink()),
            ('Phoenix patch tamper', lambda: append(phoenix + '.diff')),
            ('Phoenix preimage tamper', lambda: edit_json(phoenix + '.json', lambda d:
                d['base_sha256'].update({'fs/namei.c': '0' * 64}))),
            ('Phoenix scope broadening', lambda: edit_json(phoenix + '.json', lambda d:
                d['postimage_sha256'].update({'fs/susfs.c': '0' * 64}))),
            ('unsafe Phoenix patch', lambda: edit_json(phoenix + '.json', lambda d:
                d.update(patch='../../outside.diff'))),
        ]
        validate()
        for name, mutate in cases:
            mutate()
            try:
                validate()
            except (ValueError, KeyError, OSError):
                print('PASS: rejected ' + name)
            else:
                raise AssertionError('provenance check accepted ' + name)
            for path, data in original.items():
                (root / path).write_bytes(data)
            validate()
    print('PASS: reviewed overlay and all 18 provenance negative controls')


if __name__ == '__main__':
    main()
