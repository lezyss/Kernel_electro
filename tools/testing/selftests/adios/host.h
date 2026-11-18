/* SPDX-License-Identifier: GPL-2.0 */
/* Single-thread host mocks, not kernel locking/RCU/PM validation. */
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <linux/list.h>
#include <linux/rbtree.h>
#define __percpu
#define __rcu
#define NSEC_PER_MSEC 1000000ULL
#define GFP_KERNEL 0
#define GFP_ATOMIC 1
#define SLAB_HWCACHE_ALIGN 0
#define ADIOS_CPUS 2
#define DIV_ROUND_UP_ULL(x,y) (((x)+(y)-1)/(y))
#define abs(x) ((x)<0?-(x):(x))
#define div_u64(x,y) ((u64)(x)/(y))
#define div64_u64(x,y) ((u64)(x)/(y))
#define EXPORT_SYMBOL(x)
#define EXPORT_SYMBOL_GPL(x)
#define for_each_possible_cpu(cpu) for ((cpu)=0;(cpu)<ADIOS_CPUS;(cpu)++)
#define alloc_percpu(type) calloc(ADIOS_CPUS,sizeof(type))
#define free_percpu(x) free(x)
#define per_cpu_ptr(x,cpu) (&(x)[cpu])
#define this_cpu_ptr(x) (&(x)[0])
#define RCU_INIT_POINTER(p,v) ((p)=(v))
#define rcu_assign_pointer(p,v) ((p)=(v))
#define rcu_dereference(p) (p)
#define rcu_dereference_protected(p,c) (p)
#define rcu_access_pointer(p) (p)
#define rcu_read_lock() do {} while (0)
#define rcu_read_unlock() do {} while (0)
#define synchronize_rcu() do {} while (0)
#define kfree_rcu(p,f) free(p)
#define kfree(p) free(p)
#define lockdep_is_held(p) (*(p)!=0)
#define WARN_ON_ONCE(x) assert(!(x))
#define pr_err(...) fprintf(stderr,__VA_ARGS__)
struct rcu_head { int unused; };
typedef int spinlock_t;
static int locks, irq_depth;
#define spin_lock_init(p) (*(p)=0)
#define spin_lock(p) do { assert(!*(p)); *(p)=1; ++locks; } while (0)
#define spin_unlock(p) do { assert(*(p)); *(p)=0; --locks; } while (0)
#define spin_lock_irqsave(p,f) do { (f)=irq_depth++; spin_lock(p); } while (0)
#define spin_unlock_irqrestore(p,f) do { spin_unlock(p); assert(irq_depth==(int)(f)+1); irq_depth=(f); } while (0)
#define local_irq_save(f) do { (f)=irq_depth++; } while (0)
#define local_irq_restore(f) do { assert(irq_depth==(int)(f)+1); irq_depth=(f); } while (0)
typedef int host_atomic_t;
#define atomic_t host_atomic_t
typedef s64 atomic64_t;
#define atomic_set(p,v) (*(p)=(v))
#define atomic_read(p) (*(p))
#define atomic_or(v,p) (*(p)|=(v))
#define atomic_andnot(v,p) (*(p)&=~(v))
#define atomic64_set(p,v) (*(p)=(v))
#define atomic64_read(p) (*(p))
#define atomic64_add(v,p) (*(p)+=(v))
#define atomic64_sub(v,p) (*(p)-=(v))
#define atomic64_sub_return(v,p) (*(p)-=(v))
#define atomic64_inc(p) (++*(p))
static unsigned long jiffies;
#define msecs_to_jiffies(x) (x)
#define time_before(a,b) ((long)((a)-(b))<0)
static u64 clock_ns=1000000000ULL;
static u64 ktime_get_ns(void) { return clock_ns; }
#define RQF_ELVPRIV (1U<<0)
#define REQ_OP_MASK 255U
#define REQ_OP_READ 0U
#define REQ_OP_WRITE 1U
#define REQ_OP_DISCARD 3U
#define REQ_OP_FLUSH 2U
#define REQ_SYNC (1U<<8)
#define REQ_FUA (1U<<9)
#define REQ_PREFLUSH (1U<<10)
typedef u64 sector_t;
struct elevator_queue { void *elevator_data; int kobj; };
struct request_queue { struct elevator_queue *elevator; unsigned nr_hw_queues, nr_requests; int node; };
struct blk_mq_hw_ctx { struct request_queue *queue; };
struct bio { int unused; };
struct elevator_type { int unused; };
struct request {
 struct request_queue *q; struct list_head queuelist;
 struct { void *priv[2]; } elv;
 unsigned cmd_flags, bytes, rq_flags; u64 pos;
};
#define blk_rq_pos(rq) ((rq)->pos)
#define blk_rq_bytes(rq) ((rq)->bytes)
#define blk_rq_sectors(rq) ((rq)->bytes/512)
#define blk_queue_nonrot(q) 1
struct rb_root_cached { struct rb_root rb_root; struct rb_node *rb_leftmost; };
#define RB_ROOT_CACHED (struct rb_root_cached){RB_ROOT,NULL}
#define rb_first_cached(r) ((r)->rb_leftmost)
static void rb_insert_color_cached(struct rb_node *n,struct rb_root_cached *r,bool first) {
 if (first) r->rb_leftmost=n;
 rb_insert_color(n,&r->rb_root);
}
static void rb_erase_cached(struct rb_node *n,struct rb_root_cached *r) {
 if (r->rb_leftmost==n) r->rb_leftmost=rb_next(n);
 rb_erase(n,&r->rb_root);
}
static void list_sort(void *arg, struct list_head *head,
 int (*cmp)(void *,struct list_head *,struct list_head *)) {
 struct list_head *a,*b;
 bool changed;
 do { changed=false;
  for (a=head->next;a!=head && a->next!=head;a=a->next) {
   b=a->next;
   if (cmp(arg,a,b)>0) { list_del(b); list_add_tail(b,a); changed=true; break; }
  }
 } while (changed);
}
struct kmem_cache { size_t size; };
typedef struct { size_t size; } mempool_t;
static int fail_metadata, fail_group, live_allocations;
static void *kmem_cache_zalloc(struct kmem_cache *c,int gfp) {
 (void)gfp; if (fail_group) { --fail_group; return NULL; }
 void *p=aligned_alloc(64,(c->size+63)&~63UL); assert(p); memset(p,0,c->size); ++live_allocations; return p;
}
static void kmem_cache_free(struct kmem_cache *c,void *p) {
 (void)c; assert(p); --live_allocations; free(p);
}
static void *mempool_alloc(mempool_t *p,int gfp) {
 (void)gfp; if (fail_metadata) { --fail_metadata; return NULL; }
 void *v=aligned_alloc(64,(p->size+63)&~63UL); assert(v); memset(v,0,p->size); ++live_allocations; return v;
}
static void mempool_free(void *v,mempool_t *p) { (void)p; assert(v); --live_allocations; free(v); }
static void *kmemdup(void *p,size_t size,int gfp) {
 (void)gfp; void *v=malloc(size); assert(v); memcpy(v,p,size); return v;
}
