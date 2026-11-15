/* SPDX-License-Identifier: GPL-2.0 */
/* Actual selected SUSFS sucompat functions with host primitives, not exec. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <errno.h>
#undef __always_inline
#define __always_inline inline
#define SUCOMPAT_HOOK_TYPE static int
#define __user
#define CONFIG_64BIT 1
#define CONFIG_KSU_SUSFS 1
#define CONFIG_KSU_TAMPER_SYSCALL_TABLE 1
#define CONFIG_KSU_ENABLE_FULL_UID_CHECKS 1
#define SU_PATH "/system/bin/su"
#define constexpr const
#define static_assert _Static_assert
#define likely(x) (x)
#define unlikely(x) (x)
#define assume(x) ((void)0)
#define assume_dereferenceable(p,n) ((void)0)
#define TIF_KSU_MANAGED 0
#define untagged_addr(p) (p)
#define pr_info(...) ((void)0)
static bool allowed, managed, seccomp, compat, fault, ksud_missing;
static int escape_error, installs, calls, events, preinit_calls, adb_calls;
static bool test_thread_flag(int f) { (void)f;return managed; }
static bool ksu_is_seccomp_enabled(void) { return seccomp; }
static bool ksu_is_allow_uid_for_current(uid_t u) { (void)u;return allowed; }
struct uid { uid_t val; };
static bool escalated;
static struct uid current_uid(void) { return (struct uid){escalated ? 0:10001}; }
#define GLOBAL_ROOT_UID ((struct uid){0})
#define uid_eq(a,b) ((a).val==(b).val)
static bool is_ksu_domain(void) { return escalated; }
#define get_user(v,p) (fault ? -EFAULT : (memcpy(&(v),(p),sizeof(v)),0))
static void write_sulog(char c) { (void)c; }
static int escape_with_root_profile(void) { if(!escape_error)escalated=true;return escape_error; }
static bool is_compat_task(void) { return compat; }
static void ksu_install_su_fd(void) { installs++; }
struct path { int dummy; };
static int kern_path(const char *s,int flags,struct path *p)
{ (void)s;(void)flags;(void)p;return ksud_missing ? -ENOENT:0; }
static void path_put(struct path *p) { (void)p; }
static char *ksud_user_path(void) { return "/system/bin/ksud"; }
static char *sh_user_path(void) { return "/system/bin/sh"; }
static void ksu_sulog_emit_sucompat_post(const char *k,const char *u,void ***argv)
{ (void)k;(void)u;assert(argv && !*argv);events++; }
static void ksu_adb_root_execve(void **k,const char **u,void *e)
{ (void)k;(void)u;(void)e;adb_calls++; }
static void ksu_preinit_execve(void **k,const char **u,void *a,void *e)
{ (void)k;(void)u;(void)a;(void)e;preinit_calls++; }
/* ACTUAL */
int main(void)
{
 unsigned cases=0;
 const char su[16]=SU_PATH, other[16]="/system/bin/id";
 for(int a=0;a<2;a++)for(int m=0;m<2;m++)for(int s=0;s<2;s++)
 for(int c=0;c<2;c++)for(int f=0;f<2;f++)for(int miss=0;miss<2;miss++)
 for(int bad=0;bad<2;bad++)for(int err=0;err<2;err++)for(int name=0;name<2;name++)for(int at=0;at<2;at++) {
  allowed=a;managed=m;seccomp=s;compat=c;fault=f;ksud_missing=miss;escape_error=bad ? -EPERM:0;
  installs=calls=events=preinit_calls=adb_calls=0;escalated=false;
  const char *filename=name ? su:other;
  bool session=at ? ksu_handle_sys_execveat(NULL,&filename,NULL,NULL,NULL):ksu_handle_sys_execve(&filename,NULL,NULL);
  bool want=(a||m) && !s && !f && name && !bad;
  assert(session==want);
  assert(adb_calls==1 && preinit_calls==1);
  calls++;long result=err ? -EIO:0; /* original syscall, exactly once */
  assert(ksu_susfs_post_execve(session,result)==result);
  assert(calls==1 && installs==(want && !err));
  if(want)assert(!strcmp(filename,miss ? "/system/bin/sh":"/system/bin/ksud"));
  char context[]="u:r:test:s0", value[sizeof(context)];memcpy(value,context,sizeof(value));
  assert(ksu_hide_setprocattr_inline("current",value,sizeof(value))==0);
  assert(!memcmp(value,context,sizeof(value)));
  assert(ksu_hide_setxattr_inline("security.selinux",value,sizeof(value))==0);
  assert(!memcmp(value,context,sizeof(value)));
  cases++;
 }
 assert(!is_su_allowed(NULL));
 puts("PASS: current selected auth/exec/post-success-fd and SUSFS no-mutation handlers, 1024 host cases");
 assert(cases==1024);
 return 0;
}
