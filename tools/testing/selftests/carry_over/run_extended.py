#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Remaining carry-over host matrix; Clang on PATH, GCC for security shims."""
import argparse
from pathlib import Path
import resource
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-source', action='store_true')
    parser.add_argument('--negatives-only', action='store_true', help='Run only the separate one-at-a-time controls')
    args = parser.parse_args()
    cases = [
        ('bore/test_backport.py', ['--cc', 'clang']),
        ('cambyses/test_backport.py', ['--cc', 'clang', '--self-test-negatives']),
        ('mglru/test_backport.py', ['--cc', 'clang']),
        ('mm_backport/test_backport.py', ['--cc', 'clang']),
        ('vmalloc_backport/test_backport.py', ['--cc', 'clang']),
        ('procfs_backport/test_backport.py', ['--cc', 'clang']),
        ('fs_backport/test_backport.py', ['--cc', 'clang']),
        ('fs_backport/test_f2fs_sysfs.py', ['--models-only', '--sanitize', '--self-test-negatives']),
        ('fs_backport/test_f2fs_merge.py', ['--cc', 'clang']),
        ('bbr3/test_backport.py', ['--cc', 'clang', '--self-test-negatives']),
        ('bbr3/test_edt.py', ['--self-test-negatives']),
        ('carry_over/test_security.py', []),
        ('susfs/test_backport_240.py', ['--cc', 'clang', '--models-only', '--self-test-negatives']),
    ] + [('bpf_upgrade/test_' + n + '.py', ['--self-test-negatives'])
         for n in ['jmp32', 'core', 'atomics', 'softirq', 'lockdep', 'timer_lifetime']]
    if args.negatives_only:
        cases = []
    if args.verify_source:
        cases.insert(0, ('carry_over/verify.py', []))
    for name, extra in cases:
        print('\nRUN:', name, *extra, flush=True)
        subprocess.run([sys.executable, str(ROOT / 'tools/testing/selftests' / name), *extra], cwd=ROOT, check=True)
    # Older suites expose one-at-a-time negative controls. Count only compiled
    # controls that reach a runtime assertion/trap, never compiler failures.
    negatives = {
        'bore/test_backport.py': ['--donor-idle', '--legacy-nice'],
        'mm_backport/test_backport.py': ['donor-psi', 'old-trace', 'old-shrinker', 'old-retry'],
        'vmalloc_backport/test_backport.py': ['donor-search', 'missing-unlock', 'boot-skip', 'wrong-gfp', 'early-reuse'],
        'fs_backport/test_backport.py': ['no-file-pin', 'missing-fput', 'donor-freeing', 'late-freeing', 'no-cp-lock', 'gc-after-iput', 'atomic-bypass'],
        'procfs_backport/test_backport.py': ['--donor-padding', '--donor-locked-pss'],
        'fs_backport/test_f2fs_merge.py': ['null-selector', 'missing-accounting', 'bounce-accounting', 'no-ipu-drain', 'gc-freezer-window', 'cp-late-counter', 'cp-no-umount-protection', 'cp-no-lifetime-gate', 'cp-drop-error'],
    }
    for name, mutants in negatives.items():
        for mutant in mutants:
            opt = [mutant] if mutant.startswith('--') else ['--negative', mutant]
            command = [sys.executable, str(ROOT / 'tools/testing/selftests' / name), '--cc', 'clang', *opt]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            if name == 'fs_backport/test_f2fs_merge.py':
                # This suite itself verifies the child died by SIGABRT/SIGILL.
                assert result.returncode == 0 and 'Negative mutant rejected: ' + mutant in result.stdout, (mutant, result.stdout, result.stderr)
            else:
                assert result.returncode and ('SIGABRT' in result.stderr or 'SIGILL' in result.stderr or 'SIGFPE' in result.stderr), (name, mutant, result.stdout, result.stderr)
            assert 'error:' not in result.stderr, (name, mutant, result.stderr)
            print('PASS: compiled runtime negative rejected:', name, mutant, flush=True)
    print('\nPASS: ' + ('separate runtime negative controls' if args.negatives_only else '19 expanded host suites and requested runtime negative controls'), flush=True)
    print('LIMITS: extracted functions/mocked platforms only; not an image link, device boot, concurrency or performance qualification')


if __name__ == '__main__':
    main()
