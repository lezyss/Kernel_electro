// SPDX-License-Identifier: GPL-2.0
/*
 * Sparse, single-threaded iterator model for the extracted production cleanup.
 * Tests range arithmetic/entry selection, not real radix-tree locking or RCU.
 */
#undef NDEBUG
#include <assert.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define __rcu
#define SWAP_ADDRESS_SPACE_SHIFT 14
#define SWAP_ADDRESS_SPACE_PAGES (1UL << SWAP_ADDRESS_SPACE_SHIFT)
#define min(a, b) ((a) < (b) ? (a) : (b))
#define NSLOTS 64
#define NSPACES 8

struct slot {
	unsigned long index;
	void *value;
};
struct radix_tree_root {
	struct slot slots[NSLOTS];
	unsigned int nr;
};
struct address_space {
	int tree_lock;
	struct radix_tree_root page_tree;
};
struct radix_tree_iter {
	unsigned long index, next_index;
};
typedef struct { unsigned long offset; } swp_entry_t;
static struct address_space spaces[NSPACES];
static unsigned long lower, upper;
static unsigned int cases;
static int lock_depth;

static swp_entry_t swp_entry(int type, unsigned long offset)
{
	assert(type == 0);
	return (swp_entry_t) { offset };
}
static struct address_space *swap_address_space(swp_entry_t entry)
{
	return &spaces[(entry.offset >> SWAP_ADDRESS_SPACE_SHIFT) % NSPACES];
}
static void spin_lock_irq(int *lock)
{
	(void)lock;
	assert(!lock_depth++);
}
static void spin_unlock_irq(int *lock)
{
	(void)lock;
	assert(lock_depth-- == 1);
}
static void **next_slot(struct radix_tree_root *root,
		       struct radix_tree_iter *iter, unsigned long start)
{
	struct slot *best = NULL;
	unsigned int i;

	for (i = 0; i < root->nr; i++) {
		struct slot *s = &root->slots[i];

		if (s->value && s->index >= start &&
		    (!best || s->index < best->index))
			best = s;
	}
	if (!best)
		return NULL;
	iter->index = best->index;
	/* Like radix-tree: one past the chunk, not this entry. */
	iter->next_index = (best->index | 63UL) + 1;
	return &best->value;
}
#define radix_tree_for_each_slot(slot, root, iter, start) \
	for ((slot) = next_slot(root, iter, start); (slot); \
	     (slot) = (iter)->index == ULONG_MAX ? NULL : \
		      next_slot(root, iter, (iter)->index + 1))
#define radix_tree_deref_slot_protected(slot, lock) (*(slot))
#define radix_tree_exceptional_entry(item) ((uintptr_t)(item) & 1)
static void radix_tree_iter_delete(struct radix_tree_root *root,
				  struct radix_tree_iter *iter, void **slot)
{
	(void)root;
	assert(lock_depth == 1);
	assert(iter->index >= lower && iter->index <= upper);
	*slot = NULL;
}

/* PRODUCTION_CLEANUP */

static void check(unsigned long begin, unsigned long end,
		  const unsigned long *indices, unsigned int nr)
{
	unsigned int i, j;

	assert(nr <= NSLOTS);
	memset(spaces, 0, sizeof(spaces));
	lower = begin;
	upper = end;
	for (i = 0; i < nr; i++) {
		struct radix_tree_root *root =
			&swap_address_space(swp_entry(0, indices[i]))->page_tree;
		struct slot *s = &root->slots[root->nr++];

		s->index = indices[i];
		/* Include real-page sentinels: these must never be deleted. */
		s->value = (void *)(uintptr_t)(i % 3 == 0 ? 2 : 1);
	}
	clear_shadow_from_swap_cache(0, begin, end);
	assert(!lock_depth);
	for (i = 0; i < NSPACES; i++) {
		struct radix_tree_root *root = &spaces[i].page_tree;

		for (j = 0; j < root->nr; j++) {
			struct slot *s = &root->slots[j];
			bool in_range = begin <= end && s->index >= begin &&
					s->index <= end;

			if (s->value != (void *)2)
				assert((s->value == NULL) == in_range);
		}
	}
	cases++;
}

static uint32_t state = 1234567;
static uint32_t random32(void)
{
	state ^= state << 13;
	state ^= state >> 17;
	state ^= state << 5;
	return state;
}
int main(void)
{
	unsigned long indices[NSLOTS];
	unsigned int i, n;
	const unsigned long dense[] = {62, 63, 64, 65, 66, 126, 127, 128};
	const unsigned long hole[] = {1, 70, 71, 129};
	const unsigned long boundary[] = {16382, 16383, 16384, 16385, 16400};
	const unsigned long highest[] = {ULONG_MAX - 3, ULONG_MAX - 2,
					 ULONG_MAX - 1, ULONG_MAX};

	check(63, 127, dense, 8);
	check(64, 65, hole, 4);
	check(16383, 16385, boundary, 5);
	check(ULONG_MAX - 2, ULONG_MAX, highest, 4);
	check(127, 63, dense, 8);
	check(0, 0, NULL, 0);
	for (n = 0; n < 2000; n++) {
		unsigned long a = random32() % (4 * SWAP_ADDRESS_SPACE_PAGES);
		unsigned long b = random32() % (4 * SWAP_ADDRESS_SPACE_PAGES);

		for (i = 0; i < NSLOTS; i++) {
			unsigned int j;

			do {
				indices[i] = random32() % (4 * SWAP_ADDRESS_SPACE_PAGES);
				for (j = 0; j < i; j++)
					if (indices[j] == indices[i])
						break;
			} while (j != i);
		}
		check(min(a, b), a > b ? a : b, indices, NSLOTS);
	}
	printf("Shadow cleanup range model: PASS (%u cases)\n", cases);
	return 0;
}
