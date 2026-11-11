/* SPDX-License-Identifier: GPL-2.0 */
/* Actual TCP/FQ bodies are inserted by test_edt.py. Kernel primitives mocked. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <linux/types.h>
#include <linux/rbtree.h>
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define max_t(t,a,b) ((t)(a)>(t)(b)?(t)(a):(t)(b))
#ifndef min
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#endif
#define smp_load_acquire(p) (*(p))
#define NSEC_PER_SEC 1000000000ULL
#define NSEC_PER_USEC 1000ULL
#define SK_PACING_NEEDED 1
#define SK_PACING_FQ 2
#define TCP_CONG_EDT 8
#define TCPHDR_SYN 2
#define TCPHDR_FIN 1
#define TCPHDR_RST 4
#define div_u64(a,b) ((u64)(a)/(b))
#define do_div(a,b) ((a)/=(b))
static u64 mono, local_ns;
static u64 ktime_get_ns(void){return mono;}
static u64 tcp_clock_ns(void){return local_ns;}
struct tcp_congestion_ops {u32 flags;};
struct inet_connection_sock {struct tcp_congestion_ops *icsk_ca_ops;};
struct tcp_sock {u64 tcp_clock_cache,tcp_wstamp_ns,tcp_mstamp;};
struct sock {u32 sk_pacing_rate,sk_pacing_status;struct tcp_sock tp;struct inet_connection_sock icsk;};
#define inet_csk(sk) (&(sk)->icsk)
#define tcp_sk(sk) (&(sk)->tp)
struct tcp_skb_cb {u8 tcp_flags;};
struct sk_buff {struct sk_buff *next;struct sock *sk;u64 tcp_edt_ns;unsigned len,end;int ack,id;struct tcp_skb_cb cb;};
#define TCP_SKB_CB(skb) (&(skb)->cb)
/* TCP */
struct qdisc_watchdog {u64 next;};
/* STRUCTS */
struct Qdisc {struct fq_sched_data data;struct {unsigned qlen;} q;u64 backlog,bytes;};
#define qdisc_priv(s) (&(s)->data)
static unsigned long jiffies;
static void qdisc_qstats_backlog_dec(struct Qdisc *s,struct sk_buff *p){s->backlog-=p->len;}
static void qdisc_bstats_update(struct Qdisc *s,struct sk_buff *p){s->bytes+=p->len;}
static unsigned qdisc_pkt_len(struct sk_buff *p){return p->len;}
static bool skb_is_tcp_pure_ack(struct sk_buff *p){return p->ack;}
static void qdisc_watchdog_schedule_ns(struct qdisc_watchdog *w,u64 t){w->next=t;}
#define prefetch(p) ((void)0)
/* FQ */
static void init(struct Qdisc *s){memset(s,0,sizeof(*s));s->data.quantum=1500;s->data.rate_enable=1;s->data.flow_max_rate=~0U;s->data.low_rate_threshold=550000;s->data.time_next_delayed_flow=~0ULL;}
static void enqueue(struct Qdisc *s,struct fq_flow *f,struct sk_buff *p){
 bool empty=!f->head;flow_queue_add(f,p);f->qlen++;s->q.qlen++;s->backlog+=p->len;
 if(f==&s->data.internal)return;
 if(empty&&f->next!=&throttled){f->credit=15000;fq_flow_add_tail(&s->data.new_flows,f);}
 /* ENQUEUE REARM */
}
int main(void){struct tcp_congestion_ops ca={TCP_CONG_EDT};struct sock sk={.sk_pacing_rate=1000000,.sk_pacing_status=SK_PACING_FQ,.icsk={&ca}};struct sk_buff p={.len=1000};u64 edt;
 mono=1000000000;local_ns=900000000000ULL;tcp_mstamp_refresh(&sk.tp);assert(sk.tp.tcp_clock_cache==mono&&sk.tp.tcp_mstamp==local_ns/1000);
 edt=tcp_edt_prepare(&sk,&p,1000);assert(edt==mono);tcp_edt_advance(&sk,edt,1000,sk.sk_pacing_rate);assert(sk.tp.tcp_wstamp_ns==mono+1000000);
 assert(!tcp_edt_prepare(&sk,&p,0));assert(sk.tp.tcp_wstamp_ns==mono+1000000); /* ACK cannot erase a pending frontier. */
 for(unsigned flag=2;flag<=4;flag<<=1){p.cb.tcp_flags=flag;assert(!tcp_edt_prepare(&sk,&p,1000));assert(sk.tp.tcp_wstamp_ns==mono+1000000);}p.cb.tcp_flags=TCPHDR_FIN;assert(tcp_edt_prepare(&sk,&p,0)==sk.tp.tcp_wstamp_ns);p.cb.tcp_flags=0;
 assert(tcp_edt_prepare(&sk,&p,1000)==mono+1000000); /* no commit = failed-send simulation */
 assert(sk.tp.tcp_wstamp_ns==mono+1000000);
 tcp_edt_advance(&sk,mono,UINT_MAX,1);assert(sk.tp.tcp_wstamp_ns==mono+NSEC_PER_SEC);
 sk.sk_pacing_status=SK_PACING_NEEDED;assert(tcp_edt_prepare(&sk,&p,1000));assert(!tcp_edt_enabled(&sk));
 sk.sk_pacing_status=0;assert(!tcp_edt_prepare(&sk,&p,1000));assert(sk.tp.tcp_wstamp_ns==mono);
 sk.sk_pacing_status=SK_PACING_FQ;ca.flags=0;assert(!tcp_edt_prepare(&sk,&p,1000));ca.flags=TCP_CONG_EDT;
 sk.sk_pacing_rate=0;assert(!tcp_edt_prepare(&sk,&p,1000));sk.sk_pacing_rate=~0U;assert(!tcp_edt_prepare(&sk,&p,1000));sk.sk_pacing_rate=1000;
 {struct Qdisc s;struct fq_flow f={0};struct sk_buff a={.tcp_edt_ns=mono+1000000,.len=1000,.id=1,.sk=&sk},b={.tcp_edt_ns=mono+2000000,.len=1000,.id=2,.sk=&sk},ack={.len=40,.ack=1};init(&s);enqueue(&s,&f,&a);enqueue(&s,&f,&b);assert(!fq_dequeue(&s));assert(s.data.watchdog.next==a.tcp_edt_ns);assert(f.time_next_packet==0);enqueue(&s,&f,&ack);assert(fq_dequeue(&s)==&ack);assert(!fq_dequeue(&s));mono=a.tcp_edt_ns;assert(fq_dequeue(&s)==&a);assert(f.time_next_packet==0);assert(!fq_dequeue(&s));mono=b.tcp_edt_ns;assert(fq_dequeue(&s)==&b);assert(!s.q.qlen&&!s.backlog);}
 /* Earlier data arrival must replace an EDT throttle without stale old-head delay. */
 {struct Qdisc s;struct fq_flow f={0};struct sk_buff later={.tcp_edt_ns=mono+3000,.len=1000},early={.tcp_edt_ns=mono+1000,.len=1000};init(&s);enqueue(&s,&f,&later);assert(!fq_dequeue(&s));enqueue(&s,&f,&early);assert(!fq_dequeue(&s));assert(s.data.watchdog.next==early.tcp_edt_ns);mono=early.tcp_edt_ns;assert(fq_dequeue(&s)==&early);}
 /* Allocation-failure/internal queue must still honor deadlines and arm a watchdog. */
 {struct Qdisc s;struct sk_buff a={.tcp_edt_ns=mono+1000,.len=1000};init(&s);enqueue(&s,&s.data.internal,&a);assert(!fq_dequeue(&s));assert(s.data.watchdog.next==a.tcp_edt_ns);mono=a.tcp_edt_ns;assert(fq_dequeue(&s)==&a);}
 /* Explicit fq maxrate is independent of TCP EDT, and must not be skipped. */
 {struct Qdisc s;struct fq_flow f={0};struct sk_buff a={.tcp_edt_ns=mono,.len=1000,.sk=&sk},b={.tcp_edt_ns=mono+1,.len=1000,.sk=&sk};init(&s);s.data.flow_max_rate=1000;enqueue(&s,&f,&a);enqueue(&s,&f,&b);assert(fq_dequeue(&s)==&a);assert(f.time_next_packet==mono+NSEC_PER_SEC);assert(!fq_dequeue(&s));assert(s.data.watchdog.next==f.time_next_packet);mono=f.time_next_packet;assert(fq_dequeue(&s)==&b);}
 /* No EDT = original socket-rate pacing, while nopacing ignores EDT. */
 {struct Qdisc s;struct fq_flow f={0};struct sk_buff a={.len=1000,.sk=&sk},b={.len=1000,.sk=&sk};init(&s);sk.sk_pacing_rate=1000;enqueue(&s,&f,&a);enqueue(&s,&f,&b);assert(fq_dequeue(&s)==&a);assert(f.time_next_packet==mono+NSEC_PER_SEC);assert(!fq_dequeue(&s));}
 {struct Qdisc s;struct fq_flow f={0};struct sk_buff a={.tcp_edt_ns=mono+99999,.len=1000};init(&s);s.data.rate_enable=0;enqueue(&s,&f,&a);assert(fq_dequeue(&s)==&a);}
 /* Live switch to an untagged CC must not reorder data before prior EDT. */
 {struct Qdisc s;struct fq_flow f={0};struct sk_buff a={.tcp_edt_ns=mono+1000,.len=1000},b={.len=1000};init(&s);enqueue(&s,&f,&a);enqueue(&s,&f,&b);assert(f.head==&a&&f.tail==&b);}
 /* Stable sorted insertion and exact accounting, including 0/immediate metadata. */
 for(unsigned pass=0;pass<100;pass++){struct Qdisc s;struct fq_flow f={0};struct sk_buff packets[64];u64 previous=0;init(&s);for(unsigned i=0;i<64;i++){packets[i]=(struct sk_buff){.len=10,.tcp_edt_ns=(i*31+pass*13)%67,.ack=((i*31+pass*13)%67)==0};enqueue(&s,&f,&packets[i]);}for(unsigned i=0;i<64;i++){struct sk_buff *x=fq_dequeue_head(&s,&f);assert(x&&x->tcp_edt_ns>=previous);previous=x->tcp_edt_ns;}assert(!s.q.qlen&&!s.backlog&&!f.qlen);}
 puts("EDT actual TCP/FQ bodies: clocks, commit/failure, controls, ordering, rearm, maxrate, allocation fallback, legacy/nopacing; 6400 sorted packets PASS");return 0;}
