.. SPDX-License-Identifier: GPL-2.0

==========================
LZ4 v1.10 kernel backport
==========================

Scope and provenance
====================

The LZ4 block codec is based on the v1.10.0 kernel adaptation in
Kentanglu/kernel_xiaomi_sm6250, branch 16-ksu, snapshot
6c22e92e918cfb7540ddc298abe3a8cc05559672.  Its import series starts at
031b41a6e827eb813a7aedb3f4711a28c8a22ba8.  Upstream license notices are
retained in the imported files.  Zstd, LZ4KD, device configuration and the
ZRAM default algorithm are not changed.

This is a kernel adaptation, not an unchanged userspace library import.
It implements the existing kernel LZ4 interfaces, including the caller
workspace arguments of LZ4_compress_fast() and LZ4_compress_destSize().
It does not promise binary compatibility with previously compiled modules.
Rebuild all consumers with these headers.

Build and memory rules
======================

The existing CONFIG_LZ4_COMPRESS, CONFIG_LZ4HC_COMPRESS and
CONFIG_LZ4_DECOMPRESS selections still build separate objects/modules.
Small wrappers select the relevant portion of the shared lz4.c source;
lz4hc.c includes only its common helper definitions.  All sixteen existing
symbol exports and the module licenses are retained.

The public wrapper provides the existing workspace macros and the legacy
LZ4HC_DEFAULT_CLEVEL spelling.  Allocate contexts using LZ4_MEM_COMPRESS,
LZ4HC_MEM_COMPRESS or sizeof the corresponding stream type; do not hardcode
old internal sizes.  The checked inline LZ4_compressBound() also rejects
oversized size_t arguments before narrowing to int.

The codec does not allocate memory while compressing or decompressing.
Fast and destination-size compression use the supplied workspace.  The HC
optimal parser uses scratch embedded in the caller-owned HC state instead
of a roughly 64 KiB stack array or a GFP_KERNEL allocation.  Contexts must
not be shared concurrently without the caller's serialization.

On a 64-bit host, the HC context grows to 327784 bytes (about 320 KiB),
roughly 64 KiB above the previous HC context.  This cost applies to HC
contexts, not ordinary LZ4 ZRAM contexts.  The normal fast stream remains
16416 bytes.  Context allocation still occurs in the existing consumer's
setup path.  HC levels 10--12 retain optimal parsing; legacy requests for
levels 13--16 are normalized to the v1.10 maximum of 12 rather than rejected.

Preboot and ARM64
=================

lib/decompress_unlz4.c can still include lz4/lz4_decompress.c under STATIC.
That path now includes the allocation-free C decoder wrapper; it does not
include SIMD headers, exports or kernel allocation APIs.  The decoder-only
object has no dependency on the compressor/HC object.

Optional ARM64 acceleration is available through CONFIG_LZ4_ARM64_ACCEL,
which defaults to n and requires ARM64, KERNEL_MODE_NEON and a built-in or
modular LZ4 decoder.  The miatoll defconfig explicitly enables it for the
authorized CI/device validation build; the Kconfig default remains n.
With the option off,
the ARM64 compatibility entry points and streaming decoding still use C.

With the option on, only LZ4_arm64_decompress_safe(), its partial variant,
and the first dictionary-free LZ4_decompress_safe_continue() block may use
assembly.  Generic LZ4_decompress_safe()/partial() callers, dictionary
continuations and preboot remain C-only.  In particular, this does not
redirect the ordinary crypto/ZRAM or EROFS consumers into assembly.

The assembly uses caller-saved x6 rather than the Shadow Call Stack register
x18.  The old source-rewriting DIP exit is removed: an early exit rewinds to
the beginning of the current sequence, and the v1.10 C decoder resumes with
the original block bases and updated input/output positions.  The C tail
can reference already decoded SIMD output.  The public dip argument is
retained, but dip requests and overlapping input/output buffers use C.
This does not extend upstream C's documented in-place layout guarantees.

Acceleration requires more than 128 bytes of input and output, disjoint
buffers, system FPSIMD support and may_use_simd().  Assembly runs only
inside kernel_neon_begin()/kernel_neon_end().  CPU selection occurs inside
that pinned region; Cortex-A53 uses the no-prefetch variant.  Direct calls
replace the old per-CPU function-pointer cache, avoiding indirect assembly
CFI targets.  This is not a claim of full kernel CFI validation.

The decoder is one composite lz4_decompress.o/module containing its main C
wrapper and, when selected, both SIMD objects.  This avoids orphan built-in
assembly dependencies when CONFIG_LZ4_DECOMPRESS=m.  The separate compressor
and HC objects, existing module name and exported API remain unchanged.

Leave the experimental option disabled for release builds until target
kernel validation is complete.  No assembly speedup or ZRAM/EROFS
performance improvement is claimed here.

Validation and limits
=====================

Local checks used host-only kernel-header shims, not a full kernel build:

* The three objects compiled with warnings treated as errors, including
  freestanding 32-bit and 64-bit syntax checks.
* A host stack-usage check rejected frames larger than 2048 bytes in the
  codec objects; undefined references were restricted to memory-copy/set
  primitives, with no allocators or SIMD helpers.
* AddressSanitizer and UBSan covered 108 compression/roundtrip, partial and
  truncated-input scenarios, including HC levels 9 and 12.
* Additional sanitizer tests covered legacy APIs/constants, streaming and
  dictionary operations, bounded workspace use, destination-size compression,
  the legacy fast decoder and ARM64 C fallbacks.
* 5000 pseudorandom full/partial decoding cases and three overlapping
  in-place roundtrips passed output guards and sanitizers.
* 132 differential compression and cross-decoding cases matched the imported
  implementation, including legacy HC level 16.
* The real STATIC preboot wrapper round-tripped a legacy LZ4 kernel stream
  through the new decoder using a host preboot allocator environment.

Host shims do not validate kernel locking, allocation context, target
instruction generation or kernel module loading.  A full AOSP Clang r614150
build, device boot, memory-pressure stress and device benchmarking remain
necessary before treating the update as release-tested.  C-only operation
has no new configuration requirement; SIMD is a separate default-off option.
There is no assertion that the update is faster on SM6250.

ARM64 follow-up validation
-------------------------

The standalone test in tools/testing/selftests/lz4/test_arm64.py compiles
the actual decoder, dispatcher and assembly with freestanding header shims
and emulates AArch64 instructions with Unicorn.  Both the prefetch and
no-prefetch implementations are exercised, not substituted with C stubs.
A second executable uses Clang Shadow Call Stack and ThinLTO.  The harness
checks that SCS instrumentation actually writes the shadow stack, x18 and
callee-saved registers survive, SIMD begin/end calls balance, compressed
input is not modified, and data accesses stay within the supplied buffers.

Local results with Zig 0.14.1's Clang 19.1.7 (not AOSP r614150), Unicorn
2.1.4 and pyelftools 0.32, for each executable:

* 483 valid blocks, including all offsets 1--64, larger offsets, long
  lengths, multiple sequences, and SIMD-prefix references in the C tail.
* Full and partial results compared with the generic C decoder, including
  unaligned buffers, truncation and undersized output.
* C fallbacks with SIMD forbidden, FPSIMD unavailable, dip=true, overlapping
  buffers and small buffers; malformed offsets and size_t overflow guards.
* 1000 pseudorandom malformed blocks, with buffer-access checking.
* First-block streaming acceleration, contiguous-prefix continuation,
  external-dictionary continuation, and rejection of negative stream sizes.
* 476 full-block entries into each assembly variant, plus partial/error/
  streaming entries; both executables passed.

Additional checks compiled feature-off, no-NEON and STATIC variants without
SIMD references; compiled the three C objects for 32/64-bit targets with
warnings/frame limits enforced; linked optional decoder members into one
relocatable object; and checked Kconfig default/dependency combinations for
both built-in and modular decoding.

These are freestanding/emulator checks, not a kernel build or sanitizer
instrumentation of assembly.  SIMD eligibility, preemption and FPSIMD save/
restore are represented by shims; kernel context correctness and real CPU
behaviour still require target validation.  The release compiler remains
AOSP Clang r614150.  No full kernel build, CI run, device boot or performance
benchmark was performed for this follow-up.

Style audit
===========

The imported codec retains its upstream naming and formatting.  The full
strict checkpatch report is not clean, including inherited macro and
indentation findings.  The adaptation-only report has no errors, but retains
warnings such as exports grouped in the thin kernel object wrappers and the
shared internal HC scratch type.  These checks are separate from compilation
and runtime sanitizer results; this backport is not described as style-clean.
