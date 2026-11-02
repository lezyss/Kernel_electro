// SPDX-License-Identifier: GPL-2.0
/* Userspace shims; the runner inserts production helper bodies below. */
#undef NDEBUG
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int32_t s32;
#define min(a, b) ((a) < (b) ? (a) : (b))
#define max(a, b) ((a) > (b) ? (a) : (b))
#define min_t(t, a, b) min((t)(a), (t)(b))
#define max_t(t, a, b) max((t)(a), (t)(b))
#define unlikely(x) (x)
/* Model a valid TCP header budget; not a real device's link-layer size. */
#define MAX_TCP_HEADER 256U
#define TCP_INIT_CWND 10U
struct minmax_sample { u32 t, v; };
struct minmax { struct minmax_sample s[3]; };
static u32 minmax_get(const struct minmax *m) { return m->s[0].v; }

/* DEFINITIONS */

struct sk_buff { u32 len, seq, end_seq; };
#define TCP_SKB_CB(skb) (skb)
struct tcp_sock {
	u64 delivered_mstamp;
	u32 mss_cache, snd_una, snd_wnd, snd_cwnd;
};
struct rate_sample {
	u32 prior_in_flight;
	int losses, acked_sacked, delivered, interval_us;
	bool is_app_limited;
};
struct sock;
struct tcp_congestion_ops {
	u32 (*min_tso_segs)(struct sock *);
	u32 (*tso_segs_goal)(struct sock *);
};
struct sock {
	u32 sk_pacing_rate, sk_pacing_shift, sk_gso_max_size, sk_gso_max_segs;
	struct tcp_congestion_ops *icsk_ca_ops;
	struct tcp_sock tp;
	struct bbr bbr;
	struct sk_buff *head;
};
#define inet_csk(sk) (sk)
#define inet_csk_ca(sk) ((void *)&(sk)->bbr)
#define tcp_sk(sk) (&(sk)->tp)
#define tcp_send_head(sk) ((sk)->head)
static u32 sysctl_tcp_min_tso_segs = 2;
static unsigned int random_value;
static u32 prandom_u32_max(u32 n) { assert(n); return random_value % n; }
static u32 tcp_wnd_end(const struct tcp_sock *tp)
{
	return tp->snd_una + tp->snd_wnd;
}
static bool after(u32 a, u32 b) { return (s32)(b - a) < 0; }
static u32 tcp_stamp_us_delta(u64 a, u64 b) { return a > b ? a - b : 0; }

#define PAGE_SHIFT 12
#define SK_MEM_QUANTUM (1U << PAGE_SHIFT)
#define nr_free_buffer_pages() free_pages
static unsigned long sysctl_tcp_wmem[3], sysctl_tcp_rmem[3];

/* FUNCTIONS */

static unsigned int goal_calls, min_calls, cases;
static u32 goal;
static u32 goal_callback(struct sock *sk) { goal_calls++; return goal; }
static u32 min_callback(struct sock *sk) { min_calls++; return 8; }

static void tso(void)
{
	const u32 rates[] = {0, 1, 149999, 150000, 1000000, UINT_MAX};
	const u32 goals[] = {0, 1, 2, 127, 4096};
	const u32 caps[] = {1, 16, 64};
	const u32 shifts[] = {0, 10, 31};
	struct tcp_congestion_ops ops;
	struct sock sk = {.icsk_ca_ops = &ops, .sk_gso_max_size = 65536};
	unsigned int a, b, c, d, e, f;

	for (a = 0; a < 6; a++)
	for (b = 0; b < 5; b++)
	for (c = 0; c < 3; c++)
	for (d = 0; d < 3; d++)
	for (e = 0; e < 2; e++)
	for (f = 0; f < 2; f++) {
		u32 want, bytes;

		goal_calls = min_calls = 0;
		goal = goals[b];
		ops = (struct tcp_congestion_ops){
			.tso_segs_goal = e ? goal_callback : NULL,
			.min_tso_segs = f ? min_callback : NULL,
		};
		sk.sk_pacing_rate = rates[a];
		sk.sk_pacing_shift = shifts[d];
		sk.sk_gso_max_segs = caps[c];
		bytes = min(rates[a] >> shifts[d], 65536 - 1 - MAX_TCP_HEADER);
		want = e && goal ? goal : max(bytes / 1460, f ? 8U : 2U);
		want = min(want, caps[c]);
		assert(tcp_tso_segs(&sk, 1460) == want);
		assert(goal_calls == e);
		assert(min_calls == (f && !(e && goal)));
		cases++;
	}
	ops = (struct tcp_congestion_ops){.tso_segs_goal = bbr_tso_segs_goal};
	sk.tp.mss_cache = 1460;
	sk.sk_pacing_shift = 10;
	sk.sk_pacing_rate = 149999;
	bbr_set_tso_segs_goal(&sk);
	assert(sk.bbr.tso_segs_goal == 1);
	sk.sk_pacing_rate = 150000;
	bbr_set_tso_segs_goal(&sk);
	assert(sk.bbr.tso_segs_goal == 2);
	sk.sk_pacing_rate = UINT_MAX;
	sk.sk_pacing_shift = 0;
	sk.sk_gso_max_size = 1000000;
	bbr_set_tso_segs_goal(&sk);
	assert(sk.bbr.tso_segs_goal == 127);
	assert(tcp_tso_segs(&sk, 1460) == sk.sk_gso_max_segs);
}

static void probe(void)
{
	struct sk_buff head = {.len = 1000, .end_seq = 1000};
	struct sock base = {.head = &head, .tp = {
		.delivered_mstamp = 2000, .mss_cache = 1000, .snd_wnd = 100000}};
	struct rate_sample rs = {.prior_in_flight = 100};
	struct sock sk;
	unsigned int i;

	base.bbr.mode = BBR_PROBE_BW;
	base.bbr.min_rtt_us = 1000;
	base.bbr.cycle_len = 8;
	base.bbr.bw.s[0].v = BW_UNIT;
	bbr_set_cycle_idx(&base, BBR_BW_PROBE_UP);
	sk = base;
	bbr_drain_to_target_cycling(&sk, &rs);
	assert(sk.bbr.cycle_idx == BBR_BW_PROBE_UP);
	for (i = 0; i < 5; i++) {
		struct rate_sample sample = rs;

		sk = base;
		if (i == 0) sample.losses = 1;
		if (i == 1) sample.is_app_limited = true;
		if (i == 2) sk.head = NULL;
		if (i == 3) sk.tp.snd_wnd = 1;
		if (i == 4) sample.prior_in_flight = 2000;
		bbr_drain_to_target_cycling(&sk, &sample);
		assert(sk.bbr.cycle_idx == BBR_BW_PROBE_DOWN);
		assert(sk.bbr.pacing_gain == BBR_UNIT * 3 / 4);
		bbr_drain_to_target_cycling(&sk, &rs);
		assert(sk.bbr.cycle_idx == BBR_BW_PROBE_CRUISE);
		assert(sk.bbr.pacing_gain == BBR_UNIT);
	}
	for (i = 0; i < 7; i++) {
		sk = base;
		sk.tp.delivered_mstamp = 8001;
		random_value = i;
		bbr_drain_to_target_cycling(&sk, &rs);
		assert(sk.bbr.cycle_len == 8 - i);
		assert(sk.bbr.cycle_idx == BBR_BW_PROBE_UP);
		assert(sk.bbr.cycle_mstamp == sk.tp.delivered_mstamp);
	}
	{
		struct bbr before;

		sk = base;
		sk.bbr.mode = BBR_STARTUP;
		before = sk.bbr;
		bbr_drain_to_target_cycling(&sk, &rs);
		assert(!memcmp(&sk.bbr, &before, sizeof(before)));
	}
	/* A policer estimate must keep unity gain even when a new cycle starts. */
	sk = base;
	sk.bbr.lt_use_bw = 1;
	sk.tp.delivered_mstamp = 8001;
	bbr_drain_to_target_cycling(&sk, &rs);
	assert(sk.bbr.pacing_gain == BBR_UNIT);
}

static void ack_aggregation(void)
{
	struct sock sk = {.tp = {.delivered_mstamp = 10, .snd_cwnd = 100}};
	struct rate_sample rs = {.acked_sacked = 5, .delivered = 5, .interval_us = 10};
	struct bbr before;

	sk.bbr.bw.s[0].v = BW_UNIT;
	sk.bbr.ack_epoch_acked = 20;
	bbr_update_ack_aggregation(&sk, &rs);
	assert(sk.bbr.ack_epoch_acked == 25);
	assert(sk.bbr.extra_acked[0] == 15);
	before = sk.bbr;
	rs.acked_sacked = 0;
	bbr_update_ack_aggregation(&sk, &rs);
	assert(!memcmp(&sk.bbr, &before, sizeof(before)));
	rs.acked_sacked = 5;
	sk.bbr.ack_epoch_acked = (1U << 20) - 1;
	bbr_update_ack_aggregation(&sk, &rs);
	assert(sk.bbr.ack_epoch_acked == 5);
	assert(sk.bbr.ack_epoch_mstamp == 10);
	sk.bbr.round_start = 1;
	sk.bbr.extra_acked_win_rtts = 9;
	sk.bbr.extra_acked[1] = 100;
	bbr_update_ack_aggregation(&sk, &rs);
	assert(sk.bbr.extra_acked_win_idx == 1);
	assert(sk.bbr.extra_acked_win_rtts == 0);
	assert(sk.bbr.extra_acked[1] <= sk.tp.snd_cwnd);
}

static void memory_limits(void)
{
	const unsigned long pages[] = {0, 1, 2048, 131072, 196608, 524288, 1048576};
	unsigned int i;

	for (i = 0; i < sizeof(pages) / sizeof(pages[0]); i++) {
		unsigned long cap = min(16UL * 1024 * 1024, pages[i] * 32UL);

		init_memory_limits(pages[i]);
		assert(sysctl_tcp_wmem[0] == SK_MEM_QUANTUM);
		assert(sysctl_tcp_rmem[0] == SK_MEM_QUANTUM);
		assert(sysctl_tcp_wmem[1] == 16 * 1024);
		assert(sysctl_tcp_rmem[1] == 87380);
		assert(sysctl_tcp_wmem[2] == max(64UL * 1024, cap));
		assert(sysctl_tcp_rmem[2] == max(87380UL, cap));
	}
}

int main(void)
{
	assert(sizeof(struct bbr) <= 112);
	tso();
	probe();
	ack_aggregation();
	memory_limits();
	printf("BBRplus extracted-source models: PASS (%u TSO cases, probe phases, "
	       "ACK aggregation, memory limits; private state %zu bytes)\n", cases, sizeof(struct bbr));
	return 0;
}
