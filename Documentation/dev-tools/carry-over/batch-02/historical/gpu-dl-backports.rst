Selected KGSL and DEADLINE/cpuset backports
=========================================

Scope
-----
Only the following three recommendations from
``AzyrRuthless/kernel_xiaomi_sm6250`` are included:

* ``71a6c1d01b6f2fcf407c79f252bb8b3d6177e077``: KGSL syncsource IRQ-safe
  locking (Nitheesh Muthuraj / Qualcomm fix).
* ``bc7328a77b6be7591052cb226a029a33ee69d13e``: optimize ``dl_bw_cpus()``
  (Dietmar Eggemann / upstream scheduler change).
* Corrected adaptation of ``ad1345b413fca93af081b5e3be3fa6b85248a8a3``:
  use effective cpuset masks and prevent an out-of-range destination CPU
  (Waiman Long / upstream cpuset fix).

The first two production changes match their donor patches. The third is
adapted to this tree's ``dl_task_can_attach()`` interface, not copied blindly.
``gpu-dl-backports.json`` records hashes and provenance;
``gpu-dl-adaptation.diff`` contains only these changes against the already
modified working tree. Earlier BORE/CASS/Cambyses and cgroup work is not
replaced or reproduced in the adaptation diff.

Changes and preserved behavior
------------------------------
KGSL's syncsource cleanup, fence creation and signaling now take the common
fence lock with ``spin_lock_irqsave()`` and restore the caller's IRQ state on
unlock. Fence operations, references and error paths are otherwise unchanged.
This addresses the possibility of a local interrupt taking the same lock
while a process-context caller holds it. It is not GPU clock/boost tuning.

For DEADLINE bandwidth bookkeeping, a root-domain span wholly contained in
the active CPU mask can use ``cpumask_weight()``. The active/span intersection
walk remains for other cases, and the non-SMP fallback remains one CPU.
This does not implement capacity-aware DEADLINE admission or change CFS/BORE
weights, CASS task placement, or Cambyses balancing.

Cpuset admission now passes ``effective_cpus``, supporting a configured-empty
cgroup-v2 cpuset which inherits its usable CPUs. The existing cgroup-v1 empty
CPU/node checks, security checks and PF_NO_SETAFFINITY rejection are retained.
Parameter names are updated consistently in the affected declarations and
implementations, without changing function types or ABI.

Unlike the broken donor adaptation, the actual selected destination CPU is
validated in ``dl_task_can_attach()`` before ``dl_bw_of()`` can access its
runqueue. A second guard rejects a zero-active-CPU destination domain after
locking its bandwidth state. This handles a last-CPU-loss case without a
zero divisor in the existing ``__dl_add()`` calculation, including when the
bandwidth limit is disabled. Both guards return -EINVAL without reserving
bandwidth and release any locks/RCU state already acquired.

The existing overflow test, -EBUSY result, successful destination reservation,
source-accounting lifecycle, same-domain bypass and normal-task behavior are
not redesigned. No new hotplug lock or changed lock ordering is introduced;
the guards are not a general proof of CPU-hotplug/cgroup concurrency safety.

Excluded changes
----------------
This does not include the KGSL latency fallback tuning, unused capacity-aware
bandwidth helpers, rbtree helper conversion, optional earliest-deadline
refactor, donor defconfig additions, or compilation-fix bundle from the review.
In particular, no suspend/noirq functions or rbtree interfaces are changed.
The existing defconfig, TEO governor, production SCHED_DEBUG policy, CFQ storage
setup and 10-second freezing timeout remain unchanged. No SBalance is added.

Local validation
----------------
On 2026-11-05, GCC 12 host models passed with actual ASan and UBSan enabled:

* 65,536 eight-CPU domain/active-mask pairs, including the counting fast path.
* Extracted cpuset/core/DEADLINE paths covering inherited effective masks,
  v1 emptiness, affinity/security checks, invalid/offline destinations,
  simulated last-active-CPU loss, overflow/exact-fit/unlimited admission,
  and balanced IRQ/lock/RCU state.
* Extracted KGSL functions covering both incoming IRQ states, create/signal/
  cleanup list behavior and pre-lock lookup/allocation/file/FD failures.
* Non-SMP CPU-count fallback.
* All seven negative controls rejected. Separate runtime probes verified
  UBSan signed-overflow detection and ASan heap-use-after-free detection.
* Exact replay of the recorded adaptation and preservation audit against
  72,952 pre-existing regular files: six expected production edits, no other
  edits/deletions, and seven documentation/selftest additions.

Reproduce the host checks using
``tools/testing/selftests/gpu_dl_backport/README.md``. These are userspace
models with mocked platform context, not real interrupts, lockdep execution,
or parallel CPU-hotplug tests. Host GCC is used only for these models, not
to build a production kernel. No ARM64 object/full-image build with the pinned
AOSP compiler or device validation was performed. GPU stress, cpuset/hotplug
stress and production-toolchain/device validation remain outstanding.
No measured performance/power benefit is claimed. No push or CI run was made.
