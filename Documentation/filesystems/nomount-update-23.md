# NoMount dev update: v2.3.0 / API base 23

## Scope and source

- Repository: https://github.com/maxsteeel/nomount
- Prior dev pin: `04af0552bb29c7cee1b78c3eea69d7ed98b80bf2` (API22).
- New dev pin: `5e9feb6f3fce42423f56b37e344052c59ec16b66` (API23).
- Release master compared during review: `7914458ca71dfa3a8c162fa97fdb69332db7a690`.
  We retain dev lineage rather than silently switching to master. The dev pin's
  subject is an installer change; only kernel source, not that installer, is
  imported. Identity is pinned, not a promise about a moving branch's future tip.

`nomount.c`, `nomount.h` and LICENSE match the new upstream Git blobs exactly.
Kconfig and Makefile remain byte-identical to the prior hardened local versions:
KEYS dependency, default-off Kconfig (selected built-in by miatoll), GNU11 and
native `xattr_handler.__get` detection. Neither upstream `-O3` nor
`-fno-stack-protector` nor repository probing is introduced. This preserves the
kernel's own compiler choices; it does not assert stack protection is enabled.
The original `nomount-compat.diff` still applies to the new upstream build files.
No global VFS/KSU hooks, rule defaults, module binary or install script changed.
Use matching v2.3 userspace for rule administration; no userspace was installed.

## Review focus

This is a substantive update, not just a version macro:

- Rules now precompute `uid_count`; the optional default occupies slot zero,
  UID ranges are sorted, and inclusive overlapping scopes/exclusion holes are
  checked before insertion. The default `0..0` cannot have a nonzero exclusion
  under the insertion checks; tests do not invent invalid default exclusions.
- Child enumeration switches from bloom indexing to full-name hashes and
  bucket starts, with linear lookup for at most two entries. Name comparisons
  still disambiguate full-hash collisions. Native position cookies carry a
  16-bit fragment; compat cookies retain their 16-bit ID without a fragment.
- Virtual leaves acquire explicit references; rule arrays/leaves are retired
  for deferred reclaim after a grace period. Backing-file caching retains one
  inode-owned reference, restricts reuse by credential pointer, and drops a
  losing cache-publication opener's reference on release. llseek uses the
  caller's position for SEEK_CUR rather than a shared cached-file position.
- Lookup/rebinding and cross-superblock proxy handling, blocked UID native views,
  restored operation vectors and shutdown cleanup are updated upstream.
- Xattr setters on virtual inodes dispatch to native `vfs_setxattr` or
  `vfs_removexattr` for the backing dentry, propagate failures and check read-only
  backing superblocks. Reads retain `__vfs_getxattr`; this is **not** proof of
  permission/LSM equivalence across an injected inode and its backing inode.
- GET_LIST now signals completion with `~0U`, rather than relying on another
  empty page. Userspace must understand continuation/completion semantics.

Native4.14 headers were checked for `LOOKUP_RENAME_TARGET`, `IOP_NOFOLLOW`,
`vfs_path_lookup`, `__vfs_getxattr`, and the un-idmapped xattr signatures. No new
C/header compatibility override was needed by that inspection. This is not a
whole-translation-unit production compile or a comprehensive security audit.

## Reproducible validation

```sh
python3 tools/testing/selftests/nomount/test_update23.py --self-test-negatives --historical
python3 tools/testing/selftests/nomount/test_integration.py --config /path/to/resolved/.config
python3 tools/testing/selftests/kernelsu/test_update50.py --self-test-negatives --historical
python3 tools/testing/selftests/fs_backport/test_f2fs_sysfs.py --sanitize --self-test-negatives
python3 tools/testing/selftests/bbr3/test_provenance.py
```

Current extracted production-body models are built with host GCC/UBSan, checking:
44 capability/payload gate cases; 131072 native/compat cookie roundtrips;
400384 UID/bloom/isolation checks; 1001 range/fallback cases plus scope boundaries;
108241 overlap/exclusion pairs and UINT_MAX boundaries; 21840 child-index
lookups/removals across singleton/linear/bucket thresholds and forced full-hash
collisions. A separate native4.14 fixture tests actual open/release/seek/xattr
and retire/reclaim function bodies with mocked VFS, references and RCU. Nine
compiled semantic mutations must trip runtime assertions; eight receipt/source/
config/preserved-KSU/hardening/model/patch mutations must be rejected, after a
passing unmodified fixture. These are single-threaded mocks, not kernel tests.

ARM64 miatoll Kconfig generation uses host GCC only and checks the resolved
built-in NoMount/KEYS, KSU+50/SUSFS/compat and bbr3/fq selections. No production
AOSP Clang ARM64 image/link or boot was run. Preserved suites cover KSU/FinaSU,
SUSFS, F2FS sysfs width and BBR provenance; see the adjacent result log.

## Additive provenance (no rewriting older receipts)

`nomount-update-23.json` and `.diff` record exact before/after endpoints, current
artifacts and preserved files. `tools/testing/selftests/nomount/update23.py`
anchors the receipt digest, checks current blobs/build adaptations, inverse
replays only listed paths on detached files, verifies old hashes, then forward
replays a separate small tree and verifies new hashes. Legacy checks run on
that verified predecessor, explicitly labelled as historical. Live sources are
never temporarily reversed. The old API22 test's CLI remains for config/CI
consumers; use `test_update23.py` for current API23 behavioral models.

KSU+50's receipt seals the prior NoMount C source, so its validator composes
with this successor replay instead of resealing KSU history. Its tamper-test
fixture likewise replays the predecessor first and proves its baseline passes
before testing mutations. The original KSU+50 receipt/patch, KSU-38/FinaSU/SUSFS
receipts, production KSU source, F2FS fix, bbr3/fq settings and workflow are
preserved, not broadened or re-approved by this update.

## Outstanding target/device validation

No target compiler is installed in this sandbox. A production build must use
the already selected exact AOSP Clang revision, not substitute host GCC results.
Before deployment test native/32-bit clients, v2.3 rule add/replace/delete/list
pagination (including long paths and completion), overlapping scopes/exclusions,
UID bypass/native view, cross-superblock ext4/F2FS/EROFS paths, rename/rebind,
xattrs with enforcing SELinux/read-only backing mounts, per-open seek/IO/mmap,
cache publication races, concurrent rule churn/reclaim and shutdown. Host mocks
do not establish real VFS permissions, RCU/SMP correctness, absence of leaks or
successful boot. No device rules changed, no commit/push and no CI requested/run.
