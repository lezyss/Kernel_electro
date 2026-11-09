#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Offline FinaSU overlay provenance and extracted-production-source host tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
REFERENCES = ['8640f74f7d5fabd7ba5a07e7652e0fd1084c2173',
              'da63482157550d46b2d6a5b3ba4c855ddd1d103a',
              '0cfa13c758b7f8b68a3ed1ef11bc64186231f8f9']
FINA_PIN = '2d5786b9129a254a87ac358c8bec0203ccd53351'
SOURCES = ['manager/apk_sign.c', 'manager/apk_sign.h', 'manager/throne_tracker.c',
           'manager/manager_identity.h', 'include/uapi/supercall.h', 'supercall/dispatch.c']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check(root):
    manifest = json.loads((root / 'Documentation/dev-tools/finasu-manager.json').read_text())
    require(manifest['references'] == REFERENCES and manifest['manager_review_commit'] == FINA_PIN,
            'FinaSU reference pin changed; review explicitly')
    expected_sources = {'drivers/kernelsu/' + p for p in SOURCES}
    require(set(manifest['postimage_sha256']) == expected_sources and
            set(manifest['base_sha256']) == expected_sources, 'FinaSU source manifest incomplete')
    for name, digest in manifest['postimage_sha256'].items():
        p = root / name
        require(p.is_file() and not p.is_symlink(), 'missing regular source: ' + name)
        if name == 'drivers/kernelsu/supercall/dispatch.c':
            text = p.read_text()
            require(text.count('v3.3.1-38') == 2, 'incorrect current version display')
            # Exactly two version-label substitutions may succeed the immutable
            # original FinaSU seal. No authorization/dispatch-body edits allowed.
            restored = text.replace('v3.3.1-38', 'v3.3.1+36').encode()
            require(hashlib.sha256(restored).hexdigest() == digest,
                    'FinaSU dispatch changed beyond honest version labels')
            update = json.loads((root / 'Documentation/dev-tools/kernelsu-updates/v3.3.1-38.json').read_text())
            require(update['base_sha256'][name] == digest, 'broken FinaSU version successor')
            digest = update['postimage_sha256'][name]
        require(hashlib.sha256(p.read_bytes()).hexdigest() == digest,
                'FinaSU source changed without provenance review: ' + name)
    driver = root / 'drivers/kernelsu'
    apk_header = (driver / 'manager/apk_sign.h').read_text()
    require(manifest['package'] == 'me.yuki.fina' and manifest['certificate_size'] == 0x2cc and
            manifest['certificate_sha256'] == '2d89b50aaf1db013c2b6738f973f48b62ea21a3a8d7216bfec3521065d448458',
            'FinaSU trust anchor changed; review explicitly')
    for macro, value in [('KSU_FINASU_PACKAGE_NAME', '"me.yuki.fina"'),
                         ('KSU_FINASU_CERT_SIZE', '0x2cc'),
                         ('KSU_FINASU_CERT_SHA256', '"' + manifest['certificate_sha256'] + '"')]:
        require(re.search(r'^#define ' + macro + r' ' + re.escape(value) + r'$', apk_header, re.M),
                'FinaSU production trust constant changed: ' + macro)
    sign = (driver / 'manager/apk_sign.c').read_text()
    tracker = (driver / 'manager/throne_tracker.c').read_text()
    dispatch = (driver / 'supercall/dispatch.c').read_text()
    require(re.search(r'^CFLAGS_ksu\.o \+= -DKSU_VERSION=32717$',
                      (driver / 'Makefile').read_text(), re.M), 'do not spoof the kernel version')
    require('ksu_get_manager_version' not in dispatch and '33156' not in dispatch,
            'per-manager kernel version spoofing is not supported')
    require('KSU_GET_INFO_FLAG_HOOK_READY' not in dispatch and
            'KSU_GET_INFO_FLAG_HOOK_TRACEPOINT' not in dispatch,
            'do not claim runtime readiness or tracepoint hooks')
    actor = tracker.split('static FILLDIR_RETURN_TYPE my_actor', 1)[1].split('// compat:', 1)[0]
    require('cached_manager_apk_path' not in actor, 'unverified directory entries must not be cached')
    search = tracker.split('static noinline void search_manager', 1)[1].split('static void throne_tracker_fn', 1)[0]
    require(search.index('is_manager_apk(candidate_path)') < search.index('crown_manager(candidate_path, uid_data)') <
            search.index('strscpy(cached_manager_apk_path') < search.index('stop = 1;'),
            'scan must verify and bind UID before caching/stopping')
    require('candidate_path[0] = 0;\n\t\t\titerate_dir' in search, 'stale candidate path')
    refresh = tracker.split('if (prune_only)', 1)[1].split('\nprune:', 1)[0]
    require('is_manager_apk(cached_manager_apk_path)' in refresh and
            'crown_manager(cached_manager_apk_path, &uid_list)' in refresh and
            'ksu_invalidate_manager_uid();' in refresh, 'cached manager identity must be revalidated')
    require('!strcmp(np->package, package)' in tracker, 'verified package must match packages.list exactly')
    for name, handler, permission in [
        ('GET_FULL_VERSION_FINASU', 'do_get_full_version_finasu', 'always_allow'),
        ('GET_FULL_VERSION', 'do_get_full_version', 'always_allow'),
        ('GET_VERSION_TAG', 'do_get_version_tag', 'manager_or_root'),
        ('GET_HOOK_MODE', 'do_get_hook_mode', 'manager_or_root'),
        ('HOOK_TYPE', 'do_get_hook_type', 'manager_or_root')]:
        require(re.search(r'\.cmd = KSU_IOCTL_' + name + r',.*\.handler = ' + handler +
                          r', \.perm_check = ' + permission + r'\s*}', dispatch), 'wrong metadata permission/ABI: ' + name)
    require('KSU_FINASU_CERT_SIZE, KSU_FINASU_CERT_SHA256' in sign, 'missing certificate check')
    print('FinaSU: pinned six-source overlay, secure package binding and honest display ABI PASS')


def host_tests(root, cc, negative_tests=False):
    driver = root / 'drivers/kernelsu'
    sign = (driver / 'manager/apk_sign.c').read_text()
    tracker = (driver / 'manager/throne_tracker.c').read_text()
    dispatch = (driver / 'supercall/dispatch.c').read_text()
    header = (driver / 'include/uapi/supercall.h').read_text()
    apk_header = (driver / 'manager/apk_sign.h').read_text()
    replacements = {
        'IDENTITY': (driver / 'manager/manager_identity.h').read_text(),
        'SIGN': '\n'.join(l for l in apk_header.splitlines() if l.startswith('#define KSU_FINASU_')) +
                '\n' + sign[sign.index('int get_pkg_from_apk_dir_path('):],
        'CROWN': tracker[tracker.index('static bool crown_manager('):tracker.index('\nstruct data_path')],
        'SCANNER': tracker[tracker.index('struct data_path'):tracker.index('static void throne_tracker_fn')],
        'METADATA_STRUCTS': header[header.index('/* FinaSU manager display ABI'):header.rindex('\n#endif')],
        'METADATA': dispatch[dispatch.index('/* These describe the actual pinned'):dispatch.index('// IOCTL handlers mapping table')],
    }
    model = (root / 'tools/testing/selftests/kernelsu/finasu_model.c').read_text()
    for marker, source in replacements.items():
        model = model.replace('/* SOURCE_' + marker + ' */', source)
    with tempfile.TemporaryDirectory(prefix='finasu-test-') as directory:
        src = Path(directory) / 'model.c'
        src.write_text(model)
        for hook, flags in [('Manipulated', ['-DCONFIG_KSU_TAMPER_SYSCALL_TABLE']),
                            ('Manipulated', ['-DCONFIG_KSU_HACK_ARM64_BRANCH_LINK']),
                            ('Kprobes', ['-DCONFIG_KSU_KPROBES_KSUD']), ('Manual', [])]:
            binary = Path(directory) / 'test'
            subprocess.run(shlex.split(cc) + ['-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-Wno-sign-compare', '-Wno-unused-function',
                            '-DEXPECTED_HOOK_TYPE="' + hook + '"'] + flags + [str(src), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
        if negative_tests:
            regressions = {
                'certificate bypass': ('return check_v2_signature(path, KSU_FINASU_CERT_SIZE, KSU_FINASU_CERT_SHA256);', 'return true;'),
                'wrong package UID': ('if (!strcmp(np->package, package))', 'if (ksu_is_manager_package(np->package))'),
                'stop before verification': ('bool is_manager = is_manager_apk(candidate_path);', 'stop = 1; bool is_manager = is_manager_apk(candidate_path);'),
                'unverified cache': ('snprintf(candidate_path, DATA_PATH_LEN, "%s/%.*s", my_ctx->parent_dir, namelen, name);',
                                    'snprintf(candidate_path, DATA_PATH_LEN, "%s/%.*s", my_ctx->parent_dir, namelen, name); strcpy(cached_manager_apk_path, candidate_path);'),
                'wrong 64-byte ABI': ('char version_full[64];', 'char version_full[63];'),
                'ignored copy fault': ('return copy_to_user(arg, data, size) ? -EFAULT : 0;', 'return 0;'),
            }
            for name, (old, new) in regressions.items():
                require(model.count(old) == 1, 'negative-test substitution drift: ' + name)
                src.write_text(model.replace(old, new))
                subprocess.run(shlex.split(cc) + ['-std=gnu11', '-O1', '-DCONFIG_KSU_TAMPER_SYSCALL_TABLE',
                                '-DEXPECTED_HOOK_TYPE="Manipulated"', str(src), '-o', str(binary)], check=True)
                result = subprocess.run([str(binary)], cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                require(result.returncode != 0 and b'FAILED' in result.stderr,
                        'host test missed deliberate regression: ' + name)
                print('FinaSU deliberate regression caught: ' + name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=ROOT)
    p.add_argument('--host-tests', action='store_true')
    p.add_argument('--cc', default='clang')
    p.add_argument('--negative-tests', action='store_true', help='also inject six host-model regressions')
    args = p.parse_args()
    try:
        check(args.source_root)
        if args.host_tests:
            host_tests(args.source_root, args.cc, args.negative_tests)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print('FinaSU check FAILED: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
