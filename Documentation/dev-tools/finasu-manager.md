# FinaSU manager on the vendored backslashxx KSU

## What this changes (and does not change)

This adds **FinaSU as an alternative Android manager**, not the FinaSU kernel.
The driver remains backslashxx/KernelSU **v3.3.1-38**, commit
`feeec8e4059e3bb0ecdd1827b687b69f1cf4a2fb`, with its existing SUSFS 2.3.0
bridge and NoMount integration. No fork replacement, installer, build-time
fetch, extra SELinux grant or change to root/allowlist/unmount eligibility.

Only the exact production package **`me.yuki.fina`** is added. Its pinned APK
v2 certificate fingerprint is:

- Certificate length: **716 bytes (`0x2cc`)**.
- SHA-256: **`2d89b50aaf1db013c2b6738f973f48b62ea21a3a8d7216bfec3521065d448458`**.
- Source of this trust addition: the supplied manipvlator signature commit below.
- **No `.pr`, `.dev`, arbitrary suffix, custom/debug signing key or unrelated
  manager from that donor is added.** FinaSU's package must match FinaSU's key;
  it cannot fall back to one of the previously accepted manager keys. The
  original managers' preexisting signing policy is retained.

The release APK could not be downloaded here: GitHub release assets redirect
to a host outside the sandbox's allowed network hosts. **The current release
APK's certificate has not been independently fingerprinted here.** A key
rotation/re-signed APK will fail closed; do not disable verification to fix it.
Before testing an APK, use Android SDK build-tools on your own machine:

```sh
apksigner verify --verbose --print-certs /path/to/FinaSU-release.apk
```

Check the signer certificate SHA-256 against the value above, and verify the
package is `me.yuki.fina` (for example, with `apkanalyzer manifest application-id`).
The existing kernel parser pins certificate bytes; Android Package Manager
remains responsible for full APK signature/content verification and protected
`/data/app` installation. This change is not a new independent APK verifier.

## References and compatibility review

| Source | Use here |
| --- | --- |
| manipvlator/KernelSU `8640f74f7d5fabd7ba5a07e7652e0fd1084c2173` | FinaSU production package and certificate, not its other manager additions |
| manipvlator/KernelSU `da63482157550d46b2d6a5b3ba4c855ddd1d103a` | Read-only display ABI layouts, not per-manager numeric-version spoofing |
| manipvlator/KernelSU `0cfa13c758b7f8b68a3ed1ef11bc64186231f8f9` | Read-only configured-hook display queries, not false tracepoint/ready flags |
| LyraVoid/FinaSU `2d5786b9129a254a87ac358c8bec0203ccd53351` | Current manager JNI, UAPI and build/package review |

Release **v1.4.3** was also checked at its exact commit recorded in
`finasu-manager.json`: its JNI full-version ioctl uses a 64-byte output, its
minimum supported kernel number is **32513**, and its common UAPI is **6**.
The retained backslashxx **32717 / UAPI 6** meets that numeric minimum without
pretending to be a FinaSU kernel. Source-level agreement is not a device test.

The addition implements these display queries without changing existing ioctl
numbers/layouts, feature enumeration or the original GET_INFO/legacy handlers:

| Query | Wire layout | Access |
| --- | --- | --- |
| FinaSU full version | `_IOR('K', 29, struct { char version_full[64]; })` | Public, like GET_INFO |
| Donor-compatible full version | `_IOC(_IOC_READ, 'K', 100, 0)`, 255-byte output | Public |
| Version tag | `_IOC(_IOC_READ, 'K', 99, 0)`, 32-byte output | Active manager or root |
| Configured hook mode | `_IOC(_IOC_READ, 'K', 98, 0)`, 16-byte output | Active manager or root |
| Configured hook type | `_IOC(_IOC_READ, 'K', 101, 0)`, 32-byte output | Active manager or root |

Strings identify the actual driver: `v3.3.1-38-backslashxx-Electro`, tag
`v3.3.1-38`, and **`Manipulated`** for the miatoll syscall-table configuration.
Other configured branches report `Kprobes` or `Manual` as applicable. Buffers are
zero-initialized/NUL-terminated; copy faults return `-EFAULT`. The original
root-controlled version/flag override knobs are not altered by this overlay.

**No fake `33156`/FinaSU `v1.4.3` kernel identity**, dynamic-manager API,
GET_MANAGERS emulation, network-isolation/UTS spoofing APIs, tracepoint flag,
SUSFS-inline hook flag or unconditional runtime-ready bit is added. Our SUSFS
bridge does not turn backslashxx's syscall-table hooks into FinaSU's inline
hook implementation. A newer manager screen using only FinaSU hook flags may
show an unknown/not-reported hook mode; the reviewed HomeUiState treats an
unknown backend as not failed. The string queries describe configured hooks,
not runtime health. FinaSU-only feature pages are not a promise of support;
unimplemented commands retain `-ENOTTY`.

## Authentication and manager selection correction

The earlier tracker could verify one APK but crown the first eligible package
from `packages.list`. It also stopped at an unverified candidate and cached
paths before verification. Adding another package without fixing those paths
would be unsafe/unreliable.

Now selection proceeds as follows:

1. Match an existing supported package or exact `me.yuki.fina` directory.
2. Verify that candidate's accepted certificate (FinaSU has its own exclusive key).
3. Extract that same APK's package and find its **exact** entry in `packages.list`.
4. Only then publish its normalized app ID, cache its path and stop the scan.
5. Failed certificate/package binding continues scanning later candidates.
6. On a non-prune package refresh, reverify the active cached APK and rebind its
   exact package UID; a path merely existing is not proof of authentication.
   Invalidate a stale selection before searching again.

The single app-ID identity uses READ_ONCE/WRITE_ONCE and existing per-Android-user
UID normalization. These operations avoid torn/duplicated scalar accesses;
they are not a claim of lock-free atomicity for the complete VFS/package update.

**There is still only one active manager app ID.** If the old manager remains
installed and valid, it keeps its active slot. FinaSU is an alternative, not a
second simultaneously privileged manager. To switch, first verify/install the
trusted FinaSU APK, then uninstall the previous active manager and let the
package observer rescan (reboot if needed). Do not expect both apps to have
manager privileges. Keep a known-good boot image and a recovery route.

No APK, userspace daemon, module or runtime rule is installed by this source
change. Manager-driven changes to ksud/metamodules still need device testing;
FinaSU's kernel-specific features are not imported automatically.

## Commands to inspect, check and build

These changes are **already applied**. Do not reapply the overlay to this tree.

```sh
# Inspect the exact six-source delta over the completed KSU+SUSFS integration.
git apply --stat Documentation/dev-tools/finasu-manager.diff

# Offline provenance/source/configuration checks; no compiler/network required.
python3 tools/testing/selftests/kernelsu/test_integration.py
python3 tools/testing/selftests/kernelsu/test_finasu.py
python3 tools/testing/selftests/susfs/test_integration.py
python3 tools/testing/selftests/nomount/test_integration.py

# Host models extract the production functions and mock VFS/credentials/certs.
python3 tools/testing/selftests/kernelsu/test_finasu.py \
    --host-tests --negative-tests --cc clang
python3 tools/testing/selftests/kernelsu/test_finasu.py \
    --host-tests --cc 'clang -fsanitize=undefined -fno-sanitize-recover=all'

# Production build: keep the previously selected pinned AOSP r614150 toolchain.
TOOLCHAIN_DIR=/absolute/path/to/clang-r614150 JOBS="$(nproc)" \
    bash scripts/ci/build-kernel.sh
```

The CI script now preflights this overlay when KSU is selected. No CI run or
push is performed by adding that check.

`finasu-manager.json` records the six preimage/postimage SHA-256s and reference
pins. `finasu-manager.diff` applies only to the **pre-FinaSU, already-SUSFS**
state. It excludes tests/docs/provenance updates. Reproduction order is original
KSU compatibility patch, SUSFS patch, then this manager patch. All are historical
overlays, not patches to apply again to the current tree.

SUSFS's original 32 postimages and integration patch are preserved. Its checker
verifies the one shared file (`supercall/dispatch.c`) through the FinaSU
manifest's exact preimage-to-postimage chain. The overall KSU manifest records
**15 local overrides and 89 byte-identical upstream files**, still 104 imports.

## Validation and remaining work

Local Clang 19.1.7/LLD from Zig 0.14.1 (not production AOSP Clang 23):

- Warning-free ARM64 KSU builds with full/minimal/debug/SUSFS-disabled configs.
- Latest complete filesystem/KSU/SELinux/core whole-archive **relocatable
  ThinLTO link**; SUSFS bridge dependencies resolved and both root integrations
  retained. This is not vmlinux/modpost or a bootable image.
- Offline KSU/FinaSU/SUSFS/NoMount checks together; source/patch/preservation checks.
- Extracted-source host tests: 937 syscall-table, 937 branch-link, 945 kprobes
  and 947 manual-hook checks, also under nonrecovering UBSan. They exercise
  exact package/key selection, suffix rejection, UID binding/list ordering,
  invalid-candidate continuation, verified-only caching, multi-user app IDs,
  ioctl sizes, zero-fill, boundaries and copy-fault behavior.
- Six deliberately broken variants are rejected at runtime: certificate bypass,
  wrong package UID, early scan stop, unverified cache, wrong 64-byte ABI,
  ignored copy fault.

Not tested here: real FinaSU APK certificate, installed Android manager/ksud,
root prompts/profiles/modules, package-update races, actual concurrent VFS
behavior, phone boot or overlapping SUSFS/NoMount rules. These tests use mocked
certificate-parser results, not forged or real signed APKs. No full production
image, flash, device test, push or CI dispatch has been performed for this change.

The original FinaSU JSON/diff remains the historical +36 overlay. The
[v3.3.1-38 KSU update](kernelsu-updates/v3.3.1-38.md) succeeds only its two
dispatch version labels; the checker reconstructs and verifies the immutable
old dispatch hash, prohibiting any authorization-body changes.
