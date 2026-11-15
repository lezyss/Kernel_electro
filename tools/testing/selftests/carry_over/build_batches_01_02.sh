#!/usr/bin/env bash
# Bounded real-header object builds, NOT an image build or device qualification.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"
TOOLCHAIN_DIR=${TOOLCHAIN_DIR:-"$ROOT/.toolchains/r614150"}
TOOLCHAIN_DIR=$(cd "$TOOLCHAIN_DIR" && pwd)
OUTPUT_DIR=${OUTPUT_DIR:-"$ROOT/out/carry-over-batches-01-02"}
JOBS=${JOBS:-2}
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo 'Invalid JOBS' >&2; exit 1; }
expected=3b86e40facfff1eab4065614255d573293c10373
[[ -f "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt" ]] &&
    [[ "$(cat "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt")" == "$expected" ]] ||
    { echo 'Expected pinned AOSP Clang r614150 toolchain' >&2; exit 1; }
export PATH="$TOOLCHAIN_DIR/bin:$PATH"
for tool in clang clang++ ld.lld llvm-ar llvm-nm llvm-strip llvm-objcopy llvm-objdump llvm-readelf; do
    [[ -x "$TOOLCHAIN_DIR/bin/$tool" ]] || { echo "Missing LLVM tool: $tool" >&2; exit 1; }
done
"$TOOLCHAIN_DIR/bin/clang" --version
"$TOOLCHAIN_DIR/bin/ld.lld" --version
args=(O="$OUTPUT_DIR" ARCH=arm64 LLVM=1 LLVM_IAS=1
      CROSS_COMPILE=aarch64-linux-gnu- CLANG_TRIPLE=aarch64-linux-gnu-
      CC="$TOOLCHAIN_DIR/bin/clang" AS="$TOOLCHAIN_DIR/bin/clang"
      LD="$TOOLCHAIN_DIR/bin/ld.lld" AR="$TOOLCHAIN_DIR/bin/llvm-ar"
      NM="$TOOLCHAIN_DIR/bin/llvm-nm" STRIP="$TOOLCHAIN_DIR/bin/llvm-strip"
      OBJCOPY="$TOOLCHAIN_DIR/bin/llvm-objcopy" OBJDUMP="$TOOLCHAIN_DIR/bin/llvm-objdump"
      READELF="$TOOLCHAIN_DIR/bin/llvm-readelf"
      HOSTCC="$TOOLCHAIN_DIR/bin/clang" HOSTCXX="$TOOLCHAIN_DIR/bin/clang++"
      HOSTLDFLAGS=-fuse-ld=lld)
mkdir -p "$OUTPUT_DIR"
make "${args[@]}" vendor/xiaomi/miatoll_defconfig
scripts/config --file "$OUTPUT_DIR/.config" --disable LLVM_POLLY
make "${args[@]}" olddefconfig
cp "$OUTPUT_DIR/.config" "$OUTPUT_DIR/miatoll-default.config"
objects=(drivers/devfreq/arm-memlat-mon.o drivers/soc/qcom/scm.o
         drivers/platform/msm/ipa/ipa_v3/ipa_uc_wdi.o drivers/cpufreq/cpufreq_stats.o
         kernel/sched/fair.o kernel/sched/core.o kernel/sched/idle.o
         kernel/sched/deadline.o kernel/sched/cpufreq_schedutil.o kernel/cgroup/cpuset.o
         drivers/base/arch_topology.o drivers/base/power/wakeup.o
         drivers/cpuidle/lpm-levels.o drivers/gpu/msm/adreno.o
         drivers/gpu/msm/kgsl_gmu_core.o drivers/gpu/msm/kgsl_sync.o
         drivers/iommu/iommu.o drivers/irqchip/irq-gic-v3.o
         drivers/md/dm-verity-target.o block/cfq-iosched.o)
make -j"$JOBS" "${args[@]}" "${objects[@]}"
for object in "${objects[@]}"; do test -s "$OUTPUT_DIR/$object"; done
echo 'PASS: 20 ARM64 objects with pinned LLVM, real headers, default miatoll config (output Polly disabled)'

# The shipped config excludes some changed block-accounting branches. Build
# them explicitly in an OUTPUT-ONLY configuration, never enable BFQ on-device.
scripts/config --file "$OUTPUT_DIR/.config" --enable DEBUG_BLK_CGROUP \
    --enable IOSCHED_BFQ --enable BFQ_GROUP_IOSCHED
make "${args[@]}" olddefconfig
for setting in CONFIG_DEBUG_BLK_CGROUP=y CONFIG_IOSCHED_BFQ=y CONFIG_BFQ_GROUP_IOSCHED=y; do
    grep -qx "$setting" "$OUTPUT_DIR/.config"
done
cp "$OUTPUT_DIR/.config" "$OUTPUT_DIR/block-accounting-test.config"
make -j"$JOBS" "${args[@]}" block/cfq-iosched.o block/bfq-cgroup.o
for object in block/cfq-iosched.o block/bfq-cgroup.o; do test -s "$OUTPUT_DIR/$object"; done
echo 'PASS: real-header CFQ/BFQ debug/group-accounting object builds (test config only)'

# Exercise the atomic implementation involved in the original SCM register
# clobber concern, without enabling it in the shipped source defconfig.
scripts/config --file "$OUTPUT_DIR/.config" --enable ARM64_LSE_ATOMICS
make "${args[@]}" olddefconfig
grep -qx CONFIG_ARM64_LSE_ATOMICS=y "$OUTPUT_DIR/.config"
cp "$OUTPUT_DIR/.config" "$OUTPUT_DIR/scm-lse-test.config"
make -j"$JOBS" "${args[@]}" drivers/soc/qcom/scm.o
echo 'PASS: real-header SCM ARM64 object with LSE atomics (test config only)'
echo 'LIMITS: object compilation only; no full image link, vendor-module ABI, real PMU/SMC/IRQ/hotplug/device validation'
