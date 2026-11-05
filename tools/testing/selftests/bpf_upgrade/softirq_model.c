// SPDX-License-Identifier: GPL-2.0
/* Extracted production functions, sorted-list queue and platform/IRQ mocks.
 * Not a concurrent kernel, timerqueue/rbtree test, or device-runtime claim.
 */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef int64_t ktime_t;
typedef uint8_t u8;
#define KTIME_MAX INT64_MAX
#define MAX_CLOCKS 16
#define HRTIMER_STATE_INACTIVE 0
#define HRTIMER_STATE_ENQUEUED 1
#define HRTIMER_STATE_PINNED 2
#define CONFIG_TIME_LOW_RES 1
#define IS_ENABLED(x) 1
#define __latent_entropy
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, y) ((x) = (y))
#define BUG_ON(x) assert(!(x))
#define WARN_ON_ONCE(x) assert(!(x))
#define lockdep_assert_held(p) assert(*(p))
#define container_of(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
#define ktime_sub(a, b) ((a) - (b))
#define ktime_add(a, b) ((a) + (b))
#define __ffs(x) __builtin_ctz(x)
#define for_each_active_base(base, cpu_base, active) \
	while ((base = __next_base((cpu_base), &(active))))
/* ENUMS */
#define MASK_SHIFT (HRTIMER_MAX_CLOCK_BASES / 2)
#define HRTIMER_ACTIVE_HARD ((1U << MASK_SHIFT) - 1)
#define HRTIMER_ACTIVE_SOFT (HRTIMER_ACTIVE_HARD << MASK_SHIFT)
#define HRTIMER_ACTIVE_ALL (HRTIMER_ACTIVE_HARD | HRTIMER_ACTIVE_SOFT)

enum hrtimer_restart { HRTIMER_NORESTART, HRTIMER_RESTART };
struct timerqueue_node { ktime_t expires; struct timerqueue_node *next; };
struct timerqueue_head { struct timerqueue_node *first; };
struct hrtimer_cpu_base;
struct hrtimer;
struct hrtimer_clock_base {
	struct hrtimer_cpu_base *cpu_base;
	unsigned int index, seq;
	ktime_t offset;
	struct hrtimer *running;
	struct timerqueue_head active;
};
struct hrtimer {
	struct timerqueue_node node;
	struct hrtimer_clock_base *base;
	enum hrtimer_restart (*function)(struct hrtimer *);
	ktime_t softexpires;
	u8 state;
	bool is_soft, is_rel;
};
struct hrtimer_cpu_base {
	struct hrtimer_clock_base clock_base[HRTIMER_MAX_CLOCK_BASES];
	struct hrtimer *next_timer, *softirq_next_timer;
	ktime_t expires_next, softirq_expires_next;
	unsigned int active_bases, clock_was_set_seq;
	int cpu, lock;
	bool softirq_activated, hres_active, hang_detected, in_hrtirq;
};
struct softirq_action { int unused; };
static struct hrtimer_cpu_base cpus[2];
static int current_cpu;
static bool irq_disabled, online[2], interrupt_context;
static unsigned int bh_depth, bh_disables, bh_enables, peeks;
static unsigned long checks, calls, update_calls;
#define __hrtimer_hres_active(cpu) ((cpu)->hres_active)
#define hrtimer_get_expires_tv64(t) ((t)->node.expires)
#define ktime_before(a, b) ((a) < (b))
static void tick_program_event(ktime_t expires, int force)
{
	(void)expires; (void)force; assert(irq_disabled); update_calls++;
}
#define per_cpu(x, cpu) cpus[cpu]
#define SINGLE_DEPTH_NESTING 1
#define in_interrupt() (interrupt_context || bh_depth)
#define local_bh_disable() (++bh_depth, ++bh_disables)
#define local_bh_enable() do { assert(!irq_disabled && bh_depth && !interrupt_context); bh_depth--; bh_enables++; } while (0)
#define local_irq_save(f) do { (f) = irq_disabled; irq_disabled = true; } while (0)
#define local_irq_restore(f) (irq_disabled = (f))
#define raw_spin_lock(p) do { assert(irq_disabled && !*(p)); *(p) = 1; } while (0)
#define raw_spin_unlock(p) do { assert(irq_disabled && *(p)); *(p) = 0; } while (0)
#define raw_spin_lock_nested(p, d) raw_spin_lock(p)
static void __hrtimer_peek_ahead_timers(void)
{
	assert(irq_disabled && !cpus[0].lock && !cpus[1].lock);
	assert(in_interrupt()); peeks++;
}
static ktime_t now, real_offset, boot_offset, tai_offset;
#define this_cpu_ptr(x) (&cpus[current_cpu])
#define raw_cpu_ptr(x) this_cpu_ptr(x)
#define cpu_online(c) online[c]
#define hrtimer_get_expires(t) ((t)->node.expires)
#define hrtimer_get_softexpires_tv64(t) ((t)->softexpires)
#define hrtimer_callback_running(t) ((t)->base->running == (t))
#define raw_write_seqcount_barrier(s) (++*(s))
#define raw_read_seqcount_begin(s) (*(s))
#define read_seqcount_retry(s, seq) (*(s) != (seq))
#define seqcount_init(s) (*(s) = 0)
#define trace_hrtimer_expire_entry(t, n) ((void)0)
#define trace_hrtimer_expire_exit(t) ((void)0)
#define raw_spin_lock_irqsave(p, f) do { (f) = irq_disabled; irq_disabled = true; assert(!*(p)); *(p) = 1; } while (0)
#define raw_spin_unlock_irqrestore(p, f) do { assert(*(p)); *(p) = 0; irq_disabled = (f); } while (0)
#define raw_spin_lock_irq(p) do { irq_disabled = true; assert(!*(p)); *(p) = 1; } while (0)
static void timerqueue_init(struct timerqueue_node *node) { node->next = NULL; }
static void timerqueue_init_head(struct timerqueue_head *head) { head->first = NULL; }
static struct timerqueue_node *timerqueue_getnext(struct timerqueue_head *head) { return head->first; }
static struct timerqueue_node *timerqueue_iterate_next(struct timerqueue_node *node) { return node->next; }
static bool timerqueue_add(struct timerqueue_head *head, struct timerqueue_node *node)
{
	struct timerqueue_node **p = &head->first;
	while (*p && (*p)->expires <= node->expires) p = &(*p)->next;
	node->next = *p; *p = node;
	return head->first == node;
}
static bool timerqueue_del(struct timerqueue_head *head, struct timerqueue_node *node)
{
	struct timerqueue_node **p = &head->first;
	while (*p && *p != node) p = &(*p)->next;
	assert(*p == node); *p = node->next; node->next = NULL;
	return head->first != NULL;
}
static void debug_activate(struct hrtimer *timer, enum hrtimer_mode mode)
{
	assert(timer->is_soft == !!(mode & HRTIMER_MODE_SOFT));
}
static void debug_deactivate(struct hrtimer *timer) { (void)timer; }
static ktime_t ktime_get_update_offsets_now(unsigned int *seq, ktime_t *r, ktime_t *b, ktime_t *t)
{
	(void)seq; *r = real_offset; *b = boot_offset; *t = tai_offset; return now;
}
static int hrtimer_clockid_to_base(clockid_t clockid);
static void hrtimer_update_softirq_timer(struct hrtimer_cpu_base *cpu, bool reprogram);
/* FUNCTIONS */
static int hrtimer_clockid_to_base(clockid_t clockid)
{
	assert(clockid >= 0 && clockid < MAX_CLOCKS);
	return hrtimer_clock_to_base_table[clockid];
}
static void reset(void)
{
	memset(cpus, 0, sizeof(cpus));
	for (int c = 0; c < 2; c++) {
		cpus[c].cpu = c; cpus[c].hres_active = true; online[c] = true;
		cpus[c].expires_next = cpus[c].softirq_expires_next = KTIME_MAX;
		for (int b = 0; b < HRTIMER_MAX_CLOCK_BASES; b++) {
			cpus[c].clock_base[b].cpu_base = &cpus[c];
			cpus[c].clock_base[b].index = b;
		}
	}
	current_cpu = 0; irq_disabled = false; interrupt_context = false;
	bh_depth = bh_disables = bh_enables = peeks = 0;
	now = real_offset = boot_offset = tai_offset = 0;
}
static void add(struct hrtimer *timer, int base, ktime_t expires, bool pinned)
{
	memset(timer, 0, sizeof(*timer));
	timer->base = &cpus[current_cpu].clock_base[base];
	timer->is_soft = base >= MASK_SHIFT;
	timer->node.expires = timer->softexpires = expires;
	timer->state = pinned ? HRTIMER_STATE_PINNED : 0;
	enqueue_hrtimer(timer, timer->base, HRTIMER_MODE_ABS |
		(timer->is_soft ? HRTIMER_MODE_SOFT : 0));
}
static uint32_t rng = 0x15b0f;
static uint32_t random32(void) { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; }
static ktime_t reference(struct hrtimer_cpu_base *cpu, unsigned int mask, const struct hrtimer *exclude)
{
	ktime_t result = KTIME_MAX;
	for (int b = 0; b < HRTIMER_MAX_CLOCK_BASES; b++) {
		if (!(mask & (1U << b))) continue;
		for (struct timerqueue_node *n = cpu->clock_base[b].active.first; n; n = n->next) {
			struct hrtimer *timer = container_of(n, struct hrtimer, node);
			if (timer == exclude) continue;
			ktime_t e = n->expires - cpu->clock_base[b].offset;
			if (e < result) result = e;
		}
	}
	return result < 0 ? 0 : result;
}
static void query_tests(void)
{
	for (int iter = 0; iter < 30000; iter++) {
		struct hrtimer timers[32];
		reset();
		int n = random32() % 33;
		for (int i = 0; i < n; i++) add(&timers[i], random32() % 8, random32() % 100000, false);
		for (int b = 0; b < 8; b++) cpus[0].clock_base[b].offset = random32() % 1000;
		for (int activated = 0; activated < 2; activated++) {
			cpus[0].softirq_activated = activated;
			for (int choice = 0; choice < 3; choice++) {
				unsigned int mask = choice == 0 ? HRTIMER_ACTIVE_ALL : choice == 1 ? HRTIMER_ACTIVE_HARD : HRTIMER_ACTIVE_SOFT;
				unsigned int expected_mask = mask & (activated ? HRTIMER_ACTIVE_HARD : HRTIMER_ACTIVE_ALL);
				assert(__hrtimer_get_next_event(&cpus[0], mask) == reference(&cpus[0], expected_mask, NULL)); checks++;
			}
			assert(hrtimer_update_next_event(&cpus[0]) == reference(&cpus[0], activated ? HRTIMER_ACTIVE_HARD : HRTIMER_ACTIVE_ALL, NULL)); checks++;
			struct hrtimer *hard = cpus[0].next_timer, *soft = cpus[0].softirq_next_timer;
			for (int i = 0; i < n; i++) {
				ktime_t e = __hrtimer_next_event_base(&cpus[0], &timers[i], cpus[0].active_bases, KTIME_MAX);
				assert(e == reference(&cpus[0], HRTIMER_ACTIVE_ALL, &timers[i]));
				assert(cpus[0].next_timer == hard && cpus[0].softirq_next_timer == soft); checks++;
			}
		}
	}
}
static void init_tests(void)
{
	const int clocks[] = { CLOCK_MONOTONIC, CLOCK_REALTIME, CLOCK_BOOTTIME, CLOCK_TAI };
	const int bases[] = { HRTIMER_BASE_MONOTONIC, HRTIMER_BASE_REALTIME, HRTIMER_BASE_BOOTTIME, HRTIMER_BASE_TAI };
	reset();
	for (int mode = 0; mode < 8; mode++) for (int c = 0; c < 4; c++) {
		struct hrtimer timer;
		memset(&timer, 0xa5, sizeof(timer));
		__hrtimer_init(&timer, clocks[c], mode);
		int expected = (c == 1 && (mode & HRTIMER_MODE_REL)) ? HRTIMER_BASE_MONOTONIC : bases[c];
		if (mode & HRTIMER_MODE_SOFT) expected += MASK_SHIFT;
		assert(timer.base == &cpus[0].clock_base[expected]);
		assert(timer.is_soft == !!(mode & HRTIMER_MODE_SOFT)); checks++;
	}
	real_offset = -7; boot_offset = 13; tai_offset = 31; now = 100;
	assert(hrtimer_update_base(&cpus[0]) == now);
	for (int i = 1; i < 4; i++) assert(cpus[0].clock_base[i].offset == cpus[0].clock_base[i + MASK_SHIFT].offset);
	checks++;
}
static void hard_dispatch(void)
{
	unsigned long flags;
	raw_spin_lock_irqsave(&cpus[0].lock, flags);
	__hrtimer_run_queues(&cpus[0], now, true, HRTIMER_ACTIVE_HARD);
	raw_spin_unlock_irqrestore(&cpus[0].lock, flags);
}
static int callback_mode;
static enum hrtimer_restart callback(struct hrtimer *timer)
{
	assert(!timer->base->cpu_base->lock);
	assert(timer->base->running == timer);
	assert(hrtimer_active(timer));
	assert(irq_disabled == !timer->is_soft);
	assert(!(timer->state & HRTIMER_STATE_ENQUEUED)); calls++;
	if (timer->is_soft && callback_mode == 1) {
		hard_dispatch();
		assert(timer->base->running == timer); checks++;
	}
	if (callback_mode == 2) {
		timer->node.expires = timer->softexpires = now + 100;
		return HRTIMER_RESTART;
	}
	if (callback_mode == 3) free(timer);
	return HRTIMER_NORESTART;
}
static void dispatch_tests(void)
{
	for (int base = 0; base < 8; base++) for (int pinned = 0; pinned < 2; pinned++) {
		struct hrtimer timer;
		reset(); callback_mode = 0; calls = 0; now = 100;
		add(&timer, base, 100, pinned); timer.function = callback;
		hard_dispatch();
		assert(calls == (unsigned long)!timer.is_soft);
		cpus[0].softirq_activated = true;
		hrtimer_run_softirq(NULL);
		assert(calls == 1 && !cpus[0].softirq_activated);
		assert(timer.state == (pinned ? HRTIMER_STATE_PINNED : 0));
		assert(!timer.base->running && !hrtimer_active(&timer)); checks++;
	}
	for (int soft = 0; soft < 2; soft++) {
		struct hrtimer timer;
		reset(); now = 100; callback_mode = 2;
		add(&timer, soft * MASK_SHIFT, 100, false); timer.function = callback;
		if (soft) hrtimer_run_softirq(NULL); else hard_dispatch();
		assert(timer.state & HRTIMER_STATE_ENQUEUED);
		assert(!timer.base->running && timer.node.expires == 200); checks++;
		reset(); now = 100; callback_mode = 3;
		struct hrtimer *heap = malloc(sizeof(*heap)); assert(heap);
		add(heap, soft * MASK_SHIFT, 100, false); heap->function = callback;
		if (soft) hrtimer_run_softirq(NULL); else hard_dispatch();
		assert(!cpus[0].active_bases); checks++;
	}
	reset(); now = 100; callback_mode = 1; calls = 0;
	struct hrtimer hard, soft;
	add(&hard, 0, 100, false); hard.function = callback;
	add(&soft, MASK_SHIFT, 100, false); soft.function = callback;
	hrtimer_run_softirq(NULL);
	assert(calls == 2 && !hard.base->running && !soft.base->running); checks++;
}
static void migrate_tests(void)
{
	for (int remove = 0; remove < 2; remove++) for (int offline = 0; offline < 2; offline++) {
		struct hrtimer timers[16];
		reset(); online[0] = !offline;
		for (int i = 0; i < 16; i++) add(&timers[i], i / 2, i * 10, i % 2);
		for (int b = 0; b < 8; b++) migrate_hrtimer_list(&cpus[0].clock_base[b], &cpus[1].clock_base[b], remove);
		for (int i = 0; i < 16; i++) {
			int destination = (!remove && i % 2) ? 0 : 1;
			assert(timers[i].base == &cpus[destination].clock_base[i / 2]);
			assert(timers[i].state == (HRTIMER_STATE_ENQUEUED | (i % 2 ? HRTIMER_STATE_PINNED : 0)));
			assert(timers[i].is_soft == (i / 2 >= MASK_SHIFT)); checks++;
		}
	}
}
static void migration_context_tests(void)
{
	for (int ipi = 0; ipi < 2; ipi++) for (int remove = 0; remove < 2; remove++) {
		struct hrtimer timers[16];
		reset();
		for (int i = 0; i < 16; i++) add(&timers[i], i / 2, 200 + i, i % 2);
		unsigned long flags;
		raw_spin_lock_irqsave(&cpus[0].lock, flags);
		hrtimer_update_softirq_timer(&cpus[0], false);
		raw_spin_unlock_irqrestore(&cpus[0].lock, flags);
		assert(cpus[0].softirq_expires_next == 208);
		current_cpu = 1;
		irq_disabled = interrupt_context = ipi;
		__migrate_hrtimers(0, remove);
		assert(irq_disabled == !!ipi && !bh_depth && peeks == 1);
		assert(bh_disables == (unsigned int)!ipi && bh_enables == (unsigned int)!ipi);
		for (int i = 0; i < 16; i++) {
			int destination = (!remove && i % 2) ? 0 : 1;
			assert(timers[i].base == &cpus[destination].clock_base[i / 2]); checks++;
		}
		assert(cpus[1].softirq_expires_next == 208);
		assert(cpus[0].softirq_expires_next == (remove ? KTIME_MAX : 209)); checks++;
	}
}
static void running_soft_quiesce_test(void)
{
	struct hrtimer timer;
	reset();
	/* A soft callback rearmed itself, then an IPI interrupted it. */
	add(&timer, MASK_SHIFT, 200, false);
	timer.base->running = &timer;
	struct hrtimer_clock_base *base = timer.base;
	current_cpu = 1; irq_disabled = interrupt_context = true;
	__migrate_hrtimers(0, false);
	assert(timer.base == base && base->running == &timer);
	assert(base->active.first == &timer.node);
	assert(timer.state == HRTIMER_STATE_ENQUEUED && timer.is_soft);
	assert(!cpus[1].active_bases); checks++;
}
static void clock_and_reset_tests(void)
{
	struct hrtimer hard, soft;
	reset();
	add(&hard, HRTIMER_BASE_MONOTONIC, 80, false);
	add(&soft, HRTIMER_BASE_REALTIME_SOFT, 200, false);
	irq_disabled = true; real_offset = 150;
	hrtimer_update_base(&cpus[0]); hrtimer_force_reprogram(&cpus[0], 0);
	assert(cpus[0].next_timer == &soft && cpus[0].expires_next == 50);
	assert(cpus[0].softirq_expires_next == 50); checks++;
	real_offset = 190;
	hrtimer_update_base(&cpus[0]); hrtimer_force_reprogram(&cpus[0], 1);
	assert(cpus[0].softirq_expires_next == 10 && cpus[0].expires_next == 10); checks++;
	cpus[0].softirq_activated = true;
	hrtimer_force_reprogram(&cpus[0], 0);
	assert(cpus[0].next_timer == &hard && cpus[0].expires_next == 80); checks++;
	for (int b = 0; b < 8; b++) {
		cpus[0].clock_base[b].seq = 42;
		cpus[0].clock_base[b].running = &soft;
	}
	cpus[0].hang_detected = true;
	assert(hrtimers_prepare_cpu(0) == 0);
	assert(!cpus[0].hang_detected && !cpus[0].softirq_activated && !cpus[0].hres_active);
	assert(!cpus[0].active_bases && !cpus[0].next_timer && !cpus[0].softirq_next_timer);
	assert(cpus[0].expires_next == KTIME_MAX && cpus[0].softirq_expires_next == KTIME_MAX);
	for (int b = 0; b < 8; b++) {
		assert(!cpus[0].clock_base[b].seq && !cpus[0].clock_base[b].running);
		assert(!cpus[0].clock_base[b].active.first); checks++;
	}
}
int main(void)
{
	init_tests(); query_tests(); dispatch_tests(); migrate_tests(); migration_context_tests(); running_soft_quiesce_test(); clock_and_reset_tests();
	assert(update_calls);
	printf("PASS: %lu extracted timer checks; base/mode selection, expiry/exclusion, offsets, hard/soft dispatch, nested hard IRQ, restart/free and pinned migration\n", checks);
	return 0;
}
