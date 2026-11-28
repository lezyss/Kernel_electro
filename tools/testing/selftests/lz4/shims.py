# SPDX-License-Identifier: GPL-2.0
"""Minimal freestanding Linux-header shims, not a kernel-context emulator."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SHIMS = {'linux/types.h': '#ifndef TEST_TYPES_H\n'
                  '#define TEST_TYPES_H\n'
                  'typedef __SIZE_TYPE__ size_t;\n'
                  'typedef __PTRDIFF_TYPE__ ssize_t;\n'
                  'typedef __PTRDIFF_TYPE__ ptrdiff_t;\n'
                  'typedef __UINT8_TYPE__ uint8_t;\n'
                  'typedef __UINT16_TYPE__ uint16_t;\n'
                  'typedef __UINT32_TYPE__ uint32_t;\n'
                  'typedef __UINT64_TYPE__ uint64_t;\n'
                  'typedef __INT8_TYPE__ int8_t;\n'
                  'typedef __INT16_TYPE__ int16_t;\n'
                  'typedef __INT32_TYPE__ int32_t;\n'
                  'typedef __INT64_TYPE__ int64_t;\n'
                  'typedef __UINTPTR_TYPE__ uintptr_t;\n'
                  'typedef uint8_t u8;\n'
                  'typedef uint16_t u16;\n'
                  'typedef uint32_t u32;\n'
                  'typedef uint64_t u64;\n'
                  'typedef _Bool bool;\n'
                  '#define true 1\n'
                  '#define false 0\n'
                  '#define NULL ((void *)0)\n'
                  '#define asmlinkage\n'
                  '#endif\n',
 'linux/compiler.h': '#define __always_inline inline __attribute__((always_inline))\n'
                     '#define likely(x) __builtin_expect(!!(x), 1)\n'
                     '#define unlikely(x) __builtin_expect(!!(x), 0)\n',
 'linux/string.h': '#include <linux/types.h>\n'
                   'void *memcpy(void *, const void *, size_t);\n'
                   'void *memmove(void *, const void *, size_t);\n'
                   'void *memset(void *, int, size_t);\n',
 'linux/errno.h': '#define EIO 5\n',
 'linux/module.h': '#define EXPORT_SYMBOL(x)\n'
                   '#define MODULE_LICENSE(x)\n'
                   '#define MODULE_DESCRIPTION(x)\n'}
