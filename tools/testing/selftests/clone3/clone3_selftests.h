/* SPDX-License-Identifier: GPL-2.0 */

#ifndef _CLONE3_SELFTESTS_H
#define _CLONE3_SELFTESTS_H

#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <syscall.h>
#include <linux/types.h>
#include "../kselftest.h"
#include <linux/capability.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>

#ifndef ARRAY_SIZE
#define ARRAY_SIZE(array) (sizeof(array) / sizeof((array)[0]))
#endif

#define ptr_to_u64(ptr) ((__u64)((uintptr_t)(ptr)))

#ifndef __NR_clone3
#define __NR_clone3 -1
#endif

#ifndef CLONE_ARGS_SIZE_VER0
struct clone_args {
	__aligned_u64 flags;
	__aligned_u64 pidfd;
	__aligned_u64 child_tid;
	__aligned_u64 parent_tid;
	__aligned_u64 exit_signal;
	__aligned_u64 stack;
	__aligned_u64 stack_size;
	__aligned_u64 tls;
	__aligned_u64 set_tid;
	__aligned_u64 set_tid_size;
};
#endif

static pid_t sys_clone3(struct clone_args *args, size_t size)
{
	return syscall(__NR_clone3, args, size);
}


/* Compatibility with this tree's older kselftest.h. */
static unsigned int ksft_plan;

static inline void ksft_set_plan(unsigned int plan)
{
	ksft_plan = plan;
}

static inline void test_clone3_supported(void)
{
	/* A zero-sized argument must fail before creating a process. */
	if (sys_clone3(NULL, 0) != -1 || errno != EINVAL) {
		if (errno == ENOSYS || errno == EPERM)
			ksft_exit_skip("clone3 unavailable or blocked by policy\n");
		ksft_exit_fail_msg("unexpected clone3 probe result\n");
	}
}

static inline int clone3_has_capability(unsigned int cap)
{
	struct __user_cap_header_struct hdr = {
		.version = _LINUX_CAPABILITY_VERSION_3,
	};
	struct __user_cap_data_struct data[2] = {};

	if (syscall(SYS_capget, &hdr, data))
		return 0;
	return !!(data[cap / 32].effective & (1U << (cap % 32)));
}

#endif /* _CLONE3_SELFTESTS_H */
