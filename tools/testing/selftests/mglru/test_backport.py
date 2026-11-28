#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Host regression checks; does not exercise the running kernel's reclaim."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]


def cleanup_function(source):
    start = source.index('void clear_shadow_from_swap_cache(')
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def function_body(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def check_independent_windows(source):
    min_gens, max_gens = 2, 4

    def shown_sequences(min_seq, max_seq):
        first, second = 0, 1
        if min_seq[second] < min_seq[first]:
            first, second = second, first

        result = list(range(min_seq[first], max_seq[first] + 1))
        if max_seq[second] > max_seq[first]:
            start = max(min_seq[second], max_seq[first] + 1)
            result.extend(range(start, max_seq[second] + 1))
        return result

    for anon_width in range(min_gens, max_gens + 1):
        for file_width in range(min_gens, max_gens + 1):
            for anon_min in range(16):
                for file_min in range(16):
                    mins = (anon_min, file_min)
                    maxes = (anon_min + anon_width - 1,
                             file_min + file_width - 1)
                    actual = shown_sequences(mins, maxes)
                    expected = sorted(set(range(mins[0], maxes[0] + 1)) |
                                      set(range(mins[1], maxes[1] + 1)))
                    assert actual == expected and len(actual) == len(set(actual))

    for anon_width in range(min_gens, max_gens + 1):
        for file_width in range(min_gens, max_gens + 1):
            for anon_min in range(8):
                for file_min in range(8):
                    mins = (anon_min, file_min)
                    maxes = (anon_min + anon_width - 1,
                             file_min + file_width - 1)
                    for target_seq in range(max(maxes) + 2):
                        actual = [idx for idx in range(2)
                                  if (target_seq >= mins[idx] and
                                      maxes[idx] >= min_gens and
                                      target_seq <= maxes[idx] - min_gens)]
                        expected = [idx for idx in range(2)
                                    if mins[idx] <= target_seq <=
                                    maxes[idx] - min_gens]
                        assert actual == expected

    for width in range(min_gens, max_gens + 1):
        for min_seq in range(8):
            max_seq = min_seq + width - 1
            for target_seq in range(max_seq + 3):
                for empty_mask in range(1 << width):
                    empty = {seq for seq in range(min_seq, max_seq + 1)
                             if empty_mask & (1 << (seq - min_seq))}
                    actual = min_seq
                    if (max_seq >= min_gens and
                            target_seq <= max_seq - min_gens):
                        while (actual + min_gens <= max_seq and
                               actual <= target_seq and actual in empty):
                            actual += 1
                    assert actual <= target_seq + 1 or target_seq < min_seq
                    if target_seq > max_seq - min_gens:
                        assert actual == min_seq

    show = function_body(source, 'static int lru_gen_seq_show(')
    assert 'min_seq[second] < min_seq[first]' in show
    assert 'lru_gen_seq_show_range(m, lruvec, max_seq, min_seq,' in show
    age = function_body(source, 'static int run_aging(')
    assert 'seq <= max_seq[type]' in age and 'seq != max_seq[type]' in age
    assert 'return -EEXIST' not in age
    isolate = function_body(source, 'static int isolate_pages(')
    assert 'target_seq >= min_seq[type]' in isolate
    assert 'target_seq <= max_seq[type] - MIN_NR_GENS' in isolate
    assert 'time_before(anon_birth, file_birth)' not in isolate
    assert 'get_type_to_scan(lruvec, swappiness, &tier)' in isolate
    advance = function_body(source, 'static bool try_to_inc_min_seq(')
    assert 'target_seq > lrugen->max_seq[type] - MIN_NR_GENS' in advance
    assert 'min_seq[type] <= target_seq' in advance
    evict = function_body(source, 'static int evict_pages(')
    assert 'target_seq > lrugen->max_seq[type_i] - MIN_NR_GENS' in evict
    assert 'PageSwapCache(page)' in evict
    pageout = function_body(source, 'static pageout_t pageout(')
    assert '!PageWriteback(page) && (res || !PageLocked(page))' in pageout
    skip_mm = function_body(source, 'static bool should_skip_mm(')
    assert 'mm->lru_gen.nodes[type]' in skip_mm
    age_lruvec = function_body(source, 'static bool age_lruvec(')
    assert 'pace_aging[!type] = true;' in age_lruvec
    assert 'max_seq[!type] - min_seq[!type] + 1 < MAX_NR_GENS' in age_lruvec
    nr_to_scan = function_body(source, 'static long get_nr_to_scan(')
    assert 'return ready_without_aging ? nr_to_scan : 0;' in nr_to_scan
    assert 'pace_aging[!type] = true;' in nr_to_scan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('HOSTCC', 'cc'))
    parser.add_argument('--swap-source', type=Path,
                        default=ROOT / 'mm/swap_state.c')
    parser.add_argument('--cleanup-only', action='store_true')
    args = parser.parse_args()
    function = cleanup_function(args.swap_source.read_text())
    model = (Path(__file__).with_name('shadow_model.c')).read_text()
    with tempfile.TemporaryDirectory(prefix='mglru-test-') as tmp:
        source = Path(tmp) / 'test.c'
        binary = Path(tmp) / 'test'
        source.write_text(model.replace('/* PRODUCTION_CLEANUP */', function))
        subprocess.run(shlex.split(args.cc) + ['-std=gnu11', '-O2', '-Wall',
                       '-Wextra', '-Werror', str(source), '-o', str(binary)],
                       check=True)
        subprocess.run([str(binary)], check=True)

    if args.cleanup_only:
        return
    for name in ['mm/hmm.c', 'mm/migrate.c']:
        text = (ROOT / name).read_text()
        assert 'struct mm_walk mm_walk;' not in text, name
        assert 'struct mm_walk mm_walk = {};' in text, name
    text = (ROOT / 'mm/vmscan.c').read_text()
    assert 'memcg = mem_cgroup_disabled() ? NULL :' in text
    assert 'if (!mm->lru_gen.memcg)\n\t\treturn;' in text
    assert 'if (min_ttl && !success && !sc->order' in text
    assert 'static unsigned long lru_gen_min_ttl __read_mostly;' in text
    assert 'if (!sc->may_swap || nr_swap_pages < MIN_LRU_BATCH)' in text
    check_independent_windows(text)
    mm_inline = (ROOT / 'include/linux/mm_inline.h').read_text()
    add_page = function_body(mm_inline, 'static inline bool lru_gen_add_page(')
    assert 'PageSwapCache(page)' in add_page
    mm_types = (ROOT / 'include/linux/mm_types.h').read_text()
    assert 'nodemask_t nodes[2];' in mm_types
    workingset = (ROOT / 'mm/workingset.c').read_text()
    refault = function_body(workingset, 'void lru_gen_refault(')
    assert '((min_seq - token) & (EVICTION_MASK >> LRU_REFS_WIDTH)) >= MAX_NR_GENS' in refault
    assert '__handle_speculative_fault' not in (ROOT / 'mm/memory.c').read_text()
    print('Backport source guards: PASS')


if __name__ == '__main__':
    main()
