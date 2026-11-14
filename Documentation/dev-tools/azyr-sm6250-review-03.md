# Azyr sm6250 review 03 — continued items #26–#33

Status: **exact donor patches #26–#33 not applied**. After the initial review,
the user approved a **corrected native adaptation of #27–#30**, now applied
locally with bounded validation below. No new commit, push or CI dispatch.
This follows [#1–#10](azyr-sm6250-review-01.md) and
[#11–#25](azyr-sm6250-review-02.md), preserving the same numbering series:
**A01-026 through A01-033**. Continuation [#34–#43](azyr-sm6250-review-04.md) is recorded;
the next unassigned number is **#95 / A01-095**; [#54–#63 are recorded here](azyr-sm6250-review-06.md).
The earlier user decision remains #6 applied locally and the other #1–#25
skipped. The later memlat authorization does not approve the other items.

Source repository: <https://github.com/AzyrRuthless/kernel_xiaomi_sm6250>.
Every exact commit and every changed-file patch was inspected through the
GitHub API and compared with current working sources, not only donor subjects.

## Configuration and source evidence

The shipped Kconfig parser was built with host GCC and used to resolve the
miatoll defconfig in an external temporary directory. This is configuration
resolution only, **not an AOSP-Clang target build or device execution**.
Relevant results:

```text
CONFIG_PREEMPT=y
CONFIG_NR_CPUS=8
CONFIG_DEFAULT_CFQ=y
CONFIG_DEFAULT_IOSCHED="cfq"
# CONFIG_MQ_IOSCHED_DEADLINE is not set
CONFIG_QCOM_SCM=y
# CONFIG_ARM64_LSE_ATOMICS is not set
CONFIG_ARM_MEMLAT_MON=y
CONFIG_DEVFREQ_GOV_MEMLAT=y
# CONFIG_KSM is not set
CONFIG_CGROUP_SCHED=y
# CONFIG_FAIR_GROUP_SCHED is not set
```

The #6 Kconfig postimage still matches its recorded application receipt. No
source/configuration change from this batch was made during that initial review.
The subsequent approved native memlat adaptation is recorded below. A hypothetical
FAIR_GROUP_SCHED=y profile was resolved in cache only: the sole resolved
setting change was FAIR_GROUP_SCHED n to y; the source defconfig remains n.

## #26 / A01-026 — mq-deadline defaults

Commit: [`54a3a51323b8f585b0edae6a30360d1e37b467f2`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/54a3a51323b8f585b0edae6a30360d1e37b467f2)

Changes write expiry from 5 seconds to 1, writes_starved from 2 to 1 and front
merges from enabled to disabled in `block/mq-deadline.c`.

**Recommendation: skip for the current build; tuning only elsewhere.**
The mq-deadline scheduler is disabled and the default is CFQ, so these defaults
would not improve this production configuration. On a system using mq-deadline,
prioritizing writes sooner and changing merge behavior trades read latency,
write service and batching/throughput rather than guaranteeing responsiveness.
The corresponding tunables already exist for controlled runtime comparisons.
Do not enable/switch schedulers merely to make this inactive patch applicable.

## #27 / A01-027 — global SCM counter / memlat guard

Commit: [`d73dae72f581c0b3fd6c4966773bbe14c6a4be74`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d73dae72f581c0b3fd6c4966773bbe14c6a4be74)

Adds a global SCM-call counter and `under_scm_call()`. The goal of avoiding
IPIs to a CPU occupied by a long secure-monitor call is plausible and memlat
is enabled here. However, **the actual memlat hunk guards delete_events(),
not read_event() or get_cnt()**. Regular sampling still calls
`perf_event_read_value()` unchanged.

**Recommendation: do not apply this exact patch.** Returning early from
`delete_events()` skips counter release and pointer/reset cleanup. In the
current stop/start lifecycle that can leave live perf events and allow later
creation to overwrite their pointers; it is not a safe cleanup/latency fix.
The patch also places atomic operations alongside fixed-register SMC inline
assembly, which #28 subsequently repairs. Its non-SCM header fallback is an
extern function definition rather than a normal static-inline stub.
A corrected design needs explicit event lifetime rules, not silent teardown
skips. Commit-message claims about returning zero on reads are not what this
diff implements.

## #28 / A01-028 — separate accounting from SMC register assembly

Commit: [`12798fd3c654f0584f54afadb027f96a07461555`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/12798fd3c654f0584f54afadb027f96a07461555)

Moves SCM counter increments/decrements into outer wrapper functions, away
from local fixed x0/x1 (or w/r register) variables used by the raw SMC assembly.
The message identifies register clobbering with GCC/LSE atomic implementations.

**Recommendation: a sensible dependent correction, not a standalone fix for
Electro.** Current SCM code has no new call counter, and production uses pinned
AOSP Clang with LSE atomics disabled in this resolved config. This corrects a
hazard introduced by the proposed accounting layer; do not import #27 just to
need #28. Preserve the assembly/accounting separation if a corrected memlat/SCM
series is later approved, including compiler/inlining/disassembly validation.

## #29 / A01-029 — parallel asynchronous memlat reads

Commit: [`143f07a8f3e77aae7dcb48979d424cd1e17b2c4a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/143f07a8f3e77aae7dcb48979d424cd1e17b2c4a)

Replaces per-event synchronous remote reads with one asynchronous IPI per CPU,
local/any-CPU reads and a sleeping waiter. It changes SCM tracking from a global
counter to per-CPU counters. The direction is relevant to an enabled memlat
monitor and may reduce serialized IPI/preemption-off overhead.

**Recommendation: potentially useful redesign, but defer; not cherry-pick-ready.**
Specific compatibility and correctness work is required:

- It calls `generic_exec_single()` directly. In Electro that function is
  **static/private to kernel/smp.c**, with no public header declaration. The
  public `smp_call_function_single_async()` interface exists; adapting to it
  requires preserving CSD ownership/completion rules, not simply exporting a
  private core helper.
- Its initial `perf_event_read_local()` call has two arguments, whereas the
  current API takes four. #30 addresses this one incompatibility, not the rest.
- The series retains the early-return teardown behavior from #27.
- Per-CPU SCM wrappers sample raw_smp_processor_id() without pinning the task
  in those wrappers. The ordinary SCM path is explicitly preemptible and takes
  mutexes, so migration/accounting needs an audit before relying on that CPU
  marker. The SCM-check-versus-call race also remains a heuristic limitation.
- Stack-backed IPI data/CSD lifetimes, count publication, failed/skipped IPIs,
  waiter ordering, CPU hotplug, perf-event teardown and zero/stale-sample
  governor behavior need validation. The single-word/atomic CPU-mask design
  also has CPU-count assumptions; this target has eight CPUs, not arbitrary
  large masks.

No device jitter or power benefit is measured by inspecting this patch. Treat
#27–#30 as a separately engineered native series if pursued, not four isolated
performance toggles. Preserve existing devfreq/BW locking and do not hide
lifetime errors with teardown skips.

## #30 / A01-030 — perf_event_read_local signature correction

Commit: [`d7fda10ad1dbb38279b6d24fdd9fbf40fca53b73`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d7fda10ad1dbb38279b6d24fdd9fbf40fca53b73)

Adds the NULL enabled/running output arguments to the local perf read introduced
by #29. Both the declaration and implementation in Electro use four arguments
and permit these optional outputs to be NULL.

**Recommendation: correct and necessary if adapting #29, but not independently
needed.** The current memlat driver still uses perf_event_read_value(), so
there is no existing two-argument call here to repair. This one-line fix does
not make the asynchronous series or its lifecycle safe by itself.

## #31 / A01-031 — allegedly faster integer square root

Commit: [`04240ea8f10d8dbaba88f042c493b24e910cf8ab`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/04240ea8f10d8dbaba88f042c493b24e910cf8ab)

**Recommendation: reject as submitted — wrong results in the upper input range.**
The donor initializes place to `1UL << (BITS_PER_LONG - 2)` but then
unconditionally shifts it right by two before its first comparison. That
skips the top required power-of-four digit for large unsigned-long inputs.
The existing implementation starts at the correct digit using __fls().

The exact patch was applied only to an external temporary copy. Both extracted
functions were compiled on a 64-bit host with GCC `-std=gnu89 -O2` and compared
with Python math.isqrt() over **200,236 distinct inputs**, including a dense
small range, power-of-two boundaries and deterministic random 64-bit values:

- Current implementation: **0 mismatches**.
- Donor implementation: **74,839 mismatches**.
- Input `4611686018427387904` (2^62): expected/current **2147483648**;
  donor **2147483647**.
- Input `18446744073709551615` (ULONG_MAX on LP64): expected/current
  **4294967295**; donor **2147483647**.

See [the bounded host-validation receipt](azyr-sm6250-031-validation.json).
This is a correctness comparison, not an AArch64 execution/performance result.
The donor's repeated single-input timing does not validate the full API range
or establish a generally transferable 3x gain; inline/constant-input effects
would also need controlling in any benchmark. Do not replace correct common
kernel math with this version.

## #32 / A01-032 — KSM scan defaults

Commit: [`d8a31f03daa20dd5e0419aafc500c86be6213b7d`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d8a31f03daa20dd5e0419aafc500c86be6213b7d)

Changes pages_to_scan from 100 to 250 and the sleep interval from 20 ms to
1500 ms. It does not change the deduplication algorithm or activate KSM.

**Recommendation: skip here.** KSM resolves to disabled, so the selected build
gets no benefit. If KSM is deliberately enabled and running elsewhere, this
reduces nominal scan rate from about 5000 to 167 pages/second (ignoring actual
scan cost), trading less scanning CPU time for much slower merging. Reduced
CPU work is not proof of net battery improvement when RAM pressure also changes.
Both settings are tunable; preserve the existing dedup/default policy rather
than adding arbitrary power claims or enabling KSM as a prerequisite.

## #33 / A01-033 — enable fair CPU cgroup scheduling

Commit: [`f342693bc620cc1f914e0c5510c5fdb9be35fc5c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f342693bc620cc1f914e0c5510c5fdb9be35fc5c)

Despite the devfreq subject, this only flips CONFIG_FAIR_GROUP_SCHED from n to
y in the miatoll defconfig. It enables hierarchical fair CPU scheduling for
task groups; it does not directly change a devfreq governor.

**Recommendation: defer/skip as a generic optimization.** This changes how CPU
shares and Android's CPU cgroup hierarchy influence scheduling. It may be
useful for a specific ROM policy but needs checking against its task placement,
CPU shares and the current PELT/CASS/BORE behavior under contention. Do not assume
it improves foreground latency or power. The hypothetical Kconfig check changed
only this setting and was kept outside the source tree; it is not a runtime
policy/performance test. Existing CPU cgroup features remain untouched.

## Summary

No straightforward drop-in recommendation from this batch:

- #26 and #32 tune features disabled in this production configuration.
- #27 is not the sampling guard described in its message and skips cleanup.
- #28 and #30 are useful dependent corrections only if the new series is adopted.
- #29 has a plausible performance goal but needs a corrected native design and
  substantial compile/lifetime/hotplug/SCM validation before approval.
- #31 is demonstrably incorrect and should not be applied as-is.
- #33 is a deliberate CPU scheduling-policy change, not a devfreq bug fix.

Those were the original exact-donor assessments; they remain valid. The later
user-approved corrected memlat application below does not cherry-pick the donor
patches or activate other options. The previously applied #6 is preserved.
**Next review number: #95; see [review 09](azyr-sm6250-review-09.md).**


## Subsequent approval — corrected native memlat application (#27–#30 ideas)

User decision: “Corrected memlat good to have? if so fix it and apply”.
Applied locally to `drivers/devfreq/arm-memlat-mon.c`,
`drivers/soc/qcom/scm.c` and `include/soc/qcom/scm.h` only. No scheduler,
governor threshold, defconfig or perf/SMP core change was made by this task.

The direction is relevant because the shipped monitor is configured built in:
one asynchronous request per monitored online CPU reads all configured PMU
counters on that CPU, instead of issuing repeated synchronous cross-CPU reads.
This is an expected reduction in repeated IPI/wait overhead, **not a measured
latency, throughput or battery improvement**.

Correctness differences from the supplied series:

- Uses existing `smp_call_function_single_async()` and the native four-argument
  `perf_event_read_local()`. No private `generic_exec_single` exposure/export.
- Heap-owned per-CPU CSD/completion objects; start/sample/stop serialize under a
  monitor mutex. CPU-hotplug read protection covers dispatch and every accepted
  callback's mandatory completion wait. No timeout abandons event ownership.
- Avoids dispatch to observed idle/isolated CPUs, preserving the native no-wakeup
  intent. Idle votes clear while the baseline/time are retained; isolated/offline
  CPUs reset their epoch. This snapshot check is not a CPU-state race guarantee.
- Reads publish only complete successful snapshots. Failed reads/dispatch or SCM
  skips preserve both previous data and its baseline/timestamp. Offline CPUs
  clear votes and reset their epoch; first valid reads establish a baseline.
- All partially created events unwind on startup failure; teardown never skips
  because SCM is busy. Sparse CPU ids map to correctly sized CPU-indexed storage
  and compact governor stats. Zero cycles and large-u64 stall arithmetic handled.
- Conservative **global ARMv8** SCM accounting in ordinary C wrappers around
  noinline raw workers. All three original assembly-worker bodies are unchanged;
  seven legacy worker functions are unchanged. No preemption disable/task pinning
  across secure calls, and no counter bookkeeping inside fixed-register workers.
  Legacy/direct firmware calls are not tracked. A secure call can start after
  the hint check, so this is **not race elimination or a worst-case latency bound**.

Validation performed:

- Exact source patch/inverse replay and three-source pre/post SHA256 checks.
- Extracted actual driver/SCM-wrapper C models under pinned AOSP Clang + UBSan:
  deferred/reverse and early completions, sparse masks across 32/64-bit boundaries,
  failures/skips, offline epochs, cleanup/unwind, nested accounting and forwarding.
  20,484 exact stall-percent arithmetic comparisons; seven compiled semantic
  mutants rejected by assertions. These mocks are sequential, not real SMP.
- **Real miatoll ARM64 Kbuild objects** for both changed `.c` files with exact
  AOSP r614150 / commit `3b86e40facfff1eab4065614255d573293c10373` (Clang 23.0.1).
  ThinLTO retained; only output-config Polly disabled, as in the production CI
  script. A relocatable LTO link generated native AArch64 ELF objects, exercising
  inline assembly code generation; both ARM64 raw workers contain SMCs and no
  intervening C calls. No complete kernel image/modules link was performed.
- Actual ARM64 compilation of the SCM-disabled header branch produces a constant
  false result and no SCM-symbol dependency. This is not a full disabled profile.
- SUSFS full-profile source/config/host checks, priority-filter activation negative,
  all 30 provenance negatives, KSU update/helper negatives and NoMount host checks
  PASS. #6's ARM64 Kconfig postimage still matches its earlier receipt.

**Remaining limits:** no ARM32 target build, module-link proof, device boot,
CPU-hotplug/suspend/perf/SMC stress or performance/power measurements. The shipped
built-in miatoll path is the target: `perf_event_read_local` is not exported here
(the existing governor registration helpers are also unexported), so do not
select a module build without separate integration. Repeated skips can retain
stale governor votes; global SCM gating can conservatively skip unaffected CPUs.
Accepted callbacks always drain and can still be delayed in the SCM-start race.
No complete safety or improvement claim is made from object compilation/mocks.

Evidence: [patch](azyr-sm6250-memlat-native.diff),
[receipt](azyr-sm6250-memlat-native-validation.json),
[validation transcript](azyr-sm6250-memlat-native-validation.txt), and
`tools/testing/selftests/memlat/{README,model.c,test_memlat.py}`.
No new commit, push or CI dispatch. Other #26–#33 decisions remain unchanged.

Latest continuation: [#64–#73](azyr-sm6250-review-07.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#74–#83](azyr-sm6250-review-08.md). Next unused number: **#95 / A01-095**.

Latest continuation: [#84–#94](azyr-sm6250-review-09.md). Next unused number: **#95 / A01-095**.

Final submitted batch [review10, #95–#109](azyr-sm6250-review-10.md) is complete.
Next unassigned: **#110 / A01-110**. Historical recommendations are not approvals.
