// SPDX-License-Identifier: BSD-2-Clause
#define LZ4_KERNEL_DECOMPRESS_ONLY
#include "lz4.c"

#ifndef STATIC
#include <linux/module.h>

EXPORT_SYMBOL(LZ4_arm64_decompress_safe);
EXPORT_SYMBOL(LZ4_arm64_decompress_safe_partial);
EXPORT_SYMBOL(LZ4_decompress_safe);
EXPORT_SYMBOL(LZ4_decompress_safe_partial);
EXPORT_SYMBOL(LZ4_setStreamDecode);
EXPORT_SYMBOL(LZ4_decompress_safe_continue);

MODULE_LICENSE("Dual BSD/GPL");
MODULE_DESCRIPTION("LZ4 v1.11.1 lz4_decompress");
#endif
