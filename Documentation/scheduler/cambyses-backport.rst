Corrected Cambyses v0.6.0 adaptation
===================================

Scope and provenance
--------------------
This adapts only the Cambyses change requested from
``manipvlator/los_kernel_xiaomi_sm6150`` commit
``b53dda13d958ee8bf47e7ad9a9eda3bae51e7f47``. It is not a cherry-pick of its
head-first implementation, and does not import the preceding Vorpal or the
subsequent NAP governor changes.

The original Cambyses v0.6.0 patch by Masahito Suzuki/firelzrd is pinned to
``firelzrd/cambyses`` blob ``c86b4b7622b44b46240cb6ee0b268ea71210390f`` at
``patches/0001-6.12.74-cambyses-v0.6.0.patch``. Its mail-patch commit identifier
is ``19331ed9f4df9d572363e587d5ac0cd2b4c942d3`` (Linux 6.12.74).
``cambyses-backport.json`` records URLs, hashes and local validation results.
``cambyses-adaptation.diff`` records only this adaptation against the already
modified pre-Cambyses tree; it does not reproduce earlier BORE/CASS changes.

Production changes are restricted to ``include/linux/list.h`` and
``kernel/sched/{fair.c,features.h}``. There is no governor, defconfig, Kconfig,
boot banner or initcall change. Existing BORE, CASS, PELT and WALT policy stays
in place, with no WALT activation in the production configuration.

Corrections relative to the donor
---------------------------------

* Preserve this tree's tail-first scan and legacy reject-to-head ordering
  when block rotation is disabled. The donor scans head-first.
* Implement real O(1) cyclic rotation by relocating the list sentinel with
  ``list_move_tail(head, list)``; moving just one task is not block rotation.
  The list-head argument itself is accepted as a no-op. Membership and locking
  remain the caller's responsibility.
* When enabled, scan towards the head without modifying the list on each
  reject. At a scan boundary, move the examined rejected block to the front,
  making the first unexamined task the tail. Flush preceding rejects before
  each successful detach as well, not just at function exit.
* Preserve the existing ``rq_clock(src_rq) - start_t > 5000000`` guard and
  loop/quantum checks. Do not mark a task examined until these checks pass.
  Do not run a fallback migration after that clock guard fires. This is the
  existing rq-clock check, NOT a newly established five-millisecond wall-clock
  latency guarantee: rq_clock need not advance throughout the locked scan.
* Account for WALT's real ``detach_task()`` path: ``double_lock_balance()``
  can release the source lock. A live scan cursor/concession is discarded
  before ordinary detachment, and the cursor is refreshed afterwards. Exit
  rotation precedes fallback detachment, with no subsequent use of its old
  cursor. No saved candidate crosses a detach or a redo/retry boundary.
* Compare the whole task load with the positive remaining imbalance for
  strict budgeting. If no task has moved in this balance operation, retain
  the cheapest otherwise-eligible overshoot found in the scan and admit it
  as a progress fallback. ``LBF_MOVED`` (unused local bit 0x40) is sticky over
  ``more_balance`` retries, preventing another fallback after prior progress.
  Fallback subtraction is capped at LONG_MAX to avoid wrapping a huge
  unsigned candidate cost into a positive remaining budget.
* Preserve the local oversized-task exception when the source has at most
  two runnable tasks and IGNORE_BIG_TASKS is clear. Strict budgeting does
  not override this exception. Disabling strict budgeting restores the old
  ``load / 2`` comparison, not Linux 6.12's failure-count relaxation.
* Leave ``can_migrate_task()`` and its affinity/running/cache-hot/throttling
  checks untouched, along with LB_MIN, the minimum load of one, vendor
  IGNORE_BIG_TASKS/IGNORE_PREFERRED_CLUSTER_TASKS relaxed redo, statistics,
  source-runqueue guard and PREEMPT NEWIDLE early stop.

The implementation uses stack-local state and list operations, with no new
allocation or extra runqueue locking. Batching reduces per-reject list writes;
it does not promise a single rotation for an entire function invocation that
also migrates tasks or performs a vendor redo. Neither the fallback nor the
scan rotation is a proof of global starvation freedom or improved performance.

Feature defaults and rollback
-----------------------------
``LB_ROTATE_BLOCK`` and ``LB_STRICT_BUDGET`` default to true, as requested by
the adapted Cambyses change, and are sampled once per ``detach_tasks()`` call.
There is no new Kconfig option.

On a separately configured debug kernel exposing scheduler feature controls,
these can be disabled independently through ``sched/features`` under debugfs.
Disabling both restores the legacy decisions/list ordering apart from the
unused internal progress flag. The preserved miatoll defconfig does NOT enable
CONFIG_SCHED_DEBUG, so do not assume a runtime toggle exists on the production
build; its new defaults compile as constants. Enabling debug support would be
a separate configuration decision, not part of this adaptation.

Local validation (2026-11-05)
----------------------------

* Actual extracted code and real list.h passed native ASan plus trapping
  UBSan for all four PREEMPT/WALT combinations. Each variant passed deterministic
  cases, 3,000 exact legacy feature-off comparisons and 12,000 mixed-feature
  cases: 12,000 differential comparisons and 48,000 mixed cases in total.
  The runner verifies UBSan with an overflow probe and checks ASan symbols.
* All 12 negative controls were rejected, including an ASan heap-use-after-free
  from retaining a cursor across simulated WALT lock-drop churn. This models
  a legal intervening dequeue/free; it is not a real parallel kernel test.
* Real ``kernel/sched/fair.o`` and ``kernel/sched/core.o`` compiled and were
  partially linked for five ARM64 configurations: base PELT/PREEMPT; WALT;
  WALT plus DEBUG_KERNEL/SCHED_DEBUG/PROVE_LOCKING/DEBUG_LIST; PELT plus
  ThinLTO/shadow-call-stack; and PELT/PREEMPT_NONE. DEBUG_LIST was enabled in
  all five. Debug dependencies were checked in the resolved configuration,
  not merely requested before olddefconfig. LLD's ThinLTO backend produced
  an AArch64 ELF relocatable with executable sections, not just bitcode.
* Builds used local Zig 0.14.1 Clang 19/LLD, NOT the production pinned AOSP
  r614150 compiler. Test-only out-of-tree configurations disabled Polly and
  certificate/signature host prerequisites; the production defconfig was
  not edited. Base test builds also disabled LTO/SCS, then the ThinLTO variant
  re-enabled both. No scheduler compiler warnings/errors were recorded.
* The pre-Cambyses SHA-256 inventory was checked for preservation of all
  72,943 existing files. Only the three production files above changed;
  additions are this report/provenance/diff and four selftest source/doc files.
  The miatoll defconfig SHA-256 remains
  ``7d049399dbd01e9f517db96c152a86148d1fdf1a307be95745ba2fa29a456a75``.

See ``tools/testing/selftests/cambyses/README.md`` for reproducible host checks.
No full kernel image, boot test, real lockdep run, device scheduler stress,
power/thermal or performance benchmark was performed. No push or CI run was
performed for this work. Production-toolchain and device validation remain
outstanding; prior kernel boot results do not establish safety of this change.
