/* SPDX-License-Identifier: GPL-2.0 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <linux/bpf.h>
typedef uint32_t u32;
typedef uint64_t u64;
typedef int16_t s16;
#define S16_MIN INT16_MIN
#define BPF_REG_AX MAX_BPF_REG
#define MAX_BPF_JIT_REG (MAX_BPF_REG + 1)
#define BUILD_BUG_ON(x) _Static_assert(!(x), #x)
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define IS_ERR(x) ((uintptr_t)(x) >= (uintptr_t)-4095)
#define ERR_CAST(x) ((void *)(x))
#define GFP_USER 0
#define __init
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
static u32 get_random_int(void) { return 0x12345678; }
struct bpf_prog_aux { bool verifier_zext; u32 max_tp_access; };
struct bpf_prog {
	int len, blinded;
	struct bpf_prog_aux *aux;
	struct bpf_insn insnsi[4];
};
static int patches, releases;
static bool enabled = true;
static bool bpf_jit_blinding_enabled(struct bpf_prog *p) { return enabled; }
static struct bpf_prog *bpf_prog_clone_create(struct bpf_prog *p, int flags)
{
	struct bpf_prog *copy = malloc(sizeof(*copy));
	assert(copy);
	memcpy(copy, p, sizeof(*copy));
	return copy;
}
static void bpf_jit_prog_release_other(struct bpf_prog *p, struct bpf_prog *copy)
{
	releases++;
	free(copy);
}
static struct bpf_prog *bpf_patch_insn_single(struct bpf_prog *p, int i,
					  struct bpf_insn *insns, int count)
{
	patches++;
	assert(count > 0); /* No negative patch length may reach this function. */
	return ERR_PTR(-ENOMEM); /* Exercise the existing patch-failure path. */
}
static bool bpf_lsm_initialized;
static int bpf_lsm_hooks[1];
static int hooks_added;
static void security_add_hooks(int *hooks, size_t count, const char *name)
{
	hooks_added++;
}
#define pr_info(...) ((void)0)
struct bpf_map { int dummy; };
struct bpf_local_storage_map { struct bpf_map map; int cache_idx; };
static struct bpf_local_storage_map storage;
static int allocations, cache_gets, inode_cache;
static bool alloc_fail;
static struct bpf_local_storage_map *bpf_local_storage_map_alloc(union bpf_attr *attr)
{
	allocations++;
	return alloc_fail ? ERR_PTR(-ENOMEM) : &storage;
}
static int bpf_local_storage_cache_idx_get(int *cache) { cache_gets++; return 7; }
struct tnum { u64 value, mask; };
struct bpf_reg_state { struct tnum var_off; };
struct bpf_verifier_env { struct bpf_prog *prog; };
static bool tnum_is_const(struct tnum t) { return !t.mask; }
static void tnum_strn(char *buf, size_t size, struct tnum t) { buf[0] = 0; }
#define verbose(...) ((void)0)

/* EXTRACTED */

static void test_blinding(void)
{
	int ops[] = { BPF_JEQ, BPF_JNE, BPF_JGT, BPF_JLT, BPF_JGE, BPF_JLE,
		BPF_JSGT, BPF_JSLT, BPF_JSGE, BPF_JSLE, BPF_JSET };
	struct bpf_insn aux[2] = {0}, out[16];
	/* Every signed-16-bit offset, every immediate condition, both widths. */
	for (int width = 0; width < 2; width++) {
		for (size_t op = 0; op < ARRAY_SIZE(ops); op++) {
			for (int off = INT16_MIN; off <= INT16_MAX; off++) {
				struct bpf_insn in = { .code = (width ? BPF_JMP32 : BPF_JMP) | ops[op],
					.dst_reg = BPF_REG_1, .off = off, .imm = 42 };
				memset(out, 0, sizeof(out));
				int n = bpf_jit_blind_insn(&in, aux, out, false);
				if (off < INT16_MIN + 2) {
					assert(n == -ERANGE);
					assert(out[0].code == 0);
				} else {
					assert(n == 3);
					assert(out[2].off == (off < 0 ? off - 2 : off));
					assert(out[2].src_reg == BPF_REG_AX);
				}
			}
		}
	}
	struct bpf_prog_aux pa = {0};
	struct bpf_prog p = { .len = 1, .aux = &pa };
	for (int width = 0; width < 2; width++) {
		p.insnsi[0] = (struct bpf_insn) { .code = (width ? BPF_JMP32 : BPF_JMP) | BPF_JEQ,
			.dst_reg = BPF_REG_1, .off = INT16_MIN, .imm = 42 };
		int old = releases;
		assert(bpf_jit_blind_constants(&p) == ERR_PTR(-ERANGE));
		assert(releases == old + 1 && patches == 0 && !p.blinded);
	}
	p.insnsi[0].off = -1;
	assert(bpf_jit_blind_constants(&p) == ERR_PTR(-ENOMEM));
	assert(patches == 1 && releases == 3);
	enabled = false;
	assert(bpf_jit_blind_constants(&p) == &p);
}

static void test_inode(void)
{
	union bpf_attr attr = {0};
	assert(inode_storage_map_alloc(&attr) == ERR_PTR(-EOPNOTSUPP));
	assert(!allocations && !cache_gets);
	assert(bpf_lsm_init() == 0 && hooks_added == 1);
	assert(inode_storage_map_alloc(&attr) == &storage.map);
	assert(allocations == 1 && cache_gets == 1 && storage.cache_idx == 7);
	alloc_fail = true;
	assert(inode_storage_map_alloc(&attr) == ERR_PTR(-ENOMEM));
	assert(allocations == 2 && cache_gets == 1);
}

static void test_buffers(void)
{
	struct bpf_prog_aux aux = {0};
	struct bpf_prog p = { .aux = &aux };
	struct bpf_verifier_env env = { .prog = &p };
	struct bpf_reg_state reg = {0};
	u64 values[] = { (u64)-8, (u64)-1, 1, 8, 0 };
	for (size_t i = 0; i < ARRAY_SIZE(values); i++) {
		reg.var_off.value = values[i];
		reg.var_off.mask = i == 4 ? 8 : 0;
		for (int off = -8; off <= 8; off += 8) {
			u32 end = 123;
			aux.max_tp_access = 123;
			assert(check_tp_buffer_access(&env, &reg, 1, off, 8) == -EACCES);
			assert(aux.max_tp_access == 123);
			assert(check_buffer_access(&env, &reg, 1, off, 8, false, "rdwr", &end) == -EACCES);
			assert(end == 123);
		}
	}
	reg.var_off = (struct tnum){0};
	aux.max_tp_access = 0;
	u32 end = 0;
	assert(check_tp_buffer_access(&env, &reg, 1, 8, 8) == 0);
	assert(aux.max_tp_access == 16);
	assert(check_buffer_access(&env, &reg, 1, 8, 8, false, "rdonly", &end) == 0);
	assert(end == 16);
}
int main(void)
{
	test_blinding();
	test_inode();
	test_buffers();
	puts("PASS: 1,441,792 jump cases; error cleanup, inode initialization, buffer-offset rejection");
	return 0;
}
