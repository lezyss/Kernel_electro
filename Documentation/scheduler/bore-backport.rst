BORE 5.1.0 backport notes
=========================

Scope and provenance
--------------------
This is an adapted port of the following manipvlator/los_kernel_xiaomi_sm6150
series, in the requested order:

* a2c7aff131ae3ca2471f0134464e70a982176fff: BORE 5.1.0, attributed to Masahito
  Suzuki/firelzrd's legacy Linux 4.19 BORE patches.
* c684d01fc6f95413c4ce46fadcaf2c6f63123c18: constant scheduler granularity.
* 222cfabd72a3ca2f69c267decd3acee8278f268d: short-burst smoothing enabled.
* 3001d4566a0021858005a91d51a6193c1b40ce30: final granularity/bandwidth tuning.
* e2c4678c8b532f58a22010e756e04d6da4ecf283: always-inline task reweighting.
* 12cc0428dcbbe5085132cb02d30db92445935920: WALT-only migration guards.

The implementation remains a CFS burst-based weighting modification, not a
replacement of CFS with EEVDF. CASS CPU placement, PELT (including the existing
half-life selection), schedtune and energy-aware configuration are retained.
MGLRU context-switch/fork changes and earlier approved work are preserved.
This is not a claim of parity with newer BORE versions or of measured touch,
jitter, battery, throughput or latency improvement on miatoll.

Configuration and defaults
--------------------------
CONFIG_SCHED_BORE=y is explicitly enabled in miatoll_defconfig. The generic
Kconfig default is n, so other device configurations are not silently opted
in. The existing miatoll CONFIG_FAIR_GROUP_SCHED=n and CONFIG_SCHED_WALT=n
are unchanged; CONFIG_SCHED_CASS=y remains enabled.

The requested series' final BORE defaults are:

* latency: 24 ms;
* minimum granularity: 5 ms;
* wakeup granularity: 4 ms;
* tunable scaling: NONE (constant, not CPU-count scaling);
* long and short burst smoothing: 1;
* fork atavistic depth: 2;
* penalty offset: 22; scale: 1280; cache lifetime: 60,000,000 ns (60 ms).

The 4-ms CFS bandwidth slice applies only when CONFIG_CFS_BANDWIDTH is enabled;
that option remains off in the device configuration. These are defaults,
not a ban on Android/userspace adjusting scheduler sysctls. The donor's
kernel.sched_bore sysctl is pinned to 1, not a live disable switch. Compare
against a rebuild with CONFIG_SCHED_BORE=n instead. The disabled path retains
this tree's pre-port 5-ms/0.5-ms/1-ms normalized latency/minimum/wakeup defaults,
logarithmic scaling, 5-ms bandwidth slice and legacy SCHED_BATCH yield path.

Required backport corrections
-----------------------------

* Task/entity helpers retain the !FAIR_GROUP_SCHED case, without accessing a
  nonexistent se->my_q member. Burst scoring skips group entities.
* Reuse and relocate the existing reweight_entity/task implementation rather
  than duplicating reweight_task as donor commit #5 would do here. Task
  reweighting is private always-inline code available without fair groups.
* Settle this tree's already-weighted PELT history using the old load weight
  before changing it. Preserve the existing runqueue dequeue/re-enqueue
  accounting and group-share implementation; do not import newer PELT
  rescaling formulas into this older representation.
* set_load_weight includes the burst score when nice/policy is changed.
  SCHED_IDLE keeps WEIGHT_IDLEPRIO/WMULT_IDLEPRIO instead of being promoted to
  a normal nice weight by BORE. Burst time saturates instead of wrapping.
* Fork state is initialized coherently, including weight/inverse weight and
  invalid child caches. The inheritance depth declaration is unsigned int in
  both compilation units, matching its sysctl storage, and is sampled once.
* Inheritance runs after real_parent assignment but before task publication,
  while copy_process holds tasklist_lock for write. This serializes cache
  updates and tree traversal, avoiding writes under the donor's shared read
  lock and late updates to an already published child. No rq lock is taken
  from this path; initial load/PELT state is seeded while the child is private.
* Tree traversal has a shared 1,024-step budget, including ancestor and
  single-child chains. Child counting stops at two because only the single-
  child distinction is needed. Depth is capped at three; count/weighted-sum
  intermediates are u64. Budget-truncated results are not memoized. These
  bounds deliberately make inheritance approximate on very large trees.
* Runtime penalty observations use READ_ONCE/WRITE_ONCE. A zero cache stamp is
  invalid even during the first cache-lifetime interval after boot.
* Use ENQUEUE_WAKEUP for wakeup burst restart, leaving migration/restore
  enqueues alone. Yield restarts bursts even for a single runnable task.
* Guard the migration call with CONFIG_SCHED_WALT and remove the unused
  no-WALT stub. Redundant donor guards already nested inside WALT-only code
  are omitted; the actual WALT implementation is retained. No migration or
  placement algorithm is replaced by this cleanup.

New per-entity fields alter internal task/group layouts and add memory
footprint. A consistent full kernel/module rebuild is required; this is not
a loadable replacement for the running scheduler. Inheritance now adds bounded
work to an IRQ-off tasklist write-locked region, which still needs fork-stress
and latency testing on a real kernel.

Validation (2026-11-01)
-----------------------
Local checks used Clang 19.1.7/LLD from Zig 0.14.1, NOT production AOSP r614150.
Generated configs/outputs were outside the source tree. Polly and local
signature/trusted-key dependencies were disabled only in validation outputs;
production defconfig settings were not relaxed.

* Miatoll-derived ThinLTO/SCS: core, fair, RT, deadline, idle, wait, schedtune,
  schedutil, fork, sysctl, init_task and vmscan objects passed (12 objects).
* BORE on/off crossed with fair groups on/off passed core/fair/fork/sysctl
  checks. Debug builds in the group-on and legacy cases enabled DEBUG_KERNEL
  and SCHED_DEBUG; the group-on cases also enabled CFS_BANDWIDTH. debug.o
  passed in those validation configurations.
* WALT+BORE core/fair/fork/sysctl objects passed as a compatibility check,
  followed by restoration and rebuilding of the device's PELT configuration.
* A relocatable LTO link of core/fair/fork passed; no BORE helper references
  were left unresolved. This is not a full vmlinux link or modpost.
* Production-extracted host models passed 104,996 math/weight cases for each
  group-on/off model, plus direct/topological cache, expiry, cached-subtree,
  long-chain/wide-tree budget and inheritance-depth snapshot checks.
  Negative controls restoring the donor's SCHED_IDLE reweighting or ignoring
  burst scores on nice changes both failed C assertions.
* Existing BBRplus, procfs and MGLRU host regressions passed again.
* Scoped patch whitespace checks passed.

The host model uses fake tasks, lists, runqueues, locking and PELT callbacks;
it is single-threaded and does not run the modified kernel. These checks do
not prove lock ordering under all runtime paths, scheduler fairness, CPU
hotplug/migration safety, cpufreq interactions or fork/exit concurrency.
There has been no full production-compiler image build, boot, suspend/game/UI
or battery test, push or CI run for this scheduler port.
