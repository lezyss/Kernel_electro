# Updated `16` foundation and carry-over audit

## Exact scope / safety status

**Foundation:** `lezyss/Kernel_electro:16`, pinned at
`766a32ab1c8b889ac049ccd367e82786e5953bc0`.

**Previous known CI-successful Electro tree:**
`402566a8597ae7f0ecf3f87054b77aa7c18acdf0`.

The working source has been changed to the exact updated `16` foundation,
not a blanket merge/replay of the old Electro source. The current branch name
is retained. The local history-preserving checkpoint joins the previous
Electro tip and pinned16 as parents, with16 supplying the source tree. Prior Electro work remains recoverable from the published commit
above; its historical receipts are not resealed to pretend they validate a
new source tree. The previous inventory is retained as a HISTORICAL checklist.

**This is the base-swap + audit checkpoint, NOT completion of the carry-over.**
Missing and conflicting old integrations have not been blindly restored.
KSU/FinaSU/NoMount/SUSFS, BBRv3/EDT, MGLRU/BORE and other Electro-specific work
must not be assumed present in the new foundation. The prior successful CI
result applies to402566a85, not to this new source. **Do not flash this checkpoint.**

User exclusions: do not carry over BBRplus. The SM8150 and Phoenix batches are
excluded from the old-Electro replay checklist, NOT deleted from the maintainer's
new foundation if it already contains them. No force push, other-branch change,
new CI dispatch or target/device validation is part of this checkpoint.

## Audit method and what it does NOT prove

`audit.json` covers all143 indexed inventory references:142 in review scope,
one explicitly excluded BBRplus row. Import/version pins are handled as source
presence/version checks rather than incorrectly applying an installer's commit
patch or an app's commit to the kernel.

For ordinary references, the recorded GitHub text hunks are checked in BOTH
forward and reverse directions against disposable minimal files copied from
pinned16. These probes run outside any Git checkout so `git apply` cannot
silently skip paths because of the current working directory. No donor patch
is applied to production sources. Partial/omitted API diffs are unresolved,
not successes. Full source semantics, dependency order and Electro's corrected
adaptations still need review; an exact patch-direction test alone is not a
safe decision to cherry-pick or overwrite code.

Mechanical first-pass totals:

| Result | References | Meaning |
|---|---:|---|
| Forward candidate |59| Donor hunks forward-apply; candidate missing change, NOT permission to copy the raw donor |
| Semantic review required |75| Neither direction establishes equivalence; dependencies or native differences must be checked |
| Missing import |5| Specific KSU/FinaSU/NoMount/SUSFS/BBRv3 source/import markers absent |
| Different codec, review required |1| LZ4 is updated but not equivalent to the previous kernel adaptation |
| Partial API diff |1| Consolidated BPF reference has omitted files/hunks; not treated as a pass |
| Metadata unresolved |1| Stream-parser reference could not be fetched from its recorded repository; not guessed |
| Excluded BBRplus |1| Explicit user exclusion; no port/config carried over |

There are no reverse-hunk matches in this mechanical donor-reference pass.
That does NOT mean the new base contains none of our work: for example the
ext4 dot-last check is in the separate native/local inventory and its entire
`fs/ext4/dir.c` is byte-identical to the previous Electro file.

See `features.json` for additional source-marker/file-hash probes. A missing
marker is evidence about that implementation, not proof that an unrelated
alternative implementation is incorrect. A present marker alone is NOT a
semantic equivalence proof. Each inventory reference is listed in `items.md`.

## Confirmed early findings

- No BBRplus source or Kconfig selection is present. It stays excluded.
- BBRv3's separate implementation is absent. Resolved base config uses `cubic`
  and `fq_codel`; this is NOT the prior `bbr3`/`fq` Electro profile.
- Vendored KSU, FinaSU's KSU adapter, NoMount and native SUSFS are absent.
- MGLRU/BORE source markers, native memlat async sampling and the optional
  F2FS GC/checkpoint merge implementation markers are absent.
- Ext4's dot-as-last-entry validation is present; `dir.c` matches old Electro.
  Its early inode-body xattr validation is not present in the inspected path.
- Host-GCC ARM64 miatoll Kconfig generation succeeds. This is not a target build.
- The new base's workflow invokes `scripts/ci/build-kernel.sh` and
  `scripts/ci/package-anykernel.sh`, but neither file exists in that pinned tree.
  Its build pipeline is not self-contained as checked in. Do not dispatch it
  and expect the old Electro build result to carry over.

## LZ4 review — version number alone is insufficient

The maintainer's header declares **1.11.1** (`MAJOR=1`, `MINOR=11`, `RELEASE=1`),
whereas previous Electro used an adapted1.11.0 snapshot. `lz4-base-sha256.json`
records the exact seven inspected files. This is a header claim, not independent
proof of the upstream release provenance of every file.

Confirmed integration problems in the pinned foundation:

1. `lib/decompress_unlz4.c` still includes `lz4/lz4_decompress.c` in its `STATIC`
   preboot branch, but that file no longer exists. Preprocessing that actual
   branch fails with the missing-file error. This establishes the branch is
   broken, not that every ordinary non-STATIC decompression build fails.
2. Kernel `LZ4HC_MEM_COMPRESS` is the plain/minimum262200-byte state, not the
  327784-byte extended workspace. `LZ4_compress_HC_extStateHC()` initializes
   only `sizeof(*ctx)` and the freestanding HC optimal parser contains its
   plain-state stack fallback. With native-style header shims, host GCC-O2
   reports a **65968-byte frame**, exceeding a2048-byte frame warning bound.
   High-HC-level/plain-state safety needs a real kernel workspace adaptation;
   this is not a claim that a shipped default level executed the path on-device.
3. No previous optional ARM64 LZ4 accelerator files are present. That is not
   automatically a codec correctness bug, but it is not equivalent feature
   coverage to the old adaptation.
4. The changed Kbuild layout and module exports need full kernel/consumer/link
   checks before declaring compatibility. Old codec tests/manifests cannot be
   resealed or counted as validating this different implementation.

The old1.11.0 codec was NOT copied wholesale over the maintainer's newer code.
The raw foundation is kept explicit so a subsequent small compatibility patch
can fix these issues without an unreviewed version downgrade. `results.log`
contains the actual local diagnostics. No ARM64 production compile/link, codec
cross-decoding or device execution was done for this foundation yet.

## Reproduce / next stage

The previous inventory and its evidence paths describe the402566a85 snapshot;
retrieve those exact files from that Git commit when reviewing native corrections.

```sh
# Objects may need fetching in a shallow checkout; this does not switch branches.
git fetch origin 766a32ab1c8b889ac049ccd367e82786e5953bc0
python3 tools/testing/selftests/base_sync/verify_foundation.py

# Read-only first-pass re-audit; downloads public commit metadata via gh.
python3 tools/testing/selftests/base_sync/audit_inventory.py \
  --foundation-root . \
  --inventory Documentation/dev-tools/electro-change-inventory-no-sm8150-phoenix.md \
  --cache .cache/base-sync-commits \
  --output .cache/base-sync-recheck.json
```

Next work is semantic/dependency review of the candidates, then scoped restoration
of wanted missing integrations and repair of the foundation's build/LZ4 issues.
Keep BBRplus out. Prefer existing maintainer implementations where equivalent;
retain native safety corrections rather than raw donor patches. Only after
that should the current models/config and exact AOSP production build be used
to qualify a replacement image. No missing item is marked restored here.
