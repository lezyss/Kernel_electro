#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Reproduce KNOWN raw-base LZ4 blockers with host fixtures, not a kernel test."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def main():
    h = (ROOT / 'lib/lz4/lz4.h').read_text()
    version = tuple(int(re.search(r'^#define LZ4_VERSION_' + key + r'\s+(\d+)', h, re.M)[1])
                    for key in ['MAJOR', 'MINOR', 'RELEASE'])
    assert version == (1, 11, 1), version
    with tempfile.TemporaryDirectory(prefix='lz4-base-check-') as tmp:
        tmp = Path(tmp)
        shim = tmp / 'include/linux'
        shim.mkdir(parents=True)
        headers = {
            'compiler.h': '#define noinline __attribute__((__noinline__))\n#ifndef __always_inline\n#define __always_inline inline __attribute__((always_inline))\n#endif\n#define likely(x) __builtin_expect(!!(x),1)\n#define unlikely(x) __builtin_expect(!!(x),0)\n',
            'export.h': '#define EXPORT_SYMBOL(x)\n',
            'string.h': '#include <string.h>\n',
            'types.h': '#include <stddef.h>\n#include <stdint.h>\ntypedef uint8_t u8;\ntypedef uint16_t u16;\ntypedef uint32_t u32;\ntypedef uint64_t u64;\n',
            'limits.h': '#include <limits.h>\n',
        }
        for name, data in headers.items():
            (shim / name).write_text(data)
        preboot = subprocess.run(['gcc', '-E', '-DSTATIC=static', '-I' + str(ROOT / 'include'),
            str(ROOT / 'lib/decompress_unlz4.c')], capture_output=True, text=True)
        assert preboot.returncode and 'lz4/lz4_decompress.c: No such file' in preboot.stderr
        print('CONFIRMED BLOCKER: actual STATIC preboot wrapper includes missing lz4_decompress.c')
        print(preboot.stderr.strip())
        hc = subprocess.run(['gcc', '-std=gnu11', '-O2', '-DLZ4_FREESTANDING=1',
            '-I' + str(shim.parent), '-c', str(ROOT / 'lib/lz4/lz4hc.c'),
            '-Wframe-larger-than=2048', '-Werror', '-o', str(tmp / 'hc.o')],
            capture_output=True, text=True)
        assert hc.returncode and 'frame size of' in hc.stderr and 'implicit declaration' not in hc.stderr
        print('CONFIRMED BLOCKER: host fixture detects a >2048-byte HC optimal-parser stack frame')
        print(hc.stderr.strip())
        size = tmp / 'size.c'
        size.write_text('#include <stdio.h>\n#define LZ4_HC_STATIC_LINKING_ONLY\n#include "' +
            str(ROOT / 'include/linux/lz4.h') + '"\nint main(void){ printf("%zu %zu %zu\\n", (size_t)LZ4HC_MEM_COMPRESS, sizeof(LZ4_streamHC_t), (size_t)LZ4_STREAMHC_EXTSIZE);}\n')
        subprocess.run(['gcc', '-std=gnu11', '-Werror', '-I' + str(shim.parent), str(size),
                        '-o', str(tmp / 'size')], check=True)
        sizes = subprocess.check_output([str(tmp / 'size')], text=True).strip()
        assert sizes == '262200 262200 327784', sizes
        print('HOST SIZE FIXTURE (kernel allocation / plain / extended): ' + sizes)
    print('LIMITS: expected failures reproduced, NOT a passing kernel/codec qualification or AOSP ARM64 build.')


if __name__ == '__main__':
    main()
