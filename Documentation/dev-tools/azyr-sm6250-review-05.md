# Azyr sm6250 review 05 — continued items #44–#53

Status: **review only; none of #44–#53 applied, committed, pushed or sent to CI**.
Continues [#34–#43](azyr-sm6250-review-04.md) with stable identifiers
**A01-044 through A01-053**. Next unassigned: **#110 / A01-110**;
continuation [#54–#63](azyr-sm6250-review-06.md) is recorded. Phoenix numbering
is separate and unchanged. Prior #6, corrected native memlat, corrected #36 and
exact #41 applications are preserved; this review authorizes no further changes.

All ten exact commits and all thirteen changed-file patches were fetched through
the GitHub API, inspected against native sources and checked for complete
changed-line counts. Patch applicability and donor variants used temporary copies
only. [Evidence receipt](azyr-sm6250-review-05-validation.json) records source
hashes, patch hashes, configuration, preprocessor and bounded host models.

## Current configuration / evidence limits

Resolved the miatoll defconfig using the shipped Kconfig parser and host GCC,
`ARCH=arm64 HOSTCC=gcc CC=gcc`, in an external output directory:

```text
CONFIG_SMP=y
CONFIG_PREEMPT=y
CONFIG_NR_CPUS=8
CONFIG_SCHED_BORE=y
# CONFIG_SCHED_WALT is not set
# CONFIG_SCHED_DEBUG is not set
# CONFIG_RT_GROUP_SCHED is not set
CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y
CONFIG_CPU_IDLE_GOV_TEO=y
# CONFIG_CPU_IDLE_GOV_MENU is not set
# CONFIG_CPU_IDLE_GOV_LADDER is not set
CONFIG_HW_RANDOM_MSM_LEGACY=y
# CONFIG_HW_RANDOM_MSM is not set
CONFIG_COMMON_CLK=y
# CONFIG_COMMON_CLK_MSM is not set
# CONFIG_DEBUG_FS is not set
# CONFIG_DYNAMIC_DEBUG is not set
CONFIG_ANDROID_BINDER_IPC=y
CONFIG_MSM_PM=y
```

TTWU_QUEUE remains false. The native migration-cost default is **500,000 ns
(500 us)**. Enabled configuration does not prove runtime use. No production
AOSP target object/image build, device test, scheduler stress or performance/
power measurement was performed in this review.

## #44 / A01-044 — disable RT bandwidth throttling

Commit: [`a947a3a34cc1f25374275bd76384a71490a59fc1`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/a947a3a34cc1f25374275bd76384a71490a59fc1)

Changes `sysctl_sched_rt_runtime` from 950,000 us to -1, with the period still
1,000,000 us. Native `global_rt_runtime()` maps negative values to RUNTIME_INF,
and `rt_bandwidth_enabled()`/the RT accounting path stop enforcing that budget.
RT_GROUP_SCHED being disabled does not make the global RT budget irrelevant.

**Recommendation: reject as a general optimization.** This removes the RT
bandwidth starvation safeguard rather than simply making all tasks 5% faster.
A runaway FIFO/RR task can monopolize affected CPUs and starve fair tasks;
privileged/vendor RT code bugs are also a concern. It does not disable every
watchdog or lockup detector, but removes this specific scheduling protection.
Retain the current budget unless a diagnosed RT workload and an independent
recovery design justify changing it.

## #45 / A01-045 — source-depletion balance race

Commit: [`64fd86c0b842e87e831db924055427b62b7013bf`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/64fd86c0b842e87e831db924055427b62b7013bf)

Adds a `src_rq->nr_running <= 1` check at the start of `detach_tasks()`, clearing
LBF_ALL_PINNED and returning before an empty scan can be mistaken for an
affinity-pinned source and cause a redo.

**Recommendation: sound idea, but skip as redundant for the identified native
entry race.** The only native call to `detach_tasks()` is already preceded by
this source-rq-locked check in `load_balance()`'s `more_balance` path:

```c
if (busiest->nr_running <= 1 ||
    (busiest->active_balance && busiest->nr_running <= 2)) {
        rq_unlock_irqrestore(busiest, &rf);
        env.flags &= ~LBF_ALL_PINNED;
        goto no_move;
}
```

It runs after `rq_lock_irqsave()` and before `update_rq_clock()`/the detach call,
without an intervening source-rq unlock. This already handles the stated race
between initial busiest selection and source locking. A second entry guard
provides no demonstrated new benefit here and does not solve any later WALT
lock-drop scenario. Preserve the native Cambyses/list-rotation/budget safeguards.

## #46 / A01-046 — bail out of newly-idle balancing

Commit: [`dd7a5c396220c22784135cfcc755de3bb3d6f110`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/dd7a5c396220c22784135cfcc755de3bb3d6f110)

Makes `should_we_balance()` stop CPU_NEWLY_IDLE balancing when work has arrived.
This is relevant: native newidle code checks runnable work between domain
iterations, but `load_balance()` can otherwise spend time in its own redo loop
before returning to that check.

**Recommendation: worthwhile corrected-native candidate, not this donor hunk
unchanged.** The donor guards the queued-wakeup test with
`#if SCHED_FEAT_TTWU_QUEUE`. That macro is not defined anywhere in the native
feature/build machinery: the feature is represented by an enum
`__SCHED_FEAT_TTWU_QUEUE` and `sched_feat(TTWU_QUEUE)`, not this preprocessor name.
A GCC preprocessor probe of the exact donor body confirms that the
`llist_empty()` branch disappears, leaving only `nr_running > 0`.

The current false TTWU_QUEUE default makes the pending-wakelist path less
relevant today, but does not make an undefined preprocessor guard correct or
future-proof. A native adaptation should use the existing SMP wake-list/runnable
checks and appropriate read primitives, preserve balance-stop semantics and
custom scheduler protections, and should not enable TTWU_QUEUE as a dependency.
The donor's 120-to-6-us result is a specific benchmark, not a result on miatoll.
No corrected source was applied or timing result reproduced here.

## #47 / A01-047 — inline schedutil policy free

Commit: [`542e7b0ac23af11146f642c4787a2b11bebf4454`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/542e7b0ac23af11146f642c4787a2b11bebf4454)

Adds `inline` to a static helper containing only `kfree(sg_policy)`. Native
callers are governor setup-failure cleanup and governor exit, not the periodic
frequency-update hot path.

**Recommendation: harmless optional cleanup, very low value.** The optimizer
can already inline a small static helper, and `inline` is not an unconditional
code-generation command. No meaningful steady-state performance or power gain
is established. Do not prioritize this as a governor optimization.

## #48 / A01-048 — fls-based __calc_delta normalization

Commit: [`403836055eec7478e4e431828f0be0d650c39f9c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/403836055eec7478e4e431828f0be0d650c39f9c)

Replaces repeated one-bit normalization shifts with `fls()` of the upper 32
bits, then shifts by the computed count. Adds the explicit bitops include to
`sched.h`. It retains the existing inverse-weight calculation, multiplication
and final delta formula rather than changing BORE weights or scheduling policy.
The bit-scan is only called for a nonzero high word.

**Recommendation: strongest direct optimization candidate in this batch.**
A host shared library compiled the actual native/donor `__calc_delta()` bodies
and unchanged `__update_inv_weight()`, with modeled native 32/64-bit load scaling
and widened multiplication under GCC/UBSan. **60,810 boundary/random cases had
zero mismatches**, including returned deltas and updated inverse weights.
Inputs exercise weights <= total or NICE_0_LOAD numerators, zero and correctly
cached inverses, high-word boundaries and extreme u64 execution deltas.

This is equivalence evidence within those modeled inputs, not a 32-bit binary,
an AArch64 target build, proof for arbitrary invalid weight ratios, mathematical
exact-division proof, scheduler concurrency test, or reproduction of the donor's
7x microbenchmark. Expected savings are in normalization work; end-to-end phone
performance gains remain unmeasured. Still requires native target validation
if subsequently approved.

## #49 / A01-049 — zero migration cost

Commit: [`b74c78dbe38b67950323f55f59740518f68f7686`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b74c78dbe38b67950323f55f59740518f68f7686)

Changes the native 500-us migration-cost default to zero. `task_hot()` then
bypasses its recent-execution age test, though earlier class/buddy tests remain.
This tunable also affects newidle balancing thresholds and initial cost values;
it is not merely a statement about one shared cache.

**Recommendation: skip for the current scheduler tuning.** Atoll DT describes
distinct CPU L2 nodes referring to a shared L3; cache coherence/shared last-level
cache does not make private-cache locality or migration costs vanish. The donor's
shared-L2/no-locality-loss premise is not established for this target, and the
setting applies globally rather than checking that a particular migration is
within an appropriate DSU/cache domain. Zero may increase migration churn and
balancing work. Retain the native value absent controlled migration/latency/
power measurements. Exact donor context also differs from the current BORE file.

## #50 / A01-050 — legacy hardware RNG retry tuning

Commit: [`b2e7a75866a0fb90ca494e9fa2197c78e8b0c670`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b2e7a75866a0fb90ca494e9fa2197c78e8b0c670)

Changes delay 440 to 6 us **and** retry limit 5 to 500 in `msm_rng.c`. This
underscore-named driver is the one built by HW_RANDOM_MSM_LEGACY=y; it should
not be confused with the separate `msm-rng.c` driver, disabled here.

**Recommendation: plausible hardware-specific tuning, defer pending hardware
latency/failure tests.** A shorter retry delay may avoid excessive waiting when
the FIFO becomes ready quickly. However, this is not simply a shorter timeout:
with the exact `failed++ == RETRY_MAX_CNT` pattern, an always-empty FIFO permits
6 versus 501 status polls, 5 versus 500 delay calls, and nominal udelay totals
**2,200 versus 3,000 us**, excluding MMIO/loop overhead. Failed polls accumulate
across the read rather than resetting after successful words. The driver busy
waits while holding its RNG mutex and clock/bus votes.

A host counter model confirms those counts; it does not validate the message's
5–6-us hardware readiness assumption on this device. No entropy-quality
algorithm changes. Test normal throughput and empty/stalled-FIFO behavior before
adopting it as a latency/power improvement.

## #51 / A01-051 — remove residency wrapper

Commit: [`7475d151abe8e4620235c8d2cafc86041eb6a0da`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/7475d151abe8e4620235c8d2cafc86041eb6a0da)

Replaces the ladder/menu calls with `dev->last_residency` and removes the static
inline wrapper, whose body returns that same int member. A repository search
finds only those two callers plus its header definition.

**Recommendation: low-risk optional cleanup, not a performance improvement.**
Both affected governors are disabled in the selected TEO configuration, and
the wrapper is already inline. No reason to expect changed idle behavior or
noticeable savings. External source users would need the corresponding member
access update; this is not removal of an exported binary function.

## #52 / A01-052 — avoid parent-clock debug traversal in suspend

Commit: [`c0ff2a937bff4080b8be6ece6e97ec193e2edfb0`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c0ff2a937bff4080b8be6ece6e97ec193e2edfb0)

Passes false rather than true to `clock_debug_print_enabled()` in the non-idle
suspend branch. Native `cluster_prepare()` holds `cluster->sync_lock` across
`cluster_configure()`. With common-clock debug code enabled, the true path walks
parents through `clk_get_parent()` -> `clk_prepare_lock()`, which can call
`mutex_lock()`. The false path prints enabled-clock data without parent traversal.

**Recommendation: sound defensive correctness fix for debug-enabled builds.**
This addresses a concrete potentially sleeping parent-lookup path under the
cluster spinlock; it does not claim to prove every debug callback atomic-safe.
It retains enabled-clock suspend diagnostics rather than silencing suspend logs.

For the selected configuration, COMMON_CLK=y and DEBUG_FS=n compile an **empty
`clock_debug_print_enabled()` stub**, so there is no active suspend fix or power
benefit from changing the argument today. Keep debugfs disabled unless separately
requested; the patch is useful defensive maintenance if that path is later built.

## #53 / A01-053 — demote Binder ioctl error log

Commit: [`ca67213b29d9f08a5ff0331f9a79aa2cb68a4a0c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/ca67213b29d9f08a5ff0331f9a79aa2cb68a4a0c)

Changes one non-EINTR ioctl-error footer from `pr_info()` to `pr_debug()`.
It does not fix the error, alter the return code or Binder transaction behavior,
or suppress every Binder diagnostic. The trace_binder_ioctl_done path remains.

**Recommendation: optional log policy, not a performance fix.** With native
DYNAMIC_DEBUG=n and no Binder DEBUG define, this diagnostic normally compiles to
`no_printk()`, losing routine visibility for this class of failures. If there is
confirmed log spam, consider preserving observability through a rate-limited
info/warning message rather than silencing every occurrence. Debug-enabled builds
can retain/enable pr_debug differently. Do not treat an unobserved log flood as
proof of battery or responsiveness gains.

## Summary

- **Best optimization candidate: #48**, with bounded arithmetic equivalence
  evidence but no target/performance claim.
- **#46 is useful in corrected native form**, without the undefined feature
  preprocessor guard or an unapproved TTWU_QUEUE policy change.
- **#52 is a good defensive correctness fix**, inactive in the current debugfs-off
  build and compatible with retaining enabled-clock suspend diagnostics.
- **#45's identified entry race is already handled.** #47/#51 are optional,
  low-value cleanups. #50 needs hardware-specific timing/failure validation.
- **Reject #44; skip #49 as a generic optimization.** #53 is a logging-policy
  decision; retain useful error observability unless actual spam warrants change.

Only review documentation/evidence changed. No kernel/defconfig edits, option
activation, commit, push or CI dispatch. **Next review: #95 / A01-095; see [review 09](azyr-sm6250-review-09.md).**

Latest continuation: [#64–#73](azyr-sm6250-review-07.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#74–#83](azyr-sm6250-review-08.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.

## Later user-approved application

Items #46, #47, #48, #52 were subsequently approved and applied,
with native corrections where recorded in [the selected application](azyr-sm6250-selected.md).
Original review findings above remain historical; unselected items remain unapplied.
