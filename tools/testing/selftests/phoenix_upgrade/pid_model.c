/* SPDX-License-Identifier: GPL-2.0 */
/* alloc_pid is extracted exactly. Allocation, IDR, locks, caps and proc are fake. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <errno.h>
#include <sys/types.h>
#define GFP_KERNEL 0
#define GFP_ATOMIC 0
#define PIDNS_HASH_ADDING (1U<<31)
#define ERR_PTR(e) ((struct pid *)(intptr_t)(e))
#define unlikely(x) (x)
#define RESERVED_PIDS 300
struct user_namespace { int unused; };
struct idr { int live; };
struct pid_namespace {
    unsigned level,nr_hashed;
    void *pid_cachep,*child_reaper;
    struct user_namespace *user_ns;
    struct pid_namespace *parent;
    struct idr idr;
};
struct upid { int nr,pid_chain;struct pid_namespace *ns; };
struct pid { unsigned level;int count,tasks[4],wait_pidfd;struct upid numbers[3]; };
enum pid_type { PIDTYPE_PID,PIDTYPE_TGID,PIDTYPE_PGID,PIDTYPE_SID,PIDTYPE_MAX };
static int pidmap_lock,pid_hash[1],pid_max=32768;
static int allocation_failure,permission_failure,idr_failure,proc_failure,refs;
static int mem_live,removed,disabled;
static void *kmem_cache_alloc(void *cache,int flags) { if(allocation_failure)return NULL;mem_live++;return calloc(1,sizeof(struct pid)); }
static void kmem_cache_free(void *cache,void *p) { mem_live--;free(p); }
static int checkpoint_restore_ns_capable(struct user_namespace *n) { return !permission_failure; }
static void idr_preload(int flags) { }
static void idr_preload_end(void) { }
static void spin_lock_irq(int *p) { }
static void spin_unlock_irq(int *p) { }
static int idr_get_cursor(struct idr *i) { return 0; }
static int idr_alloc(struct idr *i,void *p,int lo,int hi,int flags) { if(idr_failure)return idr_failure;assert(i->live==0);i->live++;return lo; }
static int idr_alloc_cyclic(struct idr *i,void *p,int lo,int hi,int flags) { return idr_alloc(i,p,7,8,flags); }
static void idr_remove(struct idr *i,int nr) { assert(i->live==1);i->live--;removed++; }
static void idr_replace(struct idr *i,void *p,int nr) { assert(i->live==1); }
static int is_child_reaper(struct pid *p) { return p->numbers[p->level].nr==1; }
static int pid_ns_prepare_proc(struct pid_namespace *n) { return proc_failure; }
static void disable_pid_allocation(struct pid_namespace *n) { n->nr_hashed&=~PIDNS_HASH_ADDING;disabled++; }
static struct pid_namespace *get_pid_ns(struct pid_namespace *n) { refs++;return n; }
static void put_pid_ns(struct pid_namespace *n) { refs--; }
static void atomic_set(int *p,int n) { *p=n; }
#define INIT_HLIST_HEAD(p) (*(p)=0)
static void init_waitqueue_head(int *p) { *p=0; }
static int pid_hashfn(int nr,struct pid_namespace *ns) { return 0; }
static void hlist_add_head_rcu(int *p,int *head) { }
/* EXTRACTED */
int main(void)
{
    const int expected[]={0,-ENOMEM,-ENOMEM,-ENOMEM,-ENOMEM,-EINVAL,-EPERM,-EEXIST,-ENOMEM,-ENOMEM,-EINVAL,0,0,-EINVAL,-EINVAL,-ENOMEM};
    for(int scenario=0;scenario<16;scenario++) {
        allocation_failure=permission_failure=idr_failure=proc_failure=refs=mem_live=removed=disabled=0;
        struct user_namespace user={0};
        struct pid_namespace parent={.level=0,.nr_hashed=PIDNS_HASH_ADDING,.child_reaper=(void *)1,.user_ns=&user};
        struct pid_namespace child={.level=1,.nr_hashed=PIDNS_HASH_ADDING,.child_reaper=(void *)1,.user_ns=&user,.parent=&parent};
        pid_t tids[]={7,8};size_t n=2;
        switch(scenario) {
        case 0:break;
        case 1:child.nr_hashed=0;break;
        case 2:tids[0]=1;proc_failure=-ENOMEM;break;
        case 3:n=0;child.nr_hashed=0;break;
        case 4:n=1;child.nr_hashed=0;break;
        case 5:tids[0]=0;break;
        case 6:permission_failure=1;break;
        case 7:idr_failure=-ENOSPC;break;
        case 8:idr_failure=-ENOMEM;break;
        case 9:allocation_failure=1;break;
        case 10:n=3;break;
        case 11:n=0;break;
        case 12:n=1;break;
        case 13:tids[1]=-1;break;
        case 14:child.child_reaper=NULL;break;
        case 15:child.level=0;child.parent=NULL;n=1;child.nr_hashed=0;break;
        }
        struct pid *p=alloc_pid(&child,tids,n);
        int err=(intptr_t)p<0?(int)(intptr_t)p:0;
        assert(err==expected[scenario]);
        if(err) {
            assert(!mem_live&&!refs&&!child.idr.live&&!parent.idr.live);
            if(scenario==1||scenario==2||scenario==3||scenario==4)assert(removed==2);
            if(scenario==13||scenario==15)assert(removed==1);
            assert(disabled==(scenario==2));
        } else {
            assert(mem_live==1&&refs==1&&child.idr.live==1);
            kmem_cache_free(NULL,p);
        }
    }
    puts("PASS:16 alloc_pid error/success scenarios including partial explicit PIDs and own-namespace cleanup");
    return 0;
}
