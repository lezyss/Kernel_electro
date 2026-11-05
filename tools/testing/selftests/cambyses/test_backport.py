#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted Cambyses/list code, not a running-kernel scheduler stress test."""
import argparse
import os
from pathlib import Path
import re
import resource
import shlex
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
NEGATIVES = ('single-node-rotation', 'no-concession', 'stale-cursor',
             'no-pre-detach-flush', 'no-sticky-progress', 'bypass-filters',
             'post-timeout-concession', 'lose-two-task-exception', 'overflow-concession',
             'no-timeout', 'no-lb-min', 'zero-load-cost')
SHIMS = {
    'types.h': '''#include <stdbool.h>
struct list_head { struct list_head *next, *prev; };
struct hlist_node { struct hlist_node *next, **pprev; };
struct hlist_head { struct hlist_node *first; };
''',
    'stddef.h': '#include <stddef.h>\n',
    'poison.h': '#define LIST_POISON1 ((void *)0x100)\n#define LIST_POISON2 ((void *)0x122)\n',
    'const.h': '',
    'kernel.h': '''#include <stddef.h>
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x) = (v))
#define container_of(p,t,m) ((t *)((char *)(p) - offsetof(t,m)))
''',
}


def block(text, start):
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def function(text, signature):
    return block(text, text.index(signature))


def source(root, negative=None):
    fair = (root / 'kernel/sched/fair.c').read_text()
    features = (root / 'kernel/sched/features.h').read_text()
    header = (root / 'include/linux/list.h').read_text()
    for name in ('LB_ROTATE_BLOCK', 'LB_STRICT_BUDGET'):
        assert 'SCHED_FEAT(' + name + ', true)' in features
    detach = function(fair, 'static int detach_tasks(')
    definitions = block(fair, fair.index('struct lb_concession {')) + ';'
    helper = function(fair, 'static bool lb_cost_fits(')
    funcs = definitions + '\n' + helper + '\n' + detach
    flags = '\n'.join(re.findall(r'^#define LBF_.*$', fair, re.M))
    flags += '\nstatic const unsigned int sched_nr_migrate_break = 32;\n'
    model = (HERE / 'model.c').read_text()
    if negative == 'single-node-rotation':
        assert header.count('list_move_tail(head, list);') == 1
        header = header.replace('list_move_tail(head, list);', 'list_move(list, head);')
    elif negative == 'no-concession':
        funcs = funcs.replace('if (strict && concession.p', 'if (false && strict && concession.p')
    elif negative == 'stale-cursor':
        funcs = funcs.replace('cursor = NULL;', '/* retain stale cursor */')
        # Keep initial cursor assignment, remove only the refresh after detach.
        funcs = funcs.replace('list_add(&p->se.group_node, &env->tasks);\n\t\tcursor = tasks->prev;',
                              'list_add(&p->se.group_node, &env->tasks);')
    elif negative == 'no-pre-detach-flush':
        funcs = funcs.replace('if (rotate && p->se.group_node.next != tasks)',
                              'if (false && rotate && p->se.group_node.next != tasks)')
    elif negative == 'no-sticky-progress':
        funcs = funcs.replace('env->flags |= LBF_MOVED;', '/* progress bit missing */')
    elif negative == 'bypass-filters':
        funcs = funcs.replace('if (!can_migrate_task(p, env))', 'if (false && !can_migrate_task(p, env))')
    elif negative == 'post-timeout-concession':
        funcs = funcs.replace('!scan_timed_out)', '(scan_timed_out || !scan_timed_out))')
    elif negative == 'lose-two-task-exception':
        funcs = funcs.replace('cpu_rq(env->src_cpu)->nr_running > 2',
                              'cpu_rq(env->src_cpu)->nr_running > 0')
    elif negative == 'no-timeout':
        funcs = funcs.replace('if (rq_clock(env->src_rq) - start_t > 5000000)',
                              'if (false && rq_clock(env->src_rq) - start_t > 5000000)')
    elif negative == 'no-lb-min':
        funcs = funcs.replace('if (sched_feat(LB_MIN)', 'if (false && sched_feat(LB_MIN)')
    elif negative == 'zero-load-cost':
        funcs = funcs.replace('max_t(unsigned long, task_h_load(p), 1)', 'task_h_load(p)')
    elif negative == 'overflow-concession':
        funcs = funcs.replace('min_t(unsigned long, concession.cost, LONG_MAX)', 'concession.cost')
    code = model.replace('/* FLAGS */', flags).replace('/* FUNCTIONS */', funcs)
    code = code.replace('/* LEGACY */',
                        '#pragma GCC diagnostic push\n'
                        '#pragma GCC diagnostic ignored "-Wsign-compare"\n' +
                        (HERE / 'legacy_detach.c').read_text() +
                        '\n#pragma GCC diagnostic pop\n')
    return code, header


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(cc, root, out, asan, negative=None, variants=None):
    code, header = source(root, negative)
    shim = out / 'shim/linux'
    shim.mkdir(parents=True, exist_ok=True)
    for name, content in {**SHIMS, 'list.h': header}.items():
        (shim / name).write_text(content)
    src = out / 'model.c'
    src.write_text(code)
    flags = [*cc, '-O2', '-g', '-std=gnu11', '-UNDEBUG', '-Wall', '-Wextra', '-Werror',
             '-DCONFIG_DEBUG_LIST', '-I' + str(shim.parent),
             '-fsanitize=' + ('address,undefined' if asan else 'undefined'),
             '-fsanitize-trap=undefined', '-fno-sanitize-recover=all']
    # Make sure the compiler is really enforcing undefined-behaviour traps.
    probe = out / 'probe.c'
    probe.write_text('int main(void) { volatile int n = 2147483647; '
                     'volatile int r = n + 1; (void)r; return 0; }\n')
    subprocess.run([*flags, str(probe), '-o', str(out / 'probe')], check=True)
    p = subprocess.run([str(out / 'probe')], cwd=out, preexec_fn=no_core,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.returncode in (-signal.SIGILL, -signal.SIGTRAP), 'UBSan probe did not trap'
    for preempt, walt in variants or ((0, 0), (1, 0), (0, 1), (1, 1)):
        extra = (['-DCONFIG_PREEMPT'] if preempt else []) + (['-DCONFIG_SCHED_WALT'] if walt else [])
        exe = out / ('model-' + str(preempt) + str(walt))
        subprocess.run([*flags, *extra, str(src), '-o', str(exe)], check=True)
        if asan:
            from elftools.elf.elffile import ELFFile
            with exe.open('rb') as f:
                syms = ELFFile(f).get_section_by_name('.symtab').iter_symbols()
                assert any(s.name.startswith('__asan_') for s in syms), 'compiler ignored ASan'
        p = subprocess.run([str(exe)], cwd=out, preexec_fn=no_core,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (out / ('run-' + str(preempt) + str(walt) + '.log')).write_text(p.stdout)
        if negative:
            if p.returncode == 0:
                raise AssertionError('mutant survived: ' + negative)
            print('PASS: rejected mutant', negative, flush=True)
            return
        print('PREEMPT=' + str(preempt) + ' WALT=' + str(walt), p.stdout.strip(), flush=True)
        if p.returncode:
            raise AssertionError('model failed: ' + str(p.returncode))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cc', default=os.environ.get('HOSTCC', 'clang'))
    ap.add_argument('--source-root', type=Path, default=ROOT)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--asan', action='store_true')
    ap.add_argument('--negative', choices=NEGATIVES)
    ap.add_argument('--self-test-negatives', action='store_true')
    args = ap.parse_args()
    def perform(out):
        run(shlex.split(args.cc), args.source_root, out, args.asan, args.negative)
        if args.self_test_negatives:
            for name in NEGATIVES:
                sub = out / name
                sub.mkdir(exist_ok=True)
                run(shlex.split(args.cc), args.source_root, sub, args.asan, name, [(1, 1)])
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        perform(args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='cambyses-test-') as tmp:
            perform(Path(tmp))


if __name__ == '__main__':
    main()
