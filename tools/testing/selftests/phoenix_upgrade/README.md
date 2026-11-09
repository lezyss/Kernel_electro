# Phoenix implementation regressions — phases 01–03

Run from the repository root:

```sh
python3 tools/testing/selftests/phoenix_upgrade/test_phase01.py --self-test-negatives
python3 tools/testing/selftests/phoenix_upgrade/test_phase02.py --self-test-negatives
python3 tools/testing/selftests/phoenix_upgrade/test_phase03.py --self-test-negatives
```

Requires Python 3 and host GCC with UBSan. Generated C files and binaries live
only in temporary directories. Phase01 uses only mocks. Phase02 performs one ordinary host fork/wait and
bounded pipe I/O to exercise counter transport; it never invokes clone3, creates
a PID namespace, changes capabilities, installs a kernel or operates a device.

Checks:

- Actual RR interval helper and syscall wrappers are extracted from
  `kernel/sched/core.c`. Native-only and compat-enabled host fixtures check
  early invalid-PID/not-found/permission failures without copying to userspace,
  success, bad output pointer, PID zero and an absent RR callback. Lookup,
  locking, time conversion and user copies are mocked.
- Actual `alloc_pid` is extracted from `kernel/pid.c`. Sixteen scenarios cover
  successful/partial/automatic PID requests, late proc/namespace failures,
  earlier validation/permission/IDR/allocation failures and own-namespace cleanup.
  Locks, allocator, IDR, namespaces, proc and capability checks are mocked.
- Actual clone3 selftest `call_clone3` is extracted. Five outcomes cover success,
  syscall/wait failure, unsuccessful child and signaled child. All process
  operations are replaced with host shims; no real syscall or child is created.
- Source guards check pidfd installation after both locks are released, existing
  failure cleanup and MGLRU-before-wakeup ordering, stdio flush ordering and
  nested-test failure propagation. Phase02 explicitly supersedes the old255
  sentinel with a complete six-counter child-only delta pipe; the updated guard
  requires report/write/read/merge and abnormal-exit checks, with exact caller
  counts. Run both phase suites.
- Five deliberately regressed fixtures must be rejected: pidfd under locks,
  unconditional native/compat RR user copy, missing PID errno reset, and the old
  clone3 selftest success return value.

This is bounded extracted-source/control-flow validation, **not** a production
AOSP Clang kernel build, scheduler/RCU/SMP/lockdep/race proof, real SELinux policy
validation, boot/device test or performance measurement.

The phase overlay and provenance live at:
`Documentation/dev-tools/phoenix-review/implementation/phase-01.{json,diff}`.
Historical BPF source seals remain unchanged; the explicit overlay records the
new fork/pid hashes rather than pretending the old seals describe edited files.

## Phase02 (corrected adaptations)

- Extract actual fcntl owner encoder/decoder/clear and SIGIO/SIGURG dispatch
  bodies. Mocked task lookup and lock checks cover live/dead/absent owners,
  TID/TGID/process groups, bad pointers/PIDs/types, forced/nonforced ownership
  and lock balance. Delivery/permission hooks are mocked; this is **not** proof
  of RCU races, exec/exit races, LSM denial behavior or realtime queue fallback.
- Compile the actual clone3 counter header with GCC/UBSan.75 assertions cover
  inherited failures, all six counters, child-only subtraction, >255 results,
  real pipe/fork transport, short/absent reports, underflow and overflow with
  no partial parent mutation. Source checks enforce six nested tests, plan29,
  PID43 retry after failed ancestor allocation and abnormal-exit handling.
- Compile both actual SELinux genfs predicates:56 filesystem/policycap cases.
  FunctionFS is unconditional (no new policycap array/ABI entry); securityfs
  becomes genfs-labeled, not specially setxattr-capable. These checks cannot
  validate an Android ROM's enforcing USB/ADB policy or multiple mounts.
-512 extracted ARM/Xtensa TLS assignments verify explicit argument selection
  and no override without CLONE_SETTLS. Check all four currently clone3-capable
  architecture selectors/backends and preprocess the actual missing-TLS guard.
  Xtensa's real conversion is required before the guard (upstream c346b94f8c5d).
- Compile six arities of the actual generic compat macro and callable aliases
  using long-argument host fixtures. x86 declarations are retained. This is not
  an ARM32 compat ABI execution test.
- Eight negative fixtures reject either missing NULL guard, wrong owner mapping,
  overwriting inherited parent counts, including inherited child counts, and
  losing overflow rejection, legacy TLS selection and policycap-gating FunctionFS. Phase01's five negative controls also remain.

Phase02 replay/chain/provenance:
`Documentation/dev-tools/phoenix-review/implementation/phase-02.{json,diff}`.
Exact production AOSP Clang builds, runtime/locking/namespace and enforcing-ROM
validation remain mandatory before any deployment safety claim.

## Phase03 (remaining115 approved items)

-97 frozen native/compat syscall contracts from the pre-phase03 signatures.
  Actual current wrapper bodies are compiled with distinct argument values and
  negative helper results, detecting argument-order/return propagation regressions.
-1920 extracted multiprocess signal collector and private/shared queue cases,
  including TID/TGID/PGRP/session/broadcast types, STOP/CONT coalescing, two
  simultaneous forks and high signal bits. This is not an RCU/SMP/race test.
- Eight actual compat sigset variants (LE/BE,1–4 native words),100 high-bit
  roundtrips each plus uaccess failure tests. Unsigned shifts fix donor signed
  overflow for high signal bits; UBSan rejects the old signed-cast fixture.
-218 distinct weak fallbacks including clone3, BPF, legacy sys32_quotactl and
  ppc_rtas; original -ENOSYS body retained. Fork source guards verify collector
  cleanup on success/error, fatal-signal abort, child group-stop membership,
  schedule-tail recalculation, timer RCU lifetime, pidfd/BPF/MGLRU ordering and
  preservation of the actual kernel_clone_args interface.
- Eight deliberate regressions (including malformed native ARM clobber grammar): forwarding-argument swap, collecting TGID as
  multiprocess, lost STOP/CONT coalescing, reversed private/shared queue,
  signed high-half shift, missing fork collector cleanup and lost fatal abort.
- Phase02's int/group bridge assertion is explicitly superseded by the new
  typed interface check; the old three-call bridge remains checked only for
  a pre-phase03 tree. No other phase01/02 checks are relaxed.

SUSFS's immutable32-file import is not resealed: an explicit6-file syscall
refactor overlay extends provenance checking. Its18 negative controls include
all13 existing tests plus missing overlay/patch/base/scope/path tampering.
See `Documentation/dev-tools/phoenix-review/implementation/phase-03.json` and
`susfs-syscall-overlay.{json,diff}`. Runtime/ABI/concurrency/device validation is
still separate from these bounded host models and target compilation.

Native ARM follow-up: the real TLS backend object compiled under r614150.
Compiling native ARM fork additionally exposed a pre-existing malformed optional
asm-clobber list in `arch/arm/include/asm/uaccess.h`. The comma-prefixed IP macro
is now placed after the always-present LR/CC clobbers. Syntax controls exercise
built-in and module-long-call variants; ARM64 uses a different header. This is
an incidental prerequisite fix, not a new Phoenix review ID or production-config
change. Xtensa remains source/host-audited, not target-compiled.

Phase03 eventfd follow-up:106 extracted creation/read/lifetime cases and two
negative controls cover semaphore/counter consumption, copyout faults, waits,
signals, invalid flags, OOM and fd exhaustion. Legacy GPL `eventfd_ctx_read` and
`eventfd_ctx_get` exports remain for unaudited vendor-module ABI compatibility;
native folded paths do not call them. PHX014 intentionally changes resource-error
precedence (flags/context allocation before fd reservation). Neither these mocks
nor source checks replace live eventfd/poll/locking tests. Native ARM compile
checks also required UAL `sbcscc` spelling in its existing range-check asm.

Final ABI adaptation: retain `sys_close` export and module-only legacy
`iov_shorten`/`sigset_from_compat` APIs, alongside the converted native paths.
PHX011 is scoped to removing the helper from non-module builds/in-tree API use,
not deleting unaudited vendor-module ABI. Legacy sigset conversion keeps its
original kernel-pointer semantics with unsigned high-half shifts.160 iovec and
800 high-bit legacy sigset cases pass; an export-removal mutant is rejected.
