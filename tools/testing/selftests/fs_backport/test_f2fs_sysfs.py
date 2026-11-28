#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Actual-function host checks; NOT an ARM64 build or filesystem stress test."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def function(source, name):
    match = re.search(r'^static [^;{]+\b' + name + r'\([^;{]*\)\s*\{', source, re.M)
    assert match, name
    start = match.start()
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def macro(source, name):
    match = re.search(r'^#define ' + name + r'\([^\n]+\n(?:[^\n]*\\\n)*[^\n]*', source, re.M)
    assert match, name
    return match.group()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='gcc')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--self-test-negatives', action='store_true')
    parser.add_argument('--models-only', action='store_true', help='Run extracted-source models/guards; ordered carry-over verifier handles provenance')
    args = parser.parse_args()
    s = (ROOT / 'fs/f2fs/sysfs.c').read_text()
    # Assert complete special-case bodies are unchanged, not just keywords.
    store = function(s, '__sbi_store').replace(
        '__sbi_store_value(a, sbi, ptr + a->offset, t);', '*ui = (unsigned int)t;')
    assert hashlib.sha256(store.encode()).hexdigest() == '409b52da8b24aaece8c6ec6f2d7aac4f33f105fecf2dcc40f90684b30970d137'
    assert hashlib.sha256(function(s, 'f2fs_sbi_store').encode()).hexdigest() == '6b32e808580122f3b167b1d1463f2272e90b87c364c6fe4d7e50ccd521ba64ec'
    assert s.count('F2FS_ATTR_OFFSET(') == 2  # definition + RW wrapper, no un-sized direct users
    attrs = re.findall(r'^F2FS_(?:RW|STAT)_ATTR\((.*?)\);', s, re.M | re.S)
    assert len(attrs) == 42, len(attrs)
    struct = re.search(r'struct f2fs_attr \{.*?\n\};', s, re.S).group()
    functions = '\n'.join(function(s, n) for n in [
        '__sbi_show_value', 'f2fs_sbi_show', '__sbi_store_value', '__sbi_store', 'f2fs_sbi_store'])
    macros = '\n'.join(macro(s, n) for n in ['F2FS_ATTR_OFFSET', 'F2FS_RW_ATTR', 'F2FS_STAT_ATTR'])
    actual = struct + '\n' + functions + '\n' + macros
    model = Path(__file__).with_name('sysfs_model.c').read_text()
    cases = {'baseline': actual}
    if args.self_test_negatives:
        cases.update({
            'four-byte-show': actual.replace('*(u8 *)value', '*(u32 *)value'),
            'four-byte-store': actual.replace('*(u8 *)ui = value', '*(u32 *)ui = value'),
            'truncate-u64': actual.replace('*(u64 *)ui = value', '*(u64 *)ui = (u32)value'),
            'wrong-stat-size': actual.replace('sizeof_field(struct _struct_name, _elname)', '4'),
            'wrong-RW-size': actual.replace('sizeof_field(struct struct_name, elname)', '4'),
        })
    with tempfile.TemporaryDirectory(prefix='f2fs-sysfs-') as tmp:
        for name, code in cases.items():
            assert name == 'baseline' or code != actual
            path = Path(tmp) / (name + '.c')
            exe = Path(tmp) / name
            path.write_text(model.replace('/* ACTUAL */', code))
            flags = ['-fsanitize=undefined', '-fno-sanitize-recover=all'] if args.sanitize else []
            subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-sign-compare'] + flags + [str(path), '-o', str(exe)], check=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            if name == 'baseline':
                assert run.returncode == 0, run.stderr
                print(run.stdout.strip())
            else:
                assert run.returncode < 0 and 'Assertion' in run.stderr, (name, run.returncode, run.stderr)
                print('PASS: compiled semantic mutant rejected: ' + name)
    print('PASS: all42 local RW/stat declarations use size metadata; special-case store and locking wrapper preserved')
    if args.models_only:
        print('LIMIT: historical checkpoint seals not asserted; use carry_over/verify.py for ordered source provenance')
        return
    receipt = json.loads((ROOT / 'Documentation/filesystems/f2fs-sysfs-width-validation.json').read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(ROOT / 'fs/f2fs/sysfs.c') == receipt['after_sha256']
    patch = ROOT / receipt['patch']['path']
    assert digest(patch) == receipt['patch']['sha256']
    for name, expected in receipt['artifact_sha256'].items():
        assert digest(ROOT / name) == expected, name
    for name, expected in receipt['preserved_sha256'].items():
        assert digest(ROOT / name) == expected, name
    with tempfile.TemporaryDirectory(prefix='f2fs-sysfs-replay-') as tmp:
        root = Path(tmp)
        target = root / 'fs/f2fs/sysfs.c'
        target.parent.mkdir(parents=True)
        target.write_text(s)
        subprocess.run(['git', '-C', tmp, 'apply', '--reverse', str(patch)], check=True)
        assert digest(target) == receipt['before_sha256']
        subprocess.run(['git', '-C', tmp, 'apply', str(patch)], check=True)
        assert digest(target) == receipt['after_sha256']
    print('PASS: additive source patch reverse/forward replay; artifact/config/filesystem-policy seals')


if __name__ == '__main__':
    main()
