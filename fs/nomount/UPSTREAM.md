# Vendored NoMount

- Upstream: https://github.com/maxsteeel/nomount
- Requested branch: `dev`
- Pinned commit: `5e9feb6f3fce42423f56b37e344052c59ec16b66`
- Upstream commit subject: `module: prefer ksud/apd insmod over lkmloader during install` (kernel source pinned at this repository revision)
- Source: `kernel/src/{Kconfig,Makefile,nomount.c,nomount.h}` and `kernel/LICENSE`
- Kernel API base version: `23`, unchanged from upstream.
- License: retained GPL-2 license in `LICENSE`.

This is a real `fs/nomount/` directory, not a symlink, submodule, nested clone or
network-fetched build dependency. No upstream setup script was executed.
`UPSTREAM.json` records Git blob IDs and hashes of the locally adapted files.
Recorded identity is not an independent security audit of upstream code.

## Local changes

- `Kconfig`: default n to keep unrelated configs opt-in; depends on KEYS because
  the communication API registers a Linux key type. Miatoll explicitly enables
  CONFIG_NOMOUNT=y and CONFIG_KEYS=y.
- `Makefile`: remove the checkout-dependent Git version probe; keep upstream's
  fallback base version and record the exact revision here instead. Use C11 and
  the existing downstream xattr __get detection, but do not override kernel
  optimization/stack protection with upstream's -O3 -fno-stack-protector.
- `nomount.c`, `nomount.h` and `LICENSE`: byte-identical to the pinned upstream.

Exact adaptations: `Documentation/filesystems/nomount-compat.diff`.
Instructions and validation limits: `Documentation/filesystems/nomount-integration.md`.

No KSU source or global VFS hook was changed. NoMount uses its own capability-
gated keyring API and changes operation vectors for configured paths at runtime.
It is passive until a privileged tool configures rules. It is not a promise of
invisibility, passing integrity checks, absence of conflicts, or safe runtime
behavior. Upstream marks this VFS-layer project as research/development.

The Android NoMount userspace/metamodule is NOT installed by this kernel import.
Use a compatible version after building/flashing and validating the KSU kernel.
Do not try to load an additional NoMount LKM over this built-in implementation.

## v2.3 update

The dev branch is retained (not switched to master); see
Documentation/filesystems/nomount-update-23.md and its additive receipt/patch.
Only the C/header and provenance advance; Kconfig and hardened Makefile remain
unchanged. Source version23 is not evidence that a v2.3 userspace/module is
installed. List continuation now uses an explicit completion sentinel, so use
matching userspace for rule management. No install script or module binary was
run, and no rules or bypass UIDs were preconfigured by this source update.
