# Vendoring backslashxx/KernelSU into Electro

## What is integrated

- Fork: <https://github.com/backslashxx/KernelSU>
- Selected tag: `v3.3.1+36`
- Exact commit: `cbc0b49908066e9c7f778737f65a216f50b203ba`
- Location: `drivers/kernelsu/`, containing ordinary tracked source files.
- Target: built-in KSU on ARM64 miatoll, Linux 4.14; native and compat hooks.

There is no nested Git repository, submodule, symlink, installer invocation or
KSU network fetch in the kernel build. A normal checkout includes the driver.
The tag is a version label, not a claim that this fork was independently audited
or that the device has booted it.

**The integration is already done in this working tree. Do not rerun the import
commands over it.** They are a learning/reproduction recipe for an unintegrated
copy of the kernel. Preserve existing work first; do not reset unrelated work.
Updating KSU later requires reviewing changes, rebasing the local compatibility
patch and updating the recorded hashes, not deleting/recloning it blindly.

## Subsequent SUSFS overlay

The current tree also includes a corrected SUSFS 2.3.0 bridge, without replacing
the backslashxx base above. This guide describes the initial KSU import stage;
a fresh reproduction must additionally follow
`Documentation/filesystems/susfs/integration.md` before using the current complete
source manifests/checks. The SUSFS stage recorded ten KSU overrides. The
subsequent FinaSU-manager overlay is documented in `Documentation/dev-tools/finasu-manager.md`; follow it
after SUSFS when reproducing the current tree. There are now 15 local overrides
and 89 files retaining their original upstream blob identity.
Do not regenerate the old three-file-only manifest over the current one.

## 1. Download a specific revision outside the kernel tree

From the kernel source root, on a development machine with Git:

```bash
KSU_COMMIT=cbc0b49908066e9c7f778737f65a216f50b203ba
work=$(mktemp -d)

git clone --no-checkout https://github.com/backslashxx/KernelSU "$work/KernelSU"
git -C "$work/KernelSU" checkout --detach "$KSU_COMMIT"
test "$(git -C "$work/KernelSU" rev-parse HEAD)" = "$KSU_COMMIT"
```

`--detach` chooses an exact commit in the temporary **dependency checkout**; it
must not switch the Electro kernel's working branch. Cloning outside the kernel
keeps the dependency's `.git` directory out of the imported source. We imported
from GitHub's archive of this same exact commit and verified every imported Git
blob ID against that commit's tree; the resulting source is equivalent.

## 2. Copy only the driver source and licenses

```bash
# Stop if another integration already exists. Do not overwrite it.
test ! -e drivers/kernelsu && test ! -L drivers/kernelsu
mkdir drivers/kernelsu
cp -a "$work/KernelSU/kernel/." drivers/kernelsu/
```

Use a shell that stops on errors (`set -e`), or execute and check these steps
individually. The guard is not permission to erase an existing driver.
`kernel/.` copies the driver and its licenses, including its embedded preinit
runner's source/data. It does not copy the repository's `.git`, Android manager,
website, or unrelated userspace development tree.

**Do not run the imported `setup.sh`.** That script implements a clone/symlink
layout and is not how this vendored integration is installed or removed.

## 3. Apply the three local compatibility adjustments

This kernel repository contains the reviewed patch:

```bash
git apply --check --directory=drivers/kernelsu \
  Documentation/dev-tools/kernelsu-vendored-compat.diff
git apply --directory=drivers/kernelsu \
  Documentation/dev-tools/kernelsu-vendored-compat.diff
```

These commands are for a pristine import, not the already-adapted driver.

The changes are deliberately small:

1. Make `CONFIG_KSU` default **n** so unrelated defconfigs are not implicitly
   rooted. Miatoll enables it explicitly.
2. Generate a private pair of SELinux class headers before compiling `ksu.o`.
   Otherwise a clean/parallel build can fail because `security/selinux/flask.h`
   has not been generated yet.
3. Get `UTS_MACHINE` from Kbuild instead of depending on the generated
   `compile.h` side effect of compiling `init/version.o`.

All other imported files remain byte-identical to the pinned upstream blobs.
Do not copy archived generic KernelSU manual hooks into exec/read/stat/input on
top of this fork's syscall-table/LSM implementation.

## 4. Connect the driver to Kbuild and Kconfig

The parent `drivers/Makefile` needs exactly one entry:

```make
obj-$(CONFIG_KSU) += kernelsu/
```

`drivers/Kconfig` needs exactly one source line, inside the Device Drivers menu
before its final `endmenu`:

```kconfig
source "drivers/kernelsu/Kconfig"
```

An example command to add those entries without duplicating them:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('drivers/Makefile')
s = p.read_text()
line = 'obj-$(CONFIG_KSU) += kernelsu/'
if line not in s:
    p.write_text(s + '\n' + line + '\n')
p = Path('drivers/Kconfig')
s = p.read_text()
line = 'source "drivers/kernelsu/Kconfig"'
if line not in s:
    head, endmenu, tail = s.rpartition('endmenu')
    if not endmenu:
        raise SystemExit('Expected final drivers menu not found')
    p.write_text(head + line + '\n\n' + endmenu + tail)
PY
```

## 5. Select the miatoll configuration

These are the settings applied to
`arch/arm64/configs/vendor/xiaomi/miatoll_defconfig`:

```bash
scripts/config --file arch/arm64/configs/vendor/xiaomi/miatoll_defconfig \
  --enable KSU \
  --enable KSU_TAMPER_SYSCALL_TABLE \
  --enable KSU_LSM_SECURITY_HOOKS \
  --enable KSU_ENABLE_FULL_UID_CHECKS \
  --enable KSU_FEATURE_SULOG \
  --disable KSU_KPROBES_KSUD \
  --disable KSU_HACK_ARM64_BRANCH_LINK \
  --disable KSU_DISABLE_32BIT_HOOKS \
  --enable KSU_FEATURE_ADBROOT \
  --disable KSU_HOSTSREDIRECT \
  --disable KSU_THRONE_TRACKER_ALWAYS_THREADED \
  --disable KSU_NOPRINTK \
  --disable KSU_SHELL_HAS_SU_ALWAYS \
  --disable KSU_DEBUG
```

- `KSU=y`: build into the kernel, not an LKM that needs loading.
- `KSU_TAMPER_SYSCALL_TABLE=y`: the fork's own Kconfig recommends this method
  for 3.0--4.14; it is still runtime table hooking and must be tested on-device.
- LSM hooks stay on; SELinux is not disabled or made permissive by this config.
- Full UID checks retain an allowlist check for every non-root UID instead of
  the fork's faster shell-only gate. SU logging stays on for troubleshooting.
- `KSU_DISABLE_32BIT_HOOKS=n`: keep compat hooks for 32-bit Android processes.
- `KSU_FEATURE_ADBROOT=y`: include the existing backslashxx ADB-root feature,
  explicitly approved on 2026-11-07. Its runtime toggle still initializes off;
  compilation does not automatically activate ADB root or guarantee ROM support.
  This newly enabled configuration has not yet been target-built or device-tested.
- No unconditional shell SU, hosts redirection, branch-link hooking, deprecated
  KSU kprobes mode or KSU debug mode is enabled.
- Global kernel KPROBES, seccomp, read-only protections, and other device tuning
  are not disabled. The existing SELinux/SECCOMP/COMPAT settings are retained.

The resolved `.config` must retain KALLSYMS=y, SELinux, seccomp and these selected
KSU settings after Kconfig resolves dependencies. A defconfig line alone does
not prove that its setting survives `olddefconfig`.

## 6. Record provenance (not an embedded Git repository)

`drivers/kernelsu/UPSTREAM.md` explains the integration. `UPSTREAM.json` records
all 104 upstream Git blob IDs plus SHA-256 overrides for the three adapted
files. For this pristine-import recipe, it can be generated after step 3:

```bash
python3 - "$work/KernelSU" "$KSU_COMMIT" <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys
checkout, commit = sys.argv[1:]
listing = subprocess.check_output(
    ['git', '-C', checkout, 'ls-tree', '-r', commit + ':kernel'], text=True)
blobs = {}
for line in listing.splitlines():
    info, name = line.split('\t', 1)
    mode, kind, blob = info.split()
    if kind != 'blob':
        raise SystemExit('Unexpected non-file in driver tree')
    blobs[name] = blob
driver = Path('drivers/kernelsu')
changed = ['Kconfig', 'Makefile', 'kernel_includes.h']
manifest = {
    'repository': 'https://github.com/backslashxx/KernelSU',
    'tag': 'v3.3.1+36',
    'commit': commit,
    'upstream_subdirectory': 'kernel',
    'git_blob_sha1': blobs,
    'local_sha256': {
        name: hashlib.sha256((driver / name).read_bytes()).hexdigest()
        for name in changed
    },
}
(driver / 'UPSTREAM.json').write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + '\n')
PY
```

Do not regenerate hashes just to silence a failed integrity check. Inspect and
review the changed source first. Recorded hashes provide reproducibility, not
a substitute for trusting/reviewing the code.

## 7. Verify, build, then inspect the resolved config

The repository includes an offline integration check:

```bash
python3 tools/testing/selftests/kernelsu/test_integration.py
```

Build with the existing full-LLVM script and the pinned AOSP r614150 toolchain:

```bash
# TOOLCHAIN_DIR must point to the actual prepared AOSP toolchain directory.
TOOLCHAIN_DIR=/absolute/path/to/clang-r614150 \
  JOBS="$(nproc)" bash scripts/ci/build-kernel.sh

python3 tools/testing/selftests/kernelsu/test_integration.py --config out/.config
grep '^CONFIG_KSU' out/.config
```

The existing workflow obtains the pinned AOSP toolchain and runs this build
script. Its new preflight checks the vendored source and KSU configuration
before the kernel build; it does not download KSU. This session did not push,
dispatch CI or execute the full production build.

Before committing on the existing working branch, review the driver, parent
Makefile/Kconfig, miatoll config, compatibility patch, provenance, guide,
integration test and CI preflight. Do not commit build outputs or a temporary
clone. A useful check for accidental embedded repositories is:

```bash
find drivers/kernelsu -name .git -print
# Expected: no output.
git diff --check -- drivers/Makefile drivers/Kconfig \
  arch/arm64/configs/vendor/xiaomi/miatoll_defconfig scripts/ci/build-kernel.sh
```

Upstream source formatting is retained; it contains pre-existing whitespace and
aggressive compiler-warning/stack-protection choices. This integration is not
an audit or endorsement of every upstream implementation decision.

## Validation performed locally

Clang 19.1.7/LLD (Zig 0.14.1), not the production AOSP r614150 compiler:

- Device-derived ARM64/ThinLTO driver object and built-in archive: PASS.
- Related exec/open/stat/read, reboot, input, native/compat syscall tables and
  SELinux objects: compile PASS; combined relocatable ThinLTO partial link PASS.
- Fresh debug/lockdep output tree: standalone driver builds without either
  init/version.o's compile.h or security/selinux's generated flask.h: PASS.
- Separate CONFIG_KSU=n output: no driver object produced: PASS.
- Vendored-file/provenance checks and five deliberate corruption/policy negative
  controls: PASS.

Only generated local validation configs disabled Polly and module/verity
signature-related options to work around unavailable host OpenSSL development
files. The device defconfig keeps its original signing/verity settings. Tests
are not a full vmlinux/modpost/image build, boot, working-root test, authorization
stress test, security audit, or a guarantee of recovery behavior.

## First boot precautions

Keep a known-good boot image/flashable kernel and a working recovery/fastboot
route before flashing. Built-in KSU changes the kernel; uninstalling an Android
app does not remove it. To disable it, rebuild with CONFIG_KSU=n and flash that
kernel (or restore the known-good kernel), not the upstream setup cleanup script.

Use a manager APK compatible with this fork/revision and its expected signing
identity. The imported Makefile records the expected package/signature; do not
bypass manager signature checks to get an arbitrary APK working. A vendored
kernel driver does not install the Android manager application by itself.

After a successful boot, check kernel version, KSU status in the manager,
SELinux enforcing state, normal apps, 32-bit apps, reboot and recovery behavior.
Grant root only to a trusted test shell/app, then test `su -c id`. No such device
tests have been performed by this integration session.
