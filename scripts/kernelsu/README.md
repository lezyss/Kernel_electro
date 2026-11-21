# External KernelSU source

KernelSU is not tracked in this kernel tree.  The source is fetched and
adapted at build time so an upstream update does not become a hundred-file
kernel commit.

- Pin/fallback: `scripts/kernelsu/UPSTREAM.json`.
- Local adaptations: `scripts/kernelsu/patches/0001-electro-adaptations.patch`.
- Setup: `scripts/kernelsu/setup.sh`.
- Kconfig options: `drivers/ksu/Kconfig` is tracked so configuration works
  without a checkout; it mirrors the pinned upstream Kconfig plus the
  Electro/SUSFS options.  Keep it in sync when updating.

## Build

Run the setup once per checkout (CI does this before the build).
NoMount is a separate external source: also run `scripts/nomount/setup.sh`
(see `scripts/nomount/README.md`).

```sh
scripts/kernelsu/setup.sh
scripts/nomount/setup.sh
```

By default `KSU_REF=latest`, which resolves the latest non-prerelease
GitHub release for `backslashxx/KernelSU` and checks out that tag.  If the
release cannot be resolved, the script falls back to the commit in
`UPSTREAM.json` with a warning.

Release tags are not parsed or pattern-matched: the GitHub releases API
returns the tag name, which is checked out as-is.  Upstream has used both
`-NN` and `+NN` suffixes, so do not infer the tag format.

Overrides:

```sh
KSU_REF=pinned scripts/kernelsu/setup.sh      # verified UPSTREAM.json commit
KSU_REF=v3.3.1-54 scripts/kernelsu/setup.sh   # exact release
KSU_REF=master scripts/kernelsu/setup.sh      # upstream development head
```

The checkout is placed in `KernelSU/` (gitignored), the patch series is
applied, and `drivers/kernelsu` is created as an ignored symlink.  If the
patch no longer applies to a newly published release, setup stops with the
failing file instead of silently dropping the Electro/SUSFS adaptations.
Use `KSU_REF=pinned` to keep building while refreshing the patch.

`scripts/kernelsu/setup.sh --cleanup` removes only the symlink.  Set
`KSU_DIR` to use a checkout outside the tree.

## Updating the verified pin/patch

1. Run setup against the new release and inspect patch conflicts.
2. Rebase `patches/0001-electro-adaptations.patch` onto that tag.
3. Sync `drivers/ksu/Kconfig` if upstream options changed.
4. Update `tag`, `commit`, blob hashes and local SHA-256 records in
   `UPSTREAM.json`.
5. Run a defconfig/build check.

Normal builds follow the latest release automatically; the pin remains a
reproducible fallback (`KSU_REF=pinned`) and the CI override input.
SUSFS kernel files and hooks remain tracked in this tree; only the
KernelSU/NoMount source is external.
