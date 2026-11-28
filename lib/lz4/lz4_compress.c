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

EXPORT_SYMBOL(LZ4_initStream);
EXPORT_SYMBOL(LZ4_resetStream);
EXPORT_SYMBOL(LZ4_resetStream_fast);

MODULE_LICENSE("Dual BSD/GPL");
MODULE_DESCRIPTION("LZ4 v1.11.1 lz4_compress");
#endif
