#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Validate current resolved config separately from sealed historical sources."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def run(root, script, *args):
    subprocess.run([sys.executable, str(root / 'tools/testing/selftests' / script),
                    *map(str, args)], cwd=root, check=True)


def check(config, defconfig, cc):
    # Replay trees deliberately exclude build output. Anchor the real output
    # config before invoking ANY checker; never synthesize obsolete selectors.
    config = config.resolve(strict=True)
    requested = defconfig.read_text().splitlines()
    print('Integration preflight: CURRENT resolved config ' + str(config), flush=True)
    if 'CONFIG_KSU=y' in requested:
        # +50 validates today's config, including ABSENCE of obsolete SULOG.
        # Its historical suites use their own verified predecessor defconfig.
        run(ROOT, 'kernelsu/test_update50.py', '--config', config,
            '--self-test-negatives', '--historical')
    if 'CONFIG_NOMOUNT=y' in requested:
        run(ROOT, 'nomount/test_integration.py', '--config', config)
        run(ROOT, 'nomount/test_update23.py', '--self-test-negatives', '--historical')
    if 'CONFIG_KSU_SUSFS=y' in requested:
        # These CLIs validate current seals before detached source replay.
        run(ROOT, 'susfs/test_integration.py', '--config', config)
        run(ROOT, 'susfs/test_provenance_overlays.py', '--config', config)
        # 2.4's exact-source models must NOT read the modified +50 source as
        # though it were the old 2.4 postimage. No manifest is resealed/relaxed.
        sys.path.insert(0, str(ROOT / 'tools/testing/selftests/kernelsu'))
        from update50 import reviewed_base
        with reviewed_base(ROOT) as predecessor:
            print('SUSFS2.4 models: verified detached PRE-KSU+50 sources', flush=True)
            run(predecessor, 'susfs/test_backport_240.py', '--cc', cc,
                '--self-test-negatives')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--defconfig', type=Path, required=True)
    parser.add_argument('--cc', required=True, help='Host model compiler, not target build proof')
    args = parser.parse_args()
    check(args.config, args.defconfig, args.cc)


if __name__ == '__main__':
    main()
