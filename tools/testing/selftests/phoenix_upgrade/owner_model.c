/* SPDX-License-Identifier: GPL-2.0 */
/* Actual fcntl owner/dispatch bodies, mocked task/RCU/LSM delivery boundary. */
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#define __user
#define F_OWNER_TID 0
#define F_OWNER_PID 1
#define F_OWNER_PGRP 2
#define WARN_ON(x) assert(!(x))
enum pid_type { PIDTYPE_PID, PIDTYPE_TGID, PIDTYPE_PGID, PIDTYPE_SID, PIDTYPE_MAX };
struct task_struct { int id; } tasks[] = { {1}, {2} };
struct pid { int nr, live, n; } live = { 42, 1, 2 };
struct fown_struct { struct pid *pid; enum pid_type pid_type; int lock; };
struct file { struct fown_struct f_owner; };
struct f_owner_ex { int type, pid; };
static int tasklist_lock, rcu, calls, fault;
static enum pid_type last;
static void read_lock(int *lock) { assert(!*lock); ++*lock; }
static void read_unlock(int *lock) { assert(*lock == 1); --*lock; }
static void rcu_read_lock(void) { assert(!rcu); ++rcu; }
static void rcu_read_unlock(void) { assert(rcu == 1); --rcu; }
static struct pid *find_vpid(int nr) { assert(rcu); return nr == 42 ? &live : NULL; }
static struct task_struct *pid_task(struct pid *pid, enum pid_type type)
{
	assert(rcu && type == PIDTYPE_PID);
	return pid->live ? &tasks[0] : NULL;
}
static void __f_setown(struct file *f, struct pid *pid, enum pid_type type, int force)
{
	if (force || !f->f_owner.pid) { f->f_owner.pid = pid; f->f_owner.pid_type = type; }
}
static pid_t pid_vnr(struct pid *p) { return p ? p->nr : 0; }
static int copy_from_user(void *a, const void *b, size_t n)
{ if (fault) return 1; memcpy(a, b, n); return 0; }
static int copy_to_user(void *a, const void *b, size_t n)
{ return copy_from_user(a, b, n); }
static void dispatch(struct task_struct *p, struct fown_struct *f, enum pid_type type)
{
	assert(p && p->id && f->lock == 1);
	assert(type == f->pid_type);
	assert(type <= PIDTYPE_TGID ? rcu == 1 && !tasklist_lock : !rcu && tasklist_lock == 1);
	calls++; last = type;
}
static void send_sigio_to_task(struct task_struct *p, struct fown_struct *f,
			       int fd, int band, enum pid_type type)
{ assert(fd == 7 && band == 3); dispatch(p, f, type); }
static void send_sigurg_to_task(struct task_struct *p, struct fown_struct *f, enum pid_type type)
{ dispatch(p, f, type); }
#define do_each_pid_task(pid, type, p) \
	do { assert(type == PIDTYPE_PGID); for (int i = 0; i < (pid)->n; i++) { p = &tasks[i];
#define while_each_pid_task(pid, type, p) } } while (0)
/* EXTRACTED */
int main(void)
{
	struct file f = {0};
	struct f_owner_ex in, out;

	for (int type = 0; type < 3; type++) {
		in = (struct f_owner_ex){ type, 42 };
		assert(f_setown_ex(&f, (unsigned long)&in) == 0);
		assert(f.f_owner.pid_type == (enum pid_type)type);
		assert(f_getown_ex(&f, (unsigned long)&out) == 0);
		assert(out.type == type && out.pid == 42);
		for (int dead = 0; dead < 2; dead++) {
			live.live = !dead;
			calls = 0; send_sigio(&f.f_owner, 7, 3);
			assert(calls == (type == PIDTYPE_PGID ? 2 : !dead));
			if (calls) assert(last == (enum pid_type)type);
			calls = 0; assert(send_sigurg(&f.f_owner) == 1);
			assert(calls == (type == PIDTYPE_PGID ? 2 : !dead));
			assert(!rcu && !tasklist_lock && !f.f_owner.lock);
		}
	}
	in = (struct f_owner_ex){ F_OWNER_PID, 999 };
	assert(f_setown_ex(&f, (unsigned long)&in) == -ESRCH);
	in.type = 99; assert(f_setown_ex(&f, (unsigned long)&in) == -EINVAL);
	fault = 1; assert(f_setown_ex(&f, (unsigned long)&in) == -EFAULT);
	assert(f_getown_ex(&f, (unsigned long)&out) == -EFAULT); fault = 0;
	assert(f_setown(&f, INT_MIN, 1) == -EINVAL);
	assert(f_setown(&f, 999, 1) == -ESRCH);
	assert(f_setown(&f, 42, 1) == 0 && f.f_owner.pid_type == PIDTYPE_TGID);
	assert(f_getown(&f) == 42);
	assert(f_setown(&f, -42, 1) == 0 && f.f_owner.pid_type == PIDTYPE_PGID);
	assert(f_getown(&f) == -42);
	assert(f_setown(&f, 42, 0) == 0 && f.f_owner.pid_type == PIDTYPE_PGID);
	f_delown(&f); assert(!f.f_owner.pid && f.f_owner.pid_type == PIDTYPE_TGID);
	calls = 0; send_sigio(&f.f_owner, 7, 3);
	assert(send_sigurg(&f.f_owner) == 0 && !calls);
	assert(!rcu && !tasklist_lock && !f.f_owner.lock);
	puts("PASS: owner TID/TGID/PGRP codec, live/dead/absent dispatch, lock balance, errors and clear");
}
