#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Read-only source checks for the ADIOS review; NOT a build or safety test."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PIN = '8117e935197fd45259ef77407b1c274d3386cd53'
PATCH_SHA256 = 'ecfa33c53e09ea9ef7cd4d2df3dc7f5a49e467f1b8da74e945367f01ed95c315'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', required=True, type=Path,
                        help='unmodified pinned linux6.12.44 ADIOS 3.3.0 patch')
    args = parser.parse_args()
    raw = args.patch.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PATCH_SHA256, 'unexpected patch; re-review required'
    patch = raw.decode()
    section = patch.split('diff --git a/block/adios.c b/block/adios.c\n', 1)[1].split('diff --git ', 1)[0]
    adios = '\n'.join(line[1:] for line in section.splitlines()
                      if line.startswith('+') and not line.startswith('+++')) + '\n'
    checks = []

    def read(path):
        return (ROOT / path).read_text()

    def check(name, condition):
        assert condition, name + ': source changed; re-review required'
        checks.append(name)

    elevator = read('include/linux/elevator.h')
    sched = read('block/blk-mq-sched.h')
    mq = read('block/blk-mq.c')
    check('old elevator ops union and explicit uses_mq',
          'struct elevator_mq_ops mq;' in elevator and 'bool uses_mq;' in elevator
          and '.ops = {' in adios and '.uses_mq' not in adios)
    check('bio merge callback mismatch',
          '(*bio_merge)(struct blk_mq_hw_ctx *, struct bio *)' in elevator
          and 'adios_bio_merge(struct request_queue *q, struct bio *bio,' in adios)
    check('prepare and completion callback mismatch',
          '(*prepare_request)(struct request *, struct bio *bio)' in elevator
          and '(*completed_request)(struct request *)' in elevator
          and 'adios_completed_request(struct request *rq, u64 now)' in adios)
    check('old boolean at_head vs new insertion flags',
          '(*insert_requests)(struct blk_mq_hw_ctx *, struct list_head *, bool)' in elevator
          and 'BLK_MQ_INSERT_AT_HEAD' in adios)
    check('no depth_updated callback in this tree',
          'depth_updated' not in elevator and '.depth_updated' in adios)
    check('merge ownership differs',
          'struct request **merged_request' in sched
          and 'struct request *rq);' in sched
          and 'blk_mq_sched_try_merge(q, bio, nr_segs, &free)' in adios
          and 'blk_mq_sched_try_insert_merge(q, rq, free)' in adios
          and '__blk_put_request(q, free);' in read('block/blk-merge.c'))
    check('per-word shallow allocation, not modern queue-wide units',
          'min(sb->map[index].depth, shallow_depth)' in read('lib/sbitmap.c')
          and 'data->shallow_depth = ad->async_depth;' in adios
          and 'ad->async_depth = q->nr_requests;' in adios)
    check('no minimum-shallow-depth helper',
          'sbitmap_queue_min_shallow_depth' not in read('include/linux/sbitmap.h')
          and 'sbitmap_queue_min_shallow_depth' in adios)
    check('mq does not initialize io_start_time_ns at hardware start',
          'rq->io_start_time_ns = 0;' in mq
          and 'set_io_start_time_ns(' not in mq
          and '!rq->io_start_time_ns' in adios)
    check('timer setup exists but reduce/shutdown APIs do not',
          'timer_setup(' in read('include/linux/timer.h')
          and 'timer_reduce(' not in read('include/linux/timer.h')
          and 'timer_shutdown_sync(' not in read('include/linux/timer.h')
          and 'timer_shutdown_sync(' in adios)
    check('modern local elevator/math headers unavailable',
          not (ROOT / 'block/elevator.h').exists()
          and not (ROOT / 'include/linux/math.h').exists()
          and '#include "elevator.h"' in adios and '#include <linux/math.h>' in adios)
    check('queue flag and stats teardown APIs unavailable',
          'QUEUE_FLAG_SQ_SCHED' not in read('include/linux/blkdev.h')
          and 'BLK_FEAT_ROTATIONAL' not in read('include/linux/blkdev.h')
          and 'blk_stat_disable_accounting' not in read('block/blk-stat.h')
          and 'blk_stat_disable_accounting' in adios)
    check('request metadata allocation is unchecked',
          'rd = mempool_alloc(ad->rq_data_pool, GFP_ATOMIC);\n\tmemset(rd, 0, sizeof(*rd));' in adios)
    check('deadline node allocation failure has no queue fallback',
          'dlg = kmem_cache_zalloc(ad->dl_group_pool, GFP_ATOMIC);\n\t\tif (!dlg)\n\t\t\treturn;' in adios
          and 'add_to_dl_tree(ad, dl_idx, rq);\n\n\tif (rq_mergeable(rq))' in adios)
    check('shared aggregation scratch across per-model update locks',
          'struct lm_buckets *aggr_buckets;' in adios
          and 'struct lm_buckets *aggr = ad->aggr_buckets;' in adios
          and 'spin_lock_irqsave(&model->update_lock, flags);' in adios)
    check('GNU11 already configured; no global dialect migration needed',
          '-std=gnu11' in read('Makefile'))
    print(json.dumps({'upstream_commit': PIN, 'patch_sha256': PATCH_SHA256,
                      'source_contracts_confirmed': checks,
                      'qualification': 'static source inspection only; no scheduler imported or executed'}, indent=2))


if __name__ == '__main__':
    main()
