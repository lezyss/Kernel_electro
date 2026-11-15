#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Current +50 host checks plus immutable historical replay; not a boot test."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile

from update50 import validate, reviewed_base
from test_update import extract

ROOT = Path(__file__).resolve().parents[4]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def current_models(negatives):
    d = ROOT / 'drivers/kernelsu'
    selected = (d / 'feature/sucompat.c').read_text().split('#else /* upstream v3.3.1+50 front end */')[0]
    # SUCOMPAT_HOOK_TYPE definitions need extraction before the host replacement.
    bodies = '\n'.join(extract(selected, name) for name in [
        'is_su_allowed', 'ksu_sucompat_user_common', 'ksu_handle_sys_execve',
        'ksu_handle_sys_execveat', 'ksu_susfs_post_execve'])
    hide = (d / 'feature/selinux_hide.c').read_text()
    bodies += '\n' + '\n'.join(extract(hide, name) for name in [
        'ksu_hide_setprocattr_inline', 'ksu_hide_setxattr_inline'])
    source = Path(__file__).with_name('update50_model.c').read_text()
    cases = {'baseline': bodies}
    if negatives:
        cases['allowlist-bypass'] = bodies.replace('if (!ksu_is_allow_uid_for_current(current_uid().val))', 'if (false)')
        cases['early-fd'] = bodies.replace('su_session && !retval', 'su_session')
        cases['lost-session'] = bodies.replace('su_session = true;', 'su_session = false;')
    with tempfile.TemporaryDirectory(prefix='ksu50-model-') as tmp:
        for name, body in cases.items():
            assert name == 'baseline' or body != bodies, name
            p = Path(tmp) / (name + '.c'); exe = p.with_suffix('')
            p.write_text(source.replace('/* ACTUAL */', body))
            subprocess.run(['gcc', '-std=gnu11', '-O1', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-Wno-unused-function', '-fsanitize=undefined',
                            '-fno-sanitize-recover=all', str(p), '-o', str(exe)], check=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            if name == 'baseline':
                assert run.returncode == 0, run.stderr
                print(run.stdout.strip(), flush=True)
            else:
                assert run.returncode < 0 and 'Assertion' in run.stderr, (name,run.stderr)
                print('PASS: compiled current semantic mutant rejected: '+name, flush=True)
    hooks = (d / 'hook/syscall_table_hook_arm64.c').read_text()
    assert hooks.count('return ksu_susfs_post_execve(su_session, retval);') == 8
    assert hooks.count('bool su_session = ksu_handle_sys_execve') == 8
    assert 'ksyscall_execve_ksud(' not in selected
    assert 'ksu_adb_root_execve_user' not in selected and 'ksu_preinit_user_execve_hook' not in selected
    compat = (d / 'kernel_compat.h').read_text()
    assert '#define audit_context()' not in compat and '#define __poll_t' not in compat
    assert not re.search(r'__weak long strncpy_from_user_nofault\(', compat)
    assert 'hook/syscall_table_mirror_arm64.c' in (d/'ksu.c').read_text()
    assert not (d/'hook/syscall_table_mirror.c').exists()
    print('PASS: all8 native/compat exec wrappers, unified hook APIs and native helper bindings', flush=True)
    # Execute CURRENT (not replayed) manager trust/metadata and SUSFS models.
    from test_finasu import host_tests
    host_tests(ROOT, 'gcc -fsanitize=undefined -fno-sanitize-recover=all', negatives)
    sys.path.insert(0, str(ROOT/'tools/testing/selftests/susfs'))
    import importlib.util
    spec = importlib.util.spec_from_file_location('current_susfs', ROOT/'tools/testing/selftests/susfs/test_integration.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.models(ROOT, 'gcc -Wno-address -fsanitize=undefined -fno-sanitize-recover=all', None)


def helper_models(negatives):
    from test_update import source
    with tempfile.TemporaryDirectory(prefix='ksu50-helpers-') as tmp:
        for mutant in [None] + (['fault-status','address-limit','fallback','zero-size'] if negatives else []):
            p=Path(tmp)/(str(mutant)+'.c');exe=p.with_suffix('')
            p.write_text(source(mutant))  # reads CURRENT compat/vmap helpers
            subprocess.run(['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',
                            '-Wno-misleading-indentation','-fsanitize=undefined',
                            '-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
            run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=5)
            if mutant:
                assert run.returncode < 0 and 'Assertion' in run.stderr, run.stderr
                print('PASS: current helper semantic mutant rejected: '+mutant,flush=True)
            else:
                assert run.returncode==0,run.stderr
                print('CURRENT '+run.stdout.strip(),flush=True)


def seal_negatives():
    global ROOT
    if (ROOT/'Documentation/filesystems/nomount-update-23.json').exists():
        sys.path.insert(0,str(ROOT/'tools/testing/selftests/nomount'))
        import update23
        live=ROOT
        with update23.reviewed_base(live) as predecessor:
            try:
                ROOT=predecessor
                return seal_negatives()
            finally:
                ROOT=live
    from update50 import BASE
    m=json.loads((ROOT/(BASE+'.json')).read_text())
    names=set(m['artifact_sha256'])|set(m['preserved_sha256'])
    names|={r['path'] for r in m['changes'] if r['after_sha256'] is not None}
    names|={BASE+'.json',BASE+'.diff','drivers/kernelsu/UPSTREAM.json'}
    names|={'drivers/kernelsu/'+n for n in json.loads((ROOT/'drivers/kernelsu/UPSTREAM.json').read_text())['git_blob_sha1']}
    with tempfile.TemporaryDirectory(prefix='ksu50-negatives-') as tmp:
        tree=Path(tmp)
        for name in names:
            p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        validate(tree)  # prove the unmodified fixture passes before mutations
        cases={
            'pin':('drivers/kernelsu/UPSTREAM.json',lambda x:x.replace('ae63c92098d94bdad1696c74a3ad2e96692118bf','0'*40)),
            'version':('drivers/kernelsu/Makefile',lambda x:x.replace('32730','99999')),
            'exec-source':('drivers/kernelsu/feature/sucompat.c',lambda x:x+'\n/* unreviewed */\n'),
            'config':('arch/arm64/configs/vendor/xiaomi/miatoll_defconfig',lambda x:x.replace('CONFIG_KSU_ENABLE_FULL_UID_CHECKS=y','')),
            'patch':(BASE+'.diff',lambda x:x+'\n# unreviewed\n'),
            'receipt-reseal':(BASE+'.json',lambda x:x.replace('32730','99999')),
            'unsafe-patch':(BASE+'.json',lambda x:x.replace(BASE+'.diff','../../outside.diff')),
        }
        for name,(path,change) in cases.items():
            f=tree/path;original=f.read_text();new=change(original);assert new!=original;f.write_text(new)
            try:
                with contextlib.redirect_stdout(io.StringIO()):validate(tree)
            except AssertionError:
                print('PASS: current closed-layer tamper rejected: '+name,flush=True)
            else:
                raise AssertionError('accepted '+name)
            finally:
                f.write_text(original)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test-negatives', action='store_true')
    p.add_argument('--historical', action='store_true', help='also run predecessor suites on verified inverse replay')
    p.add_argument('--config', type=Path, default=ROOT/'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig')
    args=p.parse_args()
    validate(ROOT)
    config=args.config.read_text().splitlines()
    for option in ['CONFIG_KSU=y','CONFIG_KSU_TAMPER_SYSCALL_TABLE=y',
                   'CONFIG_KSU_LSM_SECURITY_HOOKS=y','CONFIG_KSU_ENABLE_FULL_UID_CHECKS=y',
                   'CONFIG_KSU_FEATURE_ADBROOT=y','CONFIG_KSU_SUSFS=y',
                   'CONFIG_KSU_SUSFS_SUS_PATH=y','CONFIG_KSU_SUSFS_OPEN_REDIRECT=y',
                   'CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y','CONFIG_NOMOUNT=y',
                   'CONFIG_COMPAT=y','CONFIG_SECURITY_SELINUX=y',
                   'CONFIG_DEFAULT_TCP_CONG="bbr3"']:
        assert option in config, option
    for option in ['CONFIG_KSU_FEATURE_SULOG=y','CONFIG_KSU_HACK_ARM64_BRANCH_LINK=y',
                   'CONFIG_KSU_KPROBES_KSUD=y','CONFIG_KSU_SHELL_HAS_SU_ALWAYS=y',
                   'CONFIG_KSU_DISABLE_32BIT_HOOKS=y','CONFIG_KSU_DEBUG=y']:
        assert option not in config, option
    if args.config.name=='.config':
        assert 'CONFIG_DEFAULT_NET_SCH="fq"' in config
    print('PASS: current selected KSU/SUSFS/NoMount/compat profile; no obsolete sulog selector',flush=True)
    current_models(args.self_test_negatives)
    helper_models(args.self_test_negatives)
    if args.self_test_negatives:
        seal_negatives()
    if args.historical:
        with reviewed_base(ROOT) as tree:
            suites=[['kernelsu/test_integration.py'],
                    ['kernelsu/test_finasu.py','--host-tests','--cc','gcc','--negative-tests'],
                    ['kernelsu/test_update.py','--self-test-negatives'],
                    ['susfs/test_integration.py','--host-tests','--cc','gcc -Wno-address'],
                    ['susfs/test_provenance_overlays.py'],
                    ['nomount/test_integration.py']]
            for script,*flags in suites:
                subprocess.run([sys.executable,str(tree/'tools/testing/selftests'/script)]+flags,check=True)
    print('LIMITS: host models/config/replay only; no exact-AOSP ARM64 image/link, root/manager/device proof.')


if __name__ == '__main__':
    main()
