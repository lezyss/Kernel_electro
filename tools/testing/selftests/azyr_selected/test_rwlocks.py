#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Resolve real ARM64 Kconfig in PREEMPT/non-PREEMPT modes; no target build."""
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
DEFCONFIG = ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig'
SELECTORS = {'CONFIG_ARCH_INLINE_' + kind + '_' + op + suffix
             for kind in ('READ', 'WRITE')
             for op, suffixes in (('LOCK', ('', '_BH', '_IRQ', '_IRQSAVE')),
                                  ('UNLOCK', ('', '_BH', '_IRQ', '_IRQRESTORE')))
             for suffix in suffixes}


def main():
    before = hashlib.sha256(DEFCONFIG.read_bytes()).hexdigest()
    source = (ROOT / 'arch/arm64/Kconfig').read_text()
    lines = re.findall(r'^\s*select (ARCH_INLINE_(?:READ|WRITE)_\w+)(.*)$', source, re.M)
    assert len(lines) == 16 and all(not guard.strip() for _, guard in lines)
    assert {'CONFIG_' + name for name, _ in lines} == SELECTORS
    with tempfile.TemporaryDirectory(prefix='carry-rwlocks-') as tmp:
        out = Path(tmp)
        # GCC is only the host Kconfig-tool compiler here, not ARM64 proof.
        args = ['make', '-s', '-C', str(ROOT), 'O=' + str(out),
                'ARCH=arm64', 'HOSTCC=gcc', 'CC=gcc']
        subprocess.run([*args, 'vendor/xiaomi/miatoll_defconfig'], check=True)
        config = out / '.config'
        for preempt in (True, False):
            subprocess.run([str(ROOT / 'scripts/config'), '--file', str(config),
                            '--enable' if preempt else '--disable', 'PREEMPT',
                            '--disable', 'PREEMPT_VOLUNTARY',
                            '--disable' if preempt else '--enable', 'PREEMPT_NONE'], check=True)
            subprocess.run([*args, 'olddefconfig'], check=True)
            text = config.read_text()
            assert ('CONFIG_PREEMPT=y' in text) == preempt
            assert all(name + '=y' in text.splitlines() for name in SELECTORS)
            print('PASS:', 'PREEMPT' if preempt else 'non-PREEMPT',
                  'real Kconfig resolves all 16 ARM64 rwlock inlining selectors')
    assert hashlib.sha256(DEFCONFIG.read_bytes()).hexdigest() == before
    print('LIMITS: host Kconfig only; no prebuilt vendor-module ABI or lock-stress validation')


if __name__ == '__main__':
    main()
