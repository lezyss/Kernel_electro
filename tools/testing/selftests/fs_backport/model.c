/* SPDX-License-Identifier: GPL-2.0 */
/* Extracted production functions/branches; single-threaded callback mocks. */
#undef NDEBUG
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define __acquires(x)
#define __releases(x)
#define unlikely(x) (x)
#define likely(x) (x)
#define WARN_ON(x) ((void)(x))
#define WARN(x, ...) ((void)(x))
#define EXPORT_SYMBOL(x)
#define smp_mb() ((void)0)
#define WRITE 1
#define I_DIRTY_INODE 3U
#define I_DIRTY_PAGES 4U
#define I_DIRTY_TIME 8U
#define I_DIRTY 7U
#define I_DIRTY_ALL 15U
#define I_SYNC 16U
#define I_SYNC_QUEUED 32U
#define I_WILL_FREE 64U
#define I_FREEING 128U
#define WB_SYNC_ALL 1
#define PAGECACHE_TAG_WRITEBACK 1
#define WB_registered 1
#define S_ISBLK(mode) ((mode) == 1)
struct lock {
  bool held, inode;
};
struct list_head {
  int dummy;
};
struct backing_dev_info {
  const char *name;
};
struct bdi_writeback {
  struct lock list_lock;
  struct list_head b_dirty, b_dirty_time;
  struct backing_dev_info *bdi;
  unsigned long state;
};
struct address_space {
  bool tagged;
};
struct inode;
struct super_operations {
  void (*dirty_inode)(struct inode *, int);
};
struct super_block {
  struct super_operations *s_op;
  const char *s_id;
};
struct ext_info {
  unsigned i_cluster_size;
};
struct inode {
  struct lock i_lock;
  unsigned i_state, i_mode;
  int i_count;
  bool unhashed, atomic, inline_data;
  unsigned long dirtied_when, dirtied_time_when, i_ino;
  struct address_space *i_mapping;
  struct super_block *i_sb;
  struct bdi_writeback *i_wb;
};
struct writeback_control {
  int sync_mode;
};
static struct inode *active_inode;
static unsigned handoff_state;
static bool inject_handoff;
static unsigned dels, moves, writes, wakes, enqueues, redirty;
static int wb_refs;
static struct backing_dev_info bdi = {"test"};
static struct bdi_writeback global_wb = {.bdi = &bdi};
static struct super_operations super_ops;
static struct super_block super = {.s_op = &super_ops, .s_id = "test"};
static unsigned long jiffies = 100;
static void spin_lock(struct lock *l) {
  assert(!l->held);
  l->held = true;
}
static void spin_unlock(struct lock *l) {
  assert(l->held);
  l->held = false;
  if (inject_handoff && l->inode) {
    active_inode->i_state |= handoff_state;
    inject_handoff = false;
  }
}
static int atomic_read(int *v) { return *v; }
static struct bdi_writeback *inode_to_wb(struct inode *i) { return i->i_wb; }
static void wb_get(struct bdi_writeback *w) { wb_refs++; }
static void wb_put(struct bdi_writeback *w) {
  assert(wb_refs > 0);
  wb_refs--;
}
static void cpu_relax(void) {}
static bool mapping_tagged(struct address_space *m, int tag) {
  return m->tagged;
}
static void __inode_wait_for_writeback(struct inode *i) {
  assert(i->i_lock.held);
  i->i_state &= ~I_SYNC;
}
static void wbc_attach_and_unlock_inode(struct writeback_control *w,
                                        struct inode *i) {
  spin_unlock(&i->i_lock);
}
static void wbc_detach_inode(struct writeback_control *w) {}
static int __writeback_single_inode(struct inode *i,
                                    struct writeback_control *w) {
  assert(i->i_state & I_SYNC);
  i->i_state = (i->i_state & ~I_DIRTY_ALL) | redirty;
  writes++;
  return -ENOSPC;
}
static void inode_sync_complete(struct inode *i) {
  assert(i->i_lock.held);
  i->i_state &= ~I_SYNC;
}
static void inode_io_list_del_locked(struct inode *i, struct bdi_writeback *w) {
  assert(i->i_lock.held && w->list_lock.held);
  assert(!(i->i_state & I_FREEING));
  dels++;
  i->i_state &= ~I_SYNC_QUEUED;
}
static bool inode_io_list_move_locked(struct inode *i, struct bdi_writeback *w,
                                      struct list_head *l) {
  assert(w->list_lock.held);
  assert(!(i->i_state & (I_FREEING | I_WILL_FREE)));
  moves++;
  return true;
}
static void inode_attach_wb(struct inode *i, void *p) {
  assert(i->i_lock.held);
}
static bool inode_unhashed(struct inode *i) { return i->unhashed; }
static bool bdi_cap_writeback_dirty(struct backing_dev_info *b) { return true; }
static bool test_bit(int bit, unsigned long *state) { return true; }
static void wb_wakeup_delayed(struct bdi_writeback *w) { wakes++; }
#define trace_writeback_mark_inode_dirty(...) ((void)0)
#define trace_writeback_dirty_inode_start(...) ((void)0)
#define trace_writeback_dirty_inode(...) ((void)0)
#define trace_writeback_dirty_inode_enqueue(...) (enqueues++)
/* PRODUCTION_WRITEBACK */

struct file;
struct poll_table_struct {
  unsigned long _key;
};
typedef struct poll_table_struct poll_table;
struct file_operations {
  unsigned (*poll)(struct file *, poll_table *);
};
struct file {
  long f_count;
  struct file_operations *f_op;
  struct inode *inode;
};
struct epitem {
  struct {
    struct file *file;
  } ffd;
  struct {
    unsigned events;
  } event;
};
#define DEFAULT_POLLMASK 0x145U
static unsigned polls, file_puts;
static unsigned poll_result;
static bool close_during_poll;
static int atomic_long_inc_not_zero(long *p) {
  if (!*p)
    return 0;
  (*p)++;
  return 1;
}
static void fput(struct file *f) {
  assert(f->f_count > 0);
  f->f_count--;
  file_puts++;
}
static unsigned poll_callback(struct file *f, poll_table *pt) {
  assert(f->f_count >= 2);
  polls++;
  if (close_during_poll)
    f->f_count--;
  return poll_result;
}
/* PRODUCTION_EPOLL */

/* Locking, inode ownership and compression-loop branch models. */
typedef unsigned long pgoff_t;
struct f2fs_sb_info {
  bool op_held;
  unsigned flags;
};
struct dnode_of_data {
  unsigned ofs_in_node;
  void *node_page;
};
static struct f2fs_sb_info f2;
static struct ext_info ext;
#define F2FS_I(i) (&ext)
#define SBI_NEED_FSCK 1
#define KERN_ERR ""
#define EFSCORRUPTED 117
#define LOOKUP_NODE 0
#define ADDRS_PER_PAGE(page, inode) 4UL
#define min(a, b)                                                              \
  ({                                                                           \
    __auto_type _a = (a);                                                      \
    __auto_type _b = (b);                                                      \
    _a < _b ? _a : _b;                                                         \
  })
#define round_up(x, a) (((x) + (a) - 1) & ~((a) - 1))
static unsigned lookups, mutations, node_puts, lock_calls, unlock_calls;
static int lookup_plan[4], mutation_plan[4];
static bool node_held;
static void f2fs_lock_op(struct f2fs_sb_info *s) {
  assert(!s->op_held);
  s->op_held = true;
  lock_calls++;
}
static void f2fs_unlock_op(struct f2fs_sb_info *s) {
  assert(s->op_held && !node_held);
  s->op_held = false;
  unlock_calls++;
}
static void set_new_dnode(struct dnode_of_data *dn, struct inode *i, void *p,
                          void *q, unsigned ofs) {
  assert(f2.op_held);
  dn->ofs_in_node = 0;
  dn->node_page = dn;
}
static int f2fs_get_dnode_of_data(struct dnode_of_data *dn, pgoff_t idx,
                                  int mode) {
  assert(f2.op_held && lookups < 4);
  int ret = lookup_plan[lookups++];
  node_held = !ret;
  return ret;
}
static pgoff_t f2fs_get_next_page_offset(struct dnode_of_data *dn,
                                         pgoff_t idx) {
  assert(!f2.op_held && !node_held);
  return idx + 4;
}
static int mutate_blocks(struct dnode_of_data *dn, pgoff_t count) {
  assert(f2.op_held && node_held);
  mutations++;
  return mutation_plan[lookups - 1] ? -EFSCORRUPTED : (int)count;
}
#define release_compress_blocks mutate_blocks
#define reserve_compress_blocks mutate_blocks
static void f2fs_put_dnode(struct dnode_of_data *dn) {
  assert(f2.op_held && node_held);
  node_held = false;
  node_puts++;
}
static int result_ret;
static unsigned result_blocks;
static struct inode compress_inode;
static void run_release(void) {
  struct inode *inode = &compress_inode;
  struct f2fs_sb_info *sbi = &f2;
  (void)sbi;
  pgoff_t page_idx = 0, last_idx = 16;
  unsigned released_blocks = 0;
  int ret = 0;
  /* PRODUCTION_RELEASE */
  result_ret = ret;
  result_blocks = released_blocks;
}
static void run_reserve(void) {
  struct inode *inode = &compress_inode;
  struct f2fs_sb_info *sbi = &f2;
  (void)sbi;
  pgoff_t page_idx = 0, last_idx = 16;
  unsigned reserved_blocks = 0;
  int ret = 0;
  /* PRODUCTION_RESERVE */
  result_ret = ret;
  result_blocks = reserved_blocks;
}
static int inode_refs, gc_logs, gc_migrated;
static bool f2fs_has_inline_data(struct inode *i) {
  assert(inode_refs > 0);
  return i->inline_data;
}
static void set_sbi_flag(struct f2fs_sb_info *s, unsigned flag) {
  s->flags |= flag;
}
static void iput(struct inode *i) {
  assert(inode_refs > 0);
  inode_refs--;
  i->i_ino = 0;
}
#define printk_ratelimited(...)                                                \
  do {                                                                         \
    assert(inode_refs > 0);                                                    \
    gc_logs++;                                                                 \
  } while (0)
static void gc_one(struct inode *inode) {
  struct f2fs_sb_info *sbi = &f2;
  for (unsigned once = 0; once < 1; once++) {
    /* PRODUCTION_GC */
    gc_migrated++;
    iput(inode);
  }
}
static bool deny_dst_lock;
static void inode_lock(struct inode *i) { spin_lock(&i->i_lock); }
static bool inode_trylock(struct inode *i) {
  if (deny_dst_lock)
    return false;
  inode_lock(i);
  return true;
}
static void inode_unlock(struct inode *i) { spin_unlock(&i->i_lock); }
static bool f2fs_is_atomic_file(struct inode *i) {
  assert(i->i_lock.held);
  return i->atomic;
}
static unsigned updates, mount_refs;
static void mnt_drop_write_file(struct file *f) {
  assert(mount_refs == 1);
  mount_refs--;
}
static int move_gate(struct inode *src, struct inode *dst) {
  int ret = 0;
  /* PRODUCTION_MOVE_PREFIX */
  assert(!src->atomic && !dst->atomic);
  ret = 0;
  updates++;
  /* PRODUCTION_MOVE_SUFFIX */
}
static int pin_gate(struct inode *inode) {
  struct file file = {.inode = inode};
  struct file *filp = &file;
  int ret = 0;
  inode_lock(inode);
  mount_refs++;
  /* PRODUCTION_PIN */
  assert(!inode->atomic);
  updates++;
  /* PRODUCTION_PIN_CLEANUP */
}

static void reset_wb(struct inode *i) {
  assert(!i->i_lock.held && !global_wb.list_lock.held && wb_refs == 0);
  dels = moves = writes = wakes = enqueues = 0;
  inject_handoff = false;
  handoff_state = 0;
  active_inode = i;
  i->i_wb = &global_wb;
  i->i_lock.inode = true;
}
static void test_writeback(void) {
  unsigned cases = 0;
  struct address_space mapping;
  for (unsigned state = 0; state < 256; state++)
    for (unsigned sync = 0; sync < 2; sync++)
      for (unsigned tagged = 0; tagged < 2; tagged++)
        for (redirty = 0; redirty < 16; redirty++) {
          struct inode i = {.i_state = state,
                            .i_count =
                                (state & (I_FREEING | I_WILL_FREE)) ? 0 : 1,
                            .i_mapping = &mapping,
                            .i_sb = &super};
          mapping.tagged = tagged;
          struct writeback_control w = {.sync_mode = sync};
          reset_wb(&i);
          int ret = writeback_single_inode(&i, &w);
          assert(!i.i_lock.held && !global_wb.list_lock.held && wb_refs == 0);
          bool expected_write = !((state & I_SYNC) && !sync) &&
                                ((state & I_DIRTY_ALL) || (sync && tagged));
          assert(writes == expected_write &&
                 ret == (expected_write ? -ENOSPC : 0));
          if (expected_write)
            assert(dels == (!(state & I_FREEING) && !redirty));
          else
            assert(dels == 0);
          cases++;
        }
  printf("Writeback completion/freeing cases CGWB=%d: %u PASS\n", CGWB, cases);
  cases = 0;
  for (unsigned state = 0; state < 256; state++)
    for (int flags = 1; flags < 16; flags++)
      for (unsigned handoff = 0; handoff < 3; handoff++)
        for (unsigned mode = 0; mode < 4; mode++) {
          struct inode i = {.i_state = state,
                            .i_count = 1,
                            .i_mapping = &mapping,
                            .i_sb = &super,
                            .i_mode = mode & 1,
                            .unhashed = !!(mode & 2)};
          reset_wb(&i);
          handoff_state = handoff == 1   ? I_WILL_FREE
                          : handoff == 2 ? I_FREEING
                                         : 0;
          inject_handoff = true;
          __mark_inode_dirty(&i, flags);
          assert(!i.i_lock.held && !global_wb.list_lock.held && wb_refs == 0);
          assert(dels == 0);
          if (i.i_state & (I_FREEING | I_WILL_FREE))
            assert(moves == 0 && wakes == 0 && enqueues == 0);
          assert(moves == wakes && moves == enqueues && moves <= 1);
          if ((state & I_DIRTY_INODE) && !(state & I_DIRTY_TIME) &&
              flags == I_DIRTY_TIME)
            assert(!(i.i_state & I_DIRTY_TIME));
          cases++;
        }
  inject_handoff = false;
  printf("Dirty-inode handoff/list/legacy-time cases CGWB=%d: %u PASS\n", CGWB,
         cases);
}
static void test_epoll(void) {
  unsigned cases = 0;
  struct file_operations ops = {.poll = poll_callback};
  for (long refs = 0; refs < 4; refs++)
    for (unsigned mask = 0; mask < 256; mask++)
      for (unsigned has_poll = 0; has_poll < 2; has_poll++)
        for (unsigned closing = 0; closing < 2; closing++) {
          struct file f = {.f_count = refs, .f_op = &ops};
          struct epitem epi = {.ffd.file = &f, .event.events = mask};
          poll_table pt = {._key = 0xfeed};
          ops.poll = has_poll ? poll_callback : NULL;
          polls = file_puts = 0;
          poll_result = 0xabcdef;
          close_during_poll = closing && refs > 0;
          unsigned got = ep_item_poll(&epi, &pt);
          assert(got ==
                 (refs ? ((has_poll ? poll_result : DEFAULT_POLLMASK) & mask)
                       : 0));
          assert(file_puts == (refs > 0) && polls == ((refs > 0) && has_poll));
          assert(f.f_count == refs - ((refs > 0) && has_poll && closing));
          assert(pt._key == (refs ? mask : 0xfeed));
          cases++;
        }
  printf("Epoll temporary-reference/mask/close cases: %u PASS\n", cases);
}
static void test_f2fs(void) {
  unsigned cases = 0;
  ext.i_cluster_size = 2;
  for (unsigned reserve = 0; reserve < 2; reserve++)
    for (unsigned plan = 0; plan < 1296; plan++) {
      unsigned p = plan;
      int expected_ret = 0;
      unsigned expected_blocks = 0, expected_lookups = 0,
               expected_mutations = 0;
      bool stopped = false;
      for (unsigned i = 0; i < 4; i++) {
        unsigned x = p % 6;
        p /= 6;
        lookup_plan[i] = (x % 3) == 1 ? -ENOENT : (x % 3) == 2 ? -EIO : 0;
        mutation_plan[i] = x / 3;
        if (stopped)
          continue;
        expected_lookups++;
        if (lookup_plan[i] == -ENOENT) {
          expected_ret = 0;
          continue;
        }
        if (lookup_plan[i]) {
          expected_ret = -EIO;
          stopped = true;
          continue;
        }
        expected_mutations++;
        if (mutation_plan[i]) {
          expected_ret = -EFSCORRUPTED;
          stopped = true;
          continue;
        }
        expected_ret = 4;
        expected_blocks += 4;
      }
      memset(&f2, 0, sizeof(f2));
      lookups = mutations = node_puts = lock_calls = unlock_calls = 0;
      node_held = false;
      if (reserve)
        run_reserve();
      else
        run_release();
      assert(!f2.op_held && !node_held && lock_calls == unlock_calls &&
             lock_calls == expected_lookups);
      assert(lookups == expected_lookups && mutations == expected_mutations &&
             node_puts == mutations);
      assert(result_ret == expected_ret && result_blocks == expected_blocks);
      cases++;
    }
  printf("Compression dnode/checkpoint-lock branch cases: %u PASS\n", cases);
  for (unsigned inlined = 0; inlined < 2; inlined++) {
    struct inode i = {.inline_data = inlined, .i_ino = 42};
    f2.flags = 0;
    inode_refs = 1;
    gc_logs = gc_migrated = 0;
    gc_one(&i);
    assert(inode_refs == 0 && gc_logs == inlined && gc_migrated == !inlined &&
           f2.flags == (inlined ? SBI_NEED_FSCK : 0));
  }
  puts("GC inline-data/reference/diagnostic ordering: PASS");
  cases = 0;
  for (unsigned a = 0; a < 2; a++)
    for (unsigned b = 0; b < 2; b++)
      for (unsigned same = 0; same < 2; same++)
        for (unsigned deny = 0; deny < 2; deny++) {
          struct inode src = {.atomic = a}, dst = {.atomic = b};
          struct inode *d = same ? &src : &dst;
          updates = 0;
          deny_dst_lock = deny;
          int ret = move_gate(&src, d);
          assert(ret == ((!same && deny)    ? -EBUSY
                         : (a || d->atomic) ? -EINVAL
                                            : 0));
          assert(updates == (ret == 0) && !src.i_lock.held && !dst.i_lock.held);
          cases++;
        }
  for (unsigned a = 0; a < 2; a++) {
    struct inode i = {.atomic = a};
    updates = mount_refs = 0;
    int ret = pin_gate(&i);
    assert(ret == (a ? -EINVAL : 0) && updates == !a && mount_refs == 0 &&
           !i.i_lock.held);
    cases++;
  }
  printf("Atomic-file ioctl guard/unwind cases: %u PASS\n", cases);
}
int main(void) {
  setbuf(stdout, NULL);
  test_writeback();
  test_epoll();
  test_f2fs();
  return 0;
}
