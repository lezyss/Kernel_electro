/* SPDX-License-Identifier: GPL-2.0 */
#ifndef CLONE3_SET_TID_COUNTS_H
#define CLONE3_SET_TID_COUNTS_H

#include <errno.h>
#include <limits.h>
#include <poll.h>
#include <stdio.h>
#include <unistd.h>
#include "../kselftest.h"

#ifndef ARRAY_SIZE
#define ARRAY_SIZE(array) (sizeof(array) / sizeof((array)[0]))
#endif

/* Transport child-only deltas, never inherited parent counts or exit bytes. */
static inline int clone3_count_total(const struct ksft_count *counts,
				     unsigned int expected)
{
	unsigned long long total = 0;

	total += counts->ksft_pass;
	total += counts->ksft_fail;
	total += counts->ksft_xfail;
	total += counts->ksft_xpass;
	total += counts->ksft_xskip;
	total += counts->ksft_error;
	return total == expected ? 0 : -EINVAL;
}

static inline int clone3_count_delta(const struct ksft_count *now,
				     const struct ksft_count *before,
				     struct ksft_count *delta,
				     unsigned int expected)
{
	const unsigned int values[] = {
		now->ksft_pass,
		now->ksft_fail,
		now->ksft_xfail,
		now->ksft_xpass,
		now->ksft_xskip,
		now->ksft_error
	};
	const unsigned int baseline[] = {
		before->ksft_pass,
		before->ksft_fail,
		before->ksft_xfail,
		before->ksft_xpass,
		before->ksft_xskip,
		before->ksft_error
	};
	unsigned int *child_values[] = {
		&delta->ksft_pass,
		&delta->ksft_fail,
		&delta->ksft_xfail,
		&delta->ksft_xpass,
		&delta->ksft_xskip,
		&delta->ksft_error
	};
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(values); i++) {
		if (values[i] < baseline[i])
			return -EINVAL;
		*child_values[i] = values[i] - baseline[i];
	}
	return clone3_count_total(delta, expected);
}

static inline int clone3_count_merge(struct ksft_count *parent,
				     const struct ksft_count *delta,
				     unsigned int expected)
{
	const unsigned int values[] = {
		delta->ksft_pass,
		delta->ksft_fail,
		delta->ksft_xfail,
		delta->ksft_xpass,
		delta->ksft_xskip,
		delta->ksft_error
	};
	unsigned int *parent_values[] = {
		&parent->ksft_pass,
		&parent->ksft_fail,
		&parent->ksft_xfail,
		&parent->ksft_xpass,
		&parent->ksft_xskip,
		&parent->ksft_error
	};
	unsigned int i;

	if (clone3_count_total(delta, expected))
		return -EINVAL;
	/* Validate every addition before mutating any inherited parent result. */
	for (i = 0; i < ARRAY_SIZE(values); i++) {
		if (values[i] > UINT_MAX - *parent_values[i])
			return -EOVERFLOW;
	}
	for (i = 0; i < ARRAY_SIZE(values); i++)
		*parent_values[i] += values[i];
	return 0;
}

static inline int clone3_count_write(int fd, const struct ksft_count *delta)
{
	ssize_t size;

	/* The fixed-size report fits in PIPE_BUF: one atomic pipe write. */
	_Static_assert(sizeof(*delta) <= PIPE_BUF, "counter report too large");
	do {
		size = write(fd, delta, sizeof(*delta));
	} while (size < 0 && errno == EINTR);
	return size == sizeof(*delta) ? 0 : -EIO;
}

static inline int clone3_count_read(int fd, struct ksft_count *delta)
{
	struct pollfd report = { .fd = fd, .events = POLLIN };
	ssize_t size;
	int ready;

	/* Called after waitpid: do not hang if a child exited without a report. */
	do {
		ready = poll(&report, 1, 0);
	} while (ready < 0 && errno == EINTR);
	if (ready <= 0 || !(report.revents & POLLIN))
		return -EIO;
	do {
		size = read(fd, delta, sizeof(*delta));
	} while (size < 0 && errno == EINTR);
	return size == sizeof(*delta) ? 0 : -EIO;
}

#endif /* CLONE3_SET_TID_COUNTS_H */
