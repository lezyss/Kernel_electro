# Azyr sm6250 review 01 — ten submitted commits

Status: **#6 applied locally after user approval; all other items #1–#25 skipped.**
No commit, push or CI dispatch performed for this application.
Scope: the ten links submitted together, in their original order. IDs A01-001
through A01-010 belong to this Azyr review, not the separate Phoenix ledger.
Original recommendations below are retained as review history; the later user
decision in the application section supersedes them.

Source repository: <https://github.com/AzyrRuthless/kernel_xiaomi_sm6250>.
The GitHub commit API was read for every exact SHA, including each changed-file
patch. Recommendations compare those patches against the current Electro
working sources, not merely their subjects or an assumed donor device match.

## Configuration evidence and limits

The shipped 4.14 Kconfig parser was built with host GCC and run against
`arch/arm64/configs/vendor/xiaomi/miatoll_defconfig`, with ARCH=arm64 and an
out-of-tree temporary output directory. This is **configuration resolution
only**, not an AOSP-Clang target build or a device test. Relevant resolved
settings:

```text
CONFIG_PREEMPT=y
CONFIG_LTO=y
CONFIG_THINLTO=y
CONFIG_LTO_CLANG=y
CONFIG_PERF_EVENTS=y
CONFIG_HAVE_HW_BREAKPOINT=y
# CONFIG_PCI is not set
# CONFIG_WQ_POWER_EFFICIENT_DEFAULT is not set
CONFIG_SERIAL_MSM_GENI=y
# CONFIG_SERIAL_MSM_HS is not set
# CONFIG_QPNP_FG_GEN3 is not set
# CONFIG_QPNP_FG_GEN4 is not set
CONFIG_QPNP_QG=y
# CONFIG_QPNP_SMB2 is not set
CONFIG_QPNP_SMB5=y
# CONFIG_SMB138X_CHARGER is not set
```

A bootloader/ROM can supply `workqueue.power_efficient` separately; no live
phone command line was inspected. Configuration evidence is not a measured
power, throughput, audio-latency or scheduling result.

## A01-001 — power-supply power-efficient workqueues

Commit: [`bd0b40fe745ec3b13abebd62ee7de20422db52c2`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/bd0b40fe745ec3b13abebd62ee7de20422db52c2)

**Recommendation: conditional, low priority; do not promise battery savings.**

The actual patch changes 22 delayed-work submissions: five in `battery.c`, ten
in `qpnp-fg-gen3.c`, seven in `smb-lib.c`. It redirects them from the ordinary
system workqueue to `system_power_efficient_wq`; it does not change their delay
values or automatically enable workqueue power-efficient mode.

`drivers/power/supply/qcom/Makefile` builds `battery.o` for the selected SMB5
charger, but SMB5 uses `smb5-lib.o`, not this patch's `smb-lib.o`. GEN3 fuel
gauging is also disabled. Thus only the five shared `battery.c` changes target
objects used by this production configuration. With the power-efficient mode
default off, these workqueues do not gain the intended unbound placement just
from changing the call sites. Separate queue identity/accounting still means
this should not be treated as a literal byte-for-byte behavior no-op.

A selective adaptation could be tested if power-efficient mode is deliberately
used. It needs charging/parallel-charger, USB plug/unplug, thermal/JEITA and
suspend/resume validation; changing safety/control-path work placement is not
free evidence of better battery life. Do not enable the global mode as an
unrequested side effect.

## A01-002 — hardcoded dirty expiry

Commit: [`7a4a1441c0d9d76b7032ca47c0ad7e717a39046a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/7a4a1441c0d9d76b7032ca47c0ad7e717a39046a)

**Recommendation: skip; preserve the working tuning interface.**

In `fs/fs-writeback.c:wb_writeback()`, this replaces the periodic-old-data
cutoff derived from `dirty_expire_interval` with `30 * HZ`. Electro already
initializes `dirty_expire_interval` to 30 seconds in `mm/page-writeback.c`.
There is therefore no new default improvement here. It makes this writeback
cutoff ignore the still-writable `/proc/sys/vm/dirty_expire_centisecs` setting,
which remains exposed by `kernel/sysctl.c`. Prefer a deliberate userspace
setting if a ROM overrides the value; do not silently hardcode the mechanism.
The change does not establish a 30-second upper bound on all dirty-page writeout.

## A01-003 — private NEON intrinsic compatibility header

Commit: [`0f76596195aa186a945ff41d58bf5be12faad68d`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/0f76596195aa186a945ff41d58bf5be12faad68d)

**Recommendation: defer until a real consumer needs it.**

Adds only `arch/arm64/include/asm/neon-intrinsics.h`. The wrapper reconciles
compiler stdint 64-bit integer types with kernel long-long types and avoids
feeding `arm_neon.h` into genksyms. No callers are changed. The header does not
exist in Electro and there are no existing includes of it, so adding it alone
cannot speed anything up or activate NEON/LZ4 acceleration. Existing RAID6
intrinsic code directly includes `arm_neon.h`; this patch does not update it.

If needed for a future intrinsic implementation, validate the actual caller
and flags with pinned AOSP Clang r614150; do not infer present benefit from the
compiler-compatibility description.

## A01-004 — store suspend-inclusive printk timestamps

Commit: [`dd832e421eb94be516e479f56f1915ca0314c5ba`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/dd832e421eb94be516e479f56f1915ca0314c5ba)

**Recommendation: potentially useful diagnostic enhancement, but incomplete here.**

Changes two timestamp-generation sites, `log_store()` and `cont_add()`, from
`local_clock()` to that clock plus `get_total_sleep_time_nsec()`. This can make
messages generated by these paths reflect elapsed suspend time and improve
suspend-log interpretation; it is not an FPS, scheduler or battery optimization.
Explicit caller-supplied timestamps take a separate path and are not converted
by these two substitutions.

Electro has neither a declaration nor implementation of the new helper.
`print_time()` also currently has no sleep-offset adjustment. A correct native
4.14 implementation needs the missing timekeeping foundation, review of
concurrency/NMI-safe access and timestamp consumers, and checks for no double
addition and consistent continuation handling. Merely applying A01-005 is not
that foundation. Preserve existing suspend logging; consider a separately
reviewed implementation only if suspend-inclusive printk time is wanted.

## A01-005 — timekeeping helper declaration

Commit: [`df54275a2c633b559d42b5c3d921aa5ea4d1b976`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/df54275a2c633b559d42b5c3d921aa5ea4d1b976)

**Recommendation: skip this exact patch; it is not the implementation its title suggests.**

Its entire diff adds a `get_total_sleep_time_nsec()` prototype immediately
above an already-existing identical prototype in the donor header. It changes
no timekeeping implementation and no printk code. On the inspected donor
A01-004 tree, the actual helper separately reads `tk_core.timekeeper.offs_boot`
and converts it to nanoseconds; that implementation is not introduced by
A01-005 and is absent from Electro. These two submitted commits therefore do
not form a complete standalone backport.

## A01-006 — inline lock operations under PREEMPT

Commit: [`149e6887d341948cb079ffab98845addd5e50381`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/149e6887d341948cb079ffab98845addd5e50381)

**Recommendation: the best performance experiment in this batch; benchmark first.**

Despite the spin-lock-family subject, the actual diff removes `if !PREEMPT`
from sixteen `ARCH_INLINE_READ_*` and `ARCH_INLINE_WRITE_*` selections. It does
not change `ARCH_INLINE_SPIN_*` selections or lock algorithms. Those conditional
read/write selections still exist in Electro and PREEMPT is enabled, so this
is not already-equivalent code. `kernel/Kconfig.locks` and the lock API headers
consume these selectors; the existing PREEMPT/IRQ bookkeeping must remain.

The donor's claimed 5% procfs/callbench gain is not an Electro measurement.
ThinLTO is enabled here, but that alone does not transfer the result. Validate
with the exact production compiler, compare text size and procfs workloads,
and check lock/preemption correctness and representative device workloads.
More inlining can also hurt instruction-cache behavior. Do not sell this as a
universal 5% performance gain or as permission to remove locking safeguards.

## A01-007 — QCOM lockless PCI configuration accesses

Commit: [`0a45df79d6e9ff8a84d93b6cdb213438709a6cfa`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/0a45df79d6e9ff8a84d93b6cdb213438709a6cfa)

**Recommendation: skip for this production configuration.**

Adds `select PCI_LOCKLESS_CONFIG if PCI && ARCH_QCOM`. PCI resolves to n, so it
has no active effect here. `pci-msm.c` does have its own configuration lock,
but that does not by itself establish correctness for every PCI host/path that
an architecture-wide QCOM selection could affect. Audit actual host controllers
before considering this on a different PCI-enabled target. Do not enable PCI
just to make an otherwise irrelevant optimization applicable.

## A01-008 — remove hardware breakpoint capability

Commit: [`4b6c606e8bcbd8f0073eabe65d788db4ad759b30`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/4b6c606e8bcbd8f0073eabe65d788db4ad759b30)

**Recommendation: skip; avoid a debugging capability regression.**

Deletes ARM64's `select HAVE_HW_BREAKPOINT if PERF_EVENTS`. PERF_EVENTS and
HAVE_HW_BREAKPOINT are both enabled here. It sacrifices the hardware
breakpoint/watchpoint facility and related perf/ptrace debugging support for a
speculative context-switch overhead reduction. This is not a correctness fix
or a free scheduler optimization; it does not mean all ordinary perf counters
would disappear. Preserve the current capability unless an explicit feature
removal and its consequences are approved.

## A01-009 — FIFO priority for legacy UART RX/TX workers

Commit: [`8d77468570828bd9759d69dd60753041d55643df`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/8d77468570828bd9759d69dd60753041d55643df)

**Recommendation: skip for miatoll's selected driver; conditional elsewhere.**

Sets the legacy `msm_serial_hs.c` RX/TX threads to SCHED_FIFO priority 1. This
can be a sensible latency experiment on devices actually using those workers,
but SERIAL_MSM_HS is disabled and SERIAL_MSM_GENI is enabled here. The patch
cannot improve this configuration's active GENI serial path.

It applies to the driver's ports rather than explicitly identifying only a
Bluetooth port, and ignores scheduling-policy return values. If adapted for
an appropriate target, also review initialization/error handling (the current
TX creation path incorrectly tests `rx->task`), RT behavior under load, and
actual audio/transfer measurements. Do not blindly move unrelated shared
workers to RT policy.

## A01-010 — FIFO policy for the legacy TTY worker

Commit: [`a95a7caa745bda93419cf84801ce51a465cad0e2`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/a95a7caa745bda93419cf84801ce51a465cad0e2)

**Recommendation: skip as submitted; inactive driver and missing prerequisite.**

Adds `tty_port_set_policy(..., SCHED_FIFO, 1)` to the same disabled legacy
serial driver. Electro has no declaration or implementation of that helper.
Its `tty_bufhead` contains a `struct work_struct`, and `tty_buffer.c` queues
flip work on `system_unbound_wq`, rather than exposing the per-port thread
policy API assumed by this patch. Enabling this driver after importing only
this patch would leave an unavailable helper, not a working Bluetooth fix.
A proper dedicated-worker/API foundation is a separate change; changing shared
workqueue worker policy is not an acceptable shortcut. Neither serial patch
should be transplanted onto GENI merely because both drivers serve UARTs.

## Summary

- Best optional performance candidate: **A01-006**, pending measured validation.
- Potential diagnostic enhancement: **A01-004**, only with a separately reviewed
  complete native timekeeping foundation; A01-005 alone cannot supply it.
- Conditional future work: A01-001 power-work placement, A01-003 NEON wrapper
  with a real caller, A01-009 on a different target using the legacy driver.
- No blanket cherry-pick recommendation. Preserve dirty-expiry configurability,
  hardware-breakpoint capability, inactive-driver defaults and existing logging.
- The original review did not itself approve application; see the later user
  decision below. A push or CI run is not authorized by that decision.

## Continued numbering

[Items #11–#25](azyr-sm6250-review-02.md) continue this Azyr series as
A01-011 through A01-025. No earlier IDs are reassigned. Continuations: [#26–#33](azyr-sm6250-review-03.md) and
[#34–#43](azyr-sm6250-review-04.md). Latest continuation: [#44–#53](azyr-sm6250-review-05.md).
Latest continuation: [#54–#63](azyr-sm6250-review-06.md).
Next unused number: #95 / A01-095.

## User decision and application — A01-006 only

The user explicitly requested: **“Apply #6, skip other.”** This applies to the
reviewed #1–#25: A01-006 is selected; #1–#5 and #7–#25 are skipped, including
previously optional timestamp and power-workqueue ideas. At that decision the
next number was #26, now covered by [review 03](azyr-sm6250-review-03.md).

Applied the exact donor transformation from
`149e6887d341948cb079ffab98845addd5e50381`: remove `if !PREEMPT` from precisely
sixteen `ARCH_INLINE_READ_*` / `ARCH_INLINE_WRITE_*` selections in
`arch/arm64/Kconfig`. No spinlock selectors, lock implementations, scheduler
policy, defconfig settings, Boeffla code, timestamps or wakeup handling changed.

Configuration-only before/after checks using the real shipped Kconfig parser:

- Production PREEMPT=y: exactly sixteen architecture selectors and their
  sixteen effective INLINE options change n to y; no other resolved settings
  change. PREEMPT and SUSFS priority UID filtering remain enabled.
- PREEMPT_NONE: resolved configurations are identical before/after; those
  selectors/options were already enabled.
- SUSFS host models and thirty provenance tamper controls plus the accidental
  priority-disablement control pass; KSU and NoMount source/config checks pass.
- Host GCC built only the configuration parser and host models. There is **no
  new pinned-AOSP-Clang target build, text-size comparison, device boot, lock
  stress or benchmark result**. The donor's 5% claim remains unverified.

The inline options also suppress matching out-of-line `_raw_read_*` /
`_raw_write_*` implementations/exports in `kernel/locking/spinlock.c`. Build
in-tree modules with the new kernel; check any installed prebuilt vendor
modules for symbol compatibility before claiming a safe device deployment.
No export shim or other unapproved ABI change was added.

Configuration/source hashes and the exact 32-setting change set are recorded
in [the local application receipt](azyr-sm6250-006-validation.json). That receipt
is configuration evidence, not production-build or device-performance proof.
The change remains local: **no commit, push or CI dispatch**.

Latest continuation: [#64–#73](azyr-sm6250-review-07.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#74–#83](azyr-sm6250-review-08.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.
