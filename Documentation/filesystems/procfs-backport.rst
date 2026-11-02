Procfs maps/smaps backport notes
===============================

Source and order
----------------
The thirteen changes requested from AzyrRuthless/kernel_xiaomi_sm6250 were
applied in donor dependency order.  They are a backport, not a new independent
implementation:

* 06330f5b58f958c1c51a7c2f2e5f95f3e254fceb: revert forced little-cluster
  migration during maps reads.
* ce389dc0f59a5112175fbf8e633a158e2695fb74: revert the custom ARM64 formatter
  and d_path_outlen() path plumbing.
* b810878560ba56cabdfaab57e4aaf263175de011: width-aware decimal printing.
* 686a9a0596776176dc9661785a6a21662a64dd21: hex sequence printing.
* ad17b568d5b78351d48cc074c9e49f56901f634b: shared PID/TID map handlers.
* 3638aadffd8b9c06e0dd56aef3112b618398f64e: gather smaps statistics.
* 90208857deb019965cc1bde69584e103e52dd5bc: common statistics printer.
* 2321653ec0a7cb2ab31b672463dd96a4b0a9bb6c: single-value smaps_rollup.
* 869fd85e10145d0cdd986f367ddb72e173dfd343: no-pkey vma_pkey() fallback.
* 76f0d41fa56f5bb55bbe010d9e8b72f3d53ce965: no-pkey arch_pkeys_enabled().
* 8ff3cde162fdb52ad4a8f029a6252af10d9e73e9: include linux/pkeys.h.
* d10c142d7e218a5eaa726bb006c3769f31523228: Pss_Anon/File/Shmem rollup.
* 0253fe4131436c2eb155a109ce55671a42366b3e: snapshot map_files addresses
  under mmap_sem and format names after releasing it.

Both reverted features were present here.  The reverts restore the base
expected by the series, avoid proc readers changing CPU affinity, and remove
ARM64-only 40-bit formatting limitations.  Regular maps path output again
uses seq_file_path() with newline escaping.  Android anonymous mapping names
and the existing MGLRU implementation/configuration are retained.

Local corrections
-----------------

* The decimal single-digit fast path must honor widths greater than one;
  otherwise zeros/small values lose ABI space padding.
* VmExe and VmLib are already calculated in KiB.  Do not shift them down
  again when passing them to the decimal printer.
* Locked PSS remains per-page accounting.  Adding the cumulative VMA/rollup
  PSS again in smap_gather_stats() double-counts locked pages and can also
  charge earlier unlocked mappings to a later locked mapping.
* A live mm may have no VMAs.  The rollup reader must release policy, lock
  and references without dereferencing mm->mmap in that case.
* Fixed-point PSS arguments and intermediates use u64, with casts before
  shifting; this avoids truncating compound-page PSS on 32-bit architectures.
  Shared-page division uses do_div() for 32-bit kernel compatibility.
* This older x86 mmu_context.h needs its no-pkey vma_pkey() before its inline
  access checks.  Keep that fallback and exclude the duplicate generic stub
  on x86.  Supply native arch_pkeys_enabled() using the OSPKE CPU feature.
* Documentation examples match the fields emitted.  Rollup does not emit
  per-VMA Size/page sizes/flags/names/keys.  PSS components describe actual
  page types, not just the VMA's backing file, and round after aggregation.

Validation (2026-10-31)
-----------------------

All builds below were local, selected-object checks with Clang 19.1.7/LLD
from Zig 0.14.1, not the production AOSP r614150 compiler.  Host tools also
used Clang.  Generated configurations and build products were kept outside
the source tree; the device defconfig was not relaxed for these checks.

* ARM64 miatoll-derived ThinLTO/SCS configuration, with MGLRU compiled and
  enabled at boot: task_mmu, proc/base, proc/meminfo, seq_file, dcache,
  vsprintf and vmscan objects passed.  The OF unittest object also passed
  with CONFIG_OF_UNITTEST enabled in the validation-only output config.
  The task_mmu and proc/base objects also passed with proc page monitoring
  disabled, followed by another successful build after re-enabling it.
* x86_64, NUMA/proc page monitoring enabled: the six affected MMU/core objects
  above (excluding vmscan) passed with protection keys both enabled and
  disabled.  The wrapper filtered this ARM64-oriented tree's global Cortex
  CPU/tuning flags for x86 validation; output configs used the frame-pointer
  unwinder instead of ORC because libelf development files were unavailable.
* ARM mps2 NOMMU: task_nommu, proc/base, proc/meminfo, seq_file and dcache
  objects passed.  vsprintf was blocked by the existing, unrelated
  include/linux/filter.h use of undefined compat_uptr_t on this 32-bit
  configuration; that declaration is unchanged from the branch base.  This
  is a partial NOMMU check, not a full successful NOMMU build.
* An additional ARM32 MMU attempt was blocked in the existing ARM uaccess
  inline-assembly clobber macro with the local Clang compiler.  It is not
  counted as a successful 32-bit MMU check.
* Output-only signature/trusted-key dependencies and Polly were disabled
  where necessary for locally available build dependencies.
* The host selftest passed 58,806 formatting cases plus production-extracted
  status-unit, PSS and rollup models.  Both deliberately restored donor bugs
  (single-digit padding and cumulative locked PSS) failed C assertions.
* The existing MGLRU host checks were rerun: 2,006 shadow cleanup cases and
  source guards passed.
* Scoped patch whitespace checks passed.

Run the durable host checks as documented in
``tools/testing/selftests/procfs_backport/README``.  They model page walking
and synchronization and do not run the modified kernel.  No full image link,
production-toolchain build, boot, device stress, performance measurement,
push or CI run is implied by these results.  In particular, live shmem swap,
THP/hugetlb behavior and concurrent mm teardown still need kernel/device
validation after a full build.
