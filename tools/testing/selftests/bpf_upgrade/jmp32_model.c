// SPDX-License-Identifier: GPL-2.0
/* Actual JIT jump cases + actual arm64 encoders; independent bounded decoder. */
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <linux/bpf.h>
#include "bpf_jit.h"
#define __kprobes
#define BIT(n) (1U << (n))
#define GENMASK(h, l) ((~0U << (l)) & (~0U >> (31 - (h))))
#define SZ_2M (2UL * 1024 * 1024)
#define SZ_1M (1024UL * 1024)
#define SZ_64K 65536
#define SZ_32 32
#define SZ_64 64
#define AARCH64_BREAK_FAULT 0xd4200000U
#define AARCH64_INSN_SF_BIT BIT(31)
#define ADR_IMM_HILOSPLIT 2
#define ADR_IMM_LOMASK 3
#define ADR_IMM_SIZE SZ_2M
#define ADR_IMM_HIMASK ((ADR_IMM_SIZE >> 2) - 1)
#define ADR_IMM_LOSHIFT 29
#define ADR_IMM_HISHIFT 5
#define pr_err(...) ((void)0)
#define pr_info(...) ((void)0)
#define cpu_to_le32(x) (x)
struct bpf_prog { struct bpf_insn insnsi[5]; };
struct jit_ctx {
    const struct bpf_prog *prog;
    int idx;
    int *offset;
    __le32 *image;
};
/* EXTRACTED */

static bool bpf_reference(unsigned op, bool wide, uint64_t a, uint64_t b)
{
    if (!wide) { a = (uint32_t)a; b = (uint32_t)b; }
    int64_t sa = wide ? (int64_t)a : (int32_t)a;
    int64_t sb = wide ? (int64_t)b : (int32_t)b;
    switch (op) {
    case BPF_JEQ: return a == b;
    case BPF_JNE: return a != b;
    case BPF_JGT: return a > b;
    case BPF_JGE: return a >= b;
    case BPF_JLT: return a < b;
    case BPF_JLE: return a <= b;
    case BPF_JSET: return (a & b) != 0;
    case BPF_JSGT: return sa > sb;
    case BPF_JSGE: return sa >= sb;
    case BPF_JSLT: return sa < sb;
    case BPF_JSLE: return sa <= sb;
    default: assert(0); return false;
    }
}

static bool condition(unsigned cond, bool n, bool z, bool c, bool v)
{
    switch (cond) {
    case 0: return z;
    case 1: return !z;
    case 2: return c;
    case 3: return !c;
    case 8: return c && !z;
    case 9: return !c || z;
    case 10: return n == v;
    case 11: return n != v;
    case 12: return !z && n == v;
    case 13: return z || n != v;
    default: assert(0); return false;
    }
}

/* This decoder intentionally does not call the encoder, BPF opcode dispatch,
 * or kernel condition helpers. It recognizes only the emitted instruction set. */
static bool decode(const u32 *image, unsigned begin, unsigned end,
                   uint64_t a, uint64_t b, int expected_target, bool expected_width)
{
    uint64_t regs[32] = { 0 };
    bool n = false, z = false, c = false, v = false, compared = false;
    regs[7] = a; regs[0] = b;
    for (unsigned pc = begin; pc < end; pc++) {
        uint32_t w = image[pc], base = w & 0x7f800000U;
        bool wide = w >> 31;
        uint64_t mask = wide ? UINT64_MAX : UINT32_MAX;
        unsigned rd = w & 31, rn = (w >> 5) & 31, rm = (w >> 16) & 31;
        if (base == 0x12800000U || base == 0x52800000U || base == 0x72800000U) {
            unsigned shift = ((w >> 21) & 3) * 16;
            uint64_t imm = (uint64_t)((w >> 5) & 0xffff) << shift;
            assert(wide == expected_width && rd == 10);
            if (base == 0x12800000U) regs[rd] = ~imm & mask;
            else if (base == 0x52800000U) regs[rd] = imm;
            else regs[rd] = (regs[rd] & ~(0xffffULL << shift)) | imm;
            regs[rd] &= mask;
        } else if ((w & 0x7fe0fc1fU) == 0x6b00001fU ||
                   (w & 0x7fe0fc1fU) == 0x6a00001fU) {
            uint64_t x = regs[rn] & mask, y = regs[rm] & mask, result;
            uint64_t sign = 1ULL << (wide ? 63 : 31);
            assert(wide == expected_width && !compared);
            if ((w & 0x7f000000U) == 0x6b000000U) {
                result = (x - y) & mask;
                c = x >= y;
                v = !!((x ^ y) & (x ^ result) & sign);
            } else {
                result = x & y; c = v = false;
            }
            n = !!(result & sign); z = result == 0; compared = true;
        } else if ((w & 0xff000010U) == 0x54000000U) {
            int32_t relative = (int32_t)((w >> 5) & 0x7ffff);
            if (relative & 0x40000) relative -= 0x80000;
            assert(compared && pc + 1 == end);
            assert((int)pc + relative == expected_target);
            return condition(w & 15, n, z, c, v);
        } else { assert(!"unrecognized generated instruction"); }
    }
    assert(!"missing conditional branch");
    return false;
}

static unsigned long cases;
static void check(unsigned op, bool wide, bool immediate, uint64_t a, uint64_t b, int off)
{
    struct bpf_prog prog = { 0 };
    struct bpf_insn *insn = &prog.insnsi[2];
    insn->code = (wide ? BPF_JMP : BPF_JMP32) | op | (immediate ? BPF_K : BPF_X);
    insn->dst_reg = 7; insn->src_reg = 0;
    insn->off = off; insn->imm = (int32_t)b;
    int offsets[5] = { 0, 4, 16, 24, 32 };
    struct jit_ctx ctx = { .prog = &prog, .idx = 8, .offset = offsets };
    assert(emit_jump(insn, &ctx) == 0);
    unsigned end = ctx.idx;
    assert(end <= 12);
    offsets[2] = end;
    u32 image[40] = { 0 };
    ctx.idx = 8; ctx.image = image;
    assert(emit_jump(insn, &ctx) == 0 && ctx.idx == (int)end);
    uint64_t operand = immediate ? (uint64_t)(int64_t)insn->imm : b;
    assert(decode(image, 8, end, a, b, offsets[2 + off], wide) ==
           bpf_reference(op, wide, a, operand));
    assert(image[7] == 0 && image[end] == 0);
    cases++;
}

static uint64_t seed = 0x149357;
static uint64_t random_value(void)
{ seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17; return seed; }
int main(void)
{
    for (unsigned code = 0; code < 256; code++) {
        if ((code & 7) == 4) assert(!select_width(code));
        if ((code & 7) == 7) assert(select_width(code));
    }
    const unsigned ops[] = { BPF_JEQ, BPF_JNE, BPF_JGT, BPF_JGE, BPF_JLT, BPF_JLE,
                             BPF_JSET, BPF_JSGT, BPF_JSGE, BPF_JSLT, BPF_JSLE };
    const uint64_t values[] = { 0, 1, UINT32_MAX, 0x80000000U, 0x7fffffffU,
        0x100000000ULL, 0x100000001ULL, 0xffffffff00000000ULL,
        UINT64_MAX, INT64_MAX, 0x8000000000000000ULL, 0x80000000ffffffffULL,
        0xffff8000U, 0x12345678U };
    const int offsets[] = { -2, -1, 0, 1, 2 };
    for (unsigned op = 0; op < sizeof(ops) / sizeof(*ops); op++)
        for (unsigned wide = 0; wide < 2; wide++)
            for (unsigned imm = 0; imm < 2; imm++) {
                for (unsigned a = 0; a < sizeof(values) / sizeof(*values); a++)
                    for (unsigned b = 0; b < sizeof(values) / sizeof(*values); b++)
                        for (unsigned off = 0; off < sizeof(offsets) / sizeof(*offsets); off++)
                            check(ops[op], wide, imm, values[a], values[b], offsets[off]);
                for (unsigned n = 0; n < 20000; n++) {
                    uint64_t a = random_value(), b = random_value();
                    int off = offsets[random_value() % 5];
                    check(ops[op], wide, imm, a, b, off);
                }
            }
    printf("PASS: %lu generated-code cases; 22 JMP32 + 22 JMP forms; signed/unsigned/JSET, immediates, high halves, dry/emission passes and forward/backward targets\n", cases);
    return 0;
}
