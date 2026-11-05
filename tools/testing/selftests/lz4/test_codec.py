#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Run pinned upstream block regressions against the kernel codec, not liblz4.

Requires an independently obtained, pinned upstream source tree (--upstream).
Nothing is downloaded or written to the source tree. Allocations in the test
adapters belong to the harness, never to the compiled kernel codec objects.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import resource
import signal
import shlex
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile
from test_arm64 import ROOT, SHIMS

PIN = 'c72c7c0ec132ad2ce2fe9fad7b0c728d9faee2fc'
# Exact upstream source hashes; do not silently test another release.
HASHES = {
    'lib/lz4.c':
        '45061782ff932eb8cf71c3aea9495cec0d392f012395272e0550e30c8593c740',
    'lib/lz4.h':
        '6fee8f913ce3bc65bf716060f65ce890d83bea905445256c7a56da5bf4824d73',
    'lib/lz4hc.c':
        '2511d51c3026999536b8cb56806a7f1b6a5bd8a81295a02ff2e1efc10ab071aa',
    'lib/lz4hc.h':
        'a92a509858c3b79afb033bfa64335d633802884e5c1d5a15aaa54cdb3e9e5103',
    'lib/xxhash.c':
        '9c5498e00479217d7573b2474397a4248127f013f24d9ef98de0281d2dd30d89',
    'lib/xxhash.h':
        'aefdd236f35130495c18764cabed3f7b216906855fc5e6a9025cd2040bc84444',
    'programs/platform.h':
        '0a32f1a66f3d4966c75b3dd36c1b8a54186c25a3b7f5bd67a3594c318c8004d7',
    'programs/util.h':
        'db888009f6419af2b191e92664275ab394dabddfaec32b03adc7d8eee30bfb77',
    'tests/tools/datagen.c':
        '5101ccc0f6cdc28c790c462a69aea846b5d4c067c9733ac61bd4a2bf7e6f2e8a',
    'tests/tools/datagen.h':
        '49ff2d1b70db6329f3b5d28d2befa11060a42fddbdad84b9388c40521ea6e71f',
    'tests/unit/unittest.c':
        '037bdd0115275a6ff7dc18fd9ab86ab22a20386728af4bfe9b965021f6fd74be',
    'tests/unit/unittest.h':
        '79c133cbbf4eedb7197a5b0c14a16856dc9c28b9a98c046ba428419e5d60841a',
    'tests/unit/unittest_lz4.c':
        '121922b4aaf870f69a43eea2321121e930025bfae1b850af5f4c02086225cf3e',
    'tests/unit/unittest_lz4hc.c':
        '068daacc49a775754b15cbeca381468d6c56803675670e67545ae7549024b64c',
}


COMPAT_HASHES = {
    'lib/lz4.c':
        '9396f7de527bc8435de9c7569fb7998e56545a84b4f3c2d808c0235c01774539',
    'lib/lz4.h':
        '26b82efc53d1570f3b54eef02e9c4764c1ad374ff03cac04e2ced5ea4d4c552f',
    'lib/lz4hc.c':
        '126cafafdb91767e6e55238298a910903851b35b2cee27ce80ae2280469ee232',
    'lib/lz4hc.h':
        'e43824e8a9ba16f54100c4ccbccfa5782a858ca9ab83c48aac303fea3e76e21e',
}

def region(text, start):
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return opening, end


def adapt_tests(text, suite):
    # Only omitted tests: removed userspace allocators/obsolete wrappers, plus
    # the opt-in extended-state layout which the kernel always supplies instead.
    unsupported = re.compile(r'\bLZ4_(?:create\w*|free\w*|compress_withState|'
                             r'compress_limitedOutput\w*|compress_continue|'
                             r'resetStreamState\w*|compressHC2_continue|slideInputBufferHC)\s*\(')
    text = text.replace('(LZ4_streamHC_t*)UT_defer(freeStreamHC, LZ4_createStreamHC())',
                        '(LZ4_streamHC_t*)UT_malloc(sizeof(LZ4_streamHC_t))')
    # Retain the extState/destSize alignment checks without obsolete resets.
    text = re.sub(r'^    ASSERT_EQ\(LZ4_resetStreamStateHC\(state[^\n]*\n', '', text, flags=re.M)
    omitted = []
    for match in reversed(list(re.finditer(r'^TEST\((\w+)\)', text, re.M))):
        _, end = region(text, match.start())
        block = text[match.start():end]
        name = match.group(1)
        if (unsupported.search(block) or name in ('createStream', 'createStreamHC',
                                                  'compress_HC_extendedState')):
            omitted.append(name)
            text = text[:match.start()] + text[end:]
    for name, typ, init, tail in (
        ('newStream', 'LZ4_stream_t', 'LZ4_initStream', ''),
        ('newStreamHC', 'LZ4_streamHC_t', 'LZ4_initStreamHC',
         '    LZ4_resetStreamHC_fast(stream, level);\n'),
    ):
        match = re.search(r'\b' + name + r'\([^;{}]*\)\s*\{', text)
        if match:
            opening, end = region(text, match.start())
            text = (text[:opening] + '{\n    ' + typ + '* stream = (' + typ +
                    '*)UT_malloc(sizeof(*stream));\n    ASSERT(' + init +
                    '(stream, sizeof(*stream)) != NULL);\n' + tail +
                    '    return stream;\n}' + text[end:])
    expected_omissions = {
        'lz4': {'compress_deprecatedFunctions', 'createStream', 'stream_returnValues'},
        'lz4hc': {'createStreamHC', 'streamHC_returnValues',
                  'resetStreamStateHC_compressHC2_continue', 'compressHC2_continue_roundTrip',
                  'slideInputBufferHC', 'compress_HC_extendedState'},
    }
    if set(omitted) != expected_omissions[suite]:
        raise RuntimeError('unexpected upstream test omissions: ' + repr(omitted))
    text = re.sub(r'^static void freeStream(?:HC)?\([^\n]*\n', '', text, flags=re.M)
    print('OMITTED ' + suite + ': ' + ', '.join(reversed(omitted)), flush=True)
    return text


BRIDGE = r'''
#include <stdlib.h>
#include "lz4.h"
#include "lz4hc.h"
/* Test-only workspaces adapt upstream's allocation-owning call signatures. */
static int test_default(const char *s, char *d, int n, int cap) {
    void *state = malloc(sizeof(LZ4_stream_t));
    int r;
    if (!state) abort();
    r = LZ4_compress_default(s, d, n, cap, state); free(state); return r;
}
static int test_fast(const char *s, char *d, int n, int cap, int accel) {
    void *state = malloc(sizeof(LZ4_stream_t));
    int r;
    if (!state) abort();
    r = LZ4_compress_fast(s, d, n, cap, accel, state); free(state); return r;
}
static int test_destSize(const char *s, char *d, int *n, int cap) {
    void *state = malloc(sizeof(LZ4_stream_t));
    int r;
    if (!state) abort();
    r = LZ4_compress_destSize(s, d, n, cap, state); free(state); return r;
}
static int test_hc(const char *s, char *d, int n, int cap, int level) {
    void *state = malloc(sizeof(LZ4_streamHC_t));
    int r;
    if (!state) abort();
    r = LZ4_compress_HC(s, d, n, cap, level, state); free(state); return r;
}
#define LZ4_compress_default test_default
#define LZ4_compress_fast test_fast
#define LZ4_compress_destSize test_destSize
#define LZ4_compress_HC test_hc
'''

PREBOOT = r'''
#include <linux/types.h>
static unsigned long free_mem_ptr, free_mem_end_ptr;
#define STATIC static
#include "lib/decompress_unlz4.c"
static int failures;
static void record_error(char *message) { (void)message; failures++; }
int test_preboot(unsigned char *src, long len, unsigned char *dst, long n,
                 unsigned char *arena, size_t arena_size) {
    long pos = 0;
    int ret;
    free_mem_ptr = (unsigned long)arena;
    free_mem_end_ptr = free_mem_ptr + arena_size;
    malloc_ptr = 0;
    malloc_count = 0;
    failures = 0;
    ret = __decompress(src, len, NULL, NULL, dst, n, &pos, record_error);
    return ret || failures ? -1 : 0;
}
'''

KERNEL_TESTS = r'''
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include "unittest.h"
#include "lz4.h"
#include "lz4hc.h"


TEST(kernel_real_STATIC_preboot) {
    typedef int (*pre_fn)(unsigned char *, long, unsigned char *, long,
                          unsigned char *, size_t);
    const int n = 130 * 1024, cap = LZ4_compressBound(n);
    const char *src = (const char *)UT_sample(n);
    unsigned char *block = (unsigned char *)UT_malloc(cap + 12);
    unsigned char *decoded = (unsigned char *)UT_malloc(n);
    unsigned char *arena = (unsigned char *)UT_malloc(1024);
    LZ4_stream_t *state = (LZ4_stream_t *)UT_malloc(sizeof(*state));
    void *lib = dlopen(getenv("LZ4_PREBOOT_REFERENCE"), RTLD_NOW | RTLD_LOCAL);
    pre_fn decode;
    int c, i;
    ASSERT(lib != NULL);
    decode = (pre_fn)dlsym(lib, "test_preboot");
    ASSERT(decode != NULL);
    c = LZ4_compress_default(src, (char *)block + 8, n, cap, state);
    ASSERT(c > 0);
    for (i = 0; i < 4; i++) {
        block[i] = (0x184c2102U >> (i * 8)) & 255;
        block[4 + i] = ((unsigned)c >> (i * 8)) & 255;
        block[8 + c + i] = ((unsigned)n >> (i * 8)) & 255;
    }
    ASSERT_EQ(decode(block, c + 12, decoded, n, arena, 1024), 0);
    ASSERT_MEMEQ(src, decoded, n);
    dlclose(lib);
}

TEST(kernel_sizes_and_bounds) {
    char empty = 0, out = 0;
    ASSERT_EQ(sizeof(LZ4_stream_t), 16416);
    ASSERT_EQ(sizeof(LZ4_streamHC_t), 327784);
    ASSERT_EQ(LZ4_sizeofStateHC(), sizeof(LZ4_streamHC_t));
    ASSERT_EQ(LZ4_compressBound((size_t)-1), 0);
    ASSERT_EQ(LZ4_compressBound((size_t)INT_MAX + 1), 0);
    ASSERT_EQ(LZ4_compressBound(0), 16);
    ASSERT(LZ4_decompress_safe(NULL, &out, 1, 1) < 0);
    ASSERT(LZ4_decompress_safe(&empty, NULL, 1, 1) < 0);
    ASSERT(LZ4_decompress_safe(&empty, &out, -1, 1) < 0);
    ASSERT(LZ4_decompress_safe(&empty, &out, 1, -1) < 0);
    ASSERT(LZ4_decompress_safe_partial(&empty, &out, -1, 1, 1) < 0);
    ASSERT(LZ4_initStreamHC(UT_malloc(LZ4_STREAMHC_MINSIZE),
                            LZ4_STREAMHC_MINSIZE) == NULL);
}

/* Reset on indeterminate first-use memory is an existing kernel contract.
 * Both state and output have exact allocations under ASan. Guards also detect
 * writes into/outside upstream's fixed-offset optimal parsing workspace. */
TEST(kernel_HC_caller_owned_workspace) {
    const int n = 130 * 1024, cap = LZ4_compressBound(n);
    const char *src = (const char *)UT_sample(n);
    char *out = (char *)UT_malloc(cap);
    char *decoded = (char *)UT_malloc(n);
    unsigned char *raw = (unsigned char *)UT_malloc(sizeof(LZ4_streamHC_t) + 32);
    LZ4_streamHC_t *s = (LZ4_streamHC_t *)(void *)(raw + 16);
    char *ref = (char *)UT_malloc(cap);
    int refsize = 0;
    int level, c, i;
    memset(raw, 0xa5, sizeof(*s) + 32);
    for (level = 1; level <= 16; level++) {
        memset(s, 0xa5, sizeof(*s));
        LZ4_resetStreamHC(s, level);
        c = LZ4_compress_HC_continue(s, src, out, n, cap);
        ASSERT(c > 0);
        ASSERT_EQ(LZ4_decompress_safe(out, decoded, c, n), n);
        ASSERT_MEMEQ(src, decoded, n);
        ASSERT_EQ(s->internal_donotuse.hasWorkspace, 1);
        if (level == 12) { refsize = c; memcpy(ref, out, c); }
        if (level > 12) {
            ASSERT_EQ(c, refsize);
            ASSERT_MEMEQ(out, ref, c);
        }
        for (i = 0; i < 16; i++) {
            ASSERT_EQ(raw[i], 0xa5);
            ASSERT_EQ(raw[16 + sizeof(*s) + i], 0xa5);
        }
    }
}

/* Reference library is separately built from the pinned, untouched upstream
 * sources and locally bound, so its symbols cannot resolve to kernel code. */
TEST(kernel_upstream_cross_decode) {
    typedef int (*dec_fn)(const char *, char *, int, int);
    typedef int (*comp_fn)(const char *, char *, int, int);
    typedef int (*hc_fn)(const char *, char *, int, int, int);
    void *lib = dlopen(getenv("LZ4_CODEC_REFERENCE"), RTLD_NOW | RTLD_LOCAL);
    dec_fn ref_decode;
    comp_fn ref_compress;
    hc_fn ref_hc;
    const int n = 128 * 1024, cap = LZ4_compressBound(n);
    const char *src = (const char *)UT_sample(n);
    char *block = (char *)UT_malloc(cap);
    char *decoded = (char *)UT_malloc(n);
    LZ4_stream_t *fast = (LZ4_stream_t *)UT_malloc(sizeof(*fast));
    LZ4_streamHC_t *hc = (LZ4_streamHC_t *)UT_malloc(sizeof(*hc));
    int size, kind, level, c;
    ASSERT(lib != NULL);
    ref_decode = (dec_fn)dlsym(lib, "LZ4_decompress_safe");
    ref_compress = (comp_fn)dlsym(lib, "LZ4_compress_default");
    ref_hc = (hc_fn)dlsym(lib, "LZ4_compress_HC");
    ASSERT(ref_decode && ref_compress && ref_hc);
    for (size = 0; size <= n; size = size < 20 ? size + 1 : size * 2) {
        for (kind = 0; kind < 2; kind++) for (level = 1; level <= 16; level++) {
            c = kind ? LZ4_compress_HC(src, block, size, cap, level, hc)
                     : LZ4_compress_fast(src, block, size, cap, level, fast);
            ASSERT(c > 0);
            ASSERT_EQ(ref_decode(block, decoded, c, size), size);
            ASSERT_MEMEQ(src, decoded, size);
            c = kind ? ref_hc(src, block, size, cap, level)
                     : ref_compress(src, block, size, cap);
            ASSERT(c > 0);
            ASSERT_EQ(LZ4_decompress_safe(block, decoded, c, size), size);
            ASSERT_MEMEQ(src, decoded, size);
        }
    }
    dlclose(lib);
}
'''


def run(cc, out, upstream, sanitizers, seed, compat):
    shim = out / 'shim'
    for name in ('linux/types.h', 'linux/compiler.h', 'linux/string.h',
                 'linux/errno.h', 'linux/module.h'):
        p = shim / name
        p.parent.mkdir(parents=True, exist_ok=True)
        text = SHIMS[name].replace('#define NULL ((void *)0)',
                                  '#ifndef NULL\n#define NULL ((void *)0)\n#endif')
        text = text.replace('#define __always_inline',
                            '#undef __always_inline\n#define __always_inline')
        p.write_text(text)
    codec = ROOT / 'lib/lz4'
    flags = [*cc, '-O2', '-g', '-UNDEBUG', '-DLZ4_FAST_DEC_LOOP=1',
             '-DLZ4_STATIC_LINKING_ONLY=', '-DLZ4_HC_STATIC_LINKING_ONLY=',
             '-I' + str(shim), '-I' + str(codec)]
    if sanitizers:
        flags += ['-fsanitize=' + sanitizers, '-fno-sanitize-recover=all']
        if 'undefined' in sanitizers:
            flags += ['-fsanitize-trap=undefined']
    objects = []
    for name in ('lz4_compress', 'lz4_decompress_main', 'lz4hc_compress'):
        obj = out / (name + '.o')
        subprocess.run([*flags, '-ffreestanding', '-fno-builtin', '-Wall', '-Wextra',
                        '-Werror', '-Wframe-larger-than=2048', '-c',
                        str(codec / (name + '.c')), '-o', str(obj)], check=True)
        if 'address' in sanitizers:
            with obj.open('rb') as f:
                names = {x.name for x in ELFFile(f).get_section_by_name('.symtab').iter_symbols()}
                if not any(n.startswith('__asan_') for n in names):
                    raise RuntimeError('compiler ignored ASan for ' + name)
        objects.append(str(obj))
    if 'undefined' in sanitizers:
        probe = out / 'ubsan-probe.c'
        probe.write_text('int main(void) { volatile int n = 2147483647; '
                         'volatile int r = n + 1; (void)r; return 0; }\n')
        subprocess.run([*flags, str(probe), '-o', str(out / 'ubsan-probe')], check=True)
        def no_core():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        result = subprocess.run([str(out / 'ubsan-probe')], cwd=out, preexec_fn=no_core,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode not in (-signal.SIGILL, -signal.SIGTRAP):
            raise RuntimeError('UBSan negative probe did not trap: ' + str(result.returncode))
        print('PASS: UBSan overflow probe traps; sanitizer flags are not silently ignored', flush=True)

    # The reference is intentionally NOT a source of kernel symbols.
    ref = out / 'reference.so'
    subprocess.run([*cc, '-O2', '-shared', '-fPIC', '-Wl,-Bsymbolic',
                    str(upstream / 'lib/lz4.c'), str(upstream / 'lib/lz4hc.c'),
                    '-o', str(ref)], check=True)
    # Include the real kernel public header and preboot allocator/wrapper.
    for name in ('linux/lz4.h', 'linux/decompress/mm.h'):
        p = shim / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('#include "' + str(ROOT / 'include' / name) + '"\n')
    p = shim / 'asm/unaligned.h'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('''#include <linux/types.h>
static inline u32 get_unaligned_le32(const void *p) {
    const u8 *s = (const u8 *)p;
    return s[0] | (u32)s[1] << 8 | (u32)s[2] << 16 | (u32)s[3] << 24;
}
''')
    preboot = out / 'preboot.so'
    (out / 'preboot.c').write_text(PREBOOT)
    subprocess.run([*flags, '-ffreestanding', '-fno-builtin', '-shared', '-fPIC',
                    '-Wl,-Bsymbolic', '-Wno-pointer-sign', '-I' + str(ROOT), str(out / 'preboot.c'),
                    '-o', str(preboot)], check=True)
    (out / 'bridge.h').write_text(BRIDGE)
    tests = []
    for suite in ('lz4', 'lz4hc'):
        p = out / ('unittest_' + suite + '.c')
        p.write_text(adapt_tests((upstream / 'tests/unit' / p.name).read_text(), suite))
        obj = out / (suite + '-tests.o')
        subprocess.run([*flags, '-I' + str(upstream / 'tests/unit'),
                        '-include', str(out / 'bridge.h'), '-c', str(p),
                        '-o', str(obj)], check=True)
        tests.append(str(obj))
    extra = out / 'kernel-tests.c'
    extra.write_text(KERNEL_TESTS)
    exe = out / 'codec-tests'
    subprocess.run([*flags, '-I' + str(upstream / 'tests/unit'),
                    '-I' + str(upstream / 'tests/tools'),
                    '-I' + str(upstream / 'programs'), '-I' + str(upstream / 'lib'),
                    str(extra), str(upstream / 'tests/unit/unittest.c'),
                    str(upstream / 'tests/tools/datagen.c'), str(upstream / 'lib/xxhash.c'),
                    *objects, *tests, '-ldl', '-o', str(exe)], check=True)
    subprocess.run([str(exe), '-s' + str(seed)], check=True,
                   env={**os.environ, 'LZ4_CODEC_REFERENCE': str(ref),
                        'LZ4_PREBOOT_REFERENCE': str(preboot)})
    if compat:
        old_ref = out / 'reference-1.10.so'
        subprocess.run([*cc, '-O2', '-shared', '-fPIC', '-Wl,-Bsymbolic',
                        str(compat / 'lib/lz4.c'), str(compat / 'lib/lz4hc.c'),
                        '-o', str(old_ref)], check=True)
        print('Cross-decoding upstream v1.10.0 in both directions', flush=True)
        subprocess.run([str(exe), 'kernel_upstream_cross_decode', '-s' + str(seed)],
                       check=True, env={**os.environ, 'LZ4_CODEC_REFERENCE': str(old_ref)})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--upstream', required=True, type=Path,
                    help='extracted upstream ' + PIN + ' tree')
    ap.add_argument('--cc', default=os.environ.get('CC', 'clang'))
    ap.add_argument('--output', type=Path)
    ap.add_argument('--ubsan', action='store_true')
    ap.add_argument('--asan', action='store_true')
    ap.add_argument('--compat-upstream', type=Path, help='optional upstream v1.10.0 tree')
    ap.add_argument('--seed', type=int, default=1)
    args = ap.parse_args()
    for name, digest in HASHES.items():
        actual = hashlib.sha256((args.upstream / name).read_bytes()).hexdigest()
        if actual != digest:
            ap.error(name + ': not the pinned upstream source')
    if args.compat_upstream:
        for name, digest in COMPAT_HASHES.items():
            if hashlib.sha256((args.compat_upstream / name).read_bytes()).hexdigest() != digest:
                ap.error(name + ': not upstream v1.10.0')
    sanitizers = ','.join(s for s, enabled in [('address', args.asan),
                                              ('undefined', args.ubsan)] if enabled)
    compat = args.compat_upstream.resolve() if args.compat_upstream else None
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        run(shlex.split(args.cc), args.output.resolve(), args.upstream.resolve(),
            sanitizers, args.seed, compat)
    else:
        with tempfile.TemporaryDirectory(prefix='lz4-codec-') as tmp:
            run(shlex.split(args.cc), Path(tmp), args.upstream.resolve(),
                sanitizers, args.seed, compat)


if __name__ == '__main__':
    main()
