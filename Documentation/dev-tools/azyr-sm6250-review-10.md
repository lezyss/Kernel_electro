# Azyr sm6250 review 10 — final submitted items #95–#109

**Review only. None applied, committed, pushed or sent to CI.** Continues
[review09, #84–#94](azyr-sm6250-review-09.md). Stable IDs A01-095 through
A01-109 follow submitted order. All 109 submitted Azyr items are now reviewed;
next unassigned is **#111 / A01-111**. Phoenix numbering stays separate.
Earlier approved #6, corrected native memlat, corrected #36 and exact #41 are
preserved. A shortlist is not authorization.

## Method and target

Read exact GitHub API commit patches (15 commits, 25 changed-file patches),
checked complete addition/deletion counts and inspected native callers/APIs.
The [validation receipt](azyr-sm6250-review-10-validation.json) retains exact
patches and hashes, native preimage hashes, resolved config, host fixtures and
results. Applications were on temporary source copies only. Twelve standalone
patch checks pass; #97, #101 and #109 fail. Reverse checking #97 passes, proving
its submitted change is already present. Applying #100 then #101 passes on copies,
but does not cure #101's defects.

Miatoll config was resolved using the shipped parser, external O= directory,
ARCH=arm64 HOSTCC=gcc CC=gcc. BORE/PELT, UTIL_EST/FASTUP, CPU hotplug, suspend,
GICv3, SMEM/SMP2P/sleepstate, eventtimer, ADC_TM, thermal/TSENS and CFQ are enabled.
FAIR_GROUP_SCHED, WALT, DEBUG_KERNEL, HIBERNATION, MSM_PM_LEGACY, FB_MSM,
SCSI_MQ_DEFAULT, WBT and legacy deadline are disabled; DRM_MSM is enabled,
DEFAULT_IOSCHED="cfq". Runtime queue policy can differ from config defaults.

Host actual-function models use GCC O2/UBSan and explicit mocks; they are not
production AOSP ARM64 compilation, hardware concurrency, phone boot/suspend,
thermal safety, storage performance or battery proof. Workqueue priority changes
can delay safety-related work; a queue name or donor title proves no benefit.

## Verdicts

| # / stable suffix | Exact commit | Recommendation |
|---|---|---|
| 95 | [399d7d2432016dc8ef6b3b99c096fc8417102bf1](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/399d7d2432016dc8ef6b3b99c096fc8417102bf1) | Skip default scheduler policy experiment |
| 96 | [0c023e8f08d97f3ba0a2e1a3663b404e7dc92748](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/0c023e8f08d97f3ba0a2e1a3663b404e7dc92748) | Adapt/test first; FASTUP bypasses new guard |
| 97 | [32c12e273e076934d93370ac20345d746feae037](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/32c12e273e076934d93370ac20345d746feae037) | Already present; skip duplicate |
| 98 | [6bbaff1957fa023f5ff2bdb22714eab646abd689](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/6bbaff1957fa023f5ff2bdb22714eab646abd689) | Useful diagnostic candidate; no speed/battery claim |
| 99 | [cd52aa23dc376a16445413a5069541663e3ce406](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/cd52aa23dc376a16445413a5069541663e3ce406) | Optional non-DEBUG cleanup; not substantial optimization |
| 100 | [bce80afde3100d6ca2ec1383c4141bfe872bdcf5](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/bce80afde3100d6ca2ec1383c4141bfe872bdcf5) | Reject broad native PM rollback |
| 101 | [42c641fcff89556bd0bc5ff6f5175e9d70bc26d8](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/42c641fcff89556bd0bc5ff6f5175e9d70bc26d8) | Reject exact patch: lifecycle/error-path defects |
| 102 | [72fff56a891d1146eca755f27a687d5baa759b28](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/72fff56a891d1146eca755f27a687d5baa759b28) | Optional unused-profile config cleanup; no measured battery gain |
| 103 | [74fa4d9c54c6a64ca2ad2f0afb8fc203e1e10eec](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/74fa4d9c54c6a64ca2ad2f0afb8fc203e1e10eec) | Skip lowering ADC notification priority |
| 104 | [48411a80fa03dcfddfe46fde77bcc1253efe7ab7](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/48411a80fa03dcfddfe46fde77bcc1253efe7ab7) | Skip lowering passive thermal priority |
| 105 | [cf43c849c79e06b06d7a224e1b46cc76fd44eece](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/cf43c849c79e06b06d7a224e1b46cc76fd44eece) | Skip TSENS queue policy/concurrency experiment |
| 106 | [8b330fcbd0f348436693d590cc1d688f2a1ca75e](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/8b330fcbd0f348436693d590cc1d688f2a1ca75e) | Skip global forced MQ completion affinity |
| 107 | [09d18c5f30d1ca591c556504d097322b5a960fcf](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/09d18c5f30d1ca591c556504d097322b5a960fcf) | Skip: WBT off; flash already 2ms |
| 108 | [84c17c07964727bd51c56c3c55c1f9f4bfcba4a0](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/84c17c07964727bd51c56c3c55c1f9f4bfcba4a0) | Skip: legacy deadline off; selected CFQ unchanged |
| 109 | [06410300142fe6f61d440a5558bf33aaa0a24de8](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/06410300142fe6f61d440a5558bf33aaa0a24de8) | BORE already NONE; preserve non-BORE LOG fallback |

## #95 — alternative slice policy

Enables ALT_PERIOD and BASE_SLICE by default. ALT_PERIOD uses root hierarchical
runnable count rather than local count; with FAIR_GROUP_SCHED=n this distinction
is normally redundant. BASE_SLICE floors each weighted ideal slice at min_gran,
which is a genuine policy change, not a branch optimization. Native BORE, PELT,
CASS and other scheduler integrations must remain intact.

Actual period/slice bodies with rational weight arithmetic demonstrate, at
native 24ms latency, 5ms min_gran and initial sched_nr_latency=8:

- Low-weight task among two: about 0.346ms ideal slice becomes 5ms.
- Eight equal-weight tasks: 3ms becomes 5ms. A sysctl write can recompute the
  latency threshold, so this is a stated fixture, not every runtime state.

The floor may reduce scheduling frequency but also weakens ideal weight-based
slice distinctions and changes latency. Existing tick/preemption checks mean
these numbers are not guaranteed uninterrupted wall-clock execution. Skip as an
unmeasured default change; no dependency on another submitted item.

## #96 — utilization sample guard

Adds task_util > capacity_orig_of(cpu) before EWMA consolidation. Avoiding a
misleading sample on a saturated smaller CPU has merit, but this exact placement
is after the enabled UTIL_EST_FASTUP path's goto done. Original CPU capacity is
not the thermal/frequency-reduced currently available capacity.

Actual dequeue-body model at capacity512:

- util700, previous EWMA900: native falls to850, donor preserves900.
- util400, previous EWMA900: both become775.
- util700, previous EWMA300: FASTUP makes both701 (the unchanged marker bit is
  included); donor's new guard is bypassed.
- FASTUP disabled, util700/EWMA900: native850, donor900.

Thus not a complete clamp or universally safe performance gain. A corrected
native proposal needs explicit FASTUP policy and little/big migration/schedutil
validation, not blindly moving the check or clamping task demand. Adapt first.

## #97 — offline CPU late interrupt fix

Native cpu_idle_loop already disables local IRQs before testing offline status
and stops the nohz tick before arch_cpu_idle_dead. Exact forward patch fails and
reverse check succeeds. This is a worthwhile fix already integrated; no change.

## #98 — structured wakeup IRQ reasons

Calls log_irq_wakeup_reason in the PM system IRQ wake path and GIC resume scan.
**Importantly, it removes GIC's early !msm_show_resume_irq_mask return** and gates
only pr_warn, so structured recording works even when console IRQ printing is
disabled. gic_resume_one calls the scan without an outer debug-mask gate.
Native includes/API already exist; the recorder deduplicates IRQ nodes with
locking and has CONFIG_SUSPEND stubs. Existing PM/GIC console messages remain.

Useful for Android wakeup-reason diagnosis, not an IRQ fix or power optimization.
Costs include register scanning/IRQ lookup and recorder work even with printing
off; pending+enabled GIC IRQs are candidates, not necessarily the sole physical
wake cause. Suspend/resume testing must check nested IRQ attribution and logs.
Strongest useful functionality candidate here; no #100/#101 prerequisite.

## #99 — Binder debug stubs

Native binder_debug already compiles out unless DEBUG. Donor additionally guards
binder.c's mask/module parameter, and compiles allocator debug calls/parameter
out in non-DEBUG builds. binder_alloc_debug_mask itself remains declared outside
the guard. DEBUG_KERNEL=n does not itself prove DEBUG undefined; native Binder
Makefile/defines provide no forced DEBUG in the inspected default path.

Optional cleanup reduces disabled allocator logging checks but removes runtime
parameter diagnostics. It does not rewrite Binder transaction handling or remove
all debugging infrastructure; avoid promising major IPC or battery improvement.
No prerequisite among these fifteen.

## #100 — six-file suspend/tick rollback

The title does not describe a small fix. It changes system wake counter semantics,
PIL firmware loading versus suspend exclusion, freezer wakeup checks/reset point,
tick ownership and SMP2P IRQ wake-source handling.

- Replaces first-abort relaxed increment/wake with atomic_inc and unconditional
  s2idle_wake; more wake calls do not establish correctness or a power saving.
- PIL loses down_read_trylock + pm_system_wakeup before blocking on pil_pm_rwsem;
  preserve native coordination unless a specific firmware/suspend defect is shown.
- Moves pm_wakeup_clear from enter_state into freeze_processes. Changes freezer
  completion-before-wakeup order and return condition. Actual-body model with
  todo0 and pending wake returns -EBUSY natively but 0 in donor without checking
  wakeup there. Later suspend checks still exist: not proof of a lost wake event.
- Replaces tick frozen CPU mask/owner handoff with a depth count. Two-CPU actual
  body model: after timer-owner CPU0 freezes while CPU1 remains awake, native
  moves owner to1; donor leaves owner0. Both balance one timekeeping suspend and
  resume after all CPUs freeze. No clock failure on hardware was reproduced.
- Adds a primary SMP2P ISR and embedded wake source held until threaded handler
  completes. That idea needs its own lifetime/remove/freeze/error audit; the
  squash is not justified by that one potentially useful component.

Does NOT alter native 10-second freezer timeout or set a new mem_sleep default.
Native starts TO_IDLE but platform suspend ops may select deep sleep. Reject as
submitted; do not undo existing native suspend behavior wholesale.

## #101 — SMEM/SMP2P replacement

Standalone SMP2P context needs #100; ordered100→101 applies on copies. The
advertised sleepstate IRQF_ONESHOT is **already native**, as both source and
actual probe-body model confirm. The two-argument wakeup_source_register API is
valid here; the defect is ownership, not API arity.

Confirmed donor sleepstate failure paths:

1. Wakeup-source allocation failure executes return -ENOMEM before goto err_ws;
   registered PM notifier is left behind. Body mock confirms notifier count1.
2. Invalid IRQ/probe deferral or request_irq failure calls
   wakeup_source_unregister(notify_ws), then __pm_relax(notify_ws). Native
   unregister destroys/frees the allocated source: use-after-free. Ownership-
   marking mocks record one post-unregister relax on both paths without ever
   dereferencing physically freed memory.
3. Returning notifier registration errors is sensible in isolation; native logs
   and continues. It does not justify the broken replacement.

Additional source findings: SMEM socinfo child registration may return ERR_PTR,
yet remove unconditionally platform_device_unregister's it. qcom_smem_virt_to_phys
loses its !__smem guard. Native configurable host ID is replaced by APPS; cached
entry layout/size and allocation boundary behavior also change. SMP2P switches
from devm entries to manual allocation, with failed not-yet-linked probe entries
not freed by list unwinding; restore does not check allocated wake source.
HIBERNATION=n excludes restore/freeze at present, not the ordinary probe errors.
Remove now unregisters wake source before devm IRQ teardown, requiring IRQ
quiescence audit too. Exact replacement is unsafe; reject. Do not apply #100
merely to make it fit. Any narrow SMEM correctness improvements deserve separate
native patches with bounded layout/boundary/lifetime tests.

## #102 — remove MSM eventtimer configuration

Current MSM_EVENT_TIMER=y, but selected new lpm-levels.c does not consume
get_next_event_time; legacy reader is excluded by MSM_PM_LEGACY=n. Repository
MDSS framebuffer code really registers and activates event timers, **but that
client is excluded here by FB_MSM=n**; selected display stack is DRM_MSM. Therefore
not correct to claim these MDSS clients are active on this miatoll config.

Optional profile cleanup: no active in-tree client/reader found in this selected
profile. Config-off header stubs return NULL/no-op and change behavior for other
profiles that do enable those clients. Keep a separate audit if changing display
or legacy PM config; no measured wakeup/battery benefit and no authorization to
alter defconfig. Independent of #100/#101.

## #103–#105 — thermal workqueues

#103 changes ADC_TM non_thermal notification queue from WQ_HIGHPRI to0, remaining
bound with default max_active. non_thermal means callback consumers rather than
thermal-zone-only reporting, not proof notifications are unimportant. ADC_TM and
matching ADC-TM5 DTS are present; child/client runtime use must be inspected.

#104 removes HIGHPRI from the selected passive thermal queue while retaining
UNBOUND|FREEZABLE and THERMAL_MAX_ACTIVE. This can delay passive cooling work
under CPU contention. No safe latency bound or measured efficiency improvement.

#105 changes TSENS queue from HIGHPRI/default max_active to UNBOUND/max_active1:
priority, binding and concurrency all change. It queues therm_fwk_notify after
sensor recovery; the queue is not the hardware SCM recovery operation itself.
Atoll DTS has tsens-reinit-wa. One work_struct already coalesces pending instances;
max_active1 is not proof that recovery becomes correct or cheaper. Preserve
thermal responsiveness. Skip all three as unvalidated policy changes, not claim
that they disable thermal protection outright. They apply independently.

## #106–#108 — block policy

#106 adds QUEUE_FLAG_SAME_FORCE to MQ defaults. Combined with SAME_COMP this
forces completion toward the submitting CPU rather than allowing same-cache
local completion. This is not enabling multithreading. It can increase remote
IPIs/wakeups on heterogeneous phone CPUs. SCSI_MQ_DEFAULT=n; native UFS host
has no force_blk_mq assignment found, though scsi_mod.use_blk_mq/runtime
rq_affinity can override defaults. Do not equate config with observed queue mode.
Skip a global default change; test rq_affinity on the actual queue first.

#107 sets all WBT default latency to2ms. Actual helper model: rotational
75ms→2ms, nonrotational2ms→2ms. WBT=n; UFS is nonrotational anyway. No selected
benefit; could change external rotational storage behavior in another config.

#108 changes legacy deadline write expiry5s→1s, writes_starved2→1 and disables
front merging. Can favor writes at read/merge tradeoffs, not universal throughput.
Legacy deadline=n and default CFQ: no selected benefit. Not mq-deadline tuning.
All three textual patches apply independently, with no activation authorized.

## #109 — tunable scaling

Donor replaces unconditional LINEAR with NONE. Native already has BORE-specific
NONE and non-BORE LOG; selected BORE therefore has the requested unscaled setting.
Do not replace the native conditional or claim this speeds up the current
scheduler. Exact patch does not apply. Skip; no #95 prerequisite needed.

## Completion

Consider #98 for diagnostics; #99/#102 are optional cleanup, not must-have speed
changes. #96 needs native adaptation; reject #100/#101; preserve thermal policy,
existing BORE tuning, CFQ and block defaults. None of these fifteen was applied.
Candidate sources, previous review sources/contexts, approved #6/memlat/#36/#41
and miatoll defconfig remain unchanged. No new production build/device test,
commit, push or CI. **Next unassigned: #111 / A01-111.**

Additional [review11, #110](azyr-sm6250-review-11.md) compares the submitted GPU
idle-timer lockout with its original commit. Next unassigned: **#111 / A01-111**.

## Later user-approved application

Items #98 were subsequently approved and applied,
with native corrections where recorded in [the selected application](azyr-sm6250-selected.md).
Original review findings above remain historical; unselected items remain unapplied.
