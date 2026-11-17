/*
 * Copyright (c) 2014-2019, The Linux Foundation. All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 and
 * only version 2 as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 */

#define pr_fmt(fmt) "arm-memlat-mon: " fmt

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/interrupt.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <linux/of_irq.h>
#include <linux/slab.h>
#include <linux/irq.h>
#include <linux/cpu_pm.h>
#include <linux/cpu.h>
#include <linux/of_fdt.h>
#include "governor.h"
#include "governor_memlat.h"
#include <linux/perf_event.h>
#include <linux/of_device.h>
#include <linux/completion.h>
#include <linux/math64.h>
#include <linux/mutex.h>
#include <linux/sched.h>
#include <linux/smp.h>
#include <soc/qcom/scm.h>

enum ev_index {
	INST_IDX,
	CM_IDX,
	CYC_IDX,
	STALL_CYC_IDX,
	NUM_EVENTS
};
#define INST_EV		0x08
#define L2DM_EV		0x17
#define CYC_EV		0x11

struct event_data {
	struct perf_event *pevent;
	u64 prev_count;
};

struct cpu_pmu_stats {
	struct event_data events[NUM_EVENTS];
	ktime_t prev_ts;
	ktime_t sample_ts;
	u64 totals[NUM_EVENTS];
	bool have_prev;
	bool sample_valid;
	struct dev_stats *devstats;
	call_single_data_t csd;
	struct completion done;
};

struct cpu_grp_info {
	/* Serializes sampling, event creation and teardown. */
	struct mutex lock;
	bool running;
	cpumask_t cpus;
	unsigned int event_ids[NUM_EVENTS];
	struct cpu_pmu_stats *cpustats;
	struct memlat_hwmon hw;
};

struct memlat_mon_spec {
	bool is_compute;
};

#define to_cpustats(cpu_grp, cpu) \
	(&(cpu_grp)->cpustats[(cpu)])
#define to_cpu_grp(hwmon) container_of(hwmon, struct cpu_grp_info, hw)


/* No partial sample is published and no baseline moves on a failed read. */
static void memlat_read_cpu(void *info)
{
	struct cpu_pmu_stats *cpustats = info;
	u64 totals[NUM_EVENTS] = { 0 };
	int i;

	for (i = 0; i < NUM_EVENTS; i++) {
		struct perf_event *event = cpustats->events[i].pevent;

		if (event && perf_event_read_local(event, &totals[i], NULL, NULL))
			goto out;
	}

	memcpy(cpustats->totals, totals, sizeof(totals));
	cpustats->sample_ts = ktime_get();
	cpustats->sample_valid = true;
out:
	/* Last access: the waiter may proceed to teardown after completion. */
	complete(&cpustats->done);
}

/* Exact floor(100 * stall / cycles), including large u64 counter deltas. */
static unsigned int memlat_stall_pct(u64 stall, u64 cycles)
{
	u64 q, rem, threshold;
	unsigned int lo = 0, hi = 100, mid;

	if (!cycles)
		return 0;
	stall = min(stall, cycles);
	if (stall <= (~0ULL / 100))
		return div64_u64(stall * 100, cycles);

	/* Avoid multiplying a near-U64_MAX count by 100. */
	q = div64_u64_rem(cycles, 100, &rem);
	while (lo < hi) {
		mid = (lo + hi + 1) / 2;
		threshold = q * mid + DIV_ROUND_UP(rem * mid, 100);
		if (stall >= threshold)
			lo = mid;
		else
			hi = mid - 1;
	}
	return lo;
}

static void memlat_clear_stats(struct cpu_pmu_stats *cpustats)
{
	struct dev_stats *stats = cpustats->devstats;

	stats->inst_count = 0;
	stats->mem_count = 0;
	stats->freq = 0;
	stats->stall_pct = 0;
}

static void compute_perf_counters(struct cpu_pmu_stats *cpustats)
{
	struct dev_stats *stats = cpustats->devstats;
	u64 delta[NUM_EVENTS];
	s64 elapsed;
	int i;

	if (cpustats->have_prev) {
		elapsed = ktime_to_us(ktime_sub(cpustats->sample_ts,
					      cpustats->prev_ts));
		if (elapsed <= 0)
			return;
		for (i = 0; i < NUM_EVENTS; i++)
			delta[i] = cpustats->totals[i] -
				   cpustats->events[i].prev_count;

		stats->inst_count = min_t(u64, delta[INST_IDX], ULONG_MAX);
		stats->mem_count = min_t(u64, delta[CM_IDX], ULONG_MAX);
		stats->freq = min_t(u64, div64_u64(delta[CYC_IDX], elapsed),
				    ULONG_MAX);
		stats->stall_pct = cpustats->events[STALL_CYC_IDX].pevent ?
			memlat_stall_pct(delta[STALL_CYC_IDX], delta[CYC_IDX]) : 100;
	} else {
		/* First sample (also after hotplug) establishes a fresh epoch. */
		memlat_clear_stats(cpustats);
	}

	for (i = 0; i < NUM_EVENTS; i++)
		cpustats->events[i].prev_count = cpustats->totals[i];
	cpustats->prev_ts = cpustats->sample_ts;
	cpustats->have_prev = true;
}

static unsigned long get_cnt(struct memlat_hwmon *hw)
{
	struct cpu_grp_info *cpu_grp = to_cpu_grp(hw);
	cpumask_t pending;
	int cpu;

	mutex_lock(&cpu_grp->lock);
	if (!cpu_grp->running)
		goto out;

	cpumask_clear(&pending);
	/* Keep selected CPUs online until every accepted callback has finished. */
	cpus_read_lock();
	for_each_cpu(cpu, &cpu_grp->cpus) {
		struct cpu_pmu_stats *cpustats = to_cpustats(cpu_grp, cpu);

		if (!cpu_online(cpu) || cpu_isolated(cpu)) {
			cpustats->have_prev = false;
			memlat_clear_stats(cpustats);
			continue;
		}
		/* Preserve the native exclude-idle no-wakeup intent. */
		if (idle_cpu(cpu)) {
			memlat_clear_stats(cpustats);
			continue;
		}
		/* Best effort only: SCM can start after this check. Keep old data. */
		if (scm_call_in_progress())
			continue;

		cpustats->sample_valid = false;
		reinit_completion(&cpustats->done);
		if (!smp_call_function_single_async(cpu, &cpustats->csd))
			cpumask_set_cpu(cpu, &pending);
	}

	for_each_cpu(cpu, &pending) {
		struct cpu_pmu_stats *cpustats = to_cpustats(cpu_grp, cpu);

		/* No timeout: callbacks must never outlive event ownership. */
		wait_for_completion(&cpustats->done);
		if (cpustats->sample_valid)
			compute_perf_counters(cpustats);
	}
	cpus_read_unlock();
out:
	mutex_unlock(&cpu_grp->lock);
	return 0;
}

static void delete_events(struct cpu_pmu_stats *cpustats)
{
	int i;

	/* Called under the monitor mutex, after all sampling callbacks drain. */
	cpustats->have_prev = false;
	cpustats->sample_valid = false;
	cpustats->prev_ts = 0;
	memlat_clear_stats(cpustats);
	for (i = 0; i < ARRAY_SIZE(cpustats->events); i++) {
		cpustats->events[i].prev_count = 0;
		if (cpustats->events[i].pevent) {
			perf_event_release_kernel(cpustats->events[i].pevent);
			cpustats->events[i].pevent = NULL;
		}
	}
}

static void stop_hwmon(struct memlat_hwmon *hw)
{
	struct cpu_grp_info *cpu_grp = to_cpu_grp(hw);
	int cpu;

	mutex_lock(&cpu_grp->lock);
	cpu_grp->running = false;
	for_each_cpu(cpu, &cpu_grp->cpus)
		delete_events(to_cpustats(cpu_grp, cpu));
	mutex_unlock(&cpu_grp->lock);
}

static struct perf_event_attr *alloc_attr(void)
{
	struct perf_event_attr *attr;

	attr = kzalloc(sizeof(struct perf_event_attr), GFP_KERNEL);
	if (!attr)
		return attr;

	attr->type = PERF_TYPE_RAW;
	attr->size = sizeof(struct perf_event_attr);
	attr->pinned = 1;
	attr->exclude_idle = 1;

	return attr;
}

static int set_events(struct cpu_grp_info *cpu_grp, int cpu)
{
	struct perf_event *pevent;
	struct perf_event_attr *attr;
	int err, i;
	unsigned int event_id;
	struct cpu_pmu_stats *cpustats = to_cpustats(cpu_grp, cpu);

	/* Allocate an attribute for event initialization */
	attr = alloc_attr();
	if (!attr)
		return -ENOMEM;

	for (i = 0; i < ARRAY_SIZE(cpustats->events); i++) {
		event_id = cpu_grp->event_ids[i];
		if (!event_id)
			continue;

		attr->config = event_id;
		pevent = perf_event_create_kernel_counter(attr, cpu, NULL,
							  NULL, NULL);
		if (IS_ERR(pevent))
			goto err_out;
		cpustats->events[i].pevent = pevent;
		perf_event_enable(pevent);
	}

	kfree(attr);
	return 0;

err_out:
	err = PTR_ERR(pevent);
	kfree(attr);
	return err;
}

static int start_hwmon(struct memlat_hwmon *hw)
{
	struct cpu_grp_info *cpu_grp = to_cpu_grp(hw);
	int cpu, ret = 0;

	mutex_lock(&cpu_grp->lock);
	if (cpu_grp->running)
		goto out;
	for_each_cpu(cpu, &cpu_grp->cpus) {
		ret = set_events(cpu_grp, cpu);
		if (ret) {
			pr_warn("Perf event init failed on CPU%d\n", cpu);
			goto unwind;
		}
	}
	cpu_grp->running = true;
	goto out;
unwind:
	/* Includes the failing CPU's partially created events. Never skip SCM. */
	for_each_cpu(cpu, &cpu_grp->cpus)
		delete_events(to_cpustats(cpu_grp, cpu));
out:
	mutex_unlock(&cpu_grp->lock);
	return ret;
}

static int get_mask_from_dev_handle(struct platform_device *pdev,
					cpumask_t *mask)
{
	struct device *dev = &pdev->dev;
	struct device_node *dev_phandle;
	struct device *cpu_dev;
	int cpu, i = 0;
	int ret = -ENOENT;

	dev_phandle = of_parse_phandle(dev->of_node, "qcom,cpulist", i++);
	while (dev_phandle) {
		for_each_possible_cpu(cpu) {
			cpu_dev = get_cpu_device(cpu);
			if (cpu_dev && cpu_dev->of_node == dev_phandle) {
				cpumask_set_cpu(cpu, mask);
				ret = 0;
				break;
			}
		}
		dev_phandle = of_parse_phandle(dev->of_node,
						"qcom,cpulist", i++);
	}

	return ret;
}

static struct device_node *parse_child_nodes(struct device *dev)
{
	struct device_node *of_child;
	int ddr_type_of = -1;
	int ddr_type = of_fdt_get_ddrtype();
	int ret;

	for_each_child_of_node(dev->of_node, of_child) {
		ret = of_property_read_u32(of_child, "qcom,ddr-type",
							&ddr_type_of);
		if (!ret && (ddr_type == ddr_type_of)) {
			dev_dbg(dev,
				"ddr-type = %d, is matching DT entry\n",
				ddr_type_of);
			return of_child;
		}
	}
	return NULL;
}

static void init_cpu_stats(struct cpu_grp_info *cpu_grp)
{
	struct memlat_hwmon *hw = &cpu_grp->hw;
	int cpu, index = 0;

	for_each_cpu(cpu, &cpu_grp->cpus) {
		struct cpu_pmu_stats *cpustats = to_cpustats(cpu_grp, cpu);

		cpustats->devstats = &hw->core_stats[index++];
		cpustats->devstats->id = cpu;
		init_completion(&cpustats->done);
		cpustats->csd.func = memlat_read_cpu;
		cpustats->csd.info = cpustats;
	}
}

static int arm_memlat_mon_driver_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct memlat_hwmon *hw;
	struct cpu_grp_info *cpu_grp;
	const struct memlat_mon_spec *spec;
	int ret;
	u32 event_id;

	cpu_grp = devm_kzalloc(dev, sizeof(*cpu_grp), GFP_KERNEL);
	if (!cpu_grp)
		return -ENOMEM;
	mutex_init(&cpu_grp->lock);
	hw = &cpu_grp->hw;

	hw->dev = dev;
	hw->of_node = of_parse_phandle(dev->of_node, "qcom,target-dev", 0);
	if (!hw->of_node) {
		dev_err(dev, "Couldn't find a target device\n");
		return -ENODEV;
	}

	if (get_mask_from_dev_handle(pdev, &cpu_grp->cpus)) {
		dev_err(dev, "CPU list is empty\n");
		return -ENODEV;
	}

	hw->num_cores = cpumask_weight(&cpu_grp->cpus);
	hw->core_stats = devm_kzalloc(dev, hw->num_cores *
				sizeof(*(hw->core_stats)), GFP_KERNEL);
	if (!hw->core_stats)
		return -ENOMEM;

	/* Index by CPU id, including holes in a non-contiguous DT CPU list. */
	cpu_grp->cpustats = devm_kcalloc(dev, nr_cpu_ids,
				       sizeof(*cpu_grp->cpustats), GFP_KERNEL);
	if (!cpu_grp->cpustats)
		return -ENOMEM;

	cpu_grp->event_ids[CYC_IDX] = CYC_EV;

	init_cpu_stats(cpu_grp);

	hw->start_hwmon = &start_hwmon;
	hw->stop_hwmon = &stop_hwmon;
	hw->get_cnt = &get_cnt;
	if (of_get_child_count(dev->of_node))
		hw->get_child_of_node = &parse_child_nodes;

	spec = of_device_get_match_data(dev);
	if (spec && spec->is_compute) {
		ret = register_compute(dev, hw);
		if (ret)
			pr_err("Compute Gov registration failed\n");

		return ret;
	}

	ret = of_property_read_u32(dev->of_node, "qcom,cachemiss-ev",
				   &event_id);
	if (ret) {
		dev_dbg(dev, "Cache Miss event not specified. Using def:0x%x\n",
			L2DM_EV);
		event_id = L2DM_EV;
	}
	cpu_grp->event_ids[CM_IDX] = event_id;

	ret = of_property_read_u32(dev->of_node, "qcom,inst-ev", &event_id);
	if (ret) {
		dev_dbg(dev, "Inst event not specified. Using def:0x%x\n",
			INST_EV);
		event_id = INST_EV;
	}
	cpu_grp->event_ids[INST_IDX] = event_id;

	ret = of_property_read_u32(dev->of_node, "qcom,stall-cycle-ev",
				   &event_id);
	if (ret)
		dev_dbg(dev, "Stall cycle event not specified. Event ignored.\n");
	else
		cpu_grp->event_ids[STALL_CYC_IDX] = event_id;

	ret = register_memlat(dev, hw);
	if (ret)
		pr_err("Mem Latency Gov registration failed\n");

	return ret;
}

static const struct memlat_mon_spec spec[] = {
	[0] = { false },
	[1] = { true },
};

static const struct of_device_id memlat_match_table[] = {
	{ .compatible = "qcom,arm-memlat-mon", .data = &spec[0] },
	{ .compatible = "qcom,arm-cpu-mon", .data = &spec[1] },
	{}
};

static struct platform_driver arm_memlat_mon_driver = {
	.probe = arm_memlat_mon_driver_probe,
	.driver = {
		.name = "arm-memlat-mon",
		.of_match_table = memlat_match_table,
		.suppress_bind_attrs = true,
	},
};

module_platform_driver(arm_memlat_mon_driver);

MODULE_LICENSE("GPL v2");
