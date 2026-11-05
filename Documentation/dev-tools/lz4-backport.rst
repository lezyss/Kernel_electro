.. SPDX-License-Identifier: GPL-2.0

=========================
LZ4 v1.11 kernel backport
=========================

Scope and provenance
====================

The block codec is upgraded to upstream LZ4 v1.11.0, pinned at
c72c7c0ec132ad2ce2fe9fad7b0c728d9faee2fc (upstream PR 2037).
Only lib/lz4.c, lib/lz4.h, lib/lz4hc.c and lib/lz4hc.h are adapted.
Upstream license notices are retained.  No userspace CLI, frame, file or
threading implementation is imported into the kernel.

The preceding v1.10.0 kernel adaptation came from
Kentanglu/kernel_xiaomi_sm6250, branch 16-ksu, snapshot
6c22e92e918cfb7540ddc298abe3a8cc05559672; its import series starts at
031b41a6e827eb813a7aedb3f4711a28c8a22ba8.  This upgrade preserves that
adaptation's kernel workspaces, split objects, exports and ARM64 integration.
Zstd, LZ4KD, filesystem policy, device configuration and the ZRAM default
algorithm are not changed.

lz4-1.11.json records source hashes and validation details.
lz4-1.11-adaptation.diff is the exact difference between the four pinned
upstream files and their kernel postimages.  To reproduce it, place those
upstream files under lib/lz4/ in a scratch tree, then apply the patch with
``git apply``.  The resulting four files must match the manifest hashes.
The patch describes the kernel adaptation, not the entire upstream release
history.  The upstream release notes are in NEWS.

Kernel interfaces and allocation rules
======================================

The existing CONFIG_LZ4_COMPRESS, CONFIG_LZ4HC_COMPRESS and
CONFIG_LZ4_DECOMPRESS selections still build separate objects/modules.
Small wrappers select compression, decompression, or common definitions
from the shared sources.  All sixteen existing kernel symbol exports,
module identities and licenses are retained.  Removed upstream obsolete
userspace-only wrappers are not added to the kernel API.

LZ4_compress_default(), LZ4_compress_fast(), LZ4_compress_destSize() and
LZ4_compress_HC() retain the kernel's explicit caller-workspace arguments.
The checked, inline LZ4_compressBound(size_t) rejects oversized arguments
before narrowing to int.  The public linux/lz4.h wrapper retains the kernel
workspace macros and legacy HC constants.  Rebuild consumers with these
headers; internal streaming state is not a stable binary module ABI.

The codec allocates no heap memory while compressing or decompressing.
Allocate contexts using LZ4_MEM_COMPRESS, LZ4HC_MEM_COMPRESS or sizeof the
corresponding stream type, and serialize use of shared contexts.
On 64-bit targets, the ordinary stream remains 16416 bytes and the HC stream
remains 327784 bytes: neither grows relative to this tree's v1.10 adaptation.

Unlike upstream's optional extended HC state, the kernel HC union always
owns the optimal parser's scratch storage.  LZ4_STREAMHC_EXTSIZE is
262200 + 65584 bytes; scratch starts at the fixed base-state offset 262200,
not at sizeof the enlarged kernel union.  Compile-time assertions check
base-context containment, scratch size and total capacity.  There is no
heap or approximately 64 KiB stack fallback, including at levels 10--12.
The legacy reset accepts indeterminate first-use memory without consulting
an uninitialized hasWorkspace flag.  Init, reset, dictionary load, attached
dictionaries and extState compression retain the full caller-owned storage.
An upstream base-only LZ4_STREAMHC_MINSIZE allocation is insufficient for
the kernel; LZ4_initStreamHC() rejects it.  Legacy levels 13--16 normalize
to the v1.11 maximum of 12, rather than being rejected.

Correctness changes and callers
===============================

The new core retains upstream's ring-buffer sizing margin of 64 bytes,
streaming/dictionary history checks, destination-size corrections, argument
checks, and new HC parsing algorithms.  Safe C decoding distinguishes
malformed input (-1), insufficient output capacity (-2), and missing
history/dictionary (-3).  Do not depend on a negative input-position offset.
The custom ARM64 compatibility path still promises a negative error, not
those exact categories on every assembly exit.

In-tree crypto/LZ4, crypto/LZ4HC, F2FS, pstore, SquashFS and Incremental FS
consumers check negative results; EROFS checks the expected decoded length.
They do not depend on the old negative offsets.  The preboot wrapper retains
the legacy fast decoder for trusted kernel-image input.  This upgrade does
not make legacy fast decoding safe for arbitrary untrusted data.

Preboot and ARM64
=================

lib/decompress_unlz4.c can still include lz4/lz4_decompress.c under STATIC.
The decoder-only object has no compressor, allocator or SIMD dependency.
The complete preboot wrapper, public kernel header and preboot allocator
are also exercised by the native regression test, not only a copied decoder.

CONFIG_LZ4_ARM64_ACCEL remains experimental, defaults to n, and requires
ARM64, KERNEL_MODE_NEON and a built-in or modular LZ4 decoder.  The existing
miatoll defconfig selection is unchanged by this upgrade.  With the option
off, ARM64 compatibility entry points and streaming decoding use C.

Only LZ4_arm64_decompress_safe(), its partial variant, and the first
history-free LZ4_decompress_safe_continue() block can use assembly.
Generic LZ4_decompress_safe()/partial() callers, dictionary continuations
and preboot remain C-only.  Ordinary crypto/ZRAM and EROFS consumers are
not redirected to assembly.

The assembly and dispatcher themselves are unchanged.  They preserve x18
for Shadow Call Stack, rewind incomplete sequences, and resume the v1.11
C tail using the original block bases plus advanced cursors.  The tail can
reference the SIMD-produced prefix.  DIP requests, overlapping buffers,
small buffers and unavailable/forbidden SIMD use C.  Existing upstream
in-place layout restrictions are not relaxed.

Acceleration still requires more than 128 input/output bytes, disjoint
buffers, system FPSIMD support and may_use_simd().  Calls are bracketed by
kernel_neon_begin()/kernel_neon_end(); CPU selection occurs inside that
pinned region, with Cortex-A53 selecting the no-prefetch implementation.
The decoder remains one composite object/module containing its C wrapper
and, when enabled, both SIMD objects.  No CFI guarantee is inferred from
these checks.

Local validation of v1.11
=========================

Reproducible harnesses and invocation notes are in
tools/testing/selftests/lz4/README.  Tests use Clang 19.1.7 supplied by
Zig 0.14.1, Unicorn 2.1.4 and pyelftools 0.32.  The production compiler
remains AOSP Clang r614150, not this local toolchain.

Native block-codec checks:

* 70 applicable pinned upstream LZ4/HC tests, plus four kernel-specific
  tests: 74 tests passed with seed 1, including ASan and UBSan traps.
* Coverage includes malformed/truncated input, new safe-decoder errors,
  destination-size consumption and resumption, dictionaries and overlapping
  streaming input, ring buffers, and multi-gigabyte logical stream offsets.
* Kernel tests check workspace sizes/canaries, optimal HC scratch bounds,
  first-use reset on poisoned memory, levels 1--16, exact legacy-level
  normalization, the real STATIC preboot wrapper, and reference decoding.
* Both compression/decompression directions pass against independently
  built, locally bound upstream v1.11.0 and v1.10.0 reference libraries.
* Nine upstream tests concerning removed userspace allocators/obsolete APIs
  or upstream's optional HC extension contract are explicitly omitted and
  printed by name.  Test-only allocation adapters supply kernel workspaces;
  they are not part of the codec.  Alignment tests retain the supported
  extState/destSize checks without the obsolete reset wrapper assertions.
* ASan references in every codec object are verified.  A separate signed
  overflow probe must actually trap, so ignored sanitizer flags do not pass.
  Native ASan uses raw Clang plus the host sanitizer runtime; Zig's cc
  driver must not be assumed to enable ASan merely because it accepts a flag.
* A deliberately wrong HC scratch offset was rejected with an ASan heap
  buffer overflow by the workspace regression; no mutant source remains
  in the repository.

Freestanding and real-instruction ARM checks:

* All three codec objects compile for ARM32 and ARM64 with warnings as
  errors and a 2048-byte frame limit.  Symbol audits reject allocators and
  unexpected external helpers; the export set is exactly the prior 16.
* 27 actual ARM64 default/fast/HC compression roundtrips pass, including
  optimal levels 10--12 and legacy level 16, with input/output/workspace
  guards and callee-saved/x18 preservation.
* Each of two decoder executables passes 483 valid blocks and 1000 malformed
  blocks, full/partial/truncated/undersized-output checks, SIMD fallback
  cases, and first/prefix/external-dictionary streaming.  Each exercises
  both assembly implementations (476 full-block entries into each variant).
* The second decoder executable uses Shadow Call Stack plus ThinLTO;
  actual shadow-stack writes are required.  Feature-off, no-NEON and STATIC
  objects are checked for absence of SIMD references.

Limits
======

These are host-header-shim, sanitizer and instruction-emulator checks, not
a full production kernel build.  Assembly is checked with emulated memory
access hooks, not native ASan instrumentation.  Kernel preemption, FPSIMD
ownership, locking and module loading still need target validation.
No new production image, device boot, memory-pressure stress, performance
measurement, push or CI run was performed for this upgrade.  Historical
boot results for earlier code do not establish v1.11 runtime correctness.
No phone, ZRAM, EROFS or SM6250 speedup is claimed.

Style
=====

The imported core retains upstream formatting.  It is not represented as
strict kernel-checkpatch clean; retained upstream names, macros and layout
are distinct from compilation, sanitizer and runtime results.

Integrated BPF build compatibility follow-up (2026-11-05)
------------------------------------------------------

The compiler attribute now uses ``__noinline__`` rather than ``noinline``
to prevent collision with the kernel macro. No codec logic or tuning changed.
The adaptation patch and current-source hashes were refreshed and replayed
against all four pinned upstream sources. All 74 native codec, cross-decode
and preboot tests passed again with ASan and UBSan (seed 1, host GCC); the
production ARM64 build is recorded in ``Documentation/bpf/bpf-5.15-upgrade.json``.
