#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Compile actual ADIOS prototype core with host mocks; not a kernel safety test."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    source = (ROOT / 'block/adios.c').read_text()
    for token in ('scoped_guard', 'guard(', 'timer_reduce(', 'timer_shutdown_sync(',
                  'blk_mq_sched_try_merge(', 'blk_mq_sched_try_insert_merge(',
                  'shallow_depth', 'rq->io_start_time_ns', 'rq->start_time_ns'):
        assert token not in source, token
    assert '.uses_mq = true' in source and '.ops.mq = {' in source
    assert '.allow_merge' in source and '.requeue_request' in source
    assert 'q->nr_hw_queues != 1' in source
    assert 'static ssize_t adios_' in source and '_store(' not in source
    assert 'default n' in (ROOT / 'block/Kconfig.iosched').read_text().split('config MQ_IOSCHED_ADIOS', 1)[1].split('\nconfig ', 1)[0]
    assert 'CONFIG_MQ_IOSCHED_DEFAULT_ADIOS' in (ROOT / 'block/elevator.c').read_text()
    assert 'CONFIG_MQ_IOSCHED_DEFAULT_ADIOS=y' in (ROOT / 'arch/arm64/configs/vendor/xiaomi/miatoll_defconfig').read_text()
    # Exclude only kernel includes and kernel init/sysfs/registration. Exercise
    # unmodified request allocation, queues, trees, models and lifecycle helpers.
    core = source[:source.index('static int adios_init_sched(')]
    core = '\n'.join(line for line in core.splitlines() if not line.startswith('#include'))
    with tempfile.TemporaryDirectory(prefix='adios-host-') as tmp:
        tmp = Path(tmp)
        cfile = tmp / 'adios.c'
        cfile.write_text('#include "host.h"\n' + core + '\n' + (HERE / 'main.c').read_text())
        command = [args.cc, '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                   '-Wno-unused-function', '-Wno-unused-parameter', '-Wno-unused-variable',
                   '-Wno-sign-compare', '-fsanitize=undefined', '-fno-sanitize-recover=all',
                   '-I' + str(HERE), '-I' + str(ROOT / 'tools/include'),
                   str(cfile), str(ROOT / 'tools/lib/rbtree.c'), '-o', str(tmp / 'test')]
        subprocess.run(command, check=True)
        subprocess.run([str(tmp / 'test')], check=True)
    print('PASS: native callback wiring and miatoll default selection')
    print('Host mocks do NOT validate real IRQ/RCU concurrency, UFS, crypto, recovery or PM.')


if __name__ == '__main__':
    main()
