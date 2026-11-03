#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Offline integrity/config checks and extracted-source NoMount host tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
PIN = '04af0552bb29c7cee1b78c3eea69d7ed98b80bf2'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def integrity(root, config, disabled):
    driver = root / 'fs/nomount'
    require(driver.is_dir() and not driver.is_symlink(), 'driver must be vendored regular files')
    require(not any(driver.rglob('.git')), 'nested .git is not vendoring')
    manifest = json.loads((driver / 'UPSTREAM.json').read_text())
    require(manifest['repository'] == 'https://github.com/maxsteeel/nomount', 'wrong repository')
    require(manifest['commit'] == PIN, 'unexpected revision; review updates explicitly')
    require(set(manifest['upstream_files']) == {'Kconfig', 'Makefile', 'nomount.c', 'nomount.h', 'LICENSE'},
            'incomplete file manifest')
    require(set(manifest['local_sha256']) == {'Kconfig', 'Makefile'}, 'unexpected adaptations')
    for name, source in manifest['upstream_files'].items():
        file = driver / name
        require(file.is_file() and not file.is_symlink(), 'missing regular file: ' + name)
        data = file.read_bytes()
        if name in manifest['local_sha256']:
            require(hashlib.sha256(data).hexdigest() == manifest['local_sha256'][name],
                    'adapted source changed: ' + name)
        else:
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            require(blob == source['git_blob'], 'upstream source changed: ' + name)
    require((root / 'fs/Makefile').read_text().count('obj-$(CONFIG_NOMOUNT) += nomount/') == 1,
            'Kbuild wiring must appear once')
    require((root / 'fs/Kconfig').read_text().count('source "fs/nomount/Kconfig"') == 1,
            'Kconfig wiring must appear once')
    kconfig = (driver / 'Kconfig').read_text()
    require('\tdefault n' in kconfig and '\tdepends on KEYS' in kconfig,
            'require opt-in and keyring dependency')
    makefile = (driver / 'Makefile').read_text()
    require('-fno-stack-protector' not in makefile and '-O3' not in makefile,
            'retain kernel stack-protection and optimization flags')
    require('NM_HAS_XATTR__GET' in makefile, 'missing downstream xattr detection')
    values = {}
    for line in config.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
    require(values.get('CONFIG_NOMOUNT', 'n') == ('n' if disabled else 'y'),
            'wrong resolved CONFIG_NOMOUNT')
    if not disabled:
        require(values.get('CONFIG_KEYS') == 'y', 'keyring support must remain enabled')
    print('NoMount vendored-source, wiring and configuration checks: PASS', flush=True)


def function(source, name):
    # Reject forward declarations; these selected bodies do not contain braces
    # in string literals/comments. Extract from the actual vendored files.
    pattern = r'^static [^;{}]*?\b' + re.escape(name) + r'\([^;{}]*?\)\s*\{'
    match = re.search(pattern, source, re.M)
    require(match is not None, 'function not found: ' + name)
    end, depth = match.end(), 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]


def model(root, compiler, negative):
    driver = root / 'fs/nomount'
    source = (driver / 'nomount.c').read_text()
    header = (driver / 'nomount.h').read_text()
    bodies = '\n'.join(function(source, name) for name in
                       ['nm_key_preparse', 'nm_is_uid_blocked', 'nm_select_rule'])
    bodies += '\n' + '\n'.join(function(header, name) for name in
                               ['nm_is_virtual_pos', 'nm_pack_pos', 'nm_unpack_pos',
                                'nm_uid_bloom_set', 'nm_uid_bloom_test',
                                'nm_uid_add', 'nm_uid_del'])
    if negative:
        old = bodies
        if negative == 'no-capability-gate':
            bodies = bodies.replace('if (!capable(CAP_SYS_ADMIN)) return -EPERM;', '')
        elif negative == 'no-rcu-unlock':
            bodies = bodies.replace('rcu_guard();', 'rcu_read_lock();')
        elif negative == 'wrong-compat-cookie':
            bodies = bodies.replace('(NM_SIG_16 << 16) | (id & 0xFFFF)',
                                    '(NM_SIG_16 << 48) | (id & 0xFFFF)')
        elif negative == 'no-uid-bloom':
            bodies = bodies.replace('nm_uid_bloom_set(new_arr, target);', '')
        require(old != bodies, 'negative control made no change')
    code = Path(__file__).with_name('model.c').read_text().replace('/* PRODUCTION */', bodies)
    with tempfile.TemporaryDirectory(prefix='nomount-test-') as temp:
        temp = Path(temp)
        (temp / 'model.c').write_text(code)
        subprocess.run(shlex.split(compiler) + ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-sign-compare',
                       str(temp / 'model.c'), '-o', str(temp / 'model')], check=True)
        subprocess.run([str(temp / 'model')], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--config', type=Path,
                        default=Path('arch/arm64/configs/vendor/xiaomi/miatoll_defconfig'))
    parser.add_argument('--expect-disabled', action='store_true')
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'clang'))
    parser.add_argument('--host-tests', action='store_true')
    parser.add_argument('--negative', choices=['no-capability-gate', 'no-rcu-unlock',
                                             'wrong-compat-cookie', 'no-uid-bloom'])
    args = parser.parse_args()
    config = args.config if args.config.is_absolute() else args.source_root / args.config
    try:
        integrity(args.source_root, config, args.expect_disabled)
        if args.host_tests or args.negative:
            model(args.source_root, args.cc, args.negative)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print('NoMount integration test FAILED: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
