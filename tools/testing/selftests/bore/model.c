// SPDX-License-Identifier: GPL-2.0
#undef NDEBUG
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

typedef uint8_t u8;
typedef uint32_t u32;
typedef unsigned long long u64;
typedef int32_t s32;
#define __read_mostly
#undef __always_inline
#define __always_inline inline __attribute__((always_inline))
#define min(a, b) ({ typeof(a) x_ = (a); typeof(b) y_ = (b); x_ < y_ ? x_ : y_; })
#define max(a, b) ({ typeof(a) x_ = (a); typeof(b) y_ = (b); x_ > y_ ? x_ : y_; })
#define min_t(t, a, b) min((t)(a), (t)(b))
#define U32_MAX UINT32_MAX
#define MAX_RT_PRIO 100
#define WEIGHT_IDLEPRIO 3
#define WMULT_IDLEPRIO 1431655765U
#define MAX_BURST_PENALTY (39U << 2)
#define BORE_INHERIT_BUDGET 1024U
#define UPDATE_TG 1
#define idle_policy(p) ((p) == 5)
#define scale_load(w) ((unsigned long)(w) << 10)
#define container_of(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
#define div64_u64(n, d) ((n) / (d))
static unsigned int fls64(u64 v) { return v ? 64 - __builtin_clzll(v) : 0; }

/* DEFINITIONS */

static bool flip_depth;
static unsigned int depth_reads, visits;
#define READ_ONCE(v) ({ typeof(v) value = (v); \
	if ((void *)&(v) == (void *)&sched_burst_fork_atavistic) { \
		depth_reads++; if (flip_depth) sched_burst_fork_atavistic = 0; } value; })
#define WRITE_ONCE(v, n) ((v) = (n))
struct list_head { struct list_head *next, *prev; };
static void list_init(struct list_head *h) { h->next = h->prev = h; }
static void list_add_tail(struct list_head *n, struct list_head *h)
{
	n->prev = h->prev; n->next = h; h->prev->next = n; h->prev = n;
}
#define list_first_entry(h, type, m) container_of((h)->next, type, m)
#define list_for_each_entry(p, h, m) \
	for (p = list_first_entry(h, typeof(*p), m); \
	     &(p)->m != (h) && (++visits, 1); \
	     p = container_of((p)->m.next, typeof(*p), m))
struct load_weight { unsigned long weight; u32 inv_weight; };
struct cfs_rq;
struct sched_entity {
	struct load_weight load;
	struct cfs_rq *rq, *my_q;
	unsigned int on_rq;
	u64 burst_time, child_burst_last_cached;
	u8 prev_burst_penalty, curr_burst_penalty, burst_penalty, burst_score, child_burst;
	u32 child_burst_cnt;
};
struct task_struct {
	struct sched_entity se;
	int static_prio, policy;
	const void *sched_class;
	struct task_struct *real_parent;
	struct list_head children, sibling;
};
struct cfs_rq { struct sched_entity *curr; unsigned long weight; int nr_running; };
static int fair_sched_class, rt_sched_class, tasklist_lock;
static struct task_struct *current;
static u64 clock_ns = 100000000;
static u64 ktime_get_ns(void) { return clock_ns; }
#define lockdep_assert_held(lock) assert(*(lock))
#if MODEL_GROUP
#define entity_is_task(se) (!(se)->my_q)
#else
#define entity_is_task(se) 1
#endif
#define task_of(se) container_of(se, struct task_struct, se)
#define cfs_rq_of(se) ((se)->rq)
static unsigned long old_pelt_weight, init_weight;
static unsigned int reweights;
static void update_load_avg(struct sched_entity *se, int flags)
{
	old_pelt_weight = se->load.weight;
	reweights++;
}
static void update_curr(struct cfs_rq *rq) { (void)rq; }
static void update_load_set(struct load_weight *l, unsigned long w)
{
	l->weight = w; l->inv_weight = 0;
}
static void account_entity_dequeue(struct cfs_rq *q, struct sched_entity *se)
{
	assert(q->weight >= se->load.weight && q->nr_running == 1);
	q->weight -= se->load.weight; q->nr_running--;
}
static void account_entity_enqueue(struct cfs_rq *q, struct sched_entity *se)
{
	q->weight += se->load.weight; q->nr_running++;
}
static void init_entity_runnable_average(struct sched_entity *se)
{
	init_weight = se->load.weight;
}

/* FUNCTIONS */

static unsigned int cases;
static void math_tests(void)
{
	unsigned int old, new, a, b, bit;

	for (bit = 0; bit < 64; bit++) {
		u32 last = calc_burst_penalty((1ULL << bit) - 1);
		u32 next = calc_burst_penalty(1ULL << bit);

		assert(last <= next && next <= MAX_BURST_PENALTY);
	}
	assert(!calc_burst_penalty(0));
	assert(calc_burst_penalty(ULLONG_MAX) == MAX_BURST_PENALTY);
	for (a = 0; a <= 1; a++)
	for (b = 0; b <= 1; b++)
	for (old = 0; old <= MAX_BURST_PENALTY; old++)
	for (new = 0; new <= MAX_BURST_PENALTY; new++) {
		u32 want = new >= old ? old + ((new - old) >> a) : old - ((old - new) >> b);

		sched_burst_smoothness_long = a;
		sched_burst_smoothness_short = b;
		assert(binary_smooth(new, old) == want);
		cases++;
	}
	sched_burst_smoothness_long = sched_burst_smoothness_short = 1;
}

static void weights(void)
{
	unsigned int prio, score, idle, queued;

	for (prio = 0; prio < 40; prio++)
	for (score = 0; score < 40; score++)
	for (idle = 0; idle < 2; idle++)
	for (queued = 0; queued < 2; queued++) {
		struct cfs_rq rq = {0};
		struct task_struct p = {.static_prio = 100 + prio, .policy = idle ? 5 : 0};
		unsigned long old_weight, expected;

		p.se.rq = &rq;
		set_load_weight(&p);
		old_weight = p.se.load.weight;
		p.se.on_rq = queued;
		rq.curr = &p.se;
		rq.weight = queued ? old_weight : 0;
		rq.nr_running = queued;
		p.se.burst_penalty = score << 2;
		reweights = 0;
		update_burst_score(&p.se);
		expected = scale_load(idle ? WEIGHT_IDLEPRIO : sched_prio_to_weight[min(39U, prio + score)]);
		assert(p.se.load.weight == expected);
		assert(p.se.load.inv_weight == (idle ? WMULT_IDLEPRIO : sched_prio_to_wmult[min(39U, prio + score)]));
		assert(p.se.burst_score == score);
		assert(rq.weight == (queued ? expected : 0) && rq.nr_running == (int)queued);
		if (reweights) assert(old_pelt_weight == old_weight);
		p.static_prio = 100 + (prio + 1) % 40;
		set_load_weight(&p);
		expected = scale_load(idle ? WEIGHT_IDLEPRIO : sched_prio_to_weight[min(39U, (prio + 1) % 40 + score)]);
		assert(p.se.load.weight == expected);
		p.se.on_rq = 0;
		p.se.burst_time = 1000000000;
		update_burst_penalty(&p.se);
		restart_burst(&p.se);
		assert(!p.se.burst_time && !p.se.curr_burst_penalty);
		cases++;
	}
#if MODEL_GROUP
	{
		struct task_struct p = {.static_prio = 120};
		p.se.my_q = (void *)1;
		p.se.burst_penalty = 156;
		update_burst_score(&p.se);
		assert(!p.se.burst_score);
	}
#endif
}

static struct task_struct nodes[3072];
static void node_init(struct task_struct *p, u8 penalty)
{
	memset(p, 0, sizeof(*p));
	p->static_prio = 120;
	p->sched_class = &fair_sched_class;
	p->real_parent = p;
	list_init(&p->children); list_init(&p->sibling);
	p->se.burst_penalty = penalty;
}
static void attach(struct task_struct *p, struct task_struct *child)
{
	child->real_parent = p;
	list_add_tail(&child->sibling, &p->children);
}
static void inheritance(void)
{
	struct task_struct child;
	unsigned int i;
	u32 budget;

	for (i = 0; i < 3072; i++) node_init(&nodes[i], i % 157);
	current = &nodes[0];
	for (i = 1; i < 3072; i++) attach(&nodes[0], &nodes[i]);
	node_init(&child, 0); child.real_parent = &nodes[0];
	sched_fork_bore(&child);
	sched_burst_fork_atavistic = 0;
	visits = 0; tasklist_lock = 1;
	sched_post_fork_bore(&child);
	assert(visits <= BORE_INHERIT_BUDGET + 2);
	assert(!nodes[0].se.child_burst_last_cached);
	assert(child.se.burst_score == child.se.burst_penalty >> 2);
	assert(init_weight == child.se.load.weight);
	for (i = 0; i < 3072; i++) node_init(&nodes[i], 100);
	for (i = 1; i < 3072; i++) attach(&nodes[i - 1], &nodes[i]);
	node_init(&child, 0); child.real_parent = &nodes[3071];
	visits = depth_reads = 0;
	sched_burst_fork_atavistic = 2; flip_depth = true;
	sched_post_fork_bore(&child);
	assert(depth_reads == 1 && sched_burst_fork_atavistic == 0);
	assert(visits <= 8 * BORE_INHERIT_BUDGET);
	flip_depth = false;
	/* Exact direct mean, own-parent floor, cache reuse and expiry. */
	for (i = 0; i < 4; i++) node_init(&nodes[i], 0);
	attach(&nodes[0], &nodes[1]); attach(&nodes[0], &nodes[2]);
	nodes[1].se.burst_penalty = 40; nodes[2].se.burst_penalty = 80;
	budget = 1024;
	update_child_burst_direct(&nodes[0], clock_ns, &budget);
	assert(nodes[0].se.child_burst == 60 && nodes[0].se.child_burst_cnt == 2);
	assert(!child_burst_cache_expired(&nodes[0], clock_ns + 1));
	assert(child_burst_cache_expired(&nodes[0], clock_ns + 60000000));
	nodes[0].se.burst_penalty = 120;
	budget = 1024; update_child_burst_direct(&nodes[0], clock_ns, &budget);
	assert(nodes[0].se.child_burst == 120);
	nodes[2].sched_class = &rt_sched_class;
	nodes[0].se.burst_penalty = 0;
	budget = 1024; update_child_burst_direct(&nodes[0], clock_ns, &budget);
	assert(nodes[0].se.child_burst == 40 && nodes[0].se.child_burst_cnt == 1);
	/* Exact topological mean and weighted cached-subtree reuse. */
	for (i = 0; i < 7; i++) node_init(&nodes[i], 0);
	attach(&nodes[0], &nodes[1]); attach(&nodes[0], &nodes[2]);
	attach(&nodes[1], &nodes[3]); attach(&nodes[1], &nodes[4]);
	attach(&nodes[2], &nodes[5]); attach(&nodes[2], &nodes[6]);
	nodes[3].se.burst_penalty = 10; nodes[4].se.burst_penalty = 30;
	nodes[5].se.burst_penalty = 50; nodes[6].se.burst_penalty = 70;
	{
		u64 cnt = 0, sum = 0;
		budget = 1024;
		update_child_burst_topological(&nodes[0], clock_ns, 1, &cnt, &sum, &budget);
		assert(cnt == 4 && sum == 160 && nodes[0].se.child_burst == 40);
		nodes[3].se.burst_penalty = nodes[4].se.burst_penalty = 150;
		cnt = sum = 0; budget = 1024;
		update_child_burst_topological(&nodes[0], clock_ns + 1, 1, &cnt, &sum, &budget);
		assert(cnt == 4 && sum == 160); /* cached children */
		cnt = sum = 0; budget = 1024;
		update_child_burst_topological(&nodes[0], clock_ns + 60000000, 1, &cnt, &sum, &budget);
		assert(cnt == 4 && sum == 420 && nodes[0].se.child_burst == 105);
	}
	tasklist_lock = 0;
}

int main(void)
{
	math_tests(); weights(); inheritance();
	printf("BORE extracted-source model group=%d: PASS (%u math/weight cases, "
	       "inheritance/cache/budget checks)\n", MODEL_GROUP, cases);
	return 0;
}
