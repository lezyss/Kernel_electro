#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Install/verify a pinned Antman-catalogue release without mutable manager code.

Keep the SHA-256-verified archive in the cache. Every verify compares installed
files/symlinks against that archive, not a self-asserted version marker alone.
No automatic system-library patching, latest updates, or GCC fallback.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'scripts/ci/neutron.lock.json'
ARCHIVE = '.neutron-archive.tar.zst'
RECEIPT = 'neutron-install.json'
TOOLS = ('clang', 'clang++', 'ld.lld', 'llvm-ar', 'llvm-nm', 'llvm-strip',
         'llvm-objcopy', 'llvm-objdump', 'llvm-readelf')


def fail(message):
    raise RuntimeError(message)


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def check_host(lock):
    if platform.machine() not in ('x86_64', 'amd64'):
        fail('Neutron release requires an x86-64 Linux host')
    version = subprocess.check_output(['getconf', 'GNU_LIBC_VERSION'], text=True).strip()
    try:
        actual = tuple(map(int, version.split()[-1].split('.')))
        required = tuple(map(int, lock['minimum_glibc'].split('.')))
    except ValueError:
        fail('Cannot determine host glibc: ' + version)
    if actual < required:
        fail('Neutron ' + lock['tag'] + ' needs glibc >= ' + lock['minimum_glibc'] +
             '; found ' + version + '. Use the pinned CI container; do not replace system libc.')


@contextlib.contextmanager
def tar_stream(path):
    process = subprocess.Popen(['zstd', '-dc', str(path)], stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            yield archive
        process.stdout.close()
        if process.wait() != 0:
            fail('zstd archive decompression failed')
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait()


def clean_name(name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts:
        fail('Unsafe archive member: ' + name)
    return p.as_posix()



def safe_member(member, directory):
    name = clean_name(member.name)
    root = directory.resolve()
    def contained(path):
        return os.path.commonpath((str(root), str(path.resolve()))) == str(root)
    if not contained(directory / name):
        fail('Archive path escapes toolchain directory: ' + name)
    if member.issym() or member.islnk():
        if Path(member.linkname).is_absolute():
            fail('Absolute archive link: ' + name)
        base = (directory / name).parent if member.issym() else directory
        if not contained(base / member.linkname):
            fail('Archive link escapes toolchain directory: ' + name)
    elif not (member.isfile() or member.isdir()):
        fail('Unsupported archive member: ' + name)
    return member


def extract_archive(archive, directory):
    seen = set()
    with tar_stream(archive) as tar:
        for member in tar:
            name = clean_name(member.name)
            if name in ('.', ''):
                continue
            if name in (ARCHIVE, RECEIPT) or name in seen:
                fail('Reserved/duplicate archive member: ' + name)
            seen.add(name)
            member = safe_member(member, directory)
            p = directory / name
            p.parent.mkdir(parents=True, exist_ok=True)
            if member.isdir():
                p.mkdir(exist_ok=True)
            elif member.issym():
                p.symlink_to(member.linkname)
            elif member.islnk():
                target = directory / clean_name(member.linkname)
                if not target.is_file() or target.is_symlink():
                    fail('Missing/invalid archive hardlink target: ' + name)
                os.link(target, p)
            else:
                # Never follow a pre-existing file symlink. Parent/link targets
                # have also been checked to stay inside the isolated stage.
                fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as out:
                    shutil.copyfileobj(tar.extractfile(member), out)
                p.chmod(member.mode & 0o777)


def verify_files(directory, lock):
    archive = directory / ARCHIVE
    if not archive.is_file() or sha_file(archive) != lock['archive_sha256']:
        fail('Neutron archive SHA-256 mismatch or missing cached archive')
    expected = set()
    with tar_stream(archive) as tar:
        for member in tar:
            name = clean_name(member.name)
            if name in ('.', ''):
                continue
            if name in (ARCHIVE, RECEIPT) or name in expected:
                fail('Reserved/duplicate archive member: ' + name)
            expected.add(name)
            p = directory / name
            safe = safe_member(member, directory)
            if safe.issym():
                if not p.is_symlink() or os.readlink(p) != safe.linkname:
                    fail('Installed symlink differs from pinned archive: ' + name)
            elif safe.isdir():
                if not p.is_dir() or p.is_symlink():
                    fail('Installed directory differs from pinned archive: ' + name)
            elif safe.isfile() or safe.islnk():
                if not p.is_file() or p.is_symlink():
                    fail('Installed file missing: ' + name)
                if safe.islnk():
                    # The target itself is verified as a regular archive member.
                    target = directory / clean_name(safe.linkname)
                    if not target.is_file() or sha_file(p) != sha_file(target):
                        fail('Installed hardlink differs: ' + name)
                else:
                    h = hashlib.sha256()
                    f = tar.extractfile(member)
                    for chunk in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(chunk)
                    if sha_file(p) != h.hexdigest():
                        fail('Installed file differs from pinned archive: ' + name)
                if bool(p.stat().st_mode & 0o111) != bool(safe.mode & 0o111):
                    fail('Installed executable mode differs: ' + name)
            else:
                fail('Unsupported archive member: ' + name)
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*')}
    # Tar archives need not list parent directories explicitly.
    parents = {str(p) for name in expected for p in Path(name).parents if str(p) != '.'}
    extras = actual - expected - parents - {ARCHIVE, RECEIPT}
    if extras:
        fail('Unexpected files in Neutron cache: ' + ', '.join(sorted(extras)[:5]))
    for name in TOOLS:
        if not os.access(directory / 'bin' / name, os.X_OK):
            fail('Missing pinned LLVM tool: ' + name)


def verify(directory, lock):
    check_host(lock)
    marker = directory / RECEIPT
    if not marker.is_file() or json.loads(marker.read_text()) != lock:
        fail('Neutron installation receipt does not match repository lock')
    verify_files(directory, lock)
    version = subprocess.check_output([str(directory / 'bin/clang'), '--version'], text=True)
    if 'Neutron' not in version or ('clang version ' + lock['clang_version']) not in version:
        fail('Unexpected Neutron compiler identity: ' + version)
    print('PASS: Neutron ' + lock['tag'] + ', cached archive and installed LLVM files verified')
    return version


def install(directory, lock):
    check_host(lock)
    if directory.exists():
        verify(directory, lock)
        return
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.neutron-install-', dir=directory.parent) as tmp:
        stage = Path(tmp) / 'toolchain'
        stage.mkdir()
        archive = stage / ARCHIVE
        subprocess.run(['curl', '--fail', '--location', '--retry', '3',
                        lock['archive_url'], '-o', str(archive)], check=True)
        if sha_file(archive) != lock['archive_sha256']:
            fail('Downloaded Neutron archive SHA-256 mismatch')
        extract_archive(archive, stage)
        (stage / RECEIPT).write_text(json.dumps(lock, sort_keys=True, indent=2) + '\n')
        verify(stage, lock)
        os.replace(stage, directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'verify'))
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    directory = (args.directory or ROOT / '.toolchains' / ('neutron-' + lock['tag'])).absolute()
    try:
        if args.action == 'install':
            install(directory, lock)
        else:
            print(verify(directory, lock), end='')
    except (RuntimeError, OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
