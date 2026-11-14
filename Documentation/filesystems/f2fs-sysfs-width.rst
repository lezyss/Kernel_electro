F2FS sysfs integer-width adaptation
==================================

Status: applied locally by user request; no commit, push or CI dispatch.
Only fs/f2fs/sysfs.c is changed in production code. The separate compressed-file
UAF donor170bd9221328c81568127d16befb2a9177835a5a is NOT applied.

Provenance
----------

Donor: LineageOS/android_kernel_qcom_sm8250
3fcb7aa3e71b25a6bc096ab6d6609ee716f59403, "UPSTREAM: f2fs: fix out-of-bounds
access in sysfs attribute read/write".

Original upstream:98ea0039dbfdd00e5cc1b9a8afa40434476c0955.

This is a native adaptation, not a bulk F2FS import. The donor's newer attribute
set is not imported: local declarations, handlers, lock ordering and validation
remain. There is no local F2FS_RO_ATTR wrapper to update; F2FS_RW_ATTR and
F2FS_STAT_ATTR are the local size-bearing macros. sizeof_field() and sysfs_emit()
already exist in this tree, so no helper-library backports are needed.

What changes
------------

* Add size metadata alongside the existing struct offset.
* Compute it from the actual member using sizeof_field(), including indexed
  interval_time elements and statistics attributes.
* Generic show/store use 1/2/4/8-byte accesses instead of assuming unsigned int.
* Preserve extension_list's custom array handling ahead of generic access.
* Preserve all store validation and special cases, including reserved-block
  locking, discard/migration checks, GC wakeups, unmount protection,
  iostat_enable's boolean normalization/reset and iostat_period_ms locking.

In this tree, iostat_enable is bool: its generic read must not consume adjacent
bytes. Its existing custom store remains unchanged. gc_pin_file_threshold is
u64 and interval_time elements are long (8 bytes on ARM64): generic accesses
now use their full widths rather than the low four bytes. Ordinary 4-byte
attributes keep the original unsigned presentation. The donor's carve_out and
atgc_age_threshold examples are not imported as new attributes.

Limits and preserved behavior
-----------------------------

Parsing remains kstrtoul(): on the target ARM64 profile unsigned long is64 bits;
on a32-bit kernel it cannot parse values above ULONG_MAX even for a64-bit field.
This is not a cross-architecture parser redesign. Generic presentation/access
remains unsigned as in the donor; signed-range policy is not added. Narrow
stores keep C conversion/truncation semantics, not new range rejection. Existing
attribute-specific validators still apply. Size-aware access does not make
64-bit loads/stores atomic on32-bit systems or add synchronization to attributes
that did not have it. Invalid descriptor sizes retain the donor bug/error path;
non-integer extension_list bypasses it through its existing custom handlers.

No mount options, on-disk format, compression selection, GC/checkpoint policy,
F2FS Kconfig, miatoll defconfig, TCP defaults or other filesystem code changes.
This is a sysfs correctness fix, not a storage-throughput optimization.

Validation
----------

Run from the repository root::

  python3 tools/testing/selftests/fs_backport/test_f2fs_sysfs.py \
      --sanitize --self-test-negatives
  python3 tools/testing/selftests/fs_backport/test_backport.py \
      --cc 'gcc -fsanitize=undefined -fno-sanitize-recover=all'

The new test extracts actual helper, show, store and locking-wrapper functions,
the attribute descriptor and production RW/stat macros. Host fixtures replace
kernel structures, locks and parsing. It covers all four widths with canaries,
wide values (including UINT_MAX+2 and ULONG_MAX), the boolean read/custom store,
an indexed long member, descriptor sizes, overflow/malformed input, special
validation/locking/wakeup/error paths, and unsupported descriptor sizes.

Five semantic mutants must compile but fail runtime assertions: 4-byte boolean
read/write, truncated64-bit store, incorrect RW size and incorrect stat size.
Hashes also prove that the complete old store/s_umount wrapper bodies remain
unchanged except the final generic store call. All42 local RW/stat declarations
route through the updated size-bearing macros. Source patch reverse/forward
replay and preserved-source hashes are checked independently.

GCC host UBSan tests passed, along with existing filesystem regression models.
Supplemental existing F2FS A/B1/B2 models passed using a temporary GCC wrapper
mapping Clang's -fsanitize-trap=all to -fsanitize-undefined-trap-on-error; B2 also
needed -Wno-misleading-indentation for an unchanged fixture. No production code
or existing regression runner was edited to accommodate those host differences.

These are host extraction/mock tests, not actual kernel sysfs operations,
concurrency stress, a production AOSP r614150 ARM64 compile/link, or device
filesystem testing. Those remain outstanding. Do not test arbitrary sysfs
writes on valuable mounted data to reproduce corruption. Detailed hashes/logs
are in f2fs-sysfs-width-validation.json; the additive patch is
f2fs-sysfs-width.diff. Historical F2FS receipts are not rewritten.
