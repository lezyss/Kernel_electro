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


def main():
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


if __name__ == '__main__':
    main()
