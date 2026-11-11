#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted-source host models; not a running TCP stack or phone benchmark."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
MUTANTS = ['byte-as-packets', 'no-wrap', 'no-loss-snapshot', 'no-loss-hook',
           'no-split', 'no-merge', 'no-switch-guard', 'no-loss-tag-guard',
           'no-ce-snapshot', 'required-native-hooks', 'bpf-native-exposure', 'cached-mss', 'no-legacy-refresh', 'no-edt-forecast', 'edt-without-fq']


def block(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    p.add_argument('--sanitize', action='store_true')
    p.add_argument('--mutant', choices=MUTANTS)
    p.add_argument('--self-test-negatives', action='store_true')
    args = p.parse_args()
    h = (ROOT / 'include/net/tcp.h').read_text()
    inp = (ROOT / 'net/ipv4/tcp_input.c').read_text()
    out = (ROOT / 'net/ipv4/tcp_output.c').read_text()
    bbr = (ROOT / 'net/ipv4/tcp_bbr3.c').read_text()
    rate = (ROOT / 'net/ipv4/tcp_rate.c').read_text()
    # Extract the actual outgoing metadata definition, not a parallel layout.
    a = h.index('\t\tstruct {\n\t\t\t/* There is space for up to 24 bytes */')
    b = h.index(' tx;', a)
    tx = h[a:b] + ' tx;'
    skb = 'struct tcp_skb_cb { u32 seq, end_seq; u8 sacked;\n' + tx + '\n};'
    definitions = '\n'.join([skb, block(h, 'struct rate_sample {') + ';',
                              block(h, 'enum tcp_ca_event {') + ';',
                              block(h, 'struct tcp_congestion_ops {') + ';'])
    split = block(out, '\t\tif (TCP_SKB_CB(skb)->tx.in_flight_is_packets) {')
    start = inp.index('\tif (TCP_SKB_CB(skb)->tx.in_flight_is_packets)')
    end = inp.index('\n\t/* When we\'re adding', start)
    merge = inp[start:end]
    loss = block(inp, 'static void tcp_sum_lost(')
    helpers = '\n'.join(block(h, x) for x in [
        'static inline u32 tcp_stamp32_us_delta(',
        'static inline bool tcp_skb_tx_in_flight_is_suspicious(',
        'static inline bool tcp_edt_enabled('])
    rate = re.sub(r'^#include.*\n', '', rate, flags=re.M)
    bbr = re.sub(r'^#include.*\n', '', bbr, flags=re.M)
    if args.mutant == 'byte-as-packets':
        rate = rate.replace('rs->is_tx_in_flight_valid = scb->tx.in_flight_is_packets;',
                            'rs->is_tx_in_flight_valid = true;')
    elif args.mutant == 'no-wrap':
        rate = rate.replace('tcp_stamp32_us_delta(', 'tcp_stamp_us_delta(')
    elif args.mutant == 'no-loss-snapshot':
        rate = rate.replace('TCP_SKB_CB(skb)->tx.lost\t\t= tp->lost;',
                            'TCP_SKB_CB(skb)->tx.lost = 0;')
    elif args.mutant == 'no-loss-hook':
        loss = loss.replace('ca->skb_marked_lost(sk, skb);', '(void)sk;')
    elif args.mutant == 'no-split':
        split = ''
    elif args.mutant == 'no-merge':
        merge = ''
    elif args.mutant == 'no-switch-guard':
        bbr = bbr.replace('!rs->is_tx_in_flight_valid', 'false')
    elif args.mutant == 'no-loss-tag-guard':
        bbr = bbr.replace(' ||\n\t\t     !scb->tx.in_flight_is_packets', '')
    elif args.mutant == 'no-ce-snapshot':
        rate = rate.replace('TCP_SKB_CB(skb)->tx.delivered_ce\t= tp->delivered_ce;',
                            'TCP_SKB_CB(skb)->tx.delivered_ce = 0;')
    elif args.mutant == 'no-edt-forecast':
        bbr = bbr.replace('delivered = (u64)bbr_bw(sk) * interval_us >> BW_SCALE;', 'delivered = 0;')
    elif args.mutant == 'edt-without-fq':
        bbr = bbr.replace('if (!tcp_edt_enabled(sk))', 'if (false)')
    elif args.mutant == 'no-legacy-refresh':
        rate = rate.replace('TCP_SKB_CB(skb)->tx.in_flight = TCP_SKB_CB(skb)->end_seq -\n\t\t\t\t\t     tp->snd_una;',
                            'TCP_SKB_CB(skb)->tx.in_flight = 16;')
    # Keep ABI definitions exactly as the kernel UAPI supplies them.
    diag = (ROOT / 'include/uapi/linux/inet_diag.h').read_text()
    a = diag.index('struct tcp_bbr_info {')
    diag = diag[a:diag.index('#endif', a)]
    diag = diag.replace('union tcp_cc_info {',
                        'struct tcpvegas_info { u32 unused; };\n'
                        'struct tcp_dctcp_info { u32 unused; };\n'
                        'union tcp_cc_info {')
    code = Path(__file__).with_name('model.c').read_text()
    code = code.replace('/* DEFINITIONS */', definitions)
    code = code.replace('/* DIAG */', diag)
    code = code.replace('/* HELPERS */', helpers)
    code = code.replace('/* SPLIT */', split)
    code = code.replace('/* MERGE */', merge)
    code = code.replace('/* LOSS */', loss)
    a = inp.index('#define FLAG_DATA\t')
    flags = inp[a:inp.index('#define TCP_REMNANT', a)]
    code = code.replace('/* ACK FLAGS */', flags)
    code = code.replace('/* TLP */', block(inp, 'static void tcp_process_tlp_ack('))
    code = code.replace('/* RATE */', rate)
    code = code.replace('/* BBR3 */', bbr)
    tso = block(out, 'u32 tcp_tso_autosize(') + '\n' + block(out, 'static u32 tcp_tso_segs(')
    if args.mutant == 'cached-mss':
        tso = tso.replace('ca_ops->tso_segs(sk, mss_now)',
                          'ca_ops->tso_segs(sk, tcp_sk(sk)->mss_cache)')
    code = code.replace('/* TSO */', tso)
    bpf = (ROOT / 'net/ipv4/bpf_tcp_ca.c').read_text()
    if args.mutant == 'required-native-hooks':
        bpf = bpf.replace('\toffsetof(struct tcp_congestion_ops, tso_segs),\n', '')
    elif args.mutant == 'bpf-native-exposure':
        bpf = bpf.replace('return -ENOTSUPP;', 'return 0;')
    tables = '\n'.join(block(bpf, x) + ';' for x in [
        'static u32 optional_ops[]', 'static u32 unsupported_ops[]'])
    funcs = '\n'.join(block(bpf, x) for x in [
        'static bool is_optional(', 'static bool is_unsupported(',
        'static int bpf_tcp_ca_init_member(',
        'static int bpf_tcp_ca_check_member('])
    code = code.replace('/* BPF TABLES */', tables)
    code = code.replace('/* BPF MEMBERS */', funcs)
    with tempfile.TemporaryDirectory(prefix='bbr3-test-') as tmp:
        src, exe = Path(tmp) / 'test.c', Path(tmp) / 'test'
        src.write_text(code)
        flags = ['-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                 '-Wno-unused-parameter', '-Wno-unused-function',
                 '-Wno-unused-const-variable', '-Wno-sign-compare',
                 '-Wno-missing-field-initializers']
        if args.sanitize:
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        subprocess.run(shlex.split(args.cc) + flags + [str(src), '-o', str(exe)],
                       check=True)
        subprocess.run([str(exe)], check=True)
    assert '.name\t\t= "bbr3"' in bbr
    assert '#define BBR_VERSION\t\t3' in bbr
    assert 'return false;' in block(bbr, 'static bool bbr_can_use_ecn(')
    cfg = (ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    for line in ['CONFIG_TCP_CONG_BBR3=y', 'CONFIG_TCP_CONG_BBRPLUS=y',
                 'CONFIG_TCP_CONG_BBR=y', 'CONFIG_TCP_CONG_CUBIC=y',
                 'CONFIG_DEFAULT_BBR3=y', 'CONFIG_DEFAULT_TCP_CONG="bbr3"']:
        assert line in cfg.splitlines(), line
    assert 'scb->tx.in_flight_is_packets ? 0 :' in inp
    assert 'tlp_orig_data_app_limited = TCP_SKB_CB(skb)->tx.is_app_limited' in out
    assert 'tcp_ca_event(sk, CA_EVENT_TLP_RECOVERY);' in inp
    assert 'rs->is_acking_tlp_retrans_seq = true;' in inp
    timer = (ROOT / 'net/ipv4/tcp_timer.c').read_text()
    for text in [inp, timer]:
        assert 'icsk->icsk_ca_ops->flags & TCP_CONG_RATE_IN_FLIGHT)\n\t\ttcp_rate_check_app_limited(sk);' in text
    print('BBRv3 source/config/ABI guards: PASS', flush=True)
    if args.self_test_negatives:
        assert not args.mutant
        for mutant in MUTANTS:
            cmd = [sys.executable, str(Path(__file__)), '--cc', args.cc,
                   '--mutant', mutant]
            if args.sanitize:
                cmd.append('--sanitize')
            r = subprocess.run(cmd, capture_output=True, text=True)
            # A compiler failure is NOT evidence of a detected logic defect.
            assert r.returncode and 'Assertion' in r.stderr and 'error:' not in r.stderr, (mutant, r.stdout, r.stderr)
            print('PASS: runtime assertion rejected ' + mutant, flush=True)


if __name__ == '__main__':
    main()
