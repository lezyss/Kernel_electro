#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Script contract fixtures. Payloads are synthetic, NEVER bootable images."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile
import zipfile

from shims import ROOT

TOOLS = ('clang', 'clang++', 'ld.lld', 'llvm-ar', 'llvm-nm', 'llvm-strip',
         'llvm-objcopy', 'llvm-objdump', 'llvm-readelf')


def run(root, name, env, ok=True):
    process_env = {k: v for k, v in {**os.environ, **env}.items() if v is not None}
    p = subprocess.run(['bash', str(root / 'scripts/ci' / name)],
                       cwd=root, env=process_env, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert (p.returncode == 0) == ok, p.stdout
    return p.stdout


def tests(root, anykernel):
    scripts = root / 'scripts/ci'
    scripts.mkdir(parents=True)
    for name in ('build-kernel.sh', 'package-anykernel.sh', 'anykernel.sh', 'neutron-toolchain.py'):
        shutil.copyfile(ROOT / 'scripts/ci' / name, scripts / name)
    (root / 'scripts/config').write_bytes((ROOT / 'scripts/config').read_bytes())
    (root / 'scripts/config').chmod(0o755)
    config = root / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig'
    config.parent.mkdir(parents=True)
    config.write_text('CONFIG_ARCH_ATOLL=y\nCONFIG_LLVM_POLLY=y\n')
    # A disposable repository provides truthful fixture metadata, not kernel proof.
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c',
                    'user.email=fixture@example.invalid', 'commit', '--allow-empty',
                    '-qm', 'Synthetic script fixture'], check=True)
    toolchain = root / 'toolchain'
    (toolchain / 'bin').mkdir(parents=True)
    for name in TOOLS:
        p = toolchain / 'bin' / name
        p.write_text('#!/bin/sh\n'
                     'case " $* " in *" -polly "*)\n'
                     '  test "${FAKE_POLLY_UNAVAILABLE:-0}" = 0 || exit 1\n'
                     '  if test "${FAKE_POLLY_NO_PASS:-0}" = 0; then\n'
                     '    echo "Running pass: polly::PollyFunctionPass on synthetic_fixture" >&2\n'
                     '  fi ;;\nesac\n'
                     'echo "Neutron clang version 24.0.0git (SYNTHETIC FIXTURE)"\n')
        p.chmod(0o755)
    hostbin = root / 'host-llvm'
    hostbin.mkdir()
    for name in ('clang', 'clang++', 'ld.lld'):
        p = hostbin / name
        p.write_text('#!/bin/sh\necho "Native fixture clang version 24.0.0"\n')
        p.chmod(0o755)
    fakebin = root / 'fakebin'
    fakebin.mkdir()
    # Synthetic uncompressed tar + zstd stub: tests verifier/build contracts,
    # NOT a downloaded Neutron toolchain or its real decompression.
    for name, body in [('zstd', 'cat "$2"'),
                       ('getconf', 'echo "glibc 2.43"')]:
        p = fakebin / name
        p.write_text('#!/bin/sh\n' + body + '\n')
        p.chmod(0o755)
    archive = toolchain / '.neutron-archive.tar.zst'
    with tarfile.open(archive, 'w') as tar:
        tar.add(toolchain / 'bin', arcname='bin')
    lock = json.loads((ROOT / 'scripts/ci/neutron.lock.json').read_text())
    lock['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    (scripts / 'neutron.lock.json').write_text(json.dumps(lock))
    p = fakebin / 'make'
    p.write_text('''#!/usr/bin/env python3
import json, pathlib, sys
with open('make-calls.jsonl', 'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
out=pathlib.Path('out');out.mkdir(exist_ok=True)
if 'vendor/xiaomi/miatoll_defconfig' in sys.argv:
 (out/'.config').write_text('CONFIG_ARCH_ATOLL=y\\nCONFIG_LLVM_POLLY=y\\n# CONFIG_SCSI_MQ_DEFAULT is not set\\n# CONFIG_MQ_IOSCHED_DEADLINE is not set\\n' + ''.join('CONFIG_'+x+'=y\\n' for x in ('ARM64','KERNEL_MODE_NEON','LZ4_DECOMPRESS','LZ4_ARM64_ACCEL','SCSI_UFSHCD','SCSI_UFS_QCOM','SCSI_UFS_CRYPTO','SCSI_UFS_CRYPTO_QTI','BLK_INLINE_ENCRYPTION','BLK_INLINE_ENCRYPTION_FALLBACK','IOSCHED_CFQ','DEFAULT_CFQ') if x != __import__('os').environ.get('DROP_OPTION')))
if 'olddefconfig' in sys.argv and __import__('os').environ.get('DROP_MQ_OPTION'):
 p=out/'.config'; key='CONFIG_'+__import__('os').environ['DROP_MQ_OPTION']; p.write_text(p.read_text().replace(key+'=y', '# '+key+' is not set'))
if 'Image.gz-dtb' in sys.argv:
 for name in ('Image.gz-dtb','Image.gz','dtb.img','dtbo.img'):
  p=out/'arch/arm64/boot'/name;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_bytes(b'SYNTHETIC SCRIPT FIXTURE - NOT BOOTABLE\\n')
 p=out/'include/config/kernel.release';p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text('fixture-not-bootable\\n')
''')
    p.chmod(0o755)
    env = {'TEST_SCSI_MQ': '0', 'ENABLE_POLLY': '0', 'TOOLCHAIN_DIR': str(toolchain), 'HOST_LLVM_BIN': str(hostbin), 'PATH': str(fakebin) + ':' + os.environ['PATH'],
           'DEFCONFIG': 'vendor/xiaomi/miatoll_defconfig', 'JOBS': '2'}
    run(root, 'build-kernel.sh', {**env, 'DEFCONFIG': '../../escape_defconfig'}, False)
    run(root, 'build-kernel.sh', {**env, 'JOBS': '-j8'}, False)
    run(root, 'build-kernel.sh', {**env, 'ENABLE_POLLY': 'yes'}, False)
    run(root, 'build-kernel.sh', {**env, 'TEST_SCSI_MQ': 'yes'}, False)
    run(root, 'build-kernel.sh', env, False)  # missing compiler pin
    (toolchain / 'neutron-install.json').write_text('{}\n')
    run(root, 'build-kernel.sh', env, False)
    (toolchain / 'neutron-install.json').write_text(json.dumps(lock))
    run(root, 'build-kernel.sh', env)
    calls = [json.loads(x) for x in (root / 'make-calls.jsonl').read_text().splitlines()]
    assert len(calls) == 4
    for call in calls:
        assert 'LLVM_IAS=1' in call and 'ARCH=arm64' in call
        for variable in ('CC', 'AS', 'LD', 'AR', 'NM', 'STRIP', 'OBJCOPY',
                         'OBJDUMP', 'READELF'):
            assert any(x.startswith(variable + '=' + str(toolchain / 'bin') + '/') for x in call), call
        assert 'HOSTCC=' + str(hostbin / 'clang') in call
        assert 'HOSTCXX=' + str(hostbin / 'clang++') in call
        assert 'HOSTLDFLAGS=-fuse-ld=' + str(hostbin / 'ld.lld') in call
    assert '# CONFIG_LLVM_POLLY is not set' in (root / 'out/.config').read_text()
    for option in ('ARM64', 'KERNEL_MODE_NEON', 'LZ4_DECOMPRESS', 'LZ4_ARM64_ACCEL'):
        log = run(root, 'build-kernel.sh', {**env, 'DROP_OPTION': option}, False)
        assert 'Required miatoll LZ4 acceleration option lost: CONFIG_' + option in log
    # With no selection, Polly is enabled and proves pipeline scheduling.
    # These remain fake toolchain contracts, not real Polly/ARM64 compilation.
    run(root, 'build-kernel.sh', {**env, 'ENABLE_POLLY': None})
    assert 'CONFIG_LLVM_POLLY=y' in (root / 'out/.config').read_text().splitlines()
    assert 'LLVM Polly: 1' in (root / 'out/build-info.txt').read_text()
    assert 'PollyFunctionPass' in (root / 'out/polly-probe.log').read_text()
    run(root, 'build-kernel.sh', {**env, 'ENABLE_POLLY': '1'})
    assert 'CONFIG_LLVM_POLLY=y' in (root / 'out/.config').read_text().splitlines()
    run(root, 'build-kernel.sh', {**env, 'ENABLE_POLLY': '1', 'FAKE_POLLY_UNAVAILABLE': '1'}, False)
    log = run(root, 'build-kernel.sh', {**env, 'ENABLE_POLLY': '1', 'FAKE_POLLY_NO_PASS': '1'}, False)
    assert 'no Polly pass ran' in log
    # Synthetic storage-mode contracts, not UFS execution or data-integrity tests.
    run(root, 'build-kernel.sh', {**env, 'TEST_SCSI_MQ': None})
    assert '# CONFIG_SCSI_MQ_DEFAULT is not set' in (root / 'out/.config').read_text()
    assert '# CONFIG_MQ_IOSCHED_DEADLINE is not set' in (root / 'out/.config').read_text()
    run(root, 'build-kernel.sh', {**env, 'TEST_SCSI_MQ': '1', 'ENABLE_POLLY': '1'})
    resolved = (root / 'out/.config').read_text().splitlines()
    assert 'CONFIG_SCSI_MQ_DEFAULT=y' in resolved and 'CONFIG_MQ_IOSCHED_DEADLINE=y' in resolved
    assert 'CONFIG_LLVM_POLLY=y' in resolved
    assert 'Experimental SCSI blk-mq: 1' in (root / 'out/build-info.txt').read_text()
    for option in ('SCSI_MQ_DEFAULT', 'MQ_IOSCHED_DEADLINE', 'SCSI_UFSHCD', 'SCSI_UFS_QCOM',
                   'SCSI_UFS_CRYPTO', 'SCSI_UFS_CRYPTO_QTI', 'BLK_INLINE_ENCRYPTION',
                   'BLK_INLINE_ENCRYPTION_FALLBACK', 'IOSCHED_CFQ', 'DEFAULT_CFQ'):
        log = run(root, 'build-kernel.sh', {**env, 'TEST_SCSI_MQ': '1', 'DROP_MQ_OPTION': option}, False)
        assert 'SCSI mq experiment lost required CONFIG_' + option in log
    print('PASS: SCSI mq default-off, opt-in with Polly, invalid selection and ten resolved-config guards')
    # Select the explicit opt-out when testing the no-Polly packager.
    run(root, 'build-kernel.sh', env)
    assert '# CONFIG_LLVM_POLLY is not set' in (root / 'out/.config').read_text()
    print('PASS: synthetic build script flow, LLVM overrides, invalid input/pin rejection; four resolved LZ4 guards; native host LLVM; default-on Polly, explicit on/off and unavailable/no-pass rejection')

    if anykernel:
        env = {'ANYKERNEL_DIR': str(anykernel), 'GITHUB_RUN_NUMBER': 'fixture',
               'DEFCONFIG': 'vendor/xiaomi/miatoll_defconfig'}
        run(root, 'package-anykernel.sh', {**env, 'DEFCONFIG': 'other_defconfig'}, False)
        run(root, 'package-anykernel.sh', {**env, 'ANYKERNEL_DIR': str(root)}, False)
        run(root, 'package-anykernel.sh', env)
        archive, = (root / 'out/flashable').glob('*.zip')
        assert '-neutron-06092026-' in archive.name
        with zipfile.ZipFile(archive) as z:
            assert z.read('Image.gz').startswith(b'SYNTHETIC SCRIPT FIXTURE')
            assert {'dtb', 'dtbo.img', 'anykernel.sh', 'tools/ak3-core.sh',
                    'META-INF/com/google/android/update-binary'} <= set(z.namelist())
            assert not any(x.startswith(('.git/', '.github/', 'modules/')) for x in z.namelist())
            assert '020dfeccf9d7e962a48400fc94d3e451df92eead' in z.read('build-info.txt').decode()
        digest = archive.with_suffix('.zip.sha256').read_text().split()[0]
        assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
        # zip must not retain stale entries from an earlier invocation.
        with zipfile.ZipFile(archive, 'a') as z: z.writestr('STALE-ENTRY', b'stale')
        run(root, 'package-anykernel.sh', env)
        with zipfile.ZipFile(archive) as z: assert 'STALE-ENTRY' not in z.namelist()
        with (root / 'out/.config').open('a') as f:
            f.write('CONFIG_LLVM_POLLY=y\n')
        run(root, 'package-anykernel.sh', env)
        polly_archive, = (root / 'out/flashable').glob('*-polly-*.zip')
        assert polly_archive != archive
        with (root / 'out/.config').open('a') as f:
            f.write('CONFIG_SCSI_MQ_DEFAULT=y\n')
        run(root, 'package-anykernel.sh', env, False)  # must include mq-deadline
        with (root / 'out/.config').open('a') as f:
            f.write('CONFIG_MQ_IOSCHED_DEADLINE=y\n')
        run(root, 'package-anykernel.sh', env)
        mq_archive, = (root / 'out/flashable').glob('*-polly-scsi-mq-*.zip')
        with zipfile.ZipFile(mq_archive) as z:
            assert 'EXPERIMENTAL SCSI blk-mq' in z.read('build-info.txt').decode()
        (root / 'out/arch/arm64/boot/Image.gz').unlink()
        run(root, 'package-anykernel.sh', env, False)
        print('PASS: synthetic pinned-AK3 package, layout/checksum/stale-entry and negative checks')
    else:
        print('SKIP: packaging fixture (supply --anykernel clean pinned checkout)')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--anykernel', type=Path)
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='electro-ci-fixture-') as tmp:
        tests(Path(tmp), args.anykernel.resolve() if args.anykernel else None)


if __name__ == '__main__':
    main()
