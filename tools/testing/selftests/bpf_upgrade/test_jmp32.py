#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Stage-A host checks: current ARM64 jump cases and real instruction encoders."""
import argparse
import os
from pathlib import Path
import re
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
NEGATIVES = ('missing-jmp32', 'all-64-bit', 'all-32-bit', 'cmp-width',
             'test-width', 'immediate-width', 'wrong-condition', 'branch-offset')


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def source(negative=None):
    jit = (ROOT / 'arch/arm64/net/bpf_jit_comp.c').read_text()
    enc = (ROOT / 'arch/arm64/kernel/insn.c').read_text()
    code = function(jit, 'static int build_insn(')
    width = re.search(r'const bool is64 = .*?;', code, re.S).group(0)
    cases = code[code.index('\t/* IF (dst COND src)'):code.index('\t/* function call */')]
    assert cases.count('case BPF_JMP32 |') == 22
    checks = code[code.index('#define check_imm('):code.index('\n\tswitch (code)')]
    pieces = []
    # Use real encoder implementations, not mocked machine-code constructors.
    pieces += [function(enc, sig) for sig in (
        'static int __kprobes aarch64_get_imm_shift_mask(',
        'u32 __kprobes aarch64_insn_encode_immediate(',
        'static u32 aarch64_insn_encode_register(',
        'static inline long branch_imm_common(',
        'u32 aarch64_insn_gen_cond_branch_imm(',
        'u32 aarch64_insn_gen_movewide(',
        'u32 aarch64_insn_gen_add_sub_shifted_reg(',
        'u32 aarch64_insn_gen_logical_shifted_reg(')]
    pieces += [function(jit, sig) for sig in (
        'static inline void emit(', 'static inline void emit_a64_mov_i(',
        'static inline int bpf2a64_offset(')]
    if negative == 'missing-jmp32':
        cases = re.sub(r'^\s*case BPF_JMP32 \|[^\n]*\n', '\n', cases, flags=re.M)
    elif negative == 'all-64-bit':
        width = 'const bool is64 = true;'
    elif negative == 'all-32-bit':
        width = 'const bool is64 = false;'
    elif negative == 'cmp-width':
        cases = cases.replace('A64_CMP(is64,', 'A64_CMP(1,')
    elif negative == 'test-width':
        cases = cases.replace('A64_TST(is64,', 'A64_TST(1,')
    elif negative == 'immediate-width':
        cases = cases.replace('emit_a64_mov_i(is64,', 'emit_a64_mov_i(!is64,')
    elif negative == 'wrong-condition':
        cases = once(cases, 'jmp_cond = A64_COND_LT;', 'jmp_cond = A64_COND_CC;')
    elif negative == 'branch-offset':
        cases = once(cases, 'bpf2a64_offset(i + off, i, ctx)',
                     'bpf2a64_offset(i + off, i, ctx) + 1')
    jump = '''static int emit_jump(const struct bpf_insn *insn, struct jit_ctx *ctx)
{
    const u8 code = insn->code, dst = insn->dst_reg, src = insn->src_reg;
    const u8 tmp = 10;
    const s16 off = insn->off;
    const s32 imm = insn->imm;
    const int i = insn - ctx->prog->insnsi;
    u8 jmp_cond;
    s32 jmp_offset;
''' + width + '\n' + checks + '\n switch (code) {\n' + cases + '''
    default: return -EINVAL;
    }
    return 0;
}
'''
    width_helper = 'static bool select_width(u8 code) { (void)code; ' + width + ' return is64; }\n'
    return (HERE / 'jmp32_model.c').read_text().replace('/* EXTRACTED */', '\n'.join(pieces) + '\n' + width_helper + jump)


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--asan', action='store_true')
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    cc = shlex.split(args.cc)
    flags = ['-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-UNDEBUG',
             '-fno-pie', '-no-pie', '-fsanitize=' + ('address,undefined' if args.asan else 'undefined'),
             '-fno-sanitize-recover=all']
    with tempfile.TemporaryDirectory(prefix='bpf-jmp32-') as directory:
        directory = Path(directory)
        for p in ('linux', 'asm'):
            (directory / p).mkdir()
        for dest, src in [('asm/insn.h', 'arch/arm64/include/asm/insn.h'),
                          ('bpf_jit.h', 'arch/arm64/net/bpf_jit.h'),
                          ('linux/bpf.h', 'include/uapi/linux/bpf.h'),
                          ('linux/bpf_common.h', 'include/uapi/linux/bpf_common.h')]:
            (directory / dest).write_text((ROOT / src).read_text())
        (directory / 'linux/types.h').write_text('''#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef uint8_t u8, __u8;
typedef uint16_t u16, __u16, __be16;
typedef uint32_t u32, __u32, __be32, __wsum, __le32;
typedef uint64_t u64, __u64;
typedef int16_t s16, __s16;
typedef int32_t s32, __s32;
typedef int64_t s64, __s64;
#define __aligned_u64 uint64_t __attribute__((aligned(8)))
''')
        flags += ['-I' + str(directory)]
        probe = directory / 'probe.c'
        probe.write_text('int main(void) { volatile int x=2147483647; volatile int y=x+1; return y; }\n')
        binary = directory / 'probe'
        subprocess.run(cc + flags + [str(probe), '-o', str(binary)], check=True)
        result = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
        assert result.returncode and b'runtime error' in result.stderr
        if args.asan:
            probe.write_text('#include <stdlib.h>\n__attribute__((noinline)) void f(volatile int *p,int n){p[n]=1;}\nint main(int n,char **v){(void)v;int *p=malloc(4);f(p,n);free(p);return 0;}\n')
            subprocess.run(cc + flags + [str(probe), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
            assert result.returncode and b'AddressSanitizer' in result.stderr
        print('PASS: requested sanitizer runtime probes', flush=True)
        for negative in [None] + (list(NEGATIVES) if args.self_test_negatives else []):
            path = directory / ((negative or 'current') + '.c')
            path.write_text(source(negative))
            binary = path.with_suffix('')
            subprocess.run(cc + flags + [str(path), '-o', str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, preexec_fn=no_core)
            if negative:
                assert result.returncode != 0 and 'Assertion' in result.stderr, (negative, result.stdout, result.stderr)
                print('PASS: rejected ' + negative, flush=True)
            else:
                assert result.returncode == 0, result.stderr
                print(result.stdout.strip(), flush=True)


if __name__ == '__main__':
    main()
