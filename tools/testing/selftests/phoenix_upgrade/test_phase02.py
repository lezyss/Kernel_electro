#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted host regressions only: no target kernel, clone3 syscall or device."""
import argparse
from pathlib import Path
import re
import resource
import subprocess
import tempfile
from test_phase01 import function, ROOT, HERE


def compile_run(tmp, name, source, negative=False, includes=()):
    path = tmp / (name + '.c')
    path.write_text(source)
    binary = tmp / name
    subprocess.run(['gcc', '-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', '-fno-sanitize-recover=all',
                    *[v for p in includes for v in ('-I', str(p))],
                    str(path), '-o', str(binary)], check=True)
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=5,
                            preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
    if negative:
        assert result.returncode, name + ' failed to reject regression'
        print('PASS: rejected regression ' + name)
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        print(result.stdout.strip())


def owner_source(negative=None):
    text = (ROOT / 'fs/fcntl.c').read_text()
    names = ['int f_setown(', 'void f_delown(', 'pid_t f_getown(',
             'static int f_setown_ex(', 'static int f_getown_ex(',
             'void send_sigio(', 'int send_sigurg(']
    extracted = '\n'.join(function(text, n) for n in names)
    if negative in ('sigio-null', 'sigurg-null'):
        name = 'send_sigio_to_task' if negative == 'sigio-null' else 'send_sigurg_to_task'
        extracted, n = re.subn(r'if \(p\)\n\s*(' + name + r'\()', r'\1', extracted)
        assert n == 1
    if negative == 'owner-codec':
        extracted = extracted.replace('type = PIDTYPE_TGID;', 'type = PIDTYPE_PID;')
    return (HERE / 'owner_model.c').read_text().replace('/* EXTRACTED */', extracted)


def source_checks():
    text = (ROOT / 'fs/fcntl.c').read_text()
    signal = (ROOT / 'kernel/signal.c').read_text()
    if 'enum pid_type type)' in function(signal, 'int do_send_sig_info('):
        # Phase03 explicitly supersedes the phase02 int/group bridge.
        assert text.count('p, type)') == 3
        assert 'p, type != PIDTYPE_PID)' not in text
    else:
        assert text.count('p, type != PIDTYPE_PID)') == 3
    for name in ('static void send_sigio_to_task(', 'static void send_sigurg_to_task('):
        assert 'sigio_perm(' in function(text, name)
    producers = {
        'drivers/net/tun.c': '__f_setown(file, task_pid(current), PIDTYPE_TGID, 0)',
        'drivers/tty/tty_io.c': 'type = PIDTYPE_TGID;',
        'fs/locks.c': '__f_setown(filp, task_pid(current), PIDTYPE_TGID, 0)',
        'fs/notify/dnotify/dnotify.c': '__f_setown(filp, task_pid(current), PIDTYPE_TGID, 0)',
    }
    for path, fragment in producers.items():
        assert fragment in (ROOT / path).read_text(), path
    for arch in ('arm', 'arm64', 'x86', 'xtensa'):
        assert 'select HAVE_COPY_THREAD_TLS' in (ROOT / f'arch/{arch}/Kconfig').read_text()
        process = '\n'.join(p.read_text() for p in (ROOT / f'arch/{arch}/kernel').glob('process*.c'))
        assert re.search(r'int\s+copy_thread_tls\(', process), arch
    arm = (ROOT / 'arch/arm/kernel/process.c').read_text()
    xtensa = (ROOT / 'arch/xtensa/kernel/process.c').read_text()
    assert 'thread->tp_value[0] = tls;' in arm and 'childregs->threadptr = tls;' in xtensa
    assert 'childregs->threadptr = childregs->areg[5];' not in xtensa
    fork = (ROOT / 'kernel/fork.c').read_text()
    assert '#ifndef CONFIG_HAVE_COPY_THREAD_TLS\n#error clone3 requires copy_thread_tls support in arch\n#endif' in fork
    assert 'CONFIG_CLONE_BACKWARDS' in fork and 'args->tls' in fork
    settid = (ROOT / 'tools/testing/selftests/clone3/clone3_set_tid.c').read_text()
    assert 'ksft_set_plan(29)' in settid and '#define NESTED_TESTS 6' in settid
    nested = settid[settid.index('if (ns_pid == 0) {'):settid.index('close(pipe_counts[1]);\n\n\tclose(pipe_1[1])')]
    assert nested.count('test_clone3_set_tid(') == 6
    assert nested.index('set_tid[1] = -1;') < nested.index('set_tid[1] = pid;')
    assert nested.count('set_tid[0] = 43;') == 2
    assert 'ksft_cnt.ksft_pass =' not in settid
    merge = settid.index('clone3_count_merge(')
    wait = settid.index('if (!WIFEXITED(status) || WEXITSTATUS(status))', settid.index('if (waitpid(ns_pid'))
    assert wait < merge and 'clone3_count_read(' in settid[wait:merge]
    print('PASS: producer/codec consistency, retained signal/LSM boundaries, ARM/Xtensa TLS source and six-child plan/exit/report integration')


def label_model():
    text = (ROOT / 'security/selinux/hooks.c').read_text()
    expr = function(text, 'static int selinux_is_genfs_special_handling(struct super_block *sb)\n{')
    expr = expr[expr.index('return'):expr.index(';', expr.index('return')) + 1]
    mount = text[text.index('if (!strcmp(sb->s_type->name, "debugfs")'): ]
    mount = mount[mount.index('(') + 1:mount.index('\n\t\tsbsec->flags |= SE_SBGENFS;')].strip()[:-1]
    # Compile actual source predicates, not a reimplementation of their boolean expressions.
    return '''#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define selinux_policycap_cgroupseclabel() cgroups
struct fs_type {const char *name;};
struct super_block {struct fs_type *s_type;};
static int cgroups;
static bool label(struct super_block *sb) {''' + expr + '''}
static bool mount_genfs(struct super_block *sb) {return ''' + mount + ''';}
int main(void) {
const char *names[] = {"sysfs","pstore","debugfs","tracefs","rootfs","cgroup","cgroup2","functionfs","securityfs","bpf","ext4","f2fs","proc","binder"};
for(cgroups=0;cgroups<2;cgroups++) for(unsigned i=0;i<sizeof(names)/sizeof(*names);i++) {
struct fs_type fs={names[i]};struct super_block sb={&fs};
bool expected=i<5 || i==7 || (cgroups && (i==5 || i==6));assert(label(&sb)==expected);
assert(mount_genfs(&sb)==(i==1 || i==2 || i==3 || i==7 || i==8 || i==9 || i==13));
} puts("PASS:56 actual genfs predicates (cgroup policycap on/off); FunctionFS special, securityfs genfs-only");}
'''


def tls_model():
    fragments = []
    for arch in ('arm', 'xtensa'):
        text = (ROOT / f'arch/{arch}/kernel/process.c').read_text()
        field = r'thread->tp_value\[0\]' if arch == 'arm' else r'childregs->threadptr'
        fragments.append(re.search(r'if \(clone_flags & CLONE_SETTLS\)\s*' + field + r' = tls;', text).group())
    return '''#include <assert.h>
#include <stdio.h>
#define CLONE_SETTLS 1
struct state {unsigned long tp_value[1], threadptr;};
static void arm(struct state *thread, int clone_flags, unsigned long tls) {''' + fragments[0] + '''}
static void xtensa(struct state *childregs, int clone_flags, unsigned long tls) {''' + fragments[1] + '''}
int main(void) {for(int flags=0;flags<4;flags++) for(unsigned long tls=0;tls<64;tls++) {
struct state t={{999},999};arm(&t,flags,tls);xtensa(&t,flags,tls);
assert(t.tp_value[0]==((flags & CLONE_SETTLS)?tls:999));assert(t.threadptr==t.tp_value[0]);
} puts("PASS:512 extracted ARM/Xtensa TLS assignments, distinct from legacy register/inherited value");}
'''


def compat_model():
    header = (ROOT / 'include/linux/compat.h').read_text()
    start = header.index('#define COMPAT_SYSCALL_DEFINEx(')
    macro = header[start:header.index('\n\n', start)]
    syscalls = (ROOT / 'include/linux/syscalls.h').read_text()
    maps = '\n'.join(line for line in syscalls.splitlines() if line.startswith('#define __MAP'))
    prelude = r'''#include <assert.h>
#include <stdio.h>
#define asmlinkage
#define __force
#define __SC_DECL(t,a) t a
#define __SC_LONG(t,a) long a
#define __SC_DELOUSE(t,a) ((t)(unsigned long)(a))
#define stringify_inner(x) #x
#define __stringify(x) stringify_inner(x)
'''
    definitions, calls = [], []
    for n in range(1, 7):
        args = ','.join(f'long,a{j}' for j in range(n))
        definitions.append(f'COMPAT_SYSCALL_DEFINEx({n}, _test{n}, {args}) {{return ' + '+'.join(f'a{j}' for j in range(n)) + ';}')
        calls.append(f'assert(compat_sys_test{n}(' + ','.join(str(j + 1) for j in range(n)) + f') == {n*(n+1)//2});')
    return prelude + maps + '\n' + macro + '\n' + '\n'.join(definitions) + '\nint main(void) {' + ''.join(calls) + 'puts("PASS:6 actual generic compat macro arities, prototypes and callable aliases (long-argument host model)");}'


def tls_guard_checks():
    fork = (ROOT / 'kernel/fork.c').read_text()
    guard = re.search(r'#ifndef CONFIG_HAVE_COPY_THREAD_TLS\n#error[^\n]+\n#endif', fork).group()
    source = '#ifdef __ARCH_WANT_SYS_CLONE3\n' + guard + '\n#endif\n'
    for wants, implements, expected in ((0, 0, 0), (1, 1, 0), (1, 0, 1)):
        defines = (['-D__ARCH_WANT_SYS_CLONE3'] if wants else []) + (['-DCONFIG_HAVE_COPY_THREAD_TLS'] if implements else [])
        result = subprocess.run(['gcc', '-E', '-P', '-x', 'c', *defines, '-'], input=source, text=True, capture_output=True)
        assert bool(result.returncode) == bool(expected)
    print('PASS:actual clone3 TLS preprocessing guard rejects missing implementation only when clone3 is requested')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    source_checks()
    tls_guard_checks()
    clone = ROOT / 'tools/testing/selftests/clone3'
    with tempfile.TemporaryDirectory(prefix='phx-phase02-') as directory:
        tmp = Path(directory)
        compile_run(tmp, 'owners', owner_source())
        compile_run(tmp, 'counts', (HERE / 'count_model.c').read_text(), includes=(clone,))
        compile_run(tmp, 'labels', label_model())
        compile_run(tmp, 'tls', tls_model())
        compile_run(tmp, 'compat', compat_model())
        if args.self_test_negatives:
            for name in ('sigio-null', 'sigurg-null', 'owner-codec'):
                compile_run(tmp, name, owner_source(name), True)
            compile_run(tmp, 'tls-legacy-value', tls_model().replace('= tls;', '= ((void)tls, 999);'), True)
            labels = label_model()
            old = '!strcmp(sb->s_type->name, "functionfs")'
            assert labels.count(old) == 2
            compile_run(tmp, 'functionfs-policycap-gated', labels.replace(old, '(cgroups && ' + old + ')', 1), True)
            original = (clone / 'clone3_set_tid_counts.h').read_text()
            # Header's relative kselftest include is resolved explicitly in scratch.
            original = original.replace('"../kselftest.h"', '"' + str(clone.parent / 'kselftest.h') + '"')
            for name, old, new in (
                ('counts-overwrite-parent', '*parent_values[i] += values[i];', '*parent_values[i] = values[i];'),
                ('counts-inherited-baseline', 'values[i] - baseline[i];', 'values[i];'),
                ('counts-overflow', 'values[i] > UINT_MAX - *parent_values[i]', '0'),
            ):
                assert old in original
                (tmp / 'clone3_set_tid_counts.h').write_text(original.replace(old, new))
                compile_run(tmp, name, (HERE / 'count_model.c').read_text(), True, includes=(tmp,))
    print('LIMITS: host GCC/UBSan/source predicates only; no real signal races/LSM decisions, target build, clone3 namespaces or enforcing ROM/USB/ADB proof.')


if __name__ == '__main__':
    main()
