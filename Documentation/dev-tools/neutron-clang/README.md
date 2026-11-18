# Pinned Neutron Clang build environment

The current build entry points use **Neutron 06092026 / Clang 24.0.0git**,
LLVM `f42c87ba2c70219b1f4ad1f031a5b6a1ea6603fb`, instead of AOSP r614150.
All authoritative install inputs are in `scripts/ci/neutron.lock.json`.
Historical AOSP receipts elsewhere in this tree are intentionally unchanged;
they do not validate the Neutron build.

## Distribution, integrity and Antman

Upstream manager: <https://github.com/Neutron-Toolchains/antman>, reviewed at
`0b32c45e3ad83a953b4bc3fd2feb4ad3cc87c1e8` (v3.1).
The selected release is the equivalent of `antman -S=06092026`, **not** `-S=latest`.
Antman's metadata resolution still follows mutable catalogue `main`, even when
the manager and release argument are pinned. Therefore CI does not execute the
remote manager. The small Python installer implements its download/check/extract
operation against the repository lock instead.

* Catalogue: <https://github.com/Neutron-Toolchains/clang-build-catalogue>, commit
  `4bd827900870b688fbf19c202f6625a13b04fa92`.
* Original release info: `upstream/06092026-info.txt`, SHA-256
  `0e2db658f981e2cde4a2197a0b0dc5ef6a5906bc6f9e31c58c42f6488dc9926b`.
* Archive: `neutron-clang-06092026.tar.zst`, SHA-256
  `531083928c8e37f6b31e324dbfd0b5a8323f989b1c57ff2c1368b889b5b1bd30`.
* Release asset metadata is retained in `upstream/release.json`; the archive is
  deliberately not committed. GitHub release asset redirects must be reachable.

The cache retains the verified archive plus `neutron-install.json`. On install
or verification, the installer checks the locked archive hash, compares every
installed file's bytes, link targets and executable status against the archive,
rejects extra files, then runs the compiler identity check. A marker file alone
is not accepted as proof. Installation uses a temporary sibling directory and
only publishes it after successful verification. Existing invalid installations
fail closed: remove that dedicated toolchain directory/cache and reinstall; do
not overlay arbitrary Antman updates on it. Extracted paths and link targets
must remain inside the installation; special files and duplicate members are
rejected. Downloaded archives are verified before extraction or execution.

## Isolated host and local use

This Neutron release requires **x86-64 Linux / glibc >= 2.43**. The workflow keeps
its Ubuntu 22.04 runner but executes the job in the digest-pinned Ubuntu 26.04
amd64 image recorded in the lock. Docker Library's image metadata is captured
in `upstream/ubuntu-26.04.md` from repo-info commit
`584ae88613547cccf78d1a3b09f196b2888baa43` (2026-10-04).
A runtime glibc guard fails clearly on an incompatible image/host before download
or compiler execution. There is no system libc replacement and no Antman
`--patch=glibc` (which downloads rolling Arch runtime packages).

Example from a Docker-capable x86-64 Linux host, at repository root:

```sh
IMAGE=$(python3 -c 'import json; print(json.load(open("scripts/ci/neutron.lock.json"))["container_image"])')
docker run --rm -it -v "$PWD:/src" -w /src "$IMAGE" bash
# Inside this disposable container (do not install these into an older host):
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  bc bison flex libssl-dev libelf-dev libncurses-dev make python3 python3-venv \
  git curl ca-certificates cpio rsync zip unzip xz-utils zstd lz4 clang lld libclang-rt-dev
python3 scripts/ci/neutron-toolchain.py install
HOST_LLVM_BIN=/usr/bin bash scripts/ci/test-lz4.sh
HOST_LLVM_BIN=/usr/bin bash scripts/ci/build-kernel.sh
```

Container-created files may be root-owned; adjust ownership for the invoking
host user when leaving the container. `TOOLCHAIN_DIR` may select a different
installation path, but not a different locked compiler. `HOST_LLVM_BIN` selects
the native Clang/Clang++/LLD directory (default `/usr/bin`).

Upstream describes Neutron as a kernel/bare-metal toolchain, not a libc/userspace
distribution. **Neutron builds all target kernel objects, freestanding cross
checks and ARM64 assembly tests. Native distro Clang/LLD builds libc-aware host
utilities and ASan/UBSan codec tests.** There is no GCC compiler fallback and no
use of Neutron's bundled GNU target binutils. The old Kbuild does not implement
modern `LLVM=1` fully, so explicit target LLVM overrides remain in place.

The compiler archive and base image are content-pinned. Apt host dependencies
and PyPI test dependencies are not a fully hermetic, snapshot-pinned OS; the
workflow records installed native compiler/libc package versions and OS identity
in `out/host-environment.log`. It does not claim bit-for-bit whole-build
reproducibility. Updating the compiler requires deliberate lock, cache, scripts,
workflow labels and fixture updates together.

## Preserved policy and outputs

* Manual `workflow_dispatch` only; no push/PR trigger added.
* miatoll defconfig, ThinLTO/SCS and existing device settings are retained.
  Polly remains disabled in the generated output config by default. A separate
  explicit experiment is now available; see the opt-in section below.
* All four resolved ARM64/LZ4 acceleration config guards and the full existing
  codec, freestanding, ARM64 emulation and packaging test paths remain enabled.
* AnyKernel3 remains pinned to `020dfeccf9d7e962a48400fc94d3e451df92eead`.
* Cache keys include the lock hash. ZIP/artifact names use `neutron-06092026`
  rather than the superseded `r614150`. Packaged build-info includes the lock,
  actual target/native LLVM versions and host glibc identity.

## Validation and outstanding qualification

Executed in the available sandbox:

* 14 synthetic installer/host/workflow checks passed:
  `python3 tools/testing/selftests/neutron/test_toolchain.py`.
* Build-script fixtures passed (explicit target LLVM, separate native host LLVM,
  invalid input/provenance and four resolved-config rejection cases).
* Packaging fixtures passed against a clean pinned AnyKernel3 checkout:
  layout/checksum/stale-entry and negative cases. Their images are synthetic,
  non-bootable and discarded.
* Shell syntax checks passed for the modified build/test/package entry points.
* Actual install on this glibc 2.36 sandbox correctly rejected the host.

These checks **do not execute the real Neutron compiler**. This sandbox lacks a
container runtime, and both direct release download and the GitHub asset API
redirect were blocked at `release-assets.githubusercontent.com`. No real archive
was downloaded/verified here, and no container pull, Neutron ARM64 build, full
kernel link, boot or device/performance test is claimed. The new manual workflow
has not been dispatched. Its first compatible-host run must qualify the archive
layout/tool availability, native dependencies and Clang 24 compatibility before
this migration can be considered build-validated. Do not relabel older AOSP
results as Neutron results.

## First CI integration findings

The compatible container successfully installed and integrity-verified the real
Neutron release. Neutron passed the x86-64/i386/ARM64 freestanding codec checks.
The native Clang sanitizer tests require explicit `libclang-rt-dev` when apt
recommendations are disabled; this dependency is now installed. With it, all
74 applicable codec tests passed. Neutron omits the driver's default CFI
ignorelist; the bare-metal ARM64 test now specifies `-fno-sanitize-ignorelist`
while retaining `-fsanitize=shadow-call-stack,cfi` and ThinLTO. This adds no
exclusions and changes neither the downloaded compiler nor kernel configuration.
Full-kernel and device qualification remain outstanding until separately recorded.

## Optional Polly experiment (not yet build/boot qualified)

The baseline Neutron build completed CI successfully (run `44131331960`), and
its boot was confirmed by the user. That result does **not** qualify Polly.

The manual workflow has a `polly` boolean input, default **false**. Locally:

```sh
# Run in the compatible isolated environment described above.
ENABLE_POLLY=1 HOST_LLVM_BIN=/usr/bin bash scripts/ci/build-kernel.sh
```

The output config is explicitly enabled/disabled after defconfig generation and
checked again after olddefconfig. The source device defconfig is not rewritten.
The experiment uses only `-mllvm -polly`; the legacy bundle of inlining,
strip-mining, OpenMP and scheduling flags has been removed from the Polly block.
No other optimization thresholds, CPU tuning, ThinLTO, or SCS policy are changed.
The pinned LLVM source's `polly/lib/Support/RegisterPasses.cpp` registers this
option with the new pass manager, defaults to the ISL optimizer and defaults to
no Polly vectorizer. `polly/lib/CodeGen/IslAst.cpp` leaves thread-parallel codegen
off by default. We do not enable either feature. ARM64 `-mgeneral-regs-only`
remains under Kbuild control.

An ARM64 freestanding ThinLTO compiler probe checks for actual Polly pass
scheduling in `out/polly-probe.log`; accepting an option alone is insufficient.
The probe IR is retained as `out/polly-probe.ll`. This demonstrates pipeline
participation, not useful loop transformation, whole-kernel coverage or speedup.
Unsupported options, missing pass scheduling, lost config, or size-optimization
configs fail closed. `out/build-info.txt` records the requested experiment.

Experiment ZIPs and image artifact names include `-polly`; the ZIP label comes
from the actual output config. The kernel release remains `4.14.357-electro`
and the SUSFS uname policy is unchanged. Rebuild both variants from the same
commit for an A/B comparison; keep a known-working boot image and a working
recovery path before device testing. Compare boot, suspend/resume, app use,
thermals, battery, image size and repeatable workloads before making this the
default. No Polly performance improvement or boot result is claimed here.

Synthetic script tests cover default-off and opt-in behavior, invalid selection,
compiler rejection and missing pipeline scheduling. Real compiler/build/device
validation of this experimental path is still pending; preparing it does not
automatically publish or dispatch the workflow.
