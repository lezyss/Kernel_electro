// SPDX-License-Identifier: BSD-2-Clause
#define LZ4_KERNEL_COMPRESS_ONLY
#include "lz4.c"

#ifndef STATIC
#include <linux/module.h>

EXPORT_SYMBOL(LZ4_compress_fast);
EXPORT_SYMBOL(LZ4_compress_default);
EXPORT_SYMBOL(LZ4_compress_destSize);
EXPORT_SYMBOL(LZ4_loadDict);
EXPORT_SYMBOL(LZ4_saveDict);
EXPORT_SYMBOL(LZ4_compress_fast_continue);

MODULE_LICENSE("Dual BSD/GPL");
MODULE_DESCRIPTION("LZ4 v1.10 lz4_compress");
#endif
