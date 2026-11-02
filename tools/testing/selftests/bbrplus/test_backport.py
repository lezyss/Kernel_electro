#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted-source BBRplus/TSO models, not a running TCP-stack test."""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


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
    p.add_argument('--donor-hook', action='store_true',
                   help='disable callback dispatch; the C test must fail')
    p.add_argument('--old-memory-limits', action='store_true',
                   help='restore the old 4/6 MiB caps; the C test must fail')
    args = p.parse_args()
    bbr = (ROOT / 'net/ipv4/tcp_bbrplus.c').read_text()
    output = (ROOT / 'net/ipv4/tcp_output.c').read_text()
    definitions = []
    for name in ['BW_SCALE', 'BW_UNIT', 'BBR_SCALE', 'BBR_UNIT', 'CYCLE_LEN']:
        definitions.append(re.search(r'^#define ' + name + r'\s+[^\n]+',
                                     bbr, re.M).group())
    definitions += [block(bbr, 'enum bbr_mode {') + ';',
                    block(bbr, 'enum bbr_pacing_gain_phase {') + ';',
                    block(bbr, 'struct bbr {') + ';',
                    block(bbr, 'static const int bbr_pacing_gain[]') + ';']
    for name in ['bbr_min_tso_rate', 'bbr_cycle_rand',
                 'bbr_extra_acked_gain', 'bbr_extra_acked_win_rtts',
                 'bbr_ack_epoch_acked_reset_thresh']:
        definitions.append(re.search(r'static const \w+ ' + name + r'\s*=.*?;',
                                     bbr, re.S).group())
    functions = [block(output, 'u32 tcp_tso_autosize('),
                 block(output, 'static u32 tcp_tso_segs(')]
    for sig in ['static bool tcp_snd_wnd_test(', 'static u32 bbr_max_bw(',
                'static u32 bbr_bw(', 'static void bbr_set_cycle_idx(',
                'static u32 bbr_tso_segs_goal(', 'static void bbr_set_tso_segs_goal(',
                'static u32 bbr_bdp(', 'static u32 bbr_quantization_budget(',
                'static u32 bbr_inflight(',
                'static void bbr_drain_to_target_cycling(',
                'static void bbr_update_ack_aggregation(']:
        # Skip forward declarations for the two private helpers.
        text = re.sub(r'static u32 bbr_(?:max_bw|inflight)\([^;{]+;', '', bbr)
        functions.append(block(text, sig))
    code = Path(__file__).with_name('model.c').read_text()
    code = code.replace('/* DEFINITIONS */', '\n\n'.join(definitions))
    tcp = (ROOT / 'net/ipv4/tcp.c').read_text()
    start = tcp.index('\tlimit = nr_free_buffer_pages() << (PAGE_SHIFT - 7);')
    end = tcp.index('\n\tpr_info(', start)
    functions.append('static void init_memory_limits(unsigned long free_pages)\n{\n'
                     'unsigned long limit, max_wshare, max_rshare;\n'
                     + tcp[start:end] + '\n}')
    code = code.replace('/* FUNCTIONS */', '\n\n'.join(functions))
    if args.old_memory_limits:
        old = 'min(16UL*1024*1024, limit)'
        assert code.count(old) == 2
        code = code.replace(old, 'min(4UL*1024*1024, limit)', 1)
        code = code.replace(old, 'min(6UL*1024*1024, limit)', 1)
    if args.donor_hook:
        old = 'tso_segs = ca_ops->tso_segs_goal ? ca_ops->tso_segs_goal(sk) : 0;'
        assert old in code
        code = code.replace(old, 'tso_segs = 0;')
    with tempfile.TemporaryDirectory(prefix='bbrplus-test-') as tmp:
        src, exe = Path(tmp) / 'test.c', Path(tmp) / 'test'
        src.write_text(code)
        subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2', '-Wall',
                       '-Wextra', '-Werror', '-Wno-unused-parameter',
                       '-Wno-sign-compare', str(src), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    assert 'EXPORT_SYMBOL_GPL(tcp_tso_autosize);' in output
    assert '.tso_segs_goal  = bbr_tso_segs_goal,' in bbr
    assert 'BUILD_BUG_ON(sizeof(struct bbr) > ICSK_CA_PRIV_SIZE);' in bbr
    assert 'static u32 bbr_max_bw' in bbr and 'static u32 bbr_inflight' in bbr
    kconfig = (ROOT / 'net/ipv4/Kconfig').read_text()
    assert 'default DEFAULT_CUBIC' in kconfig
    assert re.search(r'default "bbrplus" if DEFAULT_BBRPLUS\n\tdefault "cubic"', kconfig)
    config = (ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    assert 'CONFIG_TCP_CONG_BBRPLUS=y' in config
    assert 'CONFIG_DEFAULT_BBRPLUS=y' in config
    assert 'CONFIG_DEFAULT_TCP_CONG="bbrplus"' in config
    assert 'CONFIG_DEFAULT_FQ_CODEL=y' in config
    print('BBRplus source/config guards: PASS')


if __name__ == '__main__':
    main()
