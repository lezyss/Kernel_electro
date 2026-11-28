Cambyses CFS load-balancer backport
===================================

This tree carries an adaptation of Cambyses v0.7.2 for its Linux 4.14 CFS load
balancer. The upstream reference is
`firelzrd/cambyses commit 330c39118a43
<https://github.com/firelzrd/cambyses/commit/330c39118a433047b0690d55826a8c04a38530a8>`_.
This is not a verbatim import of the newer-kernel patch: it preserves the
fork's native tail-first scan, migration filters, WALT integration and scan
limits.

Behavior
--------

``LB_ROTATE_BLOCK`` advances the tail-first scan window by rotating the examined
block once, rather than moving every rejected task individually. It retains the
local cursor-refresh and pre-detach list handling needed by this 4.14 scheduler.
Turn it off to use the original per-reject list movement.

``LB_CONCEDE_CHEAPEST`` changes load admission only for the first, non-redirected
balance into an idle CPU:

* A candidate costing no more than the remaining imbalance is admitted
  normally.
* An over-budget candidate is remembered only when its cost is strictly less
  than twice the remaining imbalance. If the scan admits no task, the cheapest
  such candidate is detached. This makes progress without accepting an
  overshoot that would leave a larger reverse imbalance.
* The concession is disabled after any task has already moved in the balance
  operation, after an affinity-driven destination redirect, for a busy
  destination, or when the feature is disabled. These cases retain this tree's
  original half-imbalance admission test.

``LBF_MOVED`` (bit ``0x20``) records successful progress and is sticky across
``more_balance`` retries. ``LBF_DST_REDIRECTED`` (bit ``0x40``) marks the retry
from an idle CPU to an alternate CPU in its scheduling group. The flags are
independent. The scheduler init log identifies this implementation as Cambyses
0.7.2.

4.14-specific safeguards
------------------------

The adaptation retains the local ``nr_running <= 2`` oversized-task exception,
the 5 ms runqueue-clock scan guard, the minimum non-zero hierarchical load
cost, ``LB_MIN``, ``can_migrate_task()`` eligibility checks, and the existing
vendor redo that relaxes big-task/preferred-cluster filters when a scan moves
nothing. It does not copy the modern upstream ``shr_bound()``/balance-failure
comparison: this 4.14 baseline used ``load / 2`` against the remaining
imbalance, so that is the fallback whenever the concession is ineligible.

WALT's ``detach_task()`` may release and reacquire the source runqueue lock.
Accordingly, the block rotation is completed before a detach, the saved
concession and scan cursor are cleared before the lock-dropping path, and the
cursor is refreshed after a successful detach. A saved concession is applied
only after a scan that detached nothing and did not hit the timeout, while the
source lock still protects the candidate. No candidate or cursor is carried
across balancing retries.

Validation
----------

The extracted userspace model and test runner are in
``tools/testing/selftests/cambyses/``. They use the real list helpers with
mocked scheduler context; they are not a kernel concurrency test or a
performance benchmark. The model covers all four PREEMPT/WALT combinations,
rotation and budget cases, timeout and retry behavior, migration-filter
preservation, WALT lock-drop churn, 3,000 feature-off comparisons with the
frozen pre-Cambyses loop, 12,000 randomized mixed-feature cases, and 16
runtime negative controls. See the selftest README for commands and coverage.

Object compilation and the userspace tests do not qualify a full device image.
A production-toolchain full build, boot, scheduler stress and device-specific
latency/power measurements are still required. Upstream Cambyses benchmark
results are not claimed as measurements of this 4.14 adaptation.
