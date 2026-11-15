# SPDX-License-Identifier: GPL-2.0
# Vendored NoMount: identity is recorded in UPSTREAM.json, not a Git probe.
obj-$(CONFIG_NOMOUNT) += nomount.o

# C11 is required by declarations in for-loops and cleanup-based RCU guards.
# Retain the kernel's optimization and stack-protection choices.
ccflags-y += -std=gnu11 -Wno-declaration-after-statement

ifeq ($(shell grep -qE '\(\*[[:space:]]*__get\)' $(srctree)/include/linux/xattr.h 2>/dev/null && echo 1 || echo 0),1)
ccflags-y += -DNM_HAS_XATTR__GET
endif
