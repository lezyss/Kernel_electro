#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""v3.3.1-38 extracted helper tests; not target/kernel/device execution."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "susfs"))
from provenance_240 import reviewed_preimages

ROOT = Path(__file__).resolve().parents[4]
BASE = 'Documentation/dev-tools/kernelsu-updates/v3.3.1-38'


def extract(text, name):
    # Documentation can contain name() before the real definition.
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    match = re.search(r'^[^\n;{}]*?\b' + name + r'\([^;{}]*\)\s*\{', text, re.M)
    assert match, name
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]


def provenance():
    previous = reviewed_preimages(ROOT)
    def before_susfs(path):
        return previous.get(path, (ROOT / path).read_bytes())
    update = json.loads((ROOT / (BASE + '.json')).read_text())
    manifest = json.loads((ROOT / 'drivers/kernelsu/UPSTREAM.json').read_text())
    assert update['commit'] == manifest['commit'] == 'feeec8e4059e3bb0ecdd1827b687b69f1cf4a2fb'
    assert update['tag'] == manifest['tag'] == 'v3.3.1-38'
    assert len(update['changes']) == len({r['path'] for r in update['changes']}) == 17
    assert sum(r['old_upstream_blob'] != r['new_upstream_blob'] for r in update['changes']) == 16
    assert update['local_version_display_adaptations'] == ['drivers/kernelsu/supercall/dispatch.c']
    assert update['patch'] == BASE + '.diff'
    patch = (ROOT / update['patch']).read_bytes()
    assert hashlib.sha256(patch).hexdigest() == update['patch_sha256']
    for record in update['changes']:
        path = record['path']
        assert path.startswith('drivers/kernelsu/') and '..' not in Path(path).parts
        assert hashlib.sha256(before_susfs(path)).hexdigest() == record['after_sha256']
        assert manifest['git_blob_sha1'][path.removeprefix('drivers/kernelsu/')] == record['new_upstream_blob']
    # Reconstruct the exact reviewed local preimages and replay the full update.
    with tempfile.TemporaryDirectory(prefix='ksu-update-replay-') as d:
        tree = Path(d)
        for record in update['changes']:
            f = tree / record['path']
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(before_susfs(record['path']))
        subprocess.run(['git', 'apply', '--reverse', '--whitespace=nowarn', '-'],
                       input=patch, cwd=tree, check=True)
        for record in update['changes']:
            assert hashlib.sha256((tree / record['path']).read_bytes()).hexdigest() == record['before_sha256']
        subprocess.run(['git', 'apply', '--whitespace=nowarn', '-'], input=patch, cwd=tree, check=True)
        for record in update['changes']:
            assert (tree / record['path']).read_bytes() == before_susfs(record['path'])
    print('PASS: pinned 16-file upstream delta + honest display update, exact inverse/forward replay and source hashes')


def finasu_negatives():
    from test_finasu import check
    manifest_path = 'Documentation/dev-tools/finasu-manager.json'
    manifest = json.loads((ROOT / manifest_path).read_text())
    paths = set(manifest['postimage_sha256']) | {manifest_path, BASE + '.json',
                                               'drivers/kernelsu/Makefile'}
    with tempfile.TemporaryDirectory(prefix='ksu-version-successor-') as d:
        root = Path(d)
        for name in paths:
            f = root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes((ROOT / name).read_bytes())
        with contextlib.redirect_stdout(io.StringIO()):
            check(root)
        dispatch = root / 'drivers/kernelsu/supercall/dispatch.c'
        original = dispatch.read_text()
        for name, text in [('false-version', original.replace('v3.3.1-38', 'v9.9.9')),
                           ('resealed-body', original + '\n/* unauthorized dispatch edit */\n')]:
            dispatch.write_text(text)
            update = json.loads((root / (BASE + '.json')).read_text())
            update['postimage_sha256']['drivers/kernelsu/supercall/dispatch.c'] = hashlib.sha256(dispatch.read_bytes()).hexdigest()
            (root / (BASE + '.json')).write_text(json.dumps(update))
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    check(root)
            except ValueError:
                print('PASS: rejected FinaSU ' + name)
            else:
                raise AssertionError('accepted ' + name)
        dispatch.write_text(original)


def source(mutant=None):
    compat = (ROOT / 'drivers/kernelsu/kernel_compat.h').read_text()
    patch = (ROOT / 'drivers/kernelsu/downstream/vmap_patch.h').read_text()
    assert compat.index('#define copy_from_user copy_from_user_retry') > compat.index('static __always_inline long copy_from_user_retry(')
    bodies = '\n'.join(extract(compat, n) for n in
                       ['copy_to_kernel_nofault', 'ksu_copy_from_user_nofault', 'copy_from_user_retry', 'ksu_strscpy'])
    bodies = '#define copy_from_user_nofault ksu_copy_from_user_nofault\n' + bodies
    bodies += '\n' + '\n'.join(extract(patch, n) for n in
                               ['patch_ptr_slot_kick_cpu', 'patch_ro_slot_vmap', 'patch_ro_slot'])
    if mutant == 'fault-status':
        bodies = bodies.replace('return ret ? -EFAULT : 0;', 'return 0;')
    elif mutant == 'address-limit':
        bodies = bodies.replace('set_fs(old_fs);', '(void)old_fs;')
    elif mutant == 'fallback':
        bodies = bodies.replace('return patch_ro_slot_vmap(slot_ptr, new_ptr);', 'return 0;')
    elif mutant == 'zero-size':
        bodies = bodies.replace('if (!count)\n\t\treturn -E2BIG;', 'if (!count)\n\t\treturn 0;')
    return r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <sys/types.h>
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wunused-variable"
#pragma GCC diagnostic ignored "-Wunused-function"
#define __weak
#define __user
#define __force
#undef __always_inline
#define __always_inline inline
#define noinline __attribute__((noinline))
#define nodiscard
#define likely(v) (v)
#define PAGE_MASK (~(uintptr_t)4095)
#define VM_MAP 0
#define PAGE_KERNEL 0
#define KERNEL_DS 99
#define USER_DS 17
#define assume_dereferenceable(p,n) ((void)0)
#define WRITE_ONCE(p,v) ((p)=(v))
typedef int mm_segment_t;
static int fs=55, depth, badcopy, slowerr, slowcalls, kicks, barriers, maps, unmaps, no_page, no_map;
static mm_segment_t get_fs(void){return fs;}
static void set_fs(mm_segment_t f){fs=f;}
static void pagefault_disable(void){depth++;}
static void pagefault_enable(void){assert(depth>0);depth--;}
static long __copy_to_user_inatomic(void *d,const void *s,size_t n){assert(fs==KERNEL_DS && depth>0);if(badcopy)return n;memcpy(d,s,n);return 0;}
static long __copy_from_user_inatomic(void *d,const void *s,size_t n){assert(fs==USER_DS && depth>0);if(badcopy)return n;memcpy(d,s,n);return 0;}
static long copy_from_user(void *d,const void *s,unsigned long n){slowcalls++;if(slowerr)return slowerr;memcpy(d,s,n);return 0;}
static void kick_all_cpus_sync(void){kicks++;}
static void smp_mb(void){barriers++;}
struct page {uintptr_t base;};
#define __pa(x) (x)
static struct page pg;
static struct page *phys_to_page(uintptr_t base){pg.base=base;return no_page?NULL:&pg;}
static void *vmap(struct page **p,int count,int flags,int prot){maps++;return no_map?NULL:(void *)(*p)->base;}
static void vunmap(void *p){unmaps++;}
''' + bodies + r'''
#define copy_from_user copy_from_user_retry
int main(void){unsigned cases=0;char in[8]="sample",out[8];
for(int d=0;d<3;d++)for(int fail=0;fail<2;fail++){
 depth=d;fs=55;badcopy=fail;
 assert(copy_to_kernel_nofault(out,in,8)==(fail?-EFAULT:0));assert(fs==55 && depth==d);cases++;
 assert(ksu_copy_from_user_nofault(out,in,8)==(fail?-EFAULT:0));assert(fs==55 && depth==d);cases++;
 for(int slow=0;slow<2;slow++){
  slowcalls=0;slowerr=slow?3:0;
  assert(copy_from_user(out,in,8)==(fail?slowerr:0));assert(slowcalls==fail && fs==55 && depth==d);cases++;
 }
} depth=0;fs=55;
for(size_t len=0;len<32;len++)for(size_t count=0;count<35;count++){
 char src[40],dst[40];memset(src,'a',len);src[len]=0;memset(dst,0x55,sizeof(dst));
 ssize_t ret=ksu_strscpy(dst,src,count);
 assert(ret==(!count||len>=count?-E2BIG:(ssize_t)len));
 if(count){size_t copied=len<count?len:count-1;assert(!memcmp(dst,src,copied) && !dst[copied]);}
 for(size_t j=count;j<sizeof(dst);j++)assert((unsigned char)dst[j]==0x55);cases++;
}
for(int fail=0;fail<2;fail++)for(int pagefail=0;pagefail<2;pagefail++)for(int mapfail=0;mapfail<2;mapfail++){
 uintptr_t slot=123;badcopy=fail;no_page=pagefail;no_map=mapfail;kicks=barriers=maps=unmaps=0;
 int expected=fail?(pagefail?-EFAULT:mapfail?-ENOMEM:0):0;
 assert(patch_ro_slot((uintptr_t)&slot,456)==expected);
 assert(slot==(expected?123:456));assert(kicks==(expected?0:1));
 assert(maps==(fail&&!pagefail));assert(unmaps==(fail&&!pagefail&&!mapfail));
 assert(fs==55 && !depth);cases++;
}
assert(patch_ro_slot(0,1)==-EINVAL);assert(patch_ro_slot(1,0)==-EINVAL);cases+=2;
printf("PASS:%u extracted uaccess retry/address-limit/fault/strscpy/RO-slot fallback cases\n",cases);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    provenance()
    if args.self_test_negatives:
        finasu_negatives()
    with tempfile.TemporaryDirectory(prefix='ksu-update-models-') as d:
        for mutant in [None] + (['fault-status', 'address-limit', 'fallback', 'zero-size'] if args.self_test_negatives else []):
            p = Path(d) / (str(mutant) + '.c')
            p.write_text(source(mutant))
            exe = p.with_suffix('')
            subprocess.run(['gcc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-Wno-misleading-indentation', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            str(p), '-o', str(exe)], check=True)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=5,
                                    preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            assert bool(result.returncode) == bool(mutant), result.stdout + result.stderr
            print('PASS: rejected ' + mutant if mutant else result.stdout.strip())
    print('LIMITS: host models only; not a pinned-Clang kernel build, real RO mappings, SMP, module loading or device boot proof.')


if __name__ == '__main__':
    main()
