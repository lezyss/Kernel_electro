/* SPDX-License-Identifier: GPL-2.0 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/mman.h>
#include <unistd.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint16_t __le16;
typedef int bdaddr_t;
#define __packed __attribute__((packed))
#define cpu_to_le16(x) (x) /* Host checks run on little-endian hosts. */
#define BT_LISTEN 1
#define BT_CONFIG 2
#define BT_CONNECT 3
#define BT_OPEN 4
#define BTPROTO_RFCOMM 3
#define GFP_ATOMIC 0
#define BT_SK_DEFER_SETUP 0
#define BDADDR_ANY (&(bdaddr_t){0})
static void debug(const char *fmt, ...) { (void)fmt; }
#define BT_DBG(...) debug(__VA_ARGS__)
#define BT_ERR(...) debug(__VA_ARGS__)
/* DEFINITIONS */
struct rfcomm_session { long state; int initiator; unsigned long flags; };
struct rfcomm_dlc {
	int state, dlci, addr, cfc, remote_v24_sig, mscex;
	unsigned long flags;
	void (*modem_status)(struct rfcomm_dlc *, u8);
};
struct sock {
	struct sock *next;
	int sk_state, sk_ack_backlog, refs, locked, notifications;
	u8 channel;
	bdaddr_t src, dst;
	unsigned long flags;
	struct rfcomm_dlc *dlc;
	void (*sk_state_change)(struct sock *);
};
static struct { int lock; struct sock *head; } rfcomm_sk_list;
static int list_locked, close_on_unlock, alloc_fail, full, enqueues, sends;
static struct sock *race_parent;
static struct sock child;
static struct rfcomm_dlc child_dlc;
#define rfcomm_pi(sk) (sk)
#define bt_sk(sk) (sk)
#define sk_for_each(sk, head) for ((sk) = *(head); (sk); (sk) = (sk)->next)
static void read_lock(int *lock) { assert(!list_locked); list_locked = 1; }
static void sock_hold(struct sock *s) { assert(list_locked && s->refs > 0); s->refs++; }
static void sock_put(struct sock *s) { assert(s->refs > 0); s->refs--; }
static void read_unlock(int *lock)
{
	list_locked = 0;
	if (close_on_unlock) {
		race_parent->sk_state = 0;
		sock_put(race_parent); /* Drop close's original reference. */
	}
}
static int bacmp(bdaddr_t *a, bdaddr_t *b) { return *a != *b; }
static void bacpy(bdaddr_t *a, bdaddr_t *b) { *a = *b; }
static void bh_lock_sock(struct sock *s) { assert(s->refs > 0); s->locked = 1; }
static void bh_unlock_sock(struct sock *s) { assert(s->locked); s->locked = 0; }
static int test_bit(int bit, unsigned long *flags) { return !!(*flags & (1UL << bit)); }
static void set_bit(int bit, unsigned long *flags) { *flags |= 1UL << bit; }
static void clear_bit(int bit, unsigned long *flags) { *flags &= ~(1UL << bit); }
static int sk_acceptq_is_full(struct sock *s) { return full; }
#define sock_net(sk) 0
static struct sock *rfcomm_sock_alloc(int net, void *sock, int proto, int gfp, int kern)
{
	if (alloc_fail) return NULL;
	memset(&child, 0, sizeof(child));
	child.dlc = &child_dlc;
	return &child;
}
static void bt_sock_reclassify_lock(struct sock *s, int proto) { }
static void rfcomm_sock_init(struct sock *s, struct sock *parent) { }
static void bt_accept_enqueue(struct sock *p, struct sock *s, bool bh)
{
	assert(p->refs > 0 && p->locked && p->sk_state == BT_LISTEN);
	enqueues++;
}
static void notify(struct sock *s) { assert(s->refs > 0 && !s->locked); s->notifications++; }
static void rfcomm_session_getaddr(struct rfcomm_session *s, bdaddr_t *src, bdaddr_t *dst)
{ *src = 42; *dst = 43; }

/* Guard pages detect short reads; successful linearization moves the data,
 * and makes old storage inaccessible, catching cached pre-pull pointers.
 */
struct sk_buff { u8 *data; unsigned int len; void *mapping[8]; int maps; };
static size_t page;
static u8 *guarded(struct sk_buff *skb, unsigned int len)
{
	void *m = mmap(NULL, page * 2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	assert(m != MAP_FAILED && skb->maps < 8);
	assert(mprotect((char *)m + page, page, PROT_NONE) == 0);
	skb->mapping[skb->maps++] = m;
	return (u8 *)m + page - len;
}
static struct sk_buff packet(unsigned int len)
{
	struct sk_buff skb = { .len = len };
	skb.data = guarded(&skb, len);
	memset(skb.data, 0, len);
	return skb;
}
static bool pskb_may_pull(struct sk_buff *skb, unsigned int n)
{
	if (skb->len < n) return false;
	u8 *data = guarded(skb, skb->len);
	memcpy(data, skb->data, skb->len);
	assert(mprotect(skb->mapping[skb->maps - 2], page * 2, PROT_NONE) == 0);
	skb->data = data;
	return true;
}
static void skb_pull(struct sk_buff *skb, unsigned int n)
{ assert(skb->len >= n); skb->data += n; skb->len -= n; }
static void packet_free(struct sk_buff *skb)
{ for (int i = 0; i < skb->maps; i++) assert(!munmap(skb->mapping[i], page * 2)); }
static struct rfcomm_dlc *rfcomm_dlc_get(struct rfcomm_session *s, u8 dlci) { return NULL; }
static int rfcomm_apply_pn(struct rfcomm_dlc *d, int cr, struct rfcomm_pn *pn) { return 0; }
static void rfcomm_send_pn(struct rfcomm_session *s, int cr, struct rfcomm_dlc *d) { sends++; }
static void rfcomm_send_sabm(struct rfcomm_session *s, u8 dlci) { sends++; }
static void rfcomm_send_dm(struct rfcomm_session *s, u8 dlci) { sends++; }
static void rfcomm_dlc_link(struct rfcomm_session *s, struct rfcomm_dlc *d) { }
static void rfcomm_send_rls(struct rfcomm_session *s, int cr, u8 dlci, u8 status) { sends++; }
static void rfcomm_send_msc(struct rfcomm_session *s, int cr, u8 dlci, u8 sig) { sends++; }
static void rfcomm_dlc_lock(struct rfcomm_dlc *d) { }
static void rfcomm_dlc_unlock(struct rfcomm_dlc *d) { }
static void rfcomm_send_fcon(struct rfcomm_session *s, int cr) { sends++; }
static void rfcomm_send_fcoff(struct rfcomm_session *s, int cr) { sends++; }
static void rfcomm_send_test(struct rfcomm_session *s, int cr, u8 *data, unsigned int len) { sends++; }
static void rfcomm_send_nsc(struct rfcomm_session *s, int cr, u8 type) { sends++; }
static void rfcomm_send_rpn(struct rfcomm_session *s, int cr, u8 dlci,
		u8 rate, u8 data, u8 stop, u8 parity, u8 flow, u8 xon, u8 xoff, u16 mask)
{ sends++; }
/* FUNCTIONS */

static struct sock listener(int addr)
{
	return (struct sock){ .sk_state = BT_LISTEN, .refs = 1, .channel = 7,
		.src = addr, .flags = 1, .sk_state_change = notify };
}
static void test_listeners(void)
{
	struct sock a = listener(0), b = listener(0), c = listener(42);
	bdaddr_t addr = 42;
	a.next = &b; b.next = &c;
	rfcomm_sk_list.head = &a;
	struct sock *got = rfcomm_get_sock_by_channel(BT_LISTEN, 7, &addr);
	assert(got == &c && a.refs == 1 && b.refs == 1 && c.refs == 2);
	sock_put(got);
	b.next = NULL;
	got = rfcomm_get_sock_by_channel(BT_LISTEN, 7, &addr);
	assert(got == &b && a.refs == 1 && b.refs == 2);
	sock_put(got);
	assert(!rfcomm_get_sock_by_channel(BT_LISTEN, 8, &addr));
	a.src = 42; a.next = NULL;
	struct rfcomm_session session = {0};
	for (int mode = 0; mode < 4; mode++) {
		a = listener(42);
		alloc_fail = mode == 1; full = mode == 2;
		close_on_unlock = mode == 3; race_parent = &a;
		struct rfcomm_dlc *dlc = NULL;
		int before = enqueues;
		int result = rfcomm_connect_ind(&session, 7, &dlc);
		assert(result == (mode == 0));
		assert(enqueues == before + (mode == 0));
		assert(a.refs == (mode == 3 ? 0 : 1));
		assert(a.notifications == (mode == 3 ? 0 : 1));
		if (!mode) assert(dlc == &child_dlc);
	}
	close_on_unlock = alloc_fail = full = 0;
	rfcomm_sk_list.head = NULL;
}
static void test_packets(void)
{
	struct rfcomm_session session = {0};
	int (*handlers[])(struct rfcomm_session *, int, struct sk_buff *) = {
		rfcomm_recv_pn, rfcomm_recv_rls, rfcomm_recv_msc };
	unsigned int sizes[] = { sizeof(struct rfcomm_pn), sizeof(struct rfcomm_rls), sizeof(struct rfcomm_msc) };
	for (int h = 0; h < 3; h++) {
		for (unsigned int len = 0; len <= sizes[h]; len++) {
			for (int cr = 0; cr < 2; cr++) {
				struct sk_buff skb = packet(len);
				assert(handlers[h](&session, cr, &skb) == (len < sizes[h] ? -EILSEQ : 0));
				packet_free(&skb);
			}
		}
	}
	for (int declared = 0; declared <= 9; declared++) {
		for (unsigned int len = 0; len <= sizeof(struct rfcomm_rpn); len++) {
			for (int cr = 0; cr < 2; cr++) {
				struct sk_buff skb = packet(len);
				unsigned int need = declared == 1 ? 1 : sizeof(struct rfcomm_rpn);
				int before = sends;
				assert(rfcomm_recv_rpn(&session, cr, declared, &skb) == (len < need ? -EILSEQ : 0));
				assert(sends == before + (cr && len >= need));
				packet_free(&skb);
			}
		}
	}
	for (unsigned int len = 0; len < sizeof(struct rfcomm_mcc); len++) {
		struct sk_buff skb = packet(len);
		assert(rfcomm_recv_mcc(&session, &skb) == -EILSEQ);
		packet_free(&skb);
	}
	/* MCC dispatch of a legal single-byte RPN query (and truncated ones). */
	for (unsigned int body = 0; body <= 1; body++) {
		struct sk_buff skb = packet(2 + body);
		skb.data[0] = __mcc_type(1, RFCOMM_RPN);
		skb.data[1] = __len8(1);
		int before = sends;
		assert(rfcomm_recv_mcc(&session, &skb) == 0);
		assert(sends == before + (body == 1));
		packet_free(&skb);
	}
}
int main(void)
{
	page = (size_t)sysconf(_SC_PAGESIZE);
	test_listeners();
	test_packets();
	puts("PASS: listener reference/state/cleanup and MCC length/RPN checks (UBSan + guard pages)");
	return 0;
}
