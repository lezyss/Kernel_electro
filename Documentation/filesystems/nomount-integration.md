# NoMount integration for Electro (ARM64 4.14)

## Integrated revision and layout

NoMount's requested `dev` branch is pinned at:

```text
Repository: https://github.com/maxsteeel/nomount
Commit:     04af0552bb29c7cee1b78c3eea69d7ed98b80bf2
Subject:    kernel: drain reclaim work on shutdown
API base:   22
```

Its four `kernel/src/` files and `kernel/LICENSE` are vendored under
`fs/nomount/`. A normal kernel checkout contains everything required to compile
this driver. There is no nested Git repository, submodule or symlink, and CI
does not fetch NoMount. `fs/nomount/UPSTREAM.json` records source identity and
`UPSTREAM.md` explains local changes. NoMount C/header/license files are unchanged.

This kernel builds it in with CONFIG_NOMOUNT=y. The existing vendored KSU source
and configuration are preserved. No legacy KSU hooks or NoMount calls are added
to global namei/readdir/stat/input/SELinux paths. This NoMount revision registers
its keyring API, then intercepts operation vectors for paths configured by a
privileged userspace tool. No rules are preinstalled by this integration.

## Why not run the curl installer directly?

The supplied command downloads a moving installer and executes it immediately:

```bash
curl https://raw.githubusercontent.com/maxsteeel/nomount/refs/heads/dev/kernel/setup.sh | bash -
```

We inspected it instead. It clones `NoMount/`, resets that dependency's local
changes, selects/updates dev (falling back to master), creates a symlink to its
kernel source, and adds fs/Kconfig/Makefile entries. Its help mentions the latest
tag, but the inspected no-argument code actually selects a branch. It does not
make this layout a complete vendored import or verify device compatibility.

We used the same source at an exact pinned revision, copied the required files
as ordinary files, recorded provenance and selected the configuration explicitly.
No upstream installer or cleanup script was run.

## Learning recipe: import on a fresh tree

**Already integrated here. Do not rerun this over the existing fs/nomount.**
The following shows the equivalent import on a clean, unintegrated copy:

```bash
# Run from the kernel root and stop on errors.
set -e
NM_COMMIT=04af0552bb29c7cee1b78c3eea69d7ed98b80bf2
work=$(mktemp -d)

git clone --no-checkout https://github.com/maxsteeel/nomount "$work/nomount"
git -C "$work/nomount" checkout --detach "$NM_COMMIT"
test "$(git -C "$work/nomount" rev-parse HEAD)" = "$NM_COMMIT"

test ! -e fs/nomount && test ! -L fs/nomount
mkdir fs/nomount
cp -a "$work/nomount/kernel/src/." fs/nomount/
cp "$work/nomount/kernel/LICENSE" fs/nomount/LICENSE

git apply --check --directory=fs/nomount \
    Documentation/filesystems/nomount-compat.diff
git apply --directory=fs/nomount \
    Documentation/filesystems/nomount-compat.diff
```

The dependency checkout is outside the kernel; its detached checkout must never
switch the kernel's own working branch. Do not copy the dependency's `.git`.
Keep licenses. Only import the five files above, not Android release binaries.

Parent `fs/Makefile` needs exactly one entry:

```make
obj-$(CONFIG_NOMOUNT) += nomount/
```

Parent `fs/Kconfig` needs exactly one line before its final `endmenu`:

```kconfig
source "fs/nomount/Kconfig"
```

The applied miatoll selection can be reproduced with:

```bash
scripts/config --file arch/arm64/configs/vendor/xiaomi/miatoll_defconfig \
    --enable NOMOUNT --enable KEYS
```

KEYS already resolved to y in the previous miatoll build; it is now explicit.
NoMount Kconfig defaults to n for other configs and depends on KEYS, instead
of silently enabling a kernel redirection interface on every target.

## Local build adjustments

The compatibility diff changes only Kconfig and Makefile:

- Opt-in configuration plus the keyring dependency.
- No Git-history probe for versioning. Runtime uses upstream API base `22`;
  the full source revision is in committed provenance metadata.
- C11 remains enabled for declarations and cleanup-based scoped RCU guards.
- Preserve the kernel's optimization and stack-protection policy rather than
  forcing -O3 and -fno-stack-protector for this unit.
- Preserve upstream detection of this tree's downstream xattr_handler.__get ABI.

Miatoll currently uses shadow-call-stack and no stack-canary protector; this
integration does not change that global policy. Separate validation enabled
strong canaries and proved NoMount does not override them. KSU's own upstream
per-unit flags remain untouched.

When reproducing the import, also retain/regenerate the provenance files after
reviewing the compatibility diff. For example, after applying the diff:

```bash
python3 - "$work/nomount" "$NM_COMMIT" <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys
checkout, commit = sys.argv[1:]
files = {}
for name in ['Kconfig', 'Makefile', 'nomount.c', 'nomount.h', 'LICENSE']:
    remote = 'kernel/LICENSE' if name == 'LICENSE' else 'kernel/src/' + name
    blob = subprocess.check_output(
        ['git', '-C', checkout, 'rev-parse', commit + ':' + remote], text=True).strip()
    files[name] = {'path': remote, 'git_blob': blob}
driver = Path('fs/nomount')
manifest = {
    'repository': 'https://github.com/maxsteeel/nomount',
    'branch': 'dev', 'commit': commit,
    'upstream_files': files,
    'local_sha256': {
        name: hashlib.sha256((driver / name).read_bytes()).hexdigest()
        for name in ['Kconfig', 'Makefile']
    },
}
(driver / 'UPSTREAM.json').write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + '\n')
PY
```

Do not regenerate hashes merely to silence failed tests. Review source changes
and compatibility first. These hashes are an identity record, not a security
audit or signature-based endorsement of the project.

## Verify and build

Offline checks (no device interaction):

```bash
python3 tools/testing/selftests/nomount/test_integration.py
python3 tools/testing/selftests/kernelsu/test_integration.py
python3 tools/testing/selftests/nomount/test_integration.py --host-tests --cc clang
```

Use the existing full LLVM build script with the prepared AOSP r614150 toolchain:

```bash
TOOLCHAIN_DIR=/absolute/path/to/clang-r614150 \
    JOBS="$(nproc)" bash scripts/ci/build-kernel.sh

python3 tools/testing/selftests/nomount/test_integration.py --config out/.config
python3 tools/testing/selftests/kernelsu/test_integration.py --config out/.config
```

The build script invokes the integrity/configuration check after olddefconfig
when the selected defconfig requests NoMount. It stops if source is missing,
modified without recorded review, or NoMount/keyring settings did not survive
Kconfig resolution. No new fetch, installer invocation or workflow dependency
is required. This integration session did not push or dispatch CI.

## Android userspace is still required

Building the kernel backend does not install the Android NoMount metamodule,
its CLI, WebUI or other modules. After validating a bootable KSU kernel, install
a compatible NoMount userspace/metamodule version via the root manager. Prefer
a version matching this pinned source/API; future dev/nightly builds may change.
The installer detects the built-in API and should not need to load an LKM.
Do not load another NoMount LKM over this built-in backend.

After a successful boot/root setup, basic read-only status checks are:

```sh
su -c '/data/adb/modules/nomount/bin/nm version'
su -c '/data/adb/modules/nomount/bin/nm rule list'
```

Use the actual installed path if it differs. This NoMount `nm` is not the host
binutils symbol-listing tool of the same name. API requests require
CAP_SYS_ADMIN; integration does not remove the capability gate or disable
SELinux/seccomp. Runtime rule changes must be limited to your own authorized
files and modules. No rules or UID exclusions were configured by this session.

## Validation and outstanding work

Passed locally with Clang 19.1.7/LLD (Zig 0.14.1), not AOSP r614150:

- ARM64/ThinLTO NoMount driver object/archive in miatoll-derived configuration.
- Fresh debug/lockdep build with both NoMount and KSU enabled.
- Separate strong-stack-protector build; actual compile flags preserve it and
  shadow-call-stack. Downstream xattr __get ABI detected on all enabled builds.
- CONFIG_NOMOUNT=n gives no NoMount object; default-off and KEYS=n resolution
  correctly keep NoMount disabled.
- VFS and keyring dependency objects compiled; combined KSU/NoMount/VFS/SELinux/
  keyring ThinLTO relocatable link succeeded, with both initcalls present.
- Integrity checks; five deliberate source/dependency corruption controls.
- Extracted-source normal/UBSan tests: capability and pointer-length gate, UID
  bloom/list/RCU-scope behavior, range selection and native/compat readdir cookies.
  Four in-memory broken variants each compile and fail the expected assertion.
- All vendored KSU files unchanged; earlier device settings preserved.

Only generated validation configs disabled Polly and signature-related options
for unavailable local host dependencies, as in KSU validation. The source device
signing/verity settings are unchanged. Tests are single-threaded mocks, not real
keyring/page-pinning/VFS/RCU/mmap/shutdown executions. A relocatable partial link
is not vmlinux/modpost/image validation. No full production build, phone boot,
working-root/metamodule test, filesystem stress, power-loss test or performance
measurement has been performed. Upstream labels NoMount research/development.

Before flashing, keep a known-good boot image and working recovery/fastboot
route. Validate ordinary access, native/32-bit file operations, mmap, rule
add/delete/clear, concurrent IO, reboot/shutdown and module lifecycle using
backed-up test data. Verify the key API denies an unprivileged caller. Integration
is not a guarantee of invisibility or success of device-integrity checks.

Rollback: disable/uninstall the NoMount metamodule, restore a known-good kernel,
or rebuild with CONFIG_NOMOUNT=n and flash it. Deleting an Android module does
not remove a built-in kernel backend; do not use the upstream setup cleanup
script to remove this vendored implementation.
