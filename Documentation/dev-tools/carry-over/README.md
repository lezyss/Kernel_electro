# Reviewed carry-over on the repaired `16` foundation

**All actionable groups in the reviewed inventory are integrated, with bounded
validation. BBRplus is excluded. This is not a flash-qualified release.**

| Current accounting | References |
|---|---:|
| Applied / corrected-native coverage with bounded validation | **140** |
| Already-native `__SK_PASS`; supplied upstream reference metadata unresolved | **1 (E143)** |
| Historical LZ4 1.11.0 superseded by official repaired **1.11.1** | **1 (E115)** |
| **BBRplus excluded**, not built or selectable | **1 (E118)** |
| Pending source integration in this inventory | **0** |
| Total accounted for | **143** |

These are reference coverages, **not 140 literal donor cherry-picks**. The
selective BPF reference is not a claim of the complete donor or Linux 5.15 ABI.
[progress.json](progress.json) retains every original ID/hash and explains E138
and E143. The supplied E143 upstream SHA still has unresolved historical metadata;
its native enum and consumers are retained, not duplicated or fabricated.

All work stays on `arena/e63a046d-kernel-electro`. **No commit, push, PR or GitHub
Actions dispatch was made for this reconciliation. No complete image/module
link, phone boot, vendor-module ABI test or performance test was performed.**
Standing SM8150/Phoenix replay exclusions and skipped proposals remain excluded.
The original `base-sync-16` audit and foundation-repair receipts are unchanged;
the new ordered source receipts describe the authorized overlays instead.

## Batch 03 — E028–E114, E116–E117

[Applied delta](batch-03/applied.diff) · [source receipt](batch-03/source.json)

| Groups | Integrated result |
|---|---|
| E028–E034 | Corrected BORE 5.1 with bounded inheritance/cache traversal, idle-policy/PELT handling and Cambyses block rotation, scan budgets, 5 ms guard and migration safeguards; CASS and native wakeup fixes retained |
| E035–E064 | Corrected MGLRU with shadow/swap handling, safe cleanup bounds, native page-table walkers, memcg migration/lifecycle and DEBUG_FS guards; configured for boot enable, full history off |
| E065–E070 | Guarded readpage/readahead, paired cold-swap PSI accounting, vmstat hints, compaction retry escalation plus **native trace feedback**, and complete zero-seek shrinker handling |
| E071–E086 | Corrected vmalloc 1–16: augmented free areas, alignment/GFP/preload/error paths, busy/free locks, lazy TLB quarantine and both iterator unlocks; no #17 |
| E087–E099 | Native procfs formatter/plumbing cleanup, width/hex printing, common map/smaps handlers, corrected PSS/rollup and post-lock map_files formatting |
| E100–E104 | Corrected F2FS compression/GC/atomic-ioctl fixes, epoll temporary reference and writeback freeing/list-order handling |
| E105–E114 | Size-aware F2FS sysfs and corrected A → B1 → B2 IPU/GC/checkpoint integration; GC/checkpoint merging remain **opt-in/default off** |
| E116–E117 | zram flag packing/bounds and architecture-sized xxhash helper |

The scoped merge uses the earlier corrected aggregate `047b7fce7`, not a wholesale
old-tree restore. Newer native clone3/signal code is retained, with only required
scheduler/MGLRU hooks added. HMM/migrate walker initialization closes the MGLRU
dependency set. The updated base's watermark scale stays **20**, not the unrelated
old value 35. The native late writeback wakeup is retained with one unlock/trace
path; freeing checks precede list movement. Corrected historical Cambyses and
F2FS patches are preserved beneath `batch-03/historical/`.

## Batch 04 — E119–E142; E143 native reconciliation

[Applied delta](batch-04/applied.diff) · [source receipt](batch-04/source.json)

* **BBRv3 + TCP/fq EDT:** Google loss-based BBR3 adaptation, wrap-safe samples,
  per-skb packet/byte tagging, loss/TLP/split/merge accounting and native monotonic
  EDT. Miatoll selects **bbr3/fq**; native BBR/CUBIC and fq_codel remain available,
  generic fallback stays CUBIC, and TCP buffer caps are unchanged. No BBRplus
  code, Kconfig choice or default is imported. BBR3 uses 144 bytes of private
  storage when built; the no-BBR3 fallback remains the native **88 bytes**.
  Remove the stale BPF `tso_segs_goal` dependency rather than importing a BBRplus
  prerequisite. Native pacing helpers remain native. ECN_LOW/PLB are not claimed.
* **Pinned security sources:** vendored backslashxx KSU `ae63c92098d9` (+50,
  numeric 32730), existing package/certificate-pinned FinaSU compatibility,
  NoMount API23 `5e9feb6f3fce`, and original simonpunk SUSFS 2.4.0 adapted from
  GKI 5.10. Native/compat hooks, SUS_PATH and OPEN_REDIRECT are included without
  replacing the KSU fork/manager policy. No installer or build-time fetch runs.
  The updated base's vendor-hidden path and killable inode-lock fixes remain.
  SUSFS mount hooks use the native locked IDA paths; the anonymous-device decision
  is snapshotted once so a boot-state transition cannot pollute the normal ID cursor.
* **Selective 5.15-era BPF:** corrected ARM64 JMP32/atomics, verifier/maps/helpers,
  real pidfd lookup and task storage/run contexts, bounded build-ID handling,
  real softirq timer clock bases/tick integration, and dynamic lockdep-key
  lifetime. Preserve newer signal/clone handling; pidfd allocation returns its
  actual error and parent-TID/pidfd outputs cannot alias. Preserve native XDP
  zero-copy APIs while adding the required interfaces. Kernel/tools BPF UAPI
  matches. This is not complete 5.15 ABI or all-architecture parity.
* **E143:** `__SK_PASS` already exists in pinned16 `include/linux/skmsg.h` and
  stream/message consumers. No duplicate source change is made. Its supplied
  upstream reference identity remains unresolved and is not counted as applied.

The BPF patch's old LZ4 hunk was **excluded**. Official LZ4 1.11.1, caller-owned
HC workspaces, exports, preboot path, and the repaired exact-AOSP/manual-build/AK3
foundation remain byte-for-byte as sealed. Historical receipts are archived under
`batch-04/historical/`; none is resealed to claim this newer base is its old tree.

## Validation actually completed

Current evidence: [host matrix](remaining/host-regressions.log),
[earlier-six-suite rerun](remaining/earlier-host-regressions.log),
[stricter separate negative rerun](remaining/separate-negatives.log),
[ARM64 matrix](remaining/arm64-objects.log),
[LZ4 regressions](remaining/lz4-regressions.log),
[source verification](source-verification.log), and
[toolchain identity](remaining/toolchain.json).

* **25 carry-over host suites passed:** the earlier six plus 19 expanded suites.
  **167 regression controls** were rejected (34 earlier + 133 expanded). Tests
  use extracted production functions with mocked kernel facilities; compiled
  controls must reach runtime assertions/traps, not merely fail compilation.
* BORE exercises both group settings; Cambyses all four PREEMPT/WALT variants;
  vmalloc includes 400,000 oracle comparisons; procfs 58,806 formatting cases;
  F2FS merge models include 800 GC and 1,200 checkpoint requests. Security and
  BPF tests cover authorization, lifetime/error paths, ARM64 atomics/JMP32,
  softirq scheduling and dynamic lockdep-key retirement under host models.
* **74 explicit real-header ARM64 objects** plus the selected **kernel/bpf/**
  build directory passed with exact **AOSP r614150 / Clang 23.0.1**, full LLVM
  tools, integrated assembly, ThinLTO and shadow-call stack retained. Only Polly
  is disabled in the generated default output config. Additional **output-only**
  profiles compile MEMCG/LOCKDEP/F2FS compression/BPF events/stream-parser paths,
  then BORE/MGLRU/DEBUG_FS-off stubs. Disabled-only objects are not incorrectly
  treated as valid under the source default config. Generated profiles are
  recorded under `remaining/`; none activates these extras in the source defconfig.
* **LZ4 1.11.1 recheck passed:** 74 native ASan/UBSan tests, three architecture
  split-object checks and all 27 Kbuild selections. Synthetic build-script flow
  and invalid input/pin rejection passed. The fresh packaging fixture was
  **skipped** (no clean AnyKernel fixture supplied); prior foundation packaging
  evidence is historical, not a fresh package or boot test.
* Ordered replay verifies **73,279 pinned-base paths/modes** and **412 carried
  paths**, including declared source additions/modes. Repaired codec/build
  paths and immutable historical evidence remain unchanged. `validation.json`
  indexes current artifacts separately from the historical receipts.

An early matrix invocation incorrectly requested MEMCG/tracing-only objects
while their configs were off. The matrix was corrected to resolve their actual
Kconfig prerequisites in output-only profiles; the final complete matrix passed.
New Clang diagnostics in test shims/mutants were fixed without weakening
production warnings or counting compiler failures as semantic regression catches.

**Still unqualified:** full image and module linkage, vendor-module compatibility,
real concurrency/RCU/weak-memory/hotplug/reclaim/freezer/IRQ/LSM behavior, phone boot,
filesystem durability, power and performance. Configured defaults are not runtime
activation proof: ROM policy can override TCP/qdisc settings. Never flash merely
because these object and mock checks passed. Current base branding still reports
`4.14.357-openela-kinesis-omega-bpf`; this inventory reconciliation does not claim
to have completed the separate release-branding request.

## Reproduce

With Python 3, Git, make, host GCC and Clang/sanitizer runtimes available:

```sh
python3 tools/testing/selftests/carry_over/run_host.py --verify-source
python3 tools/testing/selftests/carry_over/run_extended.py --verify-source
TOOLCHAIN_DIR=/path/to/pinned/r614150 \
  bash tools/testing/selftests/carry_over/build_remaining.sh
TOOLCHAIN_DIR=/path/to/pinned/r614150 bash scripts/ci/test-lz4.sh
```

The target script needs normal host kernel-build development dependencies
(including bc/OpenSSL headers/libraries). `OUTPUT_DIR`, `JOBS` and
`EXTRA_HOSTCFLAGS` are configurable; default output is
`out/carry-over-remaining`. All target and Kbuild host compilers/tools are LLVM;
host GCC in the extracted models is not used as target-build proof. No command
above packages/flashes/pushes/dispatches GitHub Actions.

`carry_over/verify.py` is the current source verifier. It needs the local Git
objects for pinned16, previous Electro and the historical SUSFS header origin.
It replays batches 01 → 02 → 03 → 04 in disposable files, never into live source.
Earlier exact-checkpoint verifiers intentionally reject later authorized overlays.
The original batch-01/02 source receipts and logs remain unchanged below; their
20-object matrix is historical narrower coverage, not the current total.

## Batch 01 — E001–E020

[Exact applied delta](batch-01/applied.diff) · [source receipt](batch-01/source.json)

| IDs | Applied result |
|---|---|
| E001 | Remove `!PREEMPT` from exactly 16 ARM64 read/write-lock inlining selectors; no other Kconfig selector/default changes |
| E002–E005 | One corrected native memlat/SCM redesign covering four inspiration references, **not four literal donor cherry-picks** |
| E006 | Integer-only IPA producer wait: retain minimum 10000 us, permit maximum 12000 us; other equal-bound wait unchanged |
| E007 | Exactly two cpufreq-stat likelihood annotations, with no counter/locking/transition semantic change |
| E008 | Newly-idle balancing checks `READ_ONCE(nr_running)` and native `llist_empty(wake_list)`; no undefined donor feature guard |
| E009–E010 | Inline policy-free helper; use `fls()` normalization with the existing inverse-weight arithmetic and explicit bitops include |
| E011 | Suspend clock printer does not traverse parent clocks; existing suspend logging remains |
| E012–E013 | Final verity workqueue is bound, `CPU_INTENSIVE | MEM_RECLAIM | HIGHPRI`, max_active 0; no added tasklet feature |
| E014 | Remove GPU IRQ-only AO-counter debug reads and unused wrapper/prototype; retain polling, fault handling, recovery and lower-level users |
| E015–E016 | Balance topology cpufreq-policy references; remove successful IOMMU group-add informational print, retaining trace/error paths |
| E017 | Shared request timestamps and CFQ accounting use monotonic ktime; include the necessary **BFQ completion-reader correction** so producers/readers share a clock domain |
| E018–E019 | CFQ fallthrough annotation and clearing async queue pointers after dropping references, retaining statistics transfer |
| E020 | Record PM/GIC wake IRQ reasons regardless of the console-debug switch; console output remains gated |

Memlat uses public four-argument `perf_event_read_local()` calls on the owning
CPU, async callbacks with completion ownership/draining, sparse CPU indexing,
serialized start/sample/stop and creation-failure unwind. It does not publish
partial samples or advance baselines on failed reads. Offline/isolated epochs,
observed-idle no-IPI behavior, SCM/error skips, zero-cycle/elapsed-time arithmetic
and busy-SCM teardown retain the earlier corrected contracts. SCM's atomic count
is a **best-effort hint, not serialization**. Accounting remains outside noinline
fixed-register assembly workers; no long-call preemption-pinning shortcut is used.

Three earlier corrected scoped patches replayed cleanly on the new foundation.
The memlat and IPA/cpufreq source pre/post SHA-256 values still match the original
historical receipts exactly. The other selection is applied as a scoped delta,
not a wholesale restoration of files containing unrelated old changes.

## Batch 02 — E021–E027

[Exact applied delta](batch-02/applied.diff) · [source receipt](batch-02/source.json)

| IDs | Applied result |
|---|---|
| E021 | Compare group minimum/maximum CPU capacities directly; unrelated utilization margins unchanged |
| E022 | Mark the selected CPU and migrating-state reads/writes with READ_ONCE/WRITE_ONCE; retain existing write barrier, locks and wake_cpu behavior |
| E023 | Reject busiest-queue candidates with no runnable hierarchical CFS tasks before misfit/weighted-load cases |
| E024 | Disable IRQs **before** the offline-CPU check; use the direct stop-tick call, not the protected wrapper that re-enables IRQs; remove the later duplicate disable |
| E025 | IRQ-save KGSL syncsource locks in create/signal/cleanup; preserve reference/error paths |
| E026 | Optimize DEADLINE active-CPU counting while retaining the active-mask fallback and RCU contract |
| E027 | Use effective cpuset CPUs, retain NO_SETAFFINITY checks, reject missing destinations before lookup, and reject zero-active-CPU domains before division/reservation |

Both corrected historical scoped patches replayed cleanly after Batch 01. Their
original historical evidence is copied without changes under `historical/`.
No old scheduler/GPU file was substituted wholesale. No asym-packing, active-
balance-interval, GPU timeout, thermal or unrelated policy change is included.

