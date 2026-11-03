// SPDX-License-Identifier: BSD-2-Clause
#include "lz4hc.c"

#ifndef STATIC
#include <linux/module.h>

EXPORT_SYMBOL(LZ4_compress_HC);
EXPORT_SYMBOL(LZ4_loadDictHC);
EXPORT_SYMBOL(LZ4_compress_HC_continue);
EXPORT_SYMBOL(LZ4_saveDictHC);

MODULE_LICENSE("Dual BSD/GPL");
MODULE_DESCRIPTION("LZ4 v1.10 lz4hc_compress");
#endif
