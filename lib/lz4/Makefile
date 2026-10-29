# SPDX-License-Identifier: GPL-2.0
ccflags-y += -O3 -DLZ4_FREESTANDING=1 -DLZ4_FAST_DEC_LOOP=1

obj-$(CONFIG_LZ4_COMPRESS) += lz4_compress.o
obj-$(CONFIG_LZ4HC_COMPRESS) += lz4hc_compress.o
obj-$(CONFIG_LZ4_DECOMPRESS) += lz4_decompress.o

# Keep one decoder module, including its optional SIMD implementation.
lz4_decompress-y := lz4_decompress_main.o
lz4_decompress-$(CONFIG_LZ4_ARM64_ACCEL) += lz4armv8/lz4accel.o \
					lz4armv8/lz4armv8.o
