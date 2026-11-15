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
import zipfile

from shims import ROOT

PIN = '3b86e40facfff1eab4065614255d573293c10373'
TOOLS = ('clang', 'clang++', 'ld.lld', 'llvm-ar', 'llvm-nm', 'llvm-strip',
         'llvm-objcopy', 'llvm-objdump', 'llvm-readelf')


def run(root, name, env, ok=True):
    p = subprocess.run(['bash', str(root / 'scripts/ci' / name)],
                       cwd=root, env={**os.environ, **env}, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert (p.returncode == 0) == ok, p.stdout
    return p.stdout


def tests(root, anykernel):
    scripts = root / 'scripts/ci'
    scripts.mkdir(parents=True)
    for name in ('build-kernel.sh', 'package-anykernel.sh', 'anykernel.sh'):
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
        p.write_text('#!/bin/sh\necho "Fixture clang version 23.0.1"\n')
        p.chmod(0o755)
    fakebin = root / 'fakebin'
    fakebin.mkdir()
    p = fakebin / 'make'
    p.write_text('''#!/usr/bin/env python3
import json, pathlib, sys
with open('make-calls.jsonl', 'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
out=pathlib.Path('out');out.mkdir(exist_ok=True)
if 'vendor/xiaomi/miatoll_defconfig' in sys.argv:
 (out/'.config').write_text('CONFIG_ARCH_ATOLL=y\\nCONFIG_LLVM_POLLY=y\\n')
if 'Image.gz-dtb' in sys.argv:
 for name in ('Image.gz-dtb','Image.gz','dtb.img','dtbo.img'):
  p=out/'arch/arm64/boot'/name;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_bytes(b'SYNTHETIC SCRIPT FIXTURE - NOT BOOTABLE\\n')
 p=out/'include/config/kernel.release';p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text('fixture-not-bootable\\n')
''')
    p.chmod(0o755)
    env = {'TOOLCHAIN_DIR': str(toolchain), 'PATH': str(fakebin) + ':' + os.environ['PATH'],
           'DEFCONFIG': 'vendor/xiaomi/miatoll_defconfig', 'JOBS': '2'}
    run(root, 'build-kernel.sh', {**env, 'DEFCONFIG': '../../escape_defconfig'}, False)
    run(root, 'build-kernel.sh', {**env, 'JOBS': '-j8'}, False)
    run(root, 'build-kernel.sh', env, False)  # missing compiler pin
    (toolchain / 'aosp-prebuilts-commit.txt').write_text('wrong\n')
    run(root, 'build-kernel.sh', env, False)
    (toolchain / 'aosp-prebuilts-commit.txt').write_text(PIN + '\n')
    run(root, 'build-kernel.sh', env)
    calls = [json.loads(x) for x in (root / 'make-calls.jsonl').read_text().splitlines()]
    assert len(calls) == 4
    for call in calls:
        assert 'LLVM_IAS=1' in call and 'ARCH=arm64' in call
        for variable in ('CC', 'AS', 'LD', 'AR', 'NM', 'STRIP', 'OBJCOPY',
                         'OBJDUMP', 'READELF', 'HOSTCC', 'HOSTCXX'):
            assert any(x.startswith(variable + '=' + str(toolchain / 'bin') + '/') for x in call), call
    assert '# CONFIG_LLVM_POLLY is not set' in (root / 'out/.config').read_text()
    print('PASS: synthetic build script flow, all LLVM overrides, invalid input/pin rejection')

    if anykernel:
        env = {'ANYKERNEL_DIR': str(anykernel), 'GITHUB_RUN_NUMBER': 'fixture',
               'DEFCONFIG': 'vendor/xiaomi/miatoll_defconfig'}
        run(root, 'package-anykernel.sh', {**env, 'DEFCONFIG': 'other_defconfig'}, False)
        run(root, 'package-anykernel.sh', {**env, 'ANYKERNEL_DIR': str(root)}, False)
        run(root, 'package-anykernel.sh', env)
        archive, = (root / 'out/flashable').glob('*.zip')
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
