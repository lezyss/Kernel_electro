// SPDX-License-Identifier: BSD-2-Clause
#include "lz4hc.c"

#ifndef STATIC
#include <linux/module.h>

EXPORT_SYMBOL(LZ4_compress_HC);
EXPORT_SYMBOL(LZ4_loadDictHC);
EXPORT_SYMBOL(LZ4_compress_HC_continue);
EXPORT_SYMBOL(LZ4_saveDictHC);

EXPORT_SYMBOL(LZ4_initStreamHC);
EXPORT_SYMBOL(LZ4_resetStreamHC);
EXPORT_SYMBOL(LZ4_resetStreamHC_fast);
EXPORT_SYMBOL(LZ4_setCompressionLevel);

MODULE_LICENSE("Dual BSD/GPL");
MODULE_DESCRIPTION("LZ4 v1.11.1 lz4hc_compress");
#endif
