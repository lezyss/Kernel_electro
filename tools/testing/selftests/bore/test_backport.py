#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Production-extracted BORE models; not running-kernel scheduler tests."""
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
    p.add_argument('--donor-idle', action='store_true', help='must fail a C assertion')
    p.add_argument('--legacy-nice', action='store_true', help='must fail a C assertion')
    args = p.parse_args()
    fair = (ROOT / 'kernel/sched/fair.c').read_text()
    core = (ROOT / 'kernel/sched/core.c').read_text()
    # Avoid interpreting the forward declaration as a function definition.
    fair = re.sub(r'static __always_inline void reweight_task\([^;{]+;', '', fair)
    definitions = [block(core, 'const int sched_prio_to_weight[40]') + ';',
                   block(core, 'const u32 sched_prio_to_wmult[40]') + ';']
    for name in ['sched_burst_smoothness_long', 'sched_burst_smoothness_short',
                 'sched_burst_fork_atavistic', 'sched_burst_penalty_offset',
                 'sched_burst_penalty_scale', 'sched_burst_cache_lifetime']:
        definitions.append(re.search(r'unsigned int __read_mostly ' + name +
                                     r' = [^;]+;', fair).group())
    funcs = [block(core, 'static void set_load_weight('),
             block(fair, 'static void reweight_entity('),
             block(fair, 'static __always_inline void reweight_task(')]
    for name in ['static inline u32 log2plus1_u64_u32f8(',
                 'static inline u32 calc_burst_penalty(',
                 'static void update_burst_score(',
                 'static void update_burst_penalty(',
                 'static inline u32 binary_smooth(', 'static void restart_burst(']:
        funcs.append(block(fair, name))
    for name in ['static void sched_fork_bore(', 'static u32 count_child_tasks(',
                 'static bool task_is_inheritable(',
                 'static bool child_burst_cache_expired(',
                 'static void __update_child_burst_cache(',
                 'static void update_child_burst_direct(',
                 'static void update_child_burst_topological(',
                 'static void sched_post_fork_bore(']:
        funcs.append(block(core, name))
    code = Path(__file__).with_name('model.c').read_text()
    code = code.replace('/* DEFINITIONS */', '\n\n'.join(definitions))
    code = code.replace('/* FUNCTIONS */', '\n\n'.join(funcs))
    if args.donor_idle:
        code = code.replace(' && !idle_policy(p->policy)', '')
    if args.legacy_nice:
        code = code.replace('prio = min(39, prio + p->se.burst_score);', '(void)p;')
    with tempfile.TemporaryDirectory(prefix='bore-test-') as tmp:
        src, exe = Path(tmp) / 'test.c', Path(tmp) / 'test'
        src.write_text(code)
        for group in (0, 1):
            cmd = shlex.split(args.cc) + ['-std=gnu11', '-O2', '-Wall', '-Wextra',
                '-Werror', '-Wno-unused-parameter', '-Wno-sign-compare',
                '-DCONFIG_SCHED_BORE=1', f'-DMODEL_GROUP={group}', str(src), '-o', str(exe)]
            subprocess.run(cmd, check=True)
            subprocess.run([str(exe)], check=True)
    fork = (ROOT / 'kernel/fork.c').read_text()
    pos = fork.index('sched_post_fork(p);')
    assert fork.rfind('write_lock_irq(&tasklist_lock);', 0, pos) > fork.rfind('write_unlock_irq(&tasklist_lock);', 0, pos)
    assert pos < fork.index('init_task_pid_links(p);') < fork.index('attach_pid(p, PIDTYPE_PID);')
    assert 'read_lock(&tasklist_lock)' not in block(core, 'static void sched_post_fork_bore(')
    assert 'extern unsigned int sched_burst_fork_atavistic;' in core
    assert 'curr->burst_time += min(delta_exec, U64_MAX - curr->burst_time);' in fair
    assert fair.index('curr->exec_start = now;') < fair.index('update_burst_penalty(curr);')
    assert 'if (flags & ENQUEUE_WAKEUP)' in fair
    assert 'lru_gen_use_mm(mm);' in core
    cfg = (ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    for opt in ['CONFIG_SCHED_BORE=y', 'CONFIG_SCHED_CASS=y', 'CONFIG_LRU_GEN_ENABLED=y', 'CONFIG_DEFAULT_BBRPLUS=y']:
        assert opt in cfg, opt
    print('BORE source integration guards: PASS')


if __name__ == '__main__':
    main()
