Scheduler correctness fixes: selective backport
==============================================

Scope
-----

Apply only items 2, 3, 6 and corrected item 4 from the reviewed nine-commit
Azyr scheduler/SMP batch. Item 1 is already implemented. Item 5 is rejected:
local iteration is already ascending and its patch drops CPU-isolation
filtering. Items 7, 8 and 9 are deferred; no asym-packing or active-balance
interval changes are included.

Donor repository: https://github.com/AzyrRuthless/kernel_xiaomi_sm6250

* 298f4559960e4e14c6ff43638a1da981cf95dee8: compare minimum/maximum group
  per-CPU capacities directly. Applied unchanged. Utilization margins are
  retained everywhere else, including their existing values.
* 56c8b07bc33bb8bf83d42834be446e831f47b29b: mark task-CPU reads/stores and
  the migration-state accesses used by move_queued_task()/task_rq_lock().
  Applied unchanged, including the address-dependency comment. Existing
  smp_wmb(), runqueue locks, WALT branches and wake_cpu assignment remain.
  This is not a blanket conversion of all on_rq accesses in the kernel.
* 75c9d3457a8aedfe68ef0163b9b8d10c51248ed8: skip sources with zero runnable
  hierarchical CFS tasks before the misfit and weighted-load cases in
  find_busiest_queue(). Applied unchanged.
* e250ed8c4d54aa77f461347574cf2994f3bab0c0: corrected CPU-offline IRQ
  ordering, as described below. Not an exact donor cherry-pick.

Corrected offline idle entry
----------------------------

Move local_irq_disable() before cpu_is_offline(), use the direct
tick_nohz_idle_stop_tick() call in the offline branch, and remove the later
redundant disable before arch_cpu_idle_enter(). The NO_HZ_COMMON protected
wrapper disables and then unconditionally enables IRQs; it does not save and
restore incoming IRQ state. Keeping that wrapper would reopen the interrupt
window before cpuhp_report_idle_dead()/RCU offline reporting even with the
new early IRQ disable. The direct stop-tick call preserves IRQ-disabled state.

The protected helper itself is not removed or changed, so unrelated callers
retain their behavior. Idle polling, broadcast handling, cpuidle, architecture
exit, reschedule and pending-call processing are unchanged. Both direct and
protected helpers already have !NO_HZ_COMMON stubs.

Preservation
------------

The incremental production patch changes only five files: include/linux/sched.h
and kernel/sched/{core.c,sched.h,fair.c,idle.c}. It is relative to the dirty
pre-application tree, not a replacement for earlier backports. Exact donor
replay is verified for the three unmodified patches; the idle delta is checked
against the explicitly corrected sequence. Full-tree hashing checks all
73,005 pre-existing files/symlinks, allowing only these five source edits.

Cambyses tail-first scan, load budget, 5ms guard and migration filters are
unchanged. BORE/CASS, nohz CPU-isolation filtering, vendor active-balance
conditions, previously integrated GPU/DEADLINE changes, miatoll_defconfig,
freezer timeout and all prior unrelated work are preserved.

Validation
----------

The standalone runner in tools/testing/selftests/sched_correctness/ extracts
current source and uses mocked scheduler/IRQ context. Host GCC ASan+UBSan and
UBSan-only runs pass all six configurations, each exercising 4,198,401 capacity
pairs plus 100 edges, 50,000 randomized queue selections, task access/order
checks and 200 idle entries. All ten negative controls fail as intended,
including restoration of the protected tick call.

Regression checks pass:

* BORE: both group modes, 104,996 math/weight cases per mode plus source guards.
* Cambyses: all four PREEMPT/WALT combinations, 3,000 exact legacy comparisons
  and 12,000 mixed-feature cases per combination, plus twelve negative controls.
  The current environment lacks Clang. A temporary compiler adapter outside
  the repository translated only Clang's -fsanitize-trap=undefined spelling
  to GCC's -fsanitize-undefined-trap-on-error. The UBSan trap probe passed;
  no existing Cambyses source or test was edited.
* GPU/DEADLINE: 65,536 CPU-mask pairs, affinity/admission/IRQ/RCU checks, KGSL
  paths, non-SMP helper and seven negative controls.

The production delta passes checkpatch and git diff --check. See the companion
JSON for donor identities and per-file pre/post SHA-256 values; the companion
.diff contains only this batch's production changes.

Limitations: no full kernel or ARM64 production-object build, LKMM/concurrency
proof, device boot, hotplug/RCU stress or performance result is claimed. Host
access instrumentation checks primitive use/order, not actual ARM memory
ordering. No push, CI, new configuration defaults or deferred balancing
changes are part of this application.
