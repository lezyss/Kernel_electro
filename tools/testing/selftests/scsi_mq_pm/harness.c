/* SPDX-License-Identifier: GPL-2.0 */
/* Host mocks for extracted real functions: NOT a kernel/RCU/hardware model. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <errno.h>
#include <stddef.h>
#define RPM_ACTIVE 0
#define RPM_SUSPENDING 1
#define RPM_SUSPENDED 2
#define RPM_RESUMING 3
#define RQF_PM 1
#define __PERCPU_REF_DEAD 1UL
#define IS_ENABLED(x) ENABLE_PM
#define READ_ONCE(x) (x)
#define EXPORT_SYMBOL(x)
#define EXPORT_SYMBOL_GPL(x)
#if ENABLE_PM
#define CONFIG_BLK_MQ_RUNTIME_PM 1
#endif
static int warnings, wakes, lock_depth, runs;
#define WARN_ON_ONCE(x) ((x) ? (++warnings, 1) : 0)
#define spin_lock_irq(x) do { (void)(x); ++lock_depth; } while (0)
#define spin_unlock_irq(x) do { (void)(x); assert(lock_depth); --lock_depth; } while (0)
#define spin_lock_irqsave(x, f) do { (f)=0; spin_lock_irq(x); } while (0)
#define spin_unlock_irqrestore(x, f) do { (void)(f); spin_unlock_irq(x); } while (0)
#define rcu_read_lock_sched() do {} while (0)
#define rcu_read_unlock_sched() do {} while (0)
#define smp_rmb() do {} while (0)
#define wake_up_all(x) do { (void)(x); ++wakes; } while (0)
typedef int atomic_t;
static int atomic_read(atomic_t *x) { return *x; }
static void atomic_inc(atomic_t *x) { ++*x; }
static int atomic_dec_return(atomic_t *x) { return --*x; }
struct device { int busy, resumes, autosuspends, disabled, delay, use_auto; };
struct percpu_ref { int refs; unsigned long percpu_count_ptr; bool force_atomic; };
struct request_queue {
 void *mq_ops; struct device *dev; int rpm_status, nr_pending;
 atomic_t mq_pm_only, mq_freeze_depth; int mq_freeze_wq, dying;
 int *queue_lock; struct percpu_ref q_usage_counter;
};
struct request { struct request_queue *q; int rq_flags; };
static int percpu_ref_switch_lock;
static bool percpu_ref_is_zero(struct percpu_ref *r) { return r->refs == 0; }
static void percpu_ref_get(struct percpu_ref *r) { ++r->refs; }
static void percpu_ref_put(struct percpu_ref *r) { assert(r->refs > 0); --r->refs; }
static bool percpu_ref_tryget_live(struct percpu_ref *r) {
 if (r->percpu_count_ptr & __PERCPU_REF_DEAD) return false;
 percpu_ref_get(r); return true;
}
static void __percpu_ref_switch_mode(struct percpu_ref *r, void *unused) { (void)r; (void)unused; }
static void pm_request_resume(struct device *d) { ++d->resumes; }
static void pm_runtime_mark_last_busy(struct device *d) { ++d->busy; }
static void pm_request_autosuspend(struct device *d) { ++d->autosuspends; }
static void pm_runtime_disable(struct device *d) { ++d->disabled; }
static void pm_runtime_set_autosuspend_delay(struct device *d, int n) { d->delay=n; }
static void pm_runtime_use_autosuspend(struct device *d) { ++d->use_auto; }
static bool blk_queue_dying(struct request_queue *q) { return q->dying; }
static void __blk_run_queue(struct request_queue *q) { (void)q; ++runs; }
static struct request_queue *current_q;
static int wait_action;
static void simulate_wake(void);
#define wait_event(wq, cond) do { unsigned loops=0; (void)(wq); while (!(cond)) { assert(++loops < 8); simulate_wake(); } } while (0)
void blk_set_runtime_active(struct request_queue *q);
void blk_mq_unfreeze_queue(struct request_queue *q);
void percpu_ref_resurrect(struct percpu_ref *r);
void blk_post_runtime_resume(struct request_queue *q, int err);
static void blk_freeze_queue_start(struct request_queue *q) {
 assert(!lock_depth);
 if (++q->mq_freeze_depth == 1) {
  q->q_usage_counter.percpu_count_ptr |= __PERCPU_REF_DEAD;
  percpu_ref_put(&q->q_usage_counter);
 }
}
static void percpu_ref_switch_to_atomic_sync(struct percpu_ref *r) {
 assert(!lock_depth); assert(current_q->rpm_status == RPM_SUSPENDING);
 assert(current_q->mq_pm_only == 1); r->force_atomic=true;
}
static void percpu_ref_switch_to_percpu(struct percpu_ref *r) {
 assert(r->percpu_count_ptr & __PERCPU_REF_DEAD); r->force_atomic=false;
}
/* EXTRACTED_FUNCTIONS */
static void simulate_wake(void) {
 switch (wait_action) {
 case 1: blk_post_runtime_resume(current_q, 0); break;
 case 2: current_q->dying=1; break;
 case 3: blk_mq_unfreeze_queue(current_q); break;
 default: assert(!"unexpected blocking admission");
 }
}
static struct request_queue make_queue(struct device *d, bool mq) {
 struct request_queue q={0};
 q.mq_ops=mq ? d : NULL; q.q_usage_counter.refs=1;
 blk_pm_runtime_init(&q,d); return q;
}
int main(void) {
 struct device d={0}; struct request_queue q=make_queue(&d,true);
 current_q=&q;
#if ENABLE_PM
 assert(q.dev==&d && !d.disabled && d.use_auto && d.delay==-1);
 for (int i=0;i<2000;i++) {
  int before=d.busy;
  assert(blk_queue_enter(&q,false)==0);
  assert(blk_pre_runtime_suspend(&q)==-EBUSY);
  assert(q.rpm_status==RPM_ACTIVE && !q.mq_pm_only && !q.mq_freeze_depth);
  assert(!q.q_usage_counter.force_atomic && q.q_usage_counter.refs==2);
  assert(d.busy==before+1); blk_queue_exit(&q);
  assert(blk_pre_runtime_suspend(&q)==0);
  assert(q.rpm_status==RPM_SUSPENDING && q.mq_pm_only==1);
  assert(!q.q_usage_counter.force_atomic && q.q_usage_counter.refs==1);
  int resumes=d.resumes;
  assert(blk_queue_enter(&q,true)==-EBUSY && d.resumes>resumes);
  assert(q.q_usage_counter.refs==1);
  assert(blk_queue_enter_pm(&q,true,true)==0); blk_queue_exit(&q);
  blk_post_runtime_suspend(&q,0);
  assert(q.rpm_status==RPM_SUSPENDED && q.mq_pm_only==1);
  resumes=d.resumes;
  assert(blk_queue_enter(&q,true)==-EBUSY && d.resumes>resumes);
  blk_pre_runtime_resume(&q);
  assert(q.rpm_status==RPM_RESUMING);
  assert(blk_queue_enter(&q,true)==-EBUSY);
  assert(blk_queue_enter_pm(&q,false,true)==0); blk_queue_exit(&q);
  blk_post_runtime_resume(&q,i%2 ? -EIO : 0);
  assert(q.rpm_status==RPM_ACTIVE && !q.mq_pm_only);
  int old_wakes=wakes; blk_set_runtime_active(&q);
  assert(wakes==old_wakes && !q.mq_pm_only); /* repeated/system resume */
  assert(blk_queue_enter(&q,true)==0); blk_queue_exit(&q);
 }
 /* Failed suspend must release its gate and leave the queue usable. */
 assert(blk_pre_runtime_suspend(&q)==0); blk_post_runtime_suspend(&q,-EBUSY);
 assert(!q.mq_pm_only && q.rpm_status==RPM_ACTIVE);
 assert(blk_queue_enter(&q,true)==0); blk_queue_exit(&q);
 /* Blocking normal I/O wakes and retries, including a device-removal exit. */
 assert(blk_pre_runtime_suspend(&q)==0); blk_post_runtime_suspend(&q,0);
 wait_action=1; assert(blk_queue_enter(&q,false)==0); blk_queue_exit(&q);
 assert(blk_pre_runtime_suspend(&q)==0); blk_post_runtime_suspend(&q,0);
 wait_action=2; assert(blk_queue_enter(&q,false)==-ENODEV); q.dying=0;
 blk_post_runtime_resume(&q,0);
 /* A PM exemption never overrides a real queue freeze. */
 blk_freeze_queue_start(&q);
 assert(blk_queue_enter_pm(&q,true,true)==-EBUSY);
 wait_action=3; assert(blk_queue_enter_pm(&q,false,true)==0); blk_queue_exit(&q);
 /* Completion busy marking excludes PM requests, not ordinary requests. */
 struct request rq={&q,0}; int old_busy=d.busy;
 blk_mq_pm_mark_last_busy(&rq); assert(d.busy==old_busy+1);
 rq.rq_flags=RQF_PM; blk_mq_pm_mark_last_busy(&rq); assert(d.busy==old_busy+1);
 /* Detached mq queues cannot initiate PM. */
 struct request_queue detached={.mq_ops=&d};
 blk_mq_pm_request_resume(&detached); blk_mq_pm_mark_last_busy(&(struct request){&detached,0});
 assert(blk_pre_runtime_suspend(&detached)==0);
 assert(!runs); /* mq must never execute the legacy request_fn path */
#else
 assert(q.dev==NULL && d.disabled==1);
 assert(blk_queue_enter(&q,true)==0); blk_queue_exit(&q);
 assert(blk_pre_runtime_suspend(&q)==0);
#endif
 /* Original CFQ/legacy pending accounting and restart behavior survives. */
 d=(struct device){0}; q=make_queue(&d,false); current_q=&q;
 assert(q.dev==&d); q.nr_pending=1;
 assert(blk_pre_runtime_suspend(&q)==-EBUSY && q.rpm_status==RPM_ACTIVE);
 q.nr_pending=0; assert(blk_pre_runtime_suspend(&q)==0);
 blk_post_runtime_suspend(&q,0); assert(q.rpm_status==RPM_SUSPENDED);
 blk_pre_runtime_resume(&q); blk_post_runtime_resume(&q,-EIO);
 assert(q.rpm_status==RPM_SUSPENDED);
 int old_runs=runs; blk_post_runtime_resume(&q,0);
 assert(q.rpm_status==RPM_ACTIVE && runs==old_runs+1);
 assert(!lock_depth && !warnings);
 puts("PASS: extracted mq/legacy PM transitions, admission, rollback, resume-error and refcount contracts");
 return 0;
}
