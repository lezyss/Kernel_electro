// SPDX-License-Identifier: GPL-2.0
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
typedef uint64_t u64;typedef uint32_t u32;typedef unsigned int gfp_t;
#define __rcu
#define MAX_CLOCKS 16
#define U32_MAX UINT32_MAX
#define PAGE_SIZE 4096
#define BPF_MAP_TYPE_ARRAY 2
#define GFP_ATOMIC 0
#define BUILD_BUG_ON(x) _Static_assert(!(x),#x)
#define round_up(v,a) (((v)+(a)-1)&~((a)-1))
#define DIV_ROUND_UP_ULL(x,y) (((x)+(y)-1)/(y))
#define num_possible_cpus() 4
#define READ_ONCE(x) (x)
#define rcu_assign_pointer(p,v) ((p)=(v))
#define rcu_dereference_check(p,c) (p)
#define rcu_read_lock_bh_held() 1
#define this_cpu_read(x) (x)
#define this_cpu_write(x,v) ((x)=(v))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((intptr_t)(p))
#define BPF_CALL_1(n,t,a) static long n(t a)
#define BPF_CALL_3(n,t,a,u,b,v,c) static long n(t a,u b,v c)
#define BPF_CAST_CALL(p) ((u64 (*)(u64,u64,u64,u64,u64))(p))
/* MODES */
enum hrtimer_restart { HRTIMER_NORESTART,HRTIMER_RESTART };
struct hrtimer { enum hrtimer_restart (*function)(struct hrtimer *); int active,mode; };
struct bpf_map { int map_type,timer_off,numa_node;u32 key_size,max_entries;long usercnt; };
struct bpf_array { struct bpf_map map;u32 elem_size;char value[] __attribute__((aligned(8))); };
struct bpf_prog { int references; };
struct bpf_prog_aux { struct bpf_prog *prog; };
struct bpf_spin_lock { int locked; };
struct bpf_timer { unsigned char bytes[16]; } __attribute__((aligned(8)));
/* STRUCTS */
static struct bpf_hrtimer *hrtimer_running;
static bool nmi,alloc_fail;
static int cancels,frees,charge_result,charge_calls;
static u32 charged_pages;
#define in_nmi() nmi
#define atomic64_read(p) (*(p))
static void __bpf_spin_lock_irqsave(struct bpf_spin_lock *lock) { assert(!lock->locked);lock->locked=1; }
static void __bpf_spin_unlock_irqrestore(struct bpf_spin_lock *lock) { assert(lock->locked);lock->locked=0; }
static void *bpf_map_kmalloc_node(struct bpf_map *map,size_t size,gfp_t flags,int node)
{ return alloc_fail?NULL:malloc(size); }
static void hrtimer_init(struct hrtimer *timer,clockid_t clockid,enum hrtimer_mode mode)
{ memset(timer,0,sizeof(*timer));timer->mode=mode; }
#define ns_to_ktime(n) (n)
static void hrtimer_start(struct hrtimer *timer,u64 time,enum hrtimer_mode mode)
{ assert(mode==HRTIMER_MODE_REL_SOFT);timer->active=1; }
static int hrtimer_cancel(struct hrtimer *timer)
{ assert(!hrtimer_running || timer!=&hrtimer_running->timer);int ret=timer->active;timer->active=0;cancels++;return ret; }
static struct bpf_prog *bpf_prog_inc_not_zero(struct bpf_prog *prog)
{ if(!prog->references)return ERR_PTR(-ENOENT);prog->references++;return prog; }
static void bpf_prog_put(struct bpf_prog *prog) { assert(prog->references>1);prog->references--; }
static void kfree(void *p) { frees++;free(p); }
static int bpf_map_charge_memlock(struct bpf_map *map,u32 pages)
{ charged_pages=pages;charge_calls++;return charge_result; }
/* EXTRACTED */
static int callback_mode;
static struct bpf_timer_kern *owner;
static unsigned int callbacks;
static u64 callback(u64 map,u64 key,u64 value,u64 unused,u64 unused2)
{
 assert(hrtimer_running && hrtimer_running==owner->timer);
 assert((void *)(uintptr_t)value==hrtimer_running->value && map==(uintptr_t)hrtimer_running->map);
 assert(key);callbacks++;
 if(callback_mode==1) assert(bpf_timer_cancel(owner)==-EDEADLK);
 if(callback_mode==2) bpf_timer_cancel_and_free(owner);
 return 0;
}
static unsigned long checks;
static void run_case(bool array)
{
 struct bpf_prog one={1},two={1},dying={0};struct bpf_prog_aux aux={&one};
 struct bpf_array *a=calloc(1,sizeof(*a)+32);assert(a);
 char *hash=calloc(1,32);assert(hash);
 struct bpf_map map={.map_type=1,.timer_off=0,.key_size=8,.max_entries=10,.usercnt=1};
 a->map=map;a->map.map_type=BPF_MAP_TYPE_ARRAY;a->elem_size=32;
 struct bpf_map *m=array?&a->map:&map;
 owner=(struct bpf_timer_kern *)(array?a->value:hash+8);
 assert(bpf_timer_init(owner,m,CLOCK_MONOTONIC)==0);
 assert(owner->timer->timer.mode==HRTIMER_MODE_REL_SOFT);
 assert(bpf_timer_init(owner,m,CLOCK_MONOTONIC)==-EBUSY);checks+=3;
 assert(bpf_timer_set_callback(owner,callback,&aux)==0 && one.references==2);
 assert(bpf_timer_set_callback(owner,callback,&aux)==0 && one.references==2);
 aux.prog=&two;
 assert(bpf_timer_set_callback(owner,callback,&aux)==0 && one.references==1 && two.references==2);
 aux.prog=&dying;assert(bpf_timer_set_callback(owner,callback,&aux)==-ENOENT);
 assert(two.references==2);checks+=5;
 assert(bpf_timer_start(owner,100,1)==-EINVAL);
 assert(bpf_timer_start(owner,100,0)==0);
 assert(bpf_timer_cancel(owner)==1 && two.references==1);
 assert(bpf_timer_cancel(owner)==0 && two.references==1);checks+=4;
 aux.prog=&one;assert(bpf_timer_set_callback(owner,callback,&aux)==0);
 callback_mode=1;
 assert(owner->timer->timer.function(&owner->timer->timer)==HRTIMER_NORESTART);
 assert(one.references==2 && !hrtimer_running);checks+=3;
 callback_mode=2;int before=cancels,freed=frees;
 assert(owner->timer->timer.function(&owner->timer->timer)==HRTIMER_NORESTART);
 assert(!owner->timer && one.references==1 && cancels==before && frees==freed+1);
 bpf_timer_cancel_and_free(owner);assert(frees==freed+1);
 assert(bpf_timer_cancel(owner)==-EINVAL);checks+=4;
 m->usercnt=0;assert(bpf_timer_init(owner,m,CLOCK_MONOTONIC)==-EPERM);
 m->usercnt=1;alloc_fail=true;assert(bpf_timer_init(owner,m,CLOCK_MONOTONIC)==-ENOMEM);alloc_fail=false;
 nmi=true;assert(bpf_timer_init(owner,m,CLOCK_MONOTONIC)==-EOPNOTSUPP);nmi=false;
 assert(bpf_timer_init(owner,m,MAX_CLOCKS)==-EINVAL);checks+=4;
 free(hash);free(a);
}
static void charge_tests(void)
{
 struct bpf_map m={.timer_off=-EINVAL,.max_entries=10};
 assert(!bpf_map_charge_timers(&m) && !charge_calls);
 m.timer_off=0;assert(!bpf_map_charge_timers(&m) && charge_calls==1);
 assert(charged_pages==DIV_ROUND_UP_ULL(14*sizeof(struct bpf_hrtimer),PAGE_SIZE));
 charge_result=-EPERM;assert(bpf_map_charge_timers(&m)==-EPERM);
 m.max_entries=UINT32_MAX;assert(bpf_map_charge_timers(&m)==-E2BIG);checks+=5;
}
int main(void)
{
 for(int i=0;i<5000;i++) { run_case(false);run_case(true); }
 charge_tests();assert(callbacks==20000);
 printf("PASS: %lu BPF timer helper/lifetime/accounting checks; array/hash, callback replacement, cancel, self-delete/free, reference and error paths (mocked platform)\n",checks);
 return 0;
}
