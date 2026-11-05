Android-focused 5.15-era BPF backport
====================================

Status and scope
----------------

The planned code integration is complete: ARM64 JMP32/atomics, the approved
shared softirq hrtimer foundation, verifier/core/helper/map updates, real
pidfd-backed task storage and BPF timer helpers are integrated. The final
production ARM64 kernel, device-tree images and modules build successfully
with the exact requested AOSP toolchain. Local host regression, configuration
compile checks and preservation/replay audits are recorded alongside this file.

This is an Android-focused functional backport to 4.14.357-electro, not a
wholesale donor merge, a version spoof, or every Linux 5.15 facility. Optional
configuration activation remains separate. Device boot/runtime, networking,
SMP, lifetime stress and performance validation have NOT been performed.
Publication to the working branch and a build CI run were subsequently
authorized by the user. Git history and GitHub Actions record the resulting
commit and CI outcome; the local validation below does not imply CI success.

Baseline and source provenance
------------------------------

The original baseline is HEAD 4afc6f0769f0f3b2b10d50d3fa02f0ba7c89a183 plus
its pre-existing dirty integrations, audited across 73,011 files/symlinks.
Previous scheduler, GPU, power, F2FS, KSU/SUSFS/NoMount and other integrations
are retained. The companion ``.diff`` is a source/reference delta against
that dirty baseline, NOT a HEAD-relative replacement of prior work. Upgrade
metadata and standalone host fixtures are separate files in the checkout.

References and adaptations:

* NothingNormal/Kernel d22fb4cf8eedba08edff893f49c284299095715b supplied the
  initial JMP32 correction; later integrated atomic fixes extend that file.
* Consolidated core reference 2a58cdc0636e8eedba246338dd565bbfffc84837 was
  selectively integrated. Its complete 415,151-byte verifier was retrieved
  separately because the commit API omitted that patch; its content hash is
  recorded. Snapshot 72493ea4a19555ca1caaa0b848399b78825747b4 and original iput
  base 9700db640bbb5b27dca74ea06450d4c59550ebcc were reviewed as references,
  not clean independent implementations or wholesale merge targets.
* The shared hrtimer series through 5da70160462e80b0ab8a6960cdd0cdd476907523
  was reconciled with this tree's migration/nohz/hotplug work. Prerequisites
  63e2ed3659752a4850e0ef3a07f809988fcd74a4 and
  42f42da41b54c191ae6a775e84a86c100d66c5e8 provide mode-aware tracing and
  actual soft/hard clock bases. Later v5.15 query/expiry behavior informed
  additional reconciliation. This is not a verbatim timer-series replay.
* Upstream 108c14858b9ea224686e476c8f5ec345a0df9e27 informed real dynamic
  lockdep key registration. Retirement uses the existing 4.14 class machinery
  and appropriate grace periods, not a pretend no-op registry.
* Stream-parser behavior restores ``__SK_PASS`` using reference
  636633e1d9b1617842eff0ff3f5c9511b2d7a4d2. The IMA cached-inode hash helper
  follows genuine v5.15 behavior rather than an unavailable-function stub.

Excluded from the donor core: miatoll_defconfig, GPU accounting
``kgsl.c``/``kgsl_device.h``, branding in ``init/version.c``/``kernel/sys.c``,
``mm/filemap.c`` and ``mm/readahead.c``. Unrelated power/scheduler changes,
unprivileged-BPF policy reverts and global kernel version reporting were not
imported. One existing LZ4 attribute spelling was corrected to
``__noinline__`` to avoid a kernel macro collision; codec logic/tuning is
unchanged. Its own adaptation metadata was refreshed and replayed, and all
74 native codec/cross-decode/preboot tests passed again with ASan/UBSan.

Integrated functionality and compatibility work
----------------------------------------------

ARM64 execution
~~~~~~~~~~~~~~~

JMP32 uses 32-bit compare/test/immediate materialization while existing JMP
uses 64 bits; ALU32/ALU64 selection is preserved. Atomic fetch/add/logical,
exchange and compare-exchange emitters cover LSE and LL/SC paths. Corrections
keep the effective address stable across register aliases, preserve the
compare operand and route failed comparisons through the required barrier.
Five signed branch displacement shifts now use signed 64-bit multiplication,
removing real negative-shift undefined behavior without sanitizer exclusions.

Shared timer foundation
~~~~~~~~~~~~~~~~~~~~~~~

Soft timers have distinct bases, expiry state and softirq dispatch instead
of running BPF callbacks in hard IRQ context. Retriggering, hres/lowres query
paths, clock changes and CPU migration account for both base sets. Existing
per-CPU migration flags/counter widths, pinned state, WRITE_ONCE publication,
callback validity checks, ndelay lock loops and hotplug/quiesce APIs remain.
Quiesce avoids enabling BHs from IRQ/IPI or already-BH-disabled context and
retains callback-running rearmed soft timers on an online source CPU until
safe migration. Empty/migrated queues clear stale soft-expiry state.

BPF core, helpers and maps
~~~~~~~~~~~~~~~~~~~~~~~~~

Verifier, tnum/scalar handling, helper/UAPI tables, BTF handling, iterators,
map support and networking/cgroup call sites are updated together. Kernel and
tools BPF UAPI headers are byte-identical, including all 176 helper IDs; a
regression guard prevents the donor's stale tools timer definitions recurring.
Fork and
seq-file integration use real task/run contexts. Task storage uses actual
``pidfd_get_pid()`` fd/type/reference validation and task lifecycle cleanup,
not an EOPNOTSUPP placeholder or treating arbitrary descriptors as pidfds.

The build-ID parser checks note/header/name/descriptor bounds, GNU note names,
ELF class/endianness, program-header sizes/offsets and unaligned data before
copying. Dynamic lockdep keys are registered, validated and unregistered;
readers drain before retiring the full key/subkey range. The legacy allocator
still consumes retired class slots: this does not backport modern lockdep
slot reclamation.

BPF timers use proper softirq initialization and ``HRTIMER_MODE_REL_SOFT``
starts. Callback/program reference handling, cancellation and own-callback
map deletion follow the softirq lifetime design. On this legacy-accounting
kernel, timer-bearing maps reserve memlock pages for
``(max_entries + num_possible_cpus()) * sizeof(struct bpf_hrtimer)`` before
publication, including hash replacement spares. Failure uses existing map
cleanup/uncharge paths. This is explicit legacy RLIMIT_MEMLOCK compatibility,
NOT a full memcg backport or exact 5.15 per-allocation accounting.

Optional facilities and deliberate limits
-----------------------------------------

The production miatoll defconfig is byte-identical to the original baseline;
its SHA256 is 7d049399dbd01e9f517db96c152a86148d1fdf1a307be95745ba2fa29a456a75.
No BTF/events/LSM/stream activation was silently added to it. Necessary core
build dependencies (such as BINARY_PRINTF selected by BPF_SYSCALL) are part
of the integration, not optional feature activation.

Separate temporary configurations compile actual enabled BTF/events/LSM and
stream paths, debug lockdep, real IMA, low-resolution timers and BPF-syscall-off
compatibility. They are compile/native-codegen checks, NOT full optional image
builds or device validation. Full kernel BTF requires genuine linked vmlinux
BTF and compatible generation tooling; no fake partial BTF blob is supplied.
Userspace BTF map layouts are distinct from optional vmlinux BTF metadata.

ARM64 ``BPF_PROBE_MEM`` exception-table emission is not implemented by this
backend. Unsupported instructions fail JIT compilation; the production
JIT_ALWAYS_ON configuration rejects such programs rather than interpreting
unsupported instructions unsafely. Some optional BTF kernel-pointer tracing
programs can therefore still be rejected. No universal Linux 5.15 ISA, helper,
tracing or architecture parity is claimed. The x86 reference changes were
not target-built as part of this ARM64-focused validation.

Validation completed locally
----------------------------

* Exact AOSP Clang/LLD r614150, mirror commit
  3b86e40facfff1eab4065614255d573293c10373, Clang 23.0.1/build 16713961.
  All target compilation/assembly/linking uses LLVM, not Neutron or target GCC.
  GCC/G++ build host utilities; real OpenSSL 3.0.18 provides host crypto.
  Signing/keyring policy was not bypassed.
* Final, post-source-change production build: dtbs, vmlinux, Image.gz,
  Image.gz-dtb, dtb.img, dtbo.img and modules, exit 0. Hashes and image-format
  checks are in the companion JSON; these are build outputs, not a flashed
  boot test or a packaged release ZIP.
* Five integrated target configuration groups: debug, optional BTF/events/
  LSM/stream, IMA-enabled, lowres and BPF-syscall-off. Native relocatable
  AArch64 links lower 118 input objects in total; they allow unresolved
  external symbols and do not replace the production full link.
* Six current-source host suites pass in both ASan+UBSan and UBSan-only
  modes: 6,003,804 checks and 37 rejected runtime mutants per mode. The
  fixtures extract actual emitters, parsers and selected core/lifetime
  functions, but mock platform services. Exact coverage and limits are in
  ``tools/testing/selftests/bpf_upgrade/README.md``.
* Earlier separate timer-foundation validation covered 31 object/config
  combinations and 31 native relocatable links. Its original source and
  reconciliation provenance are retained in metadata as historical evidence.
* Full-tree preservation, normalized incremental patch replay, LZ4 replay,
  raw checkpatch diagnostics and whitespace checks are recorded in metadata.
  Raw checkpatch is not clean: 25 style errors and 192 warnings remain,
  including imported formatting and intentional-macro false positives. They
  are recorded without a broad ignore mask, not presented as zero-error checks.

Remaining device validation
---------------------------

No attached target device is available here. Boot the integrated image and
run ``tools/testing/selftests/bpf_upgrade/test_runtime.c`` with sufficient BPF
privileges. Its host compilation passes and it correctly skips the sandbox's
unrelated kernel; the BPF syscall tests have NOT run on the upgraded kernel.

Then validate asynchronous timer rearm/cancel/map and task teardown, verifier
positive/negative cases, BTF-dependent loads, real Android networking/cgroups,
sockmap/stream traffic, memory pressure, suspend/nohz/CPU-hotplug and SMP/
lockdep stress. Host shims do not establish concurrency or hardware ordering;
full kernel compilation is not proof of runtime correctness or performance.
