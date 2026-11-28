# Cambyses v0.7.2 backport checks

Run from the kernel tree with Python 3 and a host C compiler that supports
UBSan (Clang or GCC):

```sh
python3 tools/testing/selftests/cambyses/test_backport.py --cc clang
# GCC is supported too; the runner selects the compiler's UBSan trap option.
python3 tools/testing/selftests/cambyses/test_backport.py --cc gcc
python3 tools/testing/selftests/cambyses/test_backport.py --cc gcc \
    --asan --self-test-negatives --output /tmp/cambyses-check
```

The ASan run also requires a working compiler ASan runtime and `nm` from
binutils. Temporary output is removed unless `--output` is supplied. Reusing an
output directory is supported. Build artifacts stay outside the source tree.

## What is tested

The runner extracts the current `detach_tasks()`, `lb_can_concede()`,
`lb_cost_fits()`, concession structure and LBF flags from `kernel/sched/fair.c`.
It uses the real `include/linux/list.h`, including the list rotation helper,
with small userspace shims. It verifies that `LB_ROTATE_BLOCK` and
`LB_CONCEDE_CHEAPEST` are enabled by default. No alternate Cambyses
implementation is substituted. `legacy_detach.c` is the frozen pre-Cambyses
function used for differential testing; only its inherited sign-comparison
warning is suppressed.

Each PREEMPT/WALT combination runs:

- Empty/singleton lists, every rotation pivot through 12 entries, partial and
  complete scans, scan-quantum resumption, and list-operation checks.
- Idle-only cheapest-candidate concession, the strict `cost < 2 * imbalance`
  bound, cancellation when an in-budget task is admitted, the local two-task
  exception, and safe rejection of `2 * imbalance` and `ULONG_MAX` candidates.
- Feature-off, busy-destination, already-moved, and affinity-redirected
  fallback behavior; the native 5 ms scan guard, LB_MIN, task-migration filters,
  NEWIDLE/PREEMPT handling, and vendor relaxed redo.
- Mock WALT lock-drop dequeue/free churn, checking that neither cursors nor
  saved candidates survive detach paths that release `src_rq->lock`.
- 3,000 deterministic feature-off comparisons against the frozen legacy loop:
  migration order, scan trace, residual list order, imbalance, loop/break state,
  statistics and legacy-visible flags. The internal `LBF_MOVED` bit is masked.
- 12,000 randomized mixed-feature cases checking list structure, migration
  filters and accounting (four feature combinations for each of 3,000 seeds).

The optional 16 negative controls mutate one safety property at a time: list
rotation, concession existence, stale cursor handling, pre-detach flushing,
sticky progress, migration filters, timeout handling, the two-task exception,
the 2x bound, idle-only eligibility, redirect and prior-migration guards, the
feature switch, LB_MIN and the zero-load floor. Every mutant must fail. With
ASan enabled, the stale-cursor mutant exercises the lock-drop model's
use-after-free check.

## Limits

These are userspace algorithm/list checks with mocked scheduler context, not
running-kernel kselftests or a concurrency/latency benchmark. They do not
execute the real `can_migrate_task()` or prove lockdep correctness. The
4.14-specific adaptations and recorded build checks are documented in
`Documentation/scheduler/cambyses-backport.rst`. A full production-toolchain
build, boot, scheduler stress and device performance testing remain necessary.
