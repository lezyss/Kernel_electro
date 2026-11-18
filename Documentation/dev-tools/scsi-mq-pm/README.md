# Experimental blk-mq runtime-PM adaptation for 4.14

## Why this exists

The first opt-in mq build (844ac0324) booted, selected mq-deadline on the physical
UFS LUNs, and passed the user's basic disposable-file/reboot/unlock checks. It
**regressed runtime PM**: the controller had zero suspended time and sda reported
`runtime_status=unsupported`. The user's CFQ A/B accumulated about 10 seconds of
runtime-suspended time on both controller and sda. This is device runtime-PM
evidence, not proof of system/deep suspend or a measured battery difference.

Root cause: `blk_pm_runtime_init()` explicitly disabled runtime PM for mq.
Deleting that guard alone would be unsafe: this tree lacked the mq allocation
gate and reference-count protocol that make suspend admission meaningful.

CFQ remains the recommended daily-driver baseline until device requalification.

## Bounded adaptation, not a wholesale SCSI update

`CONFIG_BLK_MQ_RUNTIME_PM` defaults to **n**, depends on PM and SCSI_MQ_DEFAULT,
and does not change the source miatoll defconfig. Legacy nr_pending accounting
and request_fn restarts are retained. Vendor UFS/ICE, filesystems, DT, boot
arguments, ADIOS and Polly policy are not changed.

The selected path implements:

* A PM-only admission counter, checked in a scheduler-RCU critical section
  together with obtaining the live queue reference. Scheduler RCU is deliberate:
  this tree's percpu-ref switch uses `call_rcu_sched()`, not ordinary RCU.
* Ordinary allocations wait (NOWAIT returns -EBUSY), request device resume during
  SUSPENDING/SUSPENDED, and wake when the gate opens. PM/internal SCSI commands
  carry BLK_MQ_REQ_PREEMPT **before** allocation; real queue freezes still apply.
  Existing scsi_execute commands already carry RQF_PREEMPT after allocation. The
  exemption is for that internal-command path, not arbitrary userspace I/O.
* RPM_SUSPENDING is published before freezing and atomically collecting queue
  references. Pending references cause -EBUSY and rollback, not unsafe suspend.
* Nonzero-safe percpu_ref_resurrect allows aborting a freeze with active users.
  percpu_ref_reinit retains its zero-count assertion for existing callers. The
  mq PM path restores the ref's per-CPU policy while still dead, before unfreeze;
  this older implementation otherwise retains force_atomic across resurrection.
* Failed suspend restores ACTIVE, marks last busy and releases admission. Resume
  reactivates the queue even after device resume error so recovery commands do
  not deadlock; the SCSI caller still returns its original device error. Repeated
  or system resume while already ACTIVE does not decrement the gate again.
* Ordinary mq request freeing marks the device busy; PM requests are excluded.

The implementation is adapted, not a clean cherry-pick: upstream changed the
queue-entry API, SCSI quiescing and PM interfaces across several releases. This
patch avoids importing that entire unrelated series. `upstream.json` retains
upstream commit identities, messages and relevant patches for provenance:

| Upstream commit | Relevance |
| --- | --- |
| 18c9a6bbe064 | percpu_ref_resurrect prerequisite |
| 3a0a529971ec, cd84a62e0078 | preempt-aware admission and PM-only counter design |
| 154b00d566e2, 0d25bd072b49 | separate legacy accounting; resume from admission wait |
| 7cedffec8e75, 986d413b7c15 | queue-reference suspend checks and mq runtime-PM enable |
| fa4d0f1992a9 | publish SUSPENDING before freeze/unfreeze admission race |
| 8f38f8e0a30e | balance already-active/system resume |
| 6e1fcab00a23 | release request queue on device resume failure for recovery |

This is not a claim that all later upstream PM fixes or vendor interactions have
been reproduced or proven safe.

## Explicit build selection

Manual workflow: **scsi_mq=true AND scsi_mq_pm=true**. Both default false;
Polly remains independently default true. Locally in the pinned compatible host:

```sh
TEST_SCSI_MQ=1 TEST_SCSI_MQ_PM=1 bash scripts/ci/build-kernel.sh
```

PM without mq, non-boolean values, a non-miatoll mq config, or loss of any required
resolved setting is rejected. Ordinary builds explicitly disable the PM option (Kconfig may omit it entirely
when its mq dependency is off).
The original mq-only selection remains available for comparison and retains its
known PM limitation. PM trial archives add `-scsi-mq-pm`, derived from resolved
configuration; the package metadata warns that device requalification is needed.
Actual kernel release and SUSFS uname spoofing are unchanged.

## Validation and limitations

Local checks performed during implementation:

* Compiled the real Kconfig parser on the host and resolved the ARM64 miatoll
  baseline and PM trial. Only SCSI_MQ_DEFAULT, MQ_IOSCHED_DEADLINE and the new PM
  option changed. UFS/QCOM/crypto, inline-encryption/fallback and CFQ guards held.
* `python3 tools/testing/selftests/scsi_mq_pm/test_pm.py`: extracted actual changed
  functions compiled with host mocks and UBSan, PM enabled/disabled. Exercises
  2,000 busy/suspend/resume cycles, internal versus ordinary admission, NOWAIT,
  blocking wake, queue freeze, removal, failed suspend/resume, repeated active
  resume, completion timestamps, and legacy restart/accounting. Six deliberate
  broken variants are rejected. This is **not real RCU or hardware execution**.
* Existing synthetic CI build/package tests, Neutron toolchain contracts and
  shell syntax checks; these are not a full kernel build.

The compatible CI build is a separate required compile gate. A successful build
alone does not validate storage safety, PM ordering, recovery or encrypted data.

## Device requalification (backups and recoverable image required)

Keep the known-working CFQ boot image and an off-device backup. Do not enable
this on irreplaceable data without a verified recovery method. Do not toggle
live use_blk_mq or perform raw-device writes.

1. Verify UFS host use_blk_mq=1, physical LUN mq directories and mq-deadline.
2. Read controller and every physical LUN's `power/control`, `runtime_status`,
   `runtime_suspended_time` and `runtime_active_time` before and after idle/wake.
   `unsupported` must be gone on managed LUNs; suspended-time counters must grow
   during an appropriate quiet interval, not necessarily at the same instant.
3. Repeat idle/wake cycles, first unloaded and then with bounded disposable-file
   I/O. Verify writes with fsync and content checks, then reboot and unlock.
   Check available logs for UFS/SCSI timeouts, resets, crypto errors, filesystem
   errors, WARNs and hung tasks. Verify all LUNs, not only sda.
4. Qualify actual system suspend separately. Screen-off and runtime counters do
   not prove deep/system suspend. Recovery/error injection belongs on disposable
   controlled hardware, never mounted daily-driver data.

Restore CFQ on hangs, integrity failures, storage errors or PM regression. Do not
turn the experiment into a default based on boot success alone.
