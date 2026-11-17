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
    assert '__handle_speculative_fault' not in (ROOT / 'mm/memory.c').read_text()
    print('Backport source guards: PASS')


if __name__ == '__main__':
    main()
