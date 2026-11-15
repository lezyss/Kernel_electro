# Foundation repair: build path and LZ4 v1.11.1

## Status

**Implemented locally, with bounded validation. Not a flash-qualified release.**
No push, GitHub Actions dispatch, commit, device test or old-feature replay was
performed for this repair. BBRplus remains excluded. Other missing integrations
remain separate review work; native upstream BBR is not removed.

This is a scoped repair **over** pinned `16`
`766a32ab1c8b889ac049ccd367e82786e5953bc0`, not a replacement base or a wholesale
restore of the old Electro tree. `manifest.json` records the exact changed base
paths and added source/test files. The separate verifier checks every other
base file and mode against that pin and preserves the historical audit hashes.

The files under `../base-sync-16/` describe the **earlier, unmodified base-only
checkpoint**, including its known failures. They have not been resealed or
rewritten. Their exact-base verifier is intentionally inappropriate after this
repair; a success from their failure-reproduction checker is not repair proof.
Use the new verifier and codec tests below instead.

## Changes

### LZ4 block codec

Official v1.11.1: <https://github.com/lz4/lz4/tree/v1.11.1>, commit
`aa4647fad575d01a874aaaadcdbe8e6a40e072f5`. The upstream input hashes are in the
new manifest and test harness; `lz4-adaptation.diff` reproduces the four adapted
core files from that release. This is **not** a downgrade to 1.11.0.

* Preserve the 1.11.1 `LZ4_resetStreamHC()` correction: initialize using the
  declared state size, never an indeterminate extension marker. Establish
  freestanding settings before the release's HC heap-mode defaults.
* Keep Linux's caller-owned workspace signatures. HC states always include the
  optimal parser scratch: **327784 bytes**, not the plain 262200-byte state.
  Scratch starts at the fixed base-state offset, with compile-time layout
  assertions. No ~64 KiB fallback stack array and no codec-owned allocations.
* Workspace macros use the actual types, so existing crypto callers allocate
  the full state. Legacy HC levels 13–16 normalize to the upstream maximum 12.
* Split fast compression, HC compression and decompression into independent
  Kconfig-selected objects. Restore the real `lz4_decompress.c` needed by the
  existing STATIC/preboot include chain. Restore module exports, including
  external initialization/reset APIs, without compressor/decoder linkage leaks.
* Keep upstream's C decoder and its 1.11.1 platform selection changes. No old
  ARM64 accelerator/config/assembly is restored as part of this repair.
* Frame/file/CLI/thread code and userspace allocation-owning/obsolete wrappers
  remain out of kernel scope. Safe block decoding also rejects negative input
  sizes and a null destination with nonzero capacity. The inherited preboot
  wrapper still uses the legacy trusted-input fast decoder; this repair does
  not redesign that format or make malformed preboot input safe.

### Build and packaging

* Restore the missing `scripts/ci/build-kernel.sh`, `package-anykernel.sh` and
  miatoll `anykernel.sh`, without calling absent historical KSU/SUSFS checkers.
* Fix the top-level Makefile's reversed IAS conditional: `LLVM_IAS=1` must **not**
  add `-no-integrated-as` or search for a GCC assembler. Before the fix, the
  pinned build tried `/usr/bin/as -EL` and failed.
* Keep exact AOSP Clang r614150 commit
  `3b86e40facfff1eab4065614255d573293c10373`, explicit LLVM overrides for kernel
  and host tools, integrated assembly, and output-only Polly disabling. Local
  invocation also checks the compiler provenance receipt/version.
* Keep the workflow **manual-only**. Add pinned-upstream codec/sanitizer tests,
  object-selection checks and synthetic script checks; retain their logs.
  Unignore this workflow explicitly and ignore local output/toolchain trees.
* Require a clean AnyKernel3 checkout at
  `020dfeccf9d7e962a48400fc94d3e451df92eead`. Reject a parent-repository fallback,
  another revision or a dirty framework. Retain miatoll device/partition checks,
  separate Image.gz/DTB/DTBO payloads, ZIP integrity/checksum and stale-entry
  removal. The packaging test uses disposable **non-bootable synthetic data**.

No source defconfig defaults were changed. In particular, this base still has
its own `4.14.357-openela-kinesis-omega-bpf` release string, CUBIC/fq_codel choices
and disabled HC crypto selector. Old Electro branding/features/defaults are
not silently claimed as restored by repairing the build scripts.

## Validation actually performed

| Check | Result / boundary |
|---|---|
| Complete `scripts/ci/test-lz4.sh`, pinned AOSP r614150 | PASS; 74 tests, zero failures, native ASan + trapping UBSan; nine unsupported upstream tests explicitly omitted |
| Freestanding codec objects and real STATIC wrapper | PASS on x86-64, i386 and ARM64; no codec-owned allocation or cross-codec undefined dependency; checked exports |
| Static frame sizes with `-O3` | x86-64 max 552 B; i386 284 B; ARM64 448 B; all below the 2048 B test ceiling, no dynamic stack usage |
| Actual LZ4 Makefile selections | All 27 y/m/n combinations select the expected objects |
| Build/package script fixtures | PASS: LLVM overrides, validation/rejection cases, clean pinned AK3, ZIP layout/hash and stale-entry checks; synthetic payloads only |
| Real-header ARM64 Kbuild | PASS: all three codec objects with pinned LLVM, resolved miatoll config, ThinLTO/SCS; HC compiled as an explicit object target, not enabled in defconfig |
| Real LTO relocatable link | PASS: all three Kbuild objects linked together; undefined symbols only memcpy/memmove/memset and expected weak kernel CRC references |
| Device-tree generation | PASS with pinned LLVM and the actual miatoll config |
| Full kernel image/modules build | **NOT completed**; stopped deliberately during general kernel compilation after DTBs to bound this task; no final image/link/AK3-release result claimed |
| Workflow parse, manual trigger, script existence; `bash -n`; whitespace | PASS |
| Source-scope verification | See `source-verification.log`; all base paths checked against pinned16 with only the recorded repair exceptions; historical evidence unchanged |

The first local full-build attempt caught the IAS bug. A subsequent attempt
stopped on missing sandbox OpenSSL development headers (the workflow already
installs libssl-dev). For the bounded real-header build, matching OpenSSL 3.0.20
headers were generated in scratch and a host bc 7.0.3 was bootstrapped there;
neither dependency nor any build output is imported into the repository.
The actual AOSP compiler/LLVM tools and resource files came from the pinned
AOSP mirror and were checked against its Git blob identities; no host-GCC
result is presented as target qualification.

These are working-tree results, not a newly published commit. Raw logs retain
the checkout HEAD and dirty status; the new source manifest/verifier anchors
the **actual files tested** to pinned16 plus this repair. Host-only shims and
script fixtures are explicitly distinguished from real-header Kbuild evidence.

## Reproduce

With the pinned compiler and normal workflow build dependencies installed:

```sh
bash scripts/ci/test-lz4.sh
bash scripts/ci/build-kernel.sh
# After a complete successful build and a clean pinned AK3 checkout:
python3 tools/testing/selftests/lz4/test_ci.py --anykernel out/anykernel3
bash scripts/ci/package-anykernel.sh
```

For the source-only scope check, ensure the pinned16 and previous Electro
`402566a8597ae7f0ecf3f87054b77aa7c18acdf0` objects are available locally, then:

```sh
python3 tools/testing/selftests/base_sync/verify_repaired_foundation.py
```

See `tools/testing/selftests/lz4/README` for standalone commands, prerequisites,
explicit omissions and optional compatibility testing. Full image CI remains a
separate manual operation; this repair does not authorize a push or dispatch.
