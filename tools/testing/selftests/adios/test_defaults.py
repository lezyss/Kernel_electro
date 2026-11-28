#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Host-mock test of the actual elevator_init default/fallback policy."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
PRE = r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#define CONFIG_DEFAULT_IOSCHED "cfq"
#define IS_ENABLED(x) enabled
#define unlikely(x) (x)
#define lockdep_assert_held(x) ((void)(x))
#define INIT_LIST_HEAD(x) ((void)(x))
#define blk_queue_nonrot(q) ((q)->nonrot)
#define printk(...) ((void)0)
#define pr_warn(...) ((void)0)
#define KERN_ERR ""
struct request_queue;
struct elevator_type { const char *elevator_name; bool uses_mq; struct { struct { int (*elevator_init_fn)(struct request_queue *,struct elevator_type *); } sq; } ops; };
struct elevator_queue { struct elevator_type *type; bool registered; };
struct request_queue { struct elevator_queue *elevator; bool mq_ops, nonrot; unsigned nr_hw_queues; int sysfs_lock,queue_head,end_sector; void *last_merge,*boundary_rq; };
static bool enabled=true,missing_adios,fail_adios,fail_deadline;
static char chosen_elevator[8];
static struct elevator_type adios={.elevator_name="adios",.uses_mq=true},deadline={.elevator_name="mq-deadline",.uses_mq=true},cfq={.elevator_name="cfq"};
static struct elevator_queue eq;
static int frozen;
static int refs;
static struct elevator_type *selected;
static struct elevator_type *elevator_get(struct request_queue *q,const char *name,bool load) {
 (void)q; (void)load;
 struct elevator_type *e=NULL;
 if (!strcmp(name,"adios")) e=missing_adios?NULL:&adios;
 else if (!strcmp(name,"mq-deadline")) e=&deadline;
 else e=&cfq;
 if (e) ++refs;
 return e;
}
static void elevator_put(struct elevator_type *e) { (void)e; assert(refs>0); --refs; }
static int blk_mq_init_sched(struct request_queue *q,struct elevator_type *e) {
 if ((e==&adios && fail_adios)||(e==&deadline && fail_deadline)) return -ENOMEM;
 eq.type=e; eq.registered=false; q->elevator=&eq; selected=e; return 0;
}
static int legacy_init(struct request_queue *q,struct elevator_type *e) { eq.type=e; eq.registered=false; q->elevator=&eq; selected=e; return 0; }
static void blk_mq_freeze_queue(struct request_queue *q) { (void)q; assert(!frozen); frozen=1; }
static void blk_mq_unfreeze_queue(struct request_queue *q) { (void)q; assert(frozen); frozen=0; }
static void ioc_clear_queue(struct request_queue *q) { (void)q; assert(frozen); }
static void elevator_exit(struct request_queue *q,struct elevator_queue *e) { assert(frozen && !e->registered); elevator_put(e->type); q->elevator=NULL; }

'''
POST = r'''
static void check(bool mq,bool nonrot,unsigned hctx,const char *name,struct elevator_type *expected,int error) {
 struct request_queue q={.mq_ops=mq,.nonrot=nonrot,.nr_hw_queues=hctx};
 selected=NULL; refs=0;
 assert(elevator_init(&q,(char *)name)==error);
 assert(selected==expected);
 assert(refs==(expected?1:0));
}
int main(void) {
 cfq.ops.sq.elevator_init_fn=legacy_init;
 check(true,true,1,NULL,&adios,0);
 check(true,false,1,NULL,&deadline,0);
 check(true,true,4,NULL,NULL,0);
 check(false,true,1,NULL,&cfq,0);
 enabled=false; check(true,true,1,NULL,&deadline,0); enabled=true;
 missing_adios=true; check(true,true,1,NULL,&deadline,0); missing_adios=false;
 fail_adios=true; check(true,true,1,NULL,&deadline,0);
 check(true,true,1,"adios",NULL,-ENOMEM);
 check(true,true,1,"mq-deadline",&deadline,0);
 fail_deadline=true; check(true,true,1,NULL,NULL,-ENOMEM);
 fail_adios=fail_deadline=false;
 struct request_queue q={.mq_ops=true,.nr_hw_queues=1,.nonrot=false};
 refs=0; selected=NULL; assert(!elevator_init(&q,NULL)); assert(selected==&deadline);
 assert(!elevator_apply_mq_default(&q)); assert(selected==&deadline);
 q.nonrot=true; assert(!elevator_apply_mq_default(&q));
 assert(selected==&adios && refs==1 && !frozen);
 assert(!elevator_apply_mq_default(&q)); assert(refs==1);
 q.elevator->type=&deadline; q.elevator->registered=true; selected=&deadline;
 assert(!elevator_apply_mq_default(&q)); assert(selected==&deadline && !frozen);
 q.elevator->registered=false; fail_adios=true;
 assert(!elevator_apply_mq_default(&q)); assert(selected==&deadline && refs==1 && !frozen);
 puts("PASS: registration-time nonrot detection, drained re-selection and fallback");
 puts("PASS: extracted elevator_init: ADIOS/default-off/legacy/topology, missing/init-failed fallback, explicit selection errors and reference balance");
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    text = (ROOT / 'block/elevator.c').read_text()
    start = text.index('int elevator_init(')
    end = text.index('\nEXPORT_SYMBOL(elevator_init);', start)
    with tempfile.TemporaryDirectory(prefix='adios-default-') as tmp:
        tmp = Path(tmp)
        source = tmp / 'test.c'
        hstart = text.index('int elevator_apply_mq_default(')
        hend = text.index('\n}\n', hstart) + 3
        source.write_text(PRE + text[start:end] + text[hstart:hend] + POST)
        subprocess.run([args.cc, '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=undefined', str(source), '-o', str(tmp / 'test')], check=True)
        subprocess.run([str(tmp / 'test')], check=True)


if __name__ == '__main__':
    main()
