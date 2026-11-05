# Integrated Android-focused BPF backport checks

These checks cover the **current source**, not copied pseudocode. They supplement
(not replace) a real kernel build and device testing. Kernel code was built with
pinned AOSP r614150; the host models use GCC and mocked platform facilities.

## Host regression suites

From the kernel root, with Linux GCC, Python 3 and ASan/UBSan runtimes:

```sh
for suite in jmp32 softirq atomics core timer_lifetime lockdep; do
    python3 tools/testing/selftests/bpf_upgrade/test_${suite}.py \
        --self-test-negatives
    python3 tools/testing/selftests/bpf_upgrade/test_${suite}.py \
        --asan --self-test-negatives
done
```

Without `--asan`, the runners use UBSan. With it, both ASan and UBSan are
active. Output lives in temporary directories outside the checkout. The
sanitizer modes abort on violations; JMP32/softirq/atomic runners also probe
sanitizer detection. Negative controls must compile and fail at runtime;
a compiler error does not count as detecting a mutant. There is **no signed
shift-base suppression**: the five A64 signed branch shifts were fixed using
signed 64-bit multiplication before encoding their displacements.

| Suite | Checks per mode | Mutants | Coverage |
| --- | ---: | ---: | --- |
| `jmp32` | 923,120 | 8 | All 22 JMP32 and 22 JMP register/immediate forms; signed/unsigned/JSET; high halves, random/boundary operands; dry/emission agreement; forward/backward branches; ALU width preservation |
| `softirq` | 1,200,895 | 12 | Actual timer initialization/base switching, hard/soft expiry selection, retriggering, migration/nohz/hotplug and callback-running paths |
| `atomics` | 200,000 | 3 | Actual ARM64 atomic emitter and encoders; LSE/LL-SC, both widths, fetch/exchange/compare-exchange, address aliases, retry and failure barriers |
| `core` | 3,369,783 | 6 | Actual build-ID note/ELF parser, pidfd lookup, tnum operations and verifier scalar-bound functions |
| `timer_lifetime` | 230,005 | 5 | Actual timer init/callback/set/start/cancel/free and legacy memlock reservation; array/hash paths, callback swapping, errors, self-cancel/self-delete |
| `lockdep` | 80,001 | 3 | Actual dynamic-key register/lookup/unregister; duplicate rejection, IRQ restoration, grace-period ordering and full-subkey retirement |

**Result: 6,003,804 checks and 37 rejected mutants per mode**, in both
ASan+UBSan and UBSan-only runs.

### What is real and what is mocked?

* JMP32 and atomic suites compile the actual emitter/encoding functions and
  headers. An independent bounded decoder interprets their A64 machine words;
  it does not reuse encoder condition helpers. It is not an ARM64 CPU.
* Softirq tests extract actual scheduling/expiry/migration functions. Clocks,
  locks, interrupts, CPU state and queues have host platform shims.
* Core tests first require byte-identical kernel/tools BPF UAPI headers,
  including the timer helper IDs missing from the donor tools copy. They
  extract actual parser, pidfd, tnum and selected verifier functions.
  Build-ID checks include truncations, unaligned ELF32/64 headers, overflowing
  program-header offsets and 100,000 randomized note headers. Tnum checks
  enumerate concrete sparse-mask combinations. Scalar checks examine signed
  and unsigned 32/64-bit boundary/random additions and subtractions.
* Timer lifetime tests extract the actual helper functions and hrtimer modes.
  Allocators, maps, references, locks and hrtimer operations are mocked. Own
  callback deletion frees backing storage immediately so ASan can detect a
  subsequent use-after-free in the callback wrapper.
* Lockdep tests mock the graph lock, RCU and class retirement while checking
  their ordering, IRQ context and complete key range.

These are sequential, bounded tests. They do **not** prove the full verifier,
SMP ordering, races, CPU-hotplug behavior on hardware, network correctness or
kernel-wide memory safety. Build-ID tests do not currently use guard pages.

## Actual target builds

The integrated production build passed with exact AOSP Clang/LLD r614150,
commit `3b86e40facfff1eab4065614255d573293c10373`:

* Unchanged `vendor/xiaomi/miatoll_defconfig`.
* Final `vmlinux`, `Image.gz`, `Image.gz-dtb`, `dtb.img`, `dtbo.img`, modules.
* Separate debug lockdep with BPF core, BTF/events/LSM/stream, real IMA-enabled,
  low-resolution timer and BPF-syscall-disabled target builds.
* Five additional native AArch64 relocatable links (118 input objects), so
  optional/debug coverage is not merely unlowered LLVM bitcode. These links
  allow unresolved external symbols; only the production full link resolves
  its complete enabled configuration.

See `Documentation/bpf/bpf-5.15-upgrade.json` for pins, hashes, configuration
scope and precise limitations. Optional BTF compilation is **not** a full
BTF-enabled image build or a declaration that all tracing programs can load.

## Rooted-device smoke test (not run here)

After booting the upgraded Electro image, use a native Linux/Termux compiler
in a copy of this tree:

```sh
cc -std=gnu11 -O2 -Wall -Wextra -Werror \
    tools/testing/selftests/bpf_upgrade/test_runtime.c -o bpf-runtime-smoke
su -c ./bpf-runtime-smoke
```

The relative UAPI includes deliberately use this backport's BPF definitions.
The test checks the running release, then performs real BPF load/JIT/test-run
for JMP32 and atomic fetch-add, loads a small userspace BTF schema and tests
task-storage syscalls with real, non-pidfd, closed and reaped-task pidfds.
It needs BPF privileges and sufficient memlock allowance. It exits 4 on an
unrelated kernel; that skip is **not** a runtime PASS. Its native host build
was checked with `-Werror`; it correctly skipped the sandbox's unrelated kernel.

Further device validation is still required: asynchronous timer callbacks,
rearm/cancel/map teardown races, verifier rejection cases, network/cgroup and
sockmap traffic, suspend/nohz/CPU-hotplug, memory pressure, lockdep and SMP
stress. No device runtime, performance or universal 5.15 ABI claim is made.
