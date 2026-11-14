# Azyr sm6250 review 07 — continued items #64–#73

Status: **review only; none of #64–#73 applied, committed, pushed or sent to CI**.
Continues [#54–#63](azyr-sm6250-review-06.md), retaining stable identifiers
**A01-064 through A01-073**. Next unassigned: **#110 / A01-110**. Phoenix numbering
remains separate and unchanged. Earlier approved #6, corrected native memlat,
corrected #36 and exact #41 remain intact. Shortlisting is not application approval.

All ten exact commits and all **22 changed-file patches** were fetched through
the GitHub API, read against native sources, and checked for complete changed-line
counts. Patch applications and probes used temporary source copies, never the
working kernel tree. The [evidence receipt](azyr-sm6250-review-07-validation.json)
records hashes, patches, configuration, dependency checks, fixtures and results.

## Configuration and validation limits

The shipped Kconfig parser successfully resolved the miatoll defconfig using
`ARCH=arm64 HOSTCC=gcc CC=gcc`, with output outside the repository:

```text
CONFIG_ARM64=y
CONFIG_ARCH_ATOLL=y
CONFIG_NR_CPUS=8
CONFIG_SMP=y
CONFIG_QCA_CLD_WLAN=y
CONFIG_QCOM_KGSL=y
CONFIG_DRM_MSM=y
CONFIG_DEVFREQ_GOV_MEMLAT=y
CONFIG_QPNP_SMB5=y
CONFIG_USB_OHCI_HCD=y
CONFIG_USB_OHCI_HCD_PLATFORM=y
# CONFIG_CHARGER_QCOM_SMBB is not set
# CONFIG_DYNAMIC_DEBUG is not set
```

LPC32xx architecture/NXP OHCI glue is not enabled. Generic OHCI platform support
is **not** evidence that `ohci-nxp.c` builds on this target. Configuration is not
proof of runtime governor, panel, USB path or charging behavior. Host GCC is used
only for Kconfig and bounded probes, not as the production kernel toolchain.
No production AOSP ARM64 object/image build, device boot, GPU/display/WLAN/USB
stress, suspend testing, performance or power measurement was performed here.

## #64 / A01-064 — dedicated GPU command-dispatch kthread

Commit: [`5a139ae285b93f2aec4b09e133272122e42e2d3e`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/5a139ae285b93f2aec4b09e133272122e42e2d3e)

Replaces inline submission and shared-worker dispatch with a dedicated kthread,
atomic send flag and waitqueue, setting SCHED_FIFO priority 16 inside the thread.
Also removes the old submit lock/submit-now/slumber protocol. This changes five
files and is a scheduling/lifecycle redesign, not just a faster queue primitive.

Native deferred dispatch already uses `kgsl_driver.worker`, whose thread is
SCHED_FIFO 16 and created with `kthread_run_perf_critical(cpu_perf_mask, ...)`.
The donor's plain `kthread_run()` does not preserve that explicit placement policy.
Moving formerly inline submissions to another thread can introduce a handoff;
isolation from other KGSL worker jobs might help, but an automatic latency gain
cannot be inferred from the title.

**Concrete initialization defect:** the new thread starts before fallible
`kobject_init_and_add()`. Its error return does not stop the thread. Native
`adreno_probe()` goes directly to ringbuffer/platform cleanup on dispatcher-init
failure, without calling `adreno_dispatcher_close()`. Thus the new thread is not
unwound by the caller either. An extracted init-body probe, mocking successful
thread creation and a -ENOMEM kobject failure, gives:

```text
native_init_ret=-12 live_threads=0
donor_init_ret=-12 live_threads=1
```

This is a lifecycle model, not an executed GPU use-after-free reproducer. A live
thread retaining dispatcher state across platform cleanup is nevertheless a real
unwind/lifetime problem in the submitted code. Teardown ordering, enqueue/stop
races, GPU faults, slumber, fences and submission latency also need real testing.

**Recommendation: reject the exact patch.** Any future adaptation needs correct
thread failure unwinding, explicit affinity/priority decisions and full GPU
lifecycle validation, not a blind cherry-pick.

## #65 / A01-065 — suppress informational logs

Commit: [`57c52f760fa85b88c133e59b84a57013d5998674`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/57c52f760fa85b88c133e59b84a57013d5998674)

Ten log-call substitutions across six files demote CPU boot/shutdown/resume-up,
device-link creation/deletion, GIC redistributor discovery, IRQ affinity-break
and OOM-killer enable/disable messages to debug equivalents. Control flow and
functional operations are unchanged; failure messages such as CPU death failure
are not removed by this patch.

**Recommendation: skip the batch under the standing native suspend-log policy.**
The tradeoff is quieter logs versus lost diagnostic breadcrumbs, not proven
steady-state performance. It includes suspend/hotplug and OOM transitions, not
just repeated device-link chatter. Dynamic debug is disabled in this profile;
these debug calls are generally suppressed unless the relevant DEBUG build
setting enables them. A separately selected narrower log policy could be
reasonable, but no logging changes are authorized here.

## #66 / A01-066 — replace public PM-QoS cpumasks with atomic bits

Commit: [`8e40dd2c6aadd380a63fdd3b97a7be822321746c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/8e40dd2c6aadd380a63fdd3b97a7be822321746c)

Changes `pm_qos_request.cpus_affine` from `struct cpumask` to `atomic_t`, rewrites
QoS iteration using a stack unsigned long cast as a cpumask, replaces some mask
locks with atomics and constructs an all-CPU mask using `BIT(NR_CPUS) - 1`.

The eight-CPU target fits the new representation, but native masks already fit
one machine word. **atomic_t is signed 32-bit, not ARM64 unsigned long.** General
configurations lose CPU bits above 31; reading bit 31 into unsigned long can sign
extend; one-word stack-backed cpumasks and word-width shifts are not generally
valid for arbitrary NR_CPUS. The bounded width model preserves all 256 eight-bit
values, sign-extends bit 31 to `0xffffffff80000000`, and truncates bit 32 to zero.
Those higher-CPU examples are generic hazards, not CPU31/32 failures observed on
miatoll.

More immediately, this is a public in-tree interface change requiring complete
consumer migration. #67 does not finish it. No measured QoS contention benefit
justifies that risk, and atomic field access alone is not a lifecycle/locking
correctness proof.

**Recommendation: reject the incomplete generic conversion.** Do not apply #66
alone or assume that adding #67 makes the native tree consistent.

## #67 / A01-067 — partial driver conversion for #66

Commit: [`fae8cd95edb1e9b249b9a2f779ed04692b1786e8`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/fae8cd95edb1e9b249b9a2f779ed04692b1786e8)

Converts SDHCI, `techpack/audio/4.0/asoc/kona.c` and the older
`techpack/audio/asoc/sm6150.c`. It requires #66's type change; successful textual
application against old sources does not mean it compiles against the old type.

The ATOLL build selects audio 4.0, whose `CONFIG_SND_SOC_ATOLL` maps to **kona.o**:
that selected audio path *is* converted. Other audio variants, including 4.0
sm6150, remain unconverted, but are not evidence of an ATOLL build failure by
themselves.

**Selected WLAN is still unconverted.** qcacld's default config enables
`CONFIG_WLAN_CLD_PM_QOS`; Kbuild supplies `CLD_PM_QOS` and, on QCOM, `MSM_PLATFORM`.
On this 4.14 kernel the guarded affinity helpers still use cpumask_copy,
qdf_cpumask_clear, cpumask_set_cpu and cpumask_pr_args on `cpus_affine`. A minimal
probe of its unchanged COPY_CPU_MASK call passes with the native cpumask field
but fails GCC -Werror with the donor atomic_t field due to incompatible pointer
types. This is an interface probe, not a complete WLAN target build. Silencing
those type warnings would not turn the cpumask operations into atomic operations
or fix their incompatible representation.

SDHCI also retains **two `%lx` formats while supplying atomic_read(), an int**;
a format-check probe diagnoses the mismatch. The pair applies on temporary
copies, but that is not a complete or type-safe conversion.

**Recommendation: reject with #66.** Not a standalone optimization.

## #68 / A01-068 — high-priority devfreq monitor workqueue

Commit: [`89fdc564c08d41a7619918d3ca308de2e5c3b8ed`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/89fdc564c08d41a7619918d3ca308de2e5c3b8ed)

Native create_freezable_workqueue expands to FREEZABLE | UNBOUND | MEM_RECLAIM
plus the legacy marker, max_active 1. The donor explicitly keeps those first
three properties and max_active 1, adds **WQ_HIGHPRI**, and drops __WQ_LEGACY.

This selects a high-priority worker pool, **not a SCHED_FIFO real-time thread**.
It can reduce runnable scheduling delay for monitor jobs under contention, while
also competing more strongly with other work. It does not eliminate delayed-work
polling, deferrable-timer behavior, devfreq mutex waits or sleeping callbacks.
Dropping the legacy marker also removes the exemption from certain reclaim-work
flush-dependency warnings; it is not purely a rename of the old allocator.

**Recommendation: the best bounded candidate in this batch, for testing only.**
No source prerequisites among these ten. Preserve the already corrected memlat
implementation. Before accepting a performance claim, measure active governor
monitoring, latency and power, and exercise memory pressure and suspend/resume.
No measured gain or application approval is implied.

## #69 / A01-069 — purported command-mode prefill optimization

Commit: [`73110ccfa57473253652643ef6bc23b586e538b0`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/73110ccfa57473253652643ef6bc23b586e538b0)

**The submitted mode predicate is reversed in this native tree.** It calls:

```c
sde_encoder_check_curr_mode(encoder, MSM_DISPLAY_CAP_VID_MODE)
```

That helper compares `curr_panel_mode == mode`. It expects a **panel_op_mode**,
not an **msm_display_caps** bit:

```text
MSM_DISPLAY_CAP_VID_MODE = BIT(0) = 1
MSM_DISPLAY_VIDEO_MODE = 0
MSM_DISPLAY_CMD_MODE = 1
```

A host probe using the actual native enums and helper body confirms:

```text
panel_mode=0 donor_is_video=0 correct_is_video=1
panel_mode=1 donor_is_video=1 correct_is_video=0
```

Consequently the donor skips default and rotated-plane prefill calculations on
**video** panels, retaining them on command panels—the opposite of its title.
The miatoll curtana/joyeuse/excalibur/gram overlays include
`cust-atoll-sde-display.dtsi`, which includes the huaxing FT8756 and tianma
NT36675 panels, both explicitly tagged `dsi_video_mode`. This makes the defect
relevant to the actual target DTS, not only hypothetical command-mode hardware;
the running panel still needs device confirmation.

It also skips assignments without explicitly clearing the old/copy-state prefill
value. Native consumers include kickoff parameters, video timing and the RSC
configuration path; `sde_crtc_get_inline_prefill()` gates on rotation mode, not
simply command versus video. Fixing the enum alone is therefore not sufficient
validation for a new command-mode policy or mode-switch lifetime behavior.

**Recommendation: reject the exact patch.** Incorrect display prefill could
cause timing/vote problems; no hardware underflow or corruption is claimed to
have been reproduced. A corrected command-only optimization offers no obvious
saving on the video-panel configurations just identified.

## #70 / A01-070 — schedutil compiler hints implemented as if (0)

Commit: [`1a693d3d593231f6dddde750af48a909ebea8eaf`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/1a693d3d593231f6dddde750af48a909ebea8eaf)

Removes both local RT/DL flag-clearing operations and replaces three maximum-
frequency tests with `if (0)`, retaining their dead bodies. Native local tests
immediately following the mask are already constant-false to an optimizing
compiler; a CPU-state field read in the shared-policy loop is a different case.
Native governor startup initializes that stored field to SCHED_CPUFREQ_RT, so
calling every check a trivially removable local dead branch is inaccurate.

The donor also retains incoming RT/DL bits in stored flags while disabling the
three consumers, rather than expressing a coherent cleaned-up flag policy. No
code-size, runtime or RT/DL latency benefit was demonstrated. Startup, stale CPU
samples and shared-policy behavior need analysis before asserting equivalence.

**Recommendation: skip this low-value form.** If cleanup is wanted later, use a
clear native change with a documented policy and state-lifecycle proof, not dead
`if (0)` bodies presented as performance tuning.

## #71 / A01-071 — misleading SMBB charger optimization

Commit: [`63934468e9b20548b46c4e07f4990403b75257c7`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/63934468e9b20548b46c4e07f4990403b75257c7)

**Recommendation: reject.** `CONFIG_CHARGER_QCOM_SMBB` is disabled here and
`CONFIG_QPNP_SMB5=y`: this is not the active miatoll charger driver.

Even for SMBB hardware, the two added termination-current/pump-delay constants
have no users, so do not tune anything. The watchdog value changes 160 to 80
while the adjacent watchdog-enable setting remains zero: that does not establish
faster negotiation. The software timer was already disabled before this patch.

The functional thermal change unconditionally programs the extended comparator
range and ignores the existing `qcom,jeita-extended-temp-range` choice after
reading it. Overriding device battery-temperature policy is not evidence of
better thermal management or charging efficiency. Do not transplant this into
SMB5 or widen battery safety thresholds based on these comments.

## #72 / A01-072 — managed clock enable for NXP OHCI

Commit: [`c624d9d2c541bb5c6d29c1bc8480b7a7e9ce22c8`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c624d9d2c541bb5c6d29c1bc8480b7a7e9ce22c8)

Upstream maintenance changes manual clock acquisition/enable/unwind into
`devm_clk_get_enabled()`. Native include/linux/clk.h and drivers/clk/clk-devres.c
already declare, implement and export the helper; rejecting it merely because
this is a 4.14 tree would be wrong. Its enabled clock is disabled/unprepared on
managed release, including probe failures and unbind.

**Recommendation: reasonable generic cleanup, but skip for this miatoll
performance selection.** The file supports NXP LPC32xx, guarded by
USB_OHCI_HCD_LPC32XX / ARCH_LPC32XX / USB_ISP1301, not the phone's USB controller.
It is also the textual prerequisite for submitted #73. No NXP target build or
hardware lifecycle validation was performed.

## #73 / A01-073 — release the ISP1301 client reference

Commit: [`3368651e3daf767a2ed4d6cf85ef159b8ff7e334`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3368651e3daf767a2ed4d6cf85ef159b8ff7e334)

Standalone exact application fails because native failure labels/clock unwind
still have the pre-#72 form. **#72 → #73 applies in order** on temporary copies.
The intended DT fix is legitimate: bus_find_device in isp1301_get_client takes a
reference, which needs a corresponding put on later probe failure and unbind.

However, the **native helper's fallback returns the global client pointer
without get_device()**. Donor #73 puts the client unconditionally. The extracted
helper ownership model starts with one driver-owned reference:

```text
dt_after_lookup_and_donor_put_refs=1
fallback_after_lookup_and_donor_put_refs=0
```

Thus DT lookup is balanced but the borrowed fallback loses a reference it did
not acquire. This requires ownership-contract adaptation or a demonstrated
restriction to the ref-taking path—not blind endorsement of the unmodified
backport. The fallback includes the NULL-node case; it is not made safe simply
by enabling OF elsewhere in a kernel. This probe models reference ownership, not
real USB unbind or an observed device crash.

**Recommendation: skip for miatoll.** Valid DT leak-fix intent, but the native
fallback contract needs attention before any wider NXP backport. Like #72, this
is unrelated to phone USB performance and the driver is inactive here.

## Summary and preservation

- **#68 is the only clear performance candidate to shortlist from this batch**,
  subject to workload, power and lifecycle testing; it is not applied.
- **Reject exact #64 and #69**: missed GPU thread unwind and reversed display-mode
  test, respectively. These are not harmless micro-optimizations.
- **Reject #66/#67 together**: incomplete native client migration, plus generic
  width limits and SDHCI format errors. Selected audio coverage does not fix WLAN.
- **Skip #65** under the existing suspend-log policy; **skip #70** as unproven,
  poor-form cleanup; **reject #71** as inactive/misleading thermal-policy tuning.
- **#72/#73 are NXP maintenance, not miatoll USB gains**; #73 additionally needs
  reference-ownership reconciliation with this native helper.

All standalone textual patch checks pass except #73; #66→#67 and #72→#73 pass
as ordered temporary sequences. Applicability is not correctness. Candidate and
prior review-06 source hashes, approved #6/memlat/#36/#41 postimages and the
miatoll defconfig were checked unchanged. No kernel/defconfig edit, activation,
commit, push or CI dispatch. **Next review: #95 / A01-095.**

Latest continuation: [#74–#83](azyr-sm6250-review-08.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.
