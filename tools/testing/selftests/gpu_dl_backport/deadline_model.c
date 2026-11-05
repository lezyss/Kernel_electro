// SPDX-License-Identifier: GPL-2.0
/* Actual extracted DL/cpuset functions with mocked CPU masks and admission state. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

typedef uint64_t u64;
typedef int64_t s64;
typedef int32_t s32;
#define nr_cpu_ids 8U
#define PF_NO_SETAFFINITY 1U
#define unlikely(x) (x)
struct cpumask { unsigned bits; };
struct dl_bw { unsigned lock; u64 bw, total_bw; };
struct root_domain { struct cpumask mask; const struct cpumask *span; struct dl_bw dl_bw; };
struct rq { struct root_domain *rd; };
struct task_struct { unsigned flags; bool deadline; int cpu; struct { u64 dl_bw; } dl; };
struct cgroup_subsys_state { int dummy; };
struct cpuset {
    struct cgroup_subsys_state css;
    struct cpumask *cpus_allowed, *effective_cpus;
    unsigned mems_allowed;
    int attach_in_progress;
};
struct cgroup_taskset { struct task_struct *task; struct cpuset *target; };
static struct cpumask active;
#define cpu_active_mask (&active)
static struct rq rqs[8];
static struct root_domain domains[2];
static unsigned rcu_depth, irq_disabled, mask_visits, add_calls;
static s64 last_update;
static bool clear_active_on_lock;
static struct cpuset *cpuset_attach_old_cs;
static struct cpuset old_cs;
static unsigned cpuset_mutex, security_calls;
static bool v2;
static int security_error;
static struct rq *cpu_rq(unsigned i) { assert(i < nr_cpu_ids); return &rqs[i]; }
#define task_rq(p) cpu_rq((p)->cpu)
#define dl_task(p) ((p)->deadline)
#define rcu_read_lock_sched() (rcu_depth++)
#define rcu_read_unlock_sched() do { assert(rcu_depth == 1); rcu_depth--; } while (0)
#define rcu_read_lock_sched_held() (rcu_depth == 1)
#define RCU_LOCKDEP_WARN(test, msg) assert(!(test))
#define for_each_cpu_and(i, a, b) \
    for ((i) = 0; (unsigned)(i) < nr_cpu_ids; (i)++) \
        if ((((a)->bits & (b)->bits) & (1U << (i))) && (++mask_visits))
#define cpumask_subset(a, b) (!((a)->bits & ~(b)->bits))
static int cpumask_weight(const struct cpumask *a) { return __builtin_popcount(a->bits); }
static bool cpumask_intersects(const struct cpumask *a, const struct cpumask *b)
{ return !!(a->bits & b->bits); }
static unsigned cpumask_any_and(const struct cpumask *a, const struct cpumask *b)
{ unsigned bits = a->bits & b->bits; return bits ? (unsigned)__builtin_ctz(bits) : nr_cpu_ids; }
#define cpumask_empty(p) (!(p)->bits)
#define nodes_empty(n) (!(n))
#define raw_spin_lock_irqsave(lock, flags) do { \
    assert(!*(lock)); (flags) = irq_disabled; irq_disabled = 1; *(lock) = 1; \
    if (clear_active_on_lock) active.bits = 0; \
} while (0)
#define raw_spin_unlock_irqrestore(lock, flags) do { \
    assert(*(lock) && irq_disabled); *(lock) = 0; irq_disabled = (flags); \
} while (0)
static void __dl_update(struct dl_bw *b, s64 change)
{ assert(b->lock && rcu_depth == 1); add_calls++; last_update = change; }
#define mutex_lock(p) do { assert(!*(p)); *(p) = 1; } while (0)
#define mutex_unlock(p) do { assert(*(p)); *(p) = 0; } while (0)
static struct task_struct *cgroup_taskset_first(struct cgroup_taskset *set,
                                              struct cgroup_subsys_state **css)
{ *css = &set->target->css; return set->task; }
#define css_cs(css_ptr) ((struct cpuset *)(css_ptr))
#define task_cs(task) ((void)(task), &old_cs)
#define is_in_v2_mode() (v2)
#define cgroup_taskset_for_each(task, css, set) \
    for (int once = 1; once && (((task) = (set)->task), ((css) = &(set)->target->css), true); once = 0)
static int security_task_setscheduler(struct task_struct *p)
{ (void)p; security_calls++; return security_error; }
/* FUNCTIONS */
static void setup(void)
{
    unsigned i;
    assert(!rcu_depth && !cpuset_mutex);
    memset(domains, 0, sizeof(domains));
    for (i = 0; i < 2; i++) {
        domains[i].mask.bits = i ? 0xf0 : 0x0f;
        domains[i].span = &domains[i].mask;
        domains[i].dl_bw.bw = 100;
    }
    for (i = 0; i < 8; i++) rqs[i].rd = &domains[i / 4];
    domains[0].dl_bw.total_bw = 25;
    active.bits = 0xff;
    mask_visits = add_calls = security_calls = 0;
    last_update = 0;
    security_error = 0;
    clear_active_on_lock = false;
    irq_disabled = 0;
    v2 = true;
}
static void balanced(void)
{
    assert(!rcu_depth && !cpuset_mutex);
    assert(!domains[0].dl_bw.lock && !domains[1].dl_bw.lock);
    assert(domains[0].dl_bw.total_bw == 25);
}
int main(void)
{
    struct cpumask configured = {0}, effective = {0x10};
    struct task_struct task = { .deadline = true, .cpu = 0, .dl = { .dl_bw = 60 } };
    struct cpuset cs = { .cpus_allowed = &configured, .effective_cpus = &effective,
                         .mems_allowed = 1 };
    struct cgroup_taskset set = { .task = &task, .target = &cs };
    unsigned span, online, flags, deadline;
    setup(); rcu_depth = 1;
    for (span = 0; span < 256; span++) for (online = 0; online < 256; online++) {
        domains[0].mask.bits = span; active.bits = online; mask_visits = 0;
        assert(dl_bw_cpus(0) == __builtin_popcount(span & online));
        if (!(span & ~online)) assert(mask_visits == 0);
    }
    rcu_depth = 0;
    /* Configured-empty v2 cpuset inherits a usable effective destination. */
    setup(); assert(cpuset_can_attach(&set) == 0);
    assert(cs.attach_in_progress == 1 && security_calls == 1);
    assert(cpuset_attach_old_cs == &old_cs);
    assert(domains[1].dl_bw.total_bw == 60 && add_calls == 1 && last_update == -15);
    balanced();
    /* v1 still rejects configured-empty CPU/node masks before admission. */
    setup(); cs.attach_in_progress = 0; v2 = false;
    assert(cpuset_can_attach(&set) == -ENOSPC && !add_calls && !security_calls);
    configured.bits = effective.bits;
    setup(); v2 = false; cs.mems_allowed = 0;
    assert(cpuset_can_attach(&set) == -ENOSPC && !add_calls);
    cs.mems_allowed = 1;
    setup(); v2 = false;
    assert(cpuset_can_attach(&set) == 0 && add_calls == 1); balanced();
    /* Keep PF_NO_SETAFFINITY for both normal and DEADLINE tasks. */
    for (deadline = 0; deadline < 2; deadline++) {
        setup(); task.deadline = deadline; task.flags = PF_NO_SETAFFINITY;
        assert(cpuset_can_attach(&set) == -EINVAL && !add_calls && !security_calls);
        balanced();
    }
    task.flags = 0; task.deadline = true;
    setup(); effective.bits = 0;
    assert(dl_task_can_attach(&task, &effective) == -EINVAL && !add_calls); balanced();
    setup(); effective.bits = 0x10; active.bits = 0x0f;
    assert(dl_task_can_attach(&task, &effective) == -EINVAL && !add_calls); balanced();
    /* Simulate the last active CPU leaving after destination selection. */
    setup(); clear_active_on_lock = true; domains[1].dl_bw.bw = (u64)-1;
    assert(dl_task_can_attach(&task, &effective) == -EINVAL && !add_calls); balanced();
    setup(); domains[1].dl_bw.bw = 10;
    assert(task_can_attach(&task, &effective) == -EBUSY && !add_calls);
    assert(domains[1].dl_bw.total_bw == 0); balanced();
    setup(); domains[1].dl_bw.total_bw = 340;
    assert(task_can_attach(&task, &effective) == 0 && add_calls == 1);
    assert(domains[1].dl_bw.total_bw == 400); balanced();
    setup(); domains[1].dl_bw.total_bw = 341;
    assert(task_can_attach(&task, &effective) == -EBUSY && !add_calls);
    assert(domains[1].dl_bw.total_bw == 341); balanced();
    for (flags = 0; flags < 2; flags++) {
        setup(); irq_disabled = flags; domains[1].dl_bw.bw = (u64)-1;
        assert(task_can_attach(&task, &effective) == 0 && add_calls == 1);
        assert(domains[1].dl_bw.total_bw == 60 && irq_disabled == flags); balanced();
    }
    setup(); effective.bits = 0x02;
    assert(task_can_attach(&task, &effective) == 0 && !add_calls); balanced();
    setup(); task.deadline = false; effective.bits = 0;
    assert(task_can_attach(&task, &effective) == 0 && !add_calls); balanced();
    setup(); configured.bits = 0; effective.bits = 0x10; cs.attach_in_progress = 0;
    assert(cpuset_can_attach(&set) == 0 && !add_calls && security_calls == 1);
    assert(cs.attach_in_progress == 1); balanced();
    setup(); cs.attach_in_progress = 0; security_error = -EPERM;
    assert(cpuset_can_attach(&set) == -EPERM && !add_calls && security_calls == 1);
    assert(cs.attach_in_progress == 0); balanced();
    setup(); task.deadline = true; effective.bits = 0x10; task.flags = PF_NO_SETAFFINITY;
    cs.attach_in_progress = 0;
    assert(cpuset_can_attach(&set) == -EINVAL && !cs.attach_in_progress && !security_calls);
    task.flags = 0;
    puts("PASS: 65536 CPU-mask pairs; inherited cpuset; affinity guards; bounds/zero-CPU/overflow accounting; IRQ/RCU balance");
    return 0;
}
