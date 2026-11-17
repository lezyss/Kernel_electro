/* SPDX-License-Identifier: GPL-2.0 */
#ifndef LZ4_ARM64_ACCEL_H
#define LZ4_ARM64_ACCEL_H

#include <linux/types.h>
#include <asm/cpufeature.h>
#include <asm/simd.h>

/* Assembly may wildcopy beyond a sequence, but not beyond these margins. */
#define LZ4_FAST_MARGIN 128

static inline bool lz4_decompress_accel_enable(void)
{
	return system_supports_fpsimd() && may_use_simd();
}

int lz4_decompress_asm(u8 **dst_ptr, u8 *dst_begin, u8 *dst_end,
		       const u8 **src_ptr, const u8 *src_end);

#endif /* LZ4_ARM64_ACCEL_H */
