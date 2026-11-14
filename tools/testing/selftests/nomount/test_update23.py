#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Current NoMount23 function models + closed predecessor replay, not VFS stress."""
import argparse
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from test_integration import function
from update23 import validate, reviewed_base
import contextlib
import io
import json

ROOT=Path(__file__).resolve().parents[4]
resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def current_models(negatives):
    h=(ROOT/'fs/nomount/nomount.h').read_text();s=(ROOT/'fs/nomount/nomount.c').read_text()
    bodies='\n'.join(function(h,n) for n in ['nm_entries','nm_child_slots_for','nm_child_bucket',
        'nm_is_virtual_pos','nm_pack_pos','nm_unpack_frag','nm_unpack_pos',
        'nm_uid_bloom_set','nm_uid_bloom_test','nm_uid_add','nm_uid_del'])
    bodies+='\n'+'\n'.join(function(s,n) for n in ['nm_key_preparse','nm_is_uid_blocked',
        'nm_rules_overlap','nm_select_rule','nm_child_matches','nm_find_leaf_in_dir',
        'nm_alloc_child_array','nm_rebuild_children'])
    cases={'baseline':bodies}
    if negatives:
        cases.update({
            'no-capability':bodies.replace('if (!capable(CAP_SYS_ADMIN)) return -EPERM;',''),
            'wrong-compat-cookie':bodies.replace('(NM_SIG_16 << 16) | (id & 0xFFFF)','(NM_SIG_16 << 48) | (id & 0xFFFF)'),
            'no-uid-bloom':bodies.replace('nm_uid_bloom_set(new_arr, target);',''),
            'name-collision':bodies.replace('!memcmp(child_name, name, len)','true'),
            'lost-fallback':bodies.replace('return fallback;','(void)fallback; return NULL;'),
        })
    model=Path(__file__).with_name('model23.c').read_text()
    with tempfile.TemporaryDirectory(prefix='nomount23-model-') as tmp:
        for name,body in cases.items():
            assert name=='baseline' or body!=bodies,name
            p=Path(tmp)/(name+'.c');exe=p.with_suffix('');p.write_text(model.replace('/* PRODUCTION */',body))
            subprocess.run(['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',
                            '-Wno-unused-parameter','-Wno-unused-function','-Wno-sign-compare',
                            '-Wno-misleading-indentation','-fsanitize=undefined',
                            '-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
            run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
            if name=='baseline':
                assert run.returncode==0,run.stdout+run.stderr
                print(run.stdout.strip(),flush=True)
            else:
                assert run.returncode<0 and 'Assertion' in run.stderr,(name,run.stderr)
                print('PASS: compiled NoMount23 semantic mutant rejected: '+name,flush=True)


def io_models(negatives):
    s=(ROOT/'fs/nomount/nomount.c').read_text()
    body='\n'.join(function(s,n) for n in ['nm_leaf_put','nm_destroy_virtual_inode',
        'nm_open','nm_release','nm_llseek','nm_xattr_get','nm_xattr__get','nm_xattr_set',
        'nm_reclaim','nm_retire_array_locked','nm_retire_leaf_locked'])
    cases={'baseline':body}
    if negatives:
        cases.update({
            'borrowed-fput':body.replace('real_file != READ_ONCE(info->r_file)','true'),
            'pre-RCU-free':body.replace('synchronize_rcu();',''),
            'xattr-bypass':body.replace('return vfs_setxattr(IDMAP_PATH(info->r_path) info->r_path.dentry, full_name, buffer, size, flags);','return 0;'),
            'shared-seek':body.replace('pos = file->f_pos + offset','pos = real_file->f_pos + offset'),
        })
    model=Path(__file__).with_name('io_model23.c').read_text()
    with tempfile.TemporaryDirectory(prefix='nomount23-io-') as tmp:
        for name,code in cases.items():
            assert name=='baseline' or code!=body,name
            p=Path(tmp)/(name+'.c');exe=p.with_suffix('');p.write_text(model.replace('/* ACTUAL */',code))
            subprocess.run(['gcc','-std=gnu11','-O1','-Wall','-Wextra','-Werror',
                            '-Wno-unused-parameter','-Wno-unused-function',
                            '-fsanitize=undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            if name=='baseline':
                assert run.returncode==0,run.stdout+run.stderr
                print(run.stdout.strip(),flush=True)
            else:
                assert run.returncode<0 and 'Assertion' in run.stderr,(name,run.stderr)
                print('PASS: compiled NoMount23 IO semantic mutant rejected: '+name,flush=True)


def seal_negatives():
    from update23 import BASE
    m=json.loads((ROOT/(BASE+'.json')).read_text())
    names=set(m['artifact_sha256'])|set(m['preserved_sha256'])
    names|={r['path'] for r in m['changes']}
    names|={BASE+'.json',BASE+'.diff'}
    names|={'fs/nomount/'+n for n in ['UPSTREAM.json','nomount.c','nomount.h','Kconfig','Makefile','LICENSE']}
    with tempfile.TemporaryDirectory(prefix='nomount23-tamper-') as tmp:
        tree=Path(tmp)
        for name in names:
            p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        with contextlib.redirect_stdout(io.StringIO()):validate(tree)
        cases={
            'pin':'fs/nomount/UPSTREAM.json',
            'source':'fs/nomount/nomount.c',
            'hardening':'fs/nomount/Makefile',
            'config':'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig',
            'preserved-KSU':'drivers/kernelsu/feature/sucompat.c',
            'current-model':'tools/testing/selftests/nomount/model23.c',
            'receipt':BASE+'.json',
            'patch':BASE+'.diff',
        }
        for name,path in cases.items():
            p=tree/path;original=p.read_bytes();p.write_bytes(original+b'\n ')
            try:
                with contextlib.redirect_stdout(io.StringIO()):validate(tree)
            except AssertionError:
                print('PASS: NoMount23 closed-layer tamper rejected: '+name,flush=True)
            else:
                raise AssertionError('accepted '+name)
            finally:
                p.write_bytes(original)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test-negatives',action='store_true')
    p.add_argument('--historical',action='store_true')
    args=p.parse_args();validate(ROOT);current_models(args.self_test_negatives);io_models(args.self_test_negatives)
    if args.self_test_negatives:
        seal_negatives()
    if args.historical:
        with reviewed_base(ROOT) as tree:
            subprocess.run([sys.executable,str(tree/'tools/testing/selftests/nomount/test_integration.py'),
                            '--host-tests','--cc','gcc -fsanitize=undefined -fno-sanitize-recover=all'],check=True)
    print('LIMITS: host mocks/replay only; no target link/boot, actual VFS/xattr/RCU stress or userspace install.')


if __name__=='__main__':
    main()
