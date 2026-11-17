# VMA recency and POSIX_FADV_NOREUSE backport

## Approved sources and ordering

1. `9933074572034a9353fbed9fd75761164b5d42e4` — add `vma_has_recency()`
   (upstream origin `8788f6781486769d9598dcaedc3fe0eb12fc3e59`).
2. `13b6149f8f0ccff490045990190655c1b284c24c` — support `POSIX_FADV_NOREUSE`
   (upstream origin `17e810229cb3068b692fa078bd9b3a6527e0866a`).

Both are from `Fucking-Projekt/android_kernel_xiaomi_stone`. The second donor's
parent is the first donor. Exact GitHub commit responses, including donor file
patches, are retained under `donors/` and hashed in this stage's manifest.

This stage follows published Electro commit
`a4f0c77b8d9d01e147aad1d1c9b3261f2ba04bce`. Only six existing source files change:
`include/linux/{fs,mm_inline}.h` and `mm/{fadvise,memory,rmap,vmscan}.c`.
No defconfig/default, syscall number, LZ4 code or unrelated backport changes.
The previous MGLRU repair and the ARM64 LZ4 1.11.1 restoration are retained.

## Adaptations to this 4.14 tree

* Add the unused `FMODE_NOREUSE` bit (`0x800000`) and a shared, configuration-
  independent `vma_has_recency()` helper. A mapping lacks recency if it has
  `VM_SEQ_READ`, `VM_RAND_READ`, or a backing file description with NOREUSE.
  A NULL `vm_file` is safe. The lockless file-mode load uses `READ_ONCE`, a small
  adaptation from the donor's ordinary load; writers retain `f_lock`.
* Adapt advice handling to this tree's `ksys_fadvise64_64()` / `struct fd`, not
  the donor's `generic_fadvise()`. NOREUSE sets the mode under `f_lock` without
  changing readahead, draining LRU queues or evicting cached pages. NORMAL
  restores default readahead and clears RANDOM and NOREUSE under `f_lock`.
  RANDOM/SEQUENTIAL do not independently reset NOREUSE, matching the donor.
  Existing error handling and DAX/noop-backing-device no-op handling remain.
* Use the helper in the unmap accessed-bit path. Install the reverse-map
  `invalid_vma` callback unconditionally so it filters global reclaim as well
  as memcg reclaim. Skip no-recency VMAs before counting references, including
  the huge-page path; retain filtering of other memcgs only when a non-NULL
  target memcg was supplied. Do not add the donor's unsupported `try_lock`
  structure field or replace native page/anonymous-VMA locking.
* Preserve native MGLRU look-around, page-young/idle tracking, VM_LOCKED
  processing and failed-page-trylock fallback for eligible mappings.
* Unlike a literal donor cherry-pick, also wire the helper into this tree's
  MGLRU fault placement and `should_skip_vma()` aging filter, and normalize the
  existing look-around guard. Keep all other accessibility, special/locked/
  hugetlb, swap, shmem, mapping-unevictable and readpage capability checks.

The advice is per **open file description**, not a byte-range eviction request:
`dup()`-style shared descriptions share it; independently opened descriptions
need not. It neither disables readahead nor changes ordinary buffered-read
`mark_page_accessed()` calls. Another eligible mapping can still contribute a
reference to the same page. These are application-driven hints, not an automatic
system-wide speedup. Donor benchmark gains do not establish miatoll gains.

## Validation and limits

`tools/testing/selftests/mm_recency/test_backport.py` extracts the actual
production helper, complete fadvise implementation, reverse-map reference and
filter functions, unmap reference condition, MGLRU fault entry/exit and aging
filter. It compiles those functions against small host stubs, not against or
inside the running host kernel. Source guards check integration and native
locking/callback wiring. The host model covers:

* set/idempotence/reset and hint composition; readahead preservation, unrelated
  f_mode bits, shared versus separate descriptions, and no eager reclaim;
* invalid fd/advice/length, FIFO, and DAX/noop-backing-device cases;
* sequential/random/file-hint/no-file predicates; global and target-memcg
  filtering; another eligible mapping of a shared page;
* PTE and THP references, unmap young-bit handling, MGLRU runtime on/off,
  fault placement, aging eligibility and preserved native reclaim filters;
* all eight MGLRU/MEMCG/THP compile-time combinations and eleven intentionally
  broken source variants that must be rejected (behavioral or wiring guards).

Recorded runs:

* `aosp-host-tests.log`: all eight profiles and eleven negative controls pass
  with pinned AOSP r614150 Clang 23.0.1 and trapping UBSan. `ubsan-probe.log`
  independently confirms signed overflow traps; sanitizer flags are not merely
  assumed effective. `host-tests.log` is an additional host-GCC-only model run,
  not target-build evidence.
* `mglru-existing.log`: unchanged prior MGLRU host suite, including its 2,006
  swap-shadow cleanup cases and native source guards.
* `mm-existing-aosp.log`: unchanged earlier MM suite passes with pinned AOSP
  Clang (filemap, readahead, swap PSI, compaction, shrinkers and vmstat/default
  guards). An extra host-GCC attempt of that older harness failed its existing
  `-Werror=maybe-uninitialized` diagnostic for the extracted `pflags` stub
  (`mm-existing.log`); neither that harness nor unrelated swap code was changed
  to suppress it. The new recency harness itself passes with both compilers.
* `kbuild-enabled.log`, `kbuild-disabled.log`, `kbuild-optional.log`: actual
  ARM64 Kbuild compilation of `mm/{fadvise,memory,rmap,vmscan}.o` using exact
  AOSP prebuilt commit `3b86e40facfff1eab4065614255d573293c10373`
  (r614150 / Android build 16713961 / Clang 23.0.1), ThinLTO and SCS. Profiles:
  current miatoll (MGLRU on, memcg/THP off), all three off, and an optional
  all-three-on profile. Resolved configs are retained; enabling optional flags
  was confined to disposable output configs, not the device defconfig.
* `link-header.txt`: optional-profile objects also passed an LLD relocatable
  ThinLTO/SCS link. This deliberately leaves ordinary kernel externals
  unresolved; it is **not** a full kernel image link.
* Compiler files were recovered from the pinned prebuilt Git tree and verified
  against their Git blob IDs. Local OpenSSL 3.0.20 headers and bc 7.0.3 supply
  missing host prerequisites, not source changes. Polly was disabled only in
  generated output configs for stock AOSP LLVM compatibility.

No whole-image build, device/flash/boot, real reclaim stress/concurrency, or
performance qualification is claimed. The stubs exercise extracted decisions
and state transitions, not actual PTE locking, TLB invalidation or kernel I/O.

## Reproduction and provenance

```sh
python3 tools/testing/selftests/mm_recency/test_backport.py --negative-controls
python3 tools/testing/selftests/mm_recency/test_backport.py \
  --cc '/path/to/pinned/clang -fsanitize=undefined -fsanitize-trap=undefined' \
  --negative-controls
python3 tools/testing/selftests/mglru/test_backport.py
python3 tools/testing/selftests/mm_recency/verify_overlay.py --negative-controls
```

Use the **latest stage verifier** above for the current tree. The older
carry-over verifier alone intentionally describes the predecessor stage and
cannot accept the newly changed MM files without explicit preimages.

`manifest.json` and `adaptation.diff` record the new stage; six predecessor
preimages and all new/current source hashes and modes are explicit. The verifier
anchors those preimages to the published predecessor Git commit, replays this
stage and checks current bytes/modes, and checks every other published file for
unrelated drift. It then runs the unchanged historical receipt verifier against
those explicit MM preimages, while the existing LZ4 verifier checks current LZ4
sources. Four corruption controls cover current source, preimage, patch and
evidence. No foundation, carry-over or LZ4 receipt is rewritten or silently
resealed. These manifests are review receipts, not signed attestations.

The checkout snapshot lacked the already-published LZ4 restoration patch and
cxgbit include-path correction; both were recovered byte-for-byte from the
published predecessor, not introduced as new feature changes.

This stage is local work; no push or new CI dispatch is implied by these logs.
