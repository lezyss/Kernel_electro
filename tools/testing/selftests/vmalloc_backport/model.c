/* SPDX-License-Identifier: GPL-2.0 */
/* Production code is inserted by test_backport.py. Single-threaded mocks. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <errno.h>
#include <setjmp.h>
#undef __always_inline
#define __always_inline inline
#define __init
#define __acquires(x)
#define __releases(x)
#define likely(x) (x)
#define unlikely(x) (x)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, v) ((x) = (v))
#define rcu_assign_pointer(x, v) ((x) = (v))
#define smp_wmb()                                                              \
	do {                                                                   \
	} while (0)
#define EXPORT_SYMBOL(x)
#define EXPORT_SYMBOL_GPL(x)
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define min(a, b)                                                              \
	({                                                                     \
		__auto_type _a = (a);                                          \
		__auto_type _b = (b);                                          \
		_a < _b ? _a : _b;                                             \
	})
#define max(a, b)                                                              \
	({                                                                     \
		__auto_type _a = (a);                                          \
		__auto_type _b = (b);                                          \
		_a > _b ? _a : _b;                                             \
	})
#define max3(a, b, c) max(max(a, b), c)
#define ALIGN(x, a) (((x) + (a) - 1) & ~((a) - 1))
#define IS_ALIGNED(x, a) (!((x) & ((a) - 1)))
#define BUG() assert(!"BUG")
#define BUG_ON(x) assert(!(x))
#define WARN_ON(x) (!!(x))
#define WARN_ON_ONCE(x) (!!(x))
#define PAGE_SHIFT 12
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define offset_in_page(x) ((x) & (PAGE_SIZE - 1))
#define is_power_of_2(x) ((x) && !((x) & ((x) - 1)))
#define VMALLOC_START 0x100000UL
#define NPAGES 1024
#define VMALLOC_END (VMALLOC_START + NPAGES * PAGE_SIZE)
#define GFP_NOWAIT 0U
#define GFP_KERNEL 7U
#define GFP_RECLAIM_MASK 7U
#define __GFP_NOWARN 8U
#define SLAB_PANIC 0
#define GFP_ATOMIC 0
#define VM_ALLOC 1UL
#define VM_IOREMAP 2UL
#define VM_MAP 4UL
#define VM_USERMAP 8UL
#define VM_LOWMEM 16UL
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define IS_ERR(x) ((uintptr_t)(x) >= (uintptr_t)-4095)
#define pr_warn(...)                                                           \
	do {                                                                   \
	} while (0)
#define loff_t long long
typedef unsigned gfp_t;
/* PRODUCTION_RB */
struct list_head {
	struct list_head *next, *prev;
};
struct hlist_node {
	struct hlist_node *next, **pprev;
};
struct hlist_head {
	struct hlist_node *first;
};
#define LIST_POISON1 ((void *)0x100)
#define LIST_POISON2 ((void *)0x200)
/* PRODUCTION_LIST */
struct llist_node {
	struct llist_node *next;
};
struct llist_head {
	struct llist_node *first;
};
static void init_llist_head(struct llist_head *h)
{
	h->first = NULL;
}
static void llist_add(struct llist_node *n, struct llist_head *h)
{
	n->next = h->first;
	h->first = n;
}
static struct llist_node *llist_del_all(struct llist_head *h)
{
	struct llist_node *n = h->first;
	h->first = NULL;
	return n;
}
#define ll_entry(n, m) ((n) ? container_of(n, struct vmap_area, m) : NULL)
#define llist_for_each_entry(p, n, m)                                          \
	for ((p) = ll_entry(n, m); (p); (p) = ll_entry((p)->m.next, m))
#define llist_for_each_entry_safe(p, q, n, m)                                  \
	for ((p) = ll_entry(n, m); (p) && ((q) = ll_entry((p)->m.next, m), 1); \
	     (p) = (q))
struct vm_struct {
	struct vm_struct *next;
	void *addr;
	unsigned long size, flags, nr_pages, phys_addr;
	const void *caller;
	void *pages;
};
/* PRODUCTION_LAYOUT */
_Static_assert(sizeof(struct vmap_area) == 8 * sizeof(unsigned long), "layout");
struct lock {
	bool held;
};
static struct lock vmap_area_lock, free_vmap_area_lock, vmap_purge_lock;
static void spin_lock(struct lock *l)
{
	assert(!l->held);
	l->held = true;
}
static void spin_unlock(struct lock *l)
{
	assert(l->held);
	l->held = false;
}
static void mutex_lock(struct lock *l)
{
	assert(!l->held);
	l->held = true;
}
static bool mutex_trylock(struct lock *l)
{
	if (l->held)
		return false;
	l->held = true;
	return true;
}
static void mutex_unlock(struct lock *l)
{
	assert(!vmap_area_lock.held && !free_vmap_area_lock.held);
	assert(l->held);
	l->held = false;
}
#define lockdep_assert_held(l) assert((l)->held)
static void cond_resched_lock(struct lock *l)
{
	assert(l->held);
}
static struct rb_root vmap_area_root = RB_ROOT, free_vmap_area_root = RB_ROOT;
static LIST_HEAD(vmap_area_list);
static LIST_HEAD(free_vmap_area_list);
static struct llist_head vmap_purge_list;
static bool vmap_initialized;
struct kmem_cache {
	int unused;
};
static struct kmem_cache cache, *vmap_area_cachep = &cache;
static struct vmap_area *ne_fit_preload_node[2];
static int current_cpu;
static struct vmap_area *exchange(struct vmap_area **p, struct vmap_area *v)
{
	struct vmap_area *o = *p;
	*p = v;
	return o;
}
static struct vmap_area *
compare_exchange(struct vmap_area **p, struct vmap_area *o, struct vmap_area *v)
{
	struct vmap_area *prev = *p;
	if (prev == o)
		*p = v;
	return prev;
}
#define this_cpu_read(v) ((v)[current_cpu])
#define __this_cpu_xchg(v, n) exchange(&(v)[current_cpu], n)
#define __this_cpu_cmpxchg(v, o, n) compare_exchange(&(v)[current_cpu], o, n)
static long live_va;
static int alloc_call, fail_at, migration_at;
static bool check_flags;
static unsigned expected_flags;
static void *allocate(size_t n)
{
	alloc_call++;
	if (alloc_call == fail_at)
		return NULL;
	return calloc(1, n);
}
static void *kmem_cache_alloc_node(struct kmem_cache *c, gfp_t flags, int node)
{
	if (check_flags)
		assert(flags == expected_flags);
	void *p = allocate(sizeof(struct vmap_area));
	if (p)
		live_va++;
	if (alloc_call == migration_at)
		current_cpu ^= 1;
	return p;
}
static void *kmem_cache_alloc(struct kmem_cache *c, gfp_t flags)
{
	if (free_vmap_area_lock.held)
		assert(flags == GFP_NOWAIT);
	void *p = allocate(sizeof(struct vmap_area));
	if (p)
		live_va++;
	return p;
}
static void *kmem_cache_zalloc(struct kmem_cache *c, gfp_t flags)
{
	return kmem_cache_alloc(c, flags);
}
static void kmem_cache_free(struct kmem_cache *c, void *p)
{
	assert(p && live_va > 0);
	live_va--;
	free(p);
}
static void *kcalloc(size_t n, size_t size, gfp_t flags)
{
	return allocate(n * size);
}
static void *kzalloc(size_t n, gfp_t flags)
{
	return allocate(n);
}
#define kfree(p) free(p)
static void might_sleep(void)
{
	assert(!vmap_area_lock.held && !free_vmap_area_lock.held);
}
static void kmemleak_scan_area(void *p, size_t n, gfp_t f)
{
}
static bool gfpflags_allow_blocking(gfp_t f)
{
	return f & 1;
}
static int printk_ratelimit(void)
{
	return 0;
}
static int vmap_notify_list;
static void blocking_notifier_call_chain(int *l, int e, unsigned long *freed)
{
	*freed = 0;
}
typedef long atomic_long_t;
static atomic_long_t vmap_lazy_nr;
static long atomic_long_read(long *p)
{
	return *p;
}
static void atomic_long_sub(unsigned long v, long *p)
{
	*p -= v;
}
static long atomic_long_add_return(unsigned long v, long *p)
{
	return *p += v;
}
static unsigned long lazy_max_pages(void)
{
	return 65536;
}
static unsigned flushes;
static void verify(void);
static void flush_tlb_kernel_range(unsigned long start, unsigned long end)
{
	assert(start < end);
	verify();
	flushes++;
}
static void purge_fragmented_blocks_allcpus(void)
{
}
static void purge_vmap_area_lazy(void);
static bool panic_expected;
static jmp_buf panic_jmp;
static _Noreturn void panic(const char *fmt, ...)
{
	assert(panic_expected);
	longjmp(panic_jmp, 1);
}
static struct vm_struct *vmlist;
struct vmap_block_queue {
	struct lock lock;
	struct list_head free;
};
struct vfree_deferred {
	struct llist_head list;
	int wq;
};
static struct vmap_block_queue vmap_block_queue[2];
static struct vfree_deferred vfree_deferred[2];
#define for_each_possible_cpu(i) for ((i) = 0; (i) < 2; (i)++)
#define per_cpu(v, i) ((v)[i])
#define spin_lock_init(l) ((l)->held = false)
#define INIT_WORK(p, f) ((void)(p))
#define KMEM_CACHE(t, f) (&cache)
static void calc_total_vmalloc_size(void)
{
}
struct seq_file {
	int pending, ram, normal;
};
static void seq_printf(struct seq_file *m, const char *fmt, ...)
{
	assert(vmap_purge_lock.held && vmap_area_lock.held);
	if (strstr(fmt, "unpurged"))
		m->pending++;
	else if (strstr(fmt, "vm_map_ram"))
		m->ram++;
	else if (strstr(fmt, "0x%pK"))
		m->normal++;
}
static void seq_puts(struct seq_file *m, const char *s)
{
}
static void seq_putc(struct seq_file *m, int c)
{
}
static void show_numa_info(struct seq_file *m, struct vm_struct *v)
{
}
static bool is_vmalloc_addr(void *p)
{
	return false;
}
/* PRODUCTION_SEQ */
/* PRODUCTION_ENUM */
/* PRODUCTION_FIRST */
/* PRODUCTION_FUNCTIONS */

static uint32_t rng = 0x85917031;
static unsigned random32(void)
{
	rng ^= rng << 13;
	rng ^= rng >> 17;
	rng ^= rng << 5;
	return rng;
}
static unsigned char occupied[NPAGES];
static unsigned long search_cases, operations, pcpu_cases;
static void clear_tree(struct rb_root *root)
{
	struct rb_node *n;
	while ((n = rb_first(root))) {
		struct vmap_area *v = rb_entry(n, struct vmap_area, rb_node);
		rb_erase(n, root);
		kmem_cache_free(vmap_area_cachep, v);
	}
}
static void reset(void)
{
	assert(!vmap_area_lock.held && !free_vmap_area_lock.held &&
	       !vmap_purge_lock.held);
	struct llist_node *n = llist_del_all(&vmap_purge_list);
	while (n) {
		struct llist_node *next = n->next;
		kmem_cache_free(vmap_area_cachep,
				container_of(n, struct vmap_area, purge_list));
		n = next;
	}
	clear_tree(&vmap_area_root);
	clear_tree(&free_vmap_area_root);
	for (int i = 0; i < 2; i++)
		if (ne_fit_preload_node[i]) {
			kmem_cache_free(vmap_area_cachep,
					ne_fit_preload_node[i]);
			ne_fit_preload_node[i] = NULL;
		}
	assert(live_va == 0);
	INIT_LIST_HEAD(&vmap_area_list);
	INIT_LIST_HEAD(&free_vmap_area_list);
	vmap_initialized = true;
	vmap_lazy_nr = 0;
	flushes = 0;
	check_flags = false;
	alloc_call = fail_at = migration_at = current_cpu = 0;
	memset(occupied, 0, sizeof(occupied));
}
static struct vmap_area *new_area(unsigned long start, unsigned long end)
{
	struct vmap_area *v = kmem_cache_zalloc(vmap_area_cachep, GFP_NOWAIT);
	assert(v);
	v->va_start = start;
	v->va_end = end;
	return v;
}
static void arena(void)
{
	reset();
	insert_vmap_area_augment(new_area(VMALLOC_START, VMALLOC_END), NULL,
				 &free_vmap_area_root, &free_vmap_area_list);
}
static int verify_node(struct rb_node *n, struct rb_node *parent,
		       bool augmented)
{
	if (!n)
		return 1;
	assert(rb_parent(n) == parent);
	struct vmap_area *v = rb_entry(n, struct vmap_area, rb_node);
	assert(v->va_start < v->va_end);
	if (rb_is_red(n))
		assert((!n->rb_left || rb_is_black(n->rb_left)) &&
		       (!n->rb_right || rb_is_black(n->rb_right)));
	int l = verify_node(n->rb_left, n, augmented),
	    r = verify_node(n->rb_right, n, augmented);
	assert(l == r);
	if (augmented) {
		unsigned long m = v->va_end - v->va_start;
		if (n->rb_left)
			m = max(m,
				rb_entry(n->rb_left, struct vmap_area, rb_node)
				    ->subtree_max_size);
		if (n->rb_right)
			m = max(m,
				rb_entry(n->rb_right, struct vmap_area, rb_node)
				    ->subtree_max_size);
		assert(v->subtree_max_size == m);
	}
	return l + rb_is_black(n);
}
static void verify(void)
{
	if (free_vmap_area_root.rb_node)
		assert(rb_is_black(free_vmap_area_root.rb_node));
	if (vmap_area_root.rb_node)
		assert(rb_is_black(vmap_area_root.rb_node));
	verify_node(free_vmap_area_root.rb_node, NULL, true);
	verify_node(vmap_area_root.rb_node, NULL, false);
	struct rb_node *n = rb_first(&free_vmap_area_root);
	struct vmap_area *v;
	unsigned long prev = 0;
	list_for_each_entry(v, &free_vmap_area_list, list)
	{
		assert(n == &v->rb_node);
		assert(v->va_start >= prev);
		/* Adjacent free blocks must have coalesced. */
		if (prev)
			assert(v->va_start > prev);
		prev = v->va_end;
		n = rb_next(n);
	}
	assert(!n);
	for (unsigned i = 0; i < NPAGES; i++) {
		unsigned long addr = VMALLOC_START + i * PAGE_SIZE;
		bool isfree = false;
		list_for_each_entry(v, &free_vmap_area_list,
				    list) if (v->va_start <= addr &&
					      addr + PAGE_SIZE <= v->va_end)
		    isfree = true;
		assert(isfree == !occupied[i]);
	}
}
static bool fits_pages(unsigned long addr, unsigned long size)
{
	if (addr < VMALLOC_START || addr > VMALLOC_END ||
	    size > VMALLOC_END - addr)
		return false;
	for (unsigned i = (addr - VMALLOC_START) / PAGE_SIZE;
	     i < (addr + size - VMALLOC_START) / PAGE_SIZE; i++)
		if (occupied[i])
			return false;
	return true;
}
static unsigned long oracle(unsigned long size, unsigned long align,
			    unsigned long start, unsigned long end)
{
	for (unsigned long a = VMALLOC_START; a < VMALLOC_END; a += PAGE_SIZE)
		if (a >= start && !(a & (align - 1)) && a <= end &&
		    size <= end - a && fits_pages(a, size))
			return a;
	return end;
}
static void mark(unsigned long start, unsigned long size, bool used)
{
	for (unsigned i = (start - VMALLOC_START) / PAGE_SIZE;
	     i < (start + size - VMALLOC_START) / PAGE_SIZE; i++) {
		assert(occupied[i] != used);
		occupied[i] = used;
	}
}
static void test_search(void)
{
	arena();
	/* Two-node shape which the donor's size+padding pruning misses. */
	clear_tree(&free_vmap_area_root);
	INIT_LIST_HEAD(&free_vmap_area_list);
	insert_vmap_area_augment(new_area(0x8000, 0x9000), NULL,
				 &free_vmap_area_root, &free_vmap_area_list);
	insert_vmap_area_augment(new_area(0x2000, 0x4000), NULL,
				 &free_vmap_area_root, &free_vmap_area_list);
	struct vmap_area *v = find_vmap_lowest_match(0x2000, 0x1000, 0x1000);
	assert(v && v->va_start == 0x2000);
	for (unsigned trial = 0; trial < 100; trial++) {
		arena();
		clear_tree(&free_vmap_area_root);
		INIT_LIST_HEAD(&free_vmap_area_list);
		/* Many fragmented holes, inserted in random order to exercise
		 * rotations. */
		memset(occupied, 1, sizeof(occupied));
		unsigned order[64];
		for (unsigned i = 0; i < 64; i++)
			order[i] = i;
		for (unsigned i = 63; i; i--) {
			unsigned j = random32() % (i + 1), t = order[i];
			order[i] = order[j];
			order[j] = t;
		}
		for (unsigned i = 0; i < 64; i++) {
			unsigned p = order[i] * 16, n = 1 + random32() % 15;
			memset(occupied + p, 0, n);
			insert_vmap_area_augment(
			    new_area(VMALLOC_START + p * PAGE_SIZE,
				     VMALLOC_START + (p + n) * PAGE_SIZE),
			    NULL, &free_vmap_area_root, &free_vmap_area_list);
		}
		verify();
		for (unsigned j = 0; j < 3000; j++) {
			unsigned long size = (1 + random32() % 32) * PAGE_SIZE,
				      align = PAGE_SIZE << (random32() % 8);
			unsigned long start =
			    VMALLOC_START + (random32() % NPAGES) * PAGE_SIZE;
			unsigned long end =
			    VMALLOC_START + (random32() % NPAGES) * PAGE_SIZE;
			if (end < start) {
				unsigned long t = end;
				end = start;
				start = t;
			}
			unsigned long expected =
			    oracle(size, align, start, end);
			v = find_vmap_lowest_match(size, align, start);
			unsigned long got =
			    v ? ALIGN(max(v->va_start, start), align) : end;
			if (got > end || size > end - got)
				got = end;
			assert(got == expected);
			search_cases++;
		}
	}
	/* Alignment and end arithmetic near ULONG_MAX, checked in 128-bit
	 * oracle. */
	for (unsigned i = 0; i < 100000; i++) {
		unsigned long start = ULONG_MAX - (random32() % 65536),
			      end = ULONG_MAX - (random32() % 65536);
		if (start > end) {
			unsigned long t = end;
			end = start;
			start = t;
		}
		struct vmap_area va = {.va_start = start, .va_end = end};
		unsigned long align = 1UL << (random32() % 20),
			      size = 1 + random32() % 8192;
		unsigned long lower = ULONG_MAX - (random32() % 65536);
		__uint128_t a = ((__uint128_t)max(start, lower) + align - 1) &
				~((__uint128_t)align - 1);
		bool expected = a + size <= end;
		assert(is_within_this_va(&va, size, align, lower) == expected);
		assert(classify_va_fit_type(&va, start, ULONG_MAX) ==
		       NOTHING_FIT);
		search_cases++;
	}
	reset();
	printf("Search/overflow vs independent oracles: %lu PASS\n",
	       search_cases);
}
static void test_allocations(void)
{
	arena();
	struct vmap_area *live[128] = {0};
	for (unsigned i = 0; i < 30000; i++) {
		unsigned slot = random32() % 128;
		if (live[slot]) {
			mark(live[slot]->va_start, va_size(live[slot]), false);
			free_vmap_area(live[slot]);
			live[slot] = NULL;
		} else {
			unsigned long size = (1 + random32() % 16) * PAGE_SIZE,
				      align = PAGE_SIZE << (random32() % 6);
			unsigned long expected =
			    oracle(size, align, VMALLOC_START, VMALLOC_END);
			current_cpu = random32() % 2;
			struct vmap_area *v =
			    alloc_vmap_area(size, align, VMALLOC_START,
					    VMALLOC_END, 0, GFP_KERNEL);
			assert(IS_ERR(v) == (expected == VMALLOC_END));
			if (!IS_ERR(v)) {
				assert(v->va_start == expected);
				mark(v->va_start, size, true);
				live[slot] = v;
			}
		}
		if (i % 100 == 0)
			verify();
		operations++;
	}
	for (unsigned i = 0; i < 128; i++)
		if (live[i]) {
			mark(live[i]->va_start, va_size(live[i]), false);
			free_vmap_area(live[i]);
		}
	verify();
	assert(va_size(list_first_entry(&free_vmap_area_list, struct vmap_area,
					list)) == VMALLOC_END - VMALLOC_START);
	/* Actual GFP/preload/collision paths, including simulated CPU
	 * migration. */
	for (unsigned flags = 1; flags <= 7; flags += 2)
		for (int fail = 0; fail <= 3; fail++) {
			arena();
			alloc_call = 0;
			check_flags = true;
			expected_flags = flags;
			fail_at = fail;
			migration_at = 2;
			struct vmap_area *v = alloc_vmap_area(
			    PAGE_SIZE, PAGE_SIZE, VMALLOC_START + PAGE_SIZE,
			    VMALLOC_END, 0, flags);
			if (fail == 1)
				assert(IS_ERR(v));
			else {
				assert(!IS_ERR(v));
				mark(v->va_start, PAGE_SIZE, true);
				check_flags = false;
				mark(v->va_start, PAGE_SIZE, false);
				free_vmap_area(v);
			}
			check_flags = false;
			fail_at = 0;
			verify();
			operations++;
		}
	reset();
	printf("Allocation/split/merge/GFP/failure operations: %lu PASS\n",
	       operations);
}
static void render(struct seq_file *seq)
{
	loff_t pos = 0;
	void *p = s_start(seq, &pos);
	unsigned steps = 0;
	while (p) {
		assert(++steps < 100);
		s_show(seq, p);
		p = s_next(seq, p, &pos);
	}
	s_stop(seq, p);
	assert(!vmap_purge_lock.held && !vmap_area_lock.held);
}
static void test_lazy_and_seq(void)
{
	arena();
	struct vmap_area *a = alloc_vmap_area(
	    PAGE_SIZE, PAGE_SIZE, VMALLOC_START, VMALLOC_END, 0, GFP_KERNEL);
	mark(a->va_start, PAGE_SIZE, true);
	unsigned long addr = a->va_start;
	free_vmap_area_noflush(a);
	assert(vmap_lazy_nr == 1 && !__find_vmap_area(addr));
	/* Address still reserved until a flush; busy tree is completely empty.
	 */
	assert(find_vmap_lowest_match(PAGE_SIZE, PAGE_SIZE, addr)->va_start !=
	       addr);
	for (int repeat = 0; repeat < 3; repeat++) {
		struct seq_file seq = {0};
		render(&seq);
		assert(seq.pending == 1 && seq.ram == 0);
	}
	struct vmap_area *b = alloc_vmap_area(
	    PAGE_SIZE, PAGE_SIZE, VMALLOC_START, VMALLOC_END, 0, GFP_KERNEL);
	assert(b->va_start != addr);
	mark(b->va_start, PAGE_SIZE, true);
	struct seq_file seq = {0};
	render(&seq);
	assert(seq.pending == 1 && seq.ram == 1);
	struct vm_struct vm = {
	    .addr = (void *)b->va_start, .size = PAGE_SIZE, .flags = VM_ALLOC};
	b->vm = &vm;
	seq = (struct seq_file){0};
	render(&seq);
	assert(seq.pending == 1 && seq.normal == 1);
	/* Short read/restart, nonzero position and EOF all release both locks.
	 */
	for (loff_t initial = 0; initial < 4; initial++) {
		loff_t pos = initial;
		void *p = s_start(&seq, &pos);
		s_stop(&seq, p);
		assert(!vmap_area_lock.held && !vmap_purge_lock.held);
	}
	purge_vmap_area_lazy();
	mark(addr, PAGE_SIZE, false);
	assert(flushes && vmap_lazy_nr == 0);
	verify();
	mark(b->va_start, PAGE_SIZE, false);
	free_vmap_area(b);
	verify();
	reset();
	puts("Lazy TLB quarantine/proc iterator and lock balance: PASS");
}
static void test_boot(void)
{
	struct vm_struct a = {.addr = (void *)(VMALLOC_START + PAGE_SIZE),
			      .size = 2 * PAGE_SIZE};
	struct vm_struct b = {.addr = (void *)(VMALLOC_START + 8 * PAGE_SIZE),
			      .size = PAGE_SIZE};
	a.next = &b;
	for (int failure = 0; failure <= 5; failure++) {
		reset();
		vmap_initialized = false;
		vmlist = &a;
		fail_at = failure;
		panic_expected = failure > 0;
		if (setjmp(panic_jmp) == 0) {
			vmalloc_init();
			assert(!panic_expected && vmap_initialized);
			assert(__find_vmap_area((unsigned long)a.addr)->vm ==
			       &a);
			assert(__find_vmap_area((unsigned long)b.addr)->vm ==
			       &b);
			mark((unsigned long)a.addr, a.size, true);
			mark((unsigned long)b.addr, b.size, true);
			verify();
		} else
			assert(panic_expected && !vmap_initialized);
		panic_expected = false;
		fail_at = 0;
	}
	vmlist = NULL;
	reset();
	puts("Boot occupied/free metadata failure injection: 6 PASS");
}
static unsigned long pcpu_oracle(const unsigned long *offset,
				 const size_t *sizes, int nr,
				 unsigned long align)
{
	unsigned long end = 0;
	for (int i = 0; i < nr; i++)
		end = max(end, offset[i] + sizes[i]);
	for (unsigned long base = (VMALLOC_END - end) & ~(align - 1);
	     base >= VMALLOC_START; base -= align) {
		bool fit = true;
		for (int i = 0; i < nr; i++)
			if (!fits_pages(base + offset[i], sizes[i]))
				fit = false;
		if (fit)
			return base;
		if (base < VMALLOC_START + align)
			break;
	}
	return 0;
}
static void test_percpu(void)
{
	for (unsigned trial = 0; trial < 1000; trial++) {
		arena();
		struct vmap_area *busy[30];
		for (unsigned i = 0; i < 30; i++) {
			busy[i] = alloc_vmap_area(
			    (1 + random32() % 4) * PAGE_SIZE, PAGE_SIZE,
			    VMALLOC_START + (random32() % NPAGES) * PAGE_SIZE,
			    VMALLOC_END, 0, GFP_KERNEL);
			if (!IS_ERR(busy[i]))
				mark(busy[i]->va_start, va_size(busy[i]), true);
		}
		for (int count = 1; count <= 4; count++) {
			unsigned long offsets[4],
			    align = PAGE_SIZE << (random32() % 3), pos = 0;
			size_t sizes[4];
			for (int i = 0; i < count; i++) {
				offsets[i] = pos;
				sizes[i] = (1 + random32() % 3) * align;
				pos += sizes[i] + (1 + random32() % 6) * align;
			}
			for (int i = count - 1; i > 0; i--) {
				int j = random32() % (i + 1);
				unsigned long o = offsets[i];
				offsets[i] = offsets[j];
				offsets[j] = o;
				size_t z = sizes[i];
				sizes[i] = sizes[j];
				sizes[j] = z;
			}
			unsigned long expected =
			    pcpu_oracle(offsets, sizes, count, align);
			struct vm_struct **vms =
			    pcpu_get_vm_areas(offsets, sizes, count, align);
			assert((vms != NULL) == (expected != 0));
			if (vms) {
				for (int i = 0; i < count; i++) {
					assert((unsigned long)vms[i]->addr ==
					       expected + offsets[i]);
					mark((unsigned long)vms[i]->addr,
					     sizes[i], true);
				}
				verify();
				for (int i = 0; i < count; i++) {
					struct vmap_area *v = __find_vmap_area(
					    (unsigned long)vms[i]->addr);
					assert(v && v->vm == vms[i]);
					mark(v->va_start, va_size(v), false);
					free_vmap_area(v);
					kfree(vms[i]);
				}
				kfree(vms);
			}
			pcpu_cases++;
			verify();
		}
		for (unsigned i = 0; i < 30; i++)
			if (!IS_ERR(busy[i])) {
				mark(busy[i]->va_start, va_size(busy[i]),
				     false);
				free_vmap_area(busy[i]);
			}
		verify();
	}
	/* Fail allocations during arrays, metadata, VM descriptors and split
	 * paths. */
	for (int failure = 1; failure <= 14; failure++) {
		arena();
		unsigned long offsets[] = {PAGE_SIZE, 5 * PAGE_SIZE};
		size_t sizes[] = {PAGE_SIZE, PAGE_SIZE};
		alloc_call = 0;
		fail_at = failure;
		struct vm_struct **vms =
		    pcpu_get_vm_areas(offsets, sizes, 2, PAGE_SIZE);
		fail_at = 0;
		if (vms)
			for (int i = 0; i < 2; i++) {
				free_vmap_area(__find_vmap_area(
				    (unsigned long)vms[i]->addr));
				kfree(vms[i]);
			}
		kfree(vms);
		verify();
		pcpu_cases++;
	}
	reset();
	printf("Per-CPU allocation/oracle/rollback cases: %lu PASS\n",
	       pcpu_cases);
}
int main(void)
{
	setbuf(stdout, NULL);
	test_search();
	test_allocations();
	test_lazy_and_seq();
	test_boot();
	test_percpu();
	reset();
	return 0;
}
