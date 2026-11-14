# Azyr sm6250 review 04 — continued items #34–#43

Status: following the user decision **“#36 and #41”**, corrected native **#36**
and exact **#41** are applied locally. Other #34–#43 items remain unapplied.
No new commit, push or CI dispatch. Original donor assessments below retained.
Continues [#26–#33](azyr-sm6250-review-03.md), preserving the same Azyr numbering:
**A01-034 through A01-043**. Next unassigned: **#110 / A01-110**;
continuation [#44–#53](azyr-sm6250-review-05.md) is recorded. The separate
Phoenix ledger is unchanged. Previously approved #6 and the corrected native
memlat adaptation remain intact; this review does not change those decisions.

All ten exact commits and all twelve changed-file patches were fetched through
the GitHub API and inspected against working sources. Changed-line counts were
checked against API metadata. Exact patch checks used temporary copies only;
the #38/#39 host comparisons patched temporary copies, never working sources.
Evidence: [configuration/source hashes and bounded host-model receipt](azyr-sm6250-review-04-validation.json).

## Current configuration and limits

Resolved `vendor/xiaomi/miatoll_defconfig` with the shipped Kconfig parser,
`ARCH=arm64 HOSTCC=gcc CC=gcc`, in an external output directory:

```text
CONFIG_SCHED_BORE=y
CONFIG_NR_CPUS=8
# CONFIG_FAIR_GROUP_SCHED is not set
# CONFIG_SCHED_WALT is not set
CONFIG_CPU_FREQ_DEFAULT_GOV_PERFORMANCE=y
# CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL is not set
CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y
CONFIG_CPU_FREQ_STAT=y
# CONFIG_HID_PLAYSTATION is not set
CONFIG_IPA3=y
CONFIG_SERIAL_MSM_GENI=y
CONFIG_MSM_PM=y
# CONFIG_PCI is not set
```

These are configuration results, **not runtime policy, a production target
build, device execution or performance measurements**. The ROM may choose
schedutil at runtime despite the compiled performance default. IPA/serial
configuration also does not prove that a particular optional path is exercised.

## #34 / A01-034 — mixed “Fix Compile” changes

Commit: [`75008653a3442cfe311a67da1de6887b205c52bc`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/75008653a3442cfe311a67da1de6887b205c52bc)

Three unrelated pieces:

- Adds `USB_DEVICE_ID_SONY_PS5_CONTROLLER_2 = 0x0df2`. Native
  `hid-playstation.c` references that undefined identifier, so this is a useful
  **optional-driver compile fix**. HID_PLAYSTATION is currently disabled, so it
  is not a fix for the selected miatoll build. Adding the define alone is also
  not complete DualSense Edge support: native match/probe paths still handle
  the original controller ID, not the second ID.
- Adds schedutil hispeed/PL constants, a `conservative_pl()` returning false,
  tunable fields and policy fields. The native governor has no users of those
  identifiers. These are missing pieces of some other governor series, not a
  functional hispeed/PL implementation for this tree.
- Adds `entity_is_task()`/`task_of()` helpers which are already present before
  the native BORE code. Blind insertion risks duplicate function definitions.

**Recommendation: do not apply the mixed commit.** The HID identifier can be
split out if repairing/enabling that optional driver is requested; no reason
to import the scheduler scaffolding. Exact donor patch check fails here.

## #35 / A01-035 — schedutil headroom 1.25 to 1.125

Commit: [`969455f6c9ffed3b33a11d9e03d5e139493e95c5`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/969455f6c9ffed3b33a11d9e03d5e139493e95c5)

Changes `(freq + (freq >> 2)) * util / max` to use `freq >> 3`. This reduces
the raw proportional request by approximately 10%, shifting nominal saturation
from 80% to about 88.9% utilization (before integer/table rounding, boosting,
policy limits and the native custom 20%-step chooser).

**Recommendation: defer as a power/responsiveness experiment, not a fix.**
Less headroom may lower clocks/power in some workloads, but can delay ramp-up,
hurt frame deadlines or extend work. It changes behavior only while schedutil
is the selected runtime governor. The existing explanatory 1.25/0.8 comment
would also become stale. No battery or performance benefit established here.

## #36 / A01-036 — IPA WDI sleep slack

Commit: [`28bc6f028c8ee2d2d972ed2284d0cb5973cf3c2d`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/28bc6f028c8ee2d2d972ed2284d0cb5973cf3c2d)

Changes one `ipa3_disable_wdi_pipe()` sleep from 10,000–10,000 us to
10,000–12,000 us: `IPA_UC_POLL_SLEEP_USEC` is 100, and the code squares it.
The minimum hardware wait is preserved; the additional 2 ms permits timer
coalescing but can lengthen pipe shutdown. Another equal-min/max sleep remains
elsewhere in this file; the patch does not overhaul IPA timing or fast-path
packet processing.

**Recommendation: reasonable small cleanup in corrected integer form**, if
this WDI path is used: compute `delay` and use `delay + delay / 5` as the maximum.
Avoid the unnecessary floating literal `1.2` in kernel code. A bounded host
GCC `-O2 -mgeneral-regs-only` fixture confirms the donor's constant expression
folds to 12,000; **do not claim it necessarily emits runtime floating point or
fails the production compiler**. No AOSP target compilation was performed here.

The commit message's sleep-state explanation is misleading: native
`usleep_range()` still uses TASK_UNINTERRUPTIBLE for either range. The benefit
is scheduling slack, not making the wait interruptible/preemptible. Expected
impact is small and path-dependent, not a general Wi-Fi throughput improvement.

## #37 / A01-037 — deep-idle helper 10 to 2

Commit: [`161e2cdf1941a5537c9423fb2083b95f71354172`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/161e2cdf1941a5537c9423fb2083b95f71354172)

Changes `msm_cpuidle_get_deep_idle_latency()` from 10 to 2. Native audio/codec
and SoundWire consumers pass this result into `pm_qos_update_request()` while
holding audio wake/sleep locks. It is a **stricter latency constraint** at those
consumers, not a reduction in hardware exit time and not a rewrite of the
cpuidle states' advertised exit latencies.

**Recommendation: skip without a diagnosed audio-latency problem and measured
state/latency data.** The tighter constraint may exclude more idle states and
increase power; it cannot make the hardware wake five times faster. The fact
that the helper already returns a constant does not validate a smaller one.

## #38 / A01-038 — IRQ-domain free revert

Commit: [`4b8def97dcd06bae696bc7079c9b7a217c6c8d8b`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/4b8def97dcd06bae696bc7079c9b7a217c6c8d8b)

The native `irq_domain_free_irqs_hierarchy()` checks each IRQ's domain data and
calls `ops->free(domain, irq, 1)` individually. The revert instead calls
`ops->free(domain, irq_base, nr_irqs)` once, without the per-IRQ checks.
Native `drivers/pci/host/pci-msm-msi.c` has a range-aware free callback operating
on the allocation bitmap, client IRQ count and parent domain, so this is a
plausible lifecycle/correctness investigation rather than a speed tweak.

**Recommendation: defer pending a demonstrated affected lifecycle; not a blind
modem-crash fix for this build.** PCI is disabled in the selected configuration,
so the message's particular MSM PCI MSI path is not built here. Generic IRQ-domain
code is active and other domain free callbacks would still change behavior.

An extracted-helper host fixture confirms the semantic difference: a mapped
four-IRQ range becomes four single-IRQ callbacks natively and one four-IRQ
callback with the donor. With a missing domain-data entry, the donor still
passes the full range whereas native skips that entry. This is **not a modem
crash reproduction** and does not establish that the native MSM callback leaks
or fails when called per IRQ. The message's dynamic-virq explanation alone is
not proof: `irq_domain_get_irq_data()` walks the actual virq's domain chain,
not a fixed hardware-IRQ-to-virq assumption. Audit valid/partial/unwind and parent
free paths and stress allocation/free before choosing a correction or revert.
The referenced reverted SHA was unavailable through this donor repository's
commit endpoint, so its original rationale was not independently established.

## #39 / A01-039 — interruptible synchronize_irq wait

Commit: [`f5628227d7ea4d495c3c6edcf65e8eca2d551302`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f5628227d7ea4d495c3c6edcf65e8eca2d551302)

Replaces `wait_event()` in `synchronize_irq()` with
`wait_event_interruptible()`, discarding the result. The documented kernel
wait macro may return `-ERESTARTSYS` on a pending signal even when
`threads_active` is still nonzero. `synchronize_irq()` is void and promises
that handlers are finished before returning; its callers cannot recover from
this silently interrupted wait.

**Recommendation: reject.** This can let teardown/free/reconfiguration race a
still-running threaded handler, including lifetime/use-after-free hazards.
TASK_UNINTERRUPTIBLE does not mean that the task cannot be scheduled out; the
original wait already sleeps. The commit's preemption argument is wrong.

A host model compiled the actual native and exact donor function bodies with
mock wait semantics matching the documented signal/error behavior. In the
pending-signal, active-handler case, native returns after the model drains the
handler; donor returns with `threads_active=1`. All four signal/active combinations
are recorded. This demonstrates the control-flow/API problem, not real kernel
threading or signal-delivery execution.

## #40 / A01-040 — serial wake-byte lock 2 s to 100 ms

Commit: [`ba48a7fa0e40f5d908b01182dec4939b96503983`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/ba48a7fa0e40f5d908b01182dec4939b96503983)

Changes `WAKEBYTE_TIMEOUT_MSEC` from 2000 to 100. The native wakeup ISR applies
this after the configured wake-byte/edge-count condition and flip-buffer push;
it is not a blanket reduction for every UART interrupt. GENI serial is enabled;
the Atoll DT contains a wake-byte-enabled high-speed UART, although this review
does not establish runtime use or a particular device/ROM's response bound.

**Recommendation: defer to suspend/RX stress testing.** It can reduce wake-source
hold time in this path, but an average userspace response below 10 ms does not
prove a 100 ms worst-case budget during cold resume, congestion or heavy load.
Early resuspend or lost/delayed serial data are risks to validate. Do not call
it a free battery win from the constant change alone.

## #41 / A01-041 — cpufreq stats unlikely hints

Commit: [`b0229e526d8593782fa4806e28b16542b836bf61`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b0229e526d8593782fa4806e28b16542b836bf61)

Wraps the no-stats guard and invalid/unchanged-index guard in `unlikely()`.
Conditions, statistics and locking are unchanged. CPU_FREQ_STAT is enabled;
transition and fast-switch paths call this helper.

**Recommendation: low-risk optional micro-cleanup, not an important optimization.**
It expresses a branch-layout expectation; useful code-layout/performance effects
are compiler/workload-dependent, and an unchanged index need not always be rare.
No new functionality or correctness repair and no measured gain. This is the
cleanest small drop-in candidate in the batch, but not worth expecting noticeable
phone responsiveness or battery improvement.

## #42 / A01-042 — enable TTWU_QUEUE

Commit: [`91e171dd601acabb5ee768dba85df3bdad2e3296`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/91e171dd601acabb5ee768dba85df3bdad2e3296)

Changes the TTWU_QUEUE feature default from false to true. Native
`ttwu_queue_cond()` queues when the already selected target does not share the
waker's cache, or in its WF_ON_RQ/low-nr_running case. The wakelist is processed
on the chosen target CPU; this patch does **not** add a cache-sharing CPU
selection algorithm or retarget tasks as the subject might imply.

**Recommendation: defer; preserve current wakeup policy.** Queuing can reduce
remote rq locking/cacheline traffic under contention, but adds deferred
activation/IPI tradeoffs and changes an already customized wakeup path. Test
wake-to-run latency, scheduler contention, app/frame workloads and power with
the current PELT/CASS/BORE stack before considering it. No throughput or
interactive-latency improvement follows just from enabling the feature.

## #43 / A01-043 — linear scheduler tunable scaling

Commit: [`23405aa7c10147bd83ce6167f949b8331bfa48d0`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/23405aa7c10147bd83ce6167f949b8331bfa48d0)

Changes the donor's LOG default to LINEAR. Native BORE deliberately uses NONE
with 24 ms latency, 5 ms minimum granularity and 4 ms wakeup granularity; LOG
exists only in the non-BORE branch. The exact donor patch fails its context
check here. Changing just that legacy branch would be inactive with BORE.

**Recommendation: skip for this tree.** If instead forcing LINEAR onto the active
BORE branch with eight online CPUs, the scaling factor becomes 8 instead of 1:
24/5/4 ms becomes 192/40/32 ms. For the legacy LOG branch the factor would be
8 instead of 4. These are substantial latency/granularity policy changes, not
an automatic performance improvement; preserve the approved BORE constants.

## Recommendation summary

- Small plausible candidates: **#36 in integer form**, and **#41 as an optional
  low-impact branch hint**.
- **#34 HID-ID fragment only** is an optional-driver compile cleanup, not a
  reason to import the mixed scheduler changes or enable that driver.
- **#38** merits investigation if an affected IRQ-domain teardown is reproduced;
  the claimed PCI/MSI modem fix is not demonstrated for this PCI-disabled build.
- **Reject #39. Skip #37/#43 as generic optimizations.**
- **#35/#40/#42** are policy/latency/power experiments requiring a controlled
  device comparison, not default improvements.

The initial review was documentation/evidence only. The later approved local
application is recorded below. **Next: #95; see [review 09](azyr-sm6250-review-09.md).**


## Subsequent approval — #36 corrected and #41 applied

User decision: “#36 and #41”. Applied only:

- **#36:** in `ipa3_disable_wdi_pipe()`'s producer branch, a local integer
  `delay_us` preserves the 10,000 us minimum and sets the maximum to
  `delay_us + delay_us / 5` (12,000 us). No floating literal, no change to the
  other equal-bound sleep or any other IPA path. Additional slack may lengthen
  this shutdown wait; no throughput or power improvement is established.
- **#41:** exact donor two `unlikely()` annotations. Temporary donor-patch replay
  matched the working postimage byte-for-byte. No condition, accounting or lock
  changes.

Bounded validation PASS: exact two-source patch/inverse and reviewed preimage
hashes; extracted integer delay check under host GCC + UBSan + general-registers
only; 180 before/after cpufreq transition cases including absent stats, invalid
indices, same-index and normal matrix/counter updates; three compiled semantic
negative controls. Memlat, SUSFS full-profile/provenance/priority negative,
KernelSU and NoMount host regressions PASS. Other review-04 sources, #6,
corrected memlat and the source miatoll defconfig are unchanged.

No pinned-AOSP ARM64 object/full image/modules build, device boot, firmware/
WLAN/RX/suspend stress, or performance/power measurement was performed for these
changes. Host-model success is not production/runtime proof.

Evidence: [patch](azyr-sm6250-036-041.diff),
[receipt](azyr-sm6250-036-041-validation.json),
[transcript](azyr-sm6250-036-041-validation.txt), and
`tools/testing/selftests/cpufreq_ipa/{README,test_tuning.py}`.
No new commit, push or CI dispatch. Next review number is **#95**; see [review 09](azyr-sm6250-review-09.md).

Latest continuation: [#64–#73](azyr-sm6250-review-07.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#74–#83](azyr-sm6250-review-08.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.
