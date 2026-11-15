#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Run carry-over host regressions. GCC/mocks are NOT target/device proof."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-source', action='store_true')
    args = parser.parse_args()
    cases = [
        ('azyr_selected/test_rwlocks.py', []),
        ('memlat/test_memlat.py', ['--self-test-negatives']),
        ('cpufreq_ipa/test_tuning.py', ['--self-test-negatives', '--general-regs-only']),
        ('azyr_selected/test_selected.py', []),
        ('sched_correctness/test_backport.py', ['--cc', 'gcc', '--self-test-negatives']),
        ('gpu_dl_backport/test_backport.py', ['--cc', 'gcc', '--self-test-negatives']),
    ]
    if args.verify_source:
        cases.insert(0, ('carry_over/verify.py', []))
    for relative, extra in cases:
        print('\nRUN:', relative, *extra, flush=True)
        subprocess.run([sys.executable, str(ROOT / 'tools/testing/selftests' / relative),
                        *extra], cwd=ROOT, check=True)
    print('\nPASS: all requested host suites; NOT full ARM64 image/device/concurrency qualification', flush=True)


if __name__ == '__main__':
    main()
