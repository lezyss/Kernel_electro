# Electro individual-change inventory — excluding SM8150 and Phoenix

> Base-sync follow-up: this inventory describes the PREVIOUS Electro build at402566a85.
> Source/evidence paths below refer to that historical commit, not a claim that
> these integrations are present after changing to updated16. See
> [the base-sync audit](base-sync-16/README.md). BBRplus is explicitly excluded
> from the new foundation/carry-over scope by the user's subsequent decision.

## Scope and reading this list

- Reference build/branch tip: `402566a8597ae7f0ecf3f87054b77aa7c18acdf0`, `arena/e63a046d-kernel-electro`.
- Excluded: the previously reviewed `LineageOS/android_kernel_qcom_sm8150` backport batch and the Phoenix batch. This excludes their bulk changes, not merely commit subjects containing those names. The SM8250 F2FS sysfs fix is a different donor and is retained.
- Included: separately documented later SM6250/SM6150/upstream work, local compatibility work and configuration/build changes. Review-only, rejected, skipped and already-equivalent proposals are not presented as new implementations.
- This is a source/reference inventory, NOT a cherry-pick script and NOT a claim that every row is a separate Git commit. Many changes were published in bundled commits; some were deliberately rewritten for native 4.14. Historical source pins are separated from current selections.
- Exact donor hashes are supplied where retained. A consolidated backport or local correction is labelled as such rather than inventing upstream commit identities. The ext4 donor identities and original ARM64 LZ4 assembly donor identity are not fully recoverable from the retained per-change records; those entries are code-scope records, not falsely exact commit attributions.
- This does NOT say which changes are missing from updated `16`. That needs a separate patch/code-equivalence audit. Do not blindly reapply this inventory over the updated base.

## A. Later Azyr review: applied selection

Evidence: `Documentation/dev-tools/azyr-sm6250-selected.md; azyr-sm6250-006-validation.json; azyr-sm6250-036-041-validation.json; azyr-sm6250-memlat-native-validation.json`.

Only approved applied items are included. A01-027–030 are four inspiration references for ONE corrected native memlat/SCM redesign, not four literal cherry-picks.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E001 | [`149e6887d341`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/149e6887d341948cb079ffab98845addd5e50381) | A01-006 — inline ARM64 rwlocks under PREEMPT; remove 16 !PREEMPT restrictions | Applied Kconfig change |
| E002 | [`d73dae72f581`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d73dae72f581c0b3fd6c4966773bbe14c6a4be74) | A01-027 — SCM-call accounting / avoid unsafe reads while SCM is busy | Reference for corrected native redesign; NOT verbatim donor |
| E003 | [`12798fd3c654`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/12798fd3c654f0584f54afadb027f96a07461555) | A01-028 — keep SCM accounting separate from fixed-register SMC assembly | Reference for corrected native redesign; NOT verbatim donor |
| E004 | [`143f07a8f3e7`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/143f07a8f3e77aae7dcb48979d424cd1e17b2c4a) | A01-029 — native asynchronous per-CPU memlat sampling with completion/lifetime handling | Reference for corrected native redesign; NOT verbatim donor |
| E005 | [`d7fda10ad1db`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d7fda10ad1dbb38279b6d24fdd9fbf40fca53b73) | A01-030 — use native four-argument perf_event_read_local API | Reference for corrected native redesign; NOT verbatim donor |
| E006 | [`28bc6f028c8e`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/28bc6f028c8ee2d2d972ed2284d0cb5973cf3c2d) | A01-036 — Corrected native integer-only delay in ipa3_disable_wdi_pipe producer path: minimum 10000 us preserved, maximum 12000 us; the other equal-bound sleep and all other IPA code unchanged. | Corrected adaptation |
| E007 | [`b0229e526d85`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b0229e526d8593782fa4806e28b16542b836bf61) | A01-041 — Exact donor two unlikely() annotations in cpufreq_stats_record_transition; no condition/statistics/locking changes. | Exact two likelihood annotations |
| E008 | [`dd7a5c396220`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/dd7a5c396220c22784135cfcc755de3bb3d6f110) | A01-046 — sched: Allow newidle balancing to bail out of load_balance | Corrected native adaptation |
| E009 | [`542e7b0ac23a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/542e7b0ac23af11146f642c4787a2b11bebf4454) | A01-047 — cpufreq: schedutil: Inline `sugov_policy_free()` | Applied; retained native integration |
| E010 | [`403836055eec`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/403836055eec7478e4e431828f0be0d650c39f9c) | A01-048 — sched: Optimize __calc_delta() | Applied; retained native integration |
| E011 | [`c0ff2a937bff`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c0ff2a937bff4080b8be6ece6e97ec193e2edfb0) | A01-052 — cpuidle: lpm_levels: Don't print parent clocks during suspend | Applied; retained native integration |
| E012 | [`69cf714073eb`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/69cf714073ebe9a68322e5d9041cb325220c0dcd) | A01-056 — dm-verity: Enable WQ_HIGHPRI on verify_wq | Applied; retained native integration |
| E013 | [`94a730ad0791`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/94a730ad07912c7157f227585a1a90c117e705bd) | A01-057 — dm-verity: Stop using WQ_UNBOUND for verify_wq | Applied; retained native integration |
| E014 | [`324bac57ebad`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/324bac57ebadbd785dbb0e666505b650880c4fa1) | A01-058 — adreno: Stop reading registers just for debugging | Applied; retained native integration |
| E015 | [`3ea82acbb35f`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3ea82acbb35fa12d0c3d09b0f9137240b532e536) | A01-078 — drivers: base/arch_topology: avoid a stuck risk when cpufreq policy free | Applied; retained native integration |
| E016 | [`3e87d0295c39`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3e87d0295c39b2bb9d080a6db7464a0de7a8d651) | A01-079 — drivers: iommu: silence logging | Applied; retained native integration |
| E017 | [`202b3995f9ad`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/202b3995f9ad16f01aab59847e1ab9d15afd802d) | A01-092 — BACKPORT: block: use ktime_get_ns() instead of sched_clock() for cfq | Corrected native adaptation |
| E018 | [`79431f18b1e1`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/79431f18b1e102a6813c746be21fee0a237006d9) | A01-093 — cfq: Annotate fall-through in a switch statement | Applied; retained native integration |
| E019 | [`522ab2ee25fc`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/522ab2ee25fc0c802c55ec269dc565411422c129) | A01-094 — cfq: clear queue pointers from cfqg after unpinning them in cfq_pd_offline | Applied; retained native integration |
| E020 | [`6bbaff1957fa`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/6bbaff1957fa023f5ff2bdb22714eab646abd689) | A01-098 — drivers: power/irqchip: Add wakeup irq loggers | Applied; retained native integration |

## B. Scheduler correctness and GPU/DEADLINE/cpuset

Evidence: `Documentation/scheduler/sched-correctness-backport.rst; Documentation/dev-tools/gpu-dl-backports.rst`.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E021 | [`298f4559960e`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/298f4559960e4e14c6ff43638a1da981cf95dee8) | Compare scheduler group min/max capacities directly | exact |
| E022 | [`56c8b07bc33b`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/56c8b07bc33bb8bf83d42834be446e831f47b29b) | Mark task-CPU and migration-state accesses | exact |
| E023 | [`75c9d3457a8a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/75c9d3457a8aedfe68ef0163b9b8d10c51248ed8) | Skip busiest queues with no runnable hierarchical CFS tasks | exact |
| E024 | [`e250ed8c4d54`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/e250ed8c4d54aa77f461347574cf2994f3bab0c0) | Correct CPU-offline idle IRQ ordering; direct stop-tick call | corrected: early IRQ disable, direct stop-tick, remove later duplicate disable |
| E025 | [`71a6c1d01b6f`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/71a6c1d01b6f2fcf407c79f252bb8b3d6177e077) | BACKPORT: msm: kgsl: Fix syncsource spinlock recursion | exact donor production change |
| E026 | [`bc7328a77b6b`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/bc7328a77b6be7591052cb226a029a33ee69d13e) | UPSTREAM: sched/deadline: Optimize dl_bw_cpus() | exact donor production change |
| E027 | [`ad1345b413fc`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/ad1345b413fca93af081b5e3be3fa6b85248a8a3) | sched, cpuset: Fix dl_cpu_busy() panic due to empty cs->cpus_allowed | corrected adaptation |

## C. BORE and Cambyses

Evidence: `Documentation/scheduler/bore-backport.rst; Documentation/scheduler/cambyses-backport.rst`.

BORE enabled for miatoll with PELT/CASS retained. Cambyses is upgraded to v0.7.2's idle-only, cheapest-candidate concession with a strict less-than-2x imbalance bound, adapted to retain tail-first scanning, the existing rq-clock guard and native migration safeguards. WALT is not activated.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E028 | [`a2c7aff131ae`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/a2c7aff131ae3ca2471f0134464e70a982176fff) | BORE 5.1.0, attributed to Masahito Suzuki/firelzrd's legacy Linux 4.19 BORE patches. | Adapted/applied |
| E029 | [`c684d01fc6f9`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/c684d01fc6f95413c4ce46fadcaf2c6f63123c18) | constant scheduler granularity. | Adapted/applied |
| E030 | [`222cfabd72a3`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/222cfabd72a3ca2f69c267decd3acee8278f268d) | short-burst smoothing enabled. | Adapted/applied |
| E031 | [`3001d4566a00`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/3001d4566a0021858005a91d51a6193c1b40ce30) | final granularity/bandwidth tuning. | Adapted/applied |
| E032 | [`e2c4678c8b53`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/e2c4678c8b532f58a22010e756e04d6da4ecf283) | always-inline task reweighting. | Adapted/applied |
| E033 | [`12cc0428dcbb`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/12cc0428dcbbe5085132cb02d30db92445935920) | WALT-only migration guards. | Adapted/applied |
| E034 | [`b53dda13d958`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/b53dda13d958ee8bf47e7ad9a9eda3bae51e7f47); [`330c39118a43`](https://github.com/firelzrd/cambyses/commit/330c39118a433047b0690d55826a8c04a38530a8) | Cambyses v0.7.2: retain tail-first block rotation and add the cheapest idle-destination concession bounded by `cost < 2 * imbalance` | Adapted for 4.14; preserves the half-imbalance fallback, 5 ms guard, two-task exception and WALT lock-drop safeguards |

## D. MGLRU source series: 30 included donor references

Evidence: `Documentation/vm/mglru-backport.rst`.

The recorded SOURCE range contains 32 commits. Do not count all 32 as applied: speculative-fault support and the five-second min_ttl default were omitted. Core boot enablement is a separate local config choice; TTL remains0.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E035 | [`27048e83e24d`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/27048e83e24d7f2fa141f1e5c769612170722527) | Reapply mm: introduce __lru_cache_add_active_or_unevictable | Part of adapted MGLRU series |
| E036 | [`150b3797156a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/150b3797156a7243ce0e4d2339c1193a5117b8f6) | UPSTREAM: mm: replace list_move_tail() with add_page_to_lru_list_tail() | Part of adapted MGLRU series |
| E037 | [`80429a3f5e58`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/80429a3f5e58e046d18ba34295f4b4c7e39a5f77) | UPSTREAM: arm64: cpufeature: introduce helper cpu_has_hw_af() | Part of adapted MGLRU series |
| E038 | [`f36d767468af`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f36d767468afda9ebba0bfde87f3974876565ce1) | UPSTREAM: mm/vmscan.c: use update_lru_size() in update_lru_sizes() | Part of adapted MGLRU series |
| E039 | [`53489d60f44c`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/53489d60f44c4b9f117571c37e32da1370f650ae) | BACKPORT: mm/swapcache: support to handle the shadow entries | Part of adapted MGLRU series |
| E040 | [`f51ecb574eec`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f51ecb574eecf197ffb37d3c6fbc576844a3f90c) | BACKPORT: mm: remove superfluous __ClearPageActive() | Part of adapted MGLRU series |
| E041 | [`bf8641c30a78`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/bf8641c30a7831f3da8010ad543e63bc147b33d6) | BACKPORT: mm: use self-explanatory macros rather than "2" | Part of adapted MGLRU series |
| E042 | [`ba8564c12027`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/ba8564c1202704507dc77d8daca22eb80f6c8003) | BACKPORT: mm/vmscan.c: use add_page_to_lru_list() | Part of adapted MGLRU series |
| E043 | [`f97327ca66e9`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f97327ca66e9c855951076ba75e157d61e45b9f2) | BACKPORT: include/linux/mm_inline.h: shuffle lru list addition and deletion functions | Part of adapted MGLRU series |
| E044 | [`2615fc64834f`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/2615fc64834fbb21d7eaed52958255d2ea57a069) | BACKPORT: mm: don't pass "enum lru_list" to lru list addition functions | Part of adapted MGLRU series |
| E045 | [`cf8e44a06b89`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/cf8e44a06b890a55a819bc3459df51aa0a5d1ac7) | UPSTREAM: mm/swap.c: don't pass "enum lru_list" to trace_mm_lru_insertion() | Part of adapted MGLRU series |
| E046 | [`22902855a338`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/22902855a3380aecd81938d6d64dc43183bb5e39) | BACKPORT: mm/swap.c: don't pass "enum lru_list" to del_page_from_lru_list() | Part of adapted MGLRU series |
| E047 | [`f4aaf1dfa4c4`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f4aaf1dfa4c45dc56bf48f484f79e539d8d10fc9) | BACKPORT: mm: add __clear_page_lru_flags() to replace page_off_lru() | Part of adapted MGLRU series |
| E048 | [`c216026c8a0b`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c216026c8a0bba13a265be5e08addc2636a71bb5) | UPSTREAM: mm: VM_BUG_ON lru page flags | Part of adapted MGLRU series |
| E049 | [`38f9bf9fcbbf`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/38f9bf9fcbbfbd7bc8aabedcefe34ea09fb37b25) | BACKPORT: include/linux/mm_inline.h: fold page_lru_base_type() into its sole caller | Part of adapted MGLRU series |
| E050 | [`bc21327232c6`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/bc21327232c6b3d0db2a4a11987e60a546b7cba6) | FROMLIST: mm: x86, arm64: add arch_has_hw_pte_young() | Part of adapted MGLRU series |
| E051 | [`b0b10a2cb89f`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b0b10a2cb89fcbca4993f6716f05f7470153f28b) | FROMLIST: mm: x86: add CONFIG_ARCH_HAS_NONLEAF_PMD_YOUNG | Part of adapted MGLRU series |
| E052 | [`b329a95b729e`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b329a95b729e5744b81e9b689d9295b31cae8f54) | FROMLIST: mm: multi-gen LRU: groundwork | Part of adapted MGLRU series |
| E053 | [`d04b362714e9`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d04b362714e983a0a4371520e01bef0ecda42fb9) | FROMLIST: mm: multi-gen LRU: minimal implementation | Part of adapted MGLRU series |
| E054 | [`75713ae4030e`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/75713ae4030eb0a07f23c1cffea99f797bf91497) | FROMLIST: mm: multi-gen LRU: exploit locality in rmap | Part of adapted MGLRU series |
| E055 | [`cc109a443214`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/cc109a443214740677c2f5bdc4feb98bac50f839) | FROMLIST: mm: multi-gen LRU: support page table walks | Part of adapted MGLRU series |
| E056 | [`be671e5364be`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/be671e5364be509f616627b7e7de157dc6b04c14) | FROMLIST: mm: multi-gen LRU: optimize multiple memcgs | Part of adapted MGLRU series |
| E057 | [`3c8d5dcc8bf0`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3c8d5dcc8bf0fa170e9e101abf052300da8f7f40) | FROMLIST: mm: multi-gen LRU: kill switch | Part of adapted MGLRU series |
| E058 | [`67e4305510a1`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/67e4305510a13d671b09363007986eb17da8c0f6) | FROMLIST: mm: multi-gen LRU: thrashing prevention | Part of adapted MGLRU series |
| E059 | [`cce036fef9e6`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/cce036fef9e6efe52eaecffaaff7c8cc35a2cb96) | FROMLIST: mm: multi-gen LRU: debugfs interface | Part of adapted MGLRU series |
| E060 | [`f889fcd02d02`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/f889fcd02d02cae8878c020ede8c7a086e8fcda2) | mglru: fixes | Part of adapted MGLRU series |
| E061 | [`b40b16274a26`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b40b16274a26e5cc62b8109cb2a6ea197a6fc25f) | mm/mglru: don't sync disk for each aging cycle | Part of adapted MGLRU series |
| E062 | [`c2d7c83deb22`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/c2d7c83deb22cf5ed3b65d5c50a0e79864472b15) | mm: vmscan: Fix error when CONFIG_DEBUG_FS is disabled | Part of adapted MGLRU series |
| E063 | [`fa3bb3287d2a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/fa3bb3287d2a649c4bfbcfa2d84c17bf1333a1ba) | mm: vmscan: Don't create debugfs when CONFIG_DEBUG_FS is disabled | Part of adapted MGLRU series |
| E064 | [`3728f6da063f`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3728f6da063f3ac72a0fe71262e9ebfec1f01799) | mm: multi-gen LRU: fix crash during cgroup migration | Part of adapted MGLRU series |

## E. Six selected MM fixes

Evidence: `Documentation/vm/mm-selected-backports.rst`.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E065 | [`18ad7ca0baf1`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/18ad7ca0baf1b4edbe09aa5c14a8599b22ba4909) | Filemap: guard missing readpage callbacks | Adapted/applied |
| E066 | [`b4b6f5c674a5`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/b4b6f5c674a5c8efebc3c9cbfdf3ae7d0e0a5935) | Readahead: guard absent callbacks and preserve page/plug cleanup | Adapted/applied |
| E067 | [`06295c9d8cf9`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/06295c9d8cf9d940b7e7b3246cf6137bf60c783b) | Cold swap-in PSI exclusion; match both enter and leave using one workingset snapshot | Adapted/applied |
| E068 | [`c1965b973003`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/c1965b9730031fa0c8ac368dfc6d9de6d86037e1) | quiet_vmstat likelihood hints | Adapted/applied |
| E069 | [`433c12bbd29b`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/433c12bbd29ba45412a0e606acd4c737cce1fa65) | Compaction retry escalation; correct native trace feedback | Adapted/applied |
| E070 | [`864be1f4870e`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/864be1f4870e55172c3a587781f9ef091319917e) | Complete zero-seek shrinker handling and users | Adapted/applied |

## F. Corrected vmalloc series: first 16 only

Evidence: `Documentation/vm/vmalloc-backport.rst`.

Item16 uses the canonical upstream unlock-order fix instead of the broken donor. Item17 was not applied. Native adaptations include alignment/overflow-safe fit search, early metadata OOM handling and preserved per-CPU protection.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E071 | [`3ab436a744c5`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/3ab436a744c58e538f13f7c76d042e508b0cdc1e) | 1. SHMLBA alignment | Adapted/applied |
| E072 | [`686db5c5c84a`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/686db5c5c84ad2fc8f0aa5391870c5bfed9e8bf3) | 2. Pass VM_USERMAP directly | Adapted/applied |
| E073 | [`f75b713d9a23`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/f75b713d9a23f8b8fc9fb9d19ed7f2e8822ae059) | 3. Lazy-purge threshold | Adapted/applied |
| E074 | [`46a3b96a5a06`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/46a3b96a5a06feaff17526ed505989c4d5136540) | 4. atomic_long lazy counter | Adapted/applied |
| E075 | [`255e313d2ad1`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/255e313d2ad1bb019fece98d4fc315645de090b9) | 5. Augmented free-block allocator | Adapted/applied |
| E076 | [`a3ac4fd0986b`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/a3ac4fd0986b630c0c8f89829b105b2ef0c714a9) | 6. Remove unused node argument | Adapted/applied |
| E077 | [`5021f6a5d420`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/5021f6a5d420133f7439a27aaf72d6d431ae5e4a) | 7. Split-node preloading | Adapted/applied |
| E078 | [`7ef1c5c16b22`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/7ef1c5c16b22d7aa3017280670d83629e32f9b27) | 8. Avoid redundant unlink | Adapted/applied |
| E079 | [`902781dbff5c`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/902781dbff5c4e0772cb8f8d4be7a86315bf1172) | 9. Warn on invalid unlink | Adapted/applied |
| E080 | [`5d1313d1b8bd`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/5d1313d1b8bd53d63477fbb671c43410a0cfad30) | 10. Per-CPU search correction | Adapted/applied |
| E081 | [`64fba55ad565`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/64fba55ad5656021ebcd83966c28b3d2190b65dd) | 11. Detach pending areas from busy tree | Adapted/applied |
| E082 | [`626616a53457`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/626616a53457553bd19db2dee9419f63181e0406) | 12. State-dependent metadata union | Adapted/applied |
| E083 | [`69058cd6516c`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/69058cd6516c9a9ff73a7fca14f383db378a34f2) | 13. Speculative preload without pinning | Adapted/applied |
| E084 | [`2e4f46245786`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/2e4f46245786621a6334fbdfc009ec8e5d99582a) | 14. Respect caller GFP mask | Adapted/applied |
| E085 | [`aa7f703ce3ef`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/aa7f703ce3ef77974172205272ac0344980b5c67) | 15. Separate busy/free locks | Adapted/applied |
| E086 | [`0a7dd4e901b8`](https://github.com/torvalds/linux/commit/0a7dd4e901b8a4ee040ba953900d1d7120b34ee5) | 16. Fix unlock order in s_stop(); retain BOTH unlocks | Adapted/applied |

## G. Procfs maps/smaps: 13 donor changes

Evidence: `Documentation/filesystems/procfs-backport.rst`.

Includes local corrections for decimal-width padding, VmExe/VmLib units, locked-PSS accounting, empty address spaces and 32-bit-safe PSS arithmetic. These corrections belong to the port, not extra donor commits.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E087 | [`06330f5b58f9`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/06330f5b58f958c1c51a7c2f2e5f95f3e254fceb) | revert forced little-cluster migration during maps reads. | Adapted/applied |
| E088 | [`ce389dc0f59a`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/ce389dc0f59a5112175fbf8e633a158e2695fb74) | revert the custom ARM64 formatter and d_path_outlen() path plumbing. | Adapted/applied |
| E089 | [`b810878560ba`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/b810878560ba56cabdfaab57e4aaf263175de011) | width-aware decimal printing. | Adapted/applied |
| E090 | [`686a9a059677`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/686a9a0596776176dc9661785a6a21662a64dd21) | hex sequence printing. | Adapted/applied |
| E091 | [`ad17b568d5b7`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/ad17b568d5b78351d48cc074c9e49f56901f634b) | shared PID/TID map handlers. | Adapted/applied |
| E092 | [`3638aadffd8b`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/3638aadffd8b9c06e0dd56aef3112b618398f64e) | gather smaps statistics. | Adapted/applied |
| E093 | [`90208857deb0`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/90208857deb019965cc1bde69584e103e52dd5bc) | common statistics printer. | Adapted/applied |
| E094 | [`2321653ec0a7`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/2321653ec0a7cb2ab31b672463dd96a4b0a9bb6c) | single-value smaps_rollup. | Adapted/applied |
| E095 | [`869fd85e1014`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/869fd85e10145d0cdd986f367ddb72e173dfd343) | no-pkey vma_pkey() fallback. | Adapted/applied |
| E096 | [`76f0d41fa56f`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/76f0d41fa56f5bb55bbe010d9e8b72f3d53ce965) | no-pkey arch_pkeys_enabled(). | Adapted/applied |
| E097 | [`8ff3cde162fd`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/8ff3cde162fdb52ad4a8f029a6252af10d9e73e9) | include linux/pkeys.h. | Adapted/applied |
| E098 | [`d10c142d7e21`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/d10c142d7e218a5eaa726bb006c3769f31523228) | Pss_Anon/File/Shmem rollup. | Adapted/applied |
| E099 | [`0253fe413143`](https://github.com/AzyrRuthless/kernel_xiaomi_sm6250/commit/0253fe4131436c2eb155a109ce55671a42366b3e) | snapshot map_files addresses under mmap_sem and format names after releasing it. | Adapted/applied |

## H. Filesystem lifetime/locking fixes

Evidence: `tools/testing/selftests/fs_backport/README; Documentation/filesystems/f2fs-sysfs-width.rst`.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E100 | [`45c506bd3b8d`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/45c506bd3b8de8e79e09b4350354b211ab498aeb) | F2FS compression reserve/release: hold checkpoint operation read lock across dnode operations | Corrected/native adaptation where needed |
| E101 | [`d287de5bde53`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/d287de5bde53a9777d9bf68a166102fa03f7b92a) | F2FS GC: reject inline-data/external-block inconsistency; log before dropping inode reference | Corrected/native adaptation where needed |
| E102 | [`00ad9f944286`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/00ad9f9442869ff7cb38f5329f9e1f6a3ce684d6) | F2FS move-range and pin-file ioctls: reject atomic files with correct lock/cleanup ordering | Corrected/native adaptation where needed |
| E103 | [`655ae9dbb75a`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/655ae9dbb75a0c11932f8a8a728fdb7c8b9f323d) | Epoll: take a positive-count temporary file reference around poll; preserve native fallback | Corrected/native adaptation where needed |
| E104 | [`7209a1acc23b`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/7209a1acc23b95bbee4bfee238e2fac417d2709a) | Writeback: protect freeing-inode lists with corrected late dirty-state handling | Corrected/native adaptation where needed |
| E105 | [`3fcb7aa3e71b`](https://github.com/LineageOS/android_kernel_qcom_sm8250/commit/3fcb7aa3e71b25a6bc096ab6d6609ee716f59403) | F2FS sysfs: size-aware1/2/4/8-byte access for42 local RW/stat attributes | Local width-aware adaptation; SM8250 donor, NOT excluded SM8150 series |

## I. Selective F2FS A → B1 → B2

Evidence: `Documentation/filesystems/f2fs-staged/UPSTREAM.json; Documentation/filesystems/f2fs-staged/implementation.md`.

A is correctness work. GC merge and checkpoint merge are implemented but opt-in/default off. These are adapted reference scopes, NOT a full import of81605352. A pre-existing checkpoint-disabled prerequisite is not counted as newly applied; the writable priority knob was excluded.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E106 | [`5cdb422c8391`](https://github.com/torvalds/linux/commit/5cdb422c839134273866208dad5360835ddb9794) | f2fs: fix to avoid use-after-free for cached IPU bio — adapted IPU missing-selector fix; caller and helper guarded | Adapted reference scope |
| E107 | [`edf7e9040fc5`](https://github.com/torvalds/linux/commit/edf7e9040fc52c922db947f9c6c36f07377c52ea) | f2fs: fix UAF issue in f2fs_merge_page_bio() — adapted encrypted-page lifetime fix to original struct page; accounting also moved before publication | Adapted reference scope |
| E108 | [`6d1f622b9c06`](https://github.com/torvalds/linux/commit/6d1f622b9c069378cdb83088be2b15a9b480b8a3) | f2fs: fix submit accounting for IPU writeback — successful IPU submission accounting | Adapted reference scope |
| E109 | [`5911d2d1d1a3`](https://github.com/torvalds/linux/commit/5911d2d1d1a38b26585383478bd71d9254e48bdf) | f2fs: introduce gc_merge mount option — GC merge intent; adapted to local four-argument GC and embedded request lifetime | Adapted reference scope |
| E110 | [`8b4468ec023d`](https://github.com/torvalds/linux/commit/8b4468ec023d0d1b4669dfb867588997cc03a06b) | f2fs: fix potential deadlock in gc_merge path of f2fs_balance_fs() — drain cached OPU and all IPU writes before GC waits; also used before checkpoint queueing | Adapted reference scope |
| E111 | [`1adaa71ea9bf`](https://github.com/torvalds/linux/commit/1adaa71ea9bff3a0ca0b37eabbb7f89225b595cb) | f2fs: don't bother wait_ms by foreground gc — foreground GC must not overwrite background sleep interval | Adapted reference scope |
| E112 | [`261eeb9c1585`](https://github.com/torvalds/linux/commit/261eeb9c1585de4515a770b48a3c89672c08ae7f) | f2fs: introduce checkpoint_merge mount option — checkpoint merge intent; adapted request lifetime, publication, ownership, errors and stop | Adapted reference scope |
| E113 | [`7b02b2201893`](https://github.com/torvalds/linux/commit/7b02b2201893a71b881026cf574902019ab00db5) | f2fs: fix to destroy sbi->post_read_wq in error path of f2fs_fill_super() — checkpoint startup failure must retain post_read_wq cleanup | Adapted reference scope |
| E114 | [`f6f8f34480c7`](https://github.com/torvalds/linux/commit/f6f8f34480c78eade6542faea6386c47c9b4c6b3) | f2fs: quota: fix quota flush failure during filesystem freeze — reviewed freeze/quota cross-task issue; local worker trylock/ownership and caller fallback instead of holder-tracking transplant | Adapted reference scope |

## J. Other individually recorded codec/hash/ZRAM changes

Evidence: `Documentation/dev-tools/lz4-backport.rst; Documentation/dev-tools/lz4-1.11.json; source diffs`.

Historical v1.10 is listed separately below; current block codec is v1.11. No frame/CLI/userspace codec import.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E115 | [`c72c7c0ec132`](https://github.com/lz4/lz4/commit/c72c7c0ec132ad2ce2fe9fad7b0c728d9faee2fc) | Upgrade block LZ4/LZ4HC to v1.11.0 (PR2037); retain kernel workspaces, exports and preboot support | Current adapted upstream snapshot |
| E116 | [`730abe07b866`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/730abe07b8660c14343031a29e2fea0c1ea045b5) | zram: do not waste zram_table_entry flags bits | Adapted/applied |
| E117 | [`d8dfb8482b99`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/d8dfb8482b99ded3f6a0b57395e7edf109acea89) | xxhash: create arch-dependent32/64-bit xxhash() | Adapted/applied |

## K. BBRplus / BBRv3 and transport prerequisites

Evidence: `Documentation/networking/bbrplus-backport.rst; Documentation/networking/bbr3-validation.json; Documentation/networking/bbr3-edt-validation.json`.

BBRplus remains available, but its former default is superseded by bbr3. EDT is now included despite older baseline records listing it as excluded. ECN_LOW/PLB and other still-excluded features are not listed as applied.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E118 | [`40213eb493f2`](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/40213eb493f20807f05e830d5777ed58d3d47f39) | BBRplus port; wire TSO callback/fallback, GPL export and private helpers | Adapted/applied |
| E119 | [`90210de4b779`](https://github.com/google/bbr/commit/90210de4b779d40496dee0b89081780eeddf2a60) | Google BBRv3 loss-based implementation, adapted to native 4.14 TCP and later EDT forecast | Current adapted source snapshot |
| E120 | [`a627517bdfe0`](https://github.com/google/bbr/commit/a627517bdfe01967c3f8b931cfce99abfa878ef5) | net-tcp_bbr: v2: shrink delivered_mstamp, first_tx_mstamp to u32 to free up 8 bytes | Selective native prerequisite integration |
| E121 | [`0e6b4413cb4a`](https://github.com/google/bbr/commit/0e6b4413cb4a6a951532611bccd6aca4b22b5bbf) | net-tcp_bbr: v2: snapshot packets in flight at transmit time and pass in rate_sample | Selective native prerequisite integration |
| E122 | [`3679f3b8da5a`](https://github.com/google/bbr/commit/3679f3b8da5a5b2528b6e14c5510617ed83db72b) | net-tcp_bbr: v2: count packets lost over TCP rate sampling interval | Selective native prerequisite integration |
| E123 | [`500bcfec22c4`](https://github.com/google/bbr/commit/500bcfec22c478f4f1e07f66fd2a23ab2184b361) | net-tcp_bbr: v2: export FLAG_ECE in rate_sample.is_ece | Selective native prerequisite integration |
| E124 | [`f2078939d4a8`](https://github.com/google/bbr/commit/f2078939d4a8cee55dc24cb4736b1fbb9eae5f97) | net-tcp_bbr: v2: introduce ca_ops->skb_marked_lost() CC module callback API | Selective native prerequisite integration |
| E125 | [`88e09e2b7c84`](https://github.com/google/bbr/commit/88e09e2b7c845db4faa3532903da453db745b39c) | net-tcp_bbr: v2: adjust skb tx.in_flight upon merge in tcp_shifted_skb() | Selective native prerequisite integration |
| E126 | [`5093de531d14`](https://github.com/google/bbr/commit/5093de531d14d864bbc95bd5d3031f3996dc88fc) | net-tcp_bbr: v2: adjust skb tx.in_flight upon split in tcp_fragment() | Selective native prerequisite integration |
| E127 | [`a631934cbcd8`](https://github.com/google/bbr/commit/a631934cbcd8cddc4bac7d3fb91f890a3c07cd85) | net-tcp_bbr: v2: record app-limited status of TLP-repaired flight | Selective native prerequisite integration |
| E128 | [`3ee83ca004fa`](https://github.com/google/bbr/commit/3ee83ca004fafa436d448c261472ebe3b1942b42) | net-tcp_bbr: v2: inform CC module of losses repaired by TLP probe | Selective native prerequisite integration |
| E129 | [`703f20a1052d`](https://github.com/google/bbr/commit/703f20a1052d0c024f0e78bd1228eee6906dabf8) | net-tcp_bbr: v2: introduce is_acking_tlp_retrans_seq into rate_sample | Selective native prerequisite integration |
| E130 | [`137a508c9508`](https://github.com/google/bbr/commit/137a508c950878712068b1d7a67ece75e4f2835c) | net-tcp_bbr: broaden app-limited rate sample detection | Selective native prerequisite integration |
| E131 | [`ab408b6dc744`](https://github.com/torvalds/linux/commit/ab408b6dc7449c0f791e9e5f8de72fa7428584f2) | TCP/fq EDT model; adapted, not wholesale patch applied | Adapted EDT reference |
| E132 | [`08e14fe429a0`](https://github.com/torvalds/linux/commit/08e14fe429a07475ee9f29a283945d602e4a6d92) | EDT packets must still honor fq maxrate | Adapted EDT reference |

## L. Root/manager/NoMount/SUSFS source integrations

Evidence: `drivers/kernelsu/UPSTREAM.json; fs/nomount/UPSTREAM.json; Documentation/dev-tools/finasu-manager.json; Documentation/filesystems/susfs/backport-2.4.0.json`.

Version snapshots/imports are not a claim that every commit in the upstream repository was individually cherry-picked. Superseded pins appear in the historical appendix instead of being duplicated as current features.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E133 | [`ae63c92098d9`](https://github.com/backslashxx/KernelSU/commit/ae63c92098d94bdad1696c74a3ad2e96692118bf) | backslashxx KernelSU v3.3.1+50, numeric32730; built-in native/compat integration | Current exact vendored kernel snapshot plus local overrides |
| E134 | [`2d5786b9129a`](https://github.com/LyraVoid/FinaSU/commit/2d5786b9129a254a87ac358c8bec0203ccd53351) | FinaSU manager compatibility: package/certificate-pinned authorization and retained single-manager UID policy | Manager review pin; native compatibility adaptation, not app import |
| E135 | [`5e9feb6f3fce`](https://github.com/maxsteeel/nomount/commit/5e9feb6f3fce42423f56b37e344052c59ec16b66) | NoMount dev v2.3/API23; exact C/header, hardened built-in build files | Current pinned kernel-source import; no module installer |
| E136 | [`45a057536ddb`](https://gitlab.com/simonpunk/susfs4ksu/-/commit/45a057536ddba12fd59fb583a8f5375f83be703e) | Original simonpunk SUSFS2.4.0 adapted from GKI5.10 to native 4.14/backslashxx | Current adapted source pin; gki-android12-5.10 |

## M. BPF/timer reference identities

Evidence: `Documentation/bpf/bpf-5.15-upgrade.json; Documentation/bpf/bpf-5.15-upgrade.rst`.

The BPF upgrade is a SELECTIVE consolidated backport with native corrections, not a history-preserving cherry-pick of every upstream 5.15 commit. The functional breakdown follows below; do not invent separate upstream hashes for those local adaptations.

| ID | Donor/reference commit | Individual change | Application |
|---|---|---|---|
| E137 | [`d22fb4cf8eed`](https://github.com/NothingNormal/Kernel/commit/d22fb4cf8eedba08edff893f49c284299095715b) | Initial ARM64 JMP32 correction; later integrated atomic fixes extend it | Applied adaptation/reference identity |
| E138 | [`2a58cdc0636e`](https://github.com/NothingNormal/Kernel/commit/2a58cdc0636e8eedba246338dd565bbfffc84837) | Consolidated Android-focused5.15-era BPF core reference, selectively integrated | Applied adaptation/reference identity |
| E139 | [`63e2ed365975`](https://github.com/torvalds/linux/commit/63e2ed3659752a4850e0ef3a07f809988fcd74a4) | Shared hrtimer prerequisite: mode-aware start tracepoint | Applied adaptation/reference identity |
| E140 | [`42f42da41b54`](https://github.com/torvalds/linux/commit/42f42da41b54c191ae6a775e84a86c100d66c5e8) | Shared hrtimer prerequisite: real soft/hard clock bases and is_soft initialization | Applied adaptation/reference identity |
| E141 | [`5da70160462e`](https://github.com/torvalds/linux/commit/5da70160462e80b0ab8a6960cdd0cdd476907523) | Shared softirq hrtimer foundation endpoint; adapted, not a verbatim full-series replay | Applied adaptation/reference identity |
| E142 | [`108c14858b9e`](https://github.com/torvalds/linux/commit/108c14858b9ea224686e476c8f5ec345a0df9e27) | Reference for real dynamic lockdep-key registration/lifetime integration | Applied adaptation/reference identity |
| E143 | [`636633e1d9b1`](https://github.com/torvalds/linux/commit/636633e1d9b1617842eff0ff3f5c9511b2d7a4d2) | Reference for stream-parser __SK_PASS restoration | Applied adaptation/reference identity |

## N. Native/local changes without an independent donor commit

These are individual integration/configuration scopes, not additional donor commits. They must be checked in final source/config when syncing.

1. **Ext4 directory-entry validation** — Reject a dot entry that occupies the last record in a directory data block. Evidence: `fs/ext4/dir.c; diff against original base`.
2. **Ext4 early inode-body xattr validation** — Call xattr_check_inode before inline-data/xattr use; share declaration/macro across inode.c and xattr.c. Evidence: `fs/ext4/{inode.c,xattr.c,xattr.h}; diff against original base`.
3. **Repaired optional ARM64 LZ4 acceleration** — Avoid SCS x18 use; remove input-rewriting DIP exits; use guarded direct-call NEON block decode with C tail/fallback and proper kernel SIMD handling. Evidence: `Publication1a206aea0 and tools/testing/selftests/lz4`.
4. **LZ4 v1.11 follow-up compatibility** — Preserve kernel workspaces/exports, STATIC preboot and dictionary continuation; fix __noinline__ attribute spelling for macro compatibility. Evidence: `Documentation/dev-tools/lz4-1.11.json; BPF integration record`.
5. **MGLRU boot activation** — Select LRU_GEN and LRU_GEN_ENABLED on miatoll; keep stats off and min_ttl0. Evidence: `Documentation/vm/mglru-backport.rst`.
6. **MGLRU native safety corrections** — Retain shadow cleanup, cgroup-migration integration and legacy4.14 fallback/control behavior from the adapted series. Evidence: `Documentation/vm/mglru-backport.rst; tools/testing/selftests/mglru`.
7. **BORE miatoll activation** — Enable adapted BORE5.1.0 with its recorded constant granularity/smoothing settings; retain PELT/CASS and WALT-off policy. Evidence: `Documentation/scheduler/bore-backport.rst`.
8. **Cambyses native corrections** — Tail-first cyclic block rotation, flush rejected blocks before detach, cheapest idle-destination concession strictly below twice the remaining imbalance, and no live cursor/candidate across WALT lock-dropping detach paths; retain the 4.14 half-imbalance fallback and two-task exception. Evidence: `Documentation/scheduler/cambyses-backport.rst; tools/testing/selftests/cambyses`.
9. **Scheduler newly-idle correction** — Use READ_ONCE(nr_running) and the real pending wake-list check; do not use donor undefined preprocessor guards. Evidence: `Documentation/dev-tools/azyr-sm6250-selected.md`.
10. **Shared block timestamp correction** — Move CFQ/shared request timestamp setters AND BFQ completion reader to matching monotonic ktime_get_ns semantics. Evidence: `Documentation/dev-tools/azyr-sm6250-selected.md`.
11. **Native SCM accounting** — Migration-safe accounting outside untouched raw SMC workers; balanced nested/error lifecycle. Evidence: `Documentation/dev-tools/azyr-sm6250-memlat-native-validation.json`.
12. **Native memlat sampling lifecycle** — Public async SMP API, per-CPU completion/data ownership, hotplug read locking, event-read error/no-partial-publication handling, startup unwind and busy-SCM teardown. Evidence: `tools/testing/selftests/memlat/README`.
13. **F2FS GC merge lifecycle** — Embedded request lifetime/admission generations; cached OPU/all-IPU draining; safe freeze/stop/fallback behavior. Feature remains opt-in/default off. Evidence: `Documentation/filesystems/f2fs-staged/implementation.md`.
14. **F2FS checkpoint merge lifecycle** — Plain CP_SYNC batching only; publication/stop ownership, error cleanup and quota/freeze trylock fallback. Feature remains opt-in/default off. Evidence: `Documentation/filesystems/f2fs-staged/implementation.md`.
15. **KSU built-in native integration** — Vendored ordinary files, opt-in Kconfig, private SELinux header generation, native/compat hooks and downstream API adaptations. Evidence: `Documentation/dev-tools/kernelsu-vendoring.md`.
16. **FinaSU trust integration** — Certificate/package verification, manager UID/scanner/metadata compatibility; no broad authorization bypass or manager-fork replacement. Evidence: `Documentation/dev-tools/finasu-manager.md`.
17. **KSU ADB root activation** — CONFIG_KSU_FEATURE_ADBROOT=y; runtime toggle initially off. Evidence: `Publicationc6de0ddbe`.
18. **KSU+50 native hook/API corrections** — Original syscall exactly once; preserve reviewed SU-session handoff, post-success FD authorization and independent SELinux guards; preserve native helper bindings. Evidence: `Documentation/dev-tools/kernelsu-updates/v3.3.1+50.md`.
19. **KSU+50 sulog configuration transition** — Remove obsolete CONFIG_KSU_FEATURE_SULOG selector; unified upstream logging remains runtime-controlled. Evidence: `Documentation/dev-tools/kernelsu-updates/v3.3.1+50.md`.
20. **NoMount build hardening adaptation** — Retain KEYS dependency, default-off Kconfig with built-in miatoll selection, GNU11 and native xattr.__get detection; omit upstream -O3/-fno-stack-protector/Git probing. Evidence: `Documentation/filesystems/nomount-integration.md`.
21. **NoMount API23 rule/enumeration/cache update** — uid_count/default-slot rules, exclusion-overlap validation, full-name bucket indexing, native cookie fragments, refcounted leaves, backing-file cache/seek/xattr updates and explicit GET_LIST completion. One upstream update, not seven invented commits. Evidence: `Documentation/filesystems/nomount-update-23.md`.
22. **SUSFS native non-GKI adaptation** — Preserve physical-unmount guards, native 4.14 APIs, KSU/NoMount integration and genuine SELinux policy handling. Evidence: `Documentation/filesystems/susfs/integration.md; backport-2.4.0.json`.
23. **SUSFS selected feature activation** — Keep selected SUS_PATH/MOUNT/KSTAT, TRY_UMOUNT, uname/cmdline spoofing, logging, symbol hiding, OPEN_REDIRECT and SUS_MAP configuration; enable priority UID filtering in2.4. Evidence: `arch/arm64/configs/vendor/xiaomi/miatoll_defconfig; SUSFS receipts`.
24. **BBRv3 default selection** — Switch miatoll from BBRplus to bbr3; retain BBRplus, BBR/CUBIC alternatives and existing TCP caps. Evidence: `Publicationfb78b4118`.
25. **Native TCP EDT integration** — Carry EDT metadata through native TCP scheduling and fq deadline handling; retain legacy pacing fallback and add BBRv3 flight forecasting. Evidence: `Documentation/networking/bbr3-edt-validation.json`.
26. **fq default activation** — Build/select fq so the EDT path is usable; retain fq_codel availability. Runtime egress/device performance still require testing. Evidence: `Publication6854a5c9f`.
27. **Release identity** — Retain Electro release branding4.14.357-electro rather than Kinesis/omega-bpf naming; distinguish SUSFS-spoofed uname from actual build identity. Evidence: `Makefile; init/version.c; existing integration record`.
28. **SIMPLE_GPU_ALGORITHM selection** — Retain the explicitly selected local GPU algorithm integration/configuration; do not copy rejected GPU idle-timeout changes. Evidence: `drivers/devfreq/simple_gpu_algorithm.c; miatoll_defconfig`.

## O. BPF functional scopes inside the consolidated backport

All entries below are native/adapted parts of the references in section M. They are NOT a new list of independent source commits. Evidence: `Documentation/bpf/bpf-5.15-upgrade.rst` and `.json`.

1. ARM64 JMP32 width-correct comparison/test/immediate handling.
2. ARM64 BPF atomic fetch/logical/exchange/compare-exchange, covering LSE and LL/SC.
3. Atomic register-alias/address preservation, compare operand and failed-comparison barriers.
4. Replace signed negative branch-displacement shifts with defined64-bit arithmetic.
5. Verifier/tnum/scalar tracking and corresponding helper/UAPI updates.
6. BTF handling, iterator/map support and networking/cgroup call-site reconciliation.
7. Keep kernel/tools UAPI helper tables consistent, including176 helper IDs.
8. Real task/run-context integration across fork and seq-file paths.
9. Real pidfd-backed task storage with descriptor/type/ref validation and task lifecycle cleanup.
10. BPF timers with proper softirq hrtimer initialization/start and callback/program references.
11. Timer cancellation and own-callback map deletion lifetime handling.
12. Legacy RLIMIT_MEMLOCK accounting for timer-bearing maps, replacement spares and failure uncharge.
13. Separate soft/hard hrtimer clock bases, expiry state and softirq dispatch.
14. Both-base high/low-resolution queries, retrigger/clock-change/migration reconciliation.
15. IRQ/BH-context-safe timer quiesce and callback-running rearm/migration handling.
16. Bounded, unaligned-safe ELF/GNU build-ID parsing.
17. Real dynamic lockdep-key registration/validation/unregistration and reader-drained retirement.
18. Restore stream-parser __SK_PASS behavior where the code is built; no claim of enabling optional stream features.
19. Genuine cached IMA inode-hash behavior adapted from v5.15.
20. Preserve/reconcile KSU/SUSFS task-header overlays and provenance checks.
21. Correct standalone BPF regression fixtures/metadata without importing donor GPU/branding/readahead/filemap changes.

## P. Build, packaging and validation changes

These are local build/integration changes, not phone runtime backports.

- Pin production full LLVM AOSP Clang r614150 and prebuilts commit3b86e40facfff1eab4065614255d573293c10373; explicitly set kernel/host LLVM tools for this old Kbuild.
- Output-only LLVM_POLLY=n adjustment for stock AOSP LLVM; retain source device settings/ThinLTO.
- Build device trees and Image.gz-dtb/dtb.img/dtbo.img/modules with provenance/log/config artifacts.
- Pinned AnyKernel3 checkout and flashable miatoll ZIP packaging with checksum/release identity.
- Manual-only workflow_dispatch; no automatic push/PR builds.
- Validate selected ARM64 LZ4 acceleration survives Kconfig dependency resolution.
- Add extracted-source regression models and negative controls for the approved subsystem ports.
- Compose immutable KSU/FinaSU/SUSFS/NoMount/BBR/F2FS provenance through detached inverse/forward replay instead of rewriting old source receipts.
- Fix BPF-task-header/SUSFS provenance preflight compatibility.
- Fix CI output-config path handling by resolving an absolute path outside replay trees.
- Use current KSU+50 config checks instead of requiring the removed SULOG selector.
- Run SUSFS2.4 exact-source models on verified pre-KSU+50 sources, not today’s modified KSU source.
- Add current NoMount23 checks and preflight logging to out/integrations.log.
- Add nine CI dispatcher regression tests and fail-closed checks for stale SULOG/missing full-UID authorization settings.

## Q. Superseded stages — historical work, not extra current integrations

Keep these identities for history/equivalence analysis, not as independent features to layer over the current pins.

| Component | Historical stage | Current selection |
|---|---|---|
| KernelSU | Initial `cbc0b49908066e9c7f778737f65a216f50b203ba` → v3.3.1-38 `feeec8e4059e3bb0ecdd1827b687b69f1cf4a2fb` | v3.3.1+50 `ae63c92098d94bdad1696c74a3ad2e96692118bf` |
| NoMount | dev/API22 `04af0552bb29c7cee1b78c3eea69d7ed98b80bf2` | dev/API23 `5e9feb6f3fce42423f56b37e344052c59ec16b66` |
| SUSFS | Kernel bridge `c931cae8ca19e4b738e3d9eda8fec4cdb7947473`, KSU bridge `fcd50c8f367c470fa8e17eb64fbb8c7ce7527061` (v2.3 stage) | Original simonpunk2.4 adaptation |
| LZ4 | Adapted1.10 donor snapshot `6c22e92e918cfb7540ddc298abe3a8cc05559672`, import starting `031b41a6e827eb813a7aedb3f4711a28c8a22ba8` | Adapted upstream1.11 block codec; repaired ARM64 integration retained |
| TCP default | BBRplus selected earlier | BBRv3 default, BBRplus still available |
| Default qdisc | fq_codel retained earlier | fq default, fq_codel still available |

## Coverage and limits

- Sections A–M contain **143 source/reference rows**. This is not 143 unique cherry-picked commits: four memlat references describe one rewrite, several BPF rows are reference/prerequisite identities, and version imports are snapshots.
- The later functional/config/build lists make native/local work explicit without fabricating donor hashes. They overlap their parent integrations and must not be added to the source-row count as extra commits.
- Retained records do not preserve a one-to-one original commit identity for every atom of the bundled/native ports. In particular the original shared timer foundation is range/reference-based. A mathematically complete original-upstream commit list cannot honestly be recovered just by filtering our 25 publication commits.
- The original SM8150 and Phoenix batch internals are intentionally not enumerated here. This is not permission to undo their dependencies blindly or reapply an unsafe isolated subset.
- Review-only UFS work, rejected integer-square-root patch, unapproved tuning/governors and equivalent/skipped proposals are not counted as new applied changes.
- Inventory/report only: no source change, sync/merge/rebase, commit, push or CI dispatch performed for this request.
