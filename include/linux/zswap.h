/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_ZSWAP_H
#define _LINUX_ZSWAP_H

#include <linux/types.h>

#ifdef CONFIG_ZSWAP
bool zswap_is_enabled(void);
#else
static inline bool zswap_is_enabled(void)
{
	return false;
}
#endif

#endif /* _LINUX_ZSWAP_H */
