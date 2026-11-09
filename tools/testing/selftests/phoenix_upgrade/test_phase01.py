#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Bounded extracted-source checks, not a kernel/device test. No real clone."""
import argparse
from pathlib import Path
import resource
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def function(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def rr_source(negative=False):
    text = (ROOT / 'kernel/sched/core.c').read_text()
    helper = function(text, 'static int sched_rr_get_interval(')
    native = function(text, 'SYSCALL_DEFINE2(sched_rr_get_interval,')
    compat = function(text, 'COMPAT_SYSCALL_DEFINE2(sched_rr_get_interval,')
    if negative:
        native = native.replace('if (retval == 0)', 'if (1)')
        compat = compat.replace('if (retval == 0)', 'if (1)')
    pieces = helper + '\n' + native + '\n#ifdef CONFIG_COMPAT\n' + compat + '\n#endif\n'
    return (HERE / 'rr_model.c').read_text().replace('/* EXTRACTED */', pieces)


def pid_source(negative=False):
    text = (ROOT / 'kernel/pid.c').read_text()
    piece = function(text, 'struct pid *alloc_pid(')
    if negative:
        # Remove only the newly added post-loop reset, not the initializer.
        assert piece.count('\tretval = -ENOMEM;') == 1
        piece = piece.replace('\tretval = -ENOMEM;', '', 1)
    return (HERE / 'pid_model.c').read_text().replace('/* EXTRACTED */', piece)


def clone_source(negative=False):
    text = (ROOT / 'tools/testing/selftests/clone3/clone3.c').read_text()
    mode = text[text.index('enum test_mode {'):text.index('};', text.index('enum test_mode {')) + 2]
    piece = function(text, 'static int call_clone3(')
    if negative:
        assert piece.endswith('\treturn 0;\n}')
        piece = piece[:-len('\treturn 0;\n}')] + '\treturn -1;\n}'
    return (HERE / 'clone_model.c').read_text().replace('/* EXTRACTED */', mode + '\n' + piece)


def source_guards(fork=None, verbose=True):
    if fork is None:
        fork = (ROOT / 'kernel/fork.c').read_text()
    start = fork.index('static __latent_entropy struct task_struct *copy_process(')
    tail = fork[start:fork.index('bad_fork_cancel_cgroup:', start)]
    order = ['spin_lock(&current->sighand->siglock);', 'sched_post_fork(p);',
             'init_task_pid_links(p);', 'spin_unlock(&current->sighand->siglock);',
             'write_unlock_irq(&tasklist_lock);', 'fd_install(pidfd, pidfile);',
             'proc_fork_connector(p);']
    positions = [tail.index(token) for token in order]
    assert positions == sorted(positions)
    assert tail.count('fd_install(pidfd, pidfile);') == 1
    assert 'goto ' not in tail[tail.index('fd_install(pidfd, pidfile);'):]
    assert fork.index('lru_gen_add_mm(p->mm);') < fork.index('wake_up_new_task(p);')
    cleanup = fork[fork.index('bad_fork_put_pidfd:'):fork.index('bad_fork_free_pid:')]
    assert 'fput(pidfile);' in cleanup and 'put_unused_fd(pidfd);' in cleanup
    header = (ROOT / 'tools/testing/selftests/clone3/clone3_selftests.h').read_text()
    wrapper = function(header, 'static pid_t sys_clone3(')
    assert wrapper.index('fflush(stdout);') < wrapper.index('fflush(stderr);') < wrapper.index('return syscall(')
    settid = (ROOT / 'tools/testing/selftests/clone3/clone3_set_tid.c').read_text()
    if 'clone3_count_delta(' in settid:
        assert 'clone3_count_write(' in settid and 'clone3_count_read(' in settid
        assert 'clone3_count_merge(' in settid and '!WIFEXITED(status) || WEXITSTATUS(status)' in settid
        assert settid.count('child_exit(') == 6  # Definition + five callers.
    else:
        assert 'child_exit(ksft_get_fail_cnt() ? 255 : ksft_cnt.ksft_pass);' in settid
        assert settid.count('child_exit(') == 5  # Definition + four callers.
    assert len(re.findall(r'(?<![A-Za-z0-9_])_exit\(', settid)) == 1  # Only inside the flushing helper.
    compat = (ROOT / 'kernel/compat.c').read_text()
    assert 'COMPAT_SYSCALL_DEFINE2(sched_rr_get_interval,' not in compat
    if verbose:
        print('PASS: pidfd ordering, cleanup, MGLRU, flush and failure-propagation source guards', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    source_guards()
    if args.self_test_negatives:
        fork = (ROOT / 'kernel/fork.c').read_text()
        install = '\tif (pidfile)\n\t\tfd_install(pidfd, pidfile);\n\n'
        assert fork.count(install) == 1
        fork = fork.replace(install, '', 1)
        fork = fork.replace('\tinit_task_pid_links(p);', install + '\tinit_task_pid_links(p);', 1)
        try:
            source_guards(fork, verbose=False)
        except AssertionError:
            print('PASS: rejected regression pidfd-install-under-lock', flush=True)
        else:
            raise AssertionError('pidfd order regression was not detected')
    flags = ['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra',
             '-Werror', '-Wno-unused-parameter', '-Wno-missing-field-initializers',
             '-Wno-sign-compare',
             '-fno-pie', '-no-pie', '-fsanitize=undefined', '-fno-sanitize-recover=all']
    with tempfile.TemporaryDirectory(prefix='phoenix-phase01-') as tmp:
        path = Path(tmp)
        cases = [('rr-native', rr_source, []), ('rr-compat', rr_source, ['-DCONFIG_COMPAT']),
                 ('pid-errors', pid_source, []), ('clone-selftest', clone_source, [])]
        for name, build, extra in cases:
            for negative in [False] + ([True] if args.self_test_negatives else []):
                c, binary = path / 'test.c', path / 'test'
                c.write_text(build(negative))
                subprocess.run(flags + extra + [str(c), '-o', str(binary)], check=True)
                run = subprocess.run([str(binary)], text=True, capture_output=True,
                                     preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
                if negative:
                    assert run.returncode != 0 and 'Assertion' in run.stderr, (name, run.stdout, run.stderr)
                    print('PASS: rejected regression ' + name, flush=True)
                else:
                    assert run.returncode == 0, (name, run.stdout, run.stderr)
                    print(run.stdout.strip(), flush=True)
    print('LIMITS: mocked kernel operations and source ordering only; no target build, real clone/PID namespace, SMP/lockdep, device or performance proof.')


if __name__ == '__main__':
    main()
