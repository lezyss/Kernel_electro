#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extract actual native EDT/FQ functions; host mocks, not hardware proof."""
import argparse
from pathlib import Path
import re
import resource
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def block(s, signature):
    a = s.index(signature)
    e = s.index('{', a) + 1
    depth = 1
    while depth:
        depth += (s[e] == '{') - (s[e] == '}')
        e += 1
    return s[a:e]


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--self-test-negatives', action='store_true')
args = p.parse_args()
h = (ROOT / 'include/net/tcp.h').read_text()
out = (ROOT / 'net/ipv4/tcp_output.c').read_text()
fq = (ROOT / 'net/sched/sch_fq.c').read_text()
model = Path(__file__).with_name('edt_model.c').read_text()
model = model.replace('/* TCP */', '\n'.join([
    block(h, 'static inline bool tcp_edt_enabled('),
    block(out, 'void tcp_mstamp_refresh('),
    block(out, 'static u64 tcp_edt_prepare('),
    block(out, 'static void tcp_edt_advance(')]))
model = model.replace('/* STRUCTS */', '\n'.join(block(fq, x) + ';' for x in [
    'struct fq_flow {', 'struct fq_flow_head {', 'struct fq_sched_data {']))
functions = '\n'.join(block(fq, x) for x in [
    'static void fq_flow_set_detached(', 'static bool fq_flow_is_detached(',
    'static bool fq_flow_is_throttled(', 'static void fq_flow_add_tail(',
    'static void fq_flow_unset_throttled(', 'static void fq_flow_set_throttled(',
    'static struct sk_buff *fq_dequeue_head(', 'static void flow_queue_add(',
    'static void fq_check_throttled(', 'static struct sk_buff *fq_dequeue('])
model = model.replace('/* FQ */', 'static struct fq_flow detached, throttled;\n' + functions)
rearm = fq[fq.index('\tif (fq_flow_is_throttled(f) &&', fq.index('static int fq_enqueue')):fq.index('\n\n\tif (unlikely(f == &q->internal))', fq.index('static int fq_enqueue'))]
model = model.replace('/* ENQUEUE REARM */', rearm.replace('q, f', '&s->data, f'))
mutants = {
    'no-deadline': model.replace('deadline = max(deadline, skb->tcp_edt_ns);', 'deadline = deadline;'),
    'double-socket-rate': model.replace('if (!skb->tcp_edt_ns && skb->sk)', 'if (skb->sk)'),
    'no-maxrate': model.replace('rate = q->flow_max_rate;', 'rate = ~0U;'),
    'ack-erases-frontier': model.replace('if ((!payload_len &&', 'if (!payload_len) tp->tcp_wstamp_ns = tp->tcp_clock_cache;\n\tif ((!payload_len &&'),
    'clock-domain': model.replace('tp->tcp_clock_cache = ktime_get_ns();', 'tp->tcp_clock_cache = tcp_clock_ns();'),
    'no-sort': model.replace('skb->tcp_edt_ns >= flow->tail->tcp_edt_ns', '1'),
    'no-rearm': model.replace(rearm.replace('q, f', '&s->data, f'), ''),
    'internal-bypass': model.replace('!q->rate_enable || !skb->tcp_edt_ns ||', '1 || !q->rate_enable || !skb->tcp_edt_ns ||'),
}
with tempfile.TemporaryDirectory(prefix='edt-host-') as td:
    t = Path(td)
    for name, code in [('native', model)] + (list(mutants.items()) if args.self_test_negatives else []):
        src, exe = t / (name + '.c'), t / name
        src.write_text(code)
        subprocess.run(['gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-unused-variable',
                        '-Wno-sign-compare', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        '-I' + str(ROOT / 'tools/include'), str(src), str(ROOT / 'tools/lib/rbtree.c'),
                        '-o', str(exe)], check=True)
        r = subprocess.run([str(exe)], capture_output=True, text=True)
        if name == 'native':
            assert r.returncode == 0, r.stderr
            print(r.stdout.strip())
        else:
            assert r.returncode != 0 and 'Assertion' in r.stderr, (name, r.stderr)
            print('PASS: compiled semantic mutant rejected:', name)

# Cross-layer wiring guards complement (not replace) actual driver execution.
assert 'skb->tcp_edt_ns = edt;' in out
assert out.index('skb->tcp_edt_ns = edt;') < out.index('err = icsk->icsk_af_ops->queue_xmit')
assert 'if (!err)\n\t\ttcp_edt_advance(sk, edt, edt_len, edt_rate);' in out
assert 'new->tcp_edt_ns\t\t= old->tcp_edt_ns;' in (ROOT / 'net/core/skbuff.c').read_text()
for path in ['net/ipv4/ip_output.c', 'net/ipv6/ip6_output.c']:
    assert 'to->tcp_edt_ns = from->tcp_edt_ns;' in (ROOT / path).read_text()
assert 'skb->tcp_edt_ns = 0;' in block((ROOT / 'net/core/dev.c').read_text(), 'static int __netif_receive_skb_core(')
assert 'if (xnet)\n\t\tskb->tcp_edt_ns = 0;' in (ROOT / 'net/core/skbuff.c').read_text()
assert 'TCP_CONG_EDT' not in re.search(r'#define TCP_CONG_MASK.*(?:\\\n.*)*', h)[0]
assert 'TCP_CONG_EDT' not in (ROOT / 'net/ipv4/tcp_bbrplus.c').read_text()
print('PASS: send/clone/GSO-header/IPv4+IPv6-fragment/RX/scrub/BPF/legacy opt-in wiring')
