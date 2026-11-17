// SPDX-License-Identifier: GPL-2.0
/* Extracted scheduler code; kernel context is deliberately mocked. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <setjmp.h>
#include <stdio.h>
#include <string.h>

#define NCPU 4
#define SD_ASYM_CPUCAPACITY 1U
#define TASK_ON_RQ_MIGRATING 2
#define DEQUEUE_NOCLOCK 1
struct sched_group_capacity { unsigned long min_capacity, max_capacity; };
struct cpumask { unsigned bits; };
struct sched_group { struct sched_group_capacity *sgc; struct cpumask mask; };
struct sched_domain { unsigned flags; };
enum fbq_type { regular, remote, all };
enum group_type { group_other, group_misfit_task };
struct rq {
    struct { unsigned h_nr_running; } cfs;
    unsigned nr_running, active_balance;
    unsigned long misfit_task_load, load, capacity;
    bool reduced;
    enum fbq_type fbq;
};
struct lb_env {
    struct cpumask *cpus;
    enum fbq_type fbq_type;
    enum group_type src_grp_type;
    struct sched_domain *sd;
    unsigned dst_cpu;
    unsigned long imbalance;
};
static struct rq queues[NCPU];
#define for_each_cpu_and(i, a, b) \
    for ((i) = 0; (i) < NCPU; (i)++) \
        if (((a)->bits & (b)->bits) & (1U << (i)))
#define sched_group_span(g) (&(g)->mask)
static struct rq *cpu_rq(unsigned i) { assert(i < NCPU); return &queues[i]; }
static enum fbq_type fbq_classify_rq(struct rq *rq) { return rq->fbq; }
static unsigned long capacity_of(unsigned i) { return cpu_rq(i)->capacity; }
static unsigned long weighted_cpuload(struct rq *rq) { return rq->load; }
static bool check_cpu_capacity(struct rq *rq, struct sched_domain *sd)
{ (void)sd; return rq->reduced; }
/* CAPACITY_AND_QUEUE */

struct thread_info { unsigned cpu; };
struct task_struct { unsigned cpu, wake_cpu, on_rq; struct thread_info ti; };
#define task_thread_info(p) (&(p)->ti)
static unsigned reads, writes, stage;
static bool tracking_set;
#define READ_ONCE(x) (reads++, *(volatile __typeof__(x) *)&(x))
#define WRITE_ONCE(x, v) do { \
    writes++; if (tracking_set) assert(stage++ == 2); \
    *(volatile __typeof__(x) *)&(x) = (v); \
} while (0)
static void set_task_rq(struct task_struct *p, unsigned cpu)
{ (void)p; (void)cpu; assert(stage++ == 0); }
#define smp_wmb() do { assert(stage++ == 1); } while (0)
static void dequeue_task(struct rq *rq, struct task_struct *p, unsigned flags)
{
    (void)rq;
    assert(flags == DEQUEUE_NOCLOCK);
    assert(p->on_rq == TASK_ON_RQ_MIGRATING && writes == 1);
}
/* MIGRATION */

static bool irq_disabled, offline;
static unsigned disables, stops, reports, enters;
static jmp_buf dead_cpu;
static void local_irq_disable(void) { irq_disabled = true; disables++; }
/* Referenced by the optional negative control's actual protected wrapper. */
static void __attribute__((unused)) local_irq_enable(void) { irq_disabled = false; }
static void tick_nohz_idle_stop_tick(void)
{
    assert(irq_disabled);
#ifdef CONFIG_NO_HZ_COMMON
    stops++;
#endif
}
/* PROTECTED_WRAPPER */
static bool cpu_is_offline(unsigned cpu)
{ assert(cpu == 0 && irq_disabled); return offline; }
static void cpuhp_report_idle_dead(void)
{ assert(irq_disabled && offline); reports++; }
static void arch_cpu_idle_dead(void)
{ assert(irq_disabled && reports == 1); longjmp(dead_cpu, 1); }
static void arch_cpu_idle_enter(void)
{ assert(irq_disabled && !offline); enters++; }
static void idle_iteration(void)
{
    unsigned cpu = 0;
/* IDLE_PREFIX */
}

static void test_capacity(void)
{
    struct sched_group_capacity a, b;
    struct sched_group ga = { .sgc = &a }, gb = { .sgc = &b };
    const unsigned long edge[] = { 0, 1, 512, 600, 1023, 1024, 1735,
                                  ULONG_MAX / 1735, ULONG_MAX - 1, ULONG_MAX };
    for (unsigned long x = 0; x <= 2048; x++)
        for (unsigned long y = 0; y <= 2048; y++) {
            a.min_capacity = a.max_capacity = x;
            b.min_capacity = b.max_capacity = y;
            assert(group_smaller_min_cpu_capacity(&ga, &gb) == (x < y));
            assert(group_smaller_max_cpu_capacity(&ga, &gb) == (x < y));
        }
    for (unsigned i = 0; i < sizeof(edge) / sizeof(*edge); i++)
        for (unsigned j = 0; j < sizeof(edge) / sizeof(*edge); j++) {
            a.min_capacity = edge[i]; a.max_capacity = edge[j];
            b.min_capacity = edge[j]; b.max_capacity = edge[i];
            assert(group_smaller_min_cpu_capacity(&ga, &gb) == (edge[i] < edge[j]));
            assert(group_smaller_max_cpu_capacity(&ga, &gb) == (edge[j] < edge[i]));
        }
}

/* Independent selection oracle, using division on bounded exact powers-of-two
 * capacities. All test loads are multiples of 1024, so no rounding is lost. */
static struct rq *reference_queue(struct lb_env *env, struct sched_group *group)
{
    struct rq *best = NULL;
    unsigned long metric = 0;
    unsigned mask = env->cpus->bits & group->mask.bits;
    for (unsigned i = 0; i < NCPU; i++) {
        struct rq *rq = &queues[i];
        unsigned long value;
        if (!(mask & (1U << i)) || rq->fbq > env->fbq_type || !rq->cfs.h_nr_running)
            continue;
        if (env->src_grp_type == group_misfit_task) {
            value = rq->misfit_task_load;
        } else {
            if (rq->active_balance && rq->nr_running <= 2)
                continue;
            if ((env->sd->flags & SD_ASYM_CPUCAPACITY) &&
                queues[env->dst_cpu].capacity < rq->capacity && rq->nr_running == 1)
                continue;
            if (rq->nr_running == 1 && rq->load > env->imbalance && !rq->reduced)
                continue;
            value = rq->load * 1024 / rq->capacity;
        }
        if (value > metric) { best = rq; metric = value; }
    }
    return best;
}

static uint32_t seed = 0x149357;
static unsigned random_value(void)
{ seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return seed; }
static void test_queue(void)
{
    struct cpumask allowed = { 15 };
    struct sched_group group = { .mask = { 15 } };
    struct sched_domain sd = { 0 };
    struct lb_env env = { .cpus = &allowed, .fbq_type = all, .sd = &sd,
                         .imbalance = ULONG_MAX };
    /* A CFS-empty queue with RT tasks and stale load/misfit must never win. */
    for (unsigned type = 0; type < 2; type++) {
        memset(queues, 0, sizeof(queues));
        for (unsigned i = 0; i < NCPU; i++) queues[i].capacity = 1024;
        queues[0].nr_running = 3;
        queues[0].load = queues[0].misfit_task_load = 65536;
        queues[1].nr_running = queues[1].cfs.h_nr_running = 2;
        queues[1].load = queues[1].misfit_task_load = 1024;
        env.src_grp_type = type ? group_misfit_task : group_other;
        assert(find_busiest_queue(&env, &group) == &queues[1]);
        queues[1].cfs.h_nr_running = 0;
        assert(find_busiest_queue(&env, &group) == NULL);
    }
    for (unsigned n = 0; n < 50000; n++) {
        allowed.bits = random_value() % 16;
        group.mask.bits = random_value() % 16;
        sd.flags = random_value() % 2;
        env.src_grp_type = random_value() % 2;
        env.fbq_type = random_value() % 3;
        env.dst_cpu = random_value() % NCPU;
        env.imbalance = (random_value() % 32) * 1024UL;
        for (unsigned i = 0; i < NCPU; i++) {
            struct rq *rq = &queues[i];
            rq->cfs.h_nr_running = random_value() % 4;
            rq->nr_running = rq->cfs.h_nr_running + random_value() % 3;
            rq->active_balance = random_value() % 2;
            rq->load = (random_value() % 64) * 1024UL;
            rq->misfit_task_load = random_value() % 64;
            rq->capacity = 256UL << (random_value() % 3);
            rq->reduced = random_value() % 2;
            rq->fbq = random_value() % 3;
        }
        assert(find_busiest_queue(&env, &group) == reference_queue(&env, &group));
    }
}

static void test_migration(void)
{
    for (unsigned cpu = 0; cpu < 64; cpu++) {
        struct task_struct p = { .cpu = 99, .ti.cpu = 98, .wake_cpu = 97 };
        reads = writes = stage = 0;
        tracking_set = true;
        __set_task_cpu(&p, cpu);
        tracking_set = false;
#ifdef CONFIG_SMP
        assert(stage == 3 && writes == 1 && p.wake_cpu == cpu);
        assert(task_cpu(&p) == cpu && reads == 1);
#ifdef CONFIG_THREAD_INFO_IN_TASK
        assert(p.ti.cpu == 98);
#else
        assert(p.cpu == 99);
#endif
#else
        assert(stage == 1 && writes == 0 && p.wake_cpu == 97);
        assert(task_cpu(&p) == 0 && reads == 0);
#endif
        for (unsigned on_rq = 0; on_rq <= 2; on_rq++) {
            p.on_rq = on_rq; reads = 0;
            assert(!!task_on_rq_migrating(&p) == (on_rq == TASK_ON_RQ_MIGRATING));
            assert(reads == 1);
        }
        writes = 0;
        move_prefix(&queues[0], &p);
        assert(writes == 1 && p.on_rq == TASK_ON_RQ_MIGRATING);
    }
}

static void test_idle(void)
{
    for (volatile unsigned n = 0; n < 200; n++) {
        offline = n % 2;
        irq_disabled = false;
        disables = stops = reports = enters = 0;
        if (!setjmp(dead_cpu)) {
            idle_iteration();
            assert(!offline);
        }
        assert(irq_disabled && disables == 1);
        assert(reports == (unsigned)offline && enters == (unsigned)!offline);
#ifdef CONFIG_NO_HZ_COMMON
        assert(stops == (unsigned)offline);
#else
        assert(stops == 0);
#endif
    }
}

int main(void)
{
    test_capacity(); test_queue(); test_migration(); test_idle();
    puts("PASS: 4,198,401 capacity pairs + 100 edges, 50,000 queue cases, migration access/order and 200 idle paths");
    return 0;
}
