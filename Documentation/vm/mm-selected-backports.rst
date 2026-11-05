Selected MM backports
====================

Scope and provenance
--------------------
This ports six explicitly selected changes from the reviewed twenty-commit
manipvlator/los_kernel_xiaomi_sm6150 series. Review numbering is retained:

* #2: 18ad7ca0baf1b4edbe09aa5c14a8599b22ba4909, filemap readpage guards.
* #3: b4b6f5c674a5c8efebc3c9cbfdf3ae7d0e0a5935, readahead guards/cleanup.
* #4: 06295c9d8cf9d940b7e7b3246cf6137bf60c783b, cold swap-in PSI exclusion,
  corrected as described below.
* #18: c1965b9730031fa0c8ac368dfc6d9de6d86037e1, quiet_vmstat likelihood hints.
* #19: 433c12bbd29ba45412a0e606acd4c737cce1fa65, compaction retry escalation,
  with a local tracing correction. Canonical upstream is
  494330855641269c8a49f1580f0d4e2ead693245.
* #20: 864be1f4870e55172c3a587781f9ef091319917e, complete zero-seek shrinkers.
  Canonical upstream is 4b85afbdacd290c7a22c96df40a6433fdcacb509.

These are not the complete donor series. No watermark, dirty-page, vmstat
interval, compaction threshold/unevictable policy or overcommit defaults are
changed. The current 35 watermark scale, 20/10 dirty/background ratios,
5-second periodic writeback, 1-second vmstat interval, extfrag threshold 500,
compact_unevictable_allowed=1 and heuristic overcommit/ratio 50 remain.
Miatoll defconfig, BORE/PELT/CASS, BBRplus, MGLRU boot enablement and existing
procfs work are retained. Android/userspace can still override sysctls.
The pre-existing kmemleak unbounded allocation retry was not changed; that
separately reviewed issue is not repaired by this port.

Behavior and corrections
------------------------

Filemap and readahead
~~~~~~~~~~~~~~~~~~~~
Missing a_ops/readpage callbacks are rejected rather than called. Filemap
unlocks the page and uses its existing error/retry/reference paths with EIO.
Readahead retains readpages preference, releases unused page-list references
on rejection and balances block plugs when a plug has been started.

These checks are defensive, not a fix for arbitrary NULL-PC crashes or a
mapping lifetime guarantee. A dangling pointer, corrupt address_space or
concurrent invalid teardown is not made safe by checking for NULL. In
particular, the NULL-mapping guard inside read_pages cannot protect earlier
caller dereferences of mapping->host. The host model tests the filemap guard
blocks, not the complete VFS buffered-read/fault state machines.

Swap PSI
~~~~~~~~
The donor conditions only psi_memstall_enter, leaving an unconditional leave
that can consume uninitialized nesting flags for a cold page. This port
conditions BOTH calls on one PageWorkingset snapshot taken before submission.
It does not resample the page flag after IO, when the page may have been
unlocked or its classification changed. Initializing pflags alone would not
repair a mismatched enter/leave pair.

The existing nesting semantics and PSI-disabled stubs remain. Frontswap,
swap-file, block read_page, BIO allocation failure and BIO submission all
converge on the matched leave condition. This is submission-stall accounting,
not a new mechanism for accounting asynchronous IO completion time.

With MGLRU enabled, shadow/refault information classifies swap-in pages. The
existing legacy path marks new swap-in pages as workingset unconditionally;
this patch does not backport a different anonymous workingset detector, so
that path does not gain a complete hot/cold distinction.

Compaction
~~~~~~~~~~
COMPACT_SKIPPED remains eligible for retry only when the zonelist suitability
check suggests reclaim can help. Withdrawn/deferred/contended attempts instead
raise compaction priority when allowed, or stop this retry decision at the
minimum allowed priority. Non-costly and costly requests retain their different
minimum priorities. The local should_compact_lmk_retry early return remains;
this is not a bound on every allocation/reclaim loop.

The existing compact_retry trace feedback uses failed/withdrawn/progress
categories. Once COMPACT_SKIPPED moves to compaction_needs_reclaim, the donor
would classify it as progress by falling through the old trace helper. This
port keeps reclaim-needed outcomes in the withdrawn feedback category rather
than reporting nonexistent progress. CONFIG_COMPACTION=n has the new helper
stub too. No trace category numbers or compaction result enum values change.

Zero-seek shrinkers
~~~~~~~~~~~~~~~~~~
All four parts are included: do_shrink_slab handles seeks=0 without division,
procfs and kernfs superblock shrinkers use zero seeks, and the workingset
shadow-node shrinker uses zero seeks. The zero case targets half the reported
freeable objects per invocation, subject to existing batching/deferred scan
logic. Positive seeks retain the previous formula. It does not disable these
caches when memory is plentiful or guarantee that all metadata can be freed.

The existing count_shadow_nodes cap and MGLRU refault implementation are
retained. More aggressive reclaim targets excess shadow nodes rather than
unconditionally deleting all history. This trades metadata reconstruction CPU
work and potentially lost history for retaining more IO-backed cache. It is
not a guaranteed throughput, latency, battery or RAM-availability improvement.

Validation (2026-11-02)
-----------------------
Local ARM64 checks used Clang 19.1.7/LLD from Zig 0.14.1, NOT production AOSP
r614150. All outputs were outside the repository. Polly and signature/trusted
key dependencies were disabled only in generated validation configurations;
production configuration was not relaxed. ThinLTO and shadow-call-stack
remained enabled, as did the device's BORE scheduler.

* Miatoll-derived configuration: all nine changed C compilation units plus
  mm/compaction.o and kernel/sched/psi.o passed.
* Legacy LRU, PSI disabled: all nine changed C compilation units passed.
* Compaction disabled: all nine changed C compilation units passed, including
  the helper-stub/header integration.
* MGLRU with MEMCG, NUMA and the local LMK gate enabled: the eleven-object set
  passed. These extra options are validation-only, not device defaults.
* A relocatable ThinLTO link of the eleven device objects passed as AArch64
  ELF, with no unresolved new compaction-helper references. This is not a
  vmlinux link or modpost.
* Extracted-source host models passed 36 filemap guard, 792 readahead,
  160 swap PSI, 3,456 compaction retry, 11,440 shrinker and 12 vmstat cases,
  plus feedback/escalation checks and source guards. The same models passed
  with undefined-behavior sanitization.
* Four negative controls restoring conditional-enter-only PSI, misleading
  compaction tracing, the previous withdrawn retry decision or unguarded
  shrinker division each compiled and failed a C assertion as expected.
* Existing MGLRU (2,006), procfs (58,806), BBRplus (1,080) and both BORE group
  variants (104,996 math/weight cases each plus inheritance checks) passed.

Tests live in tools/testing/selftests/mm_backport. They use fake pages,
lists, callbacks, task flags, IO completion, shrinkers and statistics; they
are single-threaded and do not exercise real PSI scheduling, allocator locks,
page migration, memcg isolation, asynchronous device IO, filesystem recovery
or reclaim concurrency. No production-compiler/full kernel image build,
boot, camera/CMA stress, storage durability, latency or battery measurement,
push or CI was performed. Device validation remains necessary.
