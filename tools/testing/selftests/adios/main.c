/* SPDX-License-Identifier: GPL-2.0 */
static struct adios_data ad;
static struct elevator_queue eq={.elevator_data=&ad};
static struct request_queue queue={.elevator=&eq,.nr_hw_queues=1,.nr_requests=64};
static struct blk_mq_hw_ctx hctx={.queue=&queue};
static struct kmem_cache group_cache={.size=sizeof(struct dl_group)};
static mempool_t metadata_pool={.size=sizeof(struct adios_rq_data)};

static void init(void)
{
 memset(&ad,0,sizeof(ad));
 ad.rq_data_pool=&metadata_pool; ad.dl_group_pool=&group_cache;
 ad.aggr_buckets=calloc(ADIOS_OPTYPES,sizeof(struct lm_buckets));
 ad.pcpu_completion=calloc(ADIOS_CPUS,sizeof(struct adios_pcpu_completion));
 ad.global_latency_window=default_global_latency_window;
 ad.lat_model_latency_limit=default_lat_model_latency_limit;
 ad.bq_refill_below_ratio=default_bq_refill_below_ratio;
 for (int i=0;i<2;i++) {
  INIT_LIST_HEAD(&ad.prio_queue[i]); ad.dl_tree[i]=RB_ROOT_CACHED;
  ad.dl_prio[i]=default_dl_prio[i];
 }
 for (int i=0;i<ADIOS_OPTYPES;i++) {
  struct latency_model *m=&ad.latency_model[i];
  m->params=calloc(1,sizeof(*m->params));
  m->pcpu_buckets=calloc(ADIOS_CPUS,sizeof(struct lm_buckets));
  m->pcpu_snapshot=calloc(ADIOS_CPUS,sizeof(struct lm_buckets));
  m->lm_shrink_at_kreqs=default_lm_shrink_at_kreqs;
  m->lm_shrink_at_gbytes=default_lm_shrink_at_gbytes;
  m->lm_shrink_resist=default_lm_shrink_resist;
  ad.batch_limit[i]=default_batch_limit[i];
  ad.latency_target[i]=default_latency_target[i];
  for (int page=0;page<2;page++) INIT_LIST_HEAD(&ad.batch_queue[page][i]);
 }
}
static void destroy(void)
{
 assert(!adios_has_work(&hctx));
 assert(!atomic64_read(&ad.in_flight_rqs.atomic));
 assert(!live_allocations && !locks && !irq_depth);
 for (int i=0;i<2;i++) assert(RB_EMPTY_ROOT(&ad.dl_tree[i].rb_root));
 for (int i=0;i<ADIOS_OPTYPES;i++) {
  free(ad.latency_model[i].params);
  free(ad.latency_model[i].pcpu_buckets); free(ad.latency_model[i].pcpu_snapshot);
 }
 free(ad.aggr_buckets); free(ad.pcpu_completion);
}
static void prepare(struct request *rq,unsigned op)
{
 memset(rq,0,sizeof(*rq)); rq->q=&queue; rq->cmd_flags=op; rq->bytes=4096;
 INIT_LIST_HEAD(&rq->queuelist); adios_prepare_request(rq,NULL); rq->rq_flags|=RQF_ELVPRIV;
}
static void insert(struct request *rq,bool head)
{
 LIST_HEAD(list); list_add_tail(&rq->queuelist,&list);
 adios_insert_requests(&hctx,&list,head); assert(list_empty(&list));
 assert(!locks && !irq_depth);
}
static void complete(struct request *rq)
{
 adios_started_request(rq); clock_ns+=200000; jiffies+=110;
 adios_completed_request(rq); adios_finish_request(rq);
 assert(!rq->elv.priv[0] && !locks && !irq_depth);
}
int main(void)
{
 struct request r[128];
 /* Reject unsupported topology, native queue remains usable. */
 assert(!adios_init_hctx(&hctx,0)); queue.nr_hw_queues=2;
 assert(adios_init_hctx(&hctx,0)==-EINVAL); queue.nr_hw_queues=1;
 init();
 /* Native flush/bypass callbacks may have aliased private storage but no
  * RQF_ELVPRIV: never interpret the flush union as an ADIOS pointer. */
 memset(&r[0],0,sizeof(r[0])); r[0].q=&queue; r[0].elv.priv[0]=(void *)1;
 adios_started_request(&r[0]); adios_completed_request(&r[0]); adios_requeue_request(&r[0]);
 assert(!adios_allow_merge(&queue,&r[0],NULL));
 /* Both bootstrap priority levels populated: emergency must win. */
 prepare(&r[0],REQ_OP_WRITE); insert(&r[0],false);
 prepare(&r[1],REQ_OP_READ|REQ_SYNC); insert(&r[1],true);
 assert(adios_dispatch_request(&hctx)==&r[1]); complete(&r[1]);
 assert(adios_dispatch_request(&hctx)==&r[0]); complete(&r[0]);
 assert(!adios_dispatch_request(&hctx));
 assert(ad.latency_model[ADIOS_READ].params->base>0);
 assert(ad.latency_model[ADIOS_WRITE].params->base>0);
 assert(ad.aggr_buckets[ADIOS_READ].lock==0);
 /* No metadata: allocate-free fallback must dispatch and finish safely. */
 fail_metadata=1; prepare(&r[0],REQ_OP_READ); assert(!get_rq_data(&r[0]));
 insert(&r[0],false); assert(adios_has_work(&hctx));
 assert(adios_dispatch_request(&hctx)==&r[0]); complete(&r[0]);
 assert(atomic64_read(&ad.fallback_count)==1);
 /* Deadline allocation fails: request remains visible and completes. */
 ad.models_stable=true; fail_group=1;
 prepare(&r[0],REQ_OP_WRITE); insert(&r[0],false);
 assert(adios_has_work(&hctx)); assert(adios_dispatch_request(&hctx)==&r[0]);
 complete(&r[0]); assert(atomic64_read(&ad.fallback_count)==2);
 /* Cancellation before insertion never decrements uncounted state. */
 prepare(&r[0],REQ_OP_READ); adios_finish_request(&r[0]);
 assert(!atomic64_read(&ad.in_flight_rqs.atomic));
 /* Native requeue can occur with or without a completion callback. */
 for (int mode=0;mode<2;mode++) {
  prepare(&r[0],REQ_OP_READ|REQ_SYNC); insert(&r[0],true);
  assert(adios_dispatch_request(&hctx)==&r[0]); adios_started_request(&r[0]);
  if (mode) { clock_ns+=100000; adios_completed_request(&r[0]); }
  adios_requeue_request(&r[0]);
  assert(!atomic64_read(&ad.in_flight_rqs.atomic));
  insert(&r[0],true); assert(adios_dispatch_request(&hctx)==&r[0]); complete(&r[0]);
 }
 /* Sync deadline precedes background deadline within the same operation. */
 prepare(&r[0],REQ_OP_WRITE); prepare(&r[1],REQ_OP_WRITE|REQ_SYNC);
 insert(&r[0],false); insert(&r[1],false);
 assert(get_rq_data(&r[1])->deadline<get_rq_data(&r[0])->deadline);
 bool seen[128];
 for (int i=0;i<2;i++) { struct request *rq=adios_dispatch_request(&hctx); assert(rq); complete(rq); }
 /* Mixed operations, batches, quantized groups, failure fallback and model
  * updates. No request may disappear or complete twice. */
 for (int round=0;round<100;round++) {
  memset(seen,0,sizeof(seen));
  for (int i=0;i<128;i++) {
   unsigned op=i%4==0 ? REQ_OP_READ|REQ_SYNC : i%4==1 ? REQ_OP_WRITE :
               i%4==2 ? REQ_OP_DISCARD : REQ_OP_FLUSH;
   if (round%7==0 && i%11==0) fail_metadata=1;
   if (round%5==0 && i%13==0) fail_group=1;
   prepare(&r[i],op); insert(&r[i],i%31==0); clock_ns+=100000;
  }
  for (int i=0;i<128;i++) {
   struct request *rq=adios_dispatch_request(&hctx); assert(rq);
   ptrdiff_t id=rq-r; assert(id>=0 && id<128 && !seen[id]); seen[id]=true;
   complete(rq);
  }
  assert(!adios_dispatch_request(&hctx));
  assert(!adios_has_work(&hctx));
  assert(!atomic64_read(&ad.in_flight_rqs.atomic));
 }
 destroy();
 puts("PASS: actual ADIOS core under UBSan: 12,800 mixed requests, both allocation failures,");
 puts("priority/deadline ordering, model learning, cancel/requeue/finish accounting and empty dispatch");
 return 0;
}
