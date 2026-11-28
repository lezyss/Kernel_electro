#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Bounded extracted-source checks for Azyr items 36/41; no hardware tests."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HIST = ROOT / "Documentation/dev-tools/carry-over/batch-01/historical"
BASE = 'Documentation/dev-tools/azyr-sm6250-036-041'
IPA = 'drivers/platform/msm/ipa/ipa_v3/ipa_uc_wdi.c'
STATS = 'drivers/cpufreq/cpufreq_stats.c'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(text, name):
    match = re.search(r'^[^\n]*\b' + name + r'\([^;]*?\)\n\{', text, re.M)
    assert match, name
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]


def provenance(directory):
    manifest = json.loads((HIST / Path(BASE + '-validation.json').name).read_text())
    assert manifest['schema'] == 1 and manifest['review_items'] == [36, 41]
    assert set(manifest['preimage_sha256']) == set(manifest['postimage_sha256']) == {IPA, STATS}
    assert manifest['patch'] == BASE + '.diff'
    patch = HIST / Path(manifest['patch']).name
    assert digest(patch.read_bytes()) == manifest['patch_sha256']
    before, after = {}, {}
    for path in [IPA, STATS]:
        data = (ROOT / path).read_bytes()
        assert digest(data) == manifest['postimage_sha256'][path], path
        after[path] = data.decode()
        target = Path(directory) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=directory, check=True)
    review = json.loads((HIST / 'azyr-sm6250-review-04-validation.json').read_text())
    for path in [IPA, STATS]:
        data = (Path(directory) / path).read_bytes()
        assert digest(data) == manifest['preimage_sha256'][path] == review['source_sha256'][path]
        before[path] = data.decode()
    print('PASS: exact two-source patch/inverse hashes and reviewed preimage chain')
    return before, after


def fixtures(before, after):
    function = extract(after[IPA], 'ipa3_disable_wdi_pipe')
    declaration = re.search(r'\t\tconst unsigned long delay_us = IPA_UC_POLL_SLEEP_USEC \*\n\s*IPA_UC_POLL_SLEEP_USEC;\n\n', function).group()
    call = re.search(r'usleep_range\(delay_us, delay_us \+ delay_us / 5\);', function).group()
    original_call = ('usleep_range(IPA_UC_POLL_SLEEP_USEC * IPA_UC_POLL_SLEEP_USEC,\n'
                     '\t\t\tIPA_UC_POLL_SLEEP_USEC * IPA_UC_POLL_SLEEP_USEC);')
    restored = function.replace(declaration, '').replace(call, original_call)
    assert restored == extract(before[IPA], 'ipa3_disable_wdi_pipe')
    assert after[IPA].replace(function, restored) == before[IPA]
    assert not re.search(r'\d+\.\d+', declaration + call)
    macro = re.search(r'^#define IPA_UC_POLL_SLEEP_USEC\s+\d+', after[IPA], re.M).group()
    sleep = '''#include <assert.h>
#include <stdio.h>
static unsigned long minimum, maximum;
static void usleep_range(unsigned long a, unsigned long b) {minimum=a; maximum=b;}
''' + macro + '\nint main(void) {\n' + declaration + call + '''
assert(minimum==10000 && maximum==12000);
assert(minimum<=maximum && maximum-minimum==minimum/5);
puts("PASS: extracted IPA delay is integer-only 10000..12000 us; other IPA code unchanged");
return 0;
}
'''
    native = extract(before[STATS], 'cpufreq_stats_record_transition')
    corrected = extract(after[STATS], 'cpufreq_stats_record_transition')
    normalized = corrected.replace('unlikely(!stats)', '!stats').replace(
        'unlikely(old_index == -1 || new_index == -1 || old_index == new_index)',
        'old_index == -1 || new_index == -1 || old_index == new_index')
    assert normalized == native and after[STATS].replace(corrected, native) == before[STATS]
    stats = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define unlikely(x) __builtin_expect(!!(x), 0)
#define pr_debug(...) ((void)0)
struct cpufreq_stats {int last_index, max_state; unsigned trans_table[64], total_trans, updates;};
struct cpufreq_policy {struct cpufreq_stats *stats;};
static int freq_table_get_index(struct cpufreq_stats *s,unsigned freq) {return freq<8 ? (int)freq : -1;}
static void cpufreq_stats_update(struct cpufreq_stats *s) {s->updates++;}
''' + native.replace('cpufreq_stats_record_transition(', 'native_transition(', 1) + '\n' + corrected + r'''
int main(void) {
 int present,old,new,cases=0;
 for(present=0;present<2;present++) for(old=-1;old<8;old++) for(new=0;new<10;new++) {
  struct cpufreq_stats a,b; struct cpufreq_policy p,q; unsigned changed;
  int i,index=new<8?new:-1;
  memset(&a,0,sizeof(a)); a.last_index=old; a.max_state=8; a.total_trans=17;
  for(i=0;i<64;i++) a.trans_table[i]=i+100;
  b=a; p.stats=present?&a:0; q.stats=present?&b:0;
  native_transition(&p,new); cpufreq_stats_record_transition(&q,new);
  assert(!memcmp(&a,&b,sizeof(a)));
  changed=present && old>=0 && index>=0 && old!=index;
  assert(b.total_trans==17+changed && b.updates==changed);
  assert(b.last_index==(changed?index:old));
  for(i=0;i<64;i++) assert(b.trans_table[i]==(unsigned)i+100+(changed && i==old*8+index));
  cases++;
 }
 assert(cases==180);
 puts("PASS: 180 extracted cpufreq transition cases preserve guards, counters, last index and transition matrix");
 return 0;
}
'''
    return sleep, stats


def compile_run(cc, directory, name, text, negative=False, general_regs=False):
    source = Path(directory) / (name + '.c')
    binary = source.with_suffix('')
    source.write_text(text)
    flags = ['-std=gnu89', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
             '-fsanitize=undefined', '-fno-sanitize-recover=all']
    if general_regs:
        flags += ['-mgeneral-regs-only']
    subprocess.run(cc + flags + [str(source), '-o', str(binary)], check=True)
    result = subprocess.run([str(binary)], capture_output=True, text=True)
    if negative:
        assert result.returncode and 'assert' in result.stderr.lower(), (name, result.stdout, result.stderr)
        print('PASS: compiled negative control rejected: ' + name)
    else:
        assert result.returncode == 0, (name, result.stdout, result.stderr)
        print(result.stdout.strip())


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='gcc')
    parser.add_argument('--self-test-negatives', action='store_true')
    parser.add_argument('--general-regs-only', action='store_true', help='also forbid host FP/vector registers in delay fixture')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='cpufreq-ipa-tests-') as directory:
        before, after = provenance(directory)
        sleep, stats = fixtures(before, after)
        cc = shlex.split(args.cc)
        compile_run(cc, directory, 'ipa-delay', sleep, general_regs=args.general_regs_only)
        compile_run(cc, directory, 'cpufreq-stats', stats)
        if args.self_test_negatives:
            compile_run(cc, directory, 'changed-minimum', sleep.replace('usleep_range(delay_us,', 'usleep_range(delay_us / 2,'), negative=True)
            compile_run(cc, directory, 'missing-slack', sleep.replace('delay_us + delay_us / 5', 'delay_us'), negative=True)
            compile_run(cc, directory, 'broken-stats-guard', stats.replace('unlikely(old_index == -1 || new_index == -1 || old_index == new_index)', 'unlikely(old_index == -1 || new_index == -1 || old_index != new_index)'), negative=True)
    print('LIMITS: host mocks/UBSan only; no target build, real timer/PMU, concurrent cpufreq, modem, device or power proof')


if __name__ == '__main__':
    main()
