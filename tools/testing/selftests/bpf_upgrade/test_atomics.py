#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Actual ARM64 atomic emitters/encoders with an independent bounded decoder."""
import argparse
from pathlib import Path
import resource
import subprocess
import tempfile
from test_jmp32 import ROOT, HERE, function, once


def source(negative=None):
    jit = (ROOT / 'arch/arm64/net/bpf_jit_comp.c').read_text()
    enc = (ROOT / 'arch/arm64/kernel/insn.c').read_text()
    body = function(jit, 'static int build_insn(')
    cases = body[body.index('\tcase BPF_STX | BPF_ATOMIC | BPF_W:'):body.index('\n\t/* R0 = ntohx')]
    if negative == 'address-alias':
        cases = once(cases, 'reg = tmp;', 'reg = off ? tmp : dst;')
    elif negative == 'cmp-failure-barrier':
        cases = once(cases, 'jmp_offset = 3;', 'jmp_offset = 4;')
    elif negative == 'fetch-operand':
        cases = cases.replace('A64_MOV(isdw, ax, src)', 'A64_MOV(isdw, ax, tmp3)')
    pieces = [function(enc, sig) for sig in (
        'static int __kprobes aarch64_get_imm_shift_mask(',
        'u32 __kprobes aarch64_insn_encode_immediate(',
        'static u32 aarch64_insn_encode_register(',
        'static inline long branch_imm_common(',
        'u32 aarch64_insn_gen_comp_branch_imm(',
        'u32 aarch64_insn_gen_movewide(',
        'u32 aarch64_insn_gen_add_sub_shifted_reg(',
        'u32 aarch64_insn_gen_add_sub_imm(',
        'u32 aarch64_insn_gen_logical_shifted_reg(',
        'static u32 aarch64_insn_encode_ldst_size(',
        'u32 aarch64_insn_gen_load_store_ex(',
        'u32 aarch64_insn_gen_ldadd(', 'u32 aarch64_insn_gen_stadd(')]
    pieces += [function(jit, 'static inline void emit('), function(jit, 'static inline void emit_a64_mov_i(')]
    prefix = (HERE / 'jmp32_model.c').read_text().split('/* EXTRACTED */')[0]
    prefix = prefix.replace('#define SZ_1M (1024UL * 1024)', '#define SZ_1M 0x00100000')
    prefix += '\n#define SZ_4K 0x1000\n#define BPF_REG_FP BPF_REG_10\n#define pr_err_once(...) ((void)0)\n#define BPF_REG_AX 11\n#define MAX_BPF_JIT_REG 12\n'
    prefix += jit[jit.index('#define TMP_REG_1'):jit.index('/* Map BPF registers')]
    prefix += function(jit, 'static const int bpf2a64[] =') + ';\n'
    prefix += 'static bool lse;\n#define ARM64_HAS_LSE_ATOMICS 1\n#define cpus_have_cap(x) lse\n'
    checks = body[body.index('#define check_imm('):body.index('\n\tswitch (code)')]
    builder = '''static int build_atomic(const struct bpf_insn *insn, struct jit_ctx *ctx)
{
 const u8 code=insn->code, dst=bpf2a64[insn->dst_reg], src=bpf2a64[insn->src_reg];
 const u8 tmp=bpf2a64[TMP_REG_1],tmp2=bpf2a64[TMP_REG_2],tmp3=bpf2a64[TMP_REG_3];
 const bool isdw=BPF_SIZE(code)==BPF_DW;
 const s16 off=insn->off; const s32 imm=insn->imm;
 u8 reg; s32 jmp_offset;
''' + checks + '\n switch(code) {\n' + cases + '\n default:return -EINVAL;\n } return 0;\n}\n'
    return prefix + '\n'.join(pieces) + builder + (HERE / 'atomic_model.c').read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asan', action='store_true')
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='bpf-atomics-') as tmp:
        directory = Path(tmp)
        (directory / 'asm').mkdir(); (directory / 'linux').mkdir()
        for dest, src in [('asm/insn.h', 'arch/arm64/include/asm/insn.h'), ('bpf_jit.h', 'arch/arm64/net/bpf_jit.h'),
                          ('linux/bpf.h', 'include/uapi/linux/bpf.h'), ('linux/bpf_common.h', 'include/uapi/linux/bpf_common.h')]:
            (directory / dest).write_text((ROOT / src).read_text())
        (directory / 'linux/types.h').write_text('''#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef uint8_t u8,__u8;typedef uint16_t u16,__u16,__be16;
typedef uint32_t u32,__u32,__be32,__wsum,__le32;
typedef uint64_t u64,__u64;typedef int16_t s16,__s16;typedef int32_t s32,__s32;typedef int64_t s64,__s64;
#define __aligned_u64 uint64_t __attribute__((aligned(8)))
''')
        flags = ['gcc', '-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-fno-pie', '-no-pie',
                 '-fsanitize=' + ('address,undefined' if args.asan else 'undefined'), '-fno-sanitize-recover=all', '-I'+tmp]
        for negative in [None] + (['address-alias', 'cmp-failure-barrier', 'fetch-operand'] if args.self_test_negatives else []):
            c = directory / 'test.c'; binary = directory / 'test'
            c.write_text(source(negative))
            subprocess.run(flags + [str(c), '-o', str(binary)], check=True)
            r = subprocess.run([str(binary)], capture_output=True, text=True,
                               preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            if negative:
                assert r.returncode and 'Assertion' in r.stderr, (negative, r.stderr)
                print('PASS: rejected '+negative, flush=True)
            else:
                assert r.returncode == 0, r.stderr
                print(r.stdout.strip(), flush=True)


if __name__ == '__main__':
    main()
