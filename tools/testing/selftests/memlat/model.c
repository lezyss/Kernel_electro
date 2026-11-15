/* SPDX-License-Identifier: GPL-2.0 */
/* Extracted-production-code model; mocks do not emulate a real PMU or SMP. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef uint64_t u64;
typedef int64_t s64;
typedef uint32_t u32;
typedef int64_t ktime_t;
#define MAX_CPUS 96
#define PERF_TYPE_RAW 4
#define GFP_KERNEL 0
#define min(a,b) ((a)<(b)?(a):(b))
#define min_t(t,a,b) min((t)(a),(t)(b))
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define pr_warn(...) ((void)0)
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((intptr_t)(p))
static u64 div64_u64(u64 a,u64 b) { assert(b); return a/b; }
static u64 div64_u64_rem(u64 a,u64 b,u64 *r) { assert(b); *r=a%b; return a/b; }
static ktime_t ktime_sub(ktime_t a,ktime_t b) { return a-b; }
static s64 ktime_to_us(ktime_t t) { return t; }
struct mutex { bool held; };
struct completion { unsigned done; };
struct __call_single_data { void (*func)(void *); void *info; unsigned flags; };
typedef struct __call_single_data call_single_data_t;
typedef struct { u64 bits[2]; } cpumask_t;
static bool mask_test(int cpu,const cpumask_t *m) { return (m->bits[cpu/64]>>(cpu%64))&1; }
static void cpumask_set_cpu(int cpu,cpumask_t *m) { m->bits[cpu/64]|=1ULL<<(cpu%64); }
static void cpumask_clear(cpumask_t *m) { memset(m,0,sizeof(*m)); }
#define for_each_cpu(cpu,mask) for(cpu=0;cpu<MAX_CPUS;cpu++) if(mask_test(cpu,mask))
struct perf_event { int cpu,index; u64 total; bool enabled; };
struct perf_event_attr { int type,size,pinned,exclude_idle; unsigned config; };
/* DEV_STATS */
struct memlat_hwmon { unsigned num_cores; struct dev_stats *core_stats; };
struct cpu_pmu_stats;
/* DRIVER_TYPES */
static struct cpu_grp_info *owner;
static cpumask_t online, send_fail, idling, isolated;
static call_single_data_t *queued[MAX_CPUS];
static int cpu_context=-1, hotplug_depth, busy, read_fail_cpu=-1, read_fail_index=-1;
static int create_call, create_fail, attr_fail, live_events, submissions, read_calls, eager;
static ktime_t now;
static unsigned pending(void) { unsigned n=0; int c; for(c=0;c<MAX_CPUS;c++) n+=queued[c]!=NULL; return n; }
static void mutex_init(struct mutex *m) { m->held=false; }
static void mutex_lock(struct mutex *m) { assert(!m->held); m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->held && !pending()); m->held=false; }
static void init_completion(struct completion *c) { c->done=0; }
static void reinit_completion(struct completion *c) { assert(owner->lock.held); c->done=0; }
static void complete(struct completion *c) { c->done++; }
static void run_callback(int cpu,call_single_data_t *csd) {
 int saved=cpu_context; assert(hotplug_depth && owner->lock.held); cpu_context=cpu;
 csd->func(csd->info); cpu_context=saved;
}
static void wait_for_completion(struct completion *c) {
 int cpu; assert(hotplug_depth && owner->lock.held);
 /* Reverse completion order, including completion-before-wait. */
 for(cpu=MAX_CPUS-1;cpu>=0;cpu--) if(queued[cpu]) {
  call_single_data_t *csd=queued[cpu]; queued[cpu]=NULL; run_callback(cpu,csd);
 }
 assert(c->done); c->done--;
}
static void cpus_read_lock(void) { assert(!hotplug_depth); hotplug_depth++; }
static void cpus_read_unlock(void) { assert(hotplug_depth==1 && !pending()); hotplug_depth--; }
static bool cpu_online(int cpu) { assert(hotplug_depth); return mask_test(cpu,&online); }
static bool cpu_isolated(int cpu) { assert(hotplug_depth); return mask_test(cpu,&isolated); }
static bool idle_cpu(int cpu) { assert(hotplug_depth); return mask_test(cpu,&idling); }
static bool scm_call_in_progress(void) { return busy!=0; }
static int smp_call_function_single_async(int cpu,call_single_data_t *csd) {
 assert(hotplug_depth && owner->lock.held && !queued[cpu]); submissions++;
 if(mask_test(cpu,&send_fail)) return -ENXIO;
 if(eager) run_callback(cpu,csd); else queued[cpu]=csd;
 return 0;
}
static ktime_t ktime_get(void) { return now; }
static int perf_event_read_local(struct perf_event *ev,u64 *count,u64 *enabled,u64 *running) {
 assert(owner->lock.held && hotplug_depth && cpu_context==ev->cpu);
 assert(!enabled && !running && ev->enabled); read_calls++;
 if(ev->cpu==read_fail_cpu && ev->index==read_fail_index) return -EBUSY;
 *count=ev->total; return 0;
}
static void *kzalloc(size_t n,int flags) { if(attr_fail) return NULL; return calloc(1,n); }
static void kfree(void *p) { free(p); }
static struct perf_event *perf_event_create_kernel_counter(struct perf_event_attr *a,int cpu,void *x,void *y,void *z) {
 struct perf_event *ev; assert(owner->lock.held); assert(a->pinned && a->exclude_idle);
 if(++create_call==create_fail) return (void *)(intptr_t)-ENOMEM;
 ev=calloc(1,sizeof(*ev)); assert(ev); ev->cpu=cpu; ev->index=a->config-1; live_events++; return ev;
}
static void perf_event_enable(struct perf_event *ev) { ev->enabled=true; }
static void perf_event_release_kernel(struct perf_event *ev) { assert(owner->lock.held && !pending()); live_events--; free(ev); }
/* FUNCTIONS */
static void setup(struct cpu_grp_info *g,bool stall) {
 int cpu,ev; memset(g,0,sizeof(*g)); owner=g; mutex_init(&g->lock);
 /* Sparse ids, including ids beyond both 32- and 64-bit mask boundaries. */
 cpumask_clear(&g->cpus); cpumask_set_cpu(1,&g->cpus); cpumask_set_cpu(34,&g->cpus); cpumask_set_cpu(69,&g->cpus);
 online=g->cpus; cpumask_clear(&send_fail); cpumask_clear(&idling); cpumask_clear(&isolated); g->hw.num_cores=3;
 g->hw.core_stats=calloc(3,sizeof(*g->hw.core_stats)); g->cpustats=calloc(MAX_CPUS,sizeof(*g->cpustats));
 for(ev=0;ev<NUM_EVENTS;ev++) g->event_ids[ev]=(ev==STALL_CYC_IDX&&!stall)?0:ev+1;
 init_cpu_stats(g);
 for_each_cpu(cpu,&g->cpus) assert(to_cpustats(g,cpu)->devstats->id==cpu);
 busy=attr_fail=create_call=create_fail=submissions=read_calls=0; read_fail_cpu=read_fail_index=-1; now=1000;
}
static void teardown(struct cpu_grp_info *g) {
 stop_hwmon(&g->hw); assert(!g->running && live_events==0 && !pending() && !hotplug_depth);
 free(g->cpustats); free(g->hw.core_stats);
}
static void increment(struct cpu_grp_info *g,u64 cycles) {
 int cpu,ev; for_each_cpu(cpu,&g->cpus) for(ev=0;ev<NUM_EVENTS;ev++) {
  if(mask_test(cpu,&idling) || mask_test(cpu,&isolated)) continue;
  struct perf_event *e=to_cpustats(g,cpu)->events[ev].pevent;
  if(e) e->total+=ev==CYC_IDX?cycles:ev==STALL_CYC_IDX?cycles/2:cycles/4;
 }
}
static void sample(struct cpu_grp_info *g) { get_cnt(&g->hw); assert(!pending() && !hotplug_depth); }
static void lifecycle_tests(void) {
 struct cpu_grp_info g; int fail;
 for(fail=1;fail<=12;fail++) {
  setup(&g,true); create_fail=fail; assert(start_hwmon(&g.hw)==-ENOMEM); assert(!g.running && !live_events);
  create_fail=0; assert(!start_hwmon(&g.hw)); assert(live_events==12); busy=1; teardown(&g);
 }
 setup(&g,true); attr_fail=1; assert(start_hwmon(&g.hw)==-ENOMEM && !live_events); attr_fail=0;
 assert(!start_hwmon(&g.hw)); assert(!start_hwmon(&g.hw) && live_events==12); teardown(&g);
}
static void sample_tests(void) {
 struct cpu_grp_info g; struct cpu_pmu_stats *s; int fail;
 for(eager=0;eager<=1;eager++) for(fail=0;fail<NUM_EVENTS;fail++) {
  struct dev_stats last; u64 prev[NUM_EVENTS]; ktime_t stamp; int i;
  setup(&g,true); assert(!start_hwmon(&g.hw)); s=to_cpustats(&g,34);
  sample(&g); assert(s->have_prev && !s->devstats->freq && submissions==3);
  now+=100; increment(&g,10000); sample(&g);
  assert(s->devstats->freq==100 && s->devstats->stall_pct==50);
  last=*s->devstats; stamp=s->prev_ts; for(i=0;i<NUM_EVENTS;i++) prev[i]=s->events[i].prev_count;
  now+=100; increment(&g,10000); read_fail_cpu=34; read_fail_index=fail; sample(&g);
  assert(!memcmp(&last,s->devstats,sizeof(last)) && stamp==s->prev_ts);
  for(i=0;i<NUM_EVENTS;i++) assert(prev[i]==s->events[i].prev_count);
  read_fail_cpu=read_fail_index=-1; now+=100; increment(&g,10000); sample(&g);
  assert(s->devstats->freq==100 && s->devstats->stall_pct==50);
  busy=1; now+=100; increment(&g,10000); stamp=s->prev_ts; last=*s->devstats; sample(&g);
  assert(stamp==s->prev_ts && !memcmp(&last,s->devstats,sizeof(last)));
  busy=0; now+=100; increment(&g,10000); sample(&g); assert(s->devstats->freq==100);
  cpumask_set_cpu(34,&send_fail); stamp=s->prev_ts; now+=100; increment(&g,10000); sample(&g); assert(stamp==s->prev_ts);
  cpumask_clear(&send_fail); now+=100; increment(&g,10000); sample(&g); assert(s->devstats->freq==100);
  online.bits[0]&=~(1ULL<<34); sample(&g); assert(!s->have_prev && !s->devstats->freq);
  online=g.cpus; now+=100; increment(&g,10000); sample(&g); assert(s->have_prev && !s->devstats->freq);
  now+=100; increment(&g,10000); sample(&g); assert(s->devstats->freq==100);
  sample(&g); assert(s->devstats->freq==100); /* Same timestamp is ignored. */
  now+=100; sample(&g); assert(!s->devstats->freq && !s->devstats->stall_pct); /* Zero cycles. */
  busy=1; teardown(&g); /* Teardown never skips when secure firmware is busy. */
 }
 setup(&g,false); assert(!start_hwmon(&g.hw)); sample(&g); now+=100; increment(&g,10000); sample(&g);
 assert(to_cpustats(&g,1)->devstats->stall_pct==100); teardown(&g);
}
static void idle_isolation_tests(void) {
 struct cpu_grp_info g; struct cpu_pmu_stats *s; int sent; ktime_t stamp;
 setup(&g,true); assert(!start_hwmon(&g.hw)); sample(&g);
 now+=100; increment(&g,10000); sample(&g); s=to_cpustats(&g,34);
 assert(s->devstats->freq==100); stamp=s->prev_ts;
 cpumask_set_cpu(34,&idling); now+=100; increment(&g,10000); sent=submissions; sample(&g);
 assert(submissions-sent==2 && s->have_prev && !s->devstats->freq && s->prev_ts==stamp);
 cpumask_clear(&idling); now+=100; increment(&g,10000); sample(&g);
 assert(s->devstats->freq==50); /* Include actual idle interval, without waking it. */
 s=to_cpustats(&g,69); cpumask_set_cpu(69,&isolated); sent=submissions; sample(&g);
 assert(submissions-sent==2 && !s->have_prev && !s->devstats->freq);
 cpumask_clear(&isolated); now+=100; increment(&g,10000); sample(&g);
 assert(s->have_prev && !s->devstats->freq);
 now+=100; increment(&g,10000); sample(&g); assert(s->devstats->freq==100);
 teardown(&g);
 puts("PASS: observed idle/isolated CPUs receive no sampling IPI; idle votes clear without losing elapsed baseline, isolated epochs reset");
}
int main(void) {
 lifecycle_tests(); sample_tests(); idle_isolation_tests();
 assert(memlat_stall_pct(0,0)==0 && memlat_stall_pct(UINT64_MAX,UINT64_MAX)==100);
 puts("PASS: extracted async samples, completion orders, sparse masks, read/send faults, SCM skips, epochs, zero cycles, allocation unwind and busy teardown");
 return 0;
}
