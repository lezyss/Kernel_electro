# Vendored KernelSU driver

- Fork: https://github.com/backslashxx/KernelSU
- Tag: `v3.3.1+36`
- Commit: `cbc0b49908066e9c7f778737f65a216f50b203ba`
- Imported directory: `kernel/` (104 files, including licenses and preinit runner source/data)
- License: GPL-2.0-only; see `LICENSE` and retained component license notices.
- Storage: ordinary files under `drivers/kernelsu/`, not a symlink, submodule,
  embedded Git repository, or a dependency downloaded at build time.

`UPSTREAM.json` records each upstream Git blob ID and the SHA-256 of the 15
locally adapted files (including the SUSFS and FinaSU-manager overlays). These
hashes record source identity, not a security audit or independent signature
verification of the fork.

## Local adaptations

1. `Kconfig`: make the top-level KSU option default **n**. Miatoll explicitly
   selects it; merely sourcing this Kconfig must not root unrelated defconfigs.
2. `Makefile`: generate private `flask.h` and `av_permissions.h` with this kernel's
   SELinux genheaders tool. Depend on the private flask header before compiling
   ksu.o, and use the local classmap as an input. This avoids depending on a
   parallel security/selinux build. Define UTS_MACHINE from Kbuild's exported
   value, avoiding an unrelated init/version.o header-generation dependency.
3. `kernel_includes.h`: remove the generated/compile.h include; its only required
   macro here, UTS_MACHINE, is now supplied by Kbuild.

The original three compatibility adjustments are stored in
`Documentation/dev-tools/kernelsu-vendored-compat.diff`. The subsequent corrected
SUSFS bridge is recorded in `Documentation/filesystems/susfs/integration.diff`,
with provenance and explanation alongside it. It is adapted from manipvlator/KernelSU
commit fcd50c8f367c470fa8e17eb64fbb8c7ce7527061, NOT a switch to that fork.
The original backslashxx revision, manager authentication, native/compat hooks
and setuid handler are retained. SUSFS adds CAP_SYS_ADMIN-gated commands and
extra unmount paths behind the existing eligibility/zygote/denylist checks.
All 89 imported files without local overrides are byte-identical to the pinned
upstream Git blobs. Do not reformat them as
part of an update without recording the resulting local changes.

The subsequent FinaSU-manager overlay is recorded separately in
`Documentation/dev-tools/finasu-manager.{md,json,diff}`. It adds only the
production FinaSU package/key, binds verified APKs to their exact package UID,
revalidates cached selection and implements read-only version/configured-hook
queries. It retains one active manager and the real numeric backslashxx version;
no switch to a FinaSU kernel or new bypass of signature checks.

## Policy and use

The miatoll configuration builds KSU into the image, uses the fork's syscall-table
hook implementation (recommended by that revision for 3.0--4.14), retains LSM
hooks and 32-bit compat hooks, enables full UID checking and SU logging, and does
not enable unconditional shell SU, the ADB-root feature, branch-link hooks,
deprecated KSU kprobes hooks, hosts redirection or KSU debug mode. Global kernel
KPROBES, SELinux, seccomp and read-only protection settings are not disabled.
No legacy manual hooks have been added to exec/read/stat/input/SELinux code.

The upstream `setup.sh` is retained for source completeness, but is **not used**
by this vendored integration. Do not run it from here or add it to CI.
It implements a different clone/symlink layout and can select moving revisions.
Do not use its cleanup option to uninstall this vendored copy.

See `Documentation/dev-tools/kernelsu-vendoring.md` for commands, build checks,
manager expectations and recovery precautions. Vendoring a root implementation
is not a guarantee of its security, compatibility, working root or a successful
boot. Root access intentionally changes the device's security model.
