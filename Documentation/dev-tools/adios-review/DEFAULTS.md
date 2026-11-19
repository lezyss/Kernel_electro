# Current miatoll ADIOS defaults and short output names

The user requested ADIOS as the default after the prototype booted, selected
ADIOS on sda, passed file creation/copy/move and app-install checks, recorded
increasing runtime-suspended time, reported fallback_count=0, and retained both
32 MiB test-file hashes across reboot. These are bounded smoke-test results,
not recovery, power-loss, performance or long-term safety qualification.

## Default selection

The miatoll source defconfig and normal manual workflow now enable:

* SCSI_MQ_DEFAULT, BLK_MQ_RUNTIME_PM
* MQ_IOSCHED_ADIOS, MQ_IOSCHED_DEFAULT_ADIOS
* MQ_IOSCHED_DEADLINE as a built-in fallback

Polly stays default-on. CFQ remains compiled and the legacy-queue default; it is
not the active scheduler of a blk-mq queue. The ADIOS algorithm itself is unchanged
from the smoke-tested prototype: fixed controls, no scheduler-assisted merging
or shallow tag throttling, allocation-failure FIFO fallback, completion-driven
learning, and single-hctx/nonrotational restrictions remain.

The new default option prefers ADIOS on eligible single-hardware-queue,
nonrotational mq queues. This is a queue-class policy, not an sda-only rule.
Rotational queues retain mq-deadline, and multi-hctx queues retain their prior
selection behavior. Explicit scheduler requests are not silently overridden.

SCSI allocates its queue before sd reads disk rotational characteristics. Thus,
an early elevator_init change alone would not make UFS boot on ADIOS. At disk
queue registration, under the existing sysfs lock and before elevator sysfs
publication, the policy revisits only an unregistered provisional mq-deadline
queue. It freezes/drains the queue, clears its I/O contexts, exits the old
scheduler, reinitializes the configured default and unfreezes. If automatic
ADIOS initialization fails, it tries mq-deadline. Missing ADIOS also falls back;
errors from an explicitly requested scheduler remain errors. The opt-out does
not run this late selection step.

This introduces boot-time selection earlier than the user's manual post-boot
trial; a new build and device boot check are required. Android policy can still
change a scheduler afterward. Verify rather than assume:

```sh
su -c 'for d in /sys/block/sd*; do echo "$d"; cat "$d/queue/scheduler"; done'
```

Expected on eligible physical UFS queues: `[adios]`, with mq-deadline available.
Keep the known-working boot image and off-device backup.

## Comparison and recovery switches

The workflow stays manual-only. `polly`, `scsi_mq`, `scsi_mq_pm` and `adios` now
default true; the storage choices must remain consistent.

* mq-deadline comparison: keep mq/PM true and set **adios=false**. The build
  explicitly disables both ADIOS options even though the source defconfig
  enables them.
* Legacy CFQ comparison: set **scsi_mq=false, scsi_mq_pm=false, adios=false**.
* Local miatoll build: the three TEST_* storage variables default to 1. Use
  `TEST_ADIOS=0` for mq-deadline, or all three variables =0 for legacy CFQ.
* Other defconfigs do not gain implicit local storage defaults. With the
  workflow's miatoll-oriented true inputs, select appropriate explicit opt-outs
  before requesting another defconfig; the miatoll-only mq guard remains.

The Kconfig symbols still default n globally; only the miatoll defconfig and
its build/workflow defaults opt into this behavior. Native raw defconfig builds
therefore also receive the requested default without depending on CI scripts.

## Output names

Flashable ZIP and checksum:

```
kernel-electro-miatoll-4.14.357.zip
kernel-electro-miatoll-4.14.357.zip.sha256
```

Actions artifact names:

* `kernel-electro-miatoll-4.14.357` — flashable ZIP and checksum
* `kernel-electro-miatoll-4.14.357-images` — kernel images/modules
* `kernel-electro-miatoll-4.14.357-details` — logs/config/toolchain provenance

No toolchain/date/Polly/mq/PM/prototype/run suffix accumulates in these names.
Different comparison builds intentionally use the same basename; keep them in
separate folders. Metadata inside the ZIP and details artifact retains the
actual kernel release, commit, build identifier, resolved variant and compiler
provenance. The actual kernel release and SUSFS uname spoofing are unchanged.

## Validation

* Actual ARM64 Kconfig resolution confirms all five storage settings, Polly,
  CFQ and existing UFS/crypto guards.
* Extracted elevator_init and late-selection host mocks cover supported and
  unsupported queues, nonrot detection at registration, absent/failed ADIOS,
  explicit selection errors, balanced references, and freeze/unfreeze balance.
* The unchanged ADIOS core UBSan test, PM tests, synthetic build/package tests,
  Neutron contracts, and shell syntax checks are rerun. Package fixtures check
  the exact short basename, stale-entry replacement, metadata and checksum.

These host checks do not execute real kernel concurrency or UFS. A full kernel
build and a fresh device default-selection/idle-wake/integrity check remain
separate gates. Preserve recovery options; do not infer a safety or battery
improvement from making the requested default change.
