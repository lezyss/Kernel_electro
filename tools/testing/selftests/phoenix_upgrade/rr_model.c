/* SPDX-License-Identifier: GPL-2.0 */
/* Exact helper/wrappers; task lookup, locks, timespec conversion/uaccess mocked. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/types.h>
#define timespec phoenix_timespec
#define __user
#define SYSCALL_DEFINE2(n,t,a,u,b) long native_##n(t a,u b)
#define COMPAT_SYSCALL_DEFINE2(n,t,a,u,b) long compat_##n(t a,u b)
typedef int compat_pid_t;
struct timespec64 { long long tv_sec, tv_nsec; };
struct timespec { long tv_sec, tv_nsec; };
struct compat_timespec { int tv_sec, tv_nsec; };
struct rq { int unused; };
struct rq_flags { int unused; };
struct task_struct;
struct sched_class { unsigned (*get_rr_interval)(struct rq *,struct task_struct *); };
struct task_struct { struct sched_class *sched_class; };
static int absent, denied, copies, rcu, locked;
static unsigned interval(struct rq *rq,struct task_struct *task) { return 42; }
static struct sched_class klass = {interval};
static struct task_struct task = {&klass};
static struct rq rq;
static void rcu_read_lock(void) { assert(!rcu);rcu=1; }
static void rcu_read_unlock(void) { assert(rcu&&!locked);rcu=0; }
static struct task_struct *find_process_by_pid(pid_t pid) { assert(rcu);return absent?NULL:&task; }
static int security_task_getscheduler(struct task_struct *p) { assert(rcu);return denied?-EACCES:0; }
static struct rq *task_rq_lock(struct task_struct *p,struct rq_flags *f) { assert(rcu&&!locked);locked=1;return &rq; }
static void task_rq_unlock(struct rq *r,struct task_struct *p,struct rq_flags *f) { assert(locked);locked=0; }
static void jiffies_to_timespec64(unsigned value,struct timespec64 *t) { t->tv_sec=value;t->tv_nsec=0; }
static int put_timespec64(const struct timespec64 *t,struct timespec *out) { copies++;if(!out)return -EFAULT;out->tv_sec=t->tv_sec;out->tv_nsec=t->tv_nsec;return 0; }
#ifdef CONFIG_COMPAT
static int compat_put_timespec64(const struct timespec64 *t,struct compat_timespec *out) { copies++;if(!out)return -EFAULT;out->tv_sec=t->tv_sec;out->tv_nsec=t->tv_nsec;return 0; }
#endif
/* EXTRACTED */
int main(void)
{
    int paths=1;
#ifdef CONFIG_COMPAT
    paths=2;
#endif
    for(int compat=0;compat<paths;compat++)for(int scenario=0;scenario<7;scenario++) {
        struct timespec native={123,456};
#ifdef CONFIG_COMPAT
        struct compat_timespec small={123,456};
#endif
        pid_t pid=scenario==0?-1:(scenario==5?0:7);
        absent=scenario==1;denied=scenario==2;copies=rcu=locked=0;
        klass.get_rr_interval=scenario==6?NULL:interval;
        long ret;
#ifdef CONFIG_COMPAT
        if(compat)ret=compat_sched_rr_get_interval(pid,scenario==4?NULL:&small);
        else
#endif
        ret=native_sched_rr_get_interval(pid,scenario==4?NULL:&native);
        int expected[]={-EINVAL,-ESRCH,-EACCES,0,-EFAULT,0,0};
        assert(ret==expected[scenario]);assert(!rcu&&!locked);
        assert(copies==(scenario>=3));
        if(scenario<3) {
            assert(native.tv_sec==123&&native.tv_nsec==456);
#ifdef CONFIG_COMPAT
            assert(small.tv_sec==123&&small.tv_nsec==456);
#endif
        } else if(scenario!=4) {
            long sec=native.tv_sec;
#ifdef CONFIG_COMPAT
            if(compat)sec=small.tv_sec;
#endif
            assert(sec==(scenario==6?0:42));
        }
    }
    printf("PASS: RR helper native/compat error-first uaccess, success, bad pointer, PID0 and zero slice (%d paths)\n",paths);
    return 0;
}
