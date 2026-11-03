Corrected vmalloc allocator backport
===================================

Scope and provenance
--------------------

This ports the approved first sixteen changes from the reviewed vmalloc
series to this 4.14 tree. Donor commits are in
https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/ :

#. 3ab436a744c58e538f13f7c76d042e508b0cdc1e: SHMLBA alignment.
#. 686db5c5c84ad2fc8f0aa5391870c5bfed9e8bf3: pass VM_USERMAP directly.
#. f75b713d9a23f8b8fc9fb9d19ed7f2e8822ae059: lazy-purge threshold.
#. 46a3b96a5a06feaff17526ed505989c4d5136540: atomic_long lazy counter.
#. 255e313d2ad1bb019fece98d4fc315645de090b9: augmented free-block allocator.
#. a3ac4fd0986b630c0c8f89829b105b2ef0c714a9: remove unused node argument.
#. 5021f6a5d420133f7439a27aaf72d6d431ae5e4a: split-node preloading.
#. 7ef1c5c16b22d7aa3017280670d83629e32f9b27: avoid redundant unlink.
#. 902781dbff5c4e0772cb8f8d4be7a86315bf1172: warn on invalid unlink.
#. 5d1313d1b8bd53d63477fbb671c43410a0cfad30: per-CPU search correction.
#. 64fba55ad5656021ebcd83966c28b3d2190b65dd: detach pending areas from busy tree.
#. 626616a53457553bd19db2dee9419f63181e0406: state-dependent metadata union.
#. 69058cd6516c9a9ff73a7fca14f383db378a34f2: speculative preload without pinning.
#. 2e4f46245786621a6334fbdfc009ec8e5d99582a: respect caller GFP mask.
#. aa7f703ce3ef77974172205272ac0344980b5c67: separate busy/free locks.
#. Replace donor 2ad46d80f261f5568c717cd425aa81c34fb3a2fe with canonical
   upstream 0a7dd4e901b8a4ee040ba953900d1d7120b34ee5, "mm/vmalloc: Fix unlock
   order in s_stop()". The donor deletes the purge-mutex unlock; upstream
   preserves both unlocks and puts spin_unlock before mutex_unlock.

Canonical #16 is available at
https://github.com/torvalds/linux/commit/0a7dd4e901b8a4ee040ba953900d1d7120b34ee5 .

Donor #17, 7c901271bab0ccfc9972f511e2be17a07f257f1b, is intentionally omitted.
Its local substitutes do not reduce the preemption-disabled interval in this
kernel. Existing get_cpu_var/put_cpu_var protection is retained; unpinned
per-CPU queue access is not substituted.

Design and local corrections
----------------------------

The free address ranges now live in an augmented red-black tree and an
address-ordered list for adjacent-range coalescing. Busy areas have their own
tree/list and spinlock. Pending areas leave the busy tree immediately but
remain unavailable for allocation until the purge flushes the TLB and merges
them into the free tree. The purge mutex also protects pending-node lifetime
during /proc/vmallocinfo traversal.

The union contains subtree_max_size for free areas, vm for busy areas, or
purge_list for pending areas. On the tested 64-bit host layout the structure
is eight machine words (64 bytes), rather than eleven (88 bytes). This is a
metadata layout reduction, not a measured slab/RAM saving on the device.

The donor needed these corrections beyond clean patch application:

* Lowest-fit search prunes using the requested size, not size plus worst-case
  alignment padding. The latter incorrectly excludes an exactly fitting,
  already aligned hole. The iterative traversal visits eligible candidates
  in address order and backtracks after alignment failures. It does not
  recurse or assume that failure in one subtree rules out all later holes.
  Subtree pruning remains useful, but adversarial alignment can require
  examining several candidates; strict logarithmic search is not claimed.
* Candidate alignment detects unsigned wrap. Fit classification and the
  requested exclusive upper bound use subtraction-safe size checks instead
  of unchecked start-plus-size comparisons.
* Failure to allocate early busy-reservation metadata or free-gap metadata
  panics before publishing the allocator as initialized. Silently skipping
  a reservation can make live early mappings appear free. The free-gap
  import checks ordered, positive busy ranges and avoids unsigned gap
  underflow. This deliberately changes boot-time metadata OOM to fail-fast,
  rather than proceeding with an incomplete address-space map.
* /proc/vmallocinfo releases the busy spinlock before the purge mutex, with
  both lock-release annotations retained. Pending diagnostics use the
  seq-list head record, so they are emitted even with no busy areas or with
  a final vm_map_ram area. Pending records are printed first and are not
  address-sorted. The existing restricted pointer format is retained.
* Union root-name comments and purge-mutex lifetime documentation match the
  new ownership rules.

Speculative preload respects the caller's GFP_RECLAIM_MASK. Migration can
occur before the free-tree lock; the under-lock per-CPU compare/exchange
handles an occupied preload slot, and missing split metadata has a NOWAIT
fallback. This does not promise that every request has a preloaded node.

The vendor calc_total_vmalloc_size integration and vmalloc_user_node_flags
interface are retained. User-mappable allocators keep SHMLBA alignment,
VM_USERMAP and zero-fill flags. No device defconfig, MGLRU policy, scheduler
setting or physical-page reclaim tuning changes are part of this port.

Local validation (2026-11-02)
-----------------------------

Host tests in tools/testing/selftests/vmalloc_backport extract the actual
allocator, proc iterator, vmap layout, seq-list helpers, list implementation
and red-black tree implementation from this checkout. They passed normally
and with undefined-behavior sanitization:

* 400,000 fragmented lowest-fit/alignment/overflow comparisons with independent
  page-bitmap and 128-bit arithmetic oracles, plus the exact aligned-hole
  regression from review.
* 30,016 allocation/free, splitting/coalescing, caller-GFP, migration and
  allocation-failure operations. Tree/list ordering, augmentation, red-black
  invariants and page-bitmap coverage are checked along the way.
* 4,014 per-CPU allocation/oracle/rollback cases, including shuffled offset
  arrays and allocation-failure injection.
* Six boot import cases (success and five occupied/free metadata allocation
  failures).
* Lazy-reuse quarantine, flush-before-free-space publication, pending output
  with an empty busy tree, vm_map_ram and ordinary busy output, and balanced
  iterator locks for short reads, restarts and EOF.
* Five negative controls compiled and failed C assertions as expected:
  worst-case-padding pruning, missing mutex unlock, skipped early reservation,
  unconditional GFP_KERNEL preload and free-space reuse before the TLB flush.

ARM64 object validation used Clang 19.1.7/LLD from Zig 0.14.1, not the production
AOSP r614150 compiler. All build products and host tools were outside the
repository. Polly and signature/trusted-key dependencies were disabled only
in generated validation configs. Shadow-call-stack stayed enabled.

* Miatoll-derived config, with ThinLTO: mm/vmalloc.o, mm/percpu.o,
  fs/seq_file.o, arch/arm64/mm/ioremap.o, mm/kfence/core.o, mm/page_alloc.o,
  mm/vmscan.o, mm/memory.o, kernel/fork.o and kernel/sched/core.o passed.
* NUMA, DEBUG_KERNEL, DEBUG_VM, DEBUG_SPINLOCK, PROVE_LOCKING/LOCKDEP and KEXEC
  enabled, with ThinLTO: mm/vmalloc.o, mm/percpu.o, fs/seq_file.o and
  kernel/kexec_core.o passed. These are validation options, not device defaults.
* PROC_FS disabled, PREEMPT_NONE and no LTO: mm/vmalloc.o, mm/percpu.o and
  arch/arm64/mm/ioremap.o passed.
* A relocatable ThinLTO link of the ten device objects produced an AArch64
  ELF object. This is not a vmlinux link or modpost.
* Existing MM selected-backport models, MGLRU (2,006), procfs (58,806),
  BBRplus (1,080) and both BORE group variants (104,996 math/weight cases each
  plus inheritance checks) passed again.

Limitations and device follow-up
--------------------------------

The host model is single-threaded with fake slab, locks, CPU migration,
atomic/list operations, TLB flushes and seq output. It cannot establish real
lockdep cleanliness, SMP ordering, CPU-hotplug correctness, allocator pressure
behavior or page-table/TLB correctness. No production-compiler full image,
modpost, new device boot, runtime stress or performance/battery measurement
was performed. No push or CI was run.

Before calling this device-validated, build with the pinned production Clang,
boot on miatoll, check the kernel log, and exercise module/ioremap/vmalloc and
vm_map_ram allocation/free traffic under memory pressure while repeatedly
reading /proc/vmallocinfo (including short reads and seeks). A separate debug
build should run lockdep and relevant fault injection with concurrent purge
and allocation. Check for overlap, stale mappings, allocator failures,
corruption, hangs and unexpected latency. Donor synthetic benchmarks are not
evidence of phone/UI or battery gains.
