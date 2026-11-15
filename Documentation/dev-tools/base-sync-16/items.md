# Item-by-item first-pass audit against pinned updated16

Foundation: `766a32ab1c8b889ac049ccd367e82786e5953bc0`. Previous Electro: `402566a8597ae7f0ecf3f87054b77aa7c18acdf0`.

Read the method/limits in [README](README.md). **Candidate/unresolved does not mean applied.** BBRplus is excluded.

| Inventory ID | Reference | Change | Result |
|---|---|---|---|
| E001 | `149e6887d341` | A01-006 — inline ARM64 rwlocks under PREEMPT; remove 16 !PREEMPT restrictions | forward-candidate |
| E002 | `d73dae72f581` | A01-027 — SCM-call accounting / avoid unsafe reads while SCM is busy | forward-candidate |
| E003 | `12798fd3c654` | A01-028 — keep SCM accounting separate from fixed-register SMC assembly | semantic-review-required |
| E004 | `143f07a8f3e7` | A01-029 — native asynchronous per-CPU memlat sampling with completion/lifetime handling | semantic-review-required |
| E005 | `d7fda10ad1db` | A01-030 — use native four-argument perf_event_read_local API | semantic-review-required |
| E006 | `28bc6f028c8e` | A01-036 — Corrected native integer-only delay in ipa3_disable_wdi_pipe producer path: minimum 10000 us preserved, maximum 12000 us; the other equal-bound sleep and all other IPA code unchanged. | forward-candidate |
| E007 | `b0229e526d85` | A01-041 — Exact donor two unlikely() annotations in cpufreq_stats_record_transition; no condition/statistics/locking changes. | forward-candidate |
| E008 | `dd7a5c396220` | A01-046 — sched: Allow newidle balancing to bail out of load_balance | forward-candidate |
| E009 | `542e7b0ac23a` | A01-047 — cpufreq: schedutil: Inline `sugov_policy_free()` | forward-candidate |
| E010 | `403836055eec` | A01-048 — sched: Optimize __calc_delta() | forward-candidate |
| E011 | `c0ff2a937bff` | A01-052 — cpuidle: lpm_levels: Don't print parent clocks during suspend | forward-candidate |
| E012 | `69cf714073eb` | A01-056 — dm-verity: Enable WQ_HIGHPRI on verify_wq | forward-candidate |
| E013 | `94a730ad0791` | A01-057 — dm-verity: Stop using WQ_UNBOUND for verify_wq | semantic-review-required |
| E014 | `324bac57ebad` | A01-058 — adreno: Stop reading registers just for debugging | forward-candidate |
| E015 | `3ea82acbb35f` | A01-078 — drivers: base/arch_topology: avoid a stuck risk when cpufreq policy free | forward-candidate |
| E016 | `3e87d0295c39` | A01-079 — drivers: iommu: silence logging | forward-candidate |
| E017 | `202b3995f9ad` | A01-092 — BACKPORT: block: use ktime_get_ns() instead of sched_clock() for cfq | forward-candidate |
| E018 | `79431f18b1e1` | A01-093 — cfq: Annotate fall-through in a switch statement | forward-candidate |
| E019 | `522ab2ee25fc` | A01-094 — cfq: clear queue pointers from cfqg after unpinning them in cfq_pd_offline | forward-candidate |
| E020 | `6bbaff1957fa` | A01-098 — drivers: power/irqchip: Add wakeup irq loggers | forward-candidate |
| E021 | `298f4559960e` | Compare scheduler group min/max capacities directly | forward-candidate |
| E022 | `56c8b07bc33b` | Mark task-CPU and migration-state accesses | forward-candidate |
| E023 | `75c9d3457a8a` | Skip busiest queues with no runnable hierarchical CFS tasks | forward-candidate |
| E024 | `e250ed8c4d54` | Correct CPU-offline idle IRQ ordering; direct stop-tick call | forward-candidate |
| E025 | `71a6c1d01b6f` | BACKPORT: msm: kgsl: Fix syncsource spinlock recursion | forward-candidate |
| E026 | `bc7328a77b6b` | UPSTREAM: sched/deadline: Optimize dl_bw_cpus() | forward-candidate |
| E027 | `ad1345b413fc` | sched, cpuset: Fix dl_cpu_busy() panic due to empty cs->cpus_allowed | forward-candidate |
| E028 | `a2c7aff131ae` | BORE 5.1.0, attributed to Masahito Suzuki/firelzrd's legacy Linux 4.19 BORE patches. | semantic-review-required |
| E029 | `c684d01fc6f9` | constant scheduler granularity. | semantic-review-required |
| E030 | `222cfabd72a3` | short-burst smoothing enabled. | semantic-review-required |
| E031 | `3001d4566a00` | final granularity/bandwidth tuning. | semantic-review-required |
| E032 | `e2c4678c8b53` | always-inline task reweighting. | semantic-review-required |
| E033 | `12cc0428dcbb` | WALT-only migration guards. | forward-candidate |
| E034 | `b53dda13d958` | Cambyses v0.6.0: block rotation, scan-budget handling and safe migration progress fallback | semantic-review-required |
| E035 | `27048e83e24d` | Reapply mm: introduce __lru_cache_add_active_or_unevictable | forward-candidate |
| E036 | `150b3797156a` | UPSTREAM: mm: replace list_move_tail() with add_page_to_lru_list_tail() | forward-candidate |
| E037 | `80429a3f5e58` | UPSTREAM: arm64: cpufeature: introduce helper cpu_has_hw_af() | forward-candidate |
| E038 | `f36d767468af` | UPSTREAM: mm/vmscan.c: use update_lru_size() in update_lru_sizes() | forward-candidate |
| E039 | `53489d60f44c` | BACKPORT: mm/swapcache: support to handle the shadow entries | forward-candidate |
| E040 | `f51ecb574eec` | BACKPORT: mm: remove superfluous __ClearPageActive() | forward-candidate |
| E041 | `bf8641c30a78` | BACKPORT: mm: use self-explanatory macros rather than "2" | forward-candidate |
| E042 | `ba8564c12027` | BACKPORT: mm/vmscan.c: use add_page_to_lru_list() | forward-candidate |
| E043 | `f97327ca66e9` | BACKPORT: include/linux/mm_inline.h: shuffle lru list addition and deletion functions | forward-candidate |
| E044 | `2615fc64834f` | BACKPORT: mm: don't pass "enum lru_list" to lru list addition functions | semantic-review-required |
| E045 | `cf8e44a06b89` | UPSTREAM: mm/swap.c: don't pass "enum lru_list" to trace_mm_lru_insertion() | semantic-review-required |
| E046 | `22902855a338` | BACKPORT: mm/swap.c: don't pass "enum lru_list" to del_page_from_lru_list() | semantic-review-required |
| E047 | `f4aaf1dfa4c4` | BACKPORT: mm: add __clear_page_lru_flags() to replace page_off_lru() | semantic-review-required |
| E048 | `c216026c8a0b` | UPSTREAM: mm: VM_BUG_ON lru page flags | semantic-review-required |
| E049 | `38f9bf9fcbbf` | BACKPORT: include/linux/mm_inline.h: fold page_lru_base_type() into its sole caller | semantic-review-required |
| E050 | `bc21327232c6` | FROMLIST: mm: x86, arm64: add arch_has_hw_pte_young() | forward-candidate |
| E051 | `b0b10a2cb89f` | FROMLIST: mm: x86: add CONFIG_ARCH_HAS_NONLEAF_PMD_YOUNG | forward-candidate |
| E052 | `b329a95b729e` | FROMLIST: mm: multi-gen LRU: groundwork | semantic-review-required |
| E053 | `d04b362714e9` | FROMLIST: mm: multi-gen LRU: minimal implementation | semantic-review-required |
| E054 | `75713ae4030e` | FROMLIST: mm: multi-gen LRU: exploit locality in rmap | semantic-review-required |
| E055 | `cc109a443214` | FROMLIST: mm: multi-gen LRU: support page table walks | semantic-review-required |
| E056 | `be671e5364be` | FROMLIST: mm: multi-gen LRU: optimize multiple memcgs | semantic-review-required |
| E057 | `3c8d5dcc8bf0` | FROMLIST: mm: multi-gen LRU: kill switch | semantic-review-required |
| E058 | `67e4305510a1` | FROMLIST: mm: multi-gen LRU: thrashing prevention | semantic-review-required |
| E059 | `cce036fef9e6` | FROMLIST: mm: multi-gen LRU: debugfs interface | semantic-review-required |
| E060 | `f889fcd02d02` | mglru: fixes | semantic-review-required |
| E061 | `b40b16274a26` | mm/mglru: don't sync disk for each aging cycle | semantic-review-required |
| E062 | `c2d7c83deb22` | mm: vmscan: Fix error when CONFIG_DEBUG_FS is disabled | semantic-review-required |
| E063 | `fa3bb3287d2a` | mm: vmscan: Don't create debugfs when CONFIG_DEBUG_FS is disabled | semantic-review-required |
| E064 | `3728f6da063f` | mm: multi-gen LRU: fix crash during cgroup migration | semantic-review-required |
| E065 | `18ad7ca0baf1` | Filemap: guard missing readpage callbacks | forward-candidate |
| E066 | `b4b6f5c674a5` | Readahead: guard absent callbacks and preserve page/plug cleanup | forward-candidate |
| E067 | `06295c9d8cf9` | Cold swap-in PSI exclusion; match both enter and leave using one workingset snapshot | forward-candidate |
| E068 | `c1965b973003` | quiet_vmstat likelihood hints | forward-candidate |
| E069 | `433c12bbd29b` | Compaction retry escalation; correct native trace feedback | forward-candidate |
| E070 | `864be1f4870e` | Complete zero-seek shrinker handling and users | forward-candidate |
| E071 | `3ab436a744c5` | 1. SHMLBA alignment | forward-candidate |
| E072 | `686db5c5c84a` | 2. Pass VM_USERMAP directly | semantic-review-required |
| E073 | `f75b713d9a23` | 3. Lazy-purge threshold | forward-candidate |
| E074 | `46a3b96a5a06` | 4. atomic_long lazy counter | semantic-review-required |
| E075 | `255e313d2ad1` | 5. Augmented free-block allocator | forward-candidate |
| E076 | `a3ac4fd0986b` | 6. Remove unused node argument | semantic-review-required |
| E077 | `5021f6a5d420` | 7. Split-node preloading | semantic-review-required |
| E078 | `7ef1c5c16b22` | 8. Avoid redundant unlink | semantic-review-required |
| E079 | `902781dbff5c` | 9. Warn on invalid unlink | semantic-review-required |
| E080 | `5d1313d1b8bd` | 10. Per-CPU search correction | semantic-review-required |
| E081 | `64fba55ad565` | 11. Detach pending areas from busy tree | semantic-review-required |
| E082 | `626616a53457` | 12. State-dependent metadata union | semantic-review-required |
| E083 | `69058cd6516c` | 13. Speculative preload without pinning | semantic-review-required |
| E084 | `2e4f46245786` | 14. Respect caller GFP mask | semantic-review-required |
| E085 | `aa7f703ce3ef` | 15. Separate busy/free locks | semantic-review-required |
| E086 | `0a7dd4e901b8` | 16. Fix unlock order in s_stop(); retain BOTH unlocks | semantic-review-required |
| E087 | `06330f5b58f9` | revert forced little-cluster migration during maps reads. | forward-candidate |
| E088 | `ce389dc0f59a` | revert the custom ARM64 formatter and d_path_outlen() path plumbing. | forward-candidate |
| E089 | `b810878560ba` | width-aware decimal printing. | semantic-review-required |
| E090 | `686a9a059677` | hex sequence printing. | semantic-review-required |
| E091 | `ad17b568d5b7` | shared PID/TID map handlers. | semantic-review-required |
| E092 | `3638aadffd8b` | gather smaps statistics. | semantic-review-required |
| E093 | `90208857deb0` | common statistics printer. | semantic-review-required |
| E094 | `2321653ec0a7` | single-value smaps_rollup. | semantic-review-required |
| E095 | `869fd85e1014` | no-pkey vma_pkey() fallback. | forward-candidate |
| E096 | `76f0d41fa56f` | no-pkey arch_pkeys_enabled(). | forward-candidate |
| E097 | `8ff3cde162fd` | include linux/pkeys.h. | forward-candidate |
| E098 | `d10c142d7e21` | Pss_Anon/File/Shmem rollup. | semantic-review-required |
| E099 | `0253fe413143` | snapshot map_files addresses under mmap_sem and format names after releasing it. | forward-candidate |
| E100 | `45c506bd3b8d` | F2FS compression reserve/release: hold checkpoint operation read lock across dnode operations | forward-candidate |
| E101 | `d287de5bde53` | F2FS GC: reject inline-data/external-block inconsistency; log before dropping inode reference | semantic-review-required |
| E102 | `00ad9f944286` | F2FS move-range and pin-file ioctls: reject atomic files with correct lock/cleanup ordering | forward-candidate |
| E103 | `655ae9dbb75a` | Epoll: take a positive-count temporary file reference around poll; preserve native fallback | forward-candidate |
| E104 | `7209a1acc23b` | Writeback: protect freeing-inode lists with corrected late dirty-state handling | semantic-review-required |
| E105 | `3fcb7aa3e71b` | F2FS sysfs: size-aware1/2/4/8-byte access for42 local RW/stat attributes | semantic-review-required |
| E106 | `5cdb422c8391` | f2fs: fix to avoid use-after-free for cached IPU bio — adapted IPU missing-selector fix; caller and helper guarded | forward-candidate |
| E107 | `edf7e9040fc5` | f2fs: fix UAF issue in f2fs_merge_page_bio() — adapted encrypted-page lifetime fix to original struct page; accounting also moved before publication | semantic-review-required |
| E108 | `6d1f622b9c06` | f2fs: fix submit accounting for IPU writeback — successful IPU submission accounting | semantic-review-required |
| E109 | `5911d2d1d1a3` | f2fs: introduce gc_merge mount option — GC merge intent; adapted to local four-argument GC and embedded request lifetime | semantic-review-required |
| E110 | `8b4468ec023d` | f2fs: fix potential deadlock in gc_merge path of f2fs_balance_fs() — drain cached OPU and all IPU writes before GC waits; also used before checkpoint queueing | semantic-review-required |
| E111 | `1adaa71ea9bf` | f2fs: don't bother wait_ms by foreground gc — foreground GC must not overwrite background sleep interval | semantic-review-required |
| E112 | `261eeb9c1585` | f2fs: introduce checkpoint_merge mount option — checkpoint merge intent; adapted request lifetime, publication, ownership, errors and stop | semantic-review-required |
| E113 | `7b02b2201893` | f2fs: fix to destroy sbi->post_read_wq in error path of f2fs_fill_super() — checkpoint startup failure must retain post_read_wq cleanup | semantic-review-required |
| E114 | `f6f8f34480c7` | f2fs: quota: fix quota flush failure during filesystem freeze — reviewed freeze/quota cross-task issue; local worker trylock/ownership and caller fallback instead of holder-tracking transplant | semantic-review-required |
| E115 | `c72c7c0ec132` | Upgrade block LZ4/LZ4HC to v1.11.0 (PR2037); retain kernel workspaces, exports and preboot support | different-codec-review |
| E116 | `730abe07b866` | zram: do not waste zram_table_entry flags bits | forward-candidate |
| E117 | `d8dfb8482b99` | xxhash: create arch-dependent32/64-bit xxhash() | forward-candidate |
| E118 | `40213eb493f2` | BBRplus port; wire TSO callback/fallback, GPL export and private helpers | excluded-bbrplus |
| E119 | `90210de4b779` | Google BBRv3 loss-based implementation, adapted to native 4.14 TCP and later EDT forecast | missing-import |
| E120 | `a627517bdfe0` | net-tcp_bbr: v2: shrink delivered_mstamp, first_tx_mstamp to u32 to free up 8 bytes | semantic-review-required |
| E121 | `0e6b4413cb4a` | net-tcp_bbr: v2: snapshot packets in flight at transmit time and pass in rate_sample | semantic-review-required |
| E122 | `3679f3b8da5a` | net-tcp_bbr: v2: count packets lost over TCP rate sampling interval | semantic-review-required |
| E123 | `500bcfec22c4` | net-tcp_bbr: v2: export FLAG_ECE in rate_sample.is_ece | semantic-review-required |
| E124 | `f2078939d4a8` | net-tcp_bbr: v2: introduce ca_ops->skb_marked_lost() CC module callback API | semantic-review-required |
| E125 | `88e09e2b7c84` | net-tcp_bbr: v2: adjust skb tx.in_flight upon merge in tcp_shifted_skb() | forward-candidate |
| E126 | `5093de531d14` | net-tcp_bbr: v2: adjust skb tx.in_flight upon split in tcp_fragment() | semantic-review-required |
| E127 | `a631934cbcd8` | net-tcp_bbr: v2: record app-limited status of TLP-repaired flight | semantic-review-required |
| E128 | `3ee83ca004fa` | net-tcp_bbr: v2: inform CC module of losses repaired by TLP probe | forward-candidate |
| E129 | `703f20a1052d` | net-tcp_bbr: v2: introduce is_acking_tlp_retrans_seq into rate_sample | semantic-review-required |
| E130 | `137a508c9508` | net-tcp_bbr: broaden app-limited rate sample detection | semantic-review-required |
| E131 | `ab408b6dc744` | TCP/fq EDT model; adapted, not wholesale patch applied | semantic-review-required |
| E132 | `08e14fe429a0` | EDT packets must still honor fq maxrate | semantic-review-required |
| E133 | `ae63c92098d9` | backslashxx KernelSU v3.3.1+50, numeric32730; built-in native/compat integration | missing-import |
| E134 | `2d5786b9129a` | FinaSU manager compatibility: package/certificate-pinned authorization and retained single-manager UID policy | missing-import |
| E135 | `5e9feb6f3fce` | NoMount dev v2.3/API23; exact C/header, hardened built-in build files | missing-import |
| E136 | `45a057536ddb` | Original simonpunk SUSFS2.4.0 adapted from GKI5.10 to native 4.14/backslashxx | missing-import |
| E137 | `d22fb4cf8eed` | Initial ARM64 JMP32 correction; later integrated atomic fixes extend it | forward-candidate |
| E138 | `2a58cdc0636e` | Consolidated Android-focused5.15-era BPF core reference, selectively integrated | unresolved-partial-diff |
| E139 | `63e2ed365975` | Shared hrtimer prerequisite: mode-aware start tracepoint | semantic-review-required |
| E140 | `42f42da41b54` | Shared hrtimer prerequisite: real soft/hard clock bases and is_soft initialization | semantic-review-required |
| E141 | `5da70160462e` | Shared softirq hrtimer foundation endpoint; adapted, not a verbatim full-series replay | semantic-review-required |
| E142 | `108c14858b9e` | Reference for real dynamic lockdep-key registration/lifetime integration | semantic-review-required |
| E143 | `636633e1d9b1` | Reference for stream-parser __SK_PASS restoration | unresolved-metadata |

## Native/local feature probes

These complement the indexed source references; marker presence alone is not semantic proof.

| Scope | File | Probe present | Whole file identical to previous Electro |
|---|---|---|---|
| ext4_dot_last | `fs/ext4/dir.c` | True | True |
| ext4_early_ibody_check | `fs/ext4/inode.c` | False | False |
| bore | `include/linux/sched.h` | False | False |
| mglru | `mm/Kconfig` | False | False |
| memlat_async | `drivers/devfreq/arm-memlat-mon.c` | False | False |
| f2fs_gc_merge | `fs/f2fs/super.c` | False | False |
| f2fs_checkpoint_merge | `fs/f2fs/super.c` | False | False |
| f2fs_sysfs_width | `fs/f2fs/sysfs.c` | False | False |
| bpf_task_storage | `kernel/bpf/bpf_task_storage.c` | False | False |
| native_tcp_edt | `include/linux/tcp.h` | True | False |
| arm64_lz4_accel | `lib/lz4/lz4armv8/lz4armv8.S` | False | False |
| ci_build_script | `scripts/ci/build-kernel.sh` | False | False |
| ci_package_script | `scripts/ci/package-anykernel.sh` | False | False |

Other native/config/build scopes in the historical inventory remain to be semantically qualified/restored. Source markers and patch direction are not substitutes for their old corrected-native tests.
