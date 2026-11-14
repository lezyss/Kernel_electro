# Azyr sm6250 review 06 — continued items #54–#63

Status: **review only; none of #54–#63 applied, committed, pushed or sent to CI**.
Continues [#44–#53](azyr-sm6250-review-05.md), retaining stable identifiers
**A01-054 through A01-063**. Next unassigned: **#110 / A01-110**. Phoenix numbering
is separate and unchanged. Earlier #6, corrected memlat, corrected #36 and exact
#41 applications remain intact. Previous recommendations #46/#48/#52 have not
been approved/applied merely because they were shortlisted.

All ten exact commits and all fourteen changed-file patches were fetched through
the GitHub API, inspected against native sources and checked for complete
changed-line counts. Patch checks and donor applications used temporary copies
only. [Evidence receipt](azyr-sm6250-review-06-validation.json) contains source/
patch hashes, configuration and bounded host fixtures/results.

## Configuration and limits

Resolved the miatoll defconfig with the shipped Kconfig parser,
`ARCH=arm64 HOSTCC=gcc CC=gcc`, in an external output directory:

```text
CONFIG_DM_VERITY=y
CONFIG_DM_VERITY_FEC=y
CONFIG_BLK_CGROUP=y
CONFIG_IOSCHED_CFQ=y
CONFIG_CFQ_GROUP_IOSCHED=y
CONFIG_DEFAULT_CFQ=y
CONFIG_DEFAULT_IOSCHED="cfq"
CONFIG_QCOM_KGSL=y
CONFIG_PRINTK_TIME=y
# CONFIG_DEBUG_FS is not set
```

BLK_DEV_IO_TRACE resolves disabled (not enabled in generated configuration).
Configuration is not proof of runtime dm-verity use or a particular I/O path.
No production AOSP target object/image build, device boot, storage/GPU stress,
performance or power measurement was performed for this review.

## #54 / A01-054 — process-name-dependent cpufreq policy handling

Commit: [`d3cf6e4d15d895eaaa1dd5d94cf569130b810ded`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d3cf6e4d15d895eaaa1dd5d94cf569130b810ded)

Native `cpufreq_set_policy()` already clamps min to max when min > max. The donor
keeps that clamp only if some process's comm contains `libperfmgr`, scanning the
whole task list under tasklist_lock; otherwise it returns -EINVAL.

**Recommendation: skip.** A library is not reliably identified by a process
name. Android's power service can load it under another comm; process comm is
short, mutable and user-controlled, and an unrelated matching process can alter
this global decision. It also adds a process-list scan to policy updates and
reads comm without the normal task-comm accessor/locking. This is an unreliable
ROM-detection heuristic, not a generic min/max correctness improvement. Preserve
the native clamp rather than make it depend on unrelated process presence.

## #55 / A01-055 — magic PM-QoS value rewrites

Commit: [`c26cd77710e3768ce065d53c940a42db360d8629`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c26cd77710e3768ce065d53c940a42db360d8629)

After parsing a PM-QoS write, remaps numeric 0x44 (68) to decimal 44 and pretends
a write of 0x100 (256) succeeded without updating the request. Native parsing
accepts a four-byte binary s32 or a base-16 text value; the switch affects both
forms and is not scoped to one HAL, file, PM-QoS class or buggy text source.

**Recommendation: reject as a generic ABI workaround.** Valid requests for 68
or 256 acquire different semantics. Ignoring 256 can retain an earlier request,
not necessarily release/reset a vote. Fix the faulty userspace representation
or establish a narrowly scoped compatibility requirement; do not silently change
all PM-QoS consumers to fit an unverified libperfmgr configuration.

## #56 / A01-056 — high-priority dm-verity verification

Commit: [`69cf714073ebe9a68322e5d9041cb325220c0dcd`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/69cf714073ebe9a68322e5d9041cb325220c0dcd)

Adds WQ_HIGHPRI to the existing CPU_INTENSIVE/MEM_RECLAIM/UNBOUND verification
workqueue. This can reduce verification work's scheduling delay; it does not
change hash correctness, disable verity or make workers realtime tasks.

**Recommendation: plausible optimization candidate, preferably evaluated with
#57 as the donor sequence.** DM_VERITY is built in, but the ROM must actually
use a verity device for this path to matter. Higher-priority verification trades
against other CPU work; the donor's ramdisk/camera measurements are not results
on this storage/ROM. The comment referring to try_verify_in_tasklet does not
implement that absent feature in the native tree.

## #57 / A01-057 — bind dm-verity work and restore default admission limit

Commit: [`94a730ad07912c7157f227585a1a90c117e705bd`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/94a730ad07912c7157f227585a1a90c117e705bd)

Follows #56: removes WQ_UNBOUND and changes max_active from num_online_cpus() to
0. Final flags are CPU_INTENSIVE | MEM_RECLAIM | HIGHPRI. The native workqueue
default is 256 active works per CPU; that is an admission limit, not an instruction
to create 256 workers on every CPU. Memory-reclaim support is retained.

**Recommendation: sensible paired candidate with #56, conditional on runtime
verity and device validation.** Bound workers can improve locality/scheduling
behavior on asymmetric CPUs but reduce scheduler placement freedom and can
increase work on a submitting CPU. The changed concurrency/admission semantics
also matter; this is not simply removing one flag. Do not apply it as an EROFS
fix: this patch changes only dm-verity's workqueue.

The exact standalone hunk depends on #56's added flag/comment and does not apply
to the current preimage alone. The exact #56 then #57 sequence successfully
replays on temporary native copies. Test real verified-device reads, contention,
reclaim and verity error handling before claiming boot/camera/throughput gains.

## #58 / A01-058 — remove GPU IRQ debug counter reads

Commit: [`324bac57ebadbd785dbb0e666505b650880c4fa1`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/324bac57ebadbd785dbb0e666505b650880c4fa1)

Removes the always-on-counter read at IRQ entry, a read per nonzero-fence retry
and a read at fence failure, along with the diagnostic timestamps and now-unused
wrapper/prototype. Native A6xx's callback reads high/low/high registers (and may
reread low on rollover), so these can be multiple MMIO reads solely for debug
numbers even on successful interrupts.

**Recommendation: reasonable low-overhead candidate.** The wrapper has no other
native callers. The lower-level counter routine and operations remain because
other GPU code uses them. The patch retains fence polling/delay, pending-IRQ
accounting, keepalive, status reporting, fault marking and recovery dispatch;
it deliberately removes timing diagnostics rather than those safety mechanisms.

The tradeoff is less information when diagnosing fence faults. MMIO/timing
changes still need a target build plus GPU IRQ/fence/reset/suspend stress; no
measured FPS, power, or stability benefit is established here. KGSL is enabled,
but actual hardware callback use was not executed in this review.

## #59 / A01-059 — remove invalid-CPU WARN

Commit: [`aef1bd65ea60ae744a7d7f1162fd7ababe371a2b`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/aef1bd65ea60ae744a7d7f1162fd7ababe371a2b)

Changes `WARN_ON(cpu >= nr_cpu_ids)` to an ordinary bounds check in
`cpufreq_cpu_get()`. It still returns NULL without attempting the lookup for an
out-of-range CPU; the bounds protection is not removed.

**Recommendation: optional diagnostic policy, not an optimization.** This can
avoid repeated warning backtraces/taint (and panic-on-warn consequences) for a
bad caller, but also hides evidence of that caller. Diagnose any observed spam;
fixing the invalid argument or considering WARN_ON_ONCE may be preferable to
blanket suppression. No demonstrated native warning workload or performance gain.

## #60 / A01-060 — capture a cgroup named background

Commit: [`2c744e4f3929d36594c4bf781c077b67647b7122`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/2c744e4f3929d36594c4bf781c077b67647b7122)

Adds a global `blkcg_bg` and records the first successful blkg creation whose
cgroup name is exactly background. **It does not itself filter out I/O or assign
any priority.** The pointer is preparation for #61.

**Recommendation: skip this design.** A name does not uniquely identify a cgroup
path/hierarchy. There is no global publication/lifetime design, retained CSS
reference or clearing on cgroup destruction; later pointer comparisons can be
stale or misclassify reused addresses. The patch's consumers compare the pointer,
so this alone is not proof of a dangling-pointer dereference/UAF, but the tracking
is not robust. Per-queue locks do not provide a global registry across queues.

Crucially, native `blkg_create()` invokes policy pd_init callbacks **before** the
new capture point. That creates an initialization-order defect with #61.

## #61 / A01-061 — hard-coded CFQ root/background policy

Commit: [`b35a05e74293c808208f8ba5cd7cd376df5715a4`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b35a05e74293c808208f8ba5cd7cd376df5715a4)

Depends on #60's otherwise absent `blkcg_bg`. Sets shared cgroup data during
per-queue `cfq_pd_init()`: root weight 1000 / idle 2 ms; captured background
weight 200 / idle 0. It changes relative I/O service/idling policy, not a general
CFQ correctness rule. CFQ and group scheduling are enabled, so this is relevant
but not automatically appropriate for the ROM's hierarchy/storage.

**Recommendation: skip the donor pair.** In addition to #60's identity/lifetime
issues, it overwrites shared configured cgroup values during queue initialization.
Root already defaults to weight 1000 on the legacy hierarchy, but defaults differ
on the unified hierarchy; these are not universal equivalent defaults. Leaf
weights are also left unchanged.

An actual-donor-function host model following native creation order demonstrates
that the first background queue retains weight 500/idle 8 ms before capture,
while a subsequent queue gets weight 200/idle 0. Setting the cgroup weight to 777
and initializing another queue overwrites it with 200. These are bounded mocked
initialization examples, not real storage/concurrency measurements. Prefer
explicit userspace group policy and existing tunables over this name-based hook.

## #62 / A01-062 — CFQ trace guard with wrong variable

Commit: [`5663866d6cdf1761dd2fa9e96e888fb4e7d6d2ea`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/5663866d6cdf1761dd2fa9e96e888fb4e7d6d2ea)

Adds early guards to group-enabled CFQ logging macros, but uses **bfqd** even
though their parameter/local convention is **cfqd**. No bfqd exists at those
call sites. The trace helper itself already exists in this tree.

**Recommendation: reject unchanged; no benefit for this build.** The exact donor
macros fail a tracing-enabled host compile probe with undeclared bfqd. Correcting
that name makes the bounded probe compile. However, with tracing disabled,
`blk_trace_note_message_enabled(q)` expands to false without using its argument,
so the bad token is discarded and the probe compiles. **Do not claim it necessarily
breaks the current tracing-disabled build.**

The native trace-message macro already becomes a no-op when block tracing is
not configured, as here. A corrected guard could avoid argument evaluation when
tracing is compiled in but inactive; it is not a runtime optimization for this
selected profile. No need to enable tracing to make the patch relevant.

## #63 / A01-063 — broken sleep-inclusive printk timestamps

Commit: [`5dfd517cfa13ec0c7a9ac95619adc330742cda44`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/5dfd517cfa13ec0c7a9ac95619adc330742cda44)

Adds an accessor for the current cumulative sleep offset and adds it in
`print_time()`. **The addition is after `do_div(ts, 1000000000)`: ts is already
seconds, but the added offset is nanoseconds.** It is also after the NULL-buffer
size-probe return, so sizing and actual formatting disagree after sleep.

**Recommendation: reject; this is not just inaccurate logging.** An extracted
native/donor host fixture with a 12.3456789-second timestamp and 3 seconds of
sleep produces:

```text
native: [   12.345678]
donor:  [3000000012.345678]
NULL-buffer prefix size: 15 bytes for both
actual donor prefix:     20 bytes
```

Using the actual extracted `print_prefix()` and `msg_print_text()` too, an
18-byte logical output capacity permits a native 17-byte write but the donor
writes 22 bytes and overwrites the logical-boundary canary. Physical fixture
buffers are deliberately oversized to avoid real undefined memory access.
This proves a modeled violation of the caller's buffer-size contract, not an
actual kernel heap exploit; it is a serious formatting/safety defect nonetheless.

Moving the addition before division would not finish a correct design: adding
the *current* sleep total while rendering previously stored records changes
historical timestamps as later suspends accumulate. Native records store
local_clock timestamps. The added raw offset accessor also introduces a separate
uncoordinated read; an existing boot-fast accessor has its own documented
consistency limits and is not automatically a complete logging-clock solution.
A sleep-inclusive logging clock requires a separately reviewed timestamp-capture,
ordering, NMI/suspend and consumer-compatibility design—not this formatter patch.

## Summary

- **Most plausible candidates: #56 + #57 together**, if runtime dm-verity is used,
  and **#58**, trading debug timestamps for fewer GPU IRQ MMIO accesses.
- **#59** is optional warning/diagnostic policy, not a demonstrated speedup.
- **Skip #54/#55 and #60/#61**: userspace-name/magic-value hacks or fragile policy
  initialization/lifetime handling.
- **#62 is buggy for trace-enabled builds and unnecessary for this profile.**
- **Reject #63**: wrong units plus size-probe mismatch and logical buffer-bound
  violation in the extracted caller model.

Only review documentation/evidence changed. No kernel/defconfig edit, option
activation, commit, push or CI dispatch. **Next review: #95 / A01-095.**

Latest continuation: [#64–#73](azyr-sm6250-review-07.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#74–#83](azyr-sm6250-review-08.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.

## Later user-approved application

Items #56, #57, #58 were subsequently approved and applied,
with native corrections where recorded in [the selected application](azyr-sm6250-selected.md).
Original review findings above remain historical; unselected items remain unapplied.
