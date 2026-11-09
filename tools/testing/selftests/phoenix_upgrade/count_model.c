/* SPDX-License-Identifier: GPL-2.0 */
#include <assert.h>
#include <signal.h>
#include <string.h>
#include <sys/wait.h>
#include "clone3_set_tid_counts.h"
static int checks;
#define CHECK(x) do { checks++; assert(x); } while (0)
int main(void)
{
	struct ksft_count before = {10, 3, 2, 1, 4, 5}, now, delta, parent, saved;
	int fd[2], status;
	pid_t child;

	for (unsigned int failures = 0; failures <= 6; failures++) {
		now = before; now.ksft_pass += 6 - failures; now.ksft_fail += failures;
		CHECK(!clone3_count_delta(&now, &before, &delta, 6));
		parent = before; parent.ksft_error++; saved = parent;
		CHECK(!clone3_count_merge(&parent, &delta, 6));
		CHECK(parent.ksft_pass == saved.ksft_pass + 6 - failures);
		CHECK(parent.ksft_fail == saved.ksft_fail + failures);
		CHECK(parent.ksft_error == saved.ksft_error);
		CHECK(parent.ksft_xfail == before.ksft_xfail && parent.ksft_xpass == before.ksft_xpass && parent.ksft_xskip == before.ksft_xskip);
	}
	/* Distinguish each field so an accidental pointer-table permutation fails. */
	for (int field = 0; field < 6; field++) {
		struct ksft_count expected = {0};
		unsigned int *n[] = {&now.ksft_pass, &now.ksft_fail, &now.ksft_xfail,
			&now.ksft_xpass, &now.ksft_xskip, &now.ksft_error};
		unsigned int *d[] = {&expected.ksft_pass, &expected.ksft_fail,
			&expected.ksft_xfail, &expected.ksft_xpass,
			&expected.ksft_xskip, &expected.ksft_error};
		now = before; *n[field] += 6; *d[field] = 6;
		CHECK(!clone3_count_delta(&now, &before, &delta, 6) && !memcmp(&delta, &expected, sizeof(delta)));
		parent = before;
		CHECK(!clone3_count_merge(&parent, &delta, 6) && !memcmp(&parent, &now, sizeof(now)));
	}
	/* Every field, including skips/expected failures/errors, crosses the pipe. */
	delta = (struct ksft_count){1, 1, 1, 1, 1, 1};
	CHECK(pipe(fd) == 0); child = fork(); CHECK(child >= 0);
	if (!child) { close(fd[0]); int ret = clone3_count_write(fd[1], &delta); close(fd[1]); _exit(ret ? 1 : 0); }
	close(fd[1]); CHECK(waitpid(child, &status, 0) == child);
	CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
	CHECK(!clone3_count_read(fd[0], &now)); close(fd[0]);
	CHECK(!memcmp(&now, &delta, sizeof(now))); parent = before;
	CHECK(!clone3_count_merge(&parent, &now, 6));
	CHECK(parent.ksft_pass == 11 && parent.ksft_fail == 4 && parent.ksft_xfail == 3 && parent.ksft_xpass == 2 && parent.ksft_xskip == 5 && parent.ksft_error == 6);
	/* Detect underflow, invalid totals and late-field overflow without partial merge. */
	now = before; now.ksft_fail--; CHECK(clone3_count_delta(&now, &before, &delta, 6) != 0);
	delta = (struct ksft_count){7, 0, 0, 0, 0, 0}; parent = before; saved = parent;
	CHECK(clone3_count_merge(&parent, &delta, 6) != 0 && !memcmp(&parent, &saved, sizeof(parent)));
	delta = (struct ksft_count){1, 0, 0, 0, 0, 5}; parent = before; parent.ksft_error = UINT_MAX; saved = parent;
	CHECK(clone3_count_merge(&parent, &delta, 6) == -EOVERFLOW && !memcmp(&parent, &saved, sizeof(parent)));
	/* Exit-byte truncation is deliberately irrelevant, including >255 passes. */
	now = before; now.ksft_pass += 300; CHECK(!clone3_count_delta(&now, &before, &delta, 300));
	parent = before; CHECK(!clone3_count_merge(&parent, &delta, 300) && parent.ksft_pass == 310 && parent.ksft_fail == 3);
	CHECK(pipe(fd) == 0); CHECK(clone3_count_write(fd[1], &delta) == 0);
	CHECK(clone3_count_read(fd[0], &now) == 0 && now.ksft_pass == 300); close(fd[0]); close(fd[1]);
	/* Malformed/missing reports fail promptly, even with an inherited writer open. */
	CHECK(pipe(fd) == 0); CHECK(clone3_count_read(fd[0], &now) != 0);
	CHECK(write(fd[1], "x", 1) == 1); CHECK(clone3_count_read(fd[0], &now) != 0);
	close(fd[1]); CHECK(clone3_count_read(fd[0], &now) != 0); close(fd[0]);
	printf("PASS:%d count assertions; inherited failures, six counters, >255, real pipe/fork, malformed/missing and atomic overflow rejection\n", checks);
}
