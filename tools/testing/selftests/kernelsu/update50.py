#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Closed KSU +50 overlay; legacy tests replay on copies, never live sources."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASE = 'Documentation/dev-tools/kernelsu-updates/v3.3.1+50'
PIN = 'ae63c92098d94bdad1696c74a3ad2e96692118bf'
SEAL = 'f6d5887c6352e7f5e538cdfa0bac0f6dc130da182abb6ed60e36d09a2060c940'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(root):
    root = Path(root)
    if (root / 'Documentation/filesystems/nomount-update-23.json').exists():
        sys.path.insert(0, str(root / 'tools/testing/selftests/nomount'))
        import update23
        with update23.reviewed_base(root) as predecessor:
            return validate(predecessor)
    raw = (root / (BASE + '.json')).read_bytes()
    assert sha(raw) == SEAL, 'KSU +50 receipt changed without review'
    m = json.loads(raw)
    assert m['commit'] == PIN and m['tag'] == 'v3.3.1+50'
    manifest = json.loads((root / 'drivers/kernelsu/UPSTREAM.json').read_text())
    assert manifest['commit'] == PIN and manifest['tag'] == m['tag']
    assert manifest['repository'] == 'https://github.com/backslashxx/KernelSU'
    assert len(manifest['git_blob_sha1']) == 104
    for name, blob in manifest['git_blob_sha1'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        f = root / 'drivers/kernelsu' / name
        assert f.is_file() and not f.is_symlink(), name
        data = f.read_bytes()
        if name in manifest['local_sha256']:
            assert sha(data) == manifest['local_sha256'][name], name
        else:
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == blob, name
    paths = [r['path'] for r in m['changes']]
    assert len(paths) == len(set(paths))
    for r in m['changes']:
        name = r['path']
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert name.startswith('drivers/kernelsu/') or name in {
            'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig',
            'tools/testing/selftests/kernelsu/test_integration.py',
            'tools/testing/selftests/kernelsu/test_finasu.py',
            'tools/testing/selftests/kernelsu/test_update.py',
            'tools/testing/selftests/susfs/test_integration.py',
            'tools/testing/selftests/susfs/test_provenance_overlays.py',
            'tools/testing/selftests/fs_backport/test_f2fs_sysfs.py',
            'tools/testing/selftests/bbr3/test_provenance.py',
        }
        f = root / name
        assert (sha(f.read_bytes()) if f.exists() else None) == r['after_sha256'], name
    for name, digest in {**m['artifact_sha256'], **m['preserved_sha256']}.items():
        assert sha((root / name).read_bytes()) == digest, name
    patch = root / m['patch']
    assert m['patch'] == BASE + '.diff' and sha(patch.read_bytes()) == m['patch_sha256']
    make = (root / 'drivers/kernelsu/Makefile').read_text()
    assert 'CFLAGS_ksu.o += -DKSU_VERSION=32730\n' in make
    dispatch = (root / 'drivers/kernelsu/supercall/dispatch.c').read_text()
    assert dispatch.count('v3.3.1+50') == 2
    print('PASS: KSU +50 exact pin,104 blobs/overrides, version32730, closed overlay/config/artifact seals', flush=True)
    return m


@contextlib.contextmanager
def reviewed_base(root):
    """Hardlink read-only fixtures; detach changed paths BEFORE inverse replay."""
    root = Path(root)
    if (root / 'Documentation/filesystems/nomount-update-23.json').exists():
        sys.path.insert(0, str(root / 'tools/testing/selftests/nomount'))
        import update23
        with update23.reviewed_base(root) as predecessor:
            with reviewed_base(predecessor) as older:
                yield older
        return
    m = validate(root)
    with tempfile.TemporaryDirectory(prefix='ksu50-base-') as tmp:
        tree = Path(tmp) / 'tree'
        shutil.copytree(root, tree, copy_function=os.link, symlinks=True,
                        ignore=shutil.ignore_patterns('.git', '.cache', '__pycache__',
                                                     '.venv', 'node_modules', 'out', 'build', '.arena'))
        for r in m['changes']:
            f = tree / r['path']
            if f.exists():
                data = f.read_bytes()
                f.unlink()  # never write through a hardlink into live sources
                f.write_bytes(data)
        patch = (root / m['patch']).read_bytes()
        subprocess.run(['git', 'apply', '--reverse', '--whitespace=nowarn', '-'],
                       cwd=tree, input=patch, check=True)
        for r in m['changes']:
            f = tree / r['path']
            assert (sha(f.read_bytes()) if f.exists() else None) == r['before_sha256'], r['path']
        # Reapply on a small separate tree to prove BOTH endpoints before yielding.
        with tempfile.TemporaryDirectory(prefix='ksu50-forward-') as fd:
            forward = Path(fd)
            for r in m['changes']:
                f = tree / r['path']
                if f.exists():
                    dest = forward / r['path']
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(f.read_bytes())
            subprocess.run(['git', 'apply', '--whitespace=nowarn', '-'], cwd=forward, input=patch, check=True)
            for r in m['changes']:
                f = forward / r['path']
                assert (sha(f.read_bytes()) if f.exists() else None) == r['after_sha256'], r['path']
        (tree / (BASE + '.json')).unlink()  # old checkers see the exact predecessor, not this layer
        print('PASS: +50 reverse/forward replay; historical tests below run on detached pre-update copies', flush=True)
        yield tree


def legacy_main(script):
    """Retain legacy test CLIs, with explicit current-seal + historical replay."""
    root = Path(script).resolve().parents[4]
    if not (root / (BASE + '.json')).exists():
        return
    with reviewed_base(root) as tree:
        args = list(sys.argv[1:])
        if '--source-root' in args:
            i = args.index('--source-root') + 1
            assert Path(args[i]).resolve() == root, 'use original source root for successor replay'
            args[i] = str(tree)
        result = subprocess.run([sys.executable, str(tree / Path(script).resolve().relative_to(root))] + args)
    raise SystemExit(result.returncode)
