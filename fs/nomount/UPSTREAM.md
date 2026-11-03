# Vendored NoMount

- Upstream: https://github.com/maxsteeel/nomount
- Requested branch: `dev`
- Pinned commit: `04af0552bb29c7cee1b78c3eea69d7ed98b80bf2`
- Upstream commit subject: `kernel: drain reclaim work on shutdown`
- Source: `kernel/src/{Kconfig,Makefile,nomount.c,nomount.h}` and `kernel/LICENSE`
- Kernel API base version: `22`, unchanged from upstream.
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
