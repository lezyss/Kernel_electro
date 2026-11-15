# ARM64 LZ4 accelerator restored on official 1.11.1

## Correction and scope

The foundation repair intentionally omitted the old optional ARM64 accelerator.
The subsequent carry-over completion report did not account for that omission;
its broad completion claim was incorrect for this feature. This overlay restores
the previously approved feature from
`1a206aea00ea8e1788f12639251304de28083659` **without downgrading LZ4**.
The codec remains official v1.11.1
(`aa4647fad575d01a874aaaadcdbe8e6a40e072f5`) with the existing kernel adaptations,
caller-owned compressor workspaces and STATIC/preboot wrappers.

The foundation-repair manifest, carry-over progress/validation manifests, prior
patch batches and their historical evidence are intentionally NOT rewritten.
In particular E115's historical “superseded” accounting concerns the old codec;
it was not evidence that the missing assembly path had been restored.

The earlier published reconciliation's manual CI run
[43757415476](https://github.com/lezyss/Kernel_electro/actions/runs/43757415476)
completed successfully at commit `fe2f37d2f6a5232387ec5af643f2f0e3b7d06179`.
That run **predates this restoration** and does not validate it. This restoration
is local, not a new pushed commit or a newly dispatched CI build.

## Integration

* `CONFIG_LZ4_ARM64_ACCEL` is optional/default-off and depends on ARM64,
  KERNEL_MODE_NEON and the decompressor. The approved miatoll defconfig enables it.
  Manual CI checks all four resolved options after olddefconfig; it also runs
  the ARM64 regression suite before building the image.
* Kbuild keeps the `lz4_decompress` module name through a composite object; the
  real `lz4_decompress.c` remains directly includable by STATIC preboot code.
* `LZ4_arm64_decompress_safe{,_partial}` are exported, including C fallbacks when
  the feature is off. Oversized size_t inputs/outputs reject with `-EIO` before
  pointer arithmetic. The helpers otherwise retain v1.11.1 error categories;
  invalid offsets detected in assembly return `-3`.
* The v1.11.1 decoder has a resume-aware inner function and an unchanged-signature
  C wrapper. The handoff retains original input/output bounds and history base;
  a C-tail match can reference output produced by NEON. It never restarts the
  decoder with a truncated history window.
* Ordinary generic safe/partial APIs remain C-only. Only callers of the ARM64
  helpers and the first dictionary-free streaming block select acceleration.
  Dictionary/prefix continuation blocks remain C. Enabling the config is not
  evidence that every LZ4 consumer uses assembly.
* Preserve donor CPU pinning/SIMD ownership through kernel_neon_begin/end, test
  SIMD usability before entry, and select Cortex-A53's no-prefetch variant only
  after entering the pinned region. Both calls are direct, not CFI function
  pointer calls. The assembly uses x6, never the SCS-reserved x18.
* Preserve 128-byte margins, sequence-boundary rewind and immutable compressed
  input. DIP, overlapping input/output, missing FPSIMD and unusable SIMD contexts
  use C. The old source-rewriting DIP path is NOT restored.
* Add carry checks to assembly literal/match endpoint arithmetic: a wrapped
  address rewinds to C rather than bypassing unsigned endpoint comparisons.
  The normal-sized copy algorithm and tables are unchanged. A synthetic
  near-U64_MAX literal-destination test exercises the rewind in both variants.

## New validation (bounded)

All compiler tests below used the exact AOSP r614150 prebuilt at
`3b86e40facfff1eab4065614255d573293c10373`, Android build 16713961, Clang 23.0.1.
Selected toolchain files/native sanitizer runtimes were recovered from that Git
tree and verified against their Git blob IDs. No target object was built with GCC.

* `arm64.log`: actual donor-derived assembly and kernel wrappers compiled and
  executed in Unicorn, normal and ThinLTO/SCS/CFI variants. Each ran 483 valid
  blocks, 1,000 malformed blocks, both assembly CPU variants (476 entries each
  in the valid corpus), full/partial decode, alignments, truncation, undersized
  output, C-tail history, streaming/dictionaries, CPU/SIMD/FPSIMD fallbacks,
  overlap/DIP, size_t guards, bounds hooks, callee-saved ABI and x18 checks.
  SCS shadow writes must occur. Feature-off and no-NEON helper binaries execute
  C-only; STATIC objects must contain no assembly/SIMD dependency.
* `codec.log`: pinned official upstream block regressions plus existing kernel
  tests, **74 tests / 0 failed**, ASan and trapping UBSan; instrumentation and
  the negative overflow probe checked. Includes real STATIC preboot framing,
  HC workspaces/reset/canaries, exports and cross-decoding against v1.11.1.
* `build.log`: x86-64, i386 and ARM64 strict freestanding object/stack/export/
  allocator-reference checks, actual STATIC include chains, all 27 y/m/n outer
  Kbuild selections. The two helper exports are now included in expectations.
* `kbuild.log`, `kbuild-off.log`, `miatoll.config`, `kernel-symbols.txt`:
  real ARM64 miatoll Kbuild, acceleration on/off, separate HC compilation,
  SCS/ThinLTO and an LLD relocatable link. The enabled link contains both helper
  exports and assembly variants; only normal kernel services remain undefined.
  The disabled composite contains only the C wrapper. Polly was disabled only
  in the generated output config for compatibility with stock AOSP LLVM.
  Local OpenSSL 3.0.20 headers and bc 7.0.3 supplied missing host prerequisites;
  they are build-environment inputs, not kernel source changes.
* `ci-fixtures.log`: script-contract tests, including rejection of each of the
  four missing resolved miatoll acceleration options. Synthetic scripts, NOT
  a real full image/package test; the optional packaging fixture was not rerun.
* `test_lz4_overlay.py`: patch/preimage/current-source/evidence corruption must
  be rejected. `carry_over/verify.py` also replays all historical batches and
  checks original source/mode/evidence receipts against the explicit preimages,
  then independently replays this overlay and checks the CURRENT files.
  `provenance.log` records a pass over 73,279 base paths and all 412 historical
  carry-over paths; `overlay-controls.log` records all four negative controls.
  The current checkout had also lost the already-reviewed pinned16 include-path
  correction in `drivers/target/iscsi/cxgbit/Makefile`; its three `$(srctree)`
  include paths were restored byte-for-byte from the pinned base, as required by
  the existing receipts. No new cxgbit backport or receipt exception was added.

Reproduction (install requirements into an isolated Python environment):

```sh
python3 -m pip install -r tools/testing/selftests/lz4/requirements.txt
python3 tools/testing/selftests/lz4/test_arm64.py --cc /path/to/pinned/clang
python3 tools/testing/selftests/lz4/test_build.py --cc /path/to/pinned/clang
python3 tools/testing/selftests/lz4/test_codec.py --cc /path/to/pinned/clang \
  --upstream /path/to/aa4647fad575d01a874aaaadcdbe8e6a40e072f5 --asan --ubsan
python3 tools/testing/selftests/lz4/test_ci.py
python3 tools/testing/selftests/carry_over/test_lz4_overlay.py
python3 tools/testing/selftests/carry_over/verify.py
```

`manifest.json` records explicit historical preimages, current postimages/modes,
the overlay patch hash, evidence hashes and unchanged donor glue identities.
Preimages are stored under `preimages/` as `.preimage` files, not active sources.
Every modified preimage must be covered by an existing foundation/batch/source
receipt. Replay is not a silent reseal or an exception accepting arbitrary
current bytes. Manifests are review receipts, not signed attestations.

**Limits:** no new full kernel-image build, boot/flash test, hardware kernel-SIMD
context/concurrency/stress test, Termux run, or performance improvement is claimed.
Unicorn stubs kernel context primitives; bounded malformed-input coverage is not
exhaustive safety proof. The optional accelerator remains experimental.
