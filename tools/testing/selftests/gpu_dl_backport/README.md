# KGSL IRQ locking and DEADLINE/cpuset checks

Run on a Linux host with Python 3 and GCC/Clang plus its sanitizer runtimes:

```sh
python3 tools/testing/selftests/gpu_dl_backport/test_backport.py --cc cc
python3 tools/testing/selftests/gpu_dl_backport/test_backport.py --cc cc \
    --asan --self-test-negatives
```

All generated files go into a temporary directory outside the source tree.
The runner verifies UBSan with an overflow probe and, when requested, ASan with
an actual heap-use-after-free probe. Assertions remain enabled. Unused shim
parameters are allowed; the unchanged legacy `__dl_overflow()` helper alone
has its inherited unsigned-versus-minus-one warning suppressed.

## Actual source coverage

The runner extracts the current functions, rather than a reimplementation:

- `kgsl_syncsource_cleanup()`, `kgsl_ioctl_syncsource_create_fence()`, and
  `kgsl_syncsource_signal()` from `drivers/gpu/msm/kgsl_sync.c`.
- SMP `dl_bw_of()`, `dl_bw_cpus()`, `dl_task_can_attach()`, and the non-SMP
  `dl_bw_cpus()` fallback from `kernel/sched/deadline.c`.
- `task_can_attach()` from `kernel/sched/core.c` and `cpuset_can_attach()`
  from `kernel/cgroup/cpuset.c`.
- Existing `__dl_add()` and `__dl_overflow()` from `kernel/sched/sched.h`.

The model mocks platform context, CPU masks, locks, RCU, list primitives,
fences, allocation and file descriptors. It is not a running-kernel selftest.

## Checks

- All 65,536 pairs of eight-CPU domain/active masks produce the legacy
  intersection count. The fully-active fast path does not enter the CPU loop.
- Configured-empty cgroup-v2 cpusets pass the inherited effective CPU mask;
  legacy v1 CPU/node emptiness checks and security checks are retained.
- PF_NO_SETAFFINITY is rejected for both normal and DEADLINE tasks.
- Invalid/no-active destination CPUs are rejected before per-CPU access.
- Simulated loss of the last active domain CPU between selection and admission
  rejects the request before division/accounting, including unlimited bandwidth.
- Admission success, exact capacity fit, overflow, unlimited bandwidth,
  same-domain and non-DEADLINE paths preserve the expected reservation behavior.
  RCU, lock and incoming IRQ state are balanced on tested exits.
- KGSL create/signal/cleanup critical sections require IRQs disabled and restore
  both possible incoming IRQ states. The fence-list behavior and lookup,
  allocation, sync-file and file-descriptor failures are exercised.
- Seven negative controls restore unsafe GPU locking, count inactive CPUs,
  pass configured rather than effective masks, lose PF_NO_SETAFFINITY, omit
  either destination guard, or reserve on overflow. Each must fail.

See `Documentation/dev-tools/gpu-dl-backports.rst` for scope and provenance.
Host sanitizer/model success does not replace an ARM64 production-toolchain
build, real lockdep/interrupt testing, CPU-hotplug/cpuset stress, or GPU/device
validation. No battery, frame-rate, touch-latency or throughput gain is claimed.
