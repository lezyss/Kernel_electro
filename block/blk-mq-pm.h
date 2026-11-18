/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _BLK_MQ_PM_H
#define _BLK_MQ_PM_H

#include <linux/pm_runtime.h>

/* Optional 4.14 adaptation of upstream mq runtime PM; legacy PM is unchanged. */
#ifdef CONFIG_BLK_MQ_RUNTIME_PM
static inline bool blk_mq_pm_managed(struct request_queue *q)
{
	return q->mq_ops && q->dev;
}

static inline bool blk_mq_pm_only(struct request_queue *q)
{
	return atomic_read(&q->mq_pm_only) != 0;
}

static inline void blk_mq_pm_request_resume(struct request_queue *q)
{
	if (blk_mq_pm_managed(q) &&
	    (READ_ONCE(q->rpm_status) == RPM_SUSPENDING ||
	     READ_ONCE(q->rpm_status) == RPM_SUSPENDED))
		pm_request_resume(q->dev);
}

static inline void blk_mq_pm_set_only(struct request_queue *q)
{
	atomic_inc(&q->mq_pm_only);
}

static inline void blk_mq_pm_clear_only(struct request_queue *q)
{
	int count = atomic_dec_return(&q->mq_pm_only);

	WARN_ON_ONCE(count < 0);
	if (!count)
		wake_up_all(&q->mq_freeze_wq);
}

static inline void blk_mq_pm_mark_last_busy(struct request *rq)
{
	if (blk_mq_pm_managed(rq->q) && !(rq->rq_flags & RQF_PM))
		pm_runtime_mark_last_busy(rq->q->dev);
}
#else
static inline bool blk_mq_pm_managed(struct request_queue *q)
{
	return false;
}

static inline bool blk_mq_pm_only(struct request_queue *q)
{
	return false;
}

static inline void blk_mq_pm_request_resume(struct request_queue *q) {}
static inline void blk_mq_pm_mark_last_busy(struct request *rq) {}
#endif

#endif
