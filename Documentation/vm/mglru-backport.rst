.. SPDX-License-Identifier: GPL-2.0

Multi-Gen LRU experimental backport
==================================

Scope and defaults
------------------

This is an adapted March 2022 FROMLIST MGLRU implementation for this 4.14
kernel, not a claim of parity with current upstream MGLRU. The 32-commit
source series is in AzyrRuthless/kernel_xiaomi_sm6250, from
27048e83e24d7f2fa141f1e5c769612170722527 through
3728f6da063f3ac72a0fe71262e9ebfec1f01799.

The miatoll defconfig builds CONFIG_LRU_GEN=y and CONFIG_LRU_GEN_ENABLED=y:
the generation-based reclaim core is enabled at boot. Full historical
statistics (CONFIG_LRU_GEN_STATS) remain disabled. The minimum working-set
TTL defaults to zero. The donor's five-second default was deliberately not
adopted: a nonzero TTL can provoke earlier OOM decisions under pressure.

The optional speculative-page-fault patch (84a2f8f9b66a) is omitted. This
tree does not contain the prerequisite SPF framework; normal page faults
are integrated without it. No speculative-fault feature is enabled.

Controls and fallback
---------------------

After booting the rebuilt kernel, inspect the controls::

    cat /sys/kernel/mm/lru_gen/enabled
    cat /sys/kernel/mm/lru_gen/min_ttl_ms

The enabled value is a hexadecimal capability mask:

* bit 0: MGLRU reclaim core;
* bit 1: regular hardware-assisted page-table aging;
* bit 2: accessed-bit handling in non-leaf PMDs on supporting architectures.

The displayed mask depends on architecture/hardware support. ARM64 does
not gain x86's non-leaf PMD accessed-bit capability from this backport.
Do not require a particular full mask to declare ARM64 support working.
An explicit full-scan debugfs command can request a page-table walk even
when regular hardware-assisted aging is disabled.

Privileged writes can disable MGLRU and return to the traditional LRU, or
re-enable supported components::

    echo n > /sys/kernel/mm/lru_gen/enabled
    echo y > /sys/kernel/mm/lru_gen/enabled

Keep the initial TTL at zero::

    echo 0 > /sys/kernel/mm/lru_gen/min_ttl_ms

Android SELinux/root policy may restrict these writes. These commands do
not persist across reboot unless userspace explicitly makes them do so.
The existing flashed kernel is unaffected until a new build is installed.
Keep a known-good boot image/recovery method before testing. The runtime
switch cannot recover a kernel that fails before userspace starts.

Debugfs is optional; it is not required for the core or sysfs controls.
When CONFIG_DEBUG_FS is enabled and debugfs is mounted, lru_gen exposes
statistics and privileged aging/eviction commands; lru_gen_full exposes
extended information. No background proactive-reclaim daemon is added.

Local adaptations
-----------------

* Swap-shadow cleanup checks iter.index before touching an entry, bounded
  by both the requested inclusive end and the current swap address space.
  It does not mistake radix-tree iter.next_index for the current index.
  Advancing between address spaces cannot wrap at ULONG_MAX.
* Legacy HMM/migration stack mm_walk initializers are zeroed, including
  the newly consulted p4d_entry callback. Generic page-walk changes apply
  even when MGLRU itself is disabled.
* With a runtime-disabled memory controller, mm registration uses the
  same global FIFO as reclaim rather than a separate root-memcg FIFO.
* Migration before mm registration is tolerated, retaining 3728f6da063f.
* A zero TTL does not invoke the new TTL-specific OOM path. The existing
  allocator/OOM machinery is not disabled by this change.
* sc->may_swap is respected. With CONFIG_OPLUS_MM_HACKS, the local
  direct-reclaim swappiness and low-swap reserve are retained.
* The x86 non-leaf capability selection respects PGTABLE_LEVELS > 2.
* The optional THP unmap call matches this tree's three-argument rmap API.

Reclaim policy differences
-------------------------

When MGLRU is disabled, the traditional scan-selection path and its
vendor policies are retained. With MGLRU enabled, its feedback controller
replaces the old scan balancing. The size-based anon_min_kbytes,
clean_low_kbytes and clean_min_kbytes protections in the traditional
get_scan_count path are NOT applied to MGLRU. Do not assume those knobs
retain their previous effect with the new algorithm enabled, or combine
an aggressive nonzero TTL with them as if their semantics were identical.

Validation and limitations
--------------------------

Host regression checks::

    python3 tools/testing/selftests/mglru/test_backport.py

These extract the production shadow-cleanup function and execute it in a
sparse iterator model, plus check selected backport guards. They test
range arithmetic/entry selection, not actual radix-tree concurrency,
reclaim, page tables, RCU or a running kernel. See the adjacent test README.

Local ARM64 object compilation covers the miatoll configuration and
variants with memcg, THP, debugfs, full statistics, MGLRU disabled, and the
core enabled by default. Such compilation is not a full production
r614150 kernel link or a device boot/performance test. Device validation
must include sustained memory pressure, ZRAM/swap activity, app kills,
fork/cgroup migration where enabled, swapoff, and repeated runtime state
switches. Compare on/off with the same workload and TTL zero before
claiming gains or changing the TTL. Donor benchmark numbers are not
measurements of this kernel on miatoll.
