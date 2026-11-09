/* SPDX-License-Identifier: GPL-2.0 */
/* Selftest helper only: no real clone, wait, namespaces or process exit. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <signal.h>
#include <assert.h>
#define ksft_print_msg(...) ((void)0)
#define __aligned_u64 uint64_t
struct clone_args { uint64_t flags,pidfd,child_tid,parent_tid,exit_signal,stack,stack_size,tls,set_tid,set_tid_size; };
static int mode;
static pid_t fake_clone3(struct clone_args *args,size_t size) { if(mode==1){errno=EPERM;return -1;}return 1234; }
static pid_t fake_waitpid(pid_t pid,int *status,int flags) {
    if(mode==2){errno=ECHILD;return -1;}
    *status=mode==3?(2<<8):(mode==4?SIGKILL:0);
    return 1234;
}
static void fake_exit(int code) { abort(); }
#define sys_clone3 fake_clone3
#define waitpid fake_waitpid
#define _exit fake_exit
/* EXTRACTED */
int main(void)
{
    int expected[]={0,-EPERM,-ECHILD,2,-1};
    for(mode=0;mode<5;mode++)assert(call_clone3(0,0,CLONE3_ARGS_NO_TEST)==expected[mode]);
    puts("PASS:clone3 selftest helper reports success0/syscall error/wait error/child exit/signaled child");
    return 0;
}
