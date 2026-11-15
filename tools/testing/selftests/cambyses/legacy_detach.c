// SPDX-License-Identifier: GPL-2.0
/* Frozen pre-Cambyses implementation for feature-off differential checks. */
static int legacy_detach_tasks(struct lb_env *env)
{
	struct list_head *tasks = &env->src_rq->cfs_tasks;
	struct task_struct *p;
	unsigned long load = 0;
	int detached = 0;
	int orig_loop = env->loop;
	u64 start_t = rq_clock(env->src_rq);

	lockdep_assert_held(&env->src_rq->lock);

	if (env->imbalance <= 0)
		return 0;

	if (env->src_rq->nr_running < 32) {
		if (!same_cluster(env->dst_cpu, env->src_cpu))
			env->flags |= LBF_IGNORE_PREFERRED_CLUSTER_TASKS;

		if (cpu_capacity(env->dst_cpu) < cpu_capacity(env->src_cpu))
			env->flags |= LBF_IGNORE_BIG_TASKS;
	}

redo:
	while (!list_empty(tasks)) {
		/*
		 * We don't want to steal all, otherwise we may be treated likewise,
		 * which could at worst lead to a livelock crash.
		 */
		if (env->idle != CPU_NOT_IDLE && env->src_rq->nr_running <= 1)
			break;

		p = list_last_entry(tasks, struct task_struct, se.group_node);

		env->loop++;
		/* We've more or less seen every task there is, call it quits */
		if (env->loop > env->loop_max)
			break;

		/* Abort the loop, if we spent more than 5 msec */
		if (rq_clock(env->src_rq) - start_t > 5000000)
			break;

		/* take a breather every nr_migrate tasks */
		if (env->loop > env->loop_break) {
			env->loop_break += sched_nr_migrate_break;
			env->flags |= LBF_NEED_BREAK;
			break;
		}

		if (!can_migrate_task(p, env))
			goto next;

		/*
		 * Depending of the number of CPUs and tasks and the
		 * cgroup hierarchy, task_h_load() can return a null
		 * value. Make sure that env->imbalance decreases
		 * otherwise detach_tasks() will stop only after
		 * detaching up to loop_max tasks.
		 */
		load = max_t(unsigned long, task_h_load(p), 1);


		if (sched_feat(LB_MIN) && load < 16 && !env->sd->nr_balance_failed)
			goto next;

		/*
		 * p is not running task when we goes until here, so if p is one
		 * of the 2 task in src cpu rq and not the running one,
		 * that means it is the only task that can be balanced.
		 * So only when there is other tasks can be balanced or
		 * there is situation to ignore big task, it is needed
		 * to skip the task load bigger than 2*imbalance.
		 */
		if (((cpu_rq(env->src_cpu)->nr_running > 2) ||
			(env->flags & LBF_IGNORE_BIG_TASKS)) &&
			((load / 2) > env->imbalance))
			goto next;

		detach_task(p, env);
		list_add(&p->se.group_node, &env->tasks);

		detached++;
		env->imbalance -= load;

#ifdef CONFIG_PREEMPT
		/*
		 * NEWIDLE balancing is a source of latency, so preemptible
		 * kernels will stop after the first task is detached to minimize
		 * the critical section.
		 */
		if (env->idle == CPU_NEWLY_IDLE)
			break;
#endif

		/*
		 * We only want to steal up to the prescribed amount of
		 * weighted load.
		 */
		if (env->imbalance <= 0)
			break;

		continue;
next:
#ifdef CONFIG_SCHED_WALT
		trace_sched_load_balance_skip_tasks(env->src_cpu, env->dst_cpu,
				env->src_grp_type, p->pid, load, task_util(p),
				cpumask_bits(&p->cpus_allowed)[0]);
#endif
		list_move(&p->se.group_node, tasks);
	}

	if (env->flags & (LBF_IGNORE_BIG_TASKS |
			LBF_IGNORE_PREFERRED_CLUSTER_TASKS) && !detached) {
		tasks = &env->src_rq->cfs_tasks;
		env->flags &= ~(LBF_IGNORE_BIG_TASKS |
				LBF_IGNORE_PREFERRED_CLUSTER_TASKS);
		env->loop = orig_loop;
		goto redo;
	}

	/*
	 * Right now, this is one of only two places we collect this stat
	 * so we can safely collect detach_one_task() stats here rather
	 * than inside detach_one_task().
	 */
	schedstat_add(env->sd->lb_gained[env->idle], detached);

	return detached;
}
