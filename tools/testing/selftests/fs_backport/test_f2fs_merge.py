#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""F2FS selective merge checks. Extracted/mock tests are NOT filesystem stress."""
import argparse
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
from test_backport import ROOT, function, integration


IPU_STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define PAGE_SIZE 4096
#define BIO_MAX_PAGES 256
#define GFP_NOIO 0
#define EFSCORRUPTED 990
#define META_GENERIC 0
#define DATA_GENERIC 1
#define DATA 0
#define WB_DATA_TYPE(p) wb_type(p)
enum temp_type { HOT, WARM, COLD, NR_TEMP_TYPE };
struct page { struct { void *host; } *mapping; unsigned long index; int bounce; };
struct bio { int refs; };
struct list_head { struct list_head *next, *prev; };
struct bio_entry { struct bio *bio; struct list_head list; };
struct f2fs_bio_info { struct list_head bio_list; int bio_list_lock; };
struct f2fs_sb_info { struct f2fs_bio_info *write_io[1]; };
struct f2fs_io_info {
 struct f2fs_sb_info *sbi; struct page *page, *encrypted_page;
 struct bio **bio; unsigned long *last_block, new_blkaddr;
 void *io_wbc; int op, op_flags, temp;
};
static int valid, account, counted, retries, published, submitted, freed;
static struct bio cached;
static struct page *original;
#define list_for_each_entry(pos, head, member) \
 for (struct list_head *it=(head)->next; \
      it!=(head) && ((pos)=(void *)((char *)it - offsetof(struct bio_entry, member)),1); \
      it=it->next)
static int list_empty(struct list_head *h) { return h->next==h; }
#define down_read(p) ((void)(p))
#define up_read(p) ((void)(p))
#define down_write(p) ((void)(p))
#define up_write(p) ((void)(p))
static int __has_merged_page(struct bio *b, void *i, struct page *p, int n)
{ (void)b;(void)i;(void)n; assert(p);return 0; }
static void del_bio_entry(struct bio_entry *b)
{ b->list.prev->next=b->list.next;b->list.next->prev=b->list.prev; }
static void __submit_bio(struct f2fs_sb_info *s, struct bio *b,int t)
{ (void)s;(void)b;(void)t;submitted++; }
static void bio_put(struct bio *b) { assert(b->refs>0);b->refs--; }
static int f2fs_is_valid_blkaddr(struct f2fs_sb_info *s,unsigned long b,int t)
{ (void)s;(void)b;(void)t;return valid; }
#define __is_meta_io(f) 0
#define trace_f2fs_submit_page_bio(p,f) ((void)0)
#define f2fs_trace_ios(f,n) ((void)0)
static int wb_type(struct page *p) { assert(p==original);return 0; }
static void wbc_account_io(void *w, struct page *p, int n)
{ (void)w; assert(p==original && !freed && n==PAGE_SIZE);account++; }
static void inc_page_count(struct f2fs_sb_info *s,int n)
{ (void)s;(void)n; assert(!freed);counted++; }
static struct bio *__bio_alloc(struct f2fs_io_info *f,int n)
{ (void)f;(void)n;cached.refs=2;return &cached; }
#define f2fs_set_bio_crypt_ctx(...) ((void)0)
#define __attach_io_flag(f) ((void)0)
#define bio_set_op_attrs(...) ((void)0)
static void publish(struct page *p)
{ assert(account==1 && counted==1);published++;if(p->bounce)freed=1; }
static void add_bio_entry(struct f2fs_sb_info *s,struct bio *b,struct page *p,int t)
{ (void)s;(void)b;(void)t;publish(p); }
static int add_ipu_page(struct f2fs_io_info *f,struct bio **b,struct page *p)
{ (void)f;if(retries){retries--;bio_put(*b);*b=NULL;return -1;}publish(p);return 0; }
'''

DRAIN_STUBS = r'''
#define LIST_HEAD(name) struct list_head name={&name,&name}
static void list_splice_init(struct list_head *h,struct list_head *to)
{
 if(list_empty(h))return;
 to->next=h->next;to->prev=h->prev;
 to->next->prev=to;to->prev->next=to;h->next=h->prev=h;
}
#define list_for_each_entry_safe(pos,tmp,head,member) \
 for(struct list_head *it=(head)->next,*next=NULL; \
  it!=(head) && (next=it->next, \
   (pos)=(void *)((char *)it - offsetof(struct bio_entry, member)), \
   (tmp)=(void *)((char *)next - offsetof(struct bio_entry, member)), \
   (void)(tmp),1); it=next)
'''

IPU_MAIN = r'''
int main(void) {
 struct f2fs_bio_info ios[NR_TEMP_TYPE]={0};
 struct f2fs_sb_info s={ .write_io={ios} };
 struct page p={0}, bounce={.bounce=1};
 struct { void *host; } mapping={0};
 struct bio *bio=NULL;unsigned long last=0;
 struct f2fs_io_info f={.sbi=&s,.page=&p,.bio=&bio,.last_block=&last,
                        .new_blkaddr=7,.io_wbc=&p};
 p.mapping=(void *)&mapping;original=&p;
 for(int i=0;i<NR_TEMP_TYPE;i++)
  ios[i].bio_list.next=ios[i].bio_list.prev=&ios[i].bio_list;
 /* No selector must never inspect even a nonempty list. */
 struct bio_entry be={.bio=&cached};
 be.list.next=be.list.prev=&ios[0].bio_list;
 ios[0].bio_list.next=ios[0].bio_list.prev=&be.list;
 f2fs_submit_merged_ipu_write(&s,NULL,NULL);
 f2fs_submit_merged_ipu_write(&s,&bio,NULL);assert(!submitted);
 cached.refs=2;bio=&cached;
 f2fs_submit_merged_ipu_write(&s,&bio,NULL);
 assert(submitted==1 && bio==NULL && cached.refs==1);
 for(int enc=0;enc<2;enc++)for(int cached_bio=0;cached_bio<2;cached_bio++)
 for(int retry=0;retry<3;retry++) {
  account=counted=published=freed=0;valid=1;
  cached.refs=2;bio=cached_bio?&cached:NULL;retries=retry;
  f.encrypted_page=enc?&bounce:NULL;
  assert(!f2fs_merge_page_bio(&f));
  assert(account==1 && counted==1 && published==1 && last==7);
  assert(freed==enc);
 }
 struct bio bios[NR_TEMP_TYPE];struct bio_entry entries[NR_TEMP_TYPE];
 for(int i=0;i<NR_TEMP_TYPE;i++) {
  bios[i].refs=2;entries[i].bio=&bios[i];
  entries[i].list.next=entries[i].list.prev=&ios[i].bio_list;
  ios[i].bio_list.next=ios[i].bio_list.prev=&entries[i].list;
 }
 int before=submitted;
 f2fs_submit_merged_ipu_write_all(&s);
 assert(submitted==before+NR_TEMP_TYPE);
 for(int i=0;i<NR_TEMP_TYPE;i++) {
  assert(list_empty(&ios[i].bio_list));bio=&bios[i];
  f2fs_submit_merged_ipu_write(&s,&bio,NULL);
  assert(bio==NULL && bios[i].refs==1);
 }
 f2fs_submit_merged_ipu_write_all(&s);assert(submitted==before+NR_TEMP_TYPE);
 valid=0;account=counted=published=freed=0;
 assert(f2fs_merge_page_bio(&f)==-EFSCORRUPTED);
 assert(!account && !counted && !published);
 puts("IPU extracted-source selector/accounting/immediate-completion/retry tests: PASS");
}
'''


def stage_a(root):
    data = (root / 'fs/f2fs/data.c').read_text()
    merge = function(data, 'f2fs_merge_page_bio')
    assert merge.index('wbc_account_io(fio->io_wbc, fio->page,') < merge.index('alloc_new:')
    assert merge.index('inc_page_count(fio->sbi, WB_DATA_TYPE(fio->page))') < merge.index('alloc_new:')
    assert 'if (bio && *bio)\n\t\t\tf2fs_submit_merged_ipu_write' in data
    inplace = function((root / 'fs/f2fs/segment.c').read_text(), 'f2fs_inplace_write_data')
    assert 'if (!err) {\n\t\tfio->submitted = 1;' in inplace
    main, drain = IPU_MAIN, ''
    if 'void f2fs_submit_merged_ipu_write_all(' in data:
        drain = DRAIN_STUBS + function(data, 'f2fs_submit_merged_ipu_write_all')
    else:
        # The A boundary predates the global drain helper introduced in B1.
        start = main.index(' struct bio bios[NR_TEMP_TYPE]')
        end = main.index(' valid=0;account=counted=published=freed=0;')
        main = main[:start] + main[end:]
    return IPU_STUBS + drain + function(data, 'f2fs_submit_merged_ipu_write') + '\n' + merge + main


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cc', default='clang')
    ap.add_argument('--stage', choices=['A', 'B1', 'B2'], default='B2')
    ap.add_argument('--negative', choices=['null-selector', 'missing-accounting',
                    'bounce-accounting', 'no-ipu-drain', 'gc-freezer-window',
                    'cp-late-counter', 'cp-no-umount-protection',
                    'cp-no-lifetime-gate', 'cp-drop-error'])
    args = ap.parse_args()
    integration(ROOT)
    sources = [('ipu', stage_a(ROOT))]
    if args.stage != 'A':
        sources.append(('gc', stage_b1(ROOT)))
    if args.stage == 'B2':
        sources.append(('cp', stage_b2(ROOT)))
    if args.negative:
        sources = [mutate(sources, args.negative)]
    with tempfile.TemporaryDirectory(prefix='f2fs-merge-') as t:
        for name, source in sources:
            c, exe = Path(t) / (name + '.c'), Path(t) / name
            c.write_text(source)
            subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2', '-UNDEBUG',
                           '-Wall', '-Wextra', '-Werror', '-pthread',
                           '-fsanitize=undefined', '-fsanitize-trap=all',
                           str(c), '-o', str(exe)], check=True)
            run = subprocess.run([str(exe)], check=False, timeout=60,
                                 capture_output=bool(args.negative), text=True)
            if args.negative:
                assert run.returncode in [-signal.SIGABRT, -signal.SIGILL], run
                print('Negative mutant rejected:', args.negative)
            else:
                run.check_returncode()
    print('Stage', args.stage, 'checks: PASS (not a durability/concurrency proof)')


GC_STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sched.h>
#include <stdlib.h>
#include <stdio.h>
#define SB_FREEZE_WRITE 1
#define DATA 0
#define current ((void *)(uintptr_t)pthread_self())
#define READ_ONCE(x) atomic_load(&(x))
#define spin_lock(x) assert(!pthread_mutex_lock(x))
#define spin_unlock(x) assert(!pthread_mutex_unlock(x))
struct queue { pthread_mutex_t lock; pthread_cond_t cond; _Atomic int wakes; };
static void wake(struct queue *q) {
 assert(!pthread_mutex_lock(&q->lock));q->wakes++;
 assert(!pthread_cond_broadcast(&q->cond));assert(!pthread_mutex_unlock(&q->lock));
}
#define wake_up(q) wake(q)
#define wake_up_all(q) wake(q)
#define wait_event(q,condition) do { \
 assert(!pthread_mutex_lock(&(q).lock)); \
 while(!(condition))assert(!pthread_cond_wait(&(q).cond,&(q).lock)); \
 assert(!pthread_mutex_unlock(&(q).lock)); \
} while(0)
struct f2fs_gc_merge { pthread_mutex_t lock;struct queue wait;
 void *task;_Atomic unsigned long seq;_Atomic bool online,pending;bool paused; };
struct f2fs_gc_kthread { struct queue gc_wait_queue_head; };
struct f2fs_sb_info {struct f2fs_gc_merge gc_merge;
 struct {_Atomic(void *) task;} cprc_info;
 struct f2fs_gc_kthread *gc_thread;
 struct {struct { _Atomic int frozen;} s_writers;} *sb;
};
static _Atomic int opu,ipu,done;
static void f2fs_submit_merged_write(struct f2fs_sb_info *s,int t)
{ (void)s;(void)t;opu++; }
static void f2fs_submit_merged_ipu_write_all(struct f2fs_sb_info *s)
{ (void)s;ipu++; }
'''
GC_FREEZER = r'''
static struct f2fs_sb_info *freezer_sbi;
static bool freeze_requested,late_freeze,stopping;
static int freezer_calls;
static bool freezing(void *task) {(void)task;return freeze_requested;}
static bool kthread_should_stop(void) {return stopping;}
static bool kthread_freezable_should_stop(bool *was_frozen) {
 assert(freezer_sbi->gc_merge.paused && !freezer_sbi->gc_merge.pending);
 freezer_calls++;
 if(late_freeze)freeze_requested=true;
 /* A producer racing the freezer must synchronously fall back. */
 assert(!f2fs_gc_merge_request(freezer_sbi));
 *was_frozen=freeze_requested;return stopping;
}
'''

GC_MAIN = r'''
static void *request(void *arg) {
 assert(f2fs_gc_merge_request(arg));done++;return NULL;
}
static void init_queue(struct queue *q) {
 assert(!pthread_mutex_init(&q->lock,NULL));
 assert(!pthread_cond_init(&q->cond,NULL));q->wakes=0;
}
int main(void) {
 struct f2fs_sb_info s={0};typeof(*s.sb) sb={0};s.sb=&sb;
 assert(!pthread_mutex_init(&s.gc_merge.lock,NULL));init_queue(&s.gc_merge.wait);
 assert(!f2fs_gc_merge_request(&s));assert(opu==0 && ipu==0);
 for(int round=0;round<100;round++) {
  s.gc_thread=calloc(1,sizeof(*s.gc_thread));assert(s.gc_thread);
  init_queue(&s.gc_thread->gc_wait_queue_head);
  s.gc_merge.online=true;s.gc_merge.task=NULL;done=opu=ipu=0;
  enum {N=8};pthread_t reqs[N];
  for(int i=0;i<N;i++)assert(!pthread_create(&reqs[i],NULL,request,&s));
  while(s.gc_thread->gc_wait_queue_head.wakes!=N)sched_yield();
  assert(opu==N && ipu==N && s.gc_merge.pending && !done);
  wake_up_all(&s.gc_merge.wait); /* spurious wake cannot complete a request */
  assert(!done);
  if(round%2) {
   spin_lock(&s.gc_merge.lock);
   s.gc_merge.online=false;s.gc_merge.task=NULL;
   s.gc_merge.pending=false;s.gc_merge.seq++;
   spin_unlock(&s.gc_merge.lock);
   wake_up_all(&s.gc_merge.wait);
  } else finish_gc_merge(&s);
  for(int i=0;i<N;i++)assert(!pthread_join(reqs[i],NULL));
  assert(done==N && !s.gc_merge.pending);
  s.gc_merge.online=false;
  assert(!pthread_cond_destroy(&s.gc_thread->gc_wait_queue_head.cond));
  assert(!pthread_mutex_destroy(&s.gc_thread->gc_wait_queue_head.lock));
  free(s.gc_thread);s.gc_thread=NULL;
  assert(!f2fs_gc_merge_request(&s));
 }
 s.gc_merge.online=true;s.gc_merge.task=current;
 assert(f2fs_is_gc_thread(&s));assert(!f2fs_gc_merge_request(&s));
 s.gc_merge.task=NULL;sb.s_writers.frozen=SB_FREEZE_WRITE;
 assert(!f2fs_gc_merge_request(&s));
 sb.s_writers.frozen=0;freezer_sbi=&s;bool was_frozen=false;
 s.gc_merge.pending=true;
 assert(!gc_merge_freezable_should_stop(&s,&was_frozen));
 assert(s.gc_merge.pending && !was_frozen && !freezer_calls && !s.gc_merge.paused);
 finish_gc_merge(&s);late_freeze=true;
 assert(!gc_merge_freezable_should_stop(&s,&was_frozen));
 assert(was_frozen && freezer_calls==1 && !s.gc_merge.paused);
 s.gc_merge.pending=true;was_frozen=false;stopping=true;
 assert(gc_merge_freezable_should_stop(&s,&was_frozen));
 assert(!s.gc_merge.pending && !s.gc_merge.paused && freezer_calls==2);
 puts("GC extracted admission/batching/spurious-wake/stop/restart/self/freeze: 800 requests PASS");
}
'''


def stage_b1(root):
    gc = (root / 'fs/f2fs/gc.c').read_text()
    worker = function(gc, 'gc_thread_func')
    assert 'gc_merge_freezable_should_stop(sbi, &was_frozen)' in worker
    freezer = function(gc, 'gc_merge_freezable_should_stop')
    assert freezer.index('merge->paused = true') < freezer.index('kthread_freezable_should_stop') < freezer.index('merge->paused = false')
    assert 'finish_gc_merge(sbi);' in worker
    assert 'sync_mode, !foreground, NULL_SEGNO) && !foreground' in worker
    stop = function(gc, 'f2fs_stop_gc_thread')
    assert stop.index('online = false;') < stop.index('kthread_stop(') < stop.index('kvfree(gc_th)')
    req = function(gc, 'f2fs_gc_merge_request')
    assert req.index('f2fs_submit_merged_write(sbi, DATA)') < req.index('merge->pending = true;')
    assert req.index('f2fs_submit_merged_ipu_write_all') < req.index('merge->pending = true;')
    sup = (root / 'fs/f2fs/super.c').read_text()
    assert 'set_opt(sbi, GC_MERGE)' not in function(sup, 'default_options')
    assert '"gc_merge"' in sup and '"nogc_merge"' in sup
    return GC_STUBS + '\n'.join(function(gc, n) for n in
        ['finish_gc_merge', 'f2fs_is_gc_thread', 'f2fs_gc_merge_request']) + GC_FREEZER + function(gc, 'gc_merge_freezable_should_stop') + GC_MAIN


CP_STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sched.h>
#include <errno.h>
#define CP_SYNC 1
#define CP_FASTBOOT 2
#define DATA 0
#define SB_UNFROZEN 0
#define SB_FREEZE_WRITE 1
#define SB_FREEZE_FS 3
#define MERGE_CHECKPOINT 1
#define test_opt(s,o) atomic_load(&(s)->enabled)
#define MAJOR(d) ((void)(d),1)
#define MINOR(d) ((void)(d),2)
#define IOPRIO_CLASS_BE 2
#define IOPRIO_PRIO_VALUE(c,p) (((c)<<13)|(p))
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define READ_ONCE(p) __atomic_load_n(&(p),__ATOMIC_ACQUIRE)
#define WRITE_ONCE(p,v) __atomic_store_n(&(p),(v),__ATOMIC_RELEASE)
typedef _Atomic int atomic_t;
#define atomic_set(p,v) atomic_store(p,v)
#define atomic_inc(p) ((void)atomic_fetch_add(p,1))
#define atomic_dec(p) assert(atomic_fetch_sub(p,1)>0)
struct rwsem {pthread_rwlock_t lock; _Atomic bool deny_try;};
struct queue {pthread_mutex_t lock;pthread_cond_t cond;_Atomic int wakes;};
struct completion {struct queue q;bool completed;};
struct llist_node {struct llist_node *next;};
struct llist_head {_Atomic(struct llist_node *) first;};
struct task_struct {pthread_t tid;_Atomic bool stop;int (*fn)(void *);void *data;bool gc;};
static _Thread_local struct task_struct *current;
static _Thread_local int super_read,super_write,intwrite,gate_read;
struct super_block {struct rwsem s_umount;
 struct {_Atomic int frozen;} s_writers;struct {dev_t bd_dev;} *s_bdev;};
struct ckpt_req_control {struct rwsem gate;struct task_struct *task;
 struct queue wait;struct llist_head issue_list;
 atomic_t queued_ckpt,issued_ckpt,total_ckpt,fallback_ckpt;};
struct f2fs_sb_info {struct ckpt_req_control cprc_info;
 struct super_block *sb;struct rwsem gc_lock;_Atomic bool enabled;};
struct cp_control {int reason;};
static struct f2fs_sb_info *global;
static _Atomic int opu,ipu,cp_calls,cp_error,fail_start,fail_prio,done;
static _Atomic bool dispatch_hold,fail_intwrite,quota_check;
static void init_rwsem(struct rwsem *s) {assert(!pthread_rwlock_init(&s->lock,NULL));s->deny_try=false;}
static void down_read(struct rwsem *s) {assert(!pthread_rwlock_rdlock(&s->lock));if(s==&global->sb->s_umount)super_read++;if(s==&global->cprc_info.gate)gate_read++;}
static void up_read(struct rwsem *s) {if(s==&global->cprc_info.gate){assert(gate_read);gate_read--;}if(s==&global->sb->s_umount){assert(super_read);super_read--;}assert(!pthread_rwlock_unlock(&s->lock));}
static void down_write(struct rwsem *s) {assert(!pthread_rwlock_wrlock(&s->lock));if(s==&global->sb->s_umount)super_write++;}
static void up_write(struct rwsem *s) {if(s==&global->sb->s_umount){assert(super_write);super_write--;}assert(!pthread_rwlock_unlock(&s->lock));}
static int down_read_trylock(struct rwsem *s) {
 assert(s==&global->sb->s_umount && intwrite);
 if(s->deny_try||pthread_rwlock_tryrdlock(&s->lock))return 0;
 super_read++;return 1;
}
static int __sb_start_write(struct super_block *sb,int level,bool wait) {
 assert(sb==global->sb && level==SB_FREEZE_FS && !wait && !intwrite && !super_read);
 if(fail_intwrite)return 0;intwrite++;return 1;
}
static void sb_end_intwrite(struct super_block *sb) {(void)sb;assert(intwrite && !super_read);intwrite--;}
static void init_waitqueue_head(struct queue *q) {
 assert(!pthread_mutex_init(&q->lock,NULL));assert(!pthread_cond_init(&q->cond,NULL));q->wakes=0;
}
static void wake_up(struct queue *q) {
 assert(!pthread_mutex_lock(&q->lock));q->wakes++;
 assert(!pthread_cond_broadcast(&q->cond));assert(!pthread_mutex_unlock(&q->lock));
}
static int kthread_should_stop(void) {return current && current->stop;}
#define wait_event_interruptible(q,condition) do { \
 assert(!pthread_mutex_lock(&(q).lock)); \
 while(!(condition) || (dispatch_hold && !kthread_should_stop())) \
  assert(!pthread_cond_wait(&(q).cond,&(q).lock)); \
 assert(!pthread_mutex_unlock(&(q).lock)); \
} while(0)
static void init_completion(struct completion *c) {init_waitqueue_head(&c->q);c->completed=false;}
static void complete(struct completion *c) {
 assert(!pthread_mutex_lock(&c->q.lock));assert(!c->completed);c->completed=true;
 assert(!pthread_cond_signal(&c->q.cond));assert(!pthread_mutex_unlock(&c->q.lock));
}
static void wait_for_completion(struct completion *c) {
 assert(!pthread_mutex_lock(&c->q.lock));
 while(!c->completed)assert(!pthread_cond_wait(&c->q.cond,&c->q.lock));
 assert(!pthread_mutex_unlock(&c->q.lock));
 assert(!pthread_cond_destroy(&c->q.cond));assert(!pthread_mutex_destroy(&c->q.lock));
}
static void init_llist_head(struct llist_head *h) {atomic_store(&h->first,NULL);}
static bool llist_empty(struct llist_head *h) {return atomic_load(&h->first)==NULL;}
static void llist_add(struct llist_node *n,struct llist_head *h) {
 assert(gate_read && opu>=global->cprc_info.queued_ckpt && ipu>=global->cprc_info.queued_ckpt);
 n->next=atomic_load(&h->first);
 while(!atomic_compare_exchange_weak(&h->first,&n->next,n)){}
}
static struct llist_node *llist_del_all(struct llist_head *h) {return atomic_exchange(&h->first,NULL);}
static struct llist_node *llist_reverse_order(struct llist_node *n) {
 struct llist_node *prev=NULL;while(n){struct llist_node *next=n->next;n->next=prev;prev=n;n=next;}return prev;
}
#define llist_for_each_entry_safe(pos,tmp,head,member) \
 for(struct llist_node *it=(head),*_saved=NULL; \
  it && (_saved=it->next, \
   (pos)=(void *)((char *)it - offsetof(struct ckpt_req, member)), \
   (tmp)=_saved?(void *)((char *)_saved - offsetof(struct ckpt_req, member)):NULL, \
   (void)(tmp),1);it=_saved)
static void f2fs_submit_merged_write(struct f2fs_sb_info *s,int t) {(void)s;(void)t;opu++;}
static void f2fs_submit_merged_ipu_write_all(struct f2fs_sb_info *s) {(void)s;ipu++;}
static bool f2fs_is_gc_thread(struct f2fs_sb_info *s) {(void)s;return current && current->gc;}
static int f2fs_write_checkpoint(struct f2fs_sb_info *s,struct cp_control *c) {
 assert(s==global && (c->reason==CP_SYNC||c->reason==CP_FASTBOOT));
 if(quota_check)assert(super_read||super_write);
 if(current==READ_ONCE(s->cprc_info.task))assert(super_read && intwrite);
 cp_calls++;return cp_error;
}
#define f2fs_bug_on(s,c) assert(!(c))
static void *trampoline(void *arg) {current=arg;current->fn(current->data);return NULL;}
static struct task_struct *kthread_run(int (*fn)(void *),void *data,const char *fmt,...) {
 (void)fmt;if(fail_start)return (void *)(intptr_t)-ENOMEM;
 struct task_struct *t=calloc(1,sizeof(*t));assert(t);t->fn=fn;t->data=data;
 assert(!pthread_create(&t->tid,NULL,trampoline,t));return t;
}
static int kthread_stop(struct task_struct *t) {
 assert(t && current!=t);t->stop=true;wake_up(&global->cprc_info.wait);
 assert(!pthread_join(t->tid,NULL));free(t);return 0;
}
static int set_task_ioprio(struct task_struct *t,int prio) {
 assert(t && prio==IOPRIO_PRIO_VALUE(IOPRIO_CLASS_BE,3));return fail_prio?-ENOMEM:0;
}
'''
CP_MAIN = r'''
static void *request(void *arg) {
 struct task_struct task={0};current=&task;
 int ret=f2fs_issue_checkpoint(arg,CP_SYNC);assert(ret==cp_error);done++;return NULL;
}
static _Atomic bool stop_entered;
static void *stopper(void *arg) {
 struct task_struct task={0};current=&task;stop_entered=true;
 f2fs_stop_ckpt_thread(arg);return NULL;
}
int main(void) {
 struct task_struct task={0};current=&task;
 struct super_block sb={0};typeof(*sb.s_bdev) bdev={0};sb.s_bdev=&bdev;
 struct f2fs_sb_info s={.sb=&sb};global=&s;s.enabled=true;
 init_rwsem(&sb.s_umount);init_rwsem(&s.gc_lock);f2fs_init_ckpt_req_control(&s);
 fail_start=1;assert(f2fs_start_ckpt_thread(&s)==-ENOMEM && !s.cprc_info.task);fail_start=0;
 fail_prio=1;assert(f2fs_start_ckpt_thread(&s)==-ENOMEM && !s.cprc_info.task);fail_prio=0;
 /* Controlled batches, including errors, concurrent stop and immediate reuse. */
 enum {N=12,ROUNDS=100};
 for(int round=0;round<ROUNDS;round++) {
  assert(!f2fs_start_ckpt_thread(&s));assert(!f2fs_start_ckpt_thread(&s));
  dispatch_hold=true;done=0;quota_check=true;cp_error=round%3?-EIO:0;
  int issued=s.cprc_info.issued_ckpt,completed=s.cprc_info.total_ckpt;
  int wakes=s.cprc_info.wait.wakes;pthread_t requests[N],stop;
  for(int i=0;i<N;i++)assert(!pthread_create(&requests[i],NULL,request,&s));
  while(s.cprc_info.wait.wakes<wakes+N)sched_yield();
  assert(s.cprc_info.queued_ckpt==N && !done);
  if(round%2){stop_entered=false;assert(!pthread_create(&stop,NULL,stopper,&s));while(!stop_entered)sched_yield();}
  dispatch_hold=false;wake_up(&s.cprc_info.wait);
  for(int i=0;i<N;i++)assert(!pthread_join(requests[i],NULL));
  assert(done==N && !s.cprc_info.queued_ckpt && s.cprc_info.total_ckpt==completed+N);
  assert(s.cprc_info.issued_ckpt==issued+1);
  if(round%2)assert(!pthread_join(stop,NULL));else f2fs_stop_ckpt_thread(&s);
  assert(!s.cprc_info.task && llist_empty(&s.cprc_info.issue_list));
 }
 assert(!f2fs_start_ckpt_thread(&s));quota_check=true;cp_error=0;
 int fallback=s.cprc_info.fallback_ckpt,issued=s.cprc_info.issued_ckpt;
 /* Freeze/remount caller owns write s_umount: worker must not wait on it. */
 down_write(&sb.s_umount);assert(!f2fs_issue_checkpoint(&s,CP_SYNC));up_write(&sb.s_umount);
 /* Writer waiting behind a reader: simulate rwsem writer-priority denial. */
 down_read(&sb.s_umount);sb.s_umount.deny_try=true;
 assert(!f2fs_issue_checkpoint(&s,CP_SYNC));sb.s_umount.deny_try=false;
 /* Frozen state checked under worker's own s_umount read protection. */
 sb.s_writers.frozen=SB_FREEZE_WRITE;
 assert(!f2fs_issue_checkpoint(&s,CP_SYNC));sb.s_writers.frozen=SB_UNFROZEN;
 fail_intwrite=true;assert(!f2fs_issue_checkpoint(&s,CP_SYNC));fail_intwrite=false;
 up_read(&sb.s_umount);
 assert(s.cprc_info.fallback_ckpt==fallback+4 && s.cprc_info.issued_ckpt==issued);
 quota_check=false;
 assert(!f2fs_issue_checkpoint(&s,CP_FASTBOOT));
 task.gc=true;assert(!f2fs_issue_checkpoint(&s,CP_SYNC));task.gc=false;
 struct task_struct *worker=s.cprc_info.task;
 assert(__sb_start_write(&sb,SB_FREEZE_FS,false));assert(down_read_trylock(&sb.s_umount));
 current=worker;assert(!f2fs_issue_checkpoint(&s,CP_SYNC));current=&task;
 up_read(&sb.s_umount);sb_end_intwrite(&sb);
 s.enabled=false;assert(!f2fs_issue_checkpoint(&s,CP_SYNC));
 assert(s.cprc_info.issued_ckpt==issued);
 f2fs_stop_ckpt_thread(&s);f2fs_stop_ckpt_thread(&s);
 assert(!f2fs_issue_checkpoint(&s,CP_SYNC));
 assert(!s.cprc_info.queued_ckpt && !super_read && !super_write && !intwrite);
 puts("CP extracted worker/requests: 1200 batched + 4 freeze/quota fallbacks, errors/start/stop/bypass PASS");
}
'''


def stage_b2(root):
    cp = (root / 'fs/f2fs/checkpoint.c').read_text()
    req = function(cp, 'f2fs_issue_checkpoint')
    assert req.index('atomic_inc(&cprc->queued_ckpt)') < req.index('llist_add(')
    assert req.index('f2fs_submit_merged_ipu_write_all') < req.index('llist_add(')
    assert req.index('down_read(&cprc->gate)') < req.index('wait_for_completion(') < req.index('ret = req.ret;')
    dispatch = function(cp, 'checkpoint_and_complete_reqs')
    assert dispatch.index('__sb_start_write(') < dispatch.index('down_read_trylock(') < dispatch.index('SB_UNFROZEN')
    assert dispatch.index('sb_end_intwrite(') < dispatch.index('complete(&req->done)')
    assert 'req->' not in dispatch[dispatch.index('complete(&req->done)') + len('complete(&req->done)'):]
    sup = (root / 'fs/f2fs/super.c').read_text()
    assert 'set_opt(sbi, MERGE_CHECKPOINT)' not in function(sup, 'default_options')
    remount = function(sup, 'f2fs_remount')
    assert 'if (need_stop_ckpt)\n\t\tf2fs_stop_ckpt_thread(sbi);' in remount
    assert remount.index('f2fs_start_ckpt_thread') < remount.index('f2fs_start_gc_thread')
    assert remount.index('f2fs_start_ckpt_thread') < remount.index('dquot_suspend')
    assert remount.index('restore_opts:') < remount.index('if (need_stop_ckpt)')
    assert remount.index('skip:') < remount.index('f2fs_stop_ckpt_thread')
    fill = function(sup, 'f2fs_fill_super')
    assert fill.index('f2fs_init_ckpt_req_control') < fill.index('f2fs_build_gc_manager')
    assert fill.index('f2fs_start_ckpt_thread') < fill.index('sync_free_meta:') < fill.index('f2fs_destroy_post_read_wq')
    assert 'f2fs_stop_ckpt_thread' in function(sup, 'kill_f2fs_super')
    assert 'ckpt_thread_ioprio' not in sup
    from test_backport import braced
    struct = braced(cp, cp.index('struct ckpt_req {')) + ';\n'
    names = ['write_checkpoint_sync', 'checkpoint_and_complete_reqs',
             'issue_checkpoint_thread', 'f2fs_issue_checkpoint',
             'f2fs_start_ckpt_thread', 'f2fs_stop_ckpt_thread',
             'f2fs_init_ckpt_req_control']
    return CP_STUBS + struct + '\n'.join(function(cp, n) for n in names) + CP_MAIN


def mutate(sources, negative):
    changes = {
        'null-selector': ('ipu', '\tif (!target && !page)\n\t\treturn;', ''),
        'missing-accounting': ('ipu', 'inc_page_count(fio->sbi, WB_DATA_TYPE(fio->page));',
                               'if (0) inc_page_count(fio->sbi, WB_DATA_TYPE(fio->page));'),
        'bounce-accounting': ('ipu', 'WB_DATA_TYPE(fio->page)', 'WB_DATA_TYPE(page)'),
        'no-ipu-drain': ('gc', '\tf2fs_submit_merged_ipu_write_all(sbi);', '\tif (0) f2fs_submit_merged_ipu_write_all(sbi);'),
        'gc-freezer-window': ('gc', 'merge->paused = true;', 'merge->paused = false;'),
        'cp-late-counter': ('cp', 'atomic_inc(&cprc->queued_ckpt);',
                            'if (0) atomic_inc(&cprc->queued_ckpt);'),
        'cp-no-umount-protection': ('cp', 'if (down_read_trylock(&sbi->sb->s_umount))',
                                    'if (1)'),
        'cp-drop-error': ('cp', 'req->ret = ret;', 'req->ret = ret ? 0 : ret;'),
    }
    if negative == 'cp-no-lifetime-gate':
        source = dict(sources)['cp']
        req = function(source, 'f2fs_issue_checkpoint')
        mutant = req.replace('down_read(&cprc->gate);', '').replace('up_read(&cprc->gate);', '')
        assert mutant != req
        return 'cp', source.replace(req, mutant)
    name, before, after = changes[negative]
    source = dict(sources)[name]
    assert source.count(before) == 1, negative
    return name, source.replace(before, after)


if __name__ == '__main__':
    main()
