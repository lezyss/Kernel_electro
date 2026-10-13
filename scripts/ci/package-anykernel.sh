#!/usr/bin/env bash
# Package built miatoll images using a separately checked-out AnyKernel3.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"
DEFCONFIG=${DEFCONFIG:-vendor/xiaomi/miatoll_defconfig}
ANYKERNEL_DIR=${ANYKERNEL_DIR:-"$ROOT/out/anykernel3"}

# Device checks and the boot partition layout below are specific to miatoll.
if [[ "$DEFCONFIG" != vendor/xiaomi/miatoll_defconfig ]]; then
    echo "AnyKernel3 packaging is only configured for miatoll_defconfig" >&2
    exit 1
fi
for file in out/arch/arm64/boot/Image.gz out/arch/arm64/boot/dtb.img \
            out/arch/arm64/boot/dtbo.img out/include/config/kernel.release; do
    if [[ ! -s "$file" ]]; then
        echo "Missing build output: $file" >&2
        exit 1
    fi
done
if ! grep -qx 'CONFIG_ARCH_ATOLL=y' out/.config; then
    echo "Resolved kernel config is not an ATOLL build" >&2
    exit 1
fi
for file in META-INF/com/google/android/update-binary \
            META-INF/com/google/android/updater-script tools/ak3-core.sh LICENSE; do
    if [[ ! -s "$ANYKERNEL_DIR/$file" ]]; then
        echo "Missing AnyKernel3 file: $ANYKERNEL_DIR/$file" >&2
        exit 1
    fi
done
release=$(cat out/include/config/kernel.release)
build=${GITHUB_RUN_NUMBER:-local}
if [[ ! "$release" =~ ^[a-zA-Z0-9._+-]+$ || ! "$build" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Invalid release or build identifier for ZIP filename" >&2
    exit 1
fi

mkdir -p out/flashable
stage=$(mktemp -d "$ROOT/out/ak3-stage.XXXXXX")
trap 'rm -rf "$stage"' EXIT
# Copy only the installer framework, not upstream example patches/ramdisks,
# .git, CI files or module placeholders. cp -a preserves executable tools.
cp -a "$ANYKERNEL_DIR/META-INF" "$ANYKERNEL_DIR/tools" "$ANYKERNEL_DIR/LICENSE" "$stage/"
cp scripts/ci/anykernel.sh "$stage/anykernel.sh"
chmod 755 "$stage/anykernel.sh" "$stage/META-INF/com/google/android/update-binary"
cp out/arch/arm64/boot/Image.gz "$stage/Image.gz"
# Boot-header DTB payload is separate from the compressed kernel on miatoll.
cp out/arch/arm64/boot/dtb.img "$stage/dtb"
cp out/arch/arm64/boot/dtbo.img "$stage/dtbo.img"
{
    echo "Kernel release: $release"
    echo "Kernel commit: $(git rev-parse HEAD)"
    echo "AnyKernel3 commit: $(git -C "$ANYKERNEL_DIR" rev-parse HEAD)"
    echo "Devices: curtana, joyeuse, excalibur, gram (miatoll)"
    if [[ -f out/build-info.txt ]]; then
        cat out/build-info.txt
    fi
} > "$stage/build-info.txt"
cp "$stage/build-info.txt" out/package-info.txt

zipfile="$ROOT/out/flashable/Electro-miatoll-${release}-r614150-${build}.zip"
# Remove an earlier archive so zip cannot retain stale entries on local reruns.
rm -f "$zipfile"
(cd "$stage" && zip -9 -r "$zipfile" .)
unzip -t "$zipfile"
(cd "$ROOT/out/flashable" && sha256sum "$(basename "$zipfile")" > "$(basename "$zipfile").sha256")
echo "Flashable AnyKernel3 ZIP: $zipfile"
