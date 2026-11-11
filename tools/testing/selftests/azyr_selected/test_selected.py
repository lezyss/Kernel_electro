#!/usr/bin/env python3
"""Bounded actual-function host checks for the approved Azyr selection.
No target build/device/concurrency/performance proof. Requires GCC and UBSan.
"""
import ctypes
import json
import os
from pathlib import Path
import random
import re
import resource
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
PATCH = ROOT / 'Documentation/dev-tools/azyr-sm6250-selected.diff'
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def body(path, name):
    text = path.read_text()
    match = re.search(r'^[a-zA-Z_][^\n]*(?:\n)?\b' + name + r'\([^;{}]*?\)\n\{', text, re.M)
    assert match, name
    end, depth = match.end(), 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end] + '\n'


PREFIX = '#include <assert.h>\n#include <stdint.h>\n#include <stdbool.h>\n#include <stddef.h>\n#include <stdio.h>\ntypedef uint64_t u64; typedef uint32_t u32;\n'
RESULTS = {}


def run(tmp, name, text, mutants=()):
    for label, code in [('live', text)] + list(mutants):
        f = tmp / (name + '_' + label + '.c')
        f.write_text(PREFIX + code)
        exe = f.with_suffix('')
        subprocess.run(['gcc', '-std=gnu11', '-O2', '-Wall', '-Werror',
                        '-Wno-unused-function', '-Wno-unused-variable',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all',
                        str(f), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], capture_output=True, text=True)
        assert (result.returncode == 0) == (label == 'live'), (name, label, result.stderr)
        if label == 'live':
            RESULTS[name] = result.stdout.strip()
        else:
            assert result.returncode != 0
            RESULTS[name + '_negative_' + label] = 'compiled and rejected at runtime'


with tempfile.TemporaryDirectory(prefix='azyr-selected-test-') as td:
    tmp = Path(td)
    before = tmp / 'before'
    # Reconstruct exact preimages without touching native sources.
    files = re.findall(r'^\+\+\+ b/(.*)$', PATCH.read_text(), re.M)
    for p in files:
        dest = before / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / p).read_bytes())
    subprocess.run(['git', 'apply', '--reverse', str(PATCH)], cwd=before, check=True)

    balance = body(ROOT / 'kernel/sched/fair.c', 'should_we_balance')
    code = r'''
struct sched_group {int unused;};struct sched_domain {struct sched_group *groups;};
struct llist_head {void *first;};struct rq {unsigned nr_running;struct llist_head wake_list;};
struct lb_env {struct sched_domain *sd;int dst_cpu;unsigned *cpus;int idle;struct rq *dst_rq;};
static unsigned mask=1;static int allowed=1,idle_ok=1,isolated=0;
#define CPU_NEWLY_IDLE 2
#define READ_ONCE(x) (x)
#define cpumask_test_cpu(cpu,m) (allowed)
#define group_balance_mask(sg) (&mask)
#define for_each_cpu_and(cpu,a,b) for((cpu)=0;(cpu)<1;(cpu)++)
static bool llist_empty(struct llist_head *h){return h->first==NULL;}
static bool idle_cpu(int cpu){return idle_ok;}
static bool cpu_isolated(int cpu){return isolated;}
static int group_balance_cpu_not_isolated(struct sched_group *g){return 0;}
''' + balance + r'''
int main(void){int n,w,a,kind,cases=0;struct sched_group sg={0};struct sched_domain sd={&sg};struct rq rq={0};struct lb_env e={&sd,0,&mask,0,&rq};
for(kind=0;kind<3;kind++)for(a=0;a<2;a++)for(n=0;n<3;n++)for(w=0;w<2;w++){e.idle=kind;allowed=a;rq.nr_running=n;rq.wake_list.first=w?&rq:NULL;assert(should_we_balance(&e)==(a&&(kind!=CPU_NEWLY_IDLE||(!n&&!w))));cases++;}
printf("%d newly-idle/runnable/pending/hotplug/other-idle cases\n",cases);return 0;}
'''
    run(tmp, 'balance46', code, [('no_wakelist', code.replace('!llist_empty(&env->dst_rq->wake_list)', '0')), ('no_nr', code.replace('READ_ONCE(env->dst_rq->nr_running)', '0'))])

    # Actual old/new delta functions and inverse-weight helper, two modeled load scales.
    old = body(before / 'kernel/sched/fair.c', '__calc_delta').replace('__calc_delta(', 'old_delta(', 1)
    new = body(ROOT / 'kernel/sched/fair.c', '__calc_delta').replace('__calc_delta(', 'new_delta(', 1)
    inv = body(ROOT / 'kernel/sched/fair.c', '__update_inv_weight')
    code = r'''
#include <limits.h>
struct load_weight {unsigned long weight;u32 inv_weight;};static int scale;
#define BITS_PER_LONG 64
#define WMULT_CONST (~0U)
#define WMULT_SHIFT 32
#define likely(x) (x)
#define unlikely(x) (x)
#define scale_load_down(x) ((x)>>scale)
static int fls(u32 x){return x?32-__builtin_clz(x):0;}
static u64 mul_u64_u32_shr(u64 a,u32 b,unsigned shift){assert(shift<64);return (u64)(((__uint128_t)a*b)>>shift);}
''' + inv + old + new + r'''
static u64 rng=0x123abc456defULL;static u64 rand64(void){rng^=rng<<13;rng^=rng>>7;rng^=rng<<17;return rng;}
int main(void){int mode,i,cache;unsigned long edges[]={0,1,2,1023,1024,1025,0xffffffffUL,0x100000000UL,ULONG_MAX>>10};unsigned cases=0;
for(mode=0;mode<2;mode++){scale=mode?10:0;for(i=0;i<60000;i++)for(cache=0;cache<2;cache++){unsigned long total=i<9?edges[i]:rand64()>>10;unsigned long weight=total?rand64()%(total+1):0;u64 delta=i<9?UINT64_MAX:rand64();struct load_weight a={total<<scale,0},b=a;if(cache){__update_inv_weight(&a);b=a;}assert(old_delta(delta,weight<<scale,&a)==new_delta(delta,weight<<scale,&b));assert(a.inv_weight==b.inv_weight);cases++;}}
printf("%u old/new delta and inverse equivalence cases (modeled scale0/10)\n",cases);return 0;}
'''
    run(tmp, 'delta48', code, [('wrong_shift', code.replace('fs = fls(fact_hi);', 'fs = fls(fact_hi) + 1;'))])

    topology = body(ROOT / 'drivers/base/arch_topology.c', 'detect_share_cap_flag')
    code = r'''
enum share_cap_type {no_share_cap,share_cap_thread,share_cap_core,share_cap_die};static enum share_cap_type share_cap;
struct cpufreq_policy {unsigned *related_cpus;};static unsigned related;static struct cpufreq_policy policy={&related};static int mode,null_at,gets,put_count;
#define for_each_possible_cpu(cpu) for((cpu)=0;(cpu)<8;(cpu)++)
#define cpu_cpu_mask(cpu) 1
#define topology_core_cpumask(cpu) 2
#define topology_sibling_cpumask(cpu) 3
#define cpumask_equal(mask,rel) ((mask)==(mode==4?(cpu%4):mode))
static struct cpufreq_policy *cpufreq_cpu_get(int cpu){if(cpu==null_at)return NULL;gets++;return &policy;}
static void cpufreq_cpu_put(struct cpufreq_policy *p){put_count++;}
''' + topology + r'''
int main(void){int m,n,repeat,cases=0;for(m=0;m<5;m++)for(n=-1;n<8;n++)for(repeat=0;repeat<10;repeat++){mode=m;null_at=n;gets=put_count=0;detect_share_cap_flag();assert(gets==put_count);assert(gets==(n<0?8:n));cases++;}printf("%d topology policy reference cases\n",cases);return 0;}
'''
    run(tmp, 'topology78', code, [('no_put', code.replace('cpufreq_cpu_put(policy);', '(void)policy;'))])

    offline = body(ROOT / 'block/cfq-iosched.c', 'cfq_pd_offline')
    code = r'''
#define IOPRIO_BE_NR 8
struct blkg_policy_data {int unused;};struct cfq_queue {int puts;};struct cfq_group {struct cfq_queue *async_cfqq[2][8],*async_idle_cfqq;};static struct cfq_group group;static int transfers;
static struct cfq_group *pd_to_cfqg(struct blkg_policy_data *p){return &group;}
static void cfq_put_queue(struct cfq_queue *q){q->puts++;}
static void cfqg_stats_xfer_dead(struct cfq_group *g){transfers++;}
''' + offline + r'''
int main(void){int n,i;struct cfq_queue q[17];struct blkg_policy_data pd={0};for(n=0;n<=17;n++){transfers=0;for(i=0;i<17;i++){q[i].puts=0;if(i<16)group.async_cfqq[i/8][i%8]=i<n?&q[i]:NULL;else group.async_idle_cfqq=i<n?&q[i]:NULL;}cfq_pd_offline(&pd);assert(transfers==1);for(i=0;i<17;i++){assert(q[i].puts==(i<n));if(i<16)assert(!group.async_cfqq[i/8][i%8]);else assert(!group.async_idle_cfqq);}}puts("18 CFQ slot-occupancy cases, references and statistics transfer preserved");return 0;}
'''
    run(tmp, 'offline94', code, [('stale_slot', code.replace('cfqg->async_idle_cfqq = NULL;', '/* stale */'))])

    producer = ''.join(body(ROOT / 'include/linux/blkdev.h', x) for x in ['set_start_time_ns', 'set_io_start_time_ns', 'rq_start_time_ns', 'rq_io_start_time_ns'])
    cfq = body(ROOT / 'block/cfq-iosched.c', 'cfqg_stats_update_completion')
    bfq = body(ROOT / 'block/bfq-cgroup.c', 'bfqg_stats_update_completion')
    code = r'''
struct request {u64 start_time_ns,io_start_time_ns;};
struct cfqg_stats {u64 service_time,wait_time;};struct cfq_group {struct cfqg_stats stats;};
struct bfqg_stats {u64 service_time,wait_time;};struct bfq_group {struct bfqg_stats stats;};
static u64 now;static long offset;
static u64 ktime_get_ns(void){return now;}
static u64 sched_clock(void){return now+offset;}
#define time_after64(a,b) ((int64_t)((b)-(a))<0)
#define blkg_rwstat_add(p,op,val) (*(p)+=(val))
''' + producer + cfq + bfq + r'''
int main(void){long o;int a,b,c,cases=0;for(o=-500;o<=500;o+=500)for(a=0;a<2;a++)for(b=0;b<2;b++)for(c=0;c<3;c++){struct request r={0};struct cfq_group cg={0};struct bfq_group bg={0};offset=o;now=1000;set_start_time_ns(&r);now=a?1100:1000;set_io_start_time_ns(&r);now=b?1250:1000;if(c==1)now=r.io_start_time_ns;if(c==2)now=999;cfqg_stats_update_completion(&cg,rq_start_time_ns(&r),rq_io_start_time_ns(&r),0);bfqg_stats_update_completion(&bg,rq_start_time_ns(&r),rq_io_start_time_ns(&r),0);assert(cg.stats.service_time==bg.stats.service_time);assert(cg.stats.wait_time==bg.stats.wait_time);assert(cg.stats.service_time==(now>r.io_start_time_ns?now-r.io_start_time_ns:0));assert(cg.stats.wait_time==r.io_start_time_ns-r.start_time_ns);cases++;}printf("%d shared-producer CFQ/BFQ clock-domain/boundary cases\n",cases);return 0;}
'''
    run(tmp, 'clocks92', code, [('mixed_bfq_clock', code.replace(bfq, bfq.replace('ktime_get_ns()', 'sched_clock()')))])

    # GIC scan with one enabled+pending IRQ, debug printing independently gated.
    scan = body(ROOT / 'drivers/irqchip/irq-gic-v3.c', 'gic_show_resume_irq')
    code = r'''
#define __iomem
#define GICD_ICENABLER 0
#define GICD_ISPENDR 4
#define BIT(x) (1U<<(x))
struct irqaction {const char *name;};struct irq_desc {const char *name;struct irqaction *action;};struct gic_chip_data {unsigned irq_nr;};
static struct irq_desc desc={"irq",NULL};static int baseword,msm_show_resume_irq_mask,logs,prints;
static void *gic_data_dist_base(struct gic_chip_data *g){return &baseword;}
static u32 readl_relaxed(void *p){return 1;}
static int irq_find_mapping(void *domain,unsigned hwirq){return hwirq+1;}
static struct irq_desc *irq_to_desc(int irq){return &desc;}
static void log_irq_wakeup_reason(int irq){logs++;}
#define pr_warn(fmt,func,irq,name) ((void)(name),++prints)
static struct {void *dist_base;} gic_data={&baseword};
static unsigned find_next_bit(unsigned long *p,unsigned size,unsigned start){u32 bits=*(u32 *)p;unsigned i;for(i=start;i<size;i++)if(bits&(1U<<i))return i;return size;}
static unsigned find_first_bit(unsigned long *p,unsigned size){return find_next_bit(p,size,0);}
'''
    # Native field adapters stay explicit in fixture.
    scan_fields = re.findall(r'gic->([a-zA-Z_]+)', scan)
    if 'domain' in scan_fields:
        code = code.replace('unsigned irq_nr;', 'unsigned irq_nr;void *domain;')
    if 'dist_base' in scan_fields:
        code = code.replace('unsigned irq_nr;', 'unsigned irq_nr;void *dist_base;')
    code += scan + r'''
int main(void){int m;struct gic_chip_data g={.irq_nr=1};for(m=0;m<2;m++){logs=prints=0;msm_show_resume_irq_mask=m;gic_show_resume_irq(&g);assert(logs==1);assert(prints==m);}puts("2 GIC recording cases, debug console on/off");return 0;}
'''
    run(tmp, 'wakeup98', code, [('debug_gate', code.replace('for (i = 0;', 'if (!msm_show_resume_irq_mask) return;\n\tfor (i = 0;', 1))])

    verity = (ROOT / 'drivers/md/dm-verity-target.c').read_text()
    assert re.search(r'alloc_workqueue\("kverityd",\s*WQ_CPU_INTENSIVE \| WQ_MEM_RECLAIM \| WQ_HIGHPRI, 0\)', verity)
    assert 'static inline void sugov_policy_free' in (ROOT / 'kernel/sched/cpufreq_schedutil.c').read_text()
    assert 'clock_debug_print_enabled(false)' in (ROOT / 'drivers/cpuidle/lpm-levels.c').read_text()
    assert 'gmu_core_dev_read_ao_counter' not in (ROOT / 'drivers/gpu/msm/adreno.c').read_text()
    assert 'gmu_core_dev_read_ao_counter' not in (ROOT / 'drivers/gpu/msm/kgsl_gmu_core.c').read_text()
    assert 'pr_info("Adding device' not in (ROOT / 'drivers/iommu/iommu.c').read_text()
    assert 'SCHED_FEAT_TTWU_QUEUE' not in balance
    assert 'log_irq_wakeup_reason(irq_number);' in (ROOT / 'drivers/base/power/wakeup.c').read_text()
    RESULTS['structural'] = 'verity flags/admission; inline; suspend parent flag; IRQ debug wrapper removal; IOMMU log removal; native wake-list guard; PM wake recorder PASS'

print(json.dumps(RESULTS, indent=2))
