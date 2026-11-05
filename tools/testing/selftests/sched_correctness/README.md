# Scheduler correctness backport checks

Run from the kernel tree:

```sh
python3 tools/testing/selftests/sched_correctness/test_backport.py --cc gcc \
    --self-test-negatives
python3 tools/testing/selftests/sched_correctness/test_backport.py --cc gcc \
    --asan --self-test-negatives
```

Requires Python 3, a Linux host compiler and the requested sanitizer runtimes.
The runner first verifies UBSan traps a signed overflow; ASan mode also verifies
an actual heap overflow is detected. Generated files stay in a temporary
directory, not the source tree. Assertions remain enabled.

The runner extracts the current implementations of:

- `group_smaller_min_cpu_capacity()` / `group_smaller_max_cpu_capacity()`;
- the entire `find_busiest_queue()` function;
- SMP/UP `task_cpu()`, `__set_task_cpu()`, `task_on_rq_migrating()`;
- only the migrating-store/dequeue prefix of `move_queued_task()`;
- only the idle-loop entry from IRQ disable through `arch_cpu_idle_enter()`;
- the real tick protected-wrapper bodies, used for the negative control.

Each of six configurations tests:

- 4,198,401 capacity pairs (0..2048 squared), plus 100 boundary combinations
  including `ULONG_MAX`, independently varying minimum/maximum capacities;
- targeted stale-load and stale-misfit queues with no runnable CFS tasks,
  all-CFS-empty groups, and 50,000 deterministic random queue-selection cases
  against a separate division-based oracle; group/allowed masks, NUMA classes,
  active balance, source capacity, task count and reduced capacity are varied;
- instrumented READ_ONCE/WRITE_ONCE use and existing write-barrier placement,
  storage-layout selection, wake-CPU assignment and migrating-before-dequeue;
- 200 online/offline idle entries, checking IRQs at the offline check, stop-tick,
  dead-report and architecture entry boundaries. A mocked non-returning dead
  callback exits via longjmp, rather than falling through to online idle.

The matrix covers both task-CPU layouts with SMP, NO_HZ_COMMON on/off, and two
additional UP builds. Ten negative controls reintroduce the two margins,
remove the CPU/migrating access markings or write barrier, delay IRQ disable,
use the protected tick wrapper, or remove the empty-CFS guard. Each must fail a
runtime assertion, not merely fail to compile. In particular, the protected
wrapper negative control demonstrates the donor idle patch is incomplete.

## Limits

These are extracted-source host tests with mocked kernel context, **not** a
kernel build, LKMM litmus test, concurrency proof, CPU-hotplug stress test or
performance benchmark. Instrumentation verifies use/order of access primitives;
it does not implement real READ_ONCE/WRITE_ONCE or prove ARM memory ordering.
The full idle loop and full migration function are not executed. Device boot,
CPU-hotplug/RCU/lockdep stress and real scheduler workload testing remain needed.

See `Documentation/scheduler/sched-correctness-backport.rst` for scope,
provenance, preservation checks and the incremental production patch.
