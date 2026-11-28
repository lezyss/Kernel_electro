#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Freestanding object/stack/export checks, not full kernel or device validation."""
import argparse
import itertools
from pathlib import Path
import shlex
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile
from shims import ROOT, SHIMS
from test_codec import PREBOOT

EXPORTS = {
    'lz4_compress': {'LZ4_compress_fast', 'LZ4_compress_default',
                     'LZ4_compress_destSize', 'LZ4_loadDict', 'LZ4_saveDict',
                     'LZ4_compress_fast_continue', 'LZ4_initStream',
                     'LZ4_resetStream', 'LZ4_resetStream_fast'},
    'lz4hc_compress': {'LZ4_compress_HC', 'LZ4_loadDictHC',
                       'LZ4_compress_HC_continue', 'LZ4_saveDictHC',
                       'LZ4_initStreamHC', 'LZ4_resetStreamHC',
                       'LZ4_resetStreamHC_fast', 'LZ4_setCompressionLevel'},
    'lz4_decompress': {'LZ4_decompress_safe', 'LZ4_decompress_safe_partial',
                       'LZ4_setStreamDecode', 'LZ4_decompress_safe_continue'},
}


def run(cc, out):
    shim = out / 'shim'
    for name, text in SHIMS.items():
        p = shim / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if name == 'linux/module.h':
            text = '''#define EXPORT_SYMBOL(s) \\
const void * const __attribute__((used, section("ksymtab"))) __export_##s = &s
#define MODULE_LICENSE(s)
#define MODULE_DESCRIPTION(s)
'''
        p.write_text(text)
    for name in ('linux/lz4.h', 'linux/decompress/mm.h'):
        p = shim / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('#include "' + str(ROOT / 'include' / name) + '"\n')
    p = shim / 'asm/unaligned.h'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('''#include <linux/types.h>
static inline u32 get_unaligned_le32(const void *p) {
    const u8 *s = p;
    return s[0] | (u32)s[1] << 8 | (u32)s[2] << 16 | (u32)s[3] << 24;
}
''')
    preboot = out / 'preboot.c'
    preboot.write_text(PREBOOT)
    for target in ('x86_64-linux-gnu', 'i386-linux-gnu', 'aarch64-linux-gnu'):
        flags = [*cc, '-target', target, '-O3', '-std=gnu89', '-ffreestanding',
                 '-fno-builtin', '-fno-pic', '-fno-pie', '-fno-stack-protector', '-Wall', '-Wextra',
                 '-Werror', '-fstack-usage', '-Wframe-larger-than=2048', '-DLZ4_FAST_DEC_LOOP=1',
                 '-I' + str(shim), '-I' + str(ROOT)]
        if target.startswith('aarch64'):
            flags += ['-mgeneral-regs-only', '-ffixed-x18']
        seen = set()
        max_frame = 0
        for name, expected in EXPORTS.items():
            obj = out / (name + '-' + target + '.o')
            subprocess.run([*flags, '-c', str(ROOT / 'lib/lz4' / (name + '.c')),
                            '-o', str(obj)], check=True)
            for row in obj.with_suffix('.su').read_text().splitlines():
                _, size, kind = row.rsplit('\t', 2)
                assert kind == 'static' and int(size) <= 2048, row
                max_frame = max(max_frame, int(size))
            with obj.open('rb') as f:
                elf = ELFFile(f)
                symbols = list(elf.get_section_by_name('.symtab').iter_symbols())
                undefined = {s.name for s in symbols if s.name and s['st_shndx'] == 'SHN_UNDEF'}
                assert undefined <= {'memcpy', 'memmove', 'memset', 'memcmp'}, undefined
                defined = {s.name for s in symbols if s.name.startswith('LZ4_') and
                           s['st_info']['bind'] == 'STB_GLOBAL' and s['st_shndx'] != 'SHN_UNDEF'}
                assert not seen & defined, seen & defined
                seen |= defined
                exported = {s.name.removeprefix('__export_') for s in symbols
                            if s.name.startswith('__export_')}
                assert exported == expected, (name, exported ^ expected)
                assert exported <= defined
                for section in elf.iter_sections():
                    if section.name in ('.bss', '.data'):
                        assert section['sh_size'] < 4096, section.name
        # Compile the real preboot include chain for every word size/architecture.
        subprocess.run([*flags, '-Wno-pointer-sign', '-Wno-unused-function',
                        '-Wno-unused-parameter', '-Wno-sign-compare',
                        '-c', str(preboot), '-o', str(out / ('preboot-' + target + '.o'))],
                       check=True)
        print('PASS:', target, 'split objects, no codec/allocator cross-references,',
              'exports, max frame', max_frame, 'bytes, real STATIC wrapper', flush=True)

    # Evaluate the actual Makefile for all 27 y/m/n object combinations.
    probe = out / 'objects.mk'
    probe.write_text('include ' + str(ROOT / 'lib/lz4/Makefile') +
                     '\n.PHONY: print\nprint:\n\t@echo "$(obj-y)|$(obj-m)"\n')
    names = tuple(EXPORTS)
    configs = ('CONFIG_LZ4_COMPRESS', 'CONFIG_LZ4HC_COMPRESS', 'CONFIG_LZ4_DECOMPRESS')
    for values in itertools.product(('y', 'm', 'n'), repeat=3):
        result = subprocess.check_output(['make', '--no-print-directory', '-f', str(probe),
                                          'print', *[k + '=' + v for k, v in zip(configs, values)]],
                                         text=True).strip().split('|')
        for kind, actual in zip(('y', 'm'), result):
            expected = {n + '.o' for n, v in zip(names, values) if v == kind}
            assert set(actual.split()) == expected, (values, kind, actual)
    print('PASS: all 27 built-in/module/disabled Kbuild selections', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cc', default='clang')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        run(shlex.split(args.cc), args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='lz4-build-') as tmp:
            run(shlex.split(args.cc), Path(tmp))


if __name__ == '__main__':
    main()
