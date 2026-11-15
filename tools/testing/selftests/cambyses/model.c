// SPDX-License-Identifier: GPL-2.0
/* Userspace model: real list.h and extracted detach_tasks(), mocked rq context. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <linux/list.h>

typedef uint64_t u64;
enum { CPU_IDLE, CPU_NOT_IDLE, CPU_NEWLY_IDLE };
enum { LB_ROTATE_BLOCK, LB_STRICT_BUDGET, LB_MIN };
static bool features[3];
#define sched_feat(x) features[x]
#define max_t(t,a,b) ((t)(a) > (t)(b) ? (t)(a) : (t)(b))
#define min_t(t,a,b) ((t)(a) < (t)(b) ? (t)(a) : (t)(b))
#define lockdep_assert_held(x) assert(*(x))
#define schedstat_add(x,y) ((x) += (y))
#define trace_sched_load_balance_skip_tasks(...) ((void)0)
/* FLAGS */
struct task_struct {
    struct { struct list_head group_node; } se;
    int id;
    unsigned long load;
    bool pinned, running, hot, throttled, big, nonpreferred;
};
struct rq { struct list_head cfs_tasks; int nr_running; bool lock; u64 clock; };
struct sched_domain { int nr_balance_failed; int lb_gained[3]; };
struct lb_env {
    struct rq *src_rq;
    struct sched_domain *sd;
    int src_cpu, dst_cpu, idle, src_grp_type;
    unsigned flags, loop, loop_max, loop_break;
    long imbalance;
    struct list_head tasks;
};
struct world {
    struct rq rq[2];
    struct sched_domain sd;
    struct lb_env env;
    struct task_struct *allocated[128];
    bool same, churn;
    unsigned capacity[2];
    u64 step;
    int trace[10000], visits, migrations;
};
static struct world w;
static unsigned list_ops;

bool __list_add_valid(struct list_head *n, struct list_head *prev, struct list_head *next)
{
    assert(prev && next && n != prev && n != next);
    assert(prev->next == next && next->prev == prev);
    list_ops++;
    return true;
}
bool __list_del_entry_valid(struct list_head *p)
{
    assert(p->prev && p->next);
    assert(p->prev != LIST_POISON2 && p->next != LIST_POISON1);
    assert(p->prev->next == p && p->next->prev == p);
    return true;
}
static struct rq *cpu_rq(int cpu) { return &w.rq[cpu]; }
static bool same_cluster(int a, int b) { (void)a; (void)b; return w.same; }
static unsigned cpu_capacity(int cpu) { return w.capacity[cpu]; }
static u64 rq_clock(struct rq *rq) { u64 now = rq->clock; rq->clock += w.step; return now; }
static unsigned long task_h_load(struct task_struct *p) { return p->load; }
static bool can_migrate_task(struct task_struct *p, struct lb_env *env)
{
    assert(w.visits < 10000 && env->src_rq->lock);
    w.trace[w.visits++] = p->id;
    if (p->pinned || p->running || p->hot || p->throttled)
        return false;
    if (p->big && (env->flags & LBF_IGNORE_BIG_TASKS))
        return false;
#ifdef CONFIG_SCHED_WALT
    if (p->nonpreferred && (env->flags & LBF_IGNORE_PREFERRED_CLUSTER_TASKS))
        return false;
#endif
    return true;
}
static void detach_task(struct task_struct *p, struct lb_env *env)
{
    assert(env->src_rq->lock);
    assert(!p->pinned && !p->running && !p->hot && !p->throttled);
    assert(!(env->flags & LBF_IGNORE_BIG_TASKS) || !p->big);
#ifdef CONFIG_SCHED_WALT
    assert(!(env->flags & LBF_IGNORE_PREFERRED_CLUSTER_TASKS) || !p->nonpreferred);
#endif
    list_del(&p->se.group_node);
    env->src_rq->nr_running--;
    w.migrations++;
#ifdef CONFIG_SCHED_WALT
    /* Model a legal dequeue/free while WALT drops/reacquires src_rq->lock.
     * A cursor or candidate latched before detach must not survive this. */
    if (w.churn) {
        struct list_head *entry;
        env->src_rq->lock = false;
        for (entry = env->src_rq->cfs_tasks.prev;
             entry != &env->src_rq->cfs_tasks; entry = entry->prev) {
            struct task_struct *victim = list_entry(entry, struct task_struct, se.group_node);
            if (victim->running)
                continue;
            list_del(entry);
            env->src_rq->nr_running--;
            w.allocated[victim->id] = NULL;
            free(victim);
            break;
        }
        env->src_rq->lock = true;
    }
#endif
}
/* FUNCTIONS */
/* LEGACY */

static void clear_world(void)
{
    int i;
    for (i = 0; i < 128; i++) free(w.allocated[i]);
    memset(&w, 0, sizeof(w));
}
static void setup(int n)
{
    int i;
    clear_world();
    for (i = 0; i < 2; i++) {
        INIT_LIST_HEAD(&w.rq[i].cfs_tasks);
        w.rq[i].lock = true;
        w.capacity[i] = 1024;
    }
    w.same = true;
    w.rq[0].nr_running = n + 1; /* A current RT task is not on cfs_tasks. */
    w.env.src_rq = &w.rq[0]; w.env.sd = &w.sd;
    w.env.dst_cpu = 1; w.env.idle = CPU_NOT_IDLE;
    w.env.imbalance = 100; w.env.loop_max = n; w.env.loop_break = 32;
    INIT_LIST_HEAD(&w.env.tasks);
    for (i = 1; i <= n; i++) {
        struct task_struct *p = calloc(1, sizeof(*p));
        assert(p);
        p->id = i; p->load = 10; w.allocated[i] = p;
        list_add_tail(&p->se.group_node, &w.rq[0].cfs_tasks);
    }
    features[LB_ROTATE_BLOCK] = features[LB_STRICT_BUDGET] = true;
    features[LB_MIN] = false;
    list_ops = 0;
}
static int collect(struct list_head *head, int *ids)
{
    struct list_head *p;
    int n = 0;
    for (p = head->next; p != head; p = p->next) {
        assert(n < 128 && p->next->prev == p && p->prev->next == p);
        ids[n++] = list_entry(p, struct task_struct, se.group_node)->id;
    }
    return n;
}
static void assert_order(struct list_head *head, const int *ids, int count)
{
    int actual[128];
    assert(collect(head, actual) == count);
    assert(!memcmp(actual, ids, count * sizeof(*ids)));
}
static void rotation_tests(void)
{
    int size, pivot, i, expected[128];
    for (size = 0; size <= 12; size++) for (pivot = 0; pivot <= size; pivot++) {
        struct list_head *entry;
        setup(size);
        entry = pivot ? &w.allocated[pivot]->se.group_node : &w.rq[0].cfs_tasks;
        list_rotate_to_front(entry, &w.rq[0].cfs_tasks);
        for (i = 0; i < size; i++) expected[i] = pivot ? (pivot - 1 + i) % size + 1 : i + 1;
        assert_order(&w.rq[0].cfs_tasks, expected, size);
    }
    for (i = 0; i <= 5; i++) {
        int j;
        setup(5);
        for (j = 1; j <= 5; j++) w.allocated[j]->pinned = true;
        w.env.loop_max = i;
        assert(detach_tasks(&w.env) == 0);
        for (j = 0; j < 5; j++) expected[j] = (5 - i + j) % 5 + 1;
        assert_order(&w.rq[0].cfs_tasks, expected, 5);
        assert(w.visits == i && list_ops <= 1);
    }
    setup(5);
    w.allocated[5]->pinned = true; w.env.imbalance = 10;
    assert(detach_tasks(&w.env) == 1);
    assert_order(&w.rq[0].cfs_tasks, (int[]){5, 1, 2, 3}, 4);
    setup(5);
    for (i = 1; i <= 5; i++) w.allocated[i]->pinned = true;
    w.env.loop_break = 2;
    assert(detach_tasks(&w.env) == 0 && (w.env.flags & LBF_NEED_BREAK));
    assert(w.trace[0] == 5 && w.trace[1] == 4);
    w.env.flags &= ~LBF_NEED_BREAK;
    assert(detach_tasks(&w.env) == 0);
    assert(w.trace[2] == 3); /* Resume, not re-examine a prior reject. */
}
static void budget_tests(void)
{
    int i;
    setup(3);
    w.allocated[1]->load = 500; w.allocated[2]->load = 250; w.allocated[3]->load = 200;
    assert(detach_tasks(&w.env) == 1 && w.migrations == 1 && w.env.imbalance == -100);
    assert_order(&w.env.tasks, (int[]){3}, 1);
    setup(3);
    w.allocated[1]->load = 70; w.allocated[2]->load = 300; w.allocated[3]->load = 200;
    assert(detach_tasks(&w.env) == 1 && w.env.imbalance == 30);
    assert_order(&w.env.tasks, (int[]){1}, 1);
    setup(40);
    for (i = 1; i < 40; i++) w.allocated[i]->load = 1000;
    w.allocated[40]->load = 1; w.env.loop_break = 2;
    assert(detach_tasks(&w.env) == 1 && (w.env.flags & LBF_MOVED));
    assert(w.env.flags & LBF_NEED_BREAK);
    w.env.flags &= ~LBF_NEED_BREAK;
    assert(detach_tasks(&w.env) == 0 && w.migrations == 1);
    setup(3);
    for (i = 1; i <= 3; i++) w.allocated[i]->load = 1000;
    w.env.imbalance = 1;
    w.allocated[3]->load = ULONG_MAX;
    w.allocated[2]->pinned = w.allocated[1]->pinned = true;
    assert(detach_tasks(&w.env) == 1 && w.env.imbalance <= 0);
    setup(1); /* Preserve this tree's nr_running == 2 oversized-task exception. */
    w.allocated[1]->load = 1000; w.env.imbalance = 1;
    assert(detach_tasks(&w.env) == 1);
    setup(1);
    features[LB_STRICT_BUDGET] = false;
    w.allocated[1]->load = 1000; w.env.imbalance = 1;
    assert(detach_tasks(&w.env) == 1);
    setup(4);
    for (i = 1; i <= 4; i++) w.allocated[i]->load = 0;
    w.env.imbalance = 1;
    assert(detach_tasks(&w.env) == 1 && w.env.imbalance == 0);
    setup(3);
    features[LB_MIN] = true;
    assert(detach_tasks(&w.env) == 0 && w.migrations == 0);
    setup(4);
    w.allocated[1]->pinned = w.allocated[2]->running = true;
    w.allocated[3]->hot = w.allocated[4]->throttled = true;
    assert(detach_tasks(&w.env) == 0 && w.migrations == 0);
    setup(3);
    for (i = 1; i <= 3; i++) w.allocated[i]->load = 1000;
    w.step = 3000000;
    assert(detach_tasks(&w.env) == 0 && w.migrations == 0); /* No post-timeout concession. */
    setup(3);
    w.env.idle = CPU_NEWLY_IDLE;
#ifdef CONFIG_PREEMPT
    assert(detach_tasks(&w.env) == 1);
#else
    assert(detach_tasks(&w.env) == 3);
#endif
    setup(3);
    w.env.imbalance = 0;
    assert(detach_tasks(&w.env) == 0 && w.visits == 0);
    setup(0);
    assert(detach_tasks(&w.env) == 0);
    setup(4);
    w.same = false; w.capacity[1] = 500;
    for (i = 1; i <= 4; i++) {
        w.allocated[i]->big = true;
        w.allocated[i]->nonpreferred = true;
    }
    assert(detach_tasks(&w.env) > 0); /* Existing relaxed redo remains functional. */
    setup(12);
    w.churn = true; w.env.imbalance = 1000;
    assert(detach_tasks(&w.env) > 0);
    collect(&w.rq[0].cfs_tasks, (int[128]){0});
}
struct result {
    int moved, remaining[128], nr, out[128], no, trace[10000], nv, gained;
    unsigned flags, loop, brk;
    long imbalance;
};
static struct result capture(int moved)
{
    struct result r = {0};
    r.moved = moved; r.nr = collect(&w.rq[0].cfs_tasks, r.remaining);
    r.no = collect(&w.env.tasks, r.out); r.nv = w.visits;
    memcpy(r.trace, w.trace, w.visits * sizeof(int));
    r.flags = w.env.flags & ~LBF_MOVED; r.loop = w.env.loop;
    r.brk = w.env.loop_break; r.imbalance = w.env.imbalance;
    r.gained = w.sd.lb_gained[w.env.idle];
    return r;
}
static uint32_t rand32(uint32_t *state)
{
    *state ^= *state << 13; *state ^= *state >> 17; *state ^= *state << 5; return *state;
}
static void random_setup(uint32_t seed)
{
    int i, n = rand32(&seed) % 80;
    setup(n);
    w.env.imbalance = rand32(&seed) % 1000 + 1;
    w.env.idle = rand32(&seed) % 3;
    w.same = rand32(&seed) % 2;
    w.capacity[1] = (rand32(&seed) % 2) ? 500 : 1024;
    w.step = (rand32(&seed) % 4) ? 0 : 700000;
    w.churn = rand32(&seed) % 2;
    w.env.loop_max = rand32(&seed) % 81;
    w.env.loop_break = rand32(&seed) % 40 + 1;
    w.sd.nr_balance_failed = rand32(&seed) % 3;
    features[LB_MIN] = rand32(&seed) % 2;
    for (i = 1; i <= n; i++) {
        unsigned v = rand32(&seed);
        struct task_struct *p = w.allocated[i];
        p->load = rand32(&seed) % 2001;
        p->pinned = v & 1; p->running = v & 2; p->hot = v & 4;
        p->throttled = v & 8; p->big = v & 16; p->nonpreferred = v & 32;
    }
}
int main(void)
{
    unsigned i, combo;
    rotation_tests(); budget_tests();
    for (i = 1; i <= 3000; i++) {
        struct result old, current;
        uint32_t seed = i * 2654435761U;
        random_setup(seed); features[LB_ROTATE_BLOCK] = features[LB_STRICT_BUDGET] = false;
        old = capture(legacy_detach_tasks(&w.env));
        random_setup(seed); features[LB_ROTATE_BLOCK] = features[LB_STRICT_BUDGET] = false;
        current = capture(detach_tasks(&w.env));
        assert(!memcmp(&old, &current, sizeof(old)));
        for (combo = 0; combo < 4; combo++) {
            int moved;
            random_setup(seed);
            features[LB_ROTATE_BLOCK] = combo & 1;
            features[LB_STRICT_BUDGET] = combo & 2;
            moved = detach_tasks(&w.env);
            assert(moved == w.migrations && moved <= 80);
            assert(w.sd.lb_gained[w.env.idle] == moved);
            collect(&w.rq[0].cfs_tasks, (int[128]){0});
            collect(&w.env.tasks, (int[128]){0});
        }
    }
    clear_world();
    puts("PASS: rotation/budget/timeout/redo/filters/churn; 3000 exact legacy comparisons; 12000 mixed-feature cases");
    return 0;
}
