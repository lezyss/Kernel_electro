# Azyr sm6250 review 08 — continued items #74–#83

Status: **review only; none of #74–#83 applied, committed, pushed or sent to CI**.
Continues [#64–#73](azyr-sm6250-review-07.md), retaining stable identifiers
**A01-074 through A01-083** in submitted order. Next unassigned: **#110 / A01-110**.
Phoenix numbering remains separate. Earlier approved #6, corrected native memlat,
corrected #36 and exact #41 remain intact. Boeffla remains explicitly excluded;
submitting its link for review does not reverse that instruction.

All ten exact commits and all **16 changed-file patches** were fetched through
the GitHub API, read against native sources and checked for complete changed-line
counts. Patch applications and probes used temporary copies, never native source
edits. The [evidence receipt](azyr-sm6250-review-08-validation.json) includes exact
patches/hashes, applicability checks, fixtures/results, configuration and
preservation checks.

## Configuration and limits

Resolved the miatoll defconfig successfully with the shipped Kconfig parser,
`ARCH=arm64 HOSTCC=gcc CC=gcc`, using an external output directory:

```text
CONFIG_CPU_FREQ=y
CONFIG_SCHED_BORE=y
CONFIG_QCOM_QMI_HELPERS=y
CONFIG_USB_RTL8152=y
CONFIG_DRM_MSM=y
CONFIG_DRM_MSM_DSI_STAGING=y
CONFIG_HZ=100
# CONFIG_USB_RTL8150 is not set
# CONFIG_QCOM_QMI_RMNET is not set
# CONFIG_DEBUG_KERNEL is not set
# CONFIG_DYNAMIC_DEBUG is not set
# CONFIG_WQ_POWER_EFFICIENT_DEFAULT is not set
# CONFIG_ARM64_LSE_ATOMICS is not set
```

QCOM_QMI_POWER_COLLAPSE, legacy FB_MSM_MDSS and Boeffla are also unselected/absent
in the resolved configuration. QMI_HELPERS does **not** imply QMI_RMNET; USB_RTL8152
does **not** select the distinct RTL8150 driver. Native Kbuild guards establish
which exact files are omitted. Configuration is not runtime traffic/governor or
hardware-feature evidence.

Host GCC -O2/UBSan checks are bounded source/control-flow models, not the required
production AOSP compiler or an ARM64 build. No target objects/image, real device
boot, cpufreq teardown, USB disconnect, modem/suspend/display stress, atomic
benchmark, power or performance measurement was performed here.

## #74 / A01-074 — RTL8150 submission-error memory leak

Commit: [`bf4a4afcff179dc46ffca5189a2321a1dd656ccf`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/bf4a4afcff179dc46ffca5189a2321a1dd656ccf)

Adds kfree(req) and usb_free_urb(async_urb) when usb_submit_urb returns an error.
Native async_set_reg_cb owns those objects after a successful submission, but a
failed submission has no completion callback to release them. The native USB
API documentation describes completion ownership on successful submission.
The added error cleanup does not change the success callback path or -ENODEV
netif_device_detach behavior.

The extracted submit/callback model covers request and URB allocation failures,
submission failures (-ENODEV, -EPIPE, -ENOMEM), and successful submissions followed
by successful/error completions. Native submission failures leave **two**
allocations outstanding; donor leaves **zero**. Both variants correctly release
objects after successful submission/completion and on the earlier allocation
failure paths. This models the USB ownership contract, not real hardware races.

**Recommendation: sound optional generic bug fix.** It is not a phone-network
speedup: CONFIG_USB_RTL8150=n here, while RTL8152 is a separate enabled driver.
Shortlist only if inactive-driver maintenance is wanted; no activation needed
or authorized. Exact application succeeds on temporary native copies.

## #75 / A01-075 — remove a supposedly duplicate task_of

Commit: [`afee9e3a963d04bf0b0a85fcaeb50a57ff2d7717`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/afee9e3a963d04bf0b0a85fcaeb50a57ff2d7717)

**Recommendation: skip; donor-local integration repair, not a native fix.**
This tree has **one**, not two, task_of definitions in kernel/sched/fair.c, before
the BORE helpers. The definition performs the entity check and container_of;
native BORE and ordinary fair-scheduler callers use it. No alternative task_of
macro/helper was found in include/ or kernel/sched/.

The exact patch fails context application against the native BORE integration.
Forcing its intended deletion would remove the only helper. A minimal probe
using the native helper and a representative task_of caller compiles before
deletion, then fails with implicit-declaration/pointer-conversion diagnostics
after deletion. That is a counterfactual helper-deletion probe, not a full
scheduler target build or a claim that this failing patch was actually applied.
Preserve the existing corrected BORE integration.

## #76 / A01-076 — replace QMI powersave alarm with delayed work

Commit: [`842f38fd158fb49590d64b866b91b99378dbfd8d`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/842f38fd158fb49590d64b866b91b99378dbfd8d)

Removes the ALARM_BOOTTIME timer/callback and its init/cancel, requeues normal
delayed work instead, and replaces INIT_DEFERRABLE_WORK with INIT_DELAYED_WORK.
Avoiding an RTC-capable alarm could reduce suspend wakeups, but the new ordinary
non-deferrable timer can still wake an idle CPU while the system is running.
This is a change in polling/suspend policy, not an unconditional power saving.

**Concrete native regression despite successful textual application:** the patch
inserts packet sampling and dl_msg_active consumption before the ps_enabled
branch **without deleting the existing sampling block below it**. Native
rmnet_get_packets sums cumulative per-CPU packet statistics. On the normal
non-powersave path the donor now samples twice, overwrites the saved baseline
twice and reads/clears dl_msg_active twice.

If cumulative RX rises from 100 to 110 before a check and stays at 110 between
its two getter calls, the second delta becomes zero, discarding all ten packets
that should keep the link active. An actual-function host model gives:

```text
native: ps=0 reads=1 sets=0 alarms=1 queues=0 old_rx=110
donor:  ps=1 reads=2 sets=1 alarms=0 queues=0 old_rx=110
```

With no new packets, a disabled flow and dl_msg_active=true, native enters
powersave as allowed by its indication; donor consumes the indication in the
first block, sees false in the second and instead requeues. Thus this is also
lost activity-indication information, not merely redundant reads. The model
also covers ordinary idle entry and exit from powersave; no modem failure or
battery impact has been reproduced on hardware.

The powersave block is guarded by QCOM_QMI_POWER_COLLAPSE, whose parent
QCOM_QMI_RMNET is **disabled** here. qmi_rmnet.o itself is omitted by Kbuild.

**Recommendation: reject the exact native replay.** If this policy is ever
wanted on an enabled path, move rather than duplicate the sampling block and
review timer/freezer/teardown behavior. Do not activate this unused subsystem
just to obtain the advertised saving.

## #77 / A01-077 — unbound/freezable QMI powersave queue

Commit: [`150f5023d9f3b1dd5b17312826c1aa8739340e53`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/150f5023d9f3b1dd5b17312826c1aa8739340e53)

Replaces a bound WQ_CPU_INTENSIVE queue, max_active 1, with
create_freezable_workqueue. The native macro provides
__WQ_LEGACY | WQ_FREEZABLE | WQ_UNBOUND | WQ_MEM_RECLAIM, max_active 1. It adds
freezer behavior and reclaim support and removes CPU_INTENSIVE as well as CPU
binding. It is not a high-priority or real-time queue.

Both standalone application and **#76 → #77** ordered application succeed, but
#77 does **not** repair #76's duplicate sampling. Its rationale assumes the
alarm-free policy, even though there is no textual dependency. Applied alone,
the native alarm remains while work execution becomes freezable; queueing and
execution during suspend are distinct concerns. Modem/packet restarts, suspend
latency, QMI progress and teardown need validation for the chosen complete policy.

**Recommendation: skip for the current profile.** This queue is in the same
disabled QMI_RMNET powersave path. Potentially reasonable as part of a corrected,
explicitly enabled power-policy adaptation, not an independent proven saving.

## #78 / A01-078 — balance topology cpufreq policy references

Commit: [`3ea82acbb35fa12d0c3d09b0f9137240b532e536`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3ea82acbb35fa12d0c3d09b0f9137240b532e536)

**Recommendation: the strongest candidate in this batch; genuine native
correctness fix.** Native detect_share_cap_flag calls cpufreq_cpu_get per possible
CPU and never puts the successfully acquired reference. cpufreq_cpu_get takes a
policy kobject reference, and native cpufreq_cpu_put releases it. Persistent
leaks can prevent the policy's release completion during teardown/failure paths;
this is not a CPU frequency or scheduler tuning change.

The donor adds a put before each of the die/core/thread-match continue paths,
and at the end of the no-match path. The NULL-policy return acquired no current
reference; earlier loop iterations have already put theirs. No policy data is
used after the added put in that iteration. CPU_FREQ=y here, and native topology
flag detection calls this function.

The extracted native/donor function model runs ten invocations for each of
seven cases: die, core, thread, no match, mixed masks, NULL first CPU, NULL fourth
CPU. For full eight-CPU cases, native accumulates **80** references and donor
balances **80 gets / 80 puts, zero outstanding**. For the fourth-CPU NULL case,
native leaks 30 and donor balances all 30. NULL-first performs no get/put.
This is reference-accounting evidence, not a real hotplug/unbind hang reproducer.
Exact patch application succeeds; no prerequisite among these ten is needed.

## #79 / A01-079 — remove IOMMU group-add informational logging

Commit: [`3e87d0295c39b2bb9d080a6db7464a0de7a8d651`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3e87d0295c39b2bb9d080a6db7464a0de7a8d651)

Deletes only the successful "Adding device ... to group ..." pr_info call.
Group creation/attachment, the trace_add_device_to_group call, error handling
and return status remain intact. Unlike #65 this is not a broad CPU/suspend/OOM
log demotion; its tradeoff is quieter successful device enrollment versus less
visible group-assignment information in dmesg.

**Recommendation: optional log policy, low priority.** It may reduce boot/device-
enumeration printk volume, but is not demonstrated steady-state performance.
Keeping useful diagnostics is also reasonable. No IOMMU or DMA behavior is fixed.

## #80 / A01-080 — hide parent-device sleeping warning

Commit: [`ecf86f1aee946087a44bb69979cf5c0590c50a04`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/ecf86f1aee946087a44bb69979cf5c0590c50a04)

Wraps device_pm_add's parent->power.is_prepared warning in CONFIG_DEBUG_KERNEL.
DEBUG_KERNEL=n here, so the diagnostic condition/message would disappear.
The native message is dev_warn, not a WARN_ON/panic/taint mechanism. Device
registration and PM-list insertion proceed the same way before and after the
patch; the sleeping/prepared parent situation is not repaired.

**Recommendation: skip; retain the PM lifecycle diagnostic.** This conceals
potentially useful device-registration-during-suspend evidence, not its cause.
There is no demonstrated hot-path saving. DEBUG_KERNEL=y builds retain it.

## #81 / A01-081 — legacy MDSS delayed clock-off workqueue

Commit: [`e0a580013db9c16bf87fef8f44ed2cd7bd1758a3`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/e0a580013db9c16bf87fef8f44ed2cd7bd1758a3)

Moves two delayed_off_clk_work enqueue sites from system_wq to
system_power_efficient_wq. Timeout, callback and cancellation remain unchanged;
this is not a driver-wide migration of every work item. The callback still
flushes gate_clk_work to protect the ordering it documents.

**Recommendation: skip for miatoll; wrong display stack for this profile.**
mdss_mdp_intf_cmd.o belongs to legacy CONFIG_FB_MSM_MDSS, unselected here. The
active configured stack is DRM_MSM / DSI_STAGING, not this fbdev MDSS code.
Do not transplant its changes blindly into DRM/SDE.

Moreover, system_power_efficient_wq is created with WQ_POWER_EFFICIENT, and only
becomes unbound if workqueue.power_efficient is enabled. Its default comes from
WQ_POWER_EFFICIENT_DEFAULT, which is disabled here; a boot parameter can override
that policy. Merely choosing this queue therefore does not guarantee migration
to whichever CPU saves power. Runtime policy and clock-off/display stress would
be needed on a system actually using this legacy driver.

## #82 / A01-082 — introduce Boeffla wakelock blocker

Commit: [`75543139c17f9a67e1ae7826397efa6624fae52a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/75543139c17f9a67e1ae7826397efa6624fae52a)

**Skip under the explicit existing Boeffla exclusion.** This is the absent
framework's introduction, not a fix to a feature already integrated. It adds
C/header sources, sysfs interfaces, PM wakeup hooks, Kconfig/Makefile wiring and
a donor stock_defconfig setting. It is a different submitted item from the
previously skipped Boeffla follow-ups [#11–#25](azyr-sm6250-review-02.md).

Importantly its Kconfig entry has **default y whenever PM is enabled**. The
stock_defconfig hunk is not the only activation mechanism: a configuration with
PM=y and no explicit Boeffla setting picks y in an isolated shipped-Kconfig
probe. It would therefore violate the standing generic/default behavior, not
merely add an inert selectable driver. The actual header's LIST_WL_DEFAULT is
**empty**, despite older history comments listing WLAN/netlink names; do not
claim those names are automatically blocked by this exact initializer.

Independent code problems reinforce the exclusion:

- Both stores accept n equal to the array capacity and use unbounded sscanf %s.
  A 255-character user token needs 256 bytes; a 100-character default token needs
  101. Actual extracted stores overwrite a logical-end canary with NUL in a
  physically oversized backing-buffer model. These are root-controlled sysfs
  inputs, not proof of an unprivileged or remote exploit.
- check_for_block uses char wakelock_name[52] but permits a 50-character name.
  Formatting semicolon + 50 characters + semicolon + NUL requires **53 bytes**.
  A separate logical-capacity model confirms the one-byte boundary violation.
- Sysfs list rebuilding and wakeup-path readers have no publication/locking
  protocol. The diagnostic pm_get_active_wakeup_sources path can call the new
  helper and deactivate a source under SRCU without its per-source spinlock;
  native __pm_relax/timer deactivation uses that lock. A reporting path gaining
  this state-changing side effect requires far more than list matching.
- Init ignores misc_register's return before dereferencing this_device, and exit
  does not misc_deregister. Those lifecycle errors are separate from blocking
  legitimate wakeups/data processing.

No blocker was added, configured or activated. A syntactically applicable patch
is not authorization to reintroduce this rejected framework.

## #83 / A01-083 — operand prefetch for LSE atomics

Commit: [`48baf85401850874c56d37db0a6d944f8e2d5236`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/48baf85401850874c56d37db0a6d944f8e2d5236)

Adds prfm pstl1strm before the selected LSE atomic operations and matching extra
NOP padding in their LL/SC alternatives. It does not enable LSE, convert the
ordinary LL/SC implementation or change the acquire/release variant selection.
The donor benchmark concerns Kryo 485 / Snapdragon 855, not a measurement on
this phone/tree/compiler/workload.

A preprocessing/string inspection expands all **95 alternative pairs** from the
actual native and donor header. Every donor LSE path adds only the leading
prefetch instruction; every fallback adds one NOP, and native/donor alternative
instruction counts remain paired. This checks macro expansion/padding intent,
not AArch64 assembly, ELF alternative relocations, memory-ordering correctness or
hardware timing. No target assembler/compiler is available for such a proof in
this review.

**Recommendation: skip for the current configuration.** CONFIG_ARM64_LSE_ATOMICS
is disabled; native atomic.h selects atomic_ll_sc.h instead of this header.
Thus this patch has no selected-path effect. Even in an LSE-enabled kernel,
runtime feature detection matters: an unsupported CPU takes the padded LL/SC
alternative, not the new prefetch path. Do not enable LSE or transfer donor
benchmark claims automatically. It could be reconsidered with explicit LSE
configuration, runtime feature evidence and target workload tests.

## Summary and preservation

- **#78 is the main recommendation:** fix a real, selected-path policy-reference
  leak without changing tuning/defaults.
- **#74 is a valid optional generic leak fix**, but its RTL8150 driver is disabled.
- **#79 is optional quiet-boot policy**, not a measured optimization.
- **Reject exact #76** for duplicate sampling/lost indications; #77 does not fix
  it and both are in an inactive QMI path. **Do not force #75** onto the correct
  native scheduler helper layout.
- **Skip #80/#81/#83** for retained PM diagnostics, inactive legacy display code,
  and disabled LSE implementation, respectively. **#82 remains excluded.**

Standalone textual checks pass for all except #75. Ordered #76→#77 applies on
temporary copies but retains the demonstrated defect. Candidate/previous review
sources and contexts, approved #6/memlat/#36/#41 postimages, absent Boeffla files,
and miatoll defconfig are unchanged. Navigation now continues at **#95 / A01-095**.
No kernel/defconfig edit, activation, commit, push or CI dispatch.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.

## Later user-approved application

Items #78, #79 were subsequently approved and applied,
with native corrections where recorded in [the selected application](azyr-sm6250-selected.md).
Original review findings above remain historical; unselected items remain unapplied.
