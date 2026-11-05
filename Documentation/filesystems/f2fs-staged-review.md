# F2FS /data upgrade: dependency and conflict review

## Status: historical review; staged implementation completed separately

This is the include/skip plan delivered **before** the approved staged port.
At review completion, no kernel source, defconfig, mount option or on-disk
format had changed. The findings and inventory below preserve that review-time
state, not a description of the current implementation.

**A → B1 → B2 are now implemented locally**, with opt-in/default-off merge
features. See [the implementation and validation record](f2fs-staged/implementation.md)
and `f2fs-staged/UPSTREAM.json` for applied boundaries and remaining runtime
validation. No push or CI dispatch was performed for either this review or port.

Device facts supplied by the user:

- `/`: `/dev/block/dm-0`, **ext4**, read-only.
- `/data`: `/dev/block/dm-43`, **F2FS**, read-write, including
  `background_gc=on,flush_merge,mode=adaptive,inlinecrypt,fsync_mode=nobarrier`.
- FinaSU/backslashxx KSU/SUSFS/NoMount boot and basic operation were reported
  working on-device before this review. Preserve that build as recovery baseline.

F2FS code is not hard-coded to `/data`; it applies to F2FS mounts. It does not
convert or replace the ext4 root filesystem. No EROFS/ext4 upgrade is proposed.

## Donor and scope

Reference: [manipvlator/los_kernel_xiaomi_sm6150
81605352aac4c8995b6346939cb3931e14c0d7b6](https://github.com/manipvlator/los_kernel_xiaomi_sm6150/commit/81605352aac4c8995b6346939cb3931e14c0d7b6).

The commit is titled "Merge branch 'upstream-f2fs-stable-linux-4.14.y'" but the
GitHub object has one parent, `64fd748b0d919e244bc24d404974373d30ef1770`.
Its parent-relative delta spans **73 files, 11,266 additions, 5,156 deletions**.
Only 31 of those paths are inside `fs/f2fs/`. The rest include shared VFS,
fscrypt, fs-verity, ext4, quota, DAX, UBIFS, MM, ABI and documentation changes.
This is not a small two-feature merge.

All 70 non-deleted donor postimages were retrieved/verified against their Git
blob SHA-1s; the three removed paths are recorded as deletions, not postimages.
The companion JSON lists a decision for **all 73 donor paths** and pins the
current source identities for proposed targets.

### Concrete regressions a wholesale replacement would risk

The current tree has three previously approved protections which the donor's
corresponding functions do **not** contain:

1. `gc_data_segment()`: explicit inline-data/external-block inconsistency guard;
   set NEED_FSCK, log while the inode reference is owned, then release/skip.
2. Compression reserve/release dnode loops: balanced checkpoint-operation read
   locks around lookup/mutation/release, including error exits.
3. Move-range and pin-file ioctls: existing atomic-file exclusion guards.

Therefore **do not copy the donor F2FS directory or whole `file.c`/`gc.c`**.
Preserve the existing inode-reference, locking and atomic-file fixes verbatim.
The existing `tools/testing/selftests/fs_backport/test_backport.py` integration
source guards still pass on the unmodified baseline.

## Recommended include list and implementation order

### Stage A — three bounded IPU correctness fixes first

IPU means in-place update; this is an existing writeback path, not a new on-disk
feature. These are additional upstream fixes discovered during the review;
blindly importing the supplied donor does not supply them.

| ID | Upstream source | Finding in our current tree | Proposed adaptation |
| --- | --- | --- | --- |
| A1 | [`5cdb422c839134273866208dad5360835ddb9794`](https://github.com/torvalds/linux/commit/5cdb422c839134273866208dad5360835ddb9794) | CP-error handling calls `f2fs_submit_merged_ipu_write(sbi, bio, NULL)` without checking `bio && *bio`. The helper accepts a null target, and its all-null page matcher can match an unrelated cached BIO. | Validate the CP-error caller and targeted-helper contract; audit all callers. Do not use a null-target call as a new flush-all interface. |
| A2 | [`edf7e9040fc52c922db947f9c6c36f07377c52ea`](https://github.com/torvalds/linux/commit/edf7e9040fc52c922db947f9c6c36f07377c52ea) | After publishing an IPU BIO, `f2fs_merge_page_bio()` classifies the possibly encrypted bounce `page`. Another submission/completion can free that bounce page. | Use the stable original file page for post-publication classification. Audit this 4.14 tree's `wbc_account_io()` call too; do not import modern folio/cgroup APIs wholesale. |
| A3 | [`6d1f622b9c069378cdb83088be2b15a9b480b8a3`](https://github.com/torvalds/linux/commit/6d1f622b9c069378cdb83088be2b15a9b480b8a3) | Successful IPU writes do not set `fio->submitted`; the caller uses it to account writeback progress/budget. | Set the successful submission flag without marking failed operations as submitted. |

**Stage A source scope: only `fs/f2fs/data.c` and `fs/f2fs/segment.c`.** Add
focused extracted-source models/provenance, then compile both device and
compression/encryption/cgroup-writeback validation variants. No mount-policy or
partition change is needed for these correctness fixes to take effect.

A code-pattern match establishes applicability for porting, not proof that the
reported phone has hit the original upstream bug. Stage A patches have not yet
been implemented or compiled in this review.

### Stage B1 — opt-in GC merge, with safety dependencies

Source: [`5911d2d1d1a38b26585383478bd71d9254e48bdf`](https://github.com/torvalds/linux/commit/5911d2d1d1a38b26585383478bd71d9254e48bdf).

Port `gc_merge`/`nogc_merge` parsing/reporting, a foreground-request waitqueue,
worker dispatch/wakeup, shutdown handling and mount/remount lifecycle. Preserve
current adaptive allocation, normal background-GC behavior and the local GC
corruption guard. **Leave GC merge disabled by default.** The donor explicitly
sets GC_MERGE in `default_options()`; that default change is excluded.

Required safety/adaptation checks:

- Our `f2fs_gc()` takes four arguments, whereas the original feature patch takes
  five and the donor has a different control-structure interface. Retain the
  current API/locking; do not pull a full GC redesign just to make calls compile.
- [`8b4468ec023d0d1b4669dfb867588997cc03a06b`](https://github.com/torvalds/linux/commit/8b4468ec023d0d1b4669dfb867588997cc03a06b): cached OPU and IPU DATA BIOs must be submitted before the caller waits
  for foreground GC, or writeback/truncate/GC can deadlock. Neither our tree
  nor this donor has `f2fs_submit_all_merged_ipu_writes()`. A correct drain-all
  helper and declaration are a **required local dependency**, with list-lock,
  ownership/refcount, duplicate-submit and failure tests. Audit publication of
  page/writeback counters and ownership before making a global drain reachable;
  test early completion, not only ordinary successful submission. A null-target
  call to the existing helper is not a substitute.
- [`1adaa71ea9bff3a0ca0b37eabbb7f89225b595cb`](https://github.com/torvalds/linux/commit/1adaa71ea9bff3a0ca0b37eabbb7f89225b595cb): a foreground request returning no victim must not distort the next
  background-GC sleep interval.
- Check request wakeup/stop/free ordering, CP errors, freezing, remount rollback,
  read-only mounts and `background_gc=off` combined with explicit GC merge.
- Review [`c836d3b8d94e3dd381e7d4bb918875084f85715e`](https://github.com/torvalds/linux/commit/c836d3b8d94e3dd381e7d4bb918875084f85715e) without importing its newer checkpoint-readiness prerequisites. Our
  existing readiness helper already rejects CP-disabled low-free-section
  balancing; preserve that protection and test state transitions.

**B1 candidate source scope:** `data.c`, `f2fs.h`, `gc.c`, `gc.h`, `segment.c`,
`super.c`, all inside `fs/f2fs/`. This is a corrected port, not a clean cherry-pick.

### Stage B2 — opt-in checkpoint merge, separately validated

Source: [`261eeb9c1585de4515a770b48a3c89672c08ae7f`](https://github.com/torvalds/linux/commit/261eeb9c1585de4515a770b48a3c89672c08ae7f).

Port the request/completion queue, checkpoint worker, CP_SYNC dispatch,
mount/remount/teardown/error cleanup and useful debug counters. Non-CP_SYNC
reasons must stay synchronous. **Leave checkpoint merge disabled by default.**
Do not import the donor's MERGE_CHECKPOINT default or the separate upstream
commit that enables it by default.

Dependencies/conditions before calling this implementation ready:

- The kernel already supplies completion, llist/reversal, kthread,
  `ktime_ms_delta()`, `sb_start_intwrite()` and `set_task_ioprio()` primitives;
  no generic VFS/locking upgrade is justified just to get those APIs.
- Every stack-allocated checkpoint request must complete exactly once, with the
  right error result and no dereference after completion releases its waiter.
  Stop/rollback must drain or complete outstanding requests before freeing state.
- Adapt [`7b02b2201893a71b881026cf574902019ab00db5`](https://github.com/torvalds/linux/commit/7b02b2201893a71b881026cf574902019ab00db5): the post-read workqueue must be cleaned up even if worker creation fails.
  Balance all initialized/not-initialized error labels and remount rollback.
- Audit quota/freeze lock ownership before dispatching work to a different
  task. [`f6f8f34480c78eade6542faea6386c47c9b4c6b3`](https://github.com/torvalds/linux/commit/f6f8f34480c78eade6542faea6386c47c9b4c6b3) is a warning/reference for this class of bug, **not an automatically
  applicable fix**: this 4.14 tree's quota/freeze interfaces differ. Establish a
  local safe synchronous fallback and validate it before enabling the feature.
- Skip the writable `ckpt_thread_ioprio` sysfs extension. The donor guards task
  access using the mount option, not actual worker existence; upstream
  [`5cb33b00c8fbb6e8f1fa3d281c3036d5f7c7c41f`](https://github.com/torvalds/linux/commit/5cb33b00c8fbb6e8f1fa3d281c3036d5f7c7c41f) fixes a NULL-thread/lifecycle issue in that interface. Avoid adding this
  unnecessary interface rather than adding it and forgetting its fix.

**B2 candidate source scope:** `checkpoint.c`, `debug.c`, `f2fs.h`, `super.c`.
Quota/freeze lifecycle is a remaining implementation gate, not a resolved or
runtime-tested property of this review.

## Exact combined source boundary

Stages A/B may selectively modify only these **eight** kernel source files:

```
fs/f2fs/checkpoint.c
fs/f2fs/data.c
fs/f2fs/debug.c
fs/f2fs/f2fs.h
fs/f2fs/gc.c
fs/f2fs/gc.h
fs/f2fs/segment.c
fs/f2fs/super.c
```

Extend the existing `Documentation/filesystems/f2fs.txt` instead of importing
its replacement wholesale. Add narrowly scoped tests/provenance separately.
If implementation discovers a genuinely necessary dependency outside that
boundary, stop and review it explicitly rather than silently widening the port.

## Skip/defer list

- **ATGC:** separate later stage, not enabled or ported now. It expands victim
  selection, segment-age tracking and allocation dependencies substantially.
- **Atomic-write COW redesign:** retain the current implementation and atomic
  exclusion fixes; no whole `file.c`/inode/recovery transplant.
- **Compression expansion:** no LZO-RLE/LZ4HC option changes, compressed-block
  cache, manual compression interfaces, checksums or on-disk feature changes.
  Retain existing compression locking fixes and disabled production compression.
- **fscrypt/fs-verity/shared VFS/ext4/UBIFS/DAX/quota/MM refreshes:** do not apply
  the donor's non-F2FS changes. Existing encrypted `/data` behavior must remain.
  Resolve only proven feature dependencies inside the reviewed scope.
- **Other F2FS refactors/tuning:** no whole iostat rewrite, trace deletion,
  segment/extent allocation policy rewrite, GC thresholds, reclaim-prefree
  tuning, mount defaults or new UAPI/on-disk layouts.
- **KSU/FinaSU/SUSFS/NoMount:** no source, policy, provenance or configuration
  changes. No ADB-root enablement is part of this task.
- **Device policy:** no fstab/initramfs edits, live remount, formatting,
  partition conversion or changes to `fsync_mode=nobarrier`/barrier ordering.

Supporting GC/checkpoint options while leaving defaults unchanged will **not
activate them on the user's existing mount**. Later opt-in activation/testing
needs a separate decision; do not claim a performance gain just from compiling
support. Code-only fixes do not inherently require formatting.

## Validation required after implementation

1. Source guards preserving all existing fixes and protected integrations;
   exact provenance and strict patch reproduction for each small stage.
2. Extracted production-function models: null target/matching BIO, encrypted
   page lifetime, IPU submission accounting; GC BIO drain/queue/wakeup/stop;
   checkpoint batching, error propagation, request lifetime and rollback.
   Include deliberate broken controls and nonrecovering UBSan where available.
3. ARM64 device/full-debug builds; compression, encryption and cgroup-writeback
   variants; whole-filesystem/KSU/SELinux partial link. Then production pinned
   AOSP Clang CI image/modpost/AnyKernel packaging, when separately requested.
4. Disposable F2FS-image/kernel tests for fsync/checkpoint concurrency, low-space
   GC, encrypted writes, quota/freeze/thaw, remount, unmount, startup failures
   and recovery. Never run destructive stress/power-loss tests on real `/data`.
5. Back up data and retain the known-good boot image. Device boot is necessary
   but not sufficient evidence of recovery/durability or long-term stability.

## Review checks performed

- Verified donor postimage Git blobs and inventoried all 73 changed paths.
- Traced both requested features to their original upstream commits plus the
  explicitly listed safety follow-ups; inspected current/donor call sites.
- `git apply --check` of both original feature patches (excluding documentation)
  rejects multiple source hunks. Both require real adaptation, not force-apply.
- Ran existing selected-filesystem integration source guards and KSU/FinaSU/
  SUSFS/NoMount provenance/config checks on the unchanged current sources.
- SHA-256 preservation check confirms all recorded F2FS/shared-source,
  KSU/NoMount/SUSFS and defconfig preimages are unchanged by this review.

At review completion, no new code had been compiled or exercised on a filesystem;
only this review and its companion inventory were new files. Subsequent local
implementation/build/model results are recorded separately above; no
performance/durability claim is made.
