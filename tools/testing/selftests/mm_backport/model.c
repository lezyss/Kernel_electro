/* SPDX-License-Identifier: GPL-2.0 */
/* Template: the runner inserts production functions and branch blocks. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define likely(x) (x)
#define unlikely(x) (x)
#define READ_ONCE(x) (x)
#define min(a, b) ({ __auto_type _a = (a); __auto_type _b = (b); _a < _b ? _a : _b; })
typedef unsigned int gfp_t;
struct page;
struct list_head { struct page *page; struct list_head *pool; int count; };
struct page { int locked, uptodate, workingset, refs, index; struct list_head lru; };
struct file { struct address_space *f_mapping; };
struct address_space_operations {
    int (*readpage)(struct file *, struct page *);
    int (*readpages)(struct file *, struct address_space *, struct list_head *, unsigned);
};
struct address_space { struct address_space_operations *a_ops; };
static int read_calls, waits, callback_error, callback_uptodate, mutate;
static void unlock_page(struct page *p) { assert(p->locked); p->locked = 0; }
static int PageUptodate(struct page *p) { return p->uptodate; }
static int PageWorkingset(struct page *p) { return p->workingset; }
static int PageLocked(struct page *p) { return p->locked; }
static int PageSwapCache(struct page *p) { return 1; }
static void SetPageUptodate(struct page *p) { p->uptodate = 1; }
static void wait_on_page_locked(struct page *p) { assert(!p->locked); waits++; }
static int read_one(struct file *f, struct page *p)
{
    read_calls++;
    unlock_page(p);
    p->uptodate = callback_uptodate;
    if (mutate) p->workingset = !p->workingset;
    return callback_error;
}
static int buffered_guard(struct address_space *mapping, struct page *page)
{
    struct file f = { mapping }, *filp = &f;
    int error;
    /* PRODUCTION_BUFFERED */
    return error;
}
static int fault_guard(struct address_space *mapping, struct page *page)
{
    struct file f = { mapping }, *file = &f;
    int error;
    /* PRODUCTION_FAULT */
    return error;
}
static struct page pool_pages[32];
static int pool_next, insert_fail, plugs_started, plugs_finished, bulk_calls, bulk_consume;
struct blk_plug { int active; };
static void blk_start_plug(struct blk_plug *p) { p->active = 1; plugs_started++; }
static void blk_finish_plug(struct blk_plug *p) { assert(p->active); p->active = 0; plugs_finished++; }
static struct page *lru_to_page(struct list_head *p)
{
    assert(p->count > 0); return &pool_pages[pool_next];
}
static void list_del(struct list_head *p) { assert(p->pool->count); p->pool->count--; pool_next++; }
static void put_page(struct page *p) { assert(p->refs > 0); p->refs--; }
static void put_pages_list(struct list_head *p)
{
    while (p->count) { struct page *page = lru_to_page(p); list_del(&page->lru); put_page(page); }
}
static int add_to_page_cache_lru(struct page *p, struct address_space *m, int index, gfp_t g)
{
    if (insert_fail) return -EEXIST;
    p->locked = 1; p->refs++; return 0;
}
static int read_bulk(struct file *f, struct address_space *m, struct list_head *p, unsigned n)
{
    bulk_calls++;
    while (bulk_consume && p->count) {
        struct page *page = lru_to_page(p); list_del(&page->lru); put_page(page); bulk_consume--;
    }
    return callback_error;
}
/* PRODUCTION_READAHEAD */

#define VM_BUG_ON_PAGE(c, p) assert(!(c))
#define GFP_KERNEL 0
#define SWP_FILE 1
#define PSWPIN 1
#define REQ_OP_READ 0
#define TASK_UNINTERRUPTIBLE 1
#define TASK_RUNNING 0
struct task_struct { int refs; };
static struct task_struct task, *current = &task;
struct gendisk { void *queue; };
struct bio { struct gendisk *bi_disk; void *bi_private; int refs; };
typedef int blk_qc_t;
struct swap_info_struct { int flags; struct file *swap_file; void *bdev; };
static struct swap_info_struct sis;
static struct bio bio_storage;
static struct gendisk disk_storage;
static struct page *io_page;
static int route, psi_disabled, memstall, enters, leaves;
static struct swap_info_struct *page_swap_info(struct page *p) { return &sis; }
static void psi_memstall_enter(unsigned long *flags)
{
    enters++;
    if (psi_disabled) return;
    *flags = memstall;
    if (!*flags) memstall = 1;
}
static void psi_memstall_leave(unsigned long *flags)
{
    leaves++;
    assert(enters == leaves); /* A cold page must not consume uninitialized flags. */
    if (psi_disabled) return;
    if (!*flags) { assert(memstall); memstall = 0; }
}
static int frontswap_load(struct page *p)
{
    if (route != 0) return -1;
    if (mutate) p->workingset = !p->workingset;
    return 0;
}
static int bdev_read_page(void *b, int sector, struct page *p)
{
    if (route != 2) return -1;
    unlock_page(p); p->uptodate = 1;
    if (mutate) p->workingset = !p->workingset;
    return 0;
}
static int map_swap_page(struct page *p, void **b) { return 0; }
static void count_vm_event(int e) {}
static void end_swap_bio_read(struct bio *b) {}
static struct bio *get_swap_bio(gfp_t g, struct page *p, void (*end)(struct bio *))
{
    if (route == 3) return NULL;
    bio_storage = (struct bio) { .bi_disk = &disk_storage, .refs = 1 };
    io_page = p;
    return &bio_storage;
}
static void get_task_struct(struct task_struct *t) { t->refs++; }
static void bio_set_op_attrs(struct bio *b, int op, int flags) {}
static void bio_get(struct bio *b) { b->refs++; }
static void bio_put(struct bio *b) { assert(b->refs > 0); b->refs--; }
static blk_qc_t submit_bio(struct bio *b)
{
    assert(b->bi_private == current);
    b->bi_private = NULL; task.refs--; bio_put(b);
    unlock_page(io_page); io_page->uptodate = 1;
    if (mutate) io_page->workingset = !io_page->workingset;
    return 0;
}
static int blk_mq_poll(void *queue, int qc) { return 0; }
static void set_current_state(int state) {}
static void __set_current_state(int state) {}
/* PRODUCTION_SWAP */

/* PRODUCTION_ENUMS */
/* PRODUCTION_HELPERS */
/* PRODUCTION_FEEDBACK */
#define MAX_COMPACT_RETRIES 16
#define PAGE_ALLOC_COSTLY_ORDER 3
struct alloc_context { int unused; };
static bool suitable, lmk;
static int suitable_calls;
static bool should_compact_lmk_retry(struct alloc_context *ac, int order, int flags)
{ return lmk && order <= PAGE_ALLOC_COSTLY_ORDER; }
static bool compaction_zonelist_suitable(struct alloc_context *ac, int order, int flags)
{ suitable_calls++; return suitable; }
#define trace_compact_retry(o, p, r, n, m, v) do { (void)(p); (void)(n); } while (0)
/* PRODUCTION_RETRY */

struct shrink_control { int nid; unsigned long nr_to_scan, nr_scanned; };
typedef long atomic_long_t;
struct shrinker {
    unsigned long (*count_objects)(struct shrinker *, struct shrink_control *);
    unsigned long (*scan_objects)(struct shrinker *, struct shrink_control *);
    int seeks; long batch; atomic_long_t nr_deferred[1];
};
#define SHRINK_BATCH 128
#define SHRINK_STOP (~0UL)
#define SLABS_SCANNED 1
static long freeable_objects, counted_scans;
static int kswapd, stop_scan;
static unsigned long long traced_delta;
static long traced_target;
static int current_is_kswapd(void) { return kswapd; }
static long atomic_long_xchg(long *p, long v) { long old = *p; *p = v; return old; }
static long atomic_long_add_return(long v, long *p) { return *p += v; }
static long atomic_long_read(long *p) { return *p; }
#define do_div(n, b) do { assert((b) > 0); (n) /= (b); } while (0)
#define pr_err(...) assert(!"unexpected overflow")
#define trace_mm_shrink_slab_start(s, c, n, f, d, t, p) do { traced_delta = (d); traced_target = (t); } while (0)
#define trace_mm_shrink_slab_end(s, nid, f, n, new, t) do { (void)(new); } while (0)
static void count_vm_events(int event, unsigned long n) { counted_scans += n; }
static void cond_resched(void) {}
static unsigned long count_objects(struct shrinker *s, struct shrink_control *sc) { return freeable_objects; }
static unsigned long scan_objects(struct shrinker *s, struct shrink_control *sc)
{
    if (stop_scan) return SHRINK_STOP;
    return sc->nr_to_scan;
}
/* PRODUCTION_SHRINK */

#define SYSTEM_RUNNING 1
static int system_state, pending, updates_needed, refreshed, vmstat_work;
#define this_cpu_ptr(p) (p)
static int delayed_work_pending(int *work) { return pending; }
static int smp_processor_id(void) { return 0; }
static int need_update(int cpu) { return updates_needed; }
static void refresh_cpu_vm_stats(bool quiet) { assert(!quiet); refreshed++; }
/* PRODUCTION_QUIET */

static void test_filemap(void)
{
    unsigned cases = 0;
    for (int fault = 0; fault < 2; fault++)
    for (int ops = 0; ops < 3; ops++)
    for (int error = 0; error < 3; error++)
    for (int uptodate = 0; uptodate < 2; uptodate++) {
        struct address_space_operations aops = { .readpage = ops == 2 ? read_one : NULL };
        struct address_space mapping = { ops ? &aops : NULL };
        struct page p = { .locked = 1, .refs = 1 };
        callback_error = error == 2 ? 0x80001 : error ? -EIO : 0; callback_uptodate = uptodate;
        read_calls = waits = mutate = 0;
        int ret = fault ? fault_guard(&mapping, &p) : buffered_guard(&mapping, &p);
        int expected = ops < 2 ? -EIO : callback_error ? callback_error :
            fault && !uptodate ? -EIO : 0;
        assert(ret == expected && !p.locked && p.refs == 1);
        assert(read_calls == (ops == 2));
        assert(waits == (fault && ops == 2 && !error));
        cases++;
    }
    printf("Filemap guarded callback/lock cases: %u PASS\n", cases);
}
static void test_readahead(void)
{
    unsigned cases = 0;
    for (int mode = 0; mode < 6; mode++)
    for (int n = 0; n <= 32; n++)
    for (int fail = 0; fail < 2; fail++)
    for (int error = 0; error < 2; error++) {
        struct address_space_operations aops = {
            .readpage = mode == 3 || mode == 5 ? read_one : NULL,
            .readpages = mode >= 4 ? read_bulk : NULL };
        struct address_space m = { mode >= 2 ? &aops : NULL };
        struct list_head pool = { .count = n };
        for (int i = 0; i < n; i++) pool_pages[i] = (struct page) {
            .refs = 1, .index = i, .lru = { .pool = &pool } };
        pool_next = plugs_started = plugs_finished = bulk_calls = read_calls = 0;
        insert_fail = fail; callback_error = error ? -EIO : 0; bulk_consume = n / 2;
        int ret = read_pages(mode == 0 ? NULL : &m, NULL, &pool, n, 0);
        assert(ret == (mode <= 2 ? -EINVAL : mode >= 4 ? callback_error : 0));
        assert(pool.count == 0 && pool_next == n);
        assert(plugs_started == (mode >= 2) && plugs_finished == plugs_started);
        assert(bulk_calls == (mode >= 4));
        assert(read_calls == (mode == 3 && !fail ? n : 0));
        for (int i = 0; i < n; i++)
            assert(!pool_pages[i].locked && pool_pages[i].refs == (mode == 3 && !fail));
        cases++;
    }
    printf("Readahead cleanup/plug/bulk-fallback cases: %u PASS\n", cases);
}
static void test_swap(void)
{
    unsigned cases = 0;
    for (route = 0; route < 5; route++)
    for (int hot = 0; hot < 2; hot++)
    for (int nested = 0; nested < 2; nested++)
    for (psi_disabled = 0; psi_disabled < 2; psi_disabled++)
    for (int sync = 0; sync < 2; sync++)
    for (mutate = 0; mutate < 2; mutate++) {
        struct page p = { .locked = 1, .workingset = hot };
        struct address_space_operations ops = { .readpage = read_one };
        struct address_space mapping = { &ops };
        struct file file = { &mapping };
        sis = (struct swap_info_struct) { .flags = route == 1 ? SWP_FILE : 0, .swap_file = &file };
        task.refs = 1; memstall = nested; enters = leaves = 0;
        callback_error = 0; callback_uptodate = 1;
        int ret = swap_readpage(&p, sync);
        assert(ret == (route == 3 ? -ENOMEM : 0));
        assert(!p.locked && task.refs == 1);
        assert(enters == hot && leaves == hot && memstall == nested);
        if (route == 4) assert(!bio_storage.refs);
        cases++;
    }
    printf("Swap PSI route/nesting/disabled/flag-change cases: %u PASS\n", cases);
}
static void test_compaction(void)
{
    unsigned cases = 0;
    int retries[] = {0, 4, 16, 17};
    struct alloc_context ac;
    for (int order = 0; order <= 7; order++)
    for (int result = COMPACT_NOT_SUITABLE_ZONE; result <= COMPACT_SUCCESS; result++)
    for (int priority = MIN_COMPACT_PRIORITY; priority <= INIT_COMPACT_PRIORITY; priority++)
    for (unsigned ri = 0; ri < sizeof(retries)/sizeof(*retries); ri++)
    for (int lc = 0; lc < 2; lc++)
    for (int sz = 0; sz < 2; sz++) {
        enum compact_priority p = priority;
        int r = retries[ri], er = r, ep = priority;
        bool expected = false;
        int expected_suitable_calls = 0;
        lmk = lc; suitable = sz; suitable_calls = 0;
        if (order && lc && order <= 3) expected = true;
        else if (order) {
            if (result == COMPACT_SUCCESS) er++;
            bool raise = result == COMPACT_COMPLETE || result == COMPACT_DEFERRED ||
                         result == COMPACT_CONTENDED || result == COMPACT_PARTIAL_SKIPPED;
            if (result == COMPACT_SKIPPED) {
                expected = sz; expected_suitable_calls = 1;
            } else {
                if (!raise && er <= (order > 3 ? 4 : 16)) expected = true;
                else if (priority > (order > 3 ? MIN_COMPACT_COSTLY_PRIORITY : MIN_COMPACT_PRIORITY)) {
                    ep--; er = 0; expected = true;
                }
            }
        }
        bool ret = should_compact_retry(&ac, order, 0, result, &p, &r);
        assert(ret == expected && r == er && (int)p == ep);
        assert(suitable_calls == expected_suitable_calls);
        cases++;
    }
    for (int result = COMPACT_NOT_SUITABLE_ZONE; result <= COMPACT_SUCCESS; result++) {
        int expected = result == COMPACT_COMPLETE ? COMPACTION_FAILED :
            (result == COMPACT_SKIPPED || result == COMPACT_DEFERRED ||
             result == COMPACT_CONTENDED || result == COMPACT_PARTIAL_SKIPPED) ?
                COMPACTION_WITHDRAWN : COMPACTION_PROGRESS;
        assert(compact_result_to_feedback(result) == expected);
    }
    lmk = false; suitable = true;
    int withdrawn[] = {COMPACT_DEFERRED, COMPACT_CONTENDED, COMPACT_PARTIAL_SKIPPED};
    for (int order = 1; order <= 4; order += 3)
    for (unsigned i = 0; i < sizeof(withdrawn)/sizeof(*withdrawn); i++) {
        enum compact_priority p = INIT_COMPACT_PRIORITY;
        int r = 0, calls = 0;
        while (should_compact_retry(&ac, order, 0, withdrawn[i], &p, &r)) assert(++calls <= 2);
        assert((int)p == (order > 3 ? MIN_COMPACT_COSTLY_PRIORITY : MIN_COMPACT_PRIORITY));
    }
    printf("Compaction retry cases: %u + feedback/escalation PASS\n", cases);
}
static void test_shrinkers(void)
{
    unsigned cases = 0;
    long sizes[] = {0, 1, 2, 15, 127, 128, 129, 1023, 1024, 4096, 1000000};
    long debt[] = {0, 1, 127, 4096};
    for (unsigned si = 0; si < sizeof(sizes)/sizeof(*sizes); si++)
    for (int seeks = 0; seeks <= 4; seeks++)
    for (int priority = 0; priority <= 12; priority++)
    for (unsigned di = 0; di < sizeof(debt)/sizeof(*debt); di++)
    for (kswapd = 0; kswapd < 2; kswapd++)
    for (stop_scan = 0; stop_scan < 2; stop_scan++) {
        struct shrinker s = { .count_objects = count_objects, .scan_objects = scan_objects,
                             .seeks = seeks, .nr_deferred = { debt[di] } };
        struct shrink_control sc = {0};
        freeable_objects = sizes[si]; counted_scans = 0;
        traced_delta = 0; traced_target = 0;
        unsigned long freed = do_shrink_slab(&sc, &s, priority);
        if (!freeable_objects) { assert(!freed && s.nr_deferred[0] == debt[di]); cases++; continue; }
        unsigned long long delta = seeks ? ((sizes[si] >> priority) * 4ULL) / seeks : sizes[si] / 2;
        long target = debt[di] + delta;
        if (delta < (unsigned long long)(sizes[si] / 4) && target > sizes[si] / 2) target = sizes[si] / 2;
        if (target > sizes[si] * 2) target = sizes[si] * 2;
        long scanned = 0, remain = target;
        while (!stop_scan && (remain > (kswapd ? 0 : 128) || remain >= sizes[si])) {
            long n = remain < 128 ? remain : 128; assert(n > 0);
            remain -= n; scanned += n;
        }
        long deferred = debt[di] + delta;
        deferred = deferred >= scanned ? deferred - scanned : 0;
        assert(traced_delta == delta && traced_target == target);
        assert(freed == (unsigned long)scanned && counted_scans == scanned);
        assert(s.nr_deferred[0] == deferred);
        cases++;
    }
    printf("Shrinker zero/positive seeks/debt/batching/stop cases: %u PASS\n", cases);
}
static void test_vmstat(void)
{
    for (system_state = 0; system_state < 3; system_state++)
    for (pending = 0; pending < 2; pending++)
    for (updates_needed = 0; updates_needed < 2; updates_needed++) {
        refreshed = 0; quiet_vmstat();
        assert(refreshed == (system_state == SYSTEM_RUNNING && pending && updates_needed));
    }
    puts("quiet_vmstat branch outcomes: 12 PASS");
}
int main(void)
{
    test_filemap(); test_readahead(); test_swap(); test_compaction(); test_shrinkers(); test_vmstat();
    return 0;
}
