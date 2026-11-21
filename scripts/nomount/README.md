# External NoMount source

NoMount is not tracked in this kernel tree.  `scripts/nomount/setup.sh`
fetches `maxsteeel/nomount` into the gitignored `NoMount/` directory and
links its source files into `fs/nomount`.

- Pin: `scripts/nomount/UPSTREAM.json`.
- Local Makefile adaptation: `scripts/nomount/patches/0001-electro-makefile.patch`.
- Tracked Kconfig: `fs/nomount/Kconfig` (needed while Kconfig is parsed,
  before a checkout exists).
- Setup: `scripts/nomount/setup.sh`.

## Build

Run both setup scripts once per checkout (CI does this before the build):

```sh
scripts/kernelsu/setup.sh
scripts/nomount/setup.sh
```

The default `NOMOUNT_REF=pinned` uses the verified commit in
`UPSTREAM.json`.  Other modes:

```sh
NOMOUNT_REF=latest scripts/nomount/setup.sh      # newest GitHub release
NOMOUNT_REF=v2.3.1 scripts/nomount/setup.sh      # explicit release
NOMOUNT_REF=dev scripts/nomount/setup.sh         # upstream branch
```

`NOMOUNT_REF=latest` is not build-verified on this 4.14 tree; the pinned
commit is the safe default.  Set `NOMOUNT_DIR` to use another checkout.

The script removes old links before updating, so a failed fetch or patch
leaves `fs/nomount` without source and the kernel build stops at the guard
in `fs/Makefile` instead of building stale code.

`scripts/nomount/setup.sh --cleanup` removes only the links.

## Updating the pin

1. Run setup against the candidate commit or release.
2. Refresh `patches/0001-electro-makefile.patch` if upstream changed its
   Makefile.
3. Update `commit`, upstream blob IDs and local SHA-256 records in
   `UPSTREAM.json`.
4. Run a defconfig and build check.

Only the NoMount source is external.  Its Kconfig remains tracked, and
SUSFS remains part of the kernel tree.
