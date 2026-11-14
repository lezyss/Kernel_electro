# Review: 14 manipvlator SM6150 UFS commits

Scope: read-only code review against the current Kernel_electro worktree.
No UFS/PHY code, configuration or runtime settings changed; no commit, push or
CI dispatch. The locally applied F2FS sysfs-width fix remains untouched.

Donor repository: https://github.com/manipvlator/los_kernel_xiaomi_sm6150

## Result

All 14 requested changes are already represented: 8 donor patches pass an exact
`git apply --reverse --check` (check only; no patch reversed), 5 have equivalent
implementations with later context changes, and 1 intermediate fix is superseded.
All 7 reviewed production UFS/PHY files are byte-identical to local baseline
HEAD 4afc6f0769f0f3b2b10d50d3fa02f0ba7c89a183. These findings do not depend on
unpublished local UFS modifications. Equivalent code does not establish that the
identical donor SHA is in history (history available here is limited).

| # | Donor SHA | Purpose | Current-tree finding / recommendation |
|---|---|---|---|
| 1 | 4443f3415beb4f7883ded3671fb9c736bd15871d | Binary PHY power-state tracking under mutex | Equivalent present in generic PHY core, phy descriptor and UFS init/suspend/resume/clock/exit paths. Do not reapply. Cross-subsystem power/refcount semantics require care; not a universal safety certification. |
| 2 | 46e0f43715a894405e6e1295b34e2290d40a3b9a | Read descriptor header via full-size temporary buffer | Exact reverse check passes. Useful memory-safety intent, already present. |
| 3 | 1070d5ea8c6e448c2a31d343dc10923130c8c14d | Clamp descriptor copy using offset plus size | Superseded by #4: no is_kmalloc branch or clamp remains. Do not reintroduce this intermediate implementation. |
| 4 | 4c6eba0bf4663b6cf7c9e49881955b4623515e8b | Descriptor boundary check and always use temporary allocation | Exact reverse check passes. Strong correctness candidate if missing, but already present here. This does not certify all descriptor/error-response validation. |
| 5 | 2d73f3e1f0eef85430e8974c41e13e8a51a0600f | Clear cmd and finish LRB access before tag release, release PM afterwards | Equivalent ordering present in normal completion and outstanding-request abort; later QoS hooks differ. Keep existing code, no duplicate. |
| 6 | ada38c688f61f867eab8b10a12156f05f181c23c | Disable IRQ before suspend clock-off; restore on unwind | Exact reverse check passes. Useful unclocked-register-access avoidance, already present. |
| 7 | 7fe5f315f1657855c4ae9d741e33c7fb39f03ee3 | Avoid reporting clocks on while gate worker is pending/running | Exact reverse check passes, including gate_wk_in_process descriptor field. Already present; runtime race stress not performed. |
| 8 | d2d9b57e2f5622830115ad110c27a411fe5ccd15 | Clear outstanding task bit after TM timeout | Exact reverse check passes. Correctness/power-accounting intent, already present. |
| 9 | edd40ed0ed03c2a0f67959f4dfd8ce0d28287f6d | Pair SCSI block count with newly queued ungate work | Exact reverse check passes. Already present, not a new optimization. |
| 10 | 34aedc2a850d6b04b31542e909a283fb20106417 | Add Micron NO_LINK_OFF quirk | Exact reverse check passes. Existing Toshiba/WDC entries predate this donor change. Vendor-specific reliability/power tradeoff, not a global speed tweak. |
| 11 | c89ea464a3758eb288523566d48c9d04730195fa | Remove Qualcomm's old UFS PM QoS implementation | Equivalent present: old qcom callbacks, request structures and debugfs PM QoS controls absent; replacement in #12 exists. Do not apply removal as an isolated optimization. |
| 12 | 84390c4eec6e8b6b27edeee37c68f394b2462c77 | Generic IRQ-affined UFS PM QoS with get/put workers | Equivalent present: request counting, worker mutex, IRQ affinity, queue/error/completion/abort hooks, init/remove paths. Worker latency subsequently changed by #13. Not a new patch to add; lifetime/error-path and device behavior still merit testing if ever redesigned. |
| 13 | beac5b880f2f5f8e5dc0010e5ea86d398f64be46 | Set replacement QoS latency to 67 microseconds | Exact reverse check passes. Local worker already requests 67; sdmmagpie.dtsi and sm6150.dtsi also contain <67 67> in old QoS DT properties. Those old properties do not prove the replacement uses them: it hardcodes 67. This is CPU idle-latency QoS, not UFS I/O completion time, CPU frequency or a measured benchmark. |
| 14 | d9f27b52b3679bc07a9eba79b137b4fb620d6a1a | Global NO_FASTAUTO quirk, prefer FASTMODE | Equivalent wildcard UFS_ANY_VENDOR/UFS_ANY_MODEL entry exists. Broad hardware stability/power policy, not proof of all-device applicability or a maximum-gear/frequency lock. Do not duplicate or revert without device evidence. |

## Direct code evidence

* `drivers/phy/phy-core.c`: phy_power_on/off use is_binary_power_count while
  holding phy->mutex. PM-runtime and regulator work also exists outside this
  state bit, so binary power_count alone is not proof of complete ref balancing.
* `include/linux/phy/phy.h`: is_binary_power_count field.
* `drivers/scsi/ufs/ufs-qcom.c`: generic PHY flag enabled during init; explicit
  power-on/error unwind; no is_phy_pwr_on host flag; old PM QoS hooks absent.
* `drivers/scsi/ufs/ufs-qcom.h` and `ufs-qcom-debugfs.c`: removed old PM QoS
  structures/operations are not present; unrelated debugfs support remains.
* `drivers/scsi/ufs/ufshcd.c`: ufshcd_read_desc_length calls read_desc_param;
  read_desc_param rejects offset+size beyond mapped allocation, allocates its
  own buffer and copies to caller. #3's is_kmalloc clamp is absent by design.
* Same file: normal completion and abort set lrbp->cmd=NULL before releasing
  lrb_in_use, and release PM after the tag; suspend disables IRQ before clocks
  and enables IRQ at set_link_active; TM timeout clears outstanding_tasks under
  host_lock; hold increments block requests only when queue_work succeeds.
* Same file: Micron NO_LINK_OFF and wildcard NO_FASTAUTO table entries; get/put
  QoS workers/counters, 67-us active request and PM_QOS_REQ_AFFINE_IRQ setup.
* `drivers/scsi/ufs/ufshcd.h`: gate_wk_in_process and new pm_qos object.

## Judgment

Descriptor bounds, completion ordering, IRQ-before-clock ordering, timeout
cleanup and balanced request blocking are sensible correctness fixes to retain.
They offer no extra benefit from applying the same code twice. #2/#3/#4 are an
evolution of one area, not three independent gains. #11/#12/#13 form a replacement
and tuning sequence, not safe independent cherry-picks. #1 changes generic PHY
semantics; #10 and #14 are hardware power-mode quirks. Existing does not mean
universally optimal or rigorously proven safe.

No new UFS benchmark, error-injection, concurrency, suspend/resume or device
storage test was run. No full ARM64 build/link was run. For a future UFS redesign,
validate probe/unwind, repeated runtime/system suspend, error recovery/timeouts,
long mixed I/O and data integrity, request/QoS reference balance and idle power.
Do not trigger raw storage errors or destructive tests on valuable device data.

The separately applied F2FS width test and its artifact/policy seals were rerun
successfully to verify it was preserved. That test is not UFS validation.
