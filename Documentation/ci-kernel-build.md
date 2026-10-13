# GitHub Actions: full LLVM kernel build

The **Build kernel (AOSP Clang r614150)** workflow builds this ARM64 kernel
on Ubuntu 22.04. It runs on pushes and pull requests, and can also be started
from **Actions → Build kernel (AOSP Clang r614150) → Run workflow**.
The default configuration is `vendor/xiaomi/miatoll_defconfig`; manual runs
can select another existing ARM64 defconfig.

## Toolchain

The workflow downloads the `clang-r614150` directory from the official AOSP
`platform/prebuilts/clang/host/linux-x86` repository using a sparse checkout,
and caches that directory. It deliberately requests **r614150**, not whichever
revision is newest when a job runs. The exact AOSP repository commit and the
compiler/linker version output are recorded in `out/build-info.txt`.
If AOSP removes that directory from its default branch, downloading fails
rather than silently falling back to another compiler.

Kernel C and assembly use Clang with its integrated assembler; linking uses
LLD. Archive, symbol, strip, and object utilities use LLVM, and host utilities
use Clang/Clang++ with LLD. No GCC cross-toolchain is installed or selected.
`CROSS_COMPILE=aarch64-linux-gnu-` specifies the target triple in this old
Kbuild implementation; it does **not** select GCC because tools are overridden
explicitly. `LLVM=1` alone is insufficient for this tree.

The miatoll defconfig already enables Clang ThinLTO, which is preserved.
`CONFIG_LLVM_POLLY` is disabled only in the generated `out/.config`: this
tree's custom Polly command-line options are not portable to stock AOSP
Clang. The checked-in device defconfig is unchanged.

PGO, BOLT, LTO, and MLGO labels on an Android **compiler** describe how that
compiler was built or its capabilities. They do not automatically enable
PGO/BOLT/MLGO optimization of the **kernel**. This workflow does not claim
kernel PGO or BOLT optimization and does not supply MLGO training data.

## Outputs

A successful run uploads a `kernel-arm64-clang-r614150-*` artifact containing:

- `Image`, `Image.gz`, and `Image.gz-dtb`;
- `dtb.img`, `dtbo.img`, and individual device trees/overlays;
- built modules, `System.map`, and `Module.symvers` when present.

A separate `kernel-build-details-*` artifact contains toolchain provenance,
the resolved `.config`, and configuration, device-tree, and compilation logs.
This artifact is uploaded even after a failed build when files are available.
Logs use `pipefail`, so uploading a log cannot hide compilation failure.
Artifacts are retained for 14 days.

### Flashable miatoll ZIP

For the default `vendor/xiaomi/miatoll_defconfig`, CI also uploads an
`Electro-miatoll-AnyKernel3-r614150-*` artifact containing:

- `Electro-miatoll-4.14.357-electro-r614150-<run>.zip` (the flashable ZIP);
- a matching `.zip.sha256` checksum.

The filename uses the actual built kernel release. Download and extract the
GitHub Actions artifact first, then flash the **inner Electro ZIP**, not the
outer artifact archive, from a compatible custom recovery.

The installer uses upstream [osm0sis/AnyKernel3](https://github.com/osm0sis/AnyKernel3)
pinned to commit `020dfeccf9d7e962a48400fc94d3e451df92eead`. It installs
`Image.gz` and the separate `dtb` payload into the existing non-A/B boot image,
preserving its ramdisk, and flashes `dtbo.img` to the DTBO partition. Device
checks accept `curtana`, `joyeuse`, `excalibur`, `gram`, and the unified
`miatoll` name. Upstream example ramdisk patches and module placeholders are
not included. Modules remain available in the raw artifact; the installer
does not replace ROM/vendor modules.

**Back up boot and DTBO before testing.** Device-name checks do not guarantee
compatibility with every ROM or vendor firmware. Packaging has not been
validated by flashing on hardware. The ZIP is not a complete ROM or a standalone
`boot.img`.

Custom manual defconfigs still produce raw outputs but skip the miatoll-only
checkout/packaging/upload steps, preventing a different device's kernel from
being packaged with miatoll partition settings. Packaging logs and provenance
are included in the build-details artifact.

## Run locally

Install the dependencies listed in the workflow, unpack the same AOSP prebuilt
into `.toolchains/r614150`, then run:

```sh
bash scripts/ci/build-kernel.sh
```

To use a different prebuilt directory, configuration, or parallelism:

```sh
TOOLCHAIN_DIR=/absolute/path/to/clang-r614150 \
DEFCONFIG=vendor/xiaomi/miatoll_defconfig JOBS=8 \
  bash scripts/ci/build-kernel.sh
```

To package a completed miatoll build locally, check out the pinned AnyKernel3
commit in a separate directory and run:

```sh
ANYKERNEL_DIR=/absolute/path/to/AnyKernel3 \
  bash scripts/ci/package-anykernel.sh
```

The ZIP and checksum are written to `out/flashable/`.

Use a clean `out/` directory when switching configurations or toolchains.
Prebuilts, installer checkouts under `out/`, and generated ZIPs are ignored by Git.

This is a trial of a new compiler against a 4.14 kernel. Modern Clang may
expose old-source incompatibilities; inspect the build-details artifact if a
run fails. The workflow does not suppress compiler errors or change source
code to conceal those failures.
