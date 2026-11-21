# External KernelSU source

KernelSU is intentionally not tracked in this kernel tree.  The pinned
source is fetched and adapted at build time so an upstream update does not
turn into a hundred-file kernel commit.

- Pin: `scripts/kernelsu/UPSTREAM.json` (`commit`, upstream blob IDs and
  local adaptation hashes).
- Local adaptations: `scripts/kernelsu/patches/0001-electro-adaptations.patch`.
- Setup: `scripts/kernelsu/setup.sh`.
- Kconfig options: `drivers/ksu/Kconfig` is tracked so configuration works
  without a checkout; it mirrors the pinned upstream Kconfig plus the
  Electro/SUSFS options.  Keep it in sync when bumping the pin.

## Build

Run the setup once per checkout (CI does this automatically before the
build):

```sh
scripts/kernelsu/setup.sh
```

This clones `https://github.com/backslashxx/KernelSU` into `KernelSU/`
(gitignored), checks out the pinned commit, applies the patch series and
creates the ignored `drivers/kernelsu` symlink.  Building with a
`CONFIG_KSU` value without running setup stops with a clear Makefile
error instead of silently omitting KernelSU.

`scripts/kernelsu/setup.sh --cleanup` removes only the symlink.  Set
`KSU_DIR` to use a checkout outside the tree.

## Updating the pin

1. Change `commit` in `UPSTREAM.json`.
2. Rebase `patches/0001-electro-adaptations.patch` onto that revision.
3. Sync `drivers/ksu/Kconfig` if upstream options changed.
4. Refresh the blob/hash records in `UPSTREAM.json`.
5. Run setup and a defconfig/build check.

Do not add `KernelSU/` or `drivers/kernelsu/` to Git.  SUSFS kernel files
and hooks remain tracked in this tree; only the KernelSU/NoMount source is
external.
