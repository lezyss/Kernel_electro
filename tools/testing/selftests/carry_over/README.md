# Carry-over regression and source checks

The reviewed 143-reference inventory is accounted for: 140 applied/corrected-native
coverages, E143 already native (supplied upstream metadata unresolved), E115
superseded by official LZ4 1.11.1, and E118 BBRplus excluded. These are not 140
literal donor cherry-picks and not complete Linux 5.15 BPF ABI equivalence.

```sh
python3 tools/testing/selftests/carry_over/run_host.py --verify-source
python3 tools/testing/selftests/carry_over/run_extended.py --verify-source
TOOLCHAIN_DIR=/path/to/pinned/r614150 \
  bash tools/testing/selftests/carry_over/build_remaining.sh
```

`run_host.py` runs the earlier six suites, including real-host Kconfig for both
PREEMPT selector modes. `run_extended.py` requires Clang on PATH, host GCC and
sanitizer runtimes; it runs 19 expanded suites plus separate compiled negative
controls. `--negatives-only` reruns just the separate controls. Models extract
production functions but mock kernel locks, RCU, timers, hardware, VFS and other
facilities. They are not live kernel stress tests. A compiler error is never a
successful semantic negative control.

`test_security.py` verifies the current vendored KSU/FinaSU/NoMount identities
and runs extracted authorization/lifetime models. The SUSFS 2.4 and F2FS sysfs
`--models-only` modes deliberately do not assert their incompatible older full-
checkpoint seals: the ordered current source verifier owns that provenance.
Other historical provenance scripts are retained as helpers/history and are not
standalone current-checkpoint verification commands.

`verify.py` verifies all 73,279 pinned base paths/modes, repaired LZ4/build source,
four ordered overlays (412 paths including declared additions/modes), historical
receipts and current test/evidence hashes. It needs local Git objects for pinned16,
previous Electro and the historical SUSFS header origin. It does not fetch,
modify the live tree, or establish semantics. Previous exact-base/foundation-only
verifiers intentionally reject authorized later overlays.

`build_remaining.sh` requires the exact pinned AOSP toolchain and ordinary host
kernel-build dependencies (bc, OpenSSL development headers/library, etc.). It uses
LLVM for target and Kbuild host tools, integrated assembly, real kernel headers,
ThinLTO and shadow-call stack. Polly is disabled only in generated output config.
It compiles 74 explicit ARM64 objects plus the selected kernel/bpf directory,
then output-only MEMCG/LOCKDEP/F2FS-compression/BPF-events/stream-parser and
BORE/MGLRU/DEBUG_FS-off profiles. It never enables these extras in the source
miatoll defconfig. OUTPUT_DIR defaults to out/carry-over-remaining; JOBS defaults
to 2. EXTRA_HOSTCFLAGS can supply a non-system host OpenSSL include directory.

`build_batches_01_02.sh` remains the earlier narrower 20-object/accounting/LSE
checkpoint recipe. It is not the expanded matrix or a full-image build.

No full image/module link, boot, vendor-module ABI, real concurrency/IRQ/RCU/
reclaim/filesystem-durability/security certification or performance claim follows.
See Documentation/dev-tools/carry-over/README.md and validation.json for results,
limits, artifact hashes and the unresolved E143 reference identity.
