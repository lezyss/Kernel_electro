# Approved Azyr selection — thirteen items

User authorization: apply **#46 #47 #48 #52 #56 #57 #58 #78 #79 #92 #93 #94 #98**
and push to the existing `arena/e63a046d-kernel-electro` branch. This authorizes
corrected native #46/#92 as explained immediately before the request. No CI
requested or dispatched. GPU idle-timer item #110 is not selected.

## Scope applied

| Stable item | Change |
|---|---|
| A01-046 | Newly-idle balancing exits if runnable tasks or queued wakeups exist. Corrected native code uses READ_ONCE(nr_running) and existing llist_empty(wake_list), without donor's undefined SCHED_FEAT_TTWU_QUEUE preprocessor guard. SMP path only; TTWU_QUEUE default unchanged. |
| A01-047 | Mark the small schedutil policy-free helper inline; no steady-state benefit promised. |
| A01-048 | Replace iterative high-word normalization in __calc_delta with fls, retaining inverse-weight arithmetic and explicit bitops include. |
| A01-052 | Pass false to suspend clock debug printer, avoiding parent traversal under the cluster lock. Debugfs remains disabled; existing selected profile has the empty stub. |
| A01-056/057 | Apply in order; final verity queue is CPU_INTENSIVE|MEM_RECLAIM|HIGHPRI, bound, max_active0. Replace donor's inapplicable tasklet comment with an accurate policy comment and wrap the call. No tasklet feature added. |
| A01-058 | Remove GPU IRQ-only AO counter debug reads and their unused wrapper/prototype; retain lower-level counter users, fence polling, fault handling and recovery. |
| A01-078 | Balance topology cpufreq policy get/put references on every successful iteration path. |
| A01-079 | Remove successful IOMMU group-add informational print; preserve trace/error handling. |
| A01-092 | Move shared request timestamp setters and CFQ stats to monotonic ktime_get_ns. Correct the remaining BFQ completion reader to use that same clock and ordinary comparisons. Add explicit ktime header; do not convert unrelated BFQ internal timestamps or enable BFQ. |
| A01-093 | Document intended CFQ switch fallthrough; comment only. |
| A01-094 | Clear CFQ async priority/idle pointers after dropping references; preserve statistics transfer. |
| A01-098 | Add structured PM/GIC wake IRQ logging. Remove GIC's early console-debug gate but retain conditional console printing and existing suspend logs. |

No defconfig, timeout, thermal, BORE, CASS, TTWU_QUEUE, I/O scheduler or GPU-idle
policy activation/change is part of this selection. Exact donor SHAs/patches and
pre/postimage hashes are in [the receipt](azyr-sm6250-selected-validation.json).
The [scoped patch](azyr-sm6250-selected.diff) captures only these15 source files,
including the BFQ correction, not unrelated approved local work.

## Checks performed

- Re-fetched13 exact donor commits and checked/replayed their patches in order.
  Applied the specified native corrections, with no unrelated cherry-picks.
- New [extracted-function tests](../../tools/testing/selftests/azyr_selected/README.md):
  36 balancing,240,000 delta/inverse equivalence,450 topology refcount,
  18 CFQ occupancy,36 shared-clock and2 GIC logging cases. All pass GCC O2/UBSan;
  seven compiled semantic mutants fail as required. Also structural checks for
  inline/suspend flag/verity queue/debug removal/logging additions.
- Existing scheduler correctness matrix passes all six configurations, including
  capacity/queue/idle cases and ten negative controls.
- Existing suspend validation passes320 cases and two negative controls.
- Corrected memlat regression passes20,484 arithmetic cases, extracted lifecycle
  tests and seven negative controls. Approved cpufreq/IPA passes180 transition
  cases and three negative controls, retaining integer-only10–12ms IPA wait.
- KernelSU104-file provenance/wiring, NoMount integrity and UBSan host tests,
  SUSFS integrity and UBSan host tests pass. For the SUSFS GCC harness only,
  `-Wno-address` is required for an existing always-true local inode-address
  warning; initial strict-warning attempt failed compilation, not a runtime
  regression. No production source was changed for that harness warning.
- Resolve shipped miatoll config in external O= with ARCH=arm64 HOSTCC=gcc CC=gcc;
  this invokes host Kconfig tools and is not production GCC compilation. Source
  defconfig and approved #6/memlat/#36/#41 postimages remain unchanged.
- Publication baseline is the already-published branch tip7103f1eb0. All15 source
  preimages equal its blobs. This preserves the earlier20 remote commits and
  permits a normal fast-forward push without force or republishing unrelated
  local changes. Branch/index metadata was advanced to that existing tip without
  writing worktree files. The previous index was empty of staged changes.

The test runner and receipt make evidence durable. They are not performance
measurements, proof for arbitrary invalid scheduler weights, full kernel API/
concurrency testing, a target build or hardware execution.

## Publication boundaries and remaining validation

Only the15 selected source files, this application record/receipt/scoped patch,
and its two selftest files are committed. Existing local approved #6, corrected
memlat and #36/#41 remain intact but are not silently included in this publication.
Historical review documents remain local review history; the new receipt retains
standalone provenance for this selection. No other shortlisted/review-only item
becomes approved by this change.

No production AOSP r614150 ARM64 object/image build, phone boot, verity device
reads/error injection/reclaim test, GPU IRQ/fence/reset stress, cpufreq policy
teardown, suspend/resume or battery/frame-latency measurement was performed.
Host compiler/Kconfig success must not be represented as such. CI remains manual
and was not dispatched. In particular #56/#57 need runtime verified-device
activation and contention/reclaim validation before claiming a benefit; #58
reduces diagnostics, #98 adds diagnostic work, and none has a measured power gain.

Suggested phone follow-up with a recoverable known-good image: boot/root/storage
smoke, verified reads under CPU/memory contention, repeated display/GPU activity
and suspend/resume, checking faults and wakeup reasons. Keep GPU idle_timer
experiments separate and temporary, as previously discussed.
