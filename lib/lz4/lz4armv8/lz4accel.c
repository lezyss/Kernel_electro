// SPDX-License-Identifier: GPL-2.0
#include <linux/linkage.h>
#include "lz4accel.h"
#include <asm/cputype.h>
#include <asm/neon.h>

asmlinkage int _lz4_decompress_asm(u8 **dst_ptr, u8 *dst_begin, u8 *dst_end,
				   const u8 **src_ptr, const u8 *src_end);
asmlinkage int _lz4_decompress_asm_noprfm(u8 **dst_ptr, u8 *dst_begin,
					  u8 *dst_end, const u8 **src_ptr,
					  const u8 *src_end);

int lz4_decompress_asm(u8 **dst_ptr, u8 *dst_begin, u8 *dst_end,
		       const u8 **src_ptr, const u8 *src_end)
{
	int ret;

	/* Pins the CPU and protects the SIMD register file until neon_end. */
	kernel_neon_begin();
	/* Direct calls avoid an assembly function-pointer target under CFI. */
	if (read_cpuid_part_number() == ARM_CPU_PART_CORTEX_A53)
		ret = _lz4_decompress_asm_noprfm(dst_ptr, dst_begin, dst_end,
						 src_ptr, src_end);
	else
		ret = _lz4_decompress_asm(dst_ptr, dst_begin, dst_end,
					  src_ptr, src_end);
	kernel_neon_end();
	return ret;
}
