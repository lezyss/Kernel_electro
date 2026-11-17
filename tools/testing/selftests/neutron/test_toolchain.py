#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Synthetic integrity/host/workflow tests; never a real Neutron build claim."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('neutron_toolchain', ROOT / 'scripts/ci/neutron-toolchain.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


class Toolchain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='neutron-fixture-')
        self.root = Path(self.tmp.name)
        self.lock = json.loads(n.LOCK.read_text())
        self.output = self.root / 'tc'
        self.output.mkdir()
        self.tar = self.root / 'fixture.tar'
        with tarfile.open(self.tar, 'w') as tar:
            for name in n.TOOLS:
                data = b'#!/bin/sh\necho "Neutron clang version 24.0.0git (SYNTHETIC)"\n'
                item = tarfile.TarInfo('bin/' + name)
                item.size = len(data)
                item.mode = 0o755
                tar.addfile(item, io.BytesIO(data))
            item = tarfile.TarInfo('bin/clang-link')
            item.type = tarfile.SYMTYPE
            item.linkname = 'clang'
            tar.addfile(item)
        (self.output / n.ARCHIVE).write_bytes(self.tar.read_bytes())
        self.lock['archive_sha256'] = n.sha_file(self.tar)
        # The stream stub is explicitly synthetic. Real CLI uses zstd -dc.
        self.stream = patch.object(n, 'tar_stream', lambda p: tarfile.open(p, 'r:'))
        self.stream.start()
        n.extract_archive(self.tar, self.output)
        (self.output / n.RECEIPT).write_text(json.dumps(self.lock))

    def tearDown(self):
        self.stream.stop()
        self.tmp.cleanup()

    def test_valid_archive(self):
        n.verify_files(self.output, self.lock)

    def test_archive_corruption(self):
        with (self.output / n.ARCHIVE).open('ab') as f:
            f.write(b'bad')
        with self.assertRaisesRegex(RuntimeError, 'SHA-256'):
            n.verify_files(self.output, self.lock)

    def test_binary_corruption(self):
        (self.output / 'bin/clang').write_text('bad')
        with self.assertRaisesRegex(RuntimeError, 'differs'):
            n.verify_files(self.output, self.lock)

    def test_extra_file(self):
        (self.output / 'bin/unpinned').write_text('bad')
        with self.assertRaisesRegex(RuntimeError, 'Unexpected'):
            n.verify_files(self.output, self.lock)

    def test_symlink_corruption(self):
        p = self.output / 'bin/clang-link'
        p.unlink()
        p.symlink_to('clang++')
        with self.assertRaisesRegex(RuntimeError, 'symlink differs'):
            n.verify_files(self.output, self.lock)

    def test_mode_corruption(self):
        (self.output / 'bin/clang').chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, 'mode differs'):
            n.verify_files(self.output, self.lock)

    def test_stale_receipt(self):
        (self.output / n.RECEIPT).write_text('{}')
        with patch.object(n, 'check_host'):
            with self.assertRaisesRegex(RuntimeError, 'receipt'):
                n.verify(self.output, self.lock)

    def test_old_glibc(self):
        with patch.object(n.subprocess, 'check_output', return_value='glibc 2.36'):
            with self.assertRaisesRegex(RuntimeError, 'needs glibc >= 2.43'):
                n.check_host(self.lock)

    def test_supported_glibc(self):
        with patch.object(n.subprocess, 'check_output', return_value='glibc 2.43'):
            n.check_host(self.lock)

    def test_unsafe_paths_and_links(self):
        for path in ('../../escape', '/tmp/escape'):
            member = tarfile.TarInfo(path)
            with self.assertRaises(RuntimeError):
                n.safe_member(member, self.output)
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            for target in ('../../escape', '/tmp/escape'):
                member = tarfile.TarInfo('bin/bad')
                member.type, member.linkname = kind, target
                with self.assertRaises(RuntimeError):
                    n.safe_member(member, self.output)

    def test_special_file(self):
        member = tarfile.TarInfo('device')
        member.type = tarfile.CHRTYPE
        with self.assertRaisesRegex(RuntimeError, 'Unsupported'):
            n.safe_member(member, self.output)

    def test_live_identity(self):
        with patch.object(n, 'check_host'):
            n.verify(self.output, self.lock)

    def test_wrong_identity(self):
        with patch.object(n, 'check_host'), patch.object(n.subprocess, 'check_output', return_value='clang version 24.0.0git'):
            with self.assertRaisesRegex(RuntimeError, 'compiler identity'):
                n.verify(self.output, self.lock)

    def test_workflow_contract(self):
        text = (ROOT / '.github/workflows/build-kernel.yml').read_text()
        self.assertIn('  workflow_dispatch:', text)
        self.assertNotIn('  push:', text)
        self.assertNotIn('  pull_request:', text)
        self.assertIn('image: ' + self.lock['container_image'], text)
        self.assertIn("hashFiles('scripts/ci/neutron.lock.json')", text)
        self.assertNotIn('AOSP_CLANG_COMMIT', text)
        self.assertIn('python3 scripts/ci/neutron-toolchain.py install', text)
        self.assertLess(text.index('Install container build dependencies'), text.index('uses: actions/checkout'))
        script = (ROOT / 'scripts/ci/test-lz4.sh').read_text()
        self.assertIn('--cc "$HOST_TEST_CC" --upstream', script)
        self.assertIn('--asan --ubsan', script)
        self.assertIn('--cc "$TOOLCHAIN_DIR/bin/clang" --output out/lz4-tests/arm64', script)
        self.assertIn('020dfeccf9d7e962a48400fc94d3e451df92eead', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
