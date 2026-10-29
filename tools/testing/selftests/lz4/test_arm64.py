#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Freestanding Clang + Unicorn differential test of the actual ARM64 LZ4 code.

Not a kernel-context, target-toolchain or device validation. See README.
"""
import argparse
import os
from pathlib import Path
import random
import shlex
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile
from unicorn import (Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE,
                     UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE)
import unicorn.arm64_const as arm64
from unicorn.arm64_const import (UC_ARM64_REG_X0, UC_ARM64_REG_X18,
                                 UC_ARM64_REG_X19, UC_ARM64_REG_X30,
                                 UC_ARM64_REG_SP, UC_ARM64_REG_PC, UC_ARM64_REG_CPACR_EL1)

ROOT = Path(__file__).resolve().parents[4]
SHIMS = {
    'linux/types.h': '''#ifndef TEST_TYPES_H
#define TEST_TYPES_H
typedef __SIZE_TYPE__ size_t;
typedef __PTRDIFF_TYPE__ ssize_t;
typedef __UINT8_TYPE__ uint8_t;
typedef __UINT16_TYPE__ uint16_t;
typedef __UINT32_TYPE__ uint32_t;
typedef __UINT64_TYPE__ uint64_t;
typedef __INT8_TYPE__ int8_t;
typedef __INT16_TYPE__ int16_t;
typedef __INT32_TYPE__ int32_t;
typedef __INT64_TYPE__ int64_t;
typedef __UINTPTR_TYPE__ uintptr_t;
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef _Bool bool;
#define true 1
#define false 0
#define NULL ((void *)0)
#define asmlinkage
#endif
''',
    'linux/compiler.h': '''#define __always_inline inline __attribute__((always_inline))
#define likely(x) __builtin_expect(!!(x), 1)
#define unlikely(x) __builtin_expect(!!(x), 0)
''',
    'linux/string.h': '''#include <linux/types.h>
void *memcpy(void *, const void *, size_t);
void *memmove(void *, const void *, size_t);
void *memset(void *, int, size_t);
''',
    'linux/errno.h': '#define EIO 5\n',
    'linux/module.h': '''#define EXPORT_SYMBOL(x)
#define MODULE_LICENSE(x)
#define MODULE_DESCRIPTION(x)
''',
    'asm/simd.h': '''extern int simd_allowed;
static inline int may_use_simd(void) { return simd_allowed; }
''',
    'asm/cpufeature.h': '''extern int fpsimd_available;
static inline int system_supports_fpsimd(void) { return fpsimd_available; }
''',
    'asm/neon.h': '''void kernel_neon_begin(void);
void kernel_neon_end(void);
''',
    'asm/cputype.h': '''#define ARM_CPU_PART_CORTEX_A53 0xd03
extern unsigned int cpu_part;
static inline unsigned int read_cpuid_part_number(void) { return cpu_part; }
''',
    'linux/linkage.h': '''#define ENTRY(name) .globl name; .type name, %function; name:
#define ENDPROC(name) .size name, .-name
''',
    'asm/assembler.h': '',
}
RUNTIME = '''#include <linux/types.h>
int simd_allowed = 1;
int fpsimd_available = 1;
unsigned int cpu_part;
unsigned int neon_begin_count, neon_end_count;
void kernel_neon_begin(void) { neon_begin_count++; }
void kernel_neon_end(void) { neon_end_count++; }
void *memcpy(void *d, const void *s, size_t n)
{ size_t i; for (i = 0; i < n; i++) ((u8 *)d)[i] = ((const u8 *)s)[i]; return d; }
void *memset(void *d, int c, size_t n)
{ size_t i; for (i = 0; i < n; i++) ((u8 *)d)[i] = c; return d; }
void *memmove(void *d, const void *s, size_t n)
{ size_t i; if ((unsigned long)d < (unsigned long)s) return memcpy(d, s, n);
  for (i = n; i; i--) ((u8 *)d)[i-1] = ((const u8 *)s)[i-1]; return d; }
'''


def build(cc, out):
    shim = out / 'shim'
    for name, text in SHIMS.items():
        p = shim / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (out / 'runtime.c').write_text(RUNTIME)
    # Avoid compiler-generated SIMD in kernel C; assembly uses NEON explicitly.
    # Zig's driver otherwise overrides Clang's fixed-register/FP features.
    zig_cpu = ['-mcpu=generic+reserve_x18-fp_armv8-neon'] if Path(cc[0]).name == 'zig' else []
    linker = [] if Path(cc[0]).name == 'zig' else ['-fuse-ld=lld']
    common = [*cc, *zig_cpu, '-target', 'aarch64-freestanding', '-O3', '-std=gnu89',
              '-ffreestanding', '-fno-builtin', '-mgeneral-regs-only',
              '-ffixed-x18', '-Wall', '-Wextra', '-Werror',
              '-Wframe-larger-than=2048', '-I' + str(shim),
              '-DCONFIG_ARM64', '-DCONFIG_KERNEL_MODE_NEON',
              '-DCONFIG_LZ4_ARM64_ACCEL', '-DLZ4_FAST_DEC_LOOP=1']
    # Include the real wrappers, not a reimplementation of their dispatch.
    srcs = [ROOT / 'lib/lz4/lz4_decompress_main.c',
            ROOT / 'lib/lz4/lz4_compress.c',
            ROOT / 'lib/lz4/lz4hc_compress.c',
            ROOT / 'lib/lz4/lz4armv8/lz4accel.c',
            ROOT / 'lib/lz4/lz4armv8/lz4armv8.S', out / 'runtime.c']
    objs = []
    for i, src in enumerate(srcs):
        obj = out / (str(i) + '.o')
        flags = [x for x in common if src.suffix != '.S' or
                 (x != '-mgeneral-regs-only' and x not in zig_cpu)]
        subprocess.run([*flags, '-c', str(src), '-o', str(obj)], check=True)
        objs.append(obj)
    elf = out / 'test.elf'
    subprocess.run([*cc, *linker, '-target', 'aarch64-freestanding', '-nostdlib',
                    '-Wl,--entry=LZ4_decompress_safe',
                    *map(str, objs), '-o', str(elf)], check=True)
    # Compile feature-off, no-NEON and STATIC paths with the option defined too.
    for name, extra in [('off', ['-UCONFIG_LZ4_ARM64_ACCEL']),
                        ('no-neon', ['-UCONFIG_KERNEL_MODE_NEON']),
                        ('preboot', ['-DSTATIC'])]:
        obj = out / (name + '.o')
        subprocess.run([*common, *extra, '-c', str(srcs[0]), '-o', str(obj)],
                       check=True)
        with obj.open('rb') as f:
            symbols = ELFFile(f).get_section_by_name('.symtab').iter_symbols()
            assert not any('neon' in x.name or 'lz4_decompress_asm' in x.name
                           for x in symbols), name
    # Also exercise Clang's SCS/ThinLTO compiler and linker on the whole path.
    lto = []
    for i in (0, 3, 5):
        obj = out / ('scs' + str(i) + '.o')
        subprocess.run([*common, '-fsanitize=shadow-call-stack', '-flto=thin',
                        '-c', str(srcs[i]), '-o', str(obj)], check=True)
        lto.append(obj)
    subprocess.run([*cc, *linker, *zig_cpu, '-target', 'aarch64-freestanding', '-nostdlib',
                    '-flto=thin', '-ffixed-x18', '-mgeneral-regs-only',
                    '-Wl,--entry=LZ4_decompress_safe', '-Wl,--export-dynamic', *map(str, lto),
                    str(objs[4]), '-o', str(out / 'scs.elf')], check=True)
    return elf


class Machine:
    SRC, DST, STACK, STREAM, WORK, STOP, SHADOW = (
        0x4000000, 0x5000000, 0x6000000, 0x7000000,
        0x8000000, 0x9000000, 0xa000000)
    REGION = 0x200000

    def __init__(self, elf):
        self.uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.symbols = {}
        with elf.open('rb') as f:
            e = ELFFile(f)
            pages = set()
            for seg in e.iter_segments():
                if seg['p_type'] != 'PT_LOAD':
                    continue
                start, size = seg['p_vaddr'], seg['p_memsz']
                for page in range(start & ~4095, (start + size + 4095) & ~4095, 4096):
                    if page not in pages:
                        self.uc.mem_map(page, 4096)
                        pages.add(page)
                if seg['p_filesz']:
                    self.uc.mem_write(start, seg.data())
            for sym in e.get_section_by_name('.symtab').iter_symbols():
                if sym['st_value']:
                    self.symbols[sym.name] = sym['st_value']
        for base in (self.SRC, self.DST, self.STACK, self.STREAM,
                     self.WORK, self.STOP, self.SHADOW):
            self.uc.mem_map(base, self.REGION)
        self.uc.reg_write(UC_ARM64_REG_CPACR_EL1, 3 << 20)
        self.bounds = None
        self.asm_calls = [0, 0]
        self.shadow_writes = 0
        self.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.memory)
        for name in ('_lz4_decompress_asm', '_lz4_decompress_asm_noprfm'):
            addr = self.symbols[name]
            self.uc.hook_add(UC_HOOK_CODE, self.enter, begin=addr, end=addr)

    def enter(self, uc, addr, size, data):
        if addr == self.symbols.get('_lz4_decompress_asm'):
            self.asm_calls[0] += 1
        elif addr == self.symbols.get('_lz4_decompress_asm_noprfm'):
            self.asm_calls[1] += 1

    def memory(self, uc, access, addr, size, value, data):
        if self.SHADOW <= addr < self.SHADOW + self.REGION and access == UC_MEM_WRITE:
            self.shadow_writes += 1
        if self.bounds is None:
            return
        src, insize, dst, outsize = self.bounds
        for base in (self.SRC, self.DST):
            if base <= addr < base + self.REGION:
                in_src = src <= addr and addr + size <= src + insize
                in_dst = dst <= addr and addr + size <= dst + outsize
                if not (in_dst or (in_src and access != UC_MEM_WRITE)):
                    raise AssertionError(('buffer access', access, hex(addr), size,
                                          self.bounds))

    def setvar(self, name, value):
        self.uc.mem_write(self.symbols[name], value.to_bytes(4, 'little'))

    def var(self, name):
        return int.from_bytes(self.uc.mem_read(self.symbols[name], 4), 'little')

    def call(self, name, *args):
        uc = self.uc
        uc.reg_write(UC_ARM64_REG_SP, self.STACK + self.REGION - 256)
        uc.reg_write(UC_ARM64_REG_X18, self.SHADOW + 4096)
        for i in range(11):
            uc.reg_write(getattr(arm64, 'UC_ARM64_REG_X' + str(19 + i)), 0xabcdef0000 + i)
        for i, val in enumerate(args):
            uc.reg_write(UC_ARM64_REG_X0 + i, val & ((1 << 64) - 1))
        uc.reg_write(UC_ARM64_REG_X30, self.STOP)
        uc.emu_start(self.symbols[name], self.STOP, count=10000000)
        assert uc.reg_read(UC_ARM64_REG_PC) == self.STOP, 'instruction limit reached'
        assert uc.reg_read(UC_ARM64_REG_SP) == self.STACK + self.REGION - 256
        assert uc.reg_read(UC_ARM64_REG_X18) == self.SHADOW + 4096, 'x18 clobbered'
        for i in range(11):
            assert uc.reg_read(getattr(arm64, 'UC_ARM64_REG_X' + str(19 + i))) == 0xabcdef0000 + i, i
        value = uc.reg_read(UC_ARM64_REG_X0)
        # int return values need only the lower 32 bits to be defined.
        bits = 64 if name.startswith('LZ4_arm64') else 32
        value &= (1 << bits) - 1
        return value - (1 << bits) if value >> (bits - 1) else value

    def decode(self, name, compressed, capacity, simd=1, cpu=0, dip=False,
               overlap=False, src_align=0, dst_align=0, fp=1):
        self.setvar('simd_allowed', simd)
        self.setvar('cpu_part', cpu)
        self.setvar('fpsimd_available', fp)
        self.setvar('neon_begin_count', 0)
        self.setvar('neon_end_count', 0)
        self.asm_calls = [0, 0]
        src = self.SRC + 4096 + src_align
        dst = self.DST + 4096 + dst_align
        if overlap:
            # Valid LZ4 in-place placement, leaving the documented margin.
            dst = self.SRC + 4096
            src = dst + capacity + capacity // 255 + 64 - len(compressed)
        self.uc.mem_write(dst - 64, b'\xa5' * (capacity + 128))
        self.uc.mem_write(src, compressed)
        self.bounds = (src, len(compressed), dst, capacity)
        args = [src, dst, len(compressed), capacity]
        if name.startswith('LZ4_arm64'):
            args.append(int(dip))
        elif name.endswith('_partial'):
            args.append(capacity)
        result = self.call(name, *args)
        self.bounds = None
        assert self.var('neon_begin_count') == self.var('neon_end_count')
        assert self.var('neon_begin_count') == sum(self.asm_calls)
        if not overlap:
            assert bytes(self.uc.mem_read(src, len(compressed))) == compressed, 'input modified'
        assert bytes(self.uc.mem_read(dst - 64, 64)) == b'\xa5' * 64
        if not overlap:
            assert bytes(self.uc.mem_read(dst + capacity, 64)) == b'\xa5' * 64
        return result, bytes(self.uc.mem_read(dst, max(0, result)))


def ext_length(n):
    return b'\xff' * (n // 255) + bytes([n % 255])


def literals(data):
    n = len(data)
    return bytes([min(n, 15) << 4]) + (ext_length(n - 15) if n >= 15 else b'') + data


def sequence(lit, offset, length):
    assert length >= 4
    n, m = len(lit), length - 4
    return (bytes([(min(n, 15) << 4) | min(m, 15)]) +
            (ext_length(n - 15) if n >= 15 else b'') + lit +
            offset.to_bytes(2, 'little') +
            (ext_length(m - 15) if m >= 15 else b''))


def suite(m):
    rng = random.Random(0x4c5a34)
    cases = [(literals(b''), b'')]
    for n in (1, 14, 15, 16, 127, 128, 129, 255, 1024, 4096):
        raw = rng.randbytes(n)
        cases.append((literals(raw), raw))
    # Every short-match permutation and the general-copy path, long lengths,
    # and a C tail referencing bytes produced by assembly.
    for offset in (*range(1, 65), 127, 255, 1024):
        for length in (4, 18, 19, 32, 129, 300, 4096):
            prefix = rng.randbytes(max(160, offset))
            raw = bytearray(prefix)
            for _ in range(length):
                raw.append(raw[-offset])
            tail = rng.randbytes(180)
            cases.append((sequence(prefix, offset, length) + literals(tail),
                          bytes(raw) + tail))
    # Multiple SIMD sequences followed by a tail match into the SIMD prefix.
    for count in (2, 8, 32):
        data, raw = bytearray(), bytearray()
        for i in range(count):
            lit = rng.randbytes(160)
            offset, length = rng.randrange(1, 160), rng.randrange(4, 600)
            data += sequence(lit, offset, length)
            raw += lit
            for _ in range(length):
                raw.append(raw[-offset])
        data += sequence(b'xyz', 127, 64) + literals(b'last five bytes')
        raw += b'xyz'
        for _ in range(64):
            raw.append(raw[-127])
        raw += b'last five bytes'
        cases.append((bytes(data), bytes(raw)))
    checked = 0
    asm = [0, 0]
    for data, raw in cases:
        ref = m.decode('LZ4_decompress_safe', data, len(raw))
        assert ref == (len(raw), raw)
        for cpu in (0, 0xd03):
            got = m.decode('LZ4_arm64_decompress_safe', data, len(raw), cpu=cpu,
                           src_align=checked % 16, dst_align=(checked * 7) % 16)
            assert got == ref, ('full', checked, len(data), len(raw), got[0])
            asm = [a + b for a, b in zip(asm, m.asm_calls)]
        if len(data) <= 128 or len(raw) <= 128:
            assert sum(m.asm_calls) == 0
        for cap in sorted({0, min(1, len(raw)), min(129, len(raw)),
                           len(raw) // 2, len(raw)}):
            refp = m.decode('LZ4_decompress_safe_partial', data, cap)
            got = m.decode('LZ4_arm64_decompress_safe_partial', data, cap)
            assert got == refp, ('partial', checked, cap, got[0], refp[0])
        for opts in ({'simd': 0}, {'fp': 0}, {'dip': True}, {'overlap': True}):
            got = m.decode('LZ4_arm64_decompress_safe', data, len(raw), **opts)
            assert got == ref, ('fallback', opts, checked)
            assert sum(m.asm_calls) == 0
        # Truncation and undersized output; negative error positions can differ.
        for cut in (0, 1, len(data) // 2, max(0, len(data) - 1)):
            trunc = data[:cut]
            a = m.decode('LZ4_decompress_safe', trunc, len(raw))[0]
            b = m.decode('LZ4_arm64_decompress_safe', trunc, len(raw))[0]
            assert (a < 0) == (b < 0), ('truncated', checked, cut, a, b)
        if raw:
            a = m.decode('LZ4_arm64_decompress_safe', data, len(raw) - 1)[0]
            assert a < 0
        checked += 1
    assert min(asm) > 0, 'assembly never exercised'
    # Fuzz malformed blocks. Zero-offset blocks are rejected by assembly even
    # though upstream C can accept them; accepted outputs must otherwise match.
    for _ in range(1000):
        data = rng.randbytes(rng.randrange(0, 600))
        cap = rng.randrange(0, 2048)
        a = m.decode('LZ4_decompress_safe', data, cap)
        b = m.decode('LZ4_arm64_decompress_safe', data, cap, cpu=rng.choice((0, 0xd03)))
        assert b[0] < 0 or b == a, ('malformed', a[0], b[0])
    for offset in (0, 512):
        bad = sequence(b'a' * 160, offset, 32) + literals(b'z' * 180)
        assert m.decode('LZ4_arm64_decompress_safe', bad, 1024)[0] < 0
        assert sum(m.asm_calls) == 1
    # Size_t guards must run before any pointer arithmetic or SIMD entry.
    for insize, outsize in ((1 << 31, 100), (100, 1 << 31), ((1 << 64)-1, 0)):
        assert m.call('LZ4_arm64_decompress_safe', 0, 0, insize, outsize, 0) == -5
    # Streaming first block uses ASM, subsequent prefix/dictionary blocks use C.
    data, raw = cases[-1]
    m.uc.mem_write(m.STREAM, b'\0' * 64)
    m.uc.mem_write(m.SRC, data)
    m.setvar('simd_allowed', 1)
    m.asm_calls = [0, 0]
    assert m.call('LZ4_decompress_safe_continue', m.STREAM, m.SRC, m.DST,
                  len(data), len(raw)) == len(raw)
    assert sum(m.asm_calls) == 1
    assert bytes(m.uc.mem_read(m.DST, len(raw))) == raw
    # An all-match dictionary reference followed by the required final literals.
    second = sequence(b'', 64, 256) + literals(b'hello world!')
    history = bytearray(raw)
    m.uc.mem_write(m.SRC, second)
    for dst in (m.DST + len(raw), m.DST + 65536):
        expected = bytearray(history)
        for _ in range(256):
            expected.append(expected[-64])
        expected = bytes(expected[len(history):]) + b'hello world!'
        before = sum(m.asm_calls)
        assert m.call('LZ4_decompress_safe_continue', m.STREAM, m.SRC, dst,
                      len(second), len(expected)) == len(expected)
        assert sum(m.asm_calls) == before
        assert bytes(m.uc.mem_read(dst, len(expected))) == expected
        history += expected
    # Reject negative signed stream sizes without invoking SIMD or changing state.
    for insize, outsize in ((-1, 1024), (1024, -1)):
        m.uc.mem_write(m.STREAM, b'\0' * 64)
        before = sum(m.asm_calls)
        assert m.call('LZ4_decompress_safe_continue', m.STREAM, m.SRC, m.DST,
                      insize, outsize) < 0
        assert bytes(m.uc.mem_read(m.STREAM, 64)) == b'\0' * 64
        assert sum(m.asm_calls) == before
    print('PASS:', checked, 'valid blocks, full/partial/fallback/truncation/bounds;',
          '1000 malformed blocks; ASM entries', asm, '; streaming; ABI/x18')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('CC', 'clang'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    cc = shlex.split(args.cc)
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        elf = build(cc, args.output.resolve())
        suite(Machine(elf))
        scs = Machine(elf.parent / 'scs.elf')
        suite(scs)
        assert scs.shadow_writes > 0, 'SCS instrumentation not exercised'
    else:
        with tempfile.TemporaryDirectory(prefix='lz4-arm64-') as temp:
            elf = build(cc, Path(temp))
            suite(Machine(elf))
            scs = Machine(elf.parent / 'scs.elf')
            suite(scs)
            assert scs.shadow_writes > 0, 'SCS instrumentation not exercised'


if __name__ == '__main__':
    main()
