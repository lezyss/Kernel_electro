// SPDX-License-Identifier: GPL-2.0
/* Single-threaded models for extracted procfs/formatting source. */
#undef NDEBUG
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>

_Static_assert(sizeof(unsigned long) == 8, "Use a 64-bit host for this model");

typedef uint16_t u16;
typedef uint64_t u64;
#define __force
#define __aligned(n) __attribute__((aligned(n)))
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
#define cpu_to_le16(x) (x)
#else
#define cpu_to_le16(x) __builtin_bswap16(x)
#endif
#define do_div(n, b) ({ unsigned r = (n) % (b); (n) /= (b); r; })
#define PAGE_SHIFT 12
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE - 1))
#define PAGE_ALIGN(x) (((x) + PAGE_SIZE - 1) & PAGE_MASK)
#define PSS_SHIFT 12
#define VM_READ 1
#define VM_WRITE 2
#define VM_EXEC 4
#define VM_MAYSHARE 8
#define VM_LOCKED 16
#define MAJOR(d) ((unsigned int)((d) >> 20))
#define MINOR(d) ((unsigned int)((d) & ((1U << 20) - 1)))
typedef unsigned long vm_flags_t;
static const char hex_asc[] = "0123456789abcdef";
struct seq_file {
	char *buf;
	size_t count, size, pad_until;
	void *private;
};
static void seq_set_overflow(struct seq_file *m) { m->count = m->size; }
static void seq_setwidth(struct seq_file *m, size_t n)
{
	m->pad_until = m->count + n;
}
struct page {
	bool anon, swapbacked, dirty, young, referenced;
	int count, mapcount, order;
};
#define PageAnon(p) ((p)->anon)
#define PageSwapBacked(p) ((p)->swapbacked)
#define PageDirty(p) ((p)->dirty)
#define PageReferenced(p) ((p)->referenced)
#define page_is_young(p) ((p)->young)
#define page_count(p) ((p)->count)
#define page_mapcount(p) ((p)->mapcount)
#define compound_order(p) ((p)->order)
struct vm_area_struct {
	unsigned long vm_start, vm_end;
	struct vm_area_struct *vm_next;
	struct page page;
	unsigned long vm_flags;
	struct mm_struct *vm_mm;
};
enum { MM_ANONPAGES, MM_FILEPAGES, MM_SHMEMPAGES, MM_SWAPENTS };
struct mm_struct {
	struct vm_area_struct *mmap;
	int mmap_sem, refs;
	bool live;
	unsigned long total_vm, hiwater_vm, hiwater_rss, end_code, start_code;
	unsigned long exec_vm, locked_vm, pinned_vm, data_vm, stack_vm;
	unsigned long counters[4];
};
static unsigned long get_mm_counter(struct mm_struct *mm, int which)
{
	return mm->counters[which];
}
static unsigned long mm_pgtables_bytes(struct mm_struct *mm)
{
	(void)mm;
	return PAGE_SIZE;
}
static void hugetlb_report_usage(struct seq_file *m, struct mm_struct *mm)
{
	(void)m;
	(void)mm;
}

/* EXTRACTED_HELPERS */

struct task_struct { int refs; };
struct proc_maps_private {
	void *inode;
	struct task_struct *task;
	struct mm_struct *mm;
};
static struct task_struct task = {1};
static int policies;
static struct task_struct *get_proc_task(void *inode)
{
	if (!inode)
		return NULL;
	task.refs++;
	return &task;
}
static bool mmget_not_zero(struct mm_struct *mm)
{
	if (!mm->live)
		return false;
	mm->refs++;
	return true;
}
static void mmput(struct mm_struct *mm) { assert(mm->refs-- == 2); }
static void put_task_struct(struct task_struct *t) { assert(t->refs-- == 2); }
static void down_read(int *lock) { assert(!(*lock)++); }
static void up_read(int *lock) { assert((*lock)-- == 1); }
static void hold_task_mempolicy(struct proc_maps_private *p)
{
	assert(p->mm->mmap_sem == 1);
	assert(!policies++);
}
static void release_task_mempolicy(struct proc_maps_private *p)
{
	assert(p->mm->mmap_sem == 1);
	assert(policies-- == 1);
}
struct mm_walk {
	int (*pmd_entry)(void);
	struct mm_struct *mm;
	void *private;
};
static int smaps_pte_range(void) { return 0; }
static void walk_page_vma(struct vm_area_struct *vma, struct mm_walk *walk)
{
	assert(walk->mm == vma->vm_mm && walk->mm->mmap_sem == 1);
	smaps_account(walk->private, &vma->page, false, false, false,
		      !!(vma->vm_flags & VM_LOCKED));
}

/* EXTRACTED_GATHER */

static void seq_pad(struct seq_file *m, char c)
{
	while (m->count < m->pad_until && m->count < m->size)
		seq_putc(m, ' ');
	if (c)
		seq_putc(m, c);
}

/* EXTRACTED_ROLLUP */

static unsigned int cases;
static void formatting(void)
{
	const unsigned long long nums[] = {0, 1, 9, 10, 99, 100, 9999,
		99999999, 100000000, 10000000000000000ULL, ULLONG_MAX};
	unsigned int i, width, cap, hex;

	for (i = 0; i < sizeof(nums) / sizeof(nums[0]); i++)
		for (width = 0; width <= 32; width++)
			for (hex = 0; hex <= 1; hex++) {
				char expected[128];
				int len = snprintf(expected, sizeof(expected),
					hex ? "::%0*llx" : "::%*llu",
					width, nums[i]);

				for (cap = 0; cap <= 80; cap++) {
					unsigned char data[128];
					struct seq_file m = {(char *)data, 0, cap, 0, NULL};
					unsigned int j;

					memset(data, 0xa5, sizeof(data));
					if (hex)
						seq_put_hex_ll(&m, "::", nums[i], width);
					else
						seq_put_decimal_ull_width(&m, "::", nums[i], width);
					assert(m.count <= cap);
					if (m.count < cap) {
						assert(m.count == (size_t)len);
						assert(!memcmp(data, expected, len));
					} else {
						assert((size_t)len >= cap);
					}
					for (j = cap; j < sizeof(data); j++)
						assert(data[j] == 0xa5);
					cases++;
				}
			}
	/* NULL hex delimiter and wide addresses/devices must retain printf ABI. */
	{
		char data[256], expected[256];
		struct seq_file m = {data, 0, sizeof(data), 0, NULL};
		unsigned long start = 0x123456789abcUL, end = 0x123456790000UL;
		unsigned long long offset = ULLONG_MAX;
		dev_t dev = ((dev_t)0x123 << 20) | 0xabcde;

		show_vma_header_prefix(&m, start, end, VM_READ | VM_EXEC,
				       offset, dev, ULONG_MAX);
		snprintf(expected, sizeof(expected),
			 "%08lx-%08lx r-xp %08llx %02x:%02x %lu ",
			 start, end, offset, MAJOR(dev), MINOR(dev), ULONG_MAX);
		assert(m.count == strlen(expected));
		assert(!memcmp(data, expected, m.count));
	}
}

static void status_units(void)
{
	char data[2048];
	struct seq_file m = {data, 0, sizeof(data), 0, NULL};
	struct mm_struct mm = {.start_code = 0x1000, .end_code = 0x11000,
		.exec_vm = 50, .live = true};

	task_mem(&m, &mm);
	assert(m.count < m.size);
	data[m.count] = 0;
	assert(strstr(data, "VmExe:\t      64 kB\n"));
	assert(strstr(data, "VmLib:\t     136 kB\n"));
	assert(strstr(data, "VmPTE:\t       4 kB\n"));
}

static void pss_accounting(void)
{
	struct mem_size_stats mss = {0};
	struct page pages[512];
	unsigned int i;

	for (i = 0; i < 512; i++)
		pages[i] = (struct page){.anon = true, .swapbacked = true,
			.count = 1, .mapcount = 1, .order = 9};
	smaps_account(&mss, pages, true, true, false, true);
	assert(mss.pss == (512ULL * PAGE_SIZE << PSS_SHIFT));
	assert(mss.pss_locked == mss.pss);
	assert(mss.pss_anon == mss.pss);
	assert(mss.private_clean == 512 * PAGE_SIZE);
	assert(mss.resident == 512 * PAGE_SIZE);
	memset(&mss, 0, sizeof(mss));
	/* Mixed sharing and page types, including file COW. */
	for (i = 0; i < 512; i++) {
		pages[i].count = 2;
		pages[i].mapcount = i % 2 ? 2 : 1;
		pages[i].anon = i % 3 == 0;
		pages[i].swapbacked = i % 3 != 1;
	}
	smaps_account(&mss, pages, true, false, true, true);
	assert(mss.pss == mss.pss_anon + mss.pss_file + mss.pss_shmem);
	assert(mss.pss_locked == mss.pss);
	assert(mss.pss == (384ULL * PAGE_SIZE << PSS_SHIFT));
	assert(mss.shared_dirty + mss.private_dirty == 512 * PAGE_SIZE);
}

static void rollup(void)
{
	struct vm_area_struct vmas[3] = {
		{.vm_start = 0x1000, .vm_end = 0x2000, .vm_flags = VM_LOCKED,
		 .page = {.anon = true, .swapbacked = true, .count = 1, .mapcount = 1}},
		{.vm_start = 0x3000, .vm_end = 0x4000,
		 .page = {.count = 2, .mapcount = 2}},
		{.vm_start = 0x5000, .vm_end = 0x6000, .vm_flags = VM_LOCKED,
		 .page = {.swapbacked = true, .count = 2, .mapcount = 2}},
	};
	struct mm_struct mm = {.mmap = vmas, .refs = 1, .live = true};
	struct proc_maps_private priv = {.inode = (void *)1, .mm = &mm};
	char data[2048], previous[2048];
	struct seq_file m = {data, 0, sizeof(data), 0, &priv};
	unsigned int i;

	for (i = 0; i < 3; i++)
		vmas[i].vm_mm = &mm;
	vmas[0].vm_next = &vmas[1];
	vmas[1].vm_next = &vmas[2];
	for (i = 0; i < 100; i++) {
		m.count = 0;
		assert(!show_smaps_rollup(&m, NULL));
		assert(m.count < m.size);
		data[m.count] = 0;
		assert(strstr(data, "Pss:                   8 kB\n"));
		assert(strstr(data, "Pss_Anon:              4 kB\n"));
		assert(strstr(data, "Pss_File:              2 kB\n"));
		assert(strstr(data, "Pss_Shmem:             2 kB\n"));
		assert(strstr(data, "Locked:                6 kB\n"));
		assert(!strstr(data, "Size:"));
		if (!i)
			strcpy(previous, data);
		else
			assert(!strcmp(previous, data));
		assert(mm.refs == 1 && !mm.mmap_sem && task.refs == 1);
		assert(!policies && !priv.task);
	}
	/* A short-buffer retry must not retain accumulated totals. */
	m.count = 0;
	m.size = 32;
	assert(!show_smaps_rollup(&m, NULL));
	assert(m.count == m.size);
	m.count = 0;
	m.size = sizeof(data);
	assert(!show_smaps_rollup(&m, NULL));
	data[m.count] = 0;
	assert(!strcmp(previous, data));
	mm.mmap = NULL;
	m.count = 0;
	assert(!show_smaps_rollup(&m, NULL) && !m.count);
	assert(mm.refs == 1 && !mm.mmap_sem && task.refs == 1 && !policies);
	mm.live = false;
	assert(show_smaps_rollup(&m, NULL) == -ESRCH);
	assert(mm.refs == 1 && task.refs == 1 && !priv.task);
	priv.inode = NULL;
	assert(show_smaps_rollup(&m, NULL) == -ESRCH);
	assert(task.refs == 1 && !priv.task);
}

int main(void)
{
	formatting();
	status_units();
	pss_accounting();
	rollup();
	printf("Extracted-source procfs models: PASS (%u formatting cases, "
	       "status units, PSS, rollup retries/empty-mm/reference balance)\n", cases);
	return 0;
}
