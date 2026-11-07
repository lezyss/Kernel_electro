#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Offline vendoring/configuration checks, not a root or boot test."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
PIN = 'cbc0b49908066e9c7f778737f65a216f50b203ba'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(root, config, disabled):
    driver = root / 'drivers/kernelsu'
    require(driver.is_dir() and not driver.is_symlink(), 'KSU must be real vendored files')
    require(not any(driver.rglob('.git')), 'nested .git directory/file is not vendoring')
    manifest = json.loads((driver / 'UPSTREAM.json').read_text())
    require(manifest['repository'] == 'https://github.com/backslashxx/KernelSU', 'wrong fork')
    require(manifest['commit'] == PIN, 'unexpected upstream revision; review updates explicitly')
    require(manifest['tag'] == 'v3.3.1+36', 'unexpected tag')
    require(len(manifest['git_blob_sha1']) == 104, 'incomplete source manifest')
    require(set(manifest['local_sha256']) == {
        'Kconfig', 'Makefile', 'kernel_includes.h', 'ksu.c', 'feature/kernel_umount.c',
        'selinux/rules.c', 'selinux/selinux.c', 'selinux/selinux.h',
        'supercall/dispatch.c', 'supercall/supercall.c',
        'manager/apk_sign.c', 'manager/apk_sign.h', 'manager/manager_identity.h',
        'manager/throne_tracker.c', 'include/uapi/supercall.h',
    }, 'unexpected local adaptations')
    require(manifest['susfs_overlay']['commit'] ==
            'fcd50c8f367c470fa8e17eb64fbb8c7ce7527061', 'unexpected SUSFS bridge')
    require(manifest['finasu_overlay']['manager_review_commit'] ==
            '2d5786b9129a254a87ac358c8bec0203ccd53351', 'unexpected FinaSU manager review pin')
    for name, blob in manifest['git_blob_sha1'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe path')
        file = driver / name
        require(file.is_file() and not file.is_symlink(), 'missing regular source: ' + name)
        data = file.read_bytes()
        if name in manifest['local_sha256']:
            actual = hashlib.sha256(data).hexdigest()
            require(actual == manifest['local_sha256'][name], 'adapted source changed: ' + name)
        else:
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            require(actual == blob, 'upstream source changed: ' + name)
    require((driver / 'LICENSE').is_file(), 'missing GPL license')
    require((driver / 'preinit/runner/picoprintf/LICENSE').is_file(), 'missing dependency license')
    require((root / 'drivers/Kconfig').read_text().count('source "drivers/kernelsu/Kconfig"') == 1,
            'Kconfig must include KSU exactly once')
    require((root / 'drivers/Makefile').read_text().count('obj-$(CONFIG_KSU) += kernelsu/') == 1,
            'Kbuild must include KSU exactly once')
    kconfig = (driver / 'Kconfig').read_text().split('config KSU_KPROBES_KSUD')[0]
    require('\tdefault n\n' in kconfig, 'root must not default on for other defconfigs')
    makefile = (driver / 'Makefile').read_text()
    require('$(obj)/ksu.o: $(obj)/flask.h' in makefile, 'missing private SELinux header dependency')
    require('$(call if_changed,ksu_flask)' in makefile, 'missing private header generation')
    require('<generated/compile.h>' not in (driver / 'kernel_includes.h').read_text(),
            'must not rely on init/version.o build order')
    require('CFLAGS_ksu.o += -DUTS_MACHINE=' in makefile, 'missing Kbuild machine definition')
    values = {}
    for line in config.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
    if disabled:
        require(values.get('CONFIG_KSU', 'n') == 'n', 'KSU unexpectedly enabled')
    else:
        for flag in ['KSU', 'KSU_TAMPER_SYSCALL_TABLE', 'KSU_LSM_SECURITY_HOOKS',
                     'KSU_ENABLE_FULL_UID_CHECKS', 'KSU_FEATURE_SULOG', 'KSU_FEATURE_ADBROOT']:
            require(values.get('CONFIG_' + flag) == 'y', 'missing CONFIG_' + flag + '=y')
        for flag in ['KSU_KPROBES_KSUD', 'KSU_HACK_ARM64_BRANCH_LINK', 'KSU_DISABLE_32BIT_HOOKS',
                     'KSU_HOSTSREDIRECT', 'KSU_SHELL_HAS_SU_ALWAYS']:
            require(values.get('CONFIG_' + flag, 'n') == 'n', 'unexpected CONFIG_' + flag)
        # Debug logging is intentionally allowed for a dedicated validation build.
        for flag in ['SECURITY_SELINUX', 'SECCOMP', 'COMPAT']:
            require(values.get('CONFIG_' + flag) == 'y', 'missing platform CONFIG_' + flag)
        if config.name == '.config':
            require(values.get('CONFIG_KALLSYMS') == 'y', 'missing resolved CONFIG_KALLSYMS')
    print('KernelSU: 104 vendored files/provenance, wiring and ' +
          ('disabled' if disabled else 'built-in') + ' configuration PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--config', type=Path,
                        default=Path('arch/arm64/configs/vendor/xiaomi/miatoll_defconfig'))
    parser.add_argument('--expect-disabled', action='store_true')
    args = parser.parse_args()
    config = args.config if args.config.is_absolute() else args.source_root / args.config
    try:
        check(args.source_root, config, args.expect_disabled)
    except (ValueError, OSError, KeyError) as error:
        print('KernelSU integration check FAILED: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
