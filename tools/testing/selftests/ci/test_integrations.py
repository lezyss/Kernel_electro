#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Regression coverage for CI current-config / historical-source dispatch."""
import contextlib
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('ci_integrations', ROOT / 'scripts/ci/check-integrations.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ci-dispatch-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'out/.config'
        self.config.parent.mkdir()
        self.config.write_text('CONFIG_KSU=y\nCONFIG_NOMOUNT=y\nCONFIG_KEYS=y\n')
        self.defconfig = self.root / 'miatoll_defconfig'
        self.defconfig.write_text('CONFIG_KSU=y\nCONFIG_NOMOUNT=y\nCONFIG_KSU_SUSFS=y\n')
        self.calls = []
        self.replayed = []

        @contextlib.contextmanager
        def reviewed_base(root):
            self.replayed.append(root)
            yield self.root / 'verified-predecessor'

        self.enterContext(patch.object(ci, 'ROOT', self.root))
        self.enterContext(patch.object(ci, 'run', side_effect=lambda *args: self.calls.append(args)))
        self.enterContext(patch.dict(sys.modules, {'update50': types.SimpleNamespace(reviewed_base=reviewed_base)}))
        self.enterContext(patch.object(sys, 'path', list(sys.path)))

    def check(self, path=None):
        ci.check(path or self.config, self.defconfig, 'test-host-clang')

    def test_current_ksu_not_legacy_config_checker(self):
        self.check()
        _, script, *args = self.calls[0]
        self.assertEqual(script, 'kernelsu/test_update50.py')
        self.assertIn('--historical', args)
        self.assertIn('--self-test-negatives', args)
        self.assertEqual(args[:2], ['--config', self.config])
        self.assertFalse(any(c[1] == 'kernelsu/test_integration.py' for c in self.calls))

    def test_relative_build_config_becomes_absolute(self):
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            self.check(Path('out/.config'))
        finally:
            os.chdir(cwd)
        for _, _, *args in self.calls:
            if '--config' in args:
                self.assertEqual(args[args.index('--config') + 1], self.config)

    def test_susfs_models_only_on_verified_predecessor(self):
        self.check()
        self.assertEqual(self.replayed, [self.root])
        self.assertEqual(self.calls[-1], (self.root / 'verified-predecessor',
            'susfs/test_backport_240.py', '--cc', 'test-host-clang', '--self-test-negatives'))

    def test_config_not_rewritten_to_add_obsolete_selector(self):
        before = self.config.read_bytes()
        self.check()
        self.assertEqual(self.config.read_bytes(), before)
        self.assertNotIn(b'CONFIG_KSU_FEATURE_SULOG', before)

    def test_nomount_has_current_behavior_and_resolved_config_checks(self):
        self.check()
        names = [c[1] for c in self.calls]
        self.assertIn('nomount/test_update23.py', names)
        c = next(c for c in self.calls if c[1] == 'nomount/test_integration.py')
        self.assertEqual(c[2:], ('--config', self.config))

    def test_disabled_defconfig_skips_unrequested_integrations(self):
        self.defconfig.write_text('# CONFIG_KSU is not set\n')
        self.check()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.replayed, [])

    def test_missing_config_is_fatal_before_dispatch(self):
        with self.assertRaises(FileNotFoundError):
            self.check(self.root / 'missing/.config')
        self.assertEqual(self.calls, [])

    def test_failed_current_check_stops_preflight(self):
        with patch.object(ci, 'run', side_effect=subprocess.CalledProcessError(1, ['checker'])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.check()
        self.assertEqual(self.replayed, [])

    def test_build_script_calls_new_preflight_and_keeps_pipefail(self):
        script = (ROOT / 'scripts/ci/build-kernel.sh').read_text()
        self.assertIn('set -euo pipefail', script)
        self.assertEqual(script.count('python3 scripts/ci/check-integrations.py'), 1)
        self.assertIn('--config "$ROOT/out/.config"', script)
        self.assertIn('| tee out/integrations.log', script)
        self.assertNotIn('test_backport_240.py', script)
        self.assertNotIn('kernelsu/test_integration.py --config', script)


if __name__ == '__main__':
    unittest.main()
