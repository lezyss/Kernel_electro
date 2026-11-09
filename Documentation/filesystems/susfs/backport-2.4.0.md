# Original SUSFS 2.4.0 backport for Electro 4.14

## Source and scope

This is an adapted **NON-GKI / ARM64 / 4.14** backport of original
[simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu), reference branch
`gki-android12-5.10`, commit
`45a057536ddba12fd59fb583a8f5375f83be703e`, tree
`a90aee9a6a867ce1954b89bb4dd95d77872b0193`.
It is not a drop-in GKI patch, an official non-GKI recommendation, or an
unmodified replacement with a third-party port.

GitLab's original commit identity was checked independently. Source transfer
used `https://github.com/ShirkNeko/susfs4ksu`, which carries the **identical
original Git commit and tree objects**. No mirror-specific changes were used.
`backport-2.4.0.json` records original Git blob identities and SHA-256 hashes of
the three core files, kernel patch and official-KSU reference patch.

The predecessor is Electro's corrected 2.3.0 port, not pristine Linux or the
original 5.10 kernel. Original 2.3.0 ancestor
`fb16b41a65180979f05eac837681c4dd0addffd1` was used for three-way review, followed
by manual 4.14/backslashxx adaptation. Many later fixes were already present in
Electro; they are preserved rather than credited as newly introduced.

**Retained:** backslashxx KSU `v3.3.1-38` /
`feeec8e4059e3bb0ecdd1827b687b69f1cf4a2fb`, actual version 32717; FinaSU manager
package/certificate binding and honest metadata; NoMount; the selected full
SUSFS feature defaults, including SUS_PATH, legacy TRY_UMOUNT and experimental
OPEN_REDIRECT. Workflow triggers, root grants, manager identity,
module-unmount lists and the production hook strategy remain unchanged.
After the initial backport, the user explicitly approved enabling
`CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y` in the miatoll production defconfig.

## Adaptation map

| Original 2.4 change | Electro implementation / retained correction |
| --- | --- |
| Mount hiding independent of physical kernel unmount | Mark eligible, non-manager/non-allowlisted zygote children whether or not physical unmount is enabled/modules are mounted. When physical unmount runs, mark only after it finishes and credentials are restored, so SUSFS mount lookup cannot hide its unmount targets. Keep UID, denylist and old-zygote checks, every physical-unmount guard and extra-path/module-list behavior. |
| Mount fast path | Skip mount-hash locking for already-legitimate mounts; return the same owned mount/root reference pair on every branch. Balance the local defensive fallback too. |
| Clone/mount-minor fixes | Existing per-clone borrowed-ID boolean, fresh-ID marker clearing and minor base `1 << 12` were already correct and remain unchanged. |
| Independent SUS_KSTAT / OPEN_REDIRECT | Retain existing independently guarded hooks and 14-bit KSTAT buckets. Add native statfs wrappers; capture and retain the underlying mount's `f_flags`, including the fallback path. Keep inode/device collision checks and CTIME bit 8. |
| KSTAT update allocation leak | Free the replacement allocation when an update finds no matching entry. |
| SUS_PATH dentry lifetime/FUSE create protection | On 4.14, test the result **after** `lookup_real()` has populated the inode, not the newly allocated negative dentry. Read `s_magic` before releasing the dentry; deny hidden FUSE create/exclusive requests without dereferencing a released object. |
| OPEN_REDIRECT `nd->name` lifetime | Electro redirects at the owned `fs/open.c` filename/file boundary, not the 5.10 `do_o_path`/`do_tmpfile` nameidata splice. Keep this existing 4.14 design and its filename ownership; do not import the dangling-name pattern. Existing readlink length/fault/hash and page-allocation cleanup fixes stay intact. |
| Cmdline seqlock retry fix | Electro already uses a mutex-protected snapshot and an integer fallback result. Keep that byte-identical, correct implementation instead of introducing a seqlock or changing `/proc/cmdline`'s fallback ABI. |
| Existing helper linkage | Keep the global `susfs_starts_with()` implementation/prototype for 4.14 /proc/kallsyms callers; the 5.10 inline-only conversion is not a drop-in ABI change. |
| Enabled-feature allocation failure | Keep the existing NULL-safe error-copy path and minimal-build annotations. |
| SELinux type/full-tuple registries | Carry original typed filtering and original-allowed snapshots into native 4.14 query parsers using its `policy_rwlock`/sidtab API and RCU read sections. Store/check the actual type value, not just the hash bucket. Atomic writer locks and `GFP_ATOMIC` avoid sleeping under 4.14 KSU policy writers/stop-machine. |
| SELinux AV bookkeeping | Capture only `AVTAB_ALLOWED`, before mutation, preserving the first value for the full source-type/target-type/class tuple. Audit-allow/deny masks must not contaminate the allowed-mask registry. |
| Backslashxx SELinux hiding | Keep the existing runtime enable, seccomp/app-UID guards and fake-status mechanism. Replace its old string heuristic on context/access/current-attribute queries with the typed path. Explicitly retain hiding of preexisting backslashxx `su`/SU-file labels without hiding arbitrary existing types mentioned by modules. |
| SELinux real enforcement and status protocols | Do **not** transplant official KSU's different policy/status internals. The real AVC computation, ordinary context conversion, policy-cache invalidation and status sequence protocol remain unchanged. Query-view spoofing is isolated from actual access decisions. |
| AVC-log context buffer | Free the real context buffer when the existing log-substitution branch bypasses its normal cleanup. |
| SU-session FD after exec | Use the retained syscall-table strategy: save an authenticated SU-session result, execute the real syscall, then install the SU-only descriptor only on successful root/KSU-domain exec. Cover native/compat and execve/execveat wrappers; do not duplicate official inline exec hooks. Failed or unrelated execs get no new descriptor. Legacy non-table KSU modes retain their existing upstream path. |
| Priority UID filter | Carry compile-time support, root + CAP_SYS_ADMIN command authorization, and priority hooks; **Kconfig default n**, explicitly enabled in the miatoll production defconfig. Re-resolve packages only after successful rename publication, not the backslashxx pre-rename observer. Keep native `who == 0` resolution/user-reference handling. |

The original official-KSU synchronization is reference material, **not**
authorization to replace this fork or import its manager/UAPI wholesale.
The priority feature is now compiled in by the miatoll defconfig. Its UID bitmap
starts empty: a matching privileged SUSFS 2.4 userspace tool/module still needs
to supply the package list. This filters priority-query/set operations for
configured UIDs; it does not generally restrict all SUSFS processing to those UIDs.

### Priority-filter activation follow-up

The miatoll defconfig now explicitly sets
`CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER=y`; the generic Kconfig default stays n.
The real shipped Kconfig parser, built with host GCC for **configuration only**,
resolved this to y after `olddefconfig`. Full/minimal/disabled configuration
checks, existing extracted-source host models, the five backport runtime
mutants, all 30 provenance tamper controls and the new accidental-disablement
control passed. KSU, FinaSU and NoMount source/configuration checks also passed.
No target compilation is implied by using GCC to build the configuration parser.

A fresh full image build with pinned AOSP Clang has **not** been rerun for this
opt-in: the previous toolchain/output cache is no longer available in the
restored workspace. The original validation receipt remains unchanged and
records the previous priority-disabled build. Rebuild and boot-test before
claiming enabled-feature device validation. No package list is provisioned by
this configuration change, and no push or CI run is part of this follow-up.

## Provenance chain — do not reapply the recorded patches

The original `UPSTREAM.json` / `integration.diff`, FinaSU overlay, BPF/SUSFS
task-header overlay, Phoenix overlay and KSU +38 update evidence remain intact.

`backport-2.4.0.{json,diff}` is a **new 20-source successor** against the exact
local pre-2.4 tree (already including KSU +38). It is not a patch against Git
HEAD and must not be applied again. The closed-scope checker validates current
postimages, reverses the patch, validates all preimages, and replays it byte for
byte. Older checkers then verify those recovered bytes against their own
immutable historical seals. No old trust boundary is silently resealed.

`tools/testing/selftests/susfs/provenance_240.py` also fixes the successor
manifest's hash and path scope. Missing/changed/broadened successors fail closed.
Provenance records identity and review scope; it is not a signature or an
independent security audit.

## Validation and limits

See `backport-2.4.0-validation.json` for the **initial backport** build/config/source
receipt. That immutable historical receipt built with priority filtering **off**;
it is not a full-build or device-validation receipt for the later production
config activation. The follow-up changes only the defconfig, configuration
checks and documentation, not the sealed 20-source implementation.
Host checks:

```sh
python3 tools/testing/selftests/susfs/test_integration.py --host-tests --cc 'gcc -Wno-address'
python3 tools/testing/selftests/susfs/test_provenance_overlays.py
python3 tools/testing/selftests/susfs/test_backport_240.py --cc gcc --self-test-negatives
python3 tools/testing/selftests/kernelsu/test_integration.py
python3 tools/testing/selftests/kernelsu/test_finasu.py
python3 tools/testing/selftests/kernelsu/test_update.py --self-test-negatives
python3 tools/testing/selftests/nomount/test_integration.py
```

The new extracted-source tests cover 4,396 type/AV registry cases, 40 post-exec
FD authorization/result cases, 33 statfs cases, 33 SUS_PATH lookup/lifetime
cases, and all 45 field offsets/sizes in the existing LP64 command payloads.
Five deliberately broken implementations must compile and fail assertions.
The existing suite covers 272 command-authorization, 1,792 manager/zygote/unmount,
3,010 readlink and 2,404 pagemap cases. Thirty provenance tamper controls reject
missing, modified, resealed, broadened or unsafe successors/older overlays.

Native LP64 payload layout preservation also compiles with the pinned AOSP
compiler targeting AArch64. This is **not** new 32-bit SUSFS payload translation;
use a matching native ARM64 `ksu_susfs` tool. KSU's existing 32-bit compat hooks
are retained, separately from the SUSFS command-structure layout.

Kernel validation uses exact AOSP prebuilt commit
`3b86e40facfff1eab4065614255d573293c10373`, r614150 / clang 23.0.1 /
LLVM `52d25c7f6cf8d458a5d1cda9729c2ed757ebe86e`, with explicit LLVM kernel and
host-tool overrides. As in the existing build script, only the generated
output config disables stock-AOSP-incompatible LLVM_POLLY. The later priority
filter opt-in is the only follow-up production-defconfig change. Build products/toolchains stay outside Git.

Compile-only profiles are: SUSFS disabled, minimal, KSTAT-only, MOUNT-only,
OPEN_REDIRECT-only and priority-filter-only; these are not runtime activation
or proof of complete Android behavior. The later miatoll priority-filter opt-in
requires a fresh production build and device validation.
Host mocks do not establish SMP/RCU correctness, real VFS/fsnotify behavior,
policy-reload behavior, every module/tool compatibility combination, working
root, successful device boot or integrity-check outcomes.

Before device use: retain a known-good boot image/recovery path; use a matching
2.4 tool/module; check reported version/feature list, both authorized managers
(with only one selected), ordinary/non-root denial, native/compat SU including
failed execs, modules/NoMount/unmount toggles, mount/statfs/stat/fd/readlink views,
cmdline fallback, sdcard readiness, SELinux denial/audit behavior and suspend.
No device flash/boot, commit, push or CI dispatch is implied by this backport.
