# ADIOS → Electro 4.14: compatibility and dependency review

> Historical review, before prototype implementation. The user subsequently
> authorized a trial. See [prototype 1](PROTOTYPE.md) for what was implemented,
> intentionally omitted, tested, and still unqualified. Statements below about
> ADIOS being absent describe the review checkpoint, not the current tree.

## Decision

**Conditional GO for a separately authorized, default-off prototype. NO-GO for
blind patch application, a flashable ADIOS trial today, or default selection.**

A scheduler-local adaptation looks technically plausible because this tree has
mq scheduler callbacks, cached rbtrees, per-request private pointers, mempools,
RCU and 64-bit atomics. However, integration is not a rename-only backport.
Request ownership, timing, resource failure, tag allocation and teardown must
be designed and tested before a device trial. This review does not establish
that the complete port will be bounded or correct.

**No scheduler implementation, Kconfig, Makefile, CI workflow, defconfig,
UFS/ICE, filesystem or PM code was changed by this review.** Only this report,
a source-evidence manifest and a read-only review checker were added. ADIOS
remains absent. CFQ remains the normal build default; mq-deadline plus the
experimental PM adaptation remains the comparison baseline. Polly is unchanged.

## Inputs and evidence

Reviewed upstream: `firelzrd/adios`, commit
`8117e935197fd45259ef77407b1c274d3386cd53`, specifically
`patches/stable/0001-linux6.12.44-ADIOS-3.3.0.patch` (1,991-line scheduler).
This is the lowest-version patch in that pinned tree; its 6.18/7.3 patches are
not a reason to import newer block infrastructure into 4.14. A filename is not
proof that even the advertised target accepts every API used by the patch.

Sources:

* https://github.com/firelzrd/adios/tree/8117e935197fd45259ef77407b1c274d3386cd53
* https://github.com/firelzrd/adios/blob/8117e935197fd45259ef77407b1c274d3386cd53/patches/stable/0001-linux6.12.44-ADIOS-3.3.0.patch
* https://github.com/firelzrd/adios/blob/8117e935197fd45259ef77407b1c274d3386cd53/README.md

The patch SHA-256 is
`ecfa33c53e09ea9ef7cd4d2df3dc7f5a49e467f1b8da74e945367f01ed95c315`.
`source-manifest.json` records reviewed local source hashes and upstream identity.
ADIOS line numbers below refer to the extracted C file, not patch line numbers.

The upstream README and patch are not fully synchronized: the README describes
four priority tiers including a separate FUA/PREFLUSH tier, while this exact C
file documents a three-tier approach relying on the block flush state machine.
Use the pinned code, not README behavior claims, as the porting reference.

Prior PM trial `fa94a5ede76a7ec13f6044c7e3cced505f61d0d2`, CI run
https://github.com/lezyss/Kernel_electro/actions/runs/44334469197 completed
**successfully**. The user subsequently reported file copy/create, app install,
reboot and runtime-suspended time increasing on controller and sda. Those are
useful baseline checks, not ADIOS tests, recovery qualification or a performance
claim. The user's approximately 40-minute idle sample did not account for all
40 minutes in these counters, so no deep-suspend fraction/battery inference is
made here.

## API/dependency map

| Area | Pinned ADIOS assumption | Actual 4.14 tree | Proposed bounded treatment |
| --- | --- | --- | --- |
| Registration | `.ops = {...}` for mq | `include/linux/elevator.h` has `.ops.mq` union and explicit `uses_mq`; lookup checks queue type | Use native mq registration and `.uses_mq = true`; do not change elevator core layout. |
| Headers/types | local `"elevator.h"`, `linux/math.h`, `blk_opf_t`, `blk_insert_t` | First two headers absent; callbacks use unsigned op and boolean at_head | Include existing kernel headers; use native callback types, not global compatibility typedefs. |
| prepare | `(request *)` | `(request *, bio *)` | Native wrapper; establish safe per-request metadata ownership before use. |
| bio merge | `(request_queue *, bio *, nr_segs)` | `(blk_mq_hw_ctx *, bio *)` | Obtain q from hctx and use this tree's segment/crypto merge checks. |
| request insertion | flags with BLK_MQ_INSERT_AT_HEAD | boolean `at_head` | Preserve head insertion priority using native bool; do not redefine global insertion ABI. |
| completion | callback supplies `now` | callback supplies only rq | Obtain monotonic now locally and audit per-attempt vs final completion, requeue and error semantics. |
| merge helpers | deferred `free` request/list, nr_segs argument | try_merge returns merged request via pointer; try_insert_merge may free synchronously | Rework ownership and locking. Do NOT mechanically add missing arguments or free a request twice. |
| allocation depth | queue-wide shallow depth; `depth_updated`; minimum-shallow helper | `sbitmap_get_shallow` caps **each word**; no callback/helper | Adapt to native per-word semantics with a proven wakeup bound and resize handling. No broad sbitmap replacement. |
| timestamps | usable rq start and issue timestamps | Fields conditional on BLK_CGROUP; mq initializes issue time to zero and does not set it in blk_mq_start_request | Prefer scheduler-owned allocation/issue timestamps and native started_request callback. Do not pretend enabling stats fixes this. |
| queue topology | QUEUE_FLAG_SQ_SCHED and modern rotational feature bit | Flag/feature absent; global mq schedulers already exist | Use `blk_queue_nonrot`. First prototype should reject nr_hw_queues != 1 until dispatch equivalence is reviewed. Do not add an inert SQ_SCHED bit. |
| statistics lifetime | enable/disable accounting helpers | enable exists; disable absent and enable is not a consumer refcount | Prefer owned timestamps without toggling shared stats. Do not clear another consumer's accounting state. |
| lock syntax | `guard`/`scoped_guard` cleanup macros | unavailable | Explicit spin_lock_irqsave/restore with an audit of every break/return/loop exit. No global cleanup infrastructure port. |
| timer lifetime | timer_reduce, timer_shutdown_sync | timer_setup/from_timer exist, reduce/shutdown do not | Local scheduling/cancellation protocol with stop state and producer drain. `mod_timer`/`del_timer_sync` are not automatically semantic equivalents. |
| list sorting | const list-head comparison arguments | existing comparator takes non-const pointers | Match native signature without casting function pointers. |
| structures/language | cached rbtrees, rq elv.priv, per-CPU/RCU, loop declarations | present; tree already builds GNU11 | Reuse existing facilities; no language-mode upgrade or rbtree backport needed. |

### Critical semantic traps

1. **Timing would silently disable learning if only made to compile.**
   `adios_completed_request` (1323–1385) rejects samples with zero
   `rq->io_start_time_ns`. This tree's `blk_mq_rq_ctx_init` zeroes it, and
   `blk_mq_start_request` does not fill it. `blk_stat_enable_accounting()`
   records packed `issue_stat`, not that field. Also rq timestamps disappear
   when BLK_CGROUP=n. Model deadlines and issue timing need an explicit design.

2. **Synchronous merge freeing matters.**
   In this tree, `blk_attempt_req_merge` calls `__blk_put_request`, which routes
   mq requests to `blk_mq_free_request` and then finish_request. The new helper
   API instead lets ADIOS free deferred requests after releasing its lock.
   Native adaptation must prove callbacks, metadata frees, tag release and
   scheduler restart cannot invalidate a still-used rq or recursively take locks.
   Keep native inline-crypto/key-context compatibility checks intact.

3. **Tag-depth units can produce a compiling but wrong allocator.**
   ADIOS assigns q->nr_requests directly to shallow_depth (813–843). Here that
   is a per-bitmap-word limit; a large value can effectively remove the limit.
   Inspect native Kyber conversion, wake_batch, reserved tags, tag exhaustion
   and nr_requests changes. A tiny per-word limit with unsuitable wake batching
   can also stall waiters. A no-op shim for the absent helper is not acceptable.

4. **Neighbor callbacks must match the tree actually maintained.**
   ADIOS registers elv_rb_former/latter_request but orders `dl_group.node`, not
   rq->rb_node. Native requests start with RB_CLEAR_NODE, so these callbacks do
   not provide useful ADIOS neighbors. Do not traverse the grouped deadline
   tree as if it were a request-sector tree. Prove a safe merge strategy;
   omission of optional neighbor callbacks may be preferable to bogus traversal.

## Source-level safety blockers before importing

These are review findings, **not observed failures on the user's phone** (which
has never run ADIOS here), nor a claim of exhaustive upstream bug diagnosis.

### A. Unchecked atomic metadata allocation — must resolve

`adios_prepare_request` (1004–1012) does mempool_alloc(GFP_ATOMIC), immediately
memsets the result and later dereferences it. Native mempool_alloc can return
NULL when its reserve and backing allocator are exhausted without direct
reclaim. A q->nr_requests-sized reserve is not a universal proof against this:
multi-hctx capacity and later nr_requests growth require analysis. Native
prepare_request cannot return allocation failure.

Prefer scheduler-lifetime, tag-indexed metadata reserved for all admitted
requests, or another demonstrably bounded allocation scheme. If retaining a
pool, prove its bound across resize and every bypass path, or provide a complete
NULL-safe fallback (including completion/finish) with forward progress.

### B. Deadline-group allocation failure can strand a request — must resolve

`add_to_dl_tree` (717–775) returns void on failed GFP_ATOMIC dl_group allocation.
Its caller has already removed rq from the insertion list, and
`merge_or_insert_to_dl_tree` still reports success-as-inserted (false-as-merged),
possibly hashing the request without placing it on a dispatchable list/tree.
This is a direct source-level missing fallback, not just a missing API.

Provide allocation-free fallback queueing with correct work-state bits, merge
hash membership, priority, completion accounting and removal semantics. Test
failure on first insertion and on merge-driven tree reinsertion.

### C. Model-update scratch sharing — needs design review/test

One `ad->aggr_buckets` scratch area is shared by all operation models, while
latency_model_update holds only that individual model's update_lock. Bootstrap
completion updates can run concurrently for different models, as can timer
activity versus completion. Establish common serialization or per-model
scratch; also review cross-CPU counter snapshots and sysfs reset/sideload races.
This source pattern is a concurrency concern, not a reproduced kernel race.

### D. Teardown/forward-progress obligations — must prove

Drain all live requests and prevent completion/bootstrap/sysfs/timer producers
from accessing scheduler state before freeing it. Replacing shutdown_sync with
del_timer_sync without proving that nobody can rearm afterward is insufficient.
Cover partial initialization unwind, repeated scheduler switches, RCU readers
and deferred callbacks/module unload, all queue types, and cancellation races.
Audit packed 16-bit-count/48-bit-latency arithmetic, tunable limits and model
sums under long-running load; do not assume their bounds from a successful boot.

## Essential vs excluded dependencies

**Essential:** native callback wrappers; request/merge lifetime adaptation;
correct tag depth/wakeup handling; reliable scheduler-owned timestamps; explicit
lock/timer lifecycle; no-loss allocation fallback; initialization/unwind and
RCU/model concurrency review; default-off build/package guards and test evidence.

**Not justified by this port:** a generic modern blk-mq/SCSI rewrite, global
sbitmap ABI change, new UFS hardware queues, vendor crypto or PM rewrites,
filesystem changes, ADIOS default-selection patch, global cleanup macros,
upstream desktop udev rules/adiosctl integration or benchmark-driven defaults.

Do not import upstream block/Makefile's added standalone `all`/`clean` module
recipes into in-tree Kbuild. Do not import the separate make-ADIOS-default
patch or the source patch's default-selection branch in elevator.c. Build any
prototype with explicit default n, not upstream's default m.

## Resource budget and staged acceptance plan

The two 64-entry bucket types total 2,560 bytes per lm_buckets. Four operation
models each allocate a bucket plus snapshot per possible CPU: **20 KiB per
possible CPU per queue**, before metadata pools, completion state, RCU model
versions and slab overhead. With eight possible CPUs and six selected LUNs this
component alone is about **960 KiB**. Measure actual allocation/reserve sizes;
initial testing should select only the intended queue(s), not all devices by
policy. This is a source-derived estimate, not measured phone memory usage.

1. **Prototype (separate approval):** scheduler-local implementation; fix above
   blockers; default n; one-hctx restriction; no auto-selection/default changes.
   Preserve CFQ normal build, mq-deadline fallback, PM backport, Polly and crypto.
2. **Host/static tests:** deadlines/tier order, batching, state bits, arithmetic,
   per-word depth/wakeup bounds, failing metadata/group allocators, merge/finish
   exactly-once ownership, canceled/requeued/OTHER/flush requests and teardown.
   Host mocks cannot prove kernel locking, RCU or UFS correctness.
3. **Kernel compile gates:** ADIOS off/on, module linkage if offered, debug
   configurations where practical, protected UFS/crypto/PM options and resolved
   defaults. Only then produce a clearly experimental opt-in artifact.
4. **Controlled runtime:** recoverable image and off-device backup; limited
   disposable encrypted files; fsync/read integrity; app install/reboot/unlock;
   mq PM idle/wake regression checks; hung-task/reset/crypto/filesystem logs;
   scheduler switch/drain and error tests only on suitable disposable hardware.
5. **Matched A/B:** compare mq-deadline and ADIOS on the same mq/PM/Polly kernel
   and repeatable workload. Collect latency distribution, throughput, CPU cost,
   memory and PM deltas. No speed, responsiveness or battery claim in advance.

## Checks actually performed

* Read pinned patch/source and this tree's elevator, merge, mq, tag, bitmap,
  timer, mempool, statistics, flush and native scheduler code.
* `git apply --check` rejected Kconfig.iosched, block/Makefile and elevator.c
  hunks; nothing was applied. Even a clean apply would not resolve ABI semantics.
* Read-only checker confirms 16 source contracts/mismatches against the pinned
  patch. It checks identities/patterns, **not compilation or correctness**.
* No ADIOS kernel build, scheduler runtime, fault injection or benchmark ran.

Reproduce the source check without applying anything:

```sh
mkdir -p .cache/adios-review
gh api 'repos/firelzrd/adios/contents/patches/stable/0001-linux6.12.44-ADIOS-3.3.0.patch?ref=8117e935197fd45259ef77407b1c274d3386cd53' \
  --jq .content | base64 -d > .cache/adios-review/adios-6.12.patch
PYTHONDONTWRITEBYTECODE=1 python3 tools/testing/selftests/adios_review/check_review.py \
  --patch .cache/adios-review/adios-6.12.patch
```

**Bottom line:** there is enough existing mq infrastructure to justify a bounded
prototype attempt, but the identified semantic and failure-path issues are
mandatory work, not optional optimization. Review completion is not approval to
flash ADIOS or change defaults.
