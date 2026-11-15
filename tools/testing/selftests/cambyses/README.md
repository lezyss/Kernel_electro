# Corrected Cambyses backport checks

Run from the kernel tree with Python 3 and a Linux host Clang installation:

```sh
python3 tools/testing/selftests/cambyses/test_backport.py --cc clang
python3 tools/testing/selftests/cambyses/test_backport.py --cc clang \
    --asan --self-test-negatives --output /tmp/cambyses-check
```

The ASan run also requires `pyelftools` (`python3 -m pip install pyelftools`)
and a working Clang ASan runtime. The runner checks for ASan symbols when
requested, and runs a signed-overflow probe that must trap under UBSan.
Temporary output is removed unless `--output` is supplied. Reusing an output
directory is supported. Build artifacts must stay outside the source tree.

## What is tested

The runner extracts the **current** `detach_tasks()`, load-budget helper,
concession structure, and LBF flags from `kernel/sched/fair.c`. It uses the
actual `include/linux/list.h`, including the new rotation helper, with small
userspace header shims. Both new feature defaults are checked in
`kernel/sched/features.h`. No alternate implementation of the new balancer is
substituted. `legacy_detach.c` is the frozen pre-Cambyses function, renamed for
differential testing; only its inherited sign-comparison warning is suppressed.

Each of four PREEMPT/WALT combinations runs:

- Empty/singular lists and every rotation pivot for lists up to 12 entries.
- Partial/full reject scans, list-operation counts, scan-quantum resumption,
  and a rejected block immediately before a successful migration.
- Whole-budget fit, cheapest overshoot, sticky progress over retries,
  `ULONG_MAX` fallback accounting, and the local two-task exception.
- Zero-load floor, LB_MIN, mocked pinned/running/hot/throttled tasks,
  rq-clock timeout, NEWIDLE/PREEMPT, and vendor relaxed redo.
- Mock WALT lock-drop dequeue/free churn, checking refreshed cursors.
- 3,000 deterministic randomized **feature-off** comparisons against the
  frozen legacy function: migration order, scan trace, residual list order,
  imbalance, loop/break state, statistics and legacy-visible flags. The new
  internal LBF_MOVED bit is masked for this comparison.
- 12,000 randomized mixed-feature cases checking list structure, migration
  filters and accounting (four feature settings for each of 3,000 seeds).

The optional 12 negative controls deliberately introduce a single-node rather
than sentinel rotation, remove the concession, retain a stale WALT cursor,
remove pre-detach rotation, lose sticky progress, bypass migration filters,
allow a post-timeout concession, lose the two-task exception, overflow fallback
accounting, remove the timeout, bypass LB_MIN, or lose the zero-load floor.
Every mutant must fail. The stale-cursor mutant exposes an ASan heap-use-after-
free in the lock-drop model.

## Limits

These are userspace algorithm/list checks with **mocked** scheduler context,
not running-kernel kselftests or a concurrency/latency benchmark. They do not
execute the real `can_migrate_task()` or prove actual lockdep correctness.
Separate real ARM64 scheduler object compilation/partial linking is recorded
in `Documentation/scheduler/cambyses-backport.rst`. Full production-toolchain
build, boot, scheduler stress and device performance testing remain necessary.
