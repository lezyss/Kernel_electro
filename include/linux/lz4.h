/* SPDX-License-Identifier: BSD-2-Clause */
#ifndef __LINUX_LZ4_H__
#define __LINUX_LZ4_H__

#include "../../lib/lz4/lz4.h"
#include "../../lib/lz4/lz4hc.h"

#define LZ4_MEM_COMPRESS sizeof(LZ4_stream_t)
#define LZ4HC_MEM_COMPRESS sizeof(LZ4_streamHC_t)
#define LZ4HC_MIN_CLEVEL 3
#define LZ4HC_DEFAULT_CLEVEL LZ4HC_CLEVEL_DEFAULT
/* Legacy levels 13..16 are accepted and normalized to the v1.10 maximum (12). */
#define LZ4HC_MAX_CLEVEL 16
#define LZ4_STREAMHCSIZE sizeof(LZ4_streamHC_t)
#define LZ4_STREAMHCSIZE_SIZET (sizeof(LZ4_streamHC_t) / sizeof(size_t))

#endif
