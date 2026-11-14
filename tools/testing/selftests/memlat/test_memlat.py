#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Extracted-source memlat checks. Host mocks, not a PMU/SMP/device proof."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import re
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
NAMES = ['memlat_read_cpu', 'memlat_stall_pct', 'memlat_clear_stats',
         'compute_perf_counters', 'get_cnt', 'delete_events', 'stop_hwmon',
         'alloc_attr', 'set_events', 'start_hwmon', 'init_cpu_stats']


def functions(text, name):
    matches = list(re.finditer(r'^[^\n]*\b' + name + r'\([^;]*?\)\n\{', text, re.M))
    result = []
    for m in matches:
        end = m.end()
        depth = 1
        while depth:
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        result.append(text[m.start():end])
    assert result, name
    return result


def provenance_check():
    manifest = json.loads((ROOT / 'Documentation/dev-tools/azyr-sm6250-memlat-native-validation.json').read_text())
    paths = {'drivers/devfreq/arm-memlat-mon.c', 'drivers/soc/qcom/scm.c', 'include/soc/qcom/scm.h'}
    assert manifest['schema'] == 1 and set(manifest['postimage_sha256']) == paths
    assert set(manifest['preimage_sha256']) == paths
    assert manifest['patch'] == 'Documentation/dev-tools/azyr-sm6250-memlat-native.diff'
    patch = ROOT / manifest['patch']
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == manifest['patch_sha256']
    with tempfile.TemporaryDirectory(prefix='memlat-provenance-') as directory:
        for path in paths:
            data = (ROOT / path).read_bytes()
            assert hashlib.sha256(data).hexdigest() == manifest['postimage_sha256'][path], path
            target = Path(directory) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=directory, check=True)
        for path in paths:
            assert hashlib.sha256((Path(directory) / path).read_bytes()).hexdigest() == manifest['preimage_sha256'][path], path
        old = (Path(directory) / 'drivers/soc/qcom/scm.c').read_text()
        new = (ROOT / 'drivers/soc/qcom/scm.c').read_text()
        for name in ['__scm_call_armv8_64', '__scm_call_armv8_32']:
            before = [f for f in functions(old, name) if 'asm volatile' in f]
            after = functions(new, name + '_raw')
            assert len(before) == len(after)
            for a, b in zip(before, after):
                assert a[a.index('{'):] == b[b.index('{'):], name
        for name in ['smc', 'scm_call_atomic1', 'scm_call_atomic1_1', 'scm_call_atomic2',
                     'scm_call_atomic3', 'scm_call_atomic4_3', 'scm_call_atomic5_3']:
            assert functions(old, name) == functions(new, name), name
    print('PASS: exact three-source inverse patch/hash provenance, unchanged ARMv8 assembly bodies and unchanged legacy workers')


def model_source(source):
    types = source[source.index('enum ev_index {'):source.index('/* No partial sample')]
    header = (ROOT / 'drivers/devfreq/governor_memlat.h').read_text()
    stats = header[header.index('struct dev_stats {'):header.index('};', header.index('struct dev_stats {')) + 2]
    body = '\n\n'.join(functions(source, n)[0] for n in NAMES)
    return ((HERE / 'model.c').read_text().replace('/* DEV_STATS */', stats)
            .replace('/* DRIVER_TYPES */', types).replace('/* FUNCTIONS */', body))


def source_contracts(source):
    get = functions(source, 'get_cnt')[0]
    assert 'if (idle_cpu(cpu))' in get and 'cpu_isolated(cpu)' in get
    assert 'generic_exec_single' not in source
    assert 'perf_event_read_value' not in source
    assert 'preempt_disable' not in get and 'wait_for_completion_timeout' not in get
    assert get.index('cpus_read_lock()') < get.index('smp_call_function_single_async')
    assert get.index('wait_for_completion') < get.index('cpus_read_unlock()')
    assert get.index('scm_call_in_progress()') < get.index('smp_call_function_single_async')
    assert 'scm_call_in_progress' not in functions(source, 'delete_events')[0]
    assert functions(source, 'memlat_read_cpu')[0].rstrip().endswith('complete(&cpustats->done);\n}')
    assert 'devm_kcalloc(dev, nr_cpu_ids,' in source
    assert '(&(cpu_grp)->cpustats[(cpu)])' in source
    assert 'MODULE_LICENSE("GPL v2")' in source
    scm = (ROOT / 'drivers/soc/qcom/scm.c').read_text()
    header = (ROOT / 'include/soc/qcom/scm.h').read_text()
    assert 'EXPORT_SYMBOL_GPL(scm_call_in_progress)' in scm
    assert 'static inline bool scm_call_in_progress(void)' in header
    assert '#if IS_ENABLED(CONFIG_QCOM_SCM)' in header
    assert scm.count('atomic_inc(&scm_call_count);') == 3
    assert scm.count('atomic_dec(&scm_call_count);') == 3
    for name, count in [('__scm_call_armv8_64', 1), ('__scm_call_armv8_32', 2)]:
        raws = functions(scm, name + '_raw')
        assert len(raws) == count
        for raw in raws:
            assert raw.startswith('static noinline int ')
            assert 'asm volatile' in raw and 'scm_call_count' not in raw
        wrappers = [f for f in functions(scm, name) if 'scm_call_count' in f]
        assert len(wrappers) == count
        for wrapper in wrappers:
            assert wrapper.index('atomic_inc') < wrapper.index('smp_mb__after_atomic') < wrapper.index(name + '_raw(')
            assert wrapper.index(name + '_raw(') < wrapper.index('smp_mb__before_atomic') < wrapper.index('atomic_dec')
            assert 'preempt_disable' not in wrapper and 'raw_smp_processor_id' not in wrapper
    print('PASS: public async API, completion ownership, sparse allocation, unguarded teardown and non-pinning SCM wrapper contracts')


def compile_run(cc, directory, text, label, negative=False):
    p = Path(directory) / (label + '.c')
    exe = p.with_suffix('')
    p.write_text(text)
    subprocess.run(cc + ['-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', '-Wno-sign-compare',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        str(p), '-o', str(exe)], check=True)
    result = subprocess.run([str(exe)], capture_output=True, text=True)
    if negative:
        assert result.returncode and ('Assertion' in result.stderr or 'assertion' in result.stderr), (label, result.stdout, result.stderr)
        print('PASS: compiled semantic mutant rejected: ' + label)
    else:
        assert result.returncode == 0, (label, result.stdout, result.stderr)
        print(result.stdout.strip())


def scm_wrapper_check(cc, directory):
    scm = (ROOT / 'drivers/soc/qcom/scm.c').read_text()
    wrappers = []
    for name in ['__scm_call_armv8_64', '__scm_call_armv8_32']:
        variants = [f for f in functions(scm, name) if 'atomic_inc' in f]
        for index, wrapper in enumerate(variants):
            if index:
                wrapper = wrapper.replace(name, name + '_arm32')
            wrappers.append(wrapper)
    prelude = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef uint64_t u64;
typedef uint32_t u32;
typedef struct { int counter; } atomic_t;
static atomic_t scm_call_count;
static int barriers, calls, nest, depth=1;
static int atomic_read(atomic_t *a) { return a->counter; }
static void atomic_inc(atomic_t *a) { a->counter++; }
static void atomic_dec(atomic_t *a) { a->counter--; }
static void smp_mb__after_atomic(void) { barriers++; }
static void smp_mb__before_atomic(void) { barriers++; }
'''
    prototypes, raw_functions = [], []
    for index, wrapper in enumerate(wrappers):
        name = re.search(r'\b(__scm_call_armv8_\w+)\(', wrapper).group(1)
        signature = wrapper[:wrapper.index('{')].replace(name + '(', name + '_raw(')
        prototypes.append(signature.rstrip() + ';')
        word = 'x' if index == 0 else 'w'
        value = '0x1100000000ULL' if index == 0 else '0xf0000000ULL'
        nesting = '''
 if (nest) {
  u64 a,b,c; nest=0; depth=2;
  assert(__scm_call_armv8_32(0xf0000000,0xf0000001,0xf0000002,
                           0xf0000003,0xf0000004,0xf0000005,&a,&b,&c)==-55);
  assert(scm_call_count.counter==1); depth=1;
 }
''' if index == 0 else ''
        raw_functions.append(signature + '{\n' +
                             'u64 values[]={' + ','.join(word+str(i) for i in range(6)) + '};\n' +
                             'assert(scm_call_in_progress() && scm_call_count.counter==depth);\n' +
                             'for(int i=0;i<6;i++) assert(values[i]==' + value + '+i);\n' +
                             nesting +
                             '*ret1=values[1];*ret2=values[2];*ret3=values[3];calls++;return -55;\n}\n')
    main = '''
int main(void) {
 u64 a,b,c;
 assert(!scm_call_in_progress()); nest=1;
 assert(__scm_call_armv8_64(0x1100000000ULL,0x1100000001ULL,0x1100000002ULL,
                          0x1100000003ULL,0x1100000004ULL,0x1100000005ULL,&a,&b,&c)==-55);
 assert(a==0x1100000001ULL && b==0x1100000002ULL && c==0x1100000003ULL);
 assert(!scm_call_in_progress());
 assert(__scm_call_armv8_32(0xf0000000,0xf0000001,0xf0000002,
                          0xf0000003,0xf0000004,0xf0000005,&a,&b,&c)==-55);
 assert(a==0xf0000001ULL && b==0xf0000002ULL && c==0xf0000003ULL);
 assert(!scm_call_in_progress());
 assert(__scm_call_armv8_32_arm32(0xf0000000,0xf0000001,0xf0000002,
                                0xf0000003,0xf0000004,0xf0000005,&a,&b,&c)==-55);
 assert(a==0xf0000001ULL && b==0xf0000002ULL && c==0xf0000003ULL);
 assert(!scm_call_in_progress() && calls==4 && barriers==8);
 puts("PASS: three extracted SCM C wrappers preserve inputs/outputs/errors and balance nested global accounting (mock secure workers)");
 return 0;
}
'''
    code = (prelude + functions(scm, 'scm_call_in_progress')[0] + '\n' +
            '\n'.join(prototypes + wrappers + raw_functions) + main)
    compile_run(cc, directory, code, 'scm-wrappers')


def arithmetic_check(cc, directory, source):
    code = ('#include <stdint.h>\n#include <limits.h>\n'
            'typedef uint64_t u64;\n#define min(a,b) ((a)<(b)?(a):(b))\n'
            '#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))\n'
            'static u64 div64_u64(u64 a,u64 b){return a/b;}\n'
            'static u64 div64_u64_rem(u64 a,u64 b,u64 *r){*r=a%b;return a/b;}\n')
    code += functions(source, 'memlat_stall_pct')[0].replace('static unsigned int', 'unsigned int', 1)
    p = Path(directory) / 'arithmetic.c'
    p.write_text(code)
    so = p.with_suffix('.so')
    subprocess.run(cc + ['-std=gnu11', '-O2', '-Wall', '-Werror', '-shared', '-fPIC', str(p), '-o', str(so)], check=True)
    library = ctypes.CDLL(str(so))
    fn = library.memlat_stall_pct
    fn.argtypes = [ctypes.c_uint64, ctypes.c_uint64]
    fn.restype = ctypes.c_uint
    rng = random.Random(2730)
    cases = [(x, y) for x in range(102) for y in range(102)]
    for value in [0, 1, 99, 100, 101, 2**32, 2**63, 2**64 - 1]:
        for offset in range(-2, 3):
            c = max(0, min(2**64 - 1, value + offset))
            cases += [(c, value), (value, c)]
    cases += [(rng.getrandbits(64), rng.getrandbits(64)) for _ in range(10000)]
    for stall, cycles in cases:
        expected = min(stall, cycles) * 100 // cycles if cycles else 0
        assert fn(stall, cycles) == expected, (stall, cycles, expected, fn(stall, cycles))
    print('PASS: ' + str(len(cases)) + ' extracted u64 stall-percent cases, including overflow and zero cycles')


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='gcc')
    parser.add_argument('--self-test-negatives', action='store_true')
    args = parser.parse_args()
    cc = shlex.split(args.cc)
    source = (ROOT / 'drivers/devfreq/arm-memlat-mon.c').read_text()
    provenance_check()
    source_contracts(source)
    with tempfile.TemporaryDirectory(prefix='memlat-model-') as directory:
        compile_run(cc, directory, model_source(source), 'positive')
        arithmetic_check(cc, directory, source)
        scm_wrapper_check(cc, directory)
        if args.self_test_negatives:
            mutations = {
                'skip-drain': ('wait_for_completion(&cpustats->done);', '(void)wait_for_completion;'),
                'skip-busy-cleanup': ('cpustats->have_prev = false;\n\tcpustats->sample_valid = false;',
                                      'if (scm_call_in_progress()) return;\n\tcpustats->have_prev = false;\n\tcpustats->sample_valid = false;'),
                'partial-publication': ('goto out;\n\t}', 'break;\n\t}'),
                'skip-creation-unwind': ('goto unwind;', 'goto out;'),
                'missing-hotplug-lock': ('cpus_read_lock();', '(void)cpus_read_lock;'),
                'wake-observed-idle': ('if (idle_cpu(cpu))', 'if (false && idle_cpu(cpu))'),
                'sample-isolated': ('cpu_isolated(cpu)', '(false && cpu_isolated(cpu))'),
            }
            for label, (old, new) in mutations.items():
                assert source.count(old) == 1, label
                mutated = model_source(source.replace(old, new, 1))
                # Keep unreachable labels legal: negatives must fail at runtime.
                mutated = re.sub(r'^(out|unwind):$', r'\1: __attribute__((unused));', mutated, flags=re.M)
                compile_run(cc, directory, mutated, label, negative=True)


if __name__ == '__main__':
    main()
