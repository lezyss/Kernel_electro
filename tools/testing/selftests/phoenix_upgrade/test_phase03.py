#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Bounded syscall-helper and typed signal/fork regressions, not kernel execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from test_phase01 import ROOT, HERE, function
from test_phase02 import compile_run


def signals(negative=None):
    text = (ROOT / 'kernel/signal.c').read_text()
    body = function(text, 'static int __send_signal(')
    collector = body[body.index('\t/* Let multiprocess signals'):body.index('\n\tcomplete_signal(', body.index('\t/* Let multiprocess signals'))]
    if negative == 'collect-tgid':
        collector = collector.replace('type > PIDTYPE_TGID', 'type >= PIDTYPE_TGID')
    if negative == 'stop-cont':
        collector = collector.replace('sigdelsetmask(signal, SIG_KERNEL_STOP_MASK);', 'sigdelsetmask(signal, 0);')
    expr = re.search(r'pending = \(type != PIDTYPE_PID\)[^;]+;', body).group()
    if negative == 'private-queue':
        expr = expr.replace('type != PIDTYPE_PID', 'type == PIDTYPE_PID')
    return r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#define SIGCONT 18
#define SIGSTOP 19
#define SIGTSTP 20
#define SIGTTIN 21
#define SIGTTOU 22
#define BIT(s) (UINT64_C(1) << ((s)-1))
#define SIG_KERNEL_STOP_MASK (BIT(SIGSTOP)|BIT(SIGTSTP)|BIT(SIGTTIN)|BIT(SIGTTOU))
typedef struct { uint64_t bits; } sigset_t;
enum pid_type {PIDTYPE_PID,PIDTYPE_TGID,PIDTYPE_PGID,PIDTYPE_SID,PIDTYPE_MAX};
struct multiprocess_signals {sigset_t signal;};
struct head {struct multiprocess_signals items[2];};
struct sigpending {int marker;};
struct signal_struct {struct head multiprocess;struct sigpending shared_pending;};
struct task_struct {struct signal_struct *signal;struct sigpending pending;};
#define hlist_for_each_entry(v,head,node) for (int i=0;i<2 && ((v)=&(head)->items[i]);i++)
static void sigdelsetmask(sigset_t *s,uint64_t mask) {s->bits &= ~mask;}
static void sigdelset(sigset_t *s,int sig) {s->bits &= ~BIT(sig);}
static void sigaddset(sigset_t *s,int sig) {s->bits |= BIT(sig);}
static int sig_kernel_stop(int sig) {return !!(SIG_KERNEL_STOP_MASK & BIT(sig));}
static void send(int sig,struct task_struct *t,enum pid_type type) {
''' + collector + '''
}
static struct sigpending *queue(struct task_struct *t,enum pid_type type) {
struct sigpending *pending;
''' + expr + '''
return pending;}
int main(void) {int cases=0;struct signal_struct group={0};struct task_struct task={&group,{0}};
uint64_t initial[]={0,UINT64_MAX,BIT(SIGCONT),SIG_KERNEL_STOP_MASK,BIT(2)|BIT(SIGCONT),BIT(64)};
for(int type=0;type<5;type++) for(int sig=1;sig<=64;sig++) for(unsigned n=0;n<sizeof(initial)/sizeof(*initial);n++) {
for(int i=0;i<2;i++) group.multiprocess.items[i].signal.bits=initial[n];
send(sig,&task,type);uint64_t expected=initial[n];
if(type>PIDTYPE_TGID) {if(sig==SIGCONT)expected &= ~SIG_KERNEL_STOP_MASK;
else if(sig>=SIGSTOP && sig<=SIGTTOU) {expected &= ~BIT(SIGCONT);}
expected |= BIT(sig);}
for(int i=0;i<2;i++)assert(group.multiprocess.items[i].signal.bits==expected);
assert(queue(&task,type)==(type==PIDTYPE_PID?&task.pending:&group.shared_pending));cases++;
} printf("PASS:%d extracted multiprocess collector/private-shared queue cases\\n",cases);}
'''


def compat(words, big, negative=False):
    text = (ROOT / 'kernel/compat.c').read_text()
    get = function(text, 'int\nget_compat_sigset(')
    put = function(text, 'int\nput_compat_sigset(')
    legacy = function(text, 'void\nsigset_from_compat(')
    if negative:
        get = get.replace('unsigned long)v.sig[', 'long)v.sig[')
    return r'''
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <errno.h>
#undef __BIG_ENDIAN
''' + ('#define __BIG_ENDIAN 1\n' if big else '') + f'#define _NSIG_WORDS {words}\n' + r'''
#define __user
typedef struct {unsigned long sig[_NSIG_WORDS];} sigset_t;
typedef struct {uint32_t sig[2*_NSIG_WORDS];} compat_sigset_t;
static int fault;
static int copy_from_user(void *d,const void *s,unsigned n) {if(fault)return 1;memcpy(d,s,n);return 0;}
static int copy_to_user(void *d,const void *s,unsigned n) {return copy_from_user(d,s,n);}
''' + get + '\n' + put + '\n' + legacy + r'''
int main(void) {compat_sigset_t in,out;sigset_t set;
for(unsigned seed=0;seed<100;seed++) {
for(unsigned i=0;i<2*_NSIG_WORDS;i++)in.sig[i]=UINT32_C(0xdeadbeef) ^ (seed*719+i*79);
assert(get_compat_sigset(&set,&in)==0);
for(unsigned i=0;i<_NSIG_WORDS;i++)assert(set.sig[i]==((uint64_t)in.sig[2*i+1]<<32 | in.sig[2*i]));
assert(!put_compat_sigset(&out,&set,sizeof(out)));assert(!memcmp(&in,&out,sizeof(in)));
sigset_from_compat(&set,&in);
for(unsigned i=0;i<_NSIG_WORDS;i++)assert(set.sig[i]==((uint64_t)in.sig[2*i+1]<<32 | in.sig[2*i]));
} fault=1;assert(get_compat_sigset(&set,&in)==-EFAULT);assert(put_compat_sigset(&out,&set,sizeof(out))==-EFAULT);
printf("PASS:compat sigsets words=%d, endian=%s,100 high-bit roundtrips + uaccess failures\n",_NSIG_WORDS,
#ifdef __BIG_ENDIAN
"BE"
#else
"LE"
#endif
);}
'''


def fork_checks(text=None):
    text = text or (ROOT / 'kernel/fork.c').read_text()
    copy = function(text, 'static __latent_entropy struct task_struct *copy_process(')
    init = copy.index('INIT_HLIST_NODE(&delayed.node);')
    registration = copy.index('hlist_add_head(&delayed.node, &current->signal->multiprocess);')
    allocation = copy.index('p = dup_task_struct(')
    assert init < registration < allocation
    assert 'if (!(clone_flags & CLONE_THREAD))' in copy[init:registration]
    assert copy.count('hlist_del_init(&delayed.node);') == 2
    assert not re.search(r'\breturn\b', copy[registration:copy.index('return p;')])
    assert 'p->signal->shared_pending.signal = delayed.signal;' in copy
    assert 'task_join_group_stop(p);' in copy
    late = copy[copy.index('copy_seccomp(p);'):copy.index('sched_post_fork(p);')]
    assert late.index('PIDNS_HASH_ADDING') < late.index('fatal_signal_pending(current)')
    assert 'retval = -EINTR;' in late and 'signal_pending(current)' not in late.replace('fatal_signal_pending(current)', '')
    cleanup = copy[copy.index('fork_out:'):]
    assert cleanup.index('spin_lock_irq(') < cleanup.index('hlist_del_init(') < cleanup.index('spin_unlock_irq(')
    successful = copy[copy.index('total_forks++;'):copy.index('return p;')]
    assert successful.index('hlist_del_init(') < successful.index('spin_unlock(') < successful.index('fd_install(')
    outer = function(text, 'long _do_fork(struct kernel_clone_args *args)')
    assert outer.index('if (IS_ERR(p))') < outer.index('cpufreq_task_times_alloc(p);')
    assert outer.index('lru_gen_add_mm(p->mm);') < outer.index('wake_up_new_task(p);')
    assert 'args->parent_tid' in outer and 'args->exit_signal' in outer
    signal = (ROOT / 'kernel/signal.c').read_text()
    timer = function(signal, 'int send_sigqueue(')
    assert timer.index('rcu_read_lock();') < timer.index('pid_task(pid, type)') < timer.index('!t ||')
    assert 'rcu_read_unlock();' in timer and 'type != PIDTYPE_PID' in timer
    assert 'calculate_sigpending();' in function((ROOT / 'kernel/sched/core.c').read_text(), 'asmlinkage __visible void schedule_tail(')
    assert 'set_tsk_thread_flag(task, TIF_SIGPENDING)' not in (ROOT / 'include/linux/ptrace.h').read_text()


def ni_checks():
    text = (ROOT / 'kernel/sys_ni.c').read_text()
    names = []
    for line in text.splitlines():
        m = re.fullmatch(r'(cond_syscall|COND_SYSCALL|COND_SYSCALL_COMPAT)\((\w+)\);', line)
        if m:
            names.append(('sys_' if m[1] == 'COND_SYSCALL' else 'compat_sys_' if m[1] == 'COND_SYSCALL_COMPAT' else '') + m[2])
    assert len(names) == len(set(names)) == 218
    assert {'sys_clone3', 'sys_bpf', 'sys32_quotactl', 'ppc_rtas'} <= set(names)
    assert 'return -ENOSYS;' in function(text, 'asmlinkage long sys_ni_syscall(')
    print('PASS:218 unique weak fallbacks including clone3/BPF/legacy quota/ppc, -ENOSYS unchanged')


def forwarding():
    contracts = json.loads((HERE / 'forwarding-contracts.json').read_text())
    assert len(contracts) >= 70
    code = '#include <assert.h>\n#include <stdio.h>\n'
    calls = []
    for i, contract in enumerate(contracts):
        text = (ROOT / contract['path']).read_text()
        actual = function(text, contract['signature'])
        body = actual[actual.index('{'):]
        params = contract['parameters']
        args = ','.join('long ' + v for v in params) or 'void'
        helper_args = ','.join('long v' + str(j) for j in range(len(params))) or 'void'
        checks = ''.join('assert(v' + str(j) + ' == ' + str(j + 61) + ');' for j in range(len(params)))
        code += 'static long capture' + str(i) + '(' + helper_args + '){' + checks + 'return -' + str(i + 1) + ';}\n'
        code += '#define ' + contract['helper'] + ' capture' + str(i) + '\n'
        code += 'static long wrapper' + str(i) + '(' + args + ')' + body + '\n'
        code += '#undef ' + contract['helper'] + '\n'
        calls.append('assert(wrapper' + str(i) + '(' + ','.join(str(j + 61) for j in range(len(params))) + ') == -' + str(i + 1) + ');')
    code += 'int main(void){' + ''.join(calls) + 'puts("PASS:' + str(len(contracts)) + ' actual syscall forwarding bodies: distinct arguments and negative helper return values");}\n'
    return code


def legacy_module_checks(negative=False):
    exports = {
        'fs/open.c': ('EXPORT_SYMBOL(sys_close);',),
        'fs/read_write.c': ('EXPORT_SYMBOL(iov_shorten);',),
        'kernel/compat.c': ('EXPORT_SYMBOL_GPL(sigset_from_compat);',),
    }
    for path, names in exports.items():
        text = (ROOT / path).read_text()
        if negative and path == 'fs/open.c':
            text = text.replace('EXPORT_SYMBOL(sys_close);', '')
        for name in names:
            assert name in text, (path, name)
    body = function((ROOT / 'fs/read_write.c').read_text(), 'unsigned long iov_shorten(')
    return r'''
#include <assert.h>
#include <stdio.h>
#include <stddef.h>
struct iovec {void *iov_base;size_t iov_len;};
''' + body + r'''
int main(void){int cases=0;
for(unsigned long n=0;n<=4;n++)for(size_t to=0;to<32;to++){
 struct iovec v[4]={{0,1},{0,3},{0,5},{0,7}};size_t lens[]={1,3,5,7};
 size_t sum=0;unsigned long expected=0;int cut=-1;
 while(expected<n){size_t len=lens[expected++];if(sum+len>=to){cut=expected-1;break;}sum+=len;}
 assert(iov_shorten(v,n,to)==expected);
 for(unsigned long j=0;j<n;j++){
  size_t want=lens[j];if((int)j==cut)want=to-sum;
  assert(v[j].iov_len==want);
 } cases++;
}printf("PASS:%d legacy module iov_shorten count/truncation/zero/boundary cases\n",cases);}
'''


def eventfd_checks(negative=None):
    text = (ROOT / 'fs/eventfd.c').read_text()
    header = (ROOT / 'include/linux/eventfd.h').read_text()
    for name in ('eventfd_ctx_read', 'eventfd_ctx_get'):
        assert 'EXPORT_SYMBOL_GPL(' + name + ');' in text
        assert name + '(' in header
    code = '\n'.join(function(text, sig) for sig in (
        'static void eventfd_ctx_do_read(', 'ssize_t eventfd_ctx_read(',
        'static ssize_t eventfd_read(', 'static int do_eventfd(',
        'struct eventfd_ctx *eventfd_ctx_get('))
    if negative == 'eventfd-cleanup':
        code = code.replace('if (fd < 0)', 'if (fd < -10000)')
    if negative == 'eventfd-counter':
        code = code.replace('ctx->count -= *cnt;', 'ctx->count += *cnt;')
    return r'''
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#pragma GCC diagnostic ignored "-Wunused-parameter"
#define __user
#define __u64 uint64_t
#define loff_t int64_t
#define ERESTARTSYS 512
#define EFD_SEMAPHORE 1
#define EFD_NONBLOCK O_NONBLOCK
#define EFD_CLOEXEC O_CLOEXEC
#define EFD_SHARED_FCNTL_FLAGS (O_CLOEXEC|O_NONBLOCK)
#define EFD_FLAGS_SET (EFD_SHARED_FCNTL_FLAGS|EFD_SEMAPHORE)
#define GFP_KERNEL 0
#define TASK_INTERRUPTIBLE 1
#define TASK_RUNNING 0
#define POLLOUT 4
#define BUILD_BUG_ON(x) _Static_assert(!(x), "flag ABI")
#define likely(x) (x)
#define DECLARE_WAITQUEUE(w,c) int w=0
#define current 0
struct queue {int lock, active;};
struct eventfd_ctx {int kref;struct queue wqh;uint64_t count;int flags;};
struct file {struct eventfd_ctx *private_data;int f_flags;};
static int state, pending, schedules, deliver, wakes, copies, fault;
static struct eventfd_ctx *sleep_ctx;
static int oom, fd_error, allocated, freed, fd_calls, file_flags;
static struct eventfd_ctx *installed;
static int eventfd_fops;
#define spin_lock_irq(p) do {assert(!*(p));*(p)=1;} while(0)
#define spin_unlock_irq(p) do {assert(*(p));*(p)=0;} while(0)
static void __add_wait_queue(struct queue *q,int *w){assert(q->lock);q->active++;}
static void __remove_wait_queue(struct queue *q,int *w){assert(q->lock);q->active--;}
static void set_current_state(int s){state=s;}
static void __set_current_state(int s){state=s;}
static int signal_pending(int c){return pending;}
static int waitqueue_active(struct queue *q){return q->active;}
static void wake_up_locked_poll(struct queue *q,int mask){assert(q->lock && mask==POLLOUT);wakes++;}
static void schedule(void){assert(!sleep_ctx->wqh.lock && state==TASK_INTERRUPTIBLE);schedules++;if(deliver)sleep_ctx->count=7;else pending=1;}
static int put(uint64_t value,uint64_t *out){copies++;if(fault)return 1;*out=value;return 0;}
#define put_user(v,p) put(v,p)
static void *alloc(size_t n){if(oom)return NULL;allocated++;return calloc(1,n);}
#define kmalloc(n,f) alloc(n)
static void kref_init(int *r){*r=1;}
static void kref_get(int *r){assert(*r>0);(*r)++;}
static void init_waitqueue_head(struct queue *q){q->lock=0;q->active=0;}
static void eventfd_free_ctx(struct eventfd_ctx *c){freed++;free(c);}
static int anon_inode_getfd(const char *name,int *ops,struct eventfd_ctx *c,int flags){
 assert(!strcmp(name,"[eventfd]") && ops==&eventfd_fops);fd_calls++;file_flags=flags;
 if(fd_error) { return fd_error; }
 installed=c;return 23;
}
''' + code + r'''
static void reset(void){state=TASK_RUNNING;pending=schedules=deliver=wakes=copies=fault=0;}
int main(void){unsigned cases=0;
/* Actual allocation helper: all valid flags, high initial counts, allocator/fd failure. */
uint32_t counts[]={0,1,UINT32_MAX};
for(int bits=0;bits<8;bits++)for(unsigned n=0;n<3;n++)for(int failure=0;failure<3;failure++){
 int flags=(bits&1?EFD_SEMAPHORE:0)|(bits&2?EFD_NONBLOCK:0)|(bits&4?EFD_CLOEXEC:0);
 int a=allocated,f=freed,calls=fd_calls;oom=failure==1;fd_error=failure==2?-EMFILE:0;
 int r=do_eventfd(counts[n],flags);
 if(oom){assert(r==-ENOMEM && allocated==a && freed==f && fd_calls==calls);}
 else if(fd_error){assert(r==-EMFILE && allocated==a+1 && freed==f+1 && fd_calls==calls+1);}
 else {assert(r==23 && installed->count==counts[n] && installed->flags==flags);
 assert(installed->kref==1 && !installed->wqh.active && !installed->wqh.lock);
 assert(file_flags==(O_RDWR|(flags&EFD_SHARED_FCNTL_FLAGS)));
 assert(eventfd_ctx_get(installed)==installed && installed->kref==2);installed->kref--;
 eventfd_free_ctx(installed);assert(allocated==a+1 && freed==f+1);}
 cases++;
}
/* Invalid flags precede OOM/fd allocation in the approved PHX014 variant. */
int a=allocated,calls=fd_calls;oom=1;fd_error=-EMFILE;
assert(do_eventfd(1,0x40000000)==-EINVAL && allocated==a && fd_calls==calls);cases++;
uint64_t values[]={1,5,UINT64_MAX};
for(int sem=0;sem<2;sem++)for(unsigned n=0;n<3;n++)for(int badcopy=0;badcopy<2;badcopy++){
 struct eventfd_ctx c={.count=values[n],.flags=sem?EFD_SEMAPHORE:0,.wqh={0,1}};
 struct file file={&c,O_NONBLOCK};uint64_t out=99;uint64_t expected=sem?1:values[n];
 reset();fault=badcopy;
 assert(eventfd_read(&file,(char *)&out,8,NULL)==(badcopy?-EFAULT:8));
 assert(c.count==values[n]-expected && wakes==1 && copies==1 && !c.wqh.lock);
 if(!badcopy) { assert(out==expected); }
 cases++;
 c.count=values[n];reset();out=99;
 assert(eventfd_ctx_read(&c,1,&out)==0 && out==expected && c.count==values[n]-expected);
 assert(wakes==1 && !copies && !c.wqh.lock);cases++;
}
for(int legacy=0;legacy<2;legacy++)for(int mode=0;mode<4;mode++){
 struct eventfd_ctx c={.wqh={0,1}};struct file file={&c,mode==0?O_NONBLOCK:0};uint64_t out=99;
 reset();sleep_ctx=&c;pending=mode==1;deliver=mode==2;
 ssize_t r=legacy?eventfd_ctx_read(&c,mode==0,&out):eventfd_read(&file,(char *)&out,8,NULL);
 assert(r==(mode==0?-EAGAIN:mode==2?(legacy?0:8):-ERESTARTSYS));
 assert(c.wqh.active==1 && !c.wqh.lock && state==TASK_RUNNING);
 assert(schedules==(mode>=2?1:0));assert(wakes==(mode==2));
 assert(copies==(!legacy && mode==2));if(mode==2)assert(out==7 && !c.count);
 if(legacy && mode!=2) { assert(out==0); }
 cases++;
}
struct eventfd_ctx c={.count=7};struct file file={&c,0};uint64_t out=99;reset();
assert(eventfd_read(&file,(char *)&out,7,NULL)==-EINVAL && c.count==7 && !copies);cases++;
assert(allocated==freed);printf("PASS:%u extracted eventfd allocation/flags/cleanup/refcount/counter/semaphore/wait/signal/EFAULT/legacy-export cases\n",cases);
}
'''


def arm_clobber_checks(negative=False):
    text = (ROOT / 'arch/arm/include/asm/uaccess.h').read_text()
    assert 'sbcscc %1, %1, %0' in text and 'sbcccs %1, %1, %0' not in text
    line = next(line.strip() for line in text.splitlines() if ': ' in line and '__asmbl_clobber("ip")' in line)
    clobbers = line[2:-1]
    if negative:
        clobbers = '__asmbl_clobber("ip"), "lr", "cc"'
    for module in (False, True):
        macro = ', reg' if module else ''
        source = '#define __asmbl_clobber(reg) ' + macro + '\nvoid f(void){__asm__ volatile("" ::: ' + clobbers + '); }'
        # Syntax-only deliberately checks C grammar without host-register validation.
        result = subprocess.run(['gcc', '-fsyntax-only', '-x', 'c', '-'], input=source, text=True, capture_output=True)
        assert bool(result.returncode) == negative
    print('PASS:' + (' rejected bad' if negative else 'actual') + ' native ARM optional-clobber syntax, built-in/module-long-call variants')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    fork_checks()
    ni_checks()
    arm_clobber_checks()
    print('PASS:fork collector registration/all-path cleanup/fatal abort/group-stop, BPF/pidfd/MGLRU order, timer lifetime and schedule-tail source guards')
    with tempfile.TemporaryDirectory(prefix='phoenix-phase03-') as d:
        tmp = Path(d)
        compile_run(tmp, 'legacy-module-abi', legacy_module_checks())
        compile_run(tmp, 'eventfd', eventfd_checks())
        compile_run(tmp, 'signals', signals())
        compile_run(tmp, 'forwarding', forwarding())
        # Intentional upstream switch fallthrough is exercised for all word counts.
        for words in range(1, 5):
            for big in (False, True):
                source = compat(words, big).replace('#define __user', '#pragma GCC diagnostic ignored "-Wimplicit-fallthrough"\n#define __user')
                compile_run(tmp, f'compat-{words}-{big}', source)
        if args.self_test_negatives:
            arm_clobber_checks(True)
            try:
                legacy_module_checks(True)
            except AssertionError:
                print('PASS: rejected legacy module export removal')
            else:
                raise AssertionError('legacy export mutant was not rejected')
            for name in ('eventfd-cleanup', 'eventfd-counter'):
                compile_run(tmp, name, eventfd_checks(name), True)
            code = forwarding()
            assert 'return ksys_pread64(fd, buf, count, pos);' in code
            compile_run(tmp, 'forwarding-arguments', code.replace('return ksys_pread64(fd, buf, count, pos);', 'return ksys_pread64(fd, buf, pos, count);'), True)
            for name in ('collect-tgid', 'stop-cont', 'private-queue'):
                compile_run(tmp, name, signals(name), True)
            source = compat(1, True, True).replace('#define __user', '#pragma GCC diagnostic ignored "-Wimplicit-fallthrough"\n#define __user')
            compile_run(tmp, 'signed-high-half', source, True)
            fork = (ROOT / 'kernel/fork.c').read_text()
            for name, old, new in [('missing-cleanup', 'hlist_del_init(&delayed.node);', ';'),
                                   ('fatal-abort', 'retval = -EINTR;', 'retval = -ERESTARTNOINTR;')]:
                assert old in fork
                try:
                    fork_checks(fork.replace(old, new))
                except (AssertionError, ValueError):
                    print('PASS: rejected regression ' + name)
                else:
                    raise AssertionError('accepted ' + name)
    print('LIMITS:mock/extracted-source/host UBSan checks only, not real RCU/signal/fork/namespace/SELinux concurrency or target boot proof.')


if __name__ == '__main__':
    main()
