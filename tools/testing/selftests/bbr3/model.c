/* SPDX-License-Identifier: GPL-2.0 */
/* Host fixture around the actual BBRv3/rate/loss/split/merge source. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stddef.h>
#include <errno.h>
#define ENOTSUPP 524
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define TCP_CONG_MASK 7

typedef uint64_t u64;
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
typedef int64_t s64;
typedef int32_t s32;
typedef uint32_t __u32;
typedef uint8_t __u8;
#define min(a,b) ({ __typeof__(a) _a=(a); __typeof__(b) _b=(b); _a<_b?_a:_b; })
#define max(a,b) ({ __typeof__(a) _a=(a); __typeof__(b) _b=(b); _a>_b?_a:_b; })
#define min_t(t,a,b) min((t)(a),(t)(b))
#define max_t(t,a,b) max((t)(a),(t)(b))
#define clamp(v,a,b) min(max(v,a),b)
#define clamp_t(t,v,a,b) min_t(t,max_t(t,v,a),b)
#define unlikely(v) (v)
#define likely(v) (v)
#define READ_ONCE(v) (v)
#define WRITE_ONCE(v,x) ((v)=(x))
#define do_div(v,d) ((v)/=(d))
#define div_u64(v,d) ((u64)(v)/(d))
#define DIV_ROUND_UP_ULL(v,d) (((u64)(v)+(d)-1)/(d))
#define DIV_ROUND_UP(v,d) (((v)+(d)-1)/(d))
#define USEC_PER_SEC 1000000U
#define USEC_PER_MSEC 1000U
#define INET_DIAG_VEGASINFO 3
#define INET_DIAG_BBRINFO 16
static u32 ilog2(u64 v) { assert(v); return 63U - __builtin_clzll(v); }
#define HZ 1000U
#define MAX_TCP_HEADER 128U
#define GSO_MAX_SIZE 65536U
#define TCP_INIT_CWND 10U
#define TCP_INFINITE_SSTHRESH 0x7fffffffU
#define SK_PACING_NONE 0
#define SK_PACING_NEEDED 1
#define TCP_CONG_NON_RESTRICTED 1
#define TCP_CONG_RATE_IN_FLIGHT 4
#define TCP_CA_NAME_MAX 16
#define TCPCB_LOST 4
#define TCPCB_SACKED_RETRANS 2
#define TCPCB_SACKED_ACKED 1
#define TCPCB_RETRANS 0x92
#define ICSK_CA_PRIV_SIZE 144
#define SKB_TRUESIZE(v) (256U+(v))
#define cmpxchg(p,a,b) __sync_val_compare_and_swap(p,a,b)
#define EXPORT_SYMBOL_GPL(v)
#define __read_mostly
#define __init
#define __exit
#define THIS_MODULE NULL
#define BUILD_BUG_ON(v) _Static_assert(!(v), #v)
#define module_init(v)
#define module_exit(v)
#define MODULE_AUTHOR(v)
#define MODULE_LICENSE(v)
#define MODULE_DESCRIPTION(v)
#define MODULE_VERSION(v)
#define __stringify(v) #v
#define pr_debug(...) ((void)0)
static unsigned int warning_count;
static bool model_warn(bool v, const char *fmt, ...)
{ warning_count += v; return v; }
#define WARN_ONCE(v,...) model_warn(!!(v), "" __VA_ARGS__)
#define WARN_ON_ONCE(v) WARN_ONCE(v)
static u32 jiffies = 10000;
#define tcp_jiffies32 jiffies
static u32 sysctl_tcp_min_tso_segs = 2;
enum { TCP_CA_Open, TCP_CA_Disorder, TCP_CA_CWR, TCP_CA_Recovery, TCP_CA_Loss };
struct list_head { struct list_head *next, *prev; };
struct sock;
struct sk_buff;
struct module;
union tcp_cc_info;
struct ack_sample;
/* DEFINITIONS */
/* DIAG */
struct tcp_sock;
struct inet_connection_sock {
	struct tcp_congestion_ops *icsk_ca_ops;
	u8 icsk_ca_state;
	u64 ca_priv[ICSK_CA_PRIV_SIZE / sizeof(u64)];
};
struct sock {
	struct tcp_sock *tp;
	struct inet_connection_sock *icsk;
	u64 sk_pacing_rate, sk_max_pacing_rate;
	u32 sk_pacing_shift, sk_pacing_status, sk_gso_max_size, sk_wmem_alloc;
	u32 sk_gso_max_segs;
};
struct tcp_sock {
	struct sock sk; /* loss hook casts tcp_sock to sock, as in the kernel */
	u32 delivered, delivered_ce, lost, app_limited;
	u32 packets_out, retrans_out, lost_out, sacked_out;
	u64 first_tx_mstamp, delivered_mstamp, tcp_mstamp;
	u32 snd_cwnd, snd_cwnd_clamp, snd_ssthresh, prior_cwnd;
	u32 mss_cache, srtt_us, rtt_min, rcv_nxt, snd_nxt, write_seq, snd_una;
	u32 rate_delivered, rate_interval_us;
	bool rate_app_limited, is_cwnd_limited, is_sack_reneg;
	bool tlp_orig_data_app_limited, tlp_retrans;
	u32 tlp_high_seq;
	struct { u8 sack_ok; } rx_opt;
};
struct sk_buff { u64 skb_mstamp; u32 pcount; char cb[48]; };
#define TCP_SKB_CB(skb) ((struct tcp_skb_cb *)((skb)->cb))
static struct tcp_sock *tcp_sk(const struct sock *sk) { return sk->tp; }
static struct inet_connection_sock *inet_csk(const struct sock *sk) { return sk->icsk; }
static void *inet_csk_ca(const struct sock *sk) { return sk->icsk->ca_priv; }
static u32 tcp_skb_pcount(const struct sk_buff *skb) { return skb->pcount; }
static u32 tcp_packets_in_flight(const struct tcp_sock *tp)
{ return tp->packets_out + tp->retrans_out - tp->lost_out - tp->sacked_out; }
static bool before(u32 a,u32 b) { return (s32)(a-b)<0; }
static bool after(u32 a,u32 b) { return before(b,a); }
static u32 tcp_min_rtt(const struct tcp_sock *tp) { return tp->rtt_min; }
static u32 tcp_stamp_us_delta(u64 a,u64 b) { return max_t(s64,a-b,0); }
static u32 usecs_to_jiffies(u32 v) { return v / 1000; }
static u32 msecs_to_jiffies(u32 v) { return v; }
static u32 jiffies_to_usecs(u32 v) { return v * 1000; }
static u32 sk_wmem_alloc_get(const struct sock *sk) { return sk->sk_wmem_alloc; }
static u32 prandom_u32_max(u32 v)
{ static u32 seed=12345; seed=seed*1664525+1013904223; return ((u64)seed*v)>>32; }
static int tcp_register_congestion_control(struct tcp_congestion_ops *ca) { return 0; }
static void tcp_unregister_congestion_control(struct tcp_congestion_ops *ca) {}
/* HELPERS */
static void split_snapshot(struct sk_buff *skb, struct sk_buff *buff, int old_factor)
{ int inflight_prev; (void)inflight_prev; /* SPLIT */ }
static void merge_snapshot(struct sk_buff *skb, struct sk_buff *prev, u32 pcount)
{ /* MERGE */ }
/* LOSS */
/* RATE */
/* BBR3 */
/* TSO */
/* ACK FLAGS */
static unsigned int tlp_reductions, tlp_notices;
#define NET_INC_STATS(net,field) ((void)0)
static void tcp_ca_event(struct sock *sk, enum tcp_ca_event ev)
{ if (inet_csk(sk)->icsk_ca_ops->cwnd_event) inet_csk(sk)->icsk_ca_ops->cwnd_event(sk,ev); }
static void tcp_init_cwnd_reduction(struct sock *sk)
{ tcp_sk(sk)->tlp_high_seq=0; tlp_reductions++; }
static void tcp_set_ca_state(struct sock *sk, u8 state)
{ inet_csk(sk)->icsk_ca_state=state; }
static void tcp_end_cwnd_reduction(struct sock *sk) {}
static void tcp_try_keep_open(struct sock *sk) {}
/* TLP */
/* BPF TABLES */
struct btf_type { int unused; };
struct btf_member { u32 type, offset; };
static void *btf_vmlinux;
static u32 btf_member_bit_offset(const struct btf_type *t, const struct btf_member *m)
{ return m->offset*8; }
static const void *btf_type_resolve_func_ptr(void *btf, u32 type, void *id)
{ return type ? (const void *)1 : NULL; }
static int bpf_obj_name_cpy(char *dst, const char *src, size_t size)
{ size_t len=strnlen(src,size); if (!len || len>=size) return -EINVAL; memcpy(dst,src,len+1); return len; }
static const struct tcp_congestion_ops *tcp_ca_find(const char *name) { return NULL; }
/* BPF MEMBERS */

static void setup(struct tcp_sock *tp, struct inet_connection_sock *icsk)
{
	memset(tp,0,sizeof(*tp)); memset(icsk,0,sizeof(*icsk));
	tp->sk.tp=tp; tp->sk.icsk=icsk;
	icsk->icsk_ca_ops=&tcp_bbr_cong_ops;
	tp->sk.sk_max_pacing_rate=UINT64_MAX;
	tp->sk.sk_gso_max_size=65536; tp->sk.sk_pacing_shift=10;
	tp->snd_cwnd=10; tp->snd_cwnd_clamp=1000000;
	tp->mss_cache=1448; tp->srtt_us=80000; tp->rtt_min=10000;
	tp->tcp_mstamp=1000000; tp->is_cwnd_limited=true;
	bbr_init(&tp->sk);
}
static unsigned int loss_calls;
static void loss_probe(struct sock *sk, const struct sk_buff *skb)
{ loss_calls++; assert(tcp_sk(sk)->lost>=tcp_skb_pcount(skb)); }
static void accounting(void)
{
	struct tcp_sock tp; struct inet_connection_sock icsk;
	struct sk_buff skb={.pcount=3,.skb_mstamp=1000000};
	struct rate_sample rs={0}; struct tcp_congestion_ops legacy={0};
	setup(&tp,&icsk);
	tp.delivered=0xfffffff0U; tp.delivered_ce=0xfffffff0U; tp.lost=0xfffffff0U;
	tp.packets_out=17; tp.sacked_out=2; tp.lost_out=3; tp.retrans_out=1;
	tp.first_tx_mstamp=tp.delivered_mstamp=1000000;
	tcp_rate_skb_sent(&tp.sk,&skb);
	assert(TCP_SKB_CB(&skb)->tx.in_flight==16);
	assert(TCP_SKB_CB(&skb)->tx.in_flight_is_packets);
	assert(TCP_SKB_CB(&skb)->tx.lost==tp.lost);
	tcp_rate_skb_delivered(&tp.sk,&skb,&rs);
	tp.tcp_mstamp=1100000; tp.delivered+=30; tp.delivered_ce+=7; tp.lost+=4;
	tcp_rate_gen(&tp.sk,3,1,false,&rs);
	assert(rs.delivered==30 && rs.delivered_ce==7 && rs.lost==4);
	assert(rs.losses==1 && rs.is_tx_in_flight_valid && rs.tx_in_flight==16);
	/* A CC switch must not reinterpret the legacy byte count. */
	icsk.icsk_ca_ops=&legacy; memset(&rs,0,sizeof(rs));
	/* Non-cloning retransmit after bbr3 -> legacy switch: an old packet
	 * count MUST be replaced by bytes before clearing the format bit.
	 */
	TCP_SKB_CB(&skb)->tx.in_flight=16;
	TCP_SKB_CB(&skb)->end_seq=16200; tp.snd_una=200;
	tcp_rate_skb_sent(&tp.sk,&skb);
	assert(!TCP_SKB_CB(&skb)->tx.in_flight_is_packets);
	assert(TCP_SKB_CB(&skb)->tx.in_flight==16000);
	icsk.icsk_ca_ops=&tcp_bbr_cong_ops;
	tcp_rate_skb_delivered(&tp.sk,&skb,&rs);
	assert(!rs.is_tx_in_flight_valid);
	/* Full-width timestamps cross both low-32 and low-40 boundaries. */
	for (u32 i=0;i<10000;i++) {
		u64 stamp=(1ULL<<40)+UINT32_MAX-500+i*37ULL;
		memset(&rs,0,sizeof(rs));
		tp.first_tx_mstamp=tp.delivered_mstamp=stamp;
		skb.skb_mstamp=stamp+1000; tp.tcp_mstamp=stamp+20000;
		tcp_rate_skb_sent(&tp.sk,&skb);
		tcp_rate_skb_delivered(&tp.sk,&skb,&rs);
		tp.delivered++; tcp_rate_gen(&tp.sk,1,0,false,&rs);
		assert(rs.interval_us==20000 && rs.delivered==1);
	}
	/* Beyond the signed modular interval, reject rather than invent a
	 * multi-billion-microsecond rate sample. Normal TCP RTOs expire sooner.
	 */
	memset(&rs,0,sizeof(rs));
	tp.first_tx_mstamp=tp.delivered_mstamp=1ULL<<40;
	skb.skb_mstamp=tp.first_tx_mstamp;
	tcp_rate_skb_sent(&tp.sk,&skb);
	/* Zero itself is the deliberately invalid snapshot sentinel. */
	tp.first_tx_mstamp=tp.delivered_mstamp=(1ULL<<40)+100;
	skb.skb_mstamp=tp.first_tx_mstamp;
	tcp_rate_skb_sent(&tp.sk,&skb);
	tcp_rate_skb_delivered(&tp.sk,&skb,&rs);
	tp.tcp_mstamp=skb.skb_mstamp+(1ULL<<31)+100;
	tcp_rate_gen(&tp.sk,1,0,false,&rs);
	assert(rs.interval_us==-1);
	memset(&rs,0,sizeof(rs));
	TCP_SKB_CB(&skb)->tx.delivered_mstamp=0;
	tcp_rate_skb_delivered(&tp.sk,&skb,&rs);
	tcp_rate_gen(&tp.sk,0,0,false,&rs);
	assert(rs.delivered==-1 && !rs.is_tx_in_flight_valid);
	/* Reneging makes even an otherwise tagged sample invalid. */
	rs.prior_mstamp=1; rs.is_tx_in_flight_valid=true;
	tcp_rate_gen(&tp.sk,0,0,true,&rs);
	assert(rs.delivered==-1 && !rs.is_tx_in_flight_valid);
	legacy.skb_marked_lost=loss_probe; icsk.icsk_ca_ops=&legacy;
	TCP_SKB_CB(&skb)->sacked=0; tp.lost=0; loss_calls=0;
	tcp_sum_lost(&tp,&skb); assert(tp.lost==3 && loss_calls==1);
	TCP_SKB_CB(&skb)->sacked=TCPCB_LOST;
	tcp_sum_lost(&tp,&skb); assert(tp.lost==3 && loss_calls==1);
	TCP_SKB_CB(&skb)->sacked|=TCPCB_SACKED_RETRANS;
	tcp_sum_lost(&tp,&skb); assert(tp.lost==6 && loss_calls==2);
}
static void segmentation(void)
{
	struct sk_buff a={0},b={0};
	for (u32 prior=0;prior<100;prior++)
	for (u32 n=2;n<40;n++)
	for (u32 first=1;first<n;first++) {
		a.pcount=first; b.pcount=n-first;
		TCP_SKB_CB(&a)->tx.in_flight=prior+n;
		TCP_SKB_CB(&a)->tx.in_flight_is_packets=1;
		TCP_SKB_CB(&b)->tx=TCP_SKB_CB(&a)->tx;
		split_snapshot(&a,&b,n);
		assert(TCP_SKB_CB(&a)->tx.in_flight==prior+first);
		assert(TCP_SKB_CB(&b)->tx.in_flight==prior+n);
		merge_snapshot(&b,&a,n-first);
		assert(TCP_SKB_CB(&a)->tx.in_flight==prior+n);
		assert(TCP_SKB_CB(&b)->tx.in_flight==prior+first);
	}
	/* Mixed-format merging changes only packet-valued snapshots. */
	TCP_SKB_CB(&a)->tx.in_flight_is_packets=0;
	TCP_SKB_CB(&a)->tx.in_flight=9999;
	TCP_SKB_CB(&b)->tx.in_flight_is_packets=1;
	TCP_SKB_CB(&b)->tx.in_flight=10;
	merge_snapshot(&b,&a,3);
	assert(TCP_SKB_CB(&a)->tx.in_flight==9999 && TCP_SKB_CB(&b)->tx.in_flight==7);
	TCP_SKB_CB(&a)->tx.in_flight_is_packets=0;
	TCP_SKB_CB(&b)->tx.in_flight_is_packets=0;
	split_snapshot(&a,&b,5);
	assert(TCP_SKB_CB(&a)->tx.in_flight==9999 && TCP_SKB_CB(&b)->tx.in_flight==7);
	/* Local failed retransmission: pcount may have grown. */
	a.pcount=2; b.pcount=3;
	TCP_SKB_CB(&a)->sacked=TCPCB_LOST;
	TCP_SKB_CB(&a)->tx.in_flight_is_packets=1;
	TCP_SKB_CB(&a)->tx.in_flight=1;
	TCP_SKB_CB(&b)->tx=TCP_SKB_CB(&a)->tx;
	split_snapshot(&a,&b,5);
	assert(TCP_SKB_CB(&a)->tx.in_flight==2 && TCP_SKB_CB(&b)->tx.in_flight==5);
	assert(!warning_count);
}
static void algorithm(void)
{
	struct tcp_sock tp; struct inet_connection_sock icsk;
	struct rate_sample rs={.tx_in_flight=1000,.lost=30,.delivered=100};
	struct sk_buff skb={.pcount=5}; union tcp_cc_info info; int attr=-1;
	setup(&tp,&icsk); struct bbr *bbr=inet_csk_ca(&tp.sk);
	assert(sizeof(*bbr)==144);
	assert(bbr->mode==BBR_STARTUP && !bbr->ecn_eligible);
	assert(bbr_is_inflight_too_high(&tp.sk,&rs));
	rs.lost=10; assert(!bbr_is_inflight_too_high(&tp.sk,&rs));
	/* Excess classic ECE alone is NOT evidence of ECN_LOW. */
	rs.lost=0; rs.delivered_ce=99;
	assert(!bbr_is_inflight_too_high(&tp.sk,&rs));
	/* No model evolution from legacy byte-valued samples on a live switch. */
	rs=(struct rate_sample){.interval_us=10000,.delivered=100,.acked_sacked=1,
		.prior_delivered=tp.delivered,.tx_in_flight=10000,.lost=100};
	bbr_main(&tp.sk,&rs);
	assert(bbr_max_bw(&tp.sk)==0 && !bbr->round_start && !bbr->loss_in_cycle);
	/* A genuine, packet-valued delivery sample does update the model. */
	rs.is_tx_in_flight_valid=true; rs.lost=0;
	tp.delivered=100; bbr_main(&tp.sk,&rs);
	assert(bbr_max_bw(&tp.sk)>0 && bbr->round_start);
	/* The loss callback must ignore legacy byte counts, even while probing. */
	bbr->bw_probe_samples=1; bbr->inflight_hi=1000;
	TCP_SKB_CB(&skb)->tx.in_flight=1000;
	TCP_SKB_CB(&skb)->tx.delivered_mstamp=1;
	TCP_SKB_CB(&skb)->tx.lost=0; tp.lost=30;
	bbr_skb_marked_lost(&tp.sk,&skb);
	assert(bbr->inflight_hi==1000);
	TCP_SKB_CB(&skb)->tx.in_flight_is_packets=1;
	bbr_skb_marked_lost(&tp.sk,&skb);
	assert(bbr->inflight_hi<1000);
	/* No kernel-info tail: legacy ABI remains 20 bytes, v3 reports 52. */
	memset(&info,0xa5,sizeof(info));
	assert(sizeof(struct tcp_bbr_info)==20 && sizeof(struct tcp_bbr3_info)==52);
	assert(bbr_get_info(&tp.sk,~0U,&attr,&info)==52);
	assert(info.bbr3.bbr_version==3 && info.bbr3.unused1==0);
	assert(attr==INET_DIAG_BBRINFO);
	assert(!warning_count);
}
static void tlp_notice(struct sock *sk, enum tcp_ca_event ev)
{ if (ev==CA_EVENT_TLP_RECOVERY) tlp_notices++; }
static void tail_loss(void)
{
	struct tcp_sock tp; struct inet_connection_sock icsk;
	struct tcp_congestion_ops ca={.cwnd_event=tlp_notice};
	struct rate_sample rs={0};
	setup(&tp,&icsk); icsk.icsk_ca_ops=&ca;
	tp.tlp_high_seq=100; tp.tlp_retrans=true;
	tcp_process_tlp_ack(&tp.sk,99,FLAG_DATA_ACKED,&rs);
	assert(tp.tlp_high_seq==100 && !rs.is_acking_tlp_retrans_seq);
	tcp_process_tlp_ack(&tp.sk,100,FLAG_DATA_ACKED,&rs);
	assert(tp.tlp_high_seq==100 && rs.is_acking_tlp_retrans_seq);
	memset(&rs,0,sizeof(rs));
	tcp_process_tlp_ack(&tp.sk,101,FLAG_DATA_ACKED,&rs);
	assert(tp.tlp_high_seq==0 && tlp_notices==1 && tlp_reductions==1);
	tp.tlp_high_seq=100;
	tcp_process_tlp_ack(&tp.sk,100,FLAG_DSACKING_ACK,&rs);
	assert(tp.tlp_high_seq==0 && tlp_notices==1);
	tp.tlp_high_seq=100;
	tcp_process_tlp_ack(&tp.sk,100,0,&rs);
	assert(tp.tlp_high_seq==0 && tlp_notices==1);
	tp.tlp_high_seq=100; tp.tlp_retrans=false;
	tcp_process_tlp_ack(&tp.sk,100,FLAG_DATA_ACKED,&rs);
	assert(tp.tlp_high_seq==0 && tlp_notices==1);
}
static void phases(void)
{
	struct tcp_sock tp; struct inet_connection_sock icsk;
	setup(&tp,&icsk); struct bbr *bbr=inet_csk_ca(&tp.sk);
	unsigned int modes=1U<<bbr->mode, cycles=0;
	for (u32 i=0;i<1000;i++) {
		struct rate_sample rs={.interval_us=10000,.rtt_us=10000,
			.delivered=10,.acked_sacked=10,.tx_in_flight=10,
			.is_tx_in_flight_valid=true,.prior_delivered=tp.delivered};
		tp.delivered+=10; tp.tcp_mstamp+=10000; jiffies+=10;
		tp.packets_out=bbr->mode==BBR_STARTUP ? tp.snd_cwnd : 2;
		bbr_main(&tp.sk,&rs);
		modes|=1U<<bbr->mode;
		if (bbr->mode==BBR_PROBE_BW) cycles|=1U<<bbr->cycle_idx;
		assert(tp.snd_cwnd>=4 && tp.snd_cwnd<=tp.snd_cwnd_clamp);
	}
	assert(modes&(1U<<BBR_DRAIN));
	assert(modes&(1U<<BBR_PROBE_BW));
	assert(cycles==15); /* UP, DOWN, CRUISE and REFILL, not a v1 alias. */
	bbr->probe_rtt_min_stamp=jiffies-bbr_probe_rtt_win_ms-1;
	struct rate_sample rs={.interval_us=10000,.rtt_us=15000,
		.delivered=10,.acked_sacked=10,.is_tx_in_flight_valid=true,
		.prior_delivered=tp.delivered};
	tp.delivered+=10; bbr_main(&tp.sk,&rs);
	assert(bbr->mode==BBR_PROBE_RTT);
	assert(tp.snd_cwnd<=bbr_probe_rtt_cwnd(&tp.sk));
	for (u32 i=0;i<30;i++) {
		rs.prior_delivered=tp.delivered;
		tp.delivered+=10; tp.tcp_mstamp+=10000; jiffies+=10;
		bbr_main(&tp.sk,&rs);
	}
	assert(bbr->mode==BBR_PROBE_BW && !warning_count);
}
static void bpf_members(void)
{
	struct tcp_congestion_ops in={0},out={0}; struct btf_type t={0};
	struct btf_member m={.type=1};
	const u32 extra[]={offsetof(struct tcp_congestion_ops,tso_segs),
		offsetof(struct tcp_congestion_ops,skb_marked_lost)};
	for (u32 i=0;i<ARRAY_SIZE(extra);i++) {
		m.offset=extra[i];
		/* A NULL native-only callback must not become compulsory. */
		assert(bpf_tcp_ca_init_member(&t,&m,&out,&in)==0);
		assert(bpf_tcp_ca_check_member(&t,&m)==-ENOTSUPP);
	}
	m.offset=offsetof(struct tcp_congestion_ops,tso_segs_goal);
	assert(bpf_tcp_ca_init_member(&t,&m,&out,&in)==0);
	assert(bpf_tcp_ca_check_member(&t,&m)==0);
	m.offset=offsetof(struct tcp_congestion_ops,ssthresh);
	assert(bpf_tcp_ca_init_member(&t,&m,&out,&in)==-EINVAL);
	m.offset=offsetof(struct tcp_congestion_ops,flags); m.type=0;
	in.flags=0x8000;
	assert(bpf_tcp_ca_init_member(&t,&m,&out,&in)==-EINVAL);
	in.flags=TCP_CONG_NON_RESTRICTED;
	assert(bpf_tcp_ca_init_member(&t,&m,&out,&in)==1 && out.flags==in.flags);
}
static void tso_dispatch(void)
{
	const u64 rates[]={0,1000,16000,1000000,50000000,1000000000};
	const u32 msss[]={48,256,536,1200,1448,9000};
	const u32 rtts[]={0,1,100,10000,200000,UINT32_MAX};
	const u32 sizes[]={2048,65536}, caps[]={1,16,64};
	struct tcp_sock tp; struct inet_connection_sock icsk;
	setup(&tp,&icsk); struct bbr *bbr=inet_csk_ca(&tp.sk);
	unsigned int cases=0;
	for (u32 i=0;i<ARRAY_SIZE(rates);i++)
	for (u32 j=0;j<ARRAY_SIZE(msss);j++)
	for (u32 k=0;k<ARRAY_SIZE(rtts);k++)
	for (u32 l=0;l<ARRAY_SIZE(sizes);l++)
	for (u32 n=0;n<ARRAY_SIZE(caps);n++) {
		u32 mss=msss[j], size=sizes[l];
		if (mss+MAX_TCP_HEADER>=size) continue;
		tp.sk.sk_pacing_rate=rates[i]; tp.sk.sk_gso_max_size=size;
		tp.sk.sk_gso_max_segs=caps[n]; bbr->min_rtt_us=rtts[k];
		u64 bytes=rates[i]>>tp.sk.sk_pacing_shift;
		u32 r=rtts[k]>>bbr_tso_rtt_shift;
		if (r<32) bytes+=(u32)65536>>r;
		bytes=min_t(u64,bytes,size-1-MAX_TCP_HEADER);
		u32 expected=max_t(u32,bytes/mss,sysctl_tcp_min_tso_segs);
		expected=min_t(u32,expected,caps[n]);
		assert(tcp_tso_segs(&tp.sk,mss)==expected);
		cases++;
	}
	assert(cases==1188 && !warning_count);
}
int main(void)
{
	assert(sizeof(((struct tcp_skb_cb *)0)->tx)==24);
	accounting(); segmentation(); algorithm(); tail_loss(); phases(); bpf_members(); tso_dispatch();
	puts("BBRv3 extracted-source models: PASS (10,000 wrap cases; 74,100 split/merge cases; 1,188 TSO cases; CC switches, loss bounds, phases, TLP, BPF and ABI)");
	return 0;
}
