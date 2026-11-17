// SPDX-License-Identifier: GPL-2.0
/* Extracted production code is compiled here against deliberately small stubs.
 * This model does not execute the running kernel's VM or claim real locking.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>
#include <fcntl.h>

#define __force
#define READ_ONCE(x) (x)
#define likely(x) (x)
#define unlikely(x) (x)
#define IS_ENABLED(x) (x)
#define VM_READ (1UL << 0)
#define VM_WRITE (1UL << 1)
#define VM_EXEC (1UL << 2)
#define VM_SEQ_READ (1UL << 3)
#define VM_RAND_READ (1UL << 4)
#define VM_LOCKED (1UL << 5)
#define VM_SPECIAL (1UL << 6)
#define PAGE_SHIFT 12
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE - 1))
#define WB_SYNC_NONE 0
static bool warn_on_once(bool x) { assert(!x); return x; }
#define WARN_ON_ONCE(x) warn_on_once(x)
typedef unsigned int fmode_t;
typedef uint64_t u64;
typedef unsigned long pgoff_t;
typedef unsigned long pte_t;
struct backing_dev_info { unsigned long ra_pages; };
struct inode {
	unsigned int i_mode;
	loff_t i_size;
	bool dax;
	struct backing_dev_info *bdi;
};
struct address_space_operations { bool readpage; };
struct address_space {
	struct inode *host;
	struct address_space_operations *a_ops;
	bool unevictable, shmem;
};
struct file {
	fmode_t f_mode;
	int f_lock;
	struct { unsigned long ra_pages; } f_ra;
	struct inode *inode;
	struct address_space *f_mapping;
};
struct fd { struct file *file; };
struct mem_cgroup { int id; };
struct mm_struct { int cgroup; };
struct vm_area_struct {
	unsigned long vm_flags;
	struct file *vm_file;
	struct mm_struct *vm_mm;
	bool huge, anonymous, use_pmd;
	pte_t entry;
};
struct page {
	struct vm_area_struct *vmas[4];
	int count, access_count;
	bool anon, ksm, lock_fail, locked, young, idle;
};
struct page_vma_mapped_walk {
	struct page *page;
	struct vm_area_struct *vma;
	unsigned long address;
	pte_t *pte, *pmd;
	bool walked;
};
struct rmap_walk_control {
	bool (*rmap_one)(struct page *, struct vm_area_struct *, unsigned long, void *);
	void *arg;
	void *(*anon_lock)(struct page *);
	bool (*invalid_vma)(struct vm_area_struct *, void *);
};
struct lru_gen_mm_walk { bool can_swap; };
struct mm_walk { struct vm_area_struct *vma; void *private; };
struct task { bool in_lru_fault; };
static struct task task;
#define current (&task)
static struct backing_dev_info normal_bdi = { 32 }, noop_backing_dev_info;
static struct file *fds[4];
static int gets, fdputs, locks, readaheads, writebacks, drains, invalidations;
static int memcg_checks, look_arounds, cleared;
static bool gen_runtime __attribute__((unused)); /* unused when MGLRU is compiled out */
static bool pte_young(pte_t p) { return p & 1; }
static struct fd fdget(int n)
{
	struct fd fd = { n >= 0 && n < 4 ? fds[n] : NULL };
	gets++;
	return fd;
}
static void fdput(struct fd f) { assert(f.file && !f.file->f_lock); fdputs++; }
static struct inode *file_inode(struct file *f) { return f->inode; }
#define IS_DAX(i) ((i)->dax)
static struct backing_dev_info *inode_to_bdi(struct inode *i) { return i->bdi; }
static void spin_lock(int *p) { assert(!*p); *p = 1; locks++; }
static void spin_unlock(int *p) { assert(*p); *p = 0; }
static void force_page_cache_readahead(struct address_space *m, struct file *f,
				     pgoff_t start, unsigned long count)
{ (void)m; (void)f; (void)start; (void)count; readaheads++; }
static bool inode_write_congested(struct inode *i) { (void)i; return false; }
static void __filemap_fdatawrite_range(struct address_space *m, loff_t a,
				     loff_t b, int mode)
{ (void)m; (void)a; (void)b; (void)mode; writebacks++; }
static void lru_add_drain(void) { drains++; }
static void lru_add_drain_all(void) { drains++; }
static unsigned long invalidate_mapping_pages(struct address_space *m,
					      pgoff_t a, pgoff_t b)
{ (void)m; invalidations++; return b - a + 1; }
static bool page_vma_mapped_walk(struct page_vma_mapped_walk *w)
{
	if (w->walked) return false;
	w->walked = true;
	if (w->vma->use_pmd) w->pmd = &w->vma->entry;
	else w->pte = &w->vma->entry;
	return true;
}
static void page_vma_mapped_walk_done(struct page_vma_mapped_walk *w) { (void)w; }
static bool lru_gen_enabled(void)
{
#ifdef CONFIG_LRU_GEN
	return gen_runtime;
#else
	return false;
#endif
}
static void lru_gen_look_around(struct page_vma_mapped_walk *w)
{ assert(w->pte && pte_young(*w->pte)); *w->pte &= ~1UL; look_arounds++; }
static bool ptep_clear_flush_young_notify(struct vm_area_struct *vma,
					unsigned long addr, pte_t *pte)
{
	bool young = pte_young(*pte);
	(void)vma; (void)addr;
	*pte &= ~1UL; cleared++;
	return young;
}
#define pmdp_clear_flush_young_notify ptep_clear_flush_young_notify
static void clear_page_idle(struct page *p) { p->idle = false; }
static bool test_and_clear_page_young(struct page *p)
{ bool young = p->young; p->young = false; return young; }
static bool mm_match_cgroup(struct mm_struct *mm, struct mem_cgroup *memcg)
{
	assert(memcg); memcg_checks++;
	return !CONFIG_MEMCG || mm->cgroup == memcg->id;
}
static int total_mapcount(struct page *p) { return p->count; }
static bool page_mapped(struct page *p) { return p->count > 0; }
static bool page_rmapping(struct page *p) { (void)p; return true; }
static bool PageAnon(struct page *p) { return p->anon; }
static bool PageKsm(struct page *p) { return p->ksm; }
static bool trylock_page(struct page *p)
{ if (p->lock_fail) return false; assert(!p->locked); p->locked = true; return true; }
static void unlock_page(struct page *p) { assert(p->locked); p->locked = false; }
static void *page_lock_anon_vma_read(struct page *p) { return p; }
static void rmap_walk(struct page *p, struct rmap_walk_control *rwc)
{
	int i;
	assert(rwc->invalid_vma);
	for (i = 0; i < p->count; i++) {
		struct vm_area_struct *vma = p->vmas[i];
		if (rwc->invalid_vma(vma, rwc->arg)) continue;
		if (!rwc->rmap_one(p, vma, 0, rwc->arg)) break;
	}
}
#ifdef CONFIG_LRU_GEN
static bool is_vm_hugetlb_page(struct vm_area_struct *v) { return v->huge; }
static struct vm_area_struct *get_gate_vma(struct mm_struct *mm) { (void)mm; return NULL; }
static bool vma_is_anonymous(struct vm_area_struct *v) { return v->anonymous; }
static bool mapping_unevictable(struct address_space *m) { return m->unevictable; }
static bool shmem_mapping(struct address_space *m) { return m->shmem; }
#endif
static void mark_page_accessed(struct page *p) { p->access_count++; }

/* PRODUCTION */

static void test_advice(void)
{
	struct inode inode = { .i_mode = S_IFREG, .i_size = 65536, .bdi = &normal_bdi };
	struct address_space map = { .host = &inode };
	struct file file = { .inode = &inode, .f_mapping = &map,
		.f_mode = FMODE_READ | FMODE_NOWAIT, .f_ra = { 7 } };
	struct file separate = file;
	int before, i;
	fds[0] = &file; fds[1] = &file; fds[2] = &separate;
	assert(ksys_fadvise64_64(0, 123, 1, POSIX_FADV_NOREUSE) == 0);
	assert(file.f_mode == (FMODE_READ | FMODE_NOWAIT | FMODE_NOREUSE));
	assert(fds[1]->f_mode == file.f_mode && !(separate.f_mode & FMODE_NOREUSE));
	assert(file.f_ra.ra_pages == 7 && locks == 1);
	assert(!readaheads && !invalidations && !writebacks && !drains);
	assert(ksys_fadvise64_64(1, 0, 0, POSIX_FADV_NOREUSE) == 0);
	assert(locks == 2); /* idempotent but still serialized */
	assert(ksys_fadvise64_64(0, 0, 0, POSIX_FADV_RANDOM) == 0);
	assert((file.f_mode & (FMODE_RANDOM | FMODE_NOREUSE)) == (FMODE_RANDOM | FMODE_NOREUSE));
	assert(ksys_fadvise64_64(0, 0, 0, POSIX_FADV_SEQUENTIAL) == 0);
	assert((file.f_mode & FMODE_NOREUSE) && !(file.f_mode & FMODE_RANDOM));
	assert(file.f_ra.ra_pages == normal_bdi.ra_pages * 2);
	assert(ksys_fadvise64_64(0, 4096, 4096, POSIX_FADV_WILLNEED) == 0);
	assert((file.f_mode & FMODE_NOREUSE) && readaheads == 1);
	assert(ksys_fadvise64_64(0, 0, 0, POSIX_FADV_NORMAL) == 0);
	assert(file.f_mode == (FMODE_READ | FMODE_NOWAIT));
	assert(file.f_ra.ra_pages == normal_bdi.ra_pages);
	before = locks;
	assert(ksys_fadvise64_64(0, 0, -1, POSIX_FADV_NOREUSE) == -EINVAL);
	assert(ksys_fadvise64_64(0, 0, 0, 999) == -EINVAL);
	assert(ksys_fadvise64_64(3, 0, 0, POSIX_FADV_NOREUSE) == -EBADF);
	inode.i_mode = S_IFIFO;
	assert(ksys_fadvise64_64(0, 0, 0, POSIX_FADV_NOREUSE) == -ESPIPE);
	inode.i_mode = S_IFREG;
	for (i = 0; i < 2; i++) {
		inode.dax = !i;
		inode.bdi = i ? &noop_backing_dev_info : &normal_bdi;
		assert(ksys_fadvise64_64(0, 0, 0, POSIX_FADV_NOREUSE) == 0);
		assert(!(file.f_mode & FMODE_NOREUSE));
	}
	assert(locks == before && !file.f_lock);
	assert(gets == fdputs + 1); /* the invalid fd was never acquired */
}

static void test_recency(void)
{
	struct mm_struct mm = { .cgroup = 1 }, other = { .cgroup = 2 };
	struct file file = { 0 };
	struct mem_cgroup memcg = { .id = 1 };
	struct vm_area_struct vma = { .vm_flags = VM_READ, .vm_file = &file, .vm_mm = &mm };
	struct page_referenced_arg pra = { .memcg = NULL };
	struct page page = { .vmas = { &vma }, .count = 1 };
	unsigned long flags;
	unsigned long vm_flags[] = { VM_READ, VM_READ | VM_SEQ_READ,
		VM_READ | VM_RAND_READ, VM_READ | VM_SEQ_READ | VM_RAND_READ };
	unsigned int fmode[] = { FMODE_READ, FMODE_READ | FMODE_NOREUSE };
	unsigned int i, j, runtime;
	for (i = 0; i < 4; i++) for (j = 0; j < 2; j++) {
		bool expected = !i && !j;
		vma.vm_flags = vm_flags[i]; file.f_mode = fmode[j];
		assert(vma_has_recency(&vma) == expected);
		memcg_checks = 0;
		assert(invalid_page_referenced_vma(&vma, &pra) == !expected);
		assert(memcg_checks == 0); /* NULL never passed to mm_match_cgroup */
		for (runtime = 0; runtime < 2; runtime++) {
			gen_runtime = runtime;
			vma.entry = 1; page.idle = true;
			cleared = look_arounds = 0;
			assert(page_referenced(&page, 0, NULL, &flags) == expected);
			assert(!page.locked);
			assert(cleared == (int)expected);
			assert(!!vma.entry == !expected);
			assert((look_arounds > 0) == (expected && lru_gen_enabled()));
			assert(page.idle == !expected);
			page.access_count = 0;
			unmap_reference(&vma, 1, &page);
			unmap_reference(&vma, 0, &page);
			assert(page.access_count == expected);
		}
		lru_gen_enter_fault(&vma);
#ifdef CONFIG_LRU_GEN
		assert(current->in_lru_fault == expected);
#else
		assert(!current->in_lru_fault);
#endif
		lru_gen_exit_fault(); assert(!current->in_lru_fault);
	}
	vma.vm_flags = VM_READ; file.f_mode = 0;
	pra.memcg = &memcg;
	assert(!invalid_page_referenced_vma(&vma, &pra));
	vma.vm_mm = &other;
	assert(invalid_page_referenced_vma(&vma, &pra) == !!CONFIG_MEMCG);
	vma.entry = 1;
	assert(page_referenced(&page, 0, &memcg, &flags) == !CONFIG_MEMCG);
	vma.vm_mm = &mm;
	/* No vm_file: anonymous mappings still honor VMA hints, never dereference NULL. */
	vma.vm_file = NULL; assert(vma_has_recency(&vma));
	vma.vm_flags |= VM_RAND_READ; assert(!vma_has_recency(&vma));
	vma.vm_file = &file; vma.vm_flags = VM_READ;
	/* One non-recent mapping must not suppress another mapping's reference. */
	{
		struct file noreuse = { .f_mode = FMODE_NOREUSE };
		struct vm_area_struct first = vma;
		first.vm_file = &noreuse; first.entry = 1; vma.entry = 1;
		page.vmas[0] = &first; page.vmas[1] = &vma; page.count = 2;
		assert(page_referenced(&page, 0, NULL, &flags) == 1);
		assert(first.entry == 1 && vma.entry == 0);
	}
	page.vmas[0] = &vma; page.count = 1;
	/* Preserve VM_LOCKED handling and failed trylock fallback. */
	vma.vm_flags = VM_READ | VM_LOCKED; vma.entry = 1;
	assert(page_referenced(&page, 0, NULL, &flags) == 0 && (flags & VM_LOCKED));
	assert(vma.entry == 1 && !page.locked);
	vma.vm_flags = VM_READ; page.lock_fail = true;
	assert(page_referenced(&page, 0, NULL, &flags) == 1 && !page.locked);
	page.lock_fail = false;
#if CONFIG_TRANSPARENT_HUGEPAGE
	vma.use_pmd = true; vma.entry = 1;
	assert(page_referenced(&page, 0, NULL, &flags) == 1);
	file.f_mode = FMODE_NOREUSE; vma.entry = 1;
	assert(page_referenced(&page, 0, NULL, &flags) == 0 && vma.entry == 1);
#endif
}

#ifdef CONFIG_LRU_GEN
static void test_aging(void)
{
	struct address_space_operations ops = { .readpage = true };
	struct address_space map = { .a_ops = &ops };
	struct file file = { .f_mapping = &map };
	struct vm_area_struct vma = { .vm_flags = VM_READ, .vm_file = &file };
	struct lru_gen_mm_walk priv = { .can_swap = true };
	struct mm_walk walk = { .vma = &vma, .private = &priv };
	assert(!should_skip_vma(0, 4096, &walk));
	file.f_mode = FMODE_NOREUSE; assert(should_skip_vma(0, 4096, &walk));
	file.f_mode = 0;
	vma.vm_flags |= VM_RAND_READ; assert(should_skip_vma(0, 4096, &walk));
	vma.vm_flags = VM_READ | VM_SEQ_READ; assert(should_skip_vma(0, 4096, &walk));
	vma.vm_flags = VM_READ | VM_LOCKED; assert(should_skip_vma(0, 4096, &walk));
	vma.vm_flags = VM_READ | VM_SPECIAL; assert(should_skip_vma(0, 4096, &walk));
	vma.vm_flags = 0; assert(should_skip_vma(0, 4096, &walk));
	vma.vm_flags = VM_READ; vma.huge = true; assert(should_skip_vma(0, 4096, &walk));
	vma.huge = false; map.unevictable = true; assert(should_skip_vma(0, 4096, &walk));
	map.unevictable = false; ops.readpage = false; assert(should_skip_vma(0, 4096, &walk));
	ops.readpage = true; map.shmem = true; priv.can_swap = false;
	assert(should_skip_vma(0, 4096, &walk));
	priv.can_swap = true; assert(!should_skip_vma(0, 4096, &walk));
	vma.anonymous = true; vma.vm_file = NULL; priv.can_swap = false;
	assert(should_skip_vma(0, 4096, &walk));
	priv.can_swap = true; assert(!should_skip_vma(0, 4096, &walk));
}
#endif

int main(void)
{
	test_advice();
	test_recency();
#ifdef CONFIG_LRU_GEN
	test_aging();
#endif
	puts("PASS: fadvise transitions/errors, recency, shared mappings, memcg, unmap/fault/aging and native rmap safeguards");
	return 0;
}
