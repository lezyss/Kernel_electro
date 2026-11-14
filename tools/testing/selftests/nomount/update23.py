#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Closed NoMount API23 update; replay predecessor seals on detached copies."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASE='Documentation/filesystems/nomount-update-23'
PIN='5e9feb6f3fce42423f56b37e344052c59ec16b66'
SEAL='7d123b899e054d178b9dde4f09dc9e3e285eb284297b88f7d0224ac74c6be189'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(root):
    root=Path(root)
    raw=(root/(BASE+'.json')).read_bytes()
    assert sha(raw)==SEAL, 'NoMount23 receipt changed without review'
    m=json.loads(raw)
    assert m['commit']==PIN and m['branch']=='dev' and m['api_base_version']=='23'
    d=json.loads((root/'fs/nomount/UPSTREAM.json').read_text())
    assert d['commit']==PIN and d['repository']=='https://github.com/maxsteeel/nomount'
    assert d['branch']=='dev'
    assert set(d['upstream_files'])=={'Kconfig','Makefile','nomount.c','nomount.h','LICENSE'}
    assert set(d['local_sha256'])=={'Kconfig','Makefile'}
    for name,spec in d['upstream_files'].items():
        p=root/'fs/nomount'/name
        assert p.is_file() and not p.is_symlink(),name
        data=p.read_bytes()
        if name in d['local_sha256']:
            assert sha(data)==d['local_sha256'][name],name
        else:
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==spec['git_blob'],name
    paths=set()
    for r in m['changes']:
        name=r['path'];assert name not in paths;paths.add(name)
        assert name.startswith('fs/nomount/') or name in {
            'tools/testing/selftests/nomount/test_integration.py',
            'tools/testing/selftests/kernelsu/update50.py',
            'tools/testing/selftests/kernelsu/test_update50.py',
            'tools/testing/selftests/nomount/README',
            'Documentation/filesystems/nomount-integration.md'}
        assert '..' not in Path(name).parts and not Path(name).is_absolute()
        assert sha((root/name).read_bytes())==r['after_sha256'],name
    for name,h in {**m['artifact_sha256'],**m['preserved_sha256']}.items():
        assert sha((root/name).read_bytes())==h,name
    assert m['patch']==BASE+'.diff'
    assert sha((root/m['patch']).read_bytes())==m['patch_sha256']
    make=(root/'fs/nomount/Makefile').read_text()
    assert '-fno-stack-protector' not in make and '-O3' not in make
    assert 'default n' in (root/'fs/nomount/Kconfig').read_text()
    assert '#define NOMOUNT_BASE_VERSION "23"' in (root/'fs/nomount/nomount.h').read_text()
    print('PASS: NoMount API23 dev pin,5 upstream blobs/adaptations, closed source/config/hardening seals',flush=True)
    return m


@contextlib.contextmanager
def reviewed_base(root):
    root=Path(root);m=validate(root)
    with tempfile.TemporaryDirectory(prefix='nomount23-base-') as tmp:
        tree=Path(tmp)/'tree'
        shutil.copytree(root,tree,copy_function=os.link,symlinks=True,
                        ignore=shutil.ignore_patterns('.git','.cache','__pycache__','.venv','node_modules','out','build','.arena'))
        for r in m['changes']:
            p=tree/r['path'];data=p.read_bytes();p.unlink();p.write_bytes(data)
        patch=(root/m['patch']).read_bytes()
        subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=tree,input=patch,check=True)
        for r in m['changes']:assert sha((tree/r['path']).read_bytes())==r['before_sha256'],r['path']
        with tempfile.TemporaryDirectory(prefix='nomount23-forward-') as ft:
            forward=Path(ft)
            for r in m['changes']:
                p=forward/r['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((tree/r['path']).read_bytes())
            subprocess.run(['git','apply','--whitespace=nowarn','-'],cwd=forward,input=patch,check=True)
            for r in m['changes']:assert sha((forward/r['path']).read_bytes())==r['after_sha256'],r['path']
        (tree/(BASE+'.json')).unlink()
        print('PASS: NoMount23 reverse/forward endpoints; predecessor checks run on detached copies',flush=True)
        yield tree


def legacy_main(script):
    root=Path(script).resolve().parents[4]
    if not (root/(BASE+'.json')).exists():return
    with reviewed_base(root) as tree:
        args=list(sys.argv[1:])
        if '--source-root' in args:
            i=args.index('--source-root')+1;assert Path(args[i]).resolve()==root;args[i]=str(tree)
        run=subprocess.run([sys.executable,str(tree/Path(script).resolve().relative_to(root))]+args)
    raise SystemExit(run.returncode)
