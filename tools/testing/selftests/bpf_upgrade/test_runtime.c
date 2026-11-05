// SPDX-License-Identifier: GPL-2.0
/* Rooted-device smoke test. Build with a native Linux/Termux C compiler.
 * This tests the running kernel, NOT a kernel image sitting on disk.
 * It does not cover asynchronous BPF timer teardown, networking or SMP stress.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
#include "../../../../include/uapi/linux/bpf.h"
#include "../../../../include/uapi/linux/btf.h"
#ifndef __NR_bpf
#if defined(__aarch64__)
#define __NR_bpf 280
#else
#error "Use a native compiler with BPF syscall numbers"
#endif
#endif
#ifndef __NR_pidfd_open
#define __NR_pidfd_open 434
#endif
#define PTR(p) ((uint64_t)(uintptr_t)(p))
#define I(c,d,s,o,v) ((struct bpf_insn){.code=(c),.dst_reg=(d),.src_reg=(s),.off=(o),.imm=(v)})
static char logbuf[65536];
static int bpf(enum bpf_cmd cmd,union bpf_attr *attr)
{ return syscall(__NR_bpf,cmd,attr,sizeof(*attr)); }
static void die(const char *what)
{ fprintf(stderr,"FAIL: %s: %s\n%s\n",what,strerror(errno),logbuf);exit(1); }
static void program(struct bpf_insn *insns,unsigned int count,unsigned int expected)
{
 memset(logbuf,0,sizeof(logbuf));
 union bpf_attr a={.prog_type=BPF_PROG_TYPE_SOCKET_FILTER,.insn_cnt=count,.insns=PTR(insns),
  .license=PTR("GPL"),.log_buf=PTR(logbuf),.log_size=sizeof(logbuf),.log_level=1};
 int fd=bpf(BPF_PROG_LOAD,&a);if(fd<0)die("BPF_PROG_LOAD");
 unsigned char in[64]={0},out[256];memset(&a,0,sizeof(a));
 a.test.prog_fd=fd;a.test.data_in=PTR(in);a.test.data_size_in=sizeof(in);
 a.test.data_out=PTR(out);a.test.data_size_out=sizeof(out);a.test.repeat=1;
 if(bpf(BPF_PROG_TEST_RUN,&a))die("BPF_PROG_TEST_RUN");
 if(a.test.retval!=expected){errno=ERANGE;die("unexpected BPF result");}close(fd);
}
static void instructions(void)
{
 struct bpf_insn jmp[]={I(BPF_LD|BPF_DW|BPF_IMM,1,0,0,1),I(0,0,0,0,1),
  I(BPF_ALU64|BPF_MOV|BPF_K,0,0,0,42),I(BPF_JMP32|BPF_JEQ|BPF_K,1,0,1,1),
  I(BPF_ALU64|BPF_MOV|BPF_K,0,0,0,0),I(BPF_JMP|BPF_EXIT,0,0,0,0)};
 program(jmp,sizeof(jmp)/sizeof(*jmp),42);
 struct bpf_insn atomic[]={I(BPF_ST|BPF_MEM|BPF_DW,10,0,-8,5),
  I(BPF_ALU64|BPF_MOV|BPF_K,1,0,0,3),I(BPF_STX|BPF_ATOMIC|BPF_DW,10,1,-8,BPF_ADD|BPF_FETCH),
  I(BPF_LDX|BPF_MEM|BPF_DW,0,10,-8,0),I(BPF_JMP|BPF_JEQ|BPF_K,1,0,1,5),
  I(BPF_ALU64|BPF_MOV|BPF_K,0,0,0,0),I(BPF_JMP|BPF_EXIT,0,0,0,0)};
 program(atomic,sizeof(atomic)/sizeof(*atomic),8);
 puts("PASS: JMP32 high-half semantics and atomic fetch-add load/JIT/run");
}
static void task_storage(void)
{
 struct {
  struct btf_header header;
  struct btf_type integer;
  uint32_t encoding;
  char strings[5];
 } blob={.header={.magic=BTF_MAGIC,.version=BTF_VERSION,.hdr_len=sizeof(struct btf_header),
   .type_len=sizeof(struct btf_type)+4,.str_off=sizeof(struct btf_type)+4,.str_len=5},
  .integer={.name_off=1,.info=BTF_KIND_INT<<24,.size=4},.encoding=(BTF_INT_SIGNED<<24)|32,
  .strings="\0int"};
 union bpf_attr a={.btf=PTR(&blob),.btf_size=sizeof(struct btf_header)+sizeof(struct btf_type)+4+5,
  .btf_log_buf=PTR(logbuf),.btf_log_size=sizeof(logbuf),.btf_log_level=1};
 memset(logbuf,0,sizeof(logbuf));int btf=bpf(BPF_BTF_LOAD,&a);if(btf<0)die("BTF integer schema load");
 memset(&a,0,sizeof(a));a.map_type=BPF_MAP_TYPE_TASK_STORAGE;a.key_size=4;a.value_size=4;
 a.map_flags=BPF_F_NO_PREALLOC;a.btf_fd=btf;a.btf_key_type_id=1;a.btf_value_type_id=1;
 int map=bpf(BPF_MAP_CREATE,&a);if(map<0)die("task storage map create");close(btf);
 int pidfd=syscall(__NR_pidfd_open,getpid(),0);if(pidfd<0)die("pidfd_open");
 uint32_t value=0x51512345,got=0;
 memset(&a,0,sizeof(a));a.map_fd=map;a.key=PTR(&pidfd);a.value=PTR(&value);
 if(bpf(BPF_MAP_UPDATE_ELEM,&a))die("task storage update via real pidfd");
 a.value=PTR(&got);if(bpf(BPF_MAP_LOOKUP_ELEM,&a)||got!=value)die("task storage lookup");
 int wrong=open("/dev/null",O_RDONLY);if(wrong<0)die("open /dev/null");
 a.key=PTR(&wrong);errno=0;
 if(bpf(BPF_MAP_LOOKUP_ELEM,&a)!=-1||errno!=EINVAL)die("non-pidfd must fail EINVAL");
 close(wrong);
 close(pidfd);a.key=PTR(&pidfd);errno=0;
 if(bpf(BPF_MAP_LOOKUP_ELEM,&a)!=-1||errno!=EBADF)die("closed pidfd must fail EBADF");
 pid_t child=fork();if(child<0)die("fork");if(!child)_exit(0);
 pidfd=syscall(__NR_pidfd_open,child,0);if(pidfd<0)die("child pidfd_open");
 if(waitpid(child,NULL,0)!=child)die("waitpid");
 a.key=PTR(&pidfd);errno=0;
 if(bpf(BPF_MAP_LOOKUP_ELEM,&a)!=-1||errno!=ESRCH)die("reaped task must fail ESRCH");
 close(pidfd);close(map);puts("PASS: task storage real/invalid/closed/exited pidfd paths");
}
int main(void)
{
 struct utsname u;if(uname(&u))die("uname");
 printf("Running kernel: %s %s\n",u.release,u.machine);
 if(strncmp(u.release,"4.14.357-electro",16)) {
  fputs("SKIP: boot the upgraded Electro image first; host kernel tests do not validate it\n",stderr);return 4;
 }
 struct rlimit limit={RLIM_INFINITY,RLIM_INFINITY};
 if(setrlimit(RLIMIT_MEMLOCK,&limit))perror("warning: raising memlock limit");
 instructions();task_storage();
 puts("PASS: basic device smoke only; async timers, hotplug/nohz, networking and teardown stress still required");
 return 0;
}
