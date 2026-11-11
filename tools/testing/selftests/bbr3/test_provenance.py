#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Verify the additive BBRv3 source delta without rewriting historical BPF seals."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def check_base(root):
    ROOT = root
    m = json.loads((ROOT / 'Documentation/networking/bbr3-validation.json').read_text())
    patch = ROOT / m['source_delta_patch']['path']
    assert sha(patch) == m['source_delta_patch']['sha256'], 'delta patch drift'
    records = m['source_delta_records']
    assert len({r['path'] for r in records}) == len(records)
    for r in records:
        assert sha(ROOT / r['path']) == r['after_sha256'], r['path']
    for path, digest in m['protected_source_sha256'].items():
        assert sha(ROOT / path) == digest, 'protected source drift: ' + path
    bpf = json.loads((ROOT / 'Documentation/bpf/bpf-5.15-upgrade.json').read_text())
    old = {r['path']: r['after_sha256'] for r in bpf['source_delta_records']}
    overlap = {r['path'] for r in records if r['path'] in old}
    assert overlap == {'include/net/tcp.h', 'net/ipv4/bpf_tcp_ca.c', 'net/ipv4/tcp.c'}
    for r in records:
        if r['path'] in overlap:
            assert r['before_sha256'] == old[r['path']], 'BPF chain discontinuity'
    # The only tcp.c edit is exporting the existing min-TSO global for
    # modular BBRv3. Prove the rest, including 16 MiB caps, is byte-identical.
    tcp = (ROOT / 'net/ipv4/tcp.c').read_bytes()
    export = b'EXPORT_SYMBOL_GPL(sysctl_tcp_min_tso_segs);\n'
    assert tcp.count(export) == 1
    assert hashlib.sha256(tcp.replace(export, b'', 1)).hexdigest() == m['tcp_c_before_export_sha256']
    # Real zero-context reverse + forward replay, comparing BOTH endpoints.
    with tempfile.TemporaryDirectory(prefix='bbr3-replay-') as tmp:
        root = Path(tmp)
        for r in records:
            dst = root / r['path']
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / r['path'], dst)
        subprocess.run(['git', '-C', tmp, 'apply', '--unidiff-zero', '--reverse',
                        str(patch)], check=True)
        for r in records:
            assert sha(root / r['path']) == r['before_sha256'], r['path']
        subprocess.run(['git', '-C', tmp, 'apply', '--unidiff-zero', str(patch)],
                       check=True)
        for r in records:
            assert sha(root / r['path']) == r['after_sha256'], r['path']
    print(f"PASS: {len(records)} BBRv3 source endpoints, reverse/forward replay; "
          '3 historical BPF chains intact; protected BBR/BBRplus/TCP caps unchanged')


def main():
    overlay = ROOT / 'Documentation/networking/bbr3-edt-validation.json'
    if not overlay.exists():
        check_base(ROOT)
        return
    edt = json.loads(overlay.read_text())
    patch = ROOT / edt['patch']['path']
    assert sha(patch) == edt['patch']['sha256'], 'EDT patch drift'
    for r in edt['source_records']:
        assert sha(ROOT / r['path']) == r['after_sha256'], r['path']
    for path, digest in edt['protected_sha256'].items():
        assert sha(ROOT / path) == digest, 'EDT protected source drift: ' + path
    old = json.loads((ROOT / 'Documentation/networking/bbr3-validation.json').read_text())
    paths = {r['path'] for r in old['source_delta_records']} | set(old['protected_source_sha256'])
    paths |= {r['path'] for r in edt['source_records']}
    paths |= {'Documentation/networking/bbr3-validation.json',
              old['source_delta_patch']['path'], 'Documentation/bpf/bpf-5.15-upgrade.json'}
    with tempfile.TemporaryDirectory(prefix='bbr3-edt-chain-') as td:
        root = Path(td)
        for path in paths:
            dst = root / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, dst)
        subprocess.run(['git', '-C', td, 'apply', '--reverse', str(patch)], check=True)
        for r in edt['source_records']:
            assert sha(root / r['path']) == r['before_sha256'], r['path']
        # SUSFS/KSU configuration followups predate EDT and changed only the
        # config endpoint of the historical BBR receipt. Verify its exact
        # original endpoint on copies; never overwrite the working defconfig.
        cfg = root / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig'
        current_cfg = cfg.read_bytes()
        historic = edt['historical_config_prerequisite']
        cfg.write_text(historic['content'])
        assert sha(cfg) == historic['sha256']
        check_base(root)
        cfg.write_bytes(current_cfg)
        subprocess.run(['git', '-C', td, 'apply', str(patch)], check=True)
        for r in edt['source_records']:
            assert sha(root / r['path']) == r['after_sha256'], r['path']
    print('PASS: EDT overlay reverse/forward endpoints and immutable historical BBRv3/BPF chain')


if __name__ == '__main__':
    main()
