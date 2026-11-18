#!/usr/bin/env bash
# Full LLVM build for this tree's pre-LLVM=1 Kbuild implementation.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"
TOOLCHAIN_DIR=${TOOLCHAIN_DIR:-"$ROOT/.toolchains/neutron-06092026"}
DEFCONFIG=${DEFCONFIG:-vendor/xiaomi/miatoll_defconfig}
JOBS=${JOBS:-$(nproc)}
ENABLE_POLLY=${ENABLE_POLLY:-0}

if [[ "$ENABLE_POLLY" != 0 && "$ENABLE_POLLY" != 1 ]]; then
    echo "ENABLE_POLLY must be 0 or 1" >&2
    exit 1
fi

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
# Both standalone builds and CI enforce the same immutable release lock.
python3 scripts/ci/neutron-toolchain.py verify --directory "$TOOLCHAIN_DIR"
# Neutron is kernel/bare-metal focused. Native LLVM supplies libc-aware host
# utilities; never substitute GCC or silently assume target runtimes exist.
HOST_LLVM_BIN=${HOST_LLVM_BIN:-/usr/bin}
HOST_LLVM_BIN=$(cd "$HOST_LLVM_BIN" && pwd)
for tool in clang clang++ ld.lld; do
    if [[ ! -x "$HOST_LLVM_BIN/$tool" ]]; then
        echo "Missing native host LLVM tool: $HOST_LLVM_BIN/$tool" >&2
        exit 1
    fi
done
if ! "$HOST_LLVM_BIN/clang" --version | grep -q 'clang version'; then
    echo "HOST_LLVM_BIN must contain native Clang, not GCC" >&2
    exit 1
fi
mkdir -p out
# Do not misattribute evidence from a prior local experiment to this build.
rm -f out/polly-probe.ll out/polly-probe.log
{
    echo "Kernel commit: $(git rev-parse HEAD)"
    echo "Tracked worktree changes: $(git status --porcelain --untracked-files=no | wc -l)"
    echo "Defconfig: $DEFCONFIG"
    echo "Experimental Polly: $ENABLE_POLLY (flags when enabled: -mllvm -polly -mllvm -polly-position=early)"
    echo "Toolchain directory: $TOOLCHAIN_DIR"
    echo "Neutron lock:"
    cat scripts/ci/neutron.lock.json
    echo "Host glibc: $(getconf GNU_LIBC_VERSION)"
    echo "Native host LLVM: $HOST_LLVM_BIN"
    "$HOST_LLVM_BIN/clang" --version
    "$HOST_LLVM_BIN/ld.lld" --version
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
    "HOSTCC=$HOST_LLVM_BIN/clang"
    "HOSTCXX=$HOST_LLVM_BIN/clang++"
    "HOSTLDFLAGS=-fuse-ld=$HOST_LLVM_BIN/ld.lld"
)

make "${make_args[@]}" "$DEFCONFIG" 2>&1 | tee out/configure.log
# Preserve the boot-tested baseline unless explicitly opting into the experiment.
if [[ "$ENABLE_POLLY" == 1 ]]; then
    scripts/config --file out/.config --enable LLVM_POLLY
else
    scripts/config --file out/.config --disable LLVM_POLLY
fi
make "${make_args[@]}" olddefconfig 2>&1 | tee -a out/configure.log
if [[ "$ENABLE_POLLY" == 1 ]]; then
    if ! grep -qx 'CONFIG_LLVM_POLLY=y' out/.config ||
       grep -qx 'CONFIG_CC_OPTIMIZE_FOR_SIZE=y' out/.config; then
        echo "Polly experiment requires resolved CONFIG_LLVM_POLLY=y and non-size optimization" >&2
        exit 1
    fi
    # Prove that this compiler actually schedules Polly, not merely accepts a
    # flag. Use the same frontend optimization/LTO/ARM64 constraints as Kbuild.
    # This is pipeline evidence, not proof of a useful transformation or speedup.
    if ! "$TOOLCHAIN_DIR/bin/clang" --target=aarch64-linux-gnu -O2 -flto=thin \
        -ffreestanding -fno-builtin -mgeneral-regs-only -ffixed-x18 \
        -mllvm -polly -mllvm -polly-position=early -Xclang -fdebug-pass-manager -S -emit-llvm -x c \
        -o out/polly-probe.ll - 2>out/polly-probe.log <<'PROBE'
void polly_probe(int * restrict dst, const int * restrict src)
{
    for (int i = 0; i < 1024; ++i)
        dst[i] = src[i] + 1;
}
PROBE
    then
        cat out/polly-probe.log >&2
        echo "Polly compiler probe failed" >&2
        exit 1
    fi
    if ! grep -q 'Running pass: .*Polly' out/polly-probe.log; then
        tail -45 out/polly-probe.log >&2
        echo "Compiler accepted -polly but no Polly pass ran; see out/polly-probe.log" >&2
        exit 1
    fi
elif ! grep -qx '# CONFIG_LLVM_POLLY is not set' out/.config; then
    echo "Baseline must keep CONFIG_LLVM_POLLY disabled" >&2
    exit 1
fi
# Check the resolved configuration, not just the defconfig request.
if [[ "$DEFCONFIG" == vendor/xiaomi/miatoll_defconfig ]]; then
    for option in ARM64 KERNEL_MODE_NEON LZ4_DECOMPRESS LZ4_ARM64_ACCEL; do
        if ! grep -qx "CONFIG_${option}=y" out/.config; then
            echo "Required miatoll LZ4 acceleration option lost: CONFIG_${option}" >&2
            exit 1
        fi
    done
fi
# Build device trees before packing images; this tree discovers them using find.
make -j"$JOBS" "${make_args[@]}" dtbs 2>&1 | tee out/dtbs.log
make -j"$JOBS" "${make_args[@]}" Image.gz-dtb dtb.img dtbo.img modules 2>&1 | tee out/build.log

test -s out/arch/arm64/boot/Image.gz-dtb
test -s out/arch/arm64/boot/dtb.img
test -s out/arch/arm64/boot/dtbo.img
