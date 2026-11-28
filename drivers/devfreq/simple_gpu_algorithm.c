// SPDX-License-Identifier: GPL-2.0
/*
 * Author: Paul Reioux aka Faux123 <reioux@gmail.com>
 *
 * Copyright (c) 2011~2014 Paul Reioux <reioux@gmail.com>
 * Copyright (c)      2018 Ryan Andri <ryanandri@linuxmail.org>
 *			   [Backport to New Adreno 5xx driver]
 *
 * This software is licensed under the terms of the GNU General Public
 * License version 2, as published by the Free Software Foundation, and
 * may be copied, distributed, and modified under those terms.
 */
#include <linux/module.h>
#include <linux/msm_adreno_devfreq.h>

static int default_laziness = 4;
module_param_named(simple_laziness, default_laziness, int, 0664);

static int ramp_up_threshold = 3000;
module_param_named(simple_ramp_threshold, ramp_up_threshold, int, 0664);

int simple_gpu_active = 1;
module_param_named(simple_gpu_activate, simple_gpu_active, int, 0664);

static int laziness;

/*
 * A busy interval above the ramp threshold steps one level up; an idle
 * interval steps one level down, but only after @default_laziness samples.
 * @num_levels is the GPU's power-level count, not the bus vote count.
 */
int simple_gpu_algorithm(int level, int *val,
			 struct devfreq_msm_adreno_tz_data *priv,
			 int num_levels)
{
	int ret = 0;

	if (level < 0 || level >= num_levels)
		goto out;

	if (priv->bin.busy_time > ramp_up_threshold) {
		if (level > 0)
			ret = -1;
	} else if (level < num_levels - 1) {
		if (laziness > 0) {
			laziness--;
		} else {
			ret = 1;
			laziness = default_laziness;
		}
	}

out:
	*val = ret;
	return ret;
}
EXPORT_SYMBOL(simple_gpu_algorithm);
