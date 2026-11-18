# Opt-in miatoll UFS/SCSI blk-mq experiment

## Scope and evidence

This is a queue-path experiment, **not an ADIOS port**. The initial mq-only
selection changes generated configuration, not vendor UFS/ICE, filesystems,
device-tree or boot arguments. It adds:

```
CONFIG_SCSI_MQ_DEFAULT=y
CONFIG_MQ_IOSCHED_DEADLINE=y
```

The source miatoll defconfig remains unchanged. Legacy CFQ support/default
selection remains compiled in; CFQ is not used on an mq queue. Neutron, the
boot-tested Polly flags, ThinLTO/SCS, crypto settings and Electro release naming
are unchanged. Normal workflow/local builds do not request this experiment.

User-provided runtime evidence from the existing legacy build:

* `scsi_mod.use_blk_mq` is `N`.
* The reported SCSI host is `host0`, driver `ufshcd`, with `use_blk_mq=0`.
* Physical `sda` through `sdf` advertise `noop [cfq]` and no `mq` directory.
* Loop devices use mq, demonstrating framework availability only.
* The supplied command line has no `scsi_mod.use_blk_mq` override. It does
  contain `lpm_levels.sleep_disabled=1`: screen-off alone must not be counted
  as evidence of actual system/deep suspend in device qualification.

No device identifiers or full boot command line are retained here.

## Runtime-PM regression discovered by device A/B

**The initial review below missed an explicit block-layer PM disable.**
The user booted the mq trial and verified host mq, mq-deadline and basic
file/reboot/unlock behavior, but sda reported `runtime_status=unsupported` and
the controller had zero suspended time. The CFQ comparison accumulated about
10 seconds of runtime-suspended time on both controller and sda.
`blk_pm_runtime_init()` explicitly calls `pm_runtime_disable()` on mq queues.
This is not a hardware-capability failure and cannot be repaired with
`power/control=auto` alone. Runtime suspend working on CFQ does not prove deep
system suspend; battery impact has not been measured.

CFQ remains the daily-driver baseline. A separate **default-off**
[experimental runtime-PM adaptation](../scsi-mq-pm/README.md) adds the missing
admission/refcount integration, not merely guard removal. It requires both
`scsi_mq=true` and `scsi_mq_pm=true`, a full build and new device qualification.
The mq-only selection retains its known PM limitation.

## Bounded source review (not a concurrency/safety proof)

| Area | Existing source path | Remaining qualification |
| --- | --- | --- |
| Selection | `drivers/scsi/Kconfig:SCSI_MQ_DEFAULT`, `scsi.c:scsi_use_blk_mq`, `hosts.c:scsi_host_alloc`, `scsi_scan.c:scsi_alloc_sdev` select the generic SCSI mq queue allocation. UFS does not set `force_blk_mq`. | Verify actual host selection after boot; boot arguments can override the compiled default. |
| Tags/submission | `scsi_lib.c:scsi_mq_setup_tags` sizes tag depth from `shost->can_queue` and defaults hardware-queue count to one when unspecified. `ufshcd.c:ufshcd_init` sets host depth to `nutrs`; `scsi_queue_rq` dispatches through the shared UFS `ufshcd_queuecommand`. UFS checks tag bounds and arbitrates device-management tag collisions using `lrb_in_use`. | Stress tag exhaustion, busy/requeue handling and concurrent management requests. No claim that modern UFS multi-controller queues are added. |
| Completion | UFS `__ufshcd_transfer_req_compl` unmaps DMA, completes crypto handling, releases the LRB and calls `cmd->scsi_done`. The SCSI mq callback is `scsi_mq_done`, which calls `blk_mq_complete_request`. | Verify lifetime, no double completion/stuck requests under real load and errors. |
| Inline crypto | `ufshcd_slave_configure` sets up the queue keyslot manager in the shared configuration path. `ufshcd_crypto_qti_prep_lrbp_crypto` reads request/bio crypto state or uses the separate Qualcomm ICE compatibility path. Generic bio submission performs `blk_crypto_submit_bio` before invoking the queue's make-request function; merge helpers compare crypto contexts. | Identify which branch encrypted `/data` exercises, verify content and key handling; no crypto mode/keyslot changes are proposed. |
| Recovery | SCSI mq supplies a timeout callback into `scsi_times_out`; UFS registers abort, device-reset, host-reset and timed-out handlers. Request blocking/unblocking and mq-aware device quiescing already exist in SCSI. | Source presence does not prove recovery races are safe. Controlled hardware/error testing remains unperformed; do not inject faults into daily-driver mounted data. |
| PM/crypto restore | UFS suspend/resume calls shared crypto hooks. Crypto enable has key reprogramming support; Qualcomm supplies its own enable/resume operations. Clock-gating and hibern8 holds remain in the shared request path. | Runtime PM, verified system suspend, reset/key restoration and unlock cycles require device tests. |

The reviewed UFS selection code had no explicit mq prohibition, but that was
not sufficient: the block-layer runtime-PM disable above was missed. This
inspection is not an exhaustive block-stack audit, an encrypted-data integrity
guarantee, or runtime sign-off.

`block/elevator.c:elevator_init` tries built-in `mq-deadline` when the mq queue
has one hardware queue, otherwise falls back to `none` if no scheduler was
selected. The experiment makes mq-deadline available; it does not force runtime
scheduler selection or rewrite Android init rules. Verify the active scheduler.

## Build selection, guards and labels

Manual workflow: select **scsi_mq=true**, using miatoll_defconfig. Locally, in the
pinned compatible Neutron container:

```sh
TEST_SCSI_MQ=1 bash scripts/ci/build-kernel.sh
```

`TEST_SCSI_MQ` defaults to `0`, accepts only `0` or `1`, and selection `1` is
restricted to the reviewed miatoll defconfig. Polly retains its established
separate default-on setting. The normal mode leaves storage settings as the
source defconfig requests; it does not silently rewrite other defconfigs.

After olddefconfig, ten guards require the two new options, UFS/QCOM/crypto,
inline-encryption/fallback and legacy CFQ/default-CFQ settings to remain built in.
The build records the selection in `out/build-info.txt`. Artifact names add
`-scsi-mq`; the ZIP label is derived from the resolved configuration, not the
caller's environment. The packager rejects an mq build missing built-in
mq-deadline and records a warning in package-info. The actual kernel release
remains `4.14.357-electro`; SUSFS uname spoofing is unchanged.

Local synthetic fixtures cover default-off, explicit opt-in alongside Polly,
invalid selection, ten lost-option cases and labeled packaging. They do not run
UFS or prove the actual Kconfig dependencies resolve. A later host run of the
real Kconfig parser resolved the miatoll PM trial with the expected options and
legacy/crypto guards. The compatible CI build must still supply compilation
evidence, followed by device testing.

## Before flashing and first checks

**Storage-path changes can cause failure to mount, corruption or data loss.**
Keep the working boot image, an off-device backup and a verified recovery/restore
method. A successful CI build is not permission to skip those precautions.
Do not change the live `use_blk_mq` module parameter or issue raw-device writes.

After boot, collect these read-only results before load tests:

```sh
su -c 'cat /sys/module/scsi_mod/parameters/use_blk_mq'
su -c 'for h in /sys/class/scsi_host/host*; do
  echo "$h"; cat "$h/proc_name" "$h/use_blk_mq" 2>/dev/null
done'
su -c 'for d in /sys/block/sd*; do
  echo "$d"; ls -d "$d/mq" 2>/dev/null; cat "$d/queue/scheduler"
done'
```

Expected selection evidence is `Y`, UFS host `1`, and physical-device `mq`
directories. Check for `[mq-deadline]` rather than assuming scheduler activation.
An overriding `scsi_mod.use_blk_mq=N` or Android policy may change the observed
result despite the compiled configuration.

Then incrementally test dedicated disposable files on encrypted `/data`, with
write/read content checks, fsync, bounded mixed I/O, app installation, reboot and
unlock, runtime idle/wake and verified suspend/resume. Capture available kernel
logs for UFS/SCSI/crypto errors, timeouts, resets, filesystem errors and hung
tasks. Screen-off is not proof of deep suspend. Neither a benchmark throughput
number nor successful boot establishes recovery correctness or long-term safety.

Stop testing and restore the known-working image on errors. Recovery fault
injection is a separate controlled qualification task, not part of this trial.
ADIOS remains absent; evaluate it only after the underlying mq path is qualified.
