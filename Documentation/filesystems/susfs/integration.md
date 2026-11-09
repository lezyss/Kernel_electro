# Historical SUSFS 2.3.0 integration: backslashxx KSU + NoMount

> **Current successor:** [original SUSFS 2.4.0 backport](backport-2.4.0.md).
> This document and `UPSTREAM.json` / `integration.diff` describe the original
> 2.3.0 import. Their seals have not been rewritten. Current-source validation
> reverses the explicit 2.4 successor before checking these historical hashes.

## Historical status and pinned sources

Integrated the **full donor feature defaults** selected by the user, including
SUS_PATH and experimental OPEN_REDIRECT. This is an adapted in-tree port, not
an unmodified cherry-pick and not a claim of phone-tested functionality.

| Component | Exact revision |
| --- | --- |
| Kernel hooks/backport | manipvlator/los_kernel_xiaomi_sm6150 `c931cae8ca19e4b738e3d9eda8fec4cdb7947473` |
| Companion KSU bridge donor | manipvlator/KernelSU `fcd50c8f367c470fa8e17eb64fbb8c7ce7527061` |
| **Retained KSU base** | backslashxx/KernelSU v3.3.1+36 `cbc0b49908066e9c7f778737f65a216f50b203ba` |
| **Unchanged NoMount source** | maxsteeel/nomount dev `04af0552bb29c7cee1b78c3eea69d7ed98b80bf2` |

The donor kernel commit alone lacks the KSU Kconfig/control/lifecycle bridge.
Its workflow fetches a moving manipvlator KSU branch. We reviewed and pinned
that companion patch, ported the necessary pieces onto the existing vendored
backslashxx source and preserved the current manager authentication and syscall
hooks. No fork replacement, setup script, symlink, nested Git or build-time
network fetch is used. Kernel-side SUSFS source/header files are regular files.

`UPSTREAM.json` records the donor revisions, original Git blob identities of the
three added SUSFS files and exact SUSFS-stage postimage hashes for the 32 source/
hook files. Original SUSFS files were verified before adaptation. The donor
kernel is distributed under its kernel COPYING license; existing source/license
notices are retained. The existing backslashxx licenses are unchanged.
Provenance is an identity record, not a signature or independent security audit.

`integration.diff` is the exact source/config patch against this tree immediately
before SUSFS (with the previously approved backports, vendored KSU and NoMount
already integrated). It is **not** a patch for pristine Git HEAD, and must **not**
be applied again to the current working tree. The original three KSU compatibility
adjustments remain separately recorded in the earlier KSU guide/diff.

## Later FinaSU-manager overlay

`Documentation/dev-tools/finasu-manager.md` describes a subsequent alternative
manager addition on the same backslashxx base. Its separate diff/manifest must
follow the SUSFS stage during reproduction. The original SUSFS patch and
postimages remain unchanged; the checker validates the one shared file,
`drivers/kernelsu/supercall/dispatch.c`, through that overlay's exact
preimage/postimage chain. It does not weaken the SUSFS command authorization or
claim FinaSU-specific kernel APIs. Current KSU provenance counts are 15 local
overrides and 89 unchanged upstream files.

## Adaptations and corrections

### Existing functionality preserved

- Vendored backslashxx base/tag/UAPI version and manager signing checks remain.
- The KSU setuid handler is byte-identical to the pre-SUSFS integration, retaining
  manager/allowlist behavior and native/32-bit hook selection.
- Existing module-unmount enable switch, module-mounted check, eligible UID
  classes, denylist decision, old zygote-domain check, credential override,
  module list traversal and credential restoration are retained.
- SUSFS extra paths augment that guarded unmount path; they do not replace KSU's
  module list. Processes are marked only after reaching that eligible path.
- NoMount's seven source/license/provenance files and its configuration/wiring
  remain intact. SUSFS and NoMount both compile into the filesystem archive.
- Earlier empty-mm smaps-rollup handling and task/mm release paths are retained.
- SUSFS uname spoofing precedes the existing configurable root-only BPF-loader
  override, so the previously approved loader compatibility rule still wins.

### Corrected donor behavior

- Require built-in KSU, ARM64, THREAD_INFO_IN_TASK and FSNOTIFY. The code consumes
  high inode/thread flag bits and directly calls built-in KSU symbols; do not
  allow an unsupported built-in SUSFS / modular KSU combination.
- Require initial-namespace UID 0 **and CAP_SYS_ADMIN** for the SUSFS reboot API.
  No manager-signature, SELinux-enforcement or seccomp bypass was added for it.
- Initialize SUSFS work before KSU registers credential/syscall hooks. Queue
  the existing work item without the donor's leaking/no-op task-work allocation.
- Preserve KSU's target-pid manage_mark behavior instead of substituting the
  calling task's state. Boot-completed handling starts the SUSFS sdcard monitor.
- Do not add the donor's extra zygote SELinux unmount permission: unmount runs
  under the existing KSU credential override. Guard zero/unresolved SID caches.
- Refresh remote-memory VMA lookup per page **under mmap_sem**, never before the
  lock or by reusing the previous page's VMA.
- Hide pagemap entries per VMA/PMD or hugetlb walk while emitting one zero entry
  per virtual page. Do not skip a whole read chunk and corrupt byte/offset
  accounting based only on the first VMA.
- Parenthesize inode predicates so negation has the intended precedence.
- Maintain borrowed mount-ID ownership on early clone errors, and do not let a
  fresh-ID clone inherit its parent's borrowed-ID marker.
- Handle d_path error pointers; preserve readlink truncation, returned byte
  counts, delayed-call cleanup and copy faults instead of returning zero bytes
  after copying data or falling back to a real path for a short buffer.
- Match inode keys as well as devices in hash-bucket reader loops.
- Reject unterminated pathname/uname/cmdline input strings. Clear the output
  feature buffer. Fix the CTIME seconds flag typo from `1 < 8` to `1 << 8`.
- Serialize extra-unmount list reads and uname snapshots. Serialize cmdline
  output with a mutex, avoiding duplicate seq_file appends on a seqlock retry
  and concurrent first-writer allocation races.
- Supply this 4.14 fsnotify API's required free_mark callback, drop the initial
  mark reference after successful attachment and clean failed-watch resources
  outside SRCU. Preserve the donor's deferred successful event cleanup.

These are scoped integration fixes, not a complete audit of SUSFS or KSU.

## Configuration

Miatoll explicitly requests:

```text
CONFIG_KSU_SUSFS=y
CONFIG_KSU_SUSFS_SUS_PATH=y
CONFIG_KSU_SUSFS_SUS_MOUNT=y
CONFIG_KSU_SUSFS_SUS_KSTAT=y
CONFIG_KSU_SUSFS_TRY_UMOUNT=y
CONFIG_KSU_SUSFS_SPOOF_UNAME=y
CONFIG_KSU_SUSFS_ENABLE_LOG=y
CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y
CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y
CONFIG_KSU_SUSFS_OPEN_REDIRECT=y
CONFIG_KSU_SUSFS_SUS_MAP=y
```

CONFIG_KSU=y, CONFIG_NOMOUNT=y and CONFIG_KEYS=y remain selected. SUSFS itself
still defaults to n for unrelated targets. Full compile-time features do not
prepopulate paths, redirects, UID lists, fake uname/cmdline values or an enabled
AVC-log-spoofing setting. Mount-ID/symbol handling is compiled active according
to the selected options; this is not a wholly passive backend like NoMount.

Upstream labels SUS_PATH NOT recommended because of performance/side-channel
concerns, and OPEN_REDIRECT experimental. They remain enabled per the full-profile
choice. Availability does not imply using every rule or combining frameworks
on the same object is safe.

## Commands to inspect, verify and build

Read the two original changes without running installers:

```bash
gh api repos/manipvlator/los_kernel_xiaomi_sm6150/commits/c931cae8ca19e4b738e3d9eda8fec4cdb7947473 \
    --jq '.commit.message, (.files[] | .filename)'
gh api repos/manipvlator/KernelSU/commits/fcd50c8f367c470fa8e17eb64fbb8c7ce7527061 \
    --jq '.commit.message, (.files[] | .filename)'
git apply --stat Documentation/filesystems/susfs/integration.diff
```

The original kernel patch conflicted in proc/cmdline, proc/task_mmu and
kernel/sys; we adapted those hunks without replacing whole files. The donor's
sweet defconfig was not copied onto miatoll.

From this kernel root, run offline checks:

```bash
python3 tools/testing/selftests/kernelsu/test_integration.py
python3 tools/testing/selftests/nomount/test_integration.py
python3 tools/testing/selftests/susfs/test_integration.py
python3 tools/testing/selftests/susfs/test_integration.py --host-tests --cc clang
python3 tools/testing/selftests/susfs/test_integration.py --host-tests \
    --cc 'clang -fsanitize=undefined -fno-sanitize-recover=all'
```

Build with the already pinned AOSP r614150 toolchain:

```bash
TOOLCHAIN_DIR=/absolute/path/to/clang-r614150 \
    JOBS="$(nproc)" bash scripts/ci/build-kernel.sh
```

CI preflight checks KSU, NoMount and SUSFS after olddefconfig before building the
image. It does not fetch or install any of them. Validate a resolved config with:

```bash
python3 tools/testing/selftests/kernelsu/test_integration.py --config out/.config
python3 tools/testing/selftests/nomount/test_integration.py --config out/.config
python3 tools/testing/selftests/susfs/test_integration.py --config out/.config
```

Any future source changes affecting recorded postimages require reviewing the
source/diff and updating provenance. Do not blindly regenerate hashes to silence
an unexpected test failure.

## Local validation and limits

Passed with Clang 19.1.7/LLD from Zig 0.14.1, **not** production Clang r614150:

- Full ARM64/ThinLTO filesystem subtree, KSU and SELinux archives; additional
  fork/exit/credential, syscall, native/compat table, security and memory objects.
- Whole-filesystem/KSU/SELinux relocatable LTO link with core objects. Both KSU
  and NoMount initcalls exist; SUSFS/KSU bridge symbols resolve.
- Full-feature debug/lockdep/KSU_DEBUG plus strong-stack-canary build; minimal
  SUSFS feature build; complete filesystem/KSU build with SUSFS disabled.
- KSU=n and KSU=m configuration dependency checks drop SUSFS. Disabled archive
  has NoMount but no susfs.o. Normal device configuration keeps all ten features.
- Normal and UBSan extracted-source tests: 256 authorization cases, 1792 KSU
  credential/unmount cases, 3010 readlink/hash/fault cases, 2404 pagemap cases,
  predicate and mount-ID ownership checks.
- Five deliberately broken host variants trigger runtime assertions: removed
  authorization, removed zygote guard, zero-byte readlink success, hash-key
  collision and freeing a borrowed mount ID. Source/config corruption tests
  reject missing files, tampering and dropped features.
- Existing NoMount integrity/host tests pass; its imported files are unchanged.
  KSU pin/security settings and earlier miatoll settings are preserved.

Generated local configurations retain the previous KSU test accommodations for
unavailable Polly and host signing dependencies. Source signing/verity options
were not disabled. Debug/KSU_DEBUG/canary changes are validation-output-only.

These are compile/link/config/model results, **not phone boot, actual working
root/metamodule, concurrent VFS/RCU/fsnotify, power-loss, benchmark, full vmlinux/
modpost/image or security-audit results**. No guarantee of device integrity-check
results or invisibility is made. No push or CI dispatch was performed.

## Android runtime setup and recovery

A compatible **SUSFS 2.3.0 userspace tool/module** is required separately after a
successful build and boot. Older SUSFS tools with a different ABI may not work.
Use the ARM64 management binary: compiling compat filesystem/syscall hooks is
not a claim of 32-bit SUSFS control-structure translation.
The backslashxx KSU manager remains the expected manager; a matching NoMount
metamodule/CLI is also still a separate Android installation. This kernel port
does not install either module/tool or configure runtime rules.

Use the installed SUSFS tool's help/read-only version/feature queries first and
check NoMount with its own `nm version` command. Verify unprivileged and capability-
limited callers cannot invoke SUSFS commands. On backed-up private test data,
exercise stat/statx/statfs, native/32-bit directory reads, short-buffer readlink,
proc fd/maps/smaps/rollup/pagemap, remote-memory permissions, module unmount,
mount namespace cloning/failure paths and reboot/shutdown. Real concurrency and
fsnotify lifecycle testing is still required.

Do not configure SUSFS and NoMount to hide/redirect/spoof the same path until
that combination is specifically tested; source coexistence is not proof of
correct overlapping runtime rules. Use only files/modules you are authorized
to administer. Keep a known-good boot image and recovery/fastboot path.

Rollback by disabling both Android modules before restoring the known-good
image, or rebuild with CONFIG_KSU_SUSFS=n. Do not run either project's installer
cleanup scripts on this vendored layout. Disabling SUSFS does not remove KSU
or NoMount; that combination was separately compiled locally.
