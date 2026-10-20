.. SPDX-License-Identifier: GPL-2.0

KFENCE in the Electro 4.14 backport
=================================

This tree carries the KFENCE series from LineageOS's
``android_kernel_qcom_sm8150``, commits ``719db8e03dc6`` through
``5a9e63537ed9``, with compatibility adaptations for this kernel.
See :doc:`kfence` for the detector's design and interface.

Device defaults
---------------

The build's ``vendor/xiaomi/miatoll_defconfig`` selects::

    CONFIG_KFENCE=y
    CONFIG_KFENCE_SAMPLE_INTERVAL=500
    CONFIG_KFENCE_NUM_OBJECTS=63
    # CONFIG_KFENCE_KUNIT_TEST is not set

Static-key allocation sampling is selected by default when jump labels are
available. The timer uses idle waits, deferred IRQ-work wakeups, and the unbound
workqueue. Allocations with zone restrictions, including DMA/DMA32 caches, are
excluded. KFENCE is a sampled diagnostic tool, not a guarantee against memory
corruption or a substitute for testing with KASAN.

Memory and mapping costs
------------------------

With 4 KiB pages, the guarded pool is 512 KiB:
``(63 + 1) * 2 * PAGE_SIZE``. Metadata and page tables are additional costs.

This ARM64 implementation retains the upstream backport's page-granular linear
map when ``CONFIG_KFENCE=y``. It disables block and contiguous mappings across
the linear map, not just the guarded pool. Consequently, page-table memory and
TLB behavior can differ even with sampling disabled at boot. The pool size alone
must not be presented as the detector's total memory or performance overhead.
Measure boot, memory use, and workload behavior on the target device before
production deployment.

The boot argument ``kfence.sample_interval=0`` disables pool allocation and
sampling, but does not restore block mappings. Building with ``CONFIG_KFENCE=n``
is required to remove the compile-time mapping change. After boot, a disabled
KFENCE instance cannot be enabled or re-enabled through its module parameter;
choose the desired nonzero interval at boot.

Integration adaptations
-----------------------

* ARM64 handles recoverable KFENCE faults before entering the oops state,
  preserving exception-table and permission-fault handling.
* ARM64 page protection reports failures from ``set_memory_valid()`` instead of
  unconditionally claiming success.
* The bitmap and printf selftests retain their existing counter declarations;
  this tree does not provide ``KSTM_MODULE_GLOBALS()``. The printf test records
  skipped pointer-hashing tests explicitly.
* The optional KFENCE test source uses this tree's ``unsigned long`` slab-cache
  flags type. It remains disabled: the KUnit framework and its required APIs
  must be backported and validated separately before the suite can be used.
* Only the actual miatoll defconfig receives the final sampling settings; the
  source series' unrelated vendor defconfigs are not changed.

As in the original older-kernel backport, sampled allocations use root slab
caches rather than the legacy per-memcg cache. Do not assume full per-memcg
accounting for these objects.

Production diagnostics
----------------------

Leave ``no_hash_pointers`` absent from the kernel command line. Enabling it is a
debugging opt-in that exposes kernel addresses and additional report details;
it is not needed to enable KFENCE. The series does not enable KASAN or KUnit.

With debugfs mounted and appropriate privileges, inspect
``/sys/kernel/debug/kfence/stats`` and ``/sys/kernel/debug/kfence/objects`` for
sampling activity. Successful compilation is not a substitute for device boot,
allocation, suspend/resume, and fault-reporting tests. Local extracted-function
or mocked tests cannot validate ARM64 page tables, interrupt races, or hardware
behavior.
