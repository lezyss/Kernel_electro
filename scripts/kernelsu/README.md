# External KernelSU source (BakaSU)

KernelSU is not tracked in this kernel tree.  The source is fetched at
build time from `Baka-SU/BakaSU` so an upstream update does not become a
hundred-file kernel commit.

- Pin/fallback: `scripts/kernelsu/UPSTREAM.json` (`548d1dda`).
- Setup: `scripts/kernelsu/setup.sh`.
- Kconfig options: `drivers/ksu/Kconfig` is tracked so configuration works
  without a checkout; keep it in sync when updating.

## Build

Run the setup once per checkout (CI does this before the build).
NoMount is a separate external source: also run `scripts/nomount/setup.sh`
(see `scripts/nomount/README.md`).

```sh
scripts/kernelsu/setup.sh
scripts/nomount/setup.sh
```

By default `KSU_REF=latest`, which resolves the latest GitHub release
for `Baka-SU/BakaSU` (falling back to the verified commit in
`UPSTREAM.json` if unresolved).

Overrides:

```sh
KSU_REF=pinned scripts/kernelsu/setup.sh      # verified UPSTREAM.json commit (548d1dda)
KSU_REF=main scripts/kernelsu/setup.sh        # upstream development head
```

The checkout is placed in `KernelSU/` (gitignored), optional patches in
`scripts/kernelsu/patches/*.patch` are applied if present, and
`drivers/kernelsu` is created as an ignored symlink.

`scripts/kernelsu/setup.sh --cleanup` removes only the symlink.  Set
`KSU_DIR` to use a checkout outside the tree.
