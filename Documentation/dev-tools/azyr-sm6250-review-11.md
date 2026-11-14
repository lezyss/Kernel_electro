# Azyr sm6250 additional review — #110 / A01-110

**Review only. Nothing applied, committed, pushed or sent to CI.**
Continues [review10, #95–#109](azyr-sm6250-review-10.md). The original commit is
provenance for this same item, not a second numbered candidate. Next unassigned:
**#111 / A01-111**. Previously discussed shortlist remains unapplied; asking
whether it is a good choice was not application authorization.

## Sources and exact difference

Submitted: [c3ff9a15471ccb3f7f00d02666c61d459d3eb778](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c3ff9a15471ccb3f7f00d02666c61d459d3eb778),
“drivers: gpu: Prevent userspace from changing GPU idle timeout”.

Original: [5f8e1090b979fe2ec476743dbea78124fc617f94](https://github.com/kerneltoast/android_kernel_google_floral/commit/5f8e1090b979fe2ec476743dbea78124fc617f94),
“arm64: dts: sm8150: Force GPU idle timeout to 58 ms”.

Read both exact GitHub commit API responses and all three changed-file patches;
verified addition/deletion counts and tested standalone application on temporary
native copies. Both patch checks pass. The common kgsl_pwrctrl.c change is the
same: insert `return count;` immediately after declarations in __timer_store.
Original additionally changes SM8150 GPU DT idle timeout80→58ms; Azyr omits that
DT change. Therefore the Azyr patch does not reproduce the original timing policy.
The [receipt](azyr-sm6250-review-11-validation.json) retains full patches/hashes,
configuration, source hashes, host fixtures/results and preservation checks.

## What it actually does

Native idle_timer is a0644 sysfs attribute: show reads interval_timeout;
store parses a u32, checks its range, takes device mutex and updates
interval_timeout using msecs_to_jiffies. Only idle_timer calls __timer_store here.
The inserted return bypasses device validation, input parsing, range checks,
locking and the update. The attribute still advertises writable permissions and
returns success for valid and invalid strings alike. Readback shows the unchanged
value. It is a silent accepted-but-ignored write policy, not explicit read-only
sysfs, input validation or a new timeout value.

This can prevent a HAL/performance service from lengthening the timeout, but
also prevents legitimate shortening, tuning, device-specific policies and root
experiments. Permission to reach the store remains subject to normal sysfs/
SELinux policy; “userspace” does not imply any unprivileged app can write it.
No live ROM writer or harmful override has been observed in this review.

## Native miatoll timing is not the original SM8150 timing

- atoll.dtsi includes sdmmagpie-gpu.dtsi, whose GPU idle-timeout is64ms.
  The inspected Atoll/miatoll sources have no overriding idle-timeout property.
  adreno.c reads this property and falls back to64ms if absent.
- Resolved miatoll config: QCOM_KGSL=y, DRM_MSM=y, HZ=100. Resolution used shipped
  Kconfig parser, external O= and ARCH=arm64 HOSTCC=gcc CC=gcc; not a target build.
- GPU timer stores jiffies. At100Hz,64ms requests7ticks (nominal70ms);58ms requests
  6ticks (nominal60ms). Azyr locks the native DT-derived value, not58ms. The
  original's sm8150-gpu.dtsi edit does not change the Atoll GPU property.
- Native SDE display macro IDLE_POWERCOLLAPSE_DURATION=(66-16/2) equals58ms, so
  the original rationale is not wholly irrelevant. However, SDE LP2 uses a1ms
  short timeout, autorefresh can suppress delayed-off scheduling, and pending
  frames/activity affect the path. GPU idle and display resource-control work
  have independent triggers; equal requested durations do not synchronize them.

These are source/config values and nominal conversions, not extracted running
DTB values, measured firing times or evidence that GPU stays powered after every
display idle transition. Neither commit disables thermal control or forces
collapse while commands remain busy; existing state/idle checks still matter.

## Bounded actual-function check

Compiled actual native/donor __timer_store bodies with GCC O2/UBSan and mocked
device lookup, parser, mutex and small-value100Hz conversion. Initial timeout
7ticks (64ms DT request). Twelve cases: six inputs/conditions per implementation.

| Case | Native | Donor |
|---|---|---|
| Write58 | success,6ticks | success,unchanged7ticks |
| Write200 | success,20ticks | success,unchanged7ticks |
| Write0 | success,0ticks | success,unchanged7ticks |
| Invalid text | -EINVAL | success,unchanged7ticks |
| u32 overflow | -ERANGE | success,unchanged7ticks |
| Device lookup NULL | return0 | return byte count |

All donor cases bypass parsing and mutex acquisition. These mocks demonstrate
control flow, not every kernel parser edge, concurrency, GPU/display power or
ROM behavior. Both source patches apply cleanly; applicability is not approval.

## Recommendation

**Skip this exact silent-no-op patch for default integration.** It is a policy
lockdown, not a general GPU performance fix, and its power benefit depends on an
unverified userspace override. It does not deserve the same confidence as #78's
reference-accounting fix or #48's bounded arithmetic-equivalence candidate.

If idle policy is a real problem, first inspect running idle_timer after boot,
screen transitions and performance-mode changes, identify its writer, and test
candidate durations using the existing interface. Compare frame pacing,
resume/first-frame latency, collapse/wakeup activity, sustained load and power.
Shorter timeouts may reduce idle residency costs but increase power-transition
churn and wake latency; no benefit is guaranteed. Separate timing selection from
whether to restrict userspace control.

If a fixed policy is later explicitly wanted, an honestly read-only attribute or
an explicit rejected-write policy is clearer than silently claiming success,
but either is an ABI/policy change requiring ROM compatibility review. Do not
change DT, permissions, timeout defaults or the display timer now. No dependency
on shortlisted #58 (GPU IRQ debug reads), and no automatic addition to shortlist.

Candidate/inspected sources, previous review10 sources and approved #6/memlat/
#36/#41 are unchanged. No production AOSP ARM64 build, phone test, measured
battery/performance result, kernel edit, commit, push or CI dispatch.
**Next: #111 / A01-111.**
