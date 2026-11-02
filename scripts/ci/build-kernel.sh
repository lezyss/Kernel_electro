#!/usr/bin/env bash
# Full LLVM build for this tree's pre-LLVM=1 Kbuild implementation.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"
TOOLCHAIN_DIR=${TOOLCHAIN_DIR:-"$ROOT/.toolchains/r614150"}
DEFCONFIG=${DEFCONFIG:-vendor/xiaomi/miatoll_defconfig}
JOBS=${JOBS:-$(nproc)}

# Do not allow workflow inputs to become make options or escape configs/.
if [[ ! "$DEFCONFIG" =~ ^[a-zA-Z0-9_/-]+_defconfig$ || "$DEFCONFIG" == *..* || "$DEFCONFIG" == /* ]] ||
   [[ ! -f "arch/arm64/configs/$DEFCONFIG" ]]; then
    echo "Invalid ARM64 defconfig: $DEFCONFIG" >&2
    exit 1
fi
if [[ ! "$JOBS" =~ ^[1-9][0-9]*$ ]]; then
    echo "JOBS must be a positive integer" >&2
    exit 1
fi
TOOLCHAIN_DIR=$(cd "$TOOLCHAIN_DIR" && pwd)
export PATH="$TOOLCHAIN_DIR/bin:$PATH"
# Ensure every tool comes from the requested prebuilt, not the host PATH.
for tool in clang clang++ ld.lld llvm-ar llvm-nm llvm-strip llvm-objcopy llvm-objdump llvm-readelf; do
    if [[ ! -x "$TOOLCHAIN_DIR/bin/$tool" ]]; then
        echo "Missing LLVM tool: $TOOLCHAIN_DIR/bin/$tool" >&2
        exit 1
    fi
done
mkdir -p out
{
    echo "Kernel commit: $(git rev-parse HEAD)"
    echo "Defconfig: $DEFCONFIG"
    echo "Toolchain directory: $TOOLCHAIN_DIR"
    if [[ -f "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt" ]]; then
        echo "AOSP prebuilts commit: $(cat "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt")"
    fi
    "$TOOLCHAIN_DIR/bin/clang" --version
    "$TOOLCHAIN_DIR/bin/ld.lld" --version
} | tee out/build-info.txt

# LLVM=1 is not implemented by this kernel's Makefile. Explicit overrides
# are needed for BOTH the kernel and host utilities to avoid GCC/binutils.
make_args=(
    O=out ARCH=arm64
    LLVM=1 LLVM_IAS=1
    CROSS_COMPILE=aarch64-linux-gnu-
    CLANG_TRIPLE=aarch64-linux-gnu-
    "CC=$TOOLCHAIN_DIR/bin/clang"
    "AS=$TOOLCHAIN_DIR/bin/clang"
    "LD=$TOOLCHAIN_DIR/bin/ld.lld"
    "AR=$TOOLCHAIN_DIR/bin/llvm-ar"
    "NM=$TOOLCHAIN_DIR/bin/llvm-nm"
    "STRIP=$TOOLCHAIN_DIR/bin/llvm-strip"
    "OBJCOPY=$TOOLCHAIN_DIR/bin/llvm-objcopy"
    "OBJDUMP=$TOOLCHAIN_DIR/bin/llvm-objdump"
    "READELF=$TOOLCHAIN_DIR/bin/llvm-readelf"
    "HOSTCC=$TOOLCHAIN_DIR/bin/clang"
    "HOSTCXX=$TOOLCHAIN_DIR/bin/clang++"
    HOSTLDFLAGS=-fuse-ld=lld
)

make "${make_args[@]}" "$DEFCONFIG" 2>&1 | tee out/configure.log
# The defconfig's custom Polly flags are not portable to stock AOSP LLVM.
# Keep ThinLTO and the other device settings, changing only the output config.
scripts/config --file out/.config --disable LLVM_POLLY
make "${make_args[@]}" olddefconfig 2>&1 | tee -a out/configure.log
# A requested accelerator must survive dependency resolution; do not silently
# report a successful C-only build as validation of the optional assembly.
if grep -qx 'CONFIG_LZ4_ARM64_ACCEL=y' "arch/arm64/configs/$DEFCONFIG"; then
    for setting in CONFIG_ARM64=y CONFIG_KERNEL_MODE_NEON=y \
                   CONFIG_LZ4_DECOMPRESS=y CONFIG_LZ4_ARM64_ACCEL=y; do
        if ! grep -qx "$setting" out/.config; then
            echo "Required LZ4 acceleration setting missing: $setting" >&2
            exit 1
        fi
    done
    echo "ARM64 LZ4 acceleration enabled in resolved config" | tee -a out/configure.log
fi
# Build device trees before packing images; this tree discovers them using find.
make -j"$JOBS" "${make_args[@]}" dtbs 2>&1 | tee out/dtbs.log
make -j"$JOBS" "${make_args[@]}" Image.gz-dtb dtb.img dtbo.img modules 2>&1 | tee out/build.log

test -s out/arch/arm64/boot/Image.gz-dtb
test -s out/arch/arm64/boot/dtb.img
test -s out/arch/arm64/boot/dtbo.img
