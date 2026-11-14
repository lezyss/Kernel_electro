# Azyr sm6250 review 09 — continued items #84–#94

Status: **review only; none of #84–#94 applied, committed, pushed or sent to CI**.
Continues [#74–#83](azyr-sm6250-review-08.md), retaining stable identifiers
**A01-084 through A01-094** in the user's submitted order. This batch contains
**eleven**, not ten, commits. Next unassigned: **#110 / A01-110**. Phoenix numbering
remains separate. Earlier approved #6, corrected native memlat, corrected #36
and exact #41 remain intact; recommendations are not application approval.

All eleven exact commit objects and all **17 changed-file patches** were fetched
through the GitHub API, read against native sources, and checked for complete
changed-line counts. All exact standalone textual patch checks pass, but several
patches are unsuitable despite applying cleanly. Donor applications and probes
used temporary copies only. The [evidence receipt](azyr-sm6250-review-09-validation.json)
contains full patches/hashes, configuration, bounded fixtures/results, dependency
checks and preservation checks.

## Configuration and common workqueue caveat

Resolved the miatoll defconfig with the shipped Kconfig parser,
`ARCH=arm64 HOSTCC=gcc CC=gcc`, in an external output directory:

```text
CONFIG_QRTR=y
CONFIG_QRTR_SMD=y
CONFIG_QCA_CLD_WLAN=y
CONFIG_QCA_CLD_WLAN_PROFILE="default"
CONFIG_BT=y
CONFIG_BT_BREDR=y
CONFIG_BT_LE=y
CONFIG_QCOM_KGSL=y
CONFIG_THERMAL=y
CONFIG_BLK_CGROUP=y
CONFIG_IOSCHED_CFQ=y
CONFIG_CFQ_GROUP_IOSCHED=y
CONFIG_DEFAULT_IOSCHED="cfq"
# CONFIG_WQ_POWER_EFFICIENT_DEFAULT is not set
# CONFIG_SCHED_CORE_CTL is not set
# CONFIG_SCHED_WALT is not set
# CONFIG_IOSCHED_BFQ is not set
# CONFIG_DEBUG_BLK_CGROUP is not set
```

BT_6LOWPAN, PCI_MSM and LITHIUM are also unselected/absent. Current Kconfig does
not establish runtime Bluetooth transport, actual storage elevator or polling
behavior. Host GCC is not the required production AOSP ARM64 compiler.

**"Power efficient" is a conditional policy, not a power saving guarantee.**
Native system_power_efficient_wq and its freezable counterpart acquire WQ_UNBOUND
when workqueue.power_efficient is enabled; otherwise they retain ordinary bound
behavior. Its default is disabled above, though a boot parameter can override it.
A distinct workqueue object remains distinct for flushing/accounting even if it
shares the same worker pool. None of these patches enables that global policy.
They do not make ordinary work freezable unless a freezable queue is actually
selected, and WQ_HIGHPRI is a high-priority normal worker pool, not SCHED_FIFO.

No production target objects/image, phone boot, real workqueue concurrency,
WLAN/BT/modem/GPU/storage/thermal stress, suspend, power or performance measurement
was performed. Host models check source contracts/control flow only.

## #84 / A01-084 — QRTR backup-buffer refill queue

Commit: [`4eb542237b74d7e94c01a6d858fcc096dfdaf1d1`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/4eb542237b74d7e94c01a6d858fcc096dfdaf1d1)

Moves QRTR backup-buffer initialization/refill work from system_unbound_wq to
system_power_efficient_wq. The native worker fills small/large skb reserves with
GFP_KERNEL allocations, and consuming a reserve buffer queues its replenishment.
Cancellation and reserve purging remain unchanged. QRTR/SMD are selected here.

**Recommendation: skip as an unproven power optimization.** The old queue is
already unbound; the proposed queue is **bound by default in this profile**.
That can change placement in the opposite direction to the simple marketing
interpretation of "power efficient". With the global runtime policy enabled it
is again unbound, not a new guarantee of fewer wakeups. Reserve-refill latency
under receive load and memory pressure matters; no result justifies replacing
the native choice here. This is not a QRTR memory-leak or protocol fix.

## #85 / A01-085 — WLAN delayed register-write allocator

Commit: [`7e313a7259b5519e428393d765672fce3e2adacd`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/7e313a7259b5519e428393d765672fce3e2adacd)

Replaces qdf_alloc_high_prior_ordered_workqueue with
qdf_alloc_power_efficient_ordered_workqueue. **The new helper does not exist in
the native QDF C/headers.** Native qdf_defer.h and i_qdf_defer.h supply the old
wrapper, implemented through alloc_ordered_workqueue(name, WQ_HIGHPRI).
A syntax-only probe using those actual native wrappers compiles the old call
and rejects the donor call as undeclared/incompatible. A helper prerequisite
would be required; a clean textual patch check does not establish API availability.

Do not overstate current-profile build failure: the changed body is guarded by
FEATURE_HAL_DELAYED_REG_WRITE. The selected default WLAN config sets that feature
inside **LITHIUM=y and PCI_MSM=y** conditions; neither is selected here. The
inactive branch has a separate stub init. This missing helper is an enabled-
feature/backport completeness defect, not proof of a miatoll compilation failure.

**Recommendation: skip the exact patch.** If enabling that HAL feature elsewhere,
retain ordered writes, review firmware/register-write latency and add a correctly
specified allocator first. A high-priority worker by itself does not busy-spin
or prove idle power consumption; the donor's idle-power claim needs measurements.

## #86 / A01-086 — selected Bluetooth delayed work

Commit: [`a3fe2a796d8a0d666bed016d1561a45625a06d24`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/a3fe2a796d8a0d666bed016d1561a45625a06d24)

Redirects six enqueue sites across five files: 6LoWPAN peer notification, the HCI
command timeout, two L2CAP information timers, SCO connection timeout and SMP
security timeout. Existing delays and work-item cancellation stay unchanged.
Most affected protocol code is selected by BT/BREDR/LE; 6LoWPAN is not selected.

**Recommendation: low-priority conditional experiment, not a must-have.** With
power-efficient policy disabled it does not gain unbound placement. When enabled,
shared unbound execution changes affinity/contention for timeout/recovery paths,
not only harmless background reporting. HCI recovery, pairing, SCO and connection
teardown need tests, plus actual power evidence. The individual edits are more
bounded than #87, but no measured benefit warrants automatic inclusion. If #87
were applied, these explicit substitutions would mostly duplicate its helper
redirection; that is not a reason to take #87.

## #87 / A01-087 — globally redirect delayed-work helpers

Commit: [`e8b96d15d578dd9b99451f3a59d23325ce1a1419`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/e8b96d15d578dd9b99451f3a59d23325ce1a1419)

**Recommendation: reject this blanket policy change.** The title overstates its
scope in one respect and understates its risk in another: it changes only
schedule_delayed_work and schedule_delayed_work_on, **not** immediate
schedule_work or explicit queue calls, but changes those two wrappers for every
subsystem using them.

When global power-efficient policy is enabled, the _on variant no longer
provides the same bound worker-execution behavior: its requested CPU can still
control timer placement, while work can run in an unbound pool. Native callers
include CPU-oriented code such as OProfile and x86 thermal polling; not every
caller is safe to migrate merely because a driver-local cleanup was desirable.
Those examples illustrate generic API scope, not a claim they run on miatoll.

The patch also leaves flush_scheduled_work draining **system_wq**, despite moving
helper-enqueued delayed work to another queue. For zero-delay delayed work,
which is runnable immediately, the extracted wrapper/flush model gives:

```text
native: target=system    pending_after_system_flush=0
donor:  target=efficient pending_after_system_flush=1
```

This is a queue-contract model, not a real driver deadlock reproducer. It does
not claim that flush_scheduled_work ever flushes future timer expirations in the
native implementation. The zero-delay case isolates the changed queue target.
Even with unbound policy disabled, separate queue-flush behavior remains.
Audit specific callers rather than silently rewriting the global helpers.

## #88 / A01-088 — QDF delayed/periodic work queues

Commit: [`7223c15c7c93a3994c01959a3769f2d839fd5225`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/7223c15c7c93a3994c01959a3769f2d839fd5225)

Explicitly redirects qdf_delayed_work_start and both the initial/rearm paths of
QDF periodic work to system_power_efficient_wq. Contrary to the message, it does
**not** move all QDF work: immediate work, explicitly allocated queues, tasklets
and other mechanisms are untouched. Native periodic work remains initialized
with INIT_DEFERRABLE_WORK; ordinary QDF delayed work remains non-deferrable.
Stop/cancel logic, delays and callback ordering within each work item are unchanged.

These wrappers are built into selected qcacld. Native consumers include bus-
bandwidth periodic work, idle timeout and IPA wake-lock release work. Effects
therefore span WLAN performance/power policy, not one isolated background task.

**Recommendation: optional targeted experiment only; skip without evidence.**
Actual unbound placement depends on the shared runtime policy, and battery versus
callback-latency/suspend/throughput behavior needs measurement. With #87 applied,
the old schedule_delayed_work calls already target the proposed queue, so #88
adds no independent placement improvement. Neither patch is approved here.

## #89 / A01-089 — high-priority KGSL general workqueue

Commit: [`99861a5283f84a80ed566cadab1bcaf19a71a968`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/99861a5283f84a80ed566cadab1bcaf19a71a968)

Adds WQ_HIGHPRI to kgsl-workqueue, retaining UNBOUND | MEM_RECLAIM | SYSFS and
max_active 0 (the existing default concurrency choice). No new thread lifecycle,
freezer behavior or submit protocol is introduced. It is a much more bounded
change than rejected #64.

**Recommendation: a plausible performance candidate for testing.** It can reduce
CPU scheduling delay for queued KGSL work under contention, but also promotes
cleanup/housekeeping. Native kgsl_schedule_work consumers include page-table
destruction, snapshots, idle/power checks, thermal cycling and power-on work.
It is **not** a promotion of all GPU command dispatch: the separate KGSL kthread
worker already has SCHED_FIFO 16 and explicit performance-critical placement.

No dependency among these eleven. Measure relevant latency and power under CPU
load and exercise GPU faults/snapshots, memory pressure and suspend before
claiming a benefit. This patch is not a replacement for hardware validation.

## #90 / A01-090 — disable core_ctl initialization

Commit: [`268f67a457ab447c253999eb1e74fbe6e0f468d0`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/268f67a457ab447c253999eb1e74fbe6e0f468d0)

**Recommendation: reject the misleading form; no effect on this profile.**
It wraps the complete initialization tail in #if 0, including cluster lookup/
creation and late_initcall(core_ctl_init). This suppresses per-cluster state,
core-control worker creation, sysfs kobjects, hotplug callback registration and
setting initialized=true—not just userspace writes to a tuning knob.

Native core_ctl_check and core_ctl_set_boost return early while uninitialized.
Thus the patch disables the controller's bring-up while leaving its body/APIs
present. It does not let the same fully initialized kernel controller operate
independently of userspace. CONFIG_SCHED_CORE_CTL=n already omits the object on
miatoll; WALT is also off. If userspace policy protection is ever wanted on an
enabled controller, design scoped access/default policy rather than deleting
its init path behind a preprocessor dead block.

## #91 / A01-091 — thermal polling queue replacement

Commit: [`2fbba992344a6fcfd57dc29406442c9364efedc5`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/2fbba992344a6fcfd57dc29406442c9364efedc5)

**Recommendation: skip; this native tree already has a different thermal policy.**
Native ordinary polling already passes system_freezable_power_efficient_wq, and
the helper's <=1000-ms path already uses it. The donor changes only the >1000-ms
branch, ignoring the caller-provided queue and forcing that same general queue.

For passive zones, monitor_thermal_zone supplies **thermal_passive_wq**, which
native thermal_init allocates HIGHPRI | UNBOUND | FREEZABLE with its dedicated
concurrency cap. Therefore the real incremental change here is to bypass that
queue on **long passive polls**, losing its priority/queue policy. It is not a
new conversion of ordinary thermal polling to a power-efficient queue.

The actual-helper model covers normal/passive callers and delays 0, 1, 1000,
1001 and 2000 ms. Ordinary polls and short polls are unchanged; long passive
polls move from passive_highpri to the general efficient queue. Both are still
freezable; polling rounding remains unchanged. This does not prove a physical
thermal-safety failure, but neither is a queue downgrade justified by the donor's
older-tree description. Actual zones/delays require runtime confirmation.

## #92 / A01-092 — migrate CFQ/request timestamps to monotonic time

Commit: [`202b3995f9ad16f01aab59847e1ab9d15afd802d`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/202b3995f9ad16f01aab59847e1ab9d15afd802d)

**Good direction, but request a complete native adaptation rather than blindly
apply this CFQ-only backport.** It moves CFQ cgroup statistics and the shared
request start/io-start setters from sched_clock to ktime_get_ns. It removes the
two preemption-disable/enable pairs in the timestamp setters and uses u64 and
ordinary monotonic comparisons. Selected CFQ and its request timestamp producers
remain in one clock domain after this change. This is not I/O queue-depth,
latency-target or throughput tuning, and no speedup was measured.

The fields/setters in blkdev.h are **not CFQ-private**. Native BFQ completion
passes rq_start_time_ns/rq_io_start_time_ns to bfqg_stats_update_completion in
block/bfq-cgroup.c, which still takes its completion sample using **sched_clock**.
The exact donor patch does not convert that reader. Equal apparent units do not
make separate clock origins, cross-CPU behavior or suspend semantics identical.

The extracted producer/reader model uses request start=1000, dispatch=1100 and
completion=1250 in monotonic units, with sched_clock offsets -500, 0 or +500:

```text
native: CFQ service=150, BFQ service=150 for all modeled offsets
 donor: CFQ service=150, BFQ service=0 / 150 / 650 for -500 / 0 / +500
```

Wait time remains 100, since both request fields changed together. The two
setter preemption pairs become zero. These are modeled clock offsets, **not a
measured phone skew** or corruption reproducer.

**BFQ is disabled in this profile**, so that mismatch is a generic supported-
configuration/incomplete migration issue, not evidence of broken current CFQ.
A corrected native version should migrate the BFQ completion reader consuming
these shared fields as well, without indiscriminately changing unrelated BFQ
internal timestamps. DEBUG_BLK_CGROUP=n excludes the additional debug-only CFQ
wait/idle/empty paths, but ordinary CFQ group completion stats are selected.
Consider a corrected version if choosing this item; no correction is applied here.

## #93 / A01-093 — CFQ fallthrough annotation

Commit: [`79431f18b1e102a6813c746be21fee0a237006d9`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/79431f18b1e102a6813c746be21fee0a237006d9)

**Harmless optional warning cleanup, no runtime gain.** Adds a fall-through
comment after the invalid-priority diagnostic in cfq_init_prio_data. The existing
switch deliberately continues into IOPRIO_CLASS_NONE behavior; the comment does
not change it. Independent temporary replay differs from native only by that
comment. This documents intent for warning analysis; no production compiler
warning result or performance benefit is claimed. No dependency on #92 or #94.

## #94 / A01-094 — clear unpinned CFQ group async queue pointers

Commit: [`522ab2ee25fc0c802c55ec269dc565411422c129`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/522ab2ee25fc0c802c55ec269dc565411422c129)

**Recommendation: sound defensive native cleanup; strongest correctness pick in
this batch.** After cfq_pd_offline drops the pinned references to the 2x8 async
priority queues and async idle queue, it sets each occupied pointer to NULL.
Native drops those references but leaves the stale values behind. It does not
change initial queue selection, the number of references dropped or the final
statistics transfer. CFQ_GROUP_IOSCHED=y here, so this is selected code.

An actual-body host model covers all occupancy counts 0 through 17, for native
and donor (36 cases). With every slot occupied:

```text
native: puts=17 stale_slots=17 stat_transfers=1
donor:  puts=17 stale_slots=0  stat_transfers=1
```

This tracks pointer/reference ownership without dereferencing real freed memory.
It is not an observed cgroup-removal crash or proof of complete callback
idempotence: statistics transfer is still a one-time lifecycle operation.
The donor description itself characterizes this as robustness after historical
reverts. Do not promise a current reproducible UAF or speed improvement.
No prerequisite among these eleven; #92/#93/#94 also apply in order on copies.

## Summary and preservation

- **#94:** worthwhile selected-path defensive cleanup.
- **#89:** bounded performance candidate, subject to GPU/power/lifecycle testing.
- **#92:** useful clock-source migration concept, but a complete native version
  should cover the remaining BFQ consumer of the shared request timestamps.
- **#93:** optional comment-only warning cleanup.
- **#86/#88:** at most scoped experiments; queue names alone establish no saving.
- **Skip #84/#85/#90/#91 and reject global #87** for native policy/placement,
  missing optional-feature API, disabled controller init, bypassed passive thermal
  queue and global helper-contract changes, respectively.

All eleven standalone textual patch checks pass; that does not establish
semantic/API compatibility. Candidate and review-08 sources/contexts, approved
#6/memlat/#36/#41 postimages and miatoll defconfig remain unchanged. No native
kernel/defconfig edit, activation, commit, push or CI dispatch.
**Next unassigned: #110 / A01-110.**

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.

## Later user-approved application

Items #92, #93, #94 were subsequently approved and applied,
with native corrections where recorded in [the selected application](azyr-sm6250-selected.md).
Original review findings above remain historical; unselected items remain unapplied.
