### AnyKernel3 installer for Electro / Xiaomi miatoll
# Framework: osm0sis/AnyKernel3 (see LICENSE in the ZIP).

properties() { '
kernel.string=Electro for Xiaomi miatoll
do.devicecheck=1
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=0
device.name1=curtana
device.name2=joyeuse
device.name3=excalibur
device.name4=gram
device.name5=miatoll
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; }

# Miatoll has a non-A/B boot partition. Preserve the installed ROM ramdisk.
BLOCK=/dev/block/bootdevice/by-name/boot;
IS_SLOT_DEVICE=0;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=auto;

. tools/ak3-core.sh;

# No ramdisk edits: repack the existing boot image with our Image.gz and dtb.
# flash_boot alone does not flash dtbo, so install the supplied overlays too.
split_boot;
flash_boot;
flash_generic dtbo;
