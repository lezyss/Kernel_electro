# ADIOS 3.3.0 Electro prototype 1

> **Current policy:** the user requested ADIOS as the miatoll default after
> device smoke tests. See [current defaults and naming](DEFAULTS.md). The
> default-off/manual-selection descriptions below record the earlier trial.

**Experimental storage scheduler. Back up data off-device and keep the working
CFQ boot image and a verified recovery method. Not qualified for irreplaceable
data, error recovery, long-term stability, performance or battery improvement.**

This implements the separately authorized prototype following [the initial
review](README.md). It adapts the pinned firelzrd/adios 3.3.0 algorithm, rather
than replacing 4.14 blk-mq/SCSI with a modern block stack. GPL-2.0 attribution is
preserved in `block/adios.c`. Upstream patch identity and hashes remain in
`source-manifest.json`; these identify the original input, not the adapted file.

## What stays unchanged

* Source miatoll defconfig, normal CFQ default, Polly default-on/off switch,
  runtime-PM backport and its separate explicit selection.
* mq-deadline stays built-in and remains the boot mq scheduler. **Building ADIOS
  does not select it.** No init/udev rules, boot arguments or default-elevator
  branch were added. Other queues remain on their current scheduler.
* Native block-core flush/FUA handling, tag limits, inline-crypto merge checks,
  vendor UFS/ICE, filesystems, device tree and release naming are unchanged.
* No generic cleanup macros, tag allocator ABI, scheduler callback ABI, modern
  SCSI quiescing or generic timer shutdown infrastructure is imported.

## Deliberate prototype differences from upstream

This is **not feature-equivalent upstream ADIOS**, and its results must not be
presented as benchmarks of stock ADIOS 3.3.0.

| Review issue | Prototype treatment |
| --- | --- |
| Callback ABI | Native `.ops.mq`, `uses_mq`, bool at_head, prepare(rq,bio), completion(rq) and started/requeue hooks. |
| Queue topology | init_sched/init_hctx reject multiple hardware queues and rotational devices. First target is the existing single-hctx UFS path. |
| Metadata allocation failure | Pool allocation is checked. A NULL-metadata request enters a high-priority allocation-free FIFO and skips model/accounting hooks safely. A read-only fallback counter records this. |
| Deadline-group allocation failure | Request enters the high-priority FIFO rather than disappearing from dispatch structures. Count/predicted-latency state remains balanced. |
| Merge ownership mismatch | Scheduler bio/request/insert merging is deliberately omitted; allow_merge rejects scheduler-assisted merging. No fake deferred-free shim, neighbor tree callbacks or hash membership. Native merging elsewhere in the stack is not replaced. This may affect CPU cost/throughput. |
| Shallow allocator mismatch | No scheduler limit_depth or depth_updated shim. Native blk-mq/SCSI tag limits still apply. There is no ADIOS shallow-depth throttling in prototype 1; the upstream code's chosen full queue depth is not a justification to change per-word allocation semantics. |
| Timestamp gap | Scheduler-owned allocation and per-hardware-attempt issue times, independent of CONFIG_BLK_CGROUP and shared stats. No issue timestamp reads from uninitialized native fields. |
| Flush/bypass private union | get_rq_data requires RQF_ELVPRIV before interpreting elv.priv. Pure flush/bypass requests can alias that union and must not be dereferenced as metadata. Core flush state machine remains responsible for ordering. |
| Rearm/teardown race | No model-update timer is created. Model aggregation runs from completions, rate-limited per model to roughly 100ms after bootstrap. With no completions, no new aggregation is scheduled. There is no rearmable timer to outlive the scheduler. |
| Model scratch sharing | Separate aggregation buffers per operation model; per-model update lock and per-CPU bucket locks protect remote snapshots against concurrent completion updates. |
| Tuning/reset races | Fixed upstream-derived settings; no writable tuning/reset/sideload interface in this trial. Only adios_version and fallback_count are exposed read-only. |
| Completion/requeue counts | managed means the request was added to packed counted state, not merely waiting in a deadline tree. Completion clears it; requeue/finish release it only if still counted. |
| Emergency priority | When both priority FIFO bits are set, queue 0 wins rather than selecting the normal bootstrap queue. |
| Dispatch flags | Native blk-mq owns request-start flags; scheduler dispatch does not manufacture RQF_STARTED. |

The learning/bias/deadline/batching algorithm, warm-up path, fixed per-operation
latency targets and batch limits are retained as the basis of the experiment.
Queue pressure, sample/model arithmetic and long-running behavior still need
real kernel/device qualification. Metadata now includes two timestamps and can
occupy a larger slab object than upstream; per-CPU buckets/snapshots also have
locks and per-model aggregation storage. No measured memory/performance claim.

## Build and package selection

Manual workflow: select **scsi_mq=true, scsi_mq_pm=true, adios=true**. Polly
remains independently true by default. Normal builds leave ADIOS disabled.
Local invocation requires the pinned compatible compiler host:

```sh
TEST_SCSI_MQ=1 TEST_SCSI_MQ_PM=1 TEST_ADIOS=1 bash scripts/ci/build-kernel.sh
```

Non-boolean ADIOS values, missing mq/PM prerequisites, missing resolved ADIOS
option, or lost existing storage/crypto guards fail the build. Kconfig makes
the prototype built-in-only, dependent on SCSI_MQ_DEFAULT and BLK_MQ_RUNTIME_PM,
and default n. The source defconfig is unchanged.

Artifact/ZIP names add **`-scsi-mq-pm-adios-prototype`** (along with Polly's
existing label). The ZIP label derives from resolved config and package metadata
warns that availability does not imply activation. No automatically selected
ADIOS image is offered in this prototype.

## Checks performed before the compile trial

* Host UBSan compiles the actual adapted C scheduling/model/request helpers
  against mocks and the tree's userspace rbtree implementation. 12,800 mixed
  requests are drained exactly once, with deadline/priority ordering, warm-up
  learning, both allocation failures, requeue with/without completion, finish
  cleanup and empty dispatch. The mock request intentionally has no native
  timestamp fields. A poisoned flush/private union without RQF_ELVPRIV verifies
  bypass callbacks do not interpret it as an ADIOS pointer.
* Real ARM64 Kconfig parser resolves baseline and ADIOS trial. Only
  SCSI_MQ_DEFAULT, MQ_IOSCHED_DEADLINE, BLK_MQ_RUNTIME_PM and MQ_IOSCHED_ADIOS
  become enabled; UFS/QCOM/crypto/CFQ/Polly guards remain intact.
* Existing synthetic LLVM/build/Polly/PM contracts and pinned AnyKernel3 package
  fixtures, including ADIOS selection/label tests; Neutron installer contracts;
  PM helper tests and shell syntax checks pass.

Reproduce host core test:

```sh
python3 tools/testing/selftests/adios/test_adios.py
```

Host mocks are single-threaded and do not execute real IRQ/RCU locking, kernel
scheduler initialization/unwind, UFS, encryption, flush persistence, recovery or
runtime PM. A successful host test is not proof of those properties. A full
compatible CI compile/package is a separate gate; no ADIOS device testing has
been performed by the agent.

## Controlled device trial after a successful build

1. Keep the known-working boot image and off-device backup. Start with the
   trial booting on **mq-deadline**. Verify UFS host mq selection and existing
   PM behavior first. Installing the artifact is not an ADIOS activation test.
2. Inspect available/active physical queue schedulers:

   ```sh
   su -c 'for d in /sys/block/sd*; do
     echo "$d"; cat "$d/queue/scheduler"
   done'
   ```

   Expect `adios` to be available, but `[mq-deadline]` initially selected.
3. Identify the physical queue backing the disposable encrypted `/data` test
   files (device-mapper layers/partitions can obscure it). **Do not assume sda
   is the right queue, and do not switch every LUN automatically.** Once the
   actual queue is identified, select only that queue via its scheduler sysfs
   file. In this example `sdX` is a placeholder, not a device to copy literally:

   ```sh
   su -c 'echo adios > /sys/block/sdX/queue/scheduler'
   su -c 'cat /sys/block/sdX/queue/scheduler'
   su -c 'cat /sys/block/sdX/queue/iosched/adios_version'
   su -c 'cat /sys/block/sdX/queue/iosched/fallback_count'
   ```

   Require `[adios]` and `3.3.0-electro-prototype1`. A sysfs failure is a failed
   activation, not permission to change queue depth or force hardware topology.
4. Incrementally test only disposable files: create/copy, write/fsync/read
   content verification, app install, idle/wake and runtime-PM counter deltas.
   Check available logs for WARNs, UFS/SCSI timeouts/resets, filesystem/crypto
   errors and hung tasks. Record fallback_count before/after; growth means the
   fallback path was used and should be reported, not hidden.
5. Restore that queue to mq-deadline after bounded tests:

   ```sh
   su -c 'echo mq-deadline > /sys/block/sdX/queue/scheduler'
   su -c 'cat /sys/block/sdX/queue/scheduler'
   ```

   An unresponsive queue may not permit live switching; use the verified
   recovery method and known-working boot image. Reboot ordinarily restores
   mq-deadline because no persistent selection policy was added. Android policy
   may differ, so always verify after boot.

Stop and restore the known-working image on errors or integrity failures.
No raw-device writes, mounted-data fault injection, daily-driver recovery tests
or automatic scheduler policy changes are part of this trial. Compare performance
only after basic integrity and PM checks, using the same kernel and workload
with only the selected scheduler changed.
