# Selective F2FS A → B1 → B2 implementation

## Status

Implemented locally, following the approved staged review. **Both merge features
are opt-in and default off.** No fstab, device defconfig, on-disk feature,
formatting, ext4 root, publication, or CI settings were changed.

This is an adapted port, **not** the 73-file donor import. Seven source files
changed within the eight-file reviewed boundary; `gc.h` needed no change.
Existing GC inline-data/reference diagnostics, compression checkpoint locks,
atomic-file exclusions, and KSU/FinaSU/SUSFS/NoMount integration are retained.

The original inventory and exclusions remain in
[the pre-implementation review](../f2fs-staged-review.md). Exact upstream
identities, stage preimage/postimage hashes, patch hashes, configuration summaries,
and validation records are in `UPSTREAM.json` alongside this document.

## What each stage does

| Stage | Implementation | Default behavior |
| --- | --- | --- |
| A | Guard missing IPU selectors; account original rather than encrypted bounce pages before cached BIO publication; mark successful IPU writes submitted | Correctness fixes apply without enabling a feature |
| B1 | Optional foreground GC request coalescing through the existing GC worker; drain cached OPU and all IPU writes before waiting | Disabled unless `gc_merge` is requested |
| B2 | Optional plain `CP_SYNC` request batching through a dedicated checkpoint worker | Disabled unless `checkpoint_merge` is requested |

### A: publication and encrypted-page lifetime

Both the checkpoint-error caller and the IPU selector helper reject a missing
target. `(NULL, NULL)` is **not** a flush-all operation. The separate all-IPU
helper introduced in B1 is the only new flush-all interface.

`wbc_account_io()` and `WB_DATA_TYPE()` use the original page, before either a
new cached BIO or an appended page becomes visible to another submitter.
Accounting happens once, outside the full/detached-BIO retry loop. This avoids
both bounce-page lifetime misuse and completion preceding writeback accounting.

### B1: GC lifetime, draining and freeze

The request lock, generation and waitqueue live in `sbi`, not in the separately
allocated GC-thread structure. Stop closes admission and wakes waiters before
stopping/freeing that thread; a restart advances the generation rather than
reusing a transient wake condition. Offline, self-worker, paused/freezing-worker
and filesystem-freeze cases retain the original direct-GC fallback as applicable.

Admission is paused across the worker's freezer transition. An already accepted
request is either serviced before attempting a new freeze, or released before
the refrigerator; no caller can enqueue into that transition window.
`kthread_freezable_should_stop()` also allows stopping a frozen worker. A
foreground GC attempt bypasses background idle gating and does not overwrite
the background sleep interval.

The all-IPU helper detaches lists under their existing write locks and submits
outside those locks. The submit reference remains with the detached BIO; the
producer's extra reference stays valid until its subsequent selector/append
cleanup. A producer whose cached BIO was detached retries with a new BIO without
accounting the page twice. Cached OPU and IPU writes are drained before either
new GC or checkpoint waits, avoiding waits on IO retained by the waiting caller.

### B2: checkpoint ownership, errors and rollback

Only exact `CP_SYNC` requests enter the queue. Close/unmount, fastboot, discard,
recovery, resize and other checkpoint reasons retain their existing synchronous
paths. GC-worker and checkpoint-worker callers do not delegate checkpoints;
checkpoint-worker allocations likewise do not delegate back to the GC worker.

A per-superblock rwsem pins worker admission from queue publication through
completion. Stop takes it for write only after accepted requests finish. Queue
accounting precedes publication. Each detached request receives one result and
one completion; the iterator saves its next pointer before waking a caller whose
request lives on its stack. There is no request access after completion.

The checkpoint worker **never waits to acquire freezer protection or s_umount**:

1. Try internal-write protection using the existing local VFS helper.
2. Try an independent `s_umount` read lock in the worker itself.
3. Check `SB_UNFROZEN` while holding that lock.
4. Run the checkpoint with both protections, then release them before completion.

If a trylock or freeze check fails, the queued request is handed back for the
original caller to checkpoint synchronously, in its own lock context. This covers
the freezer/remounter holding `s_umount` for write and writer-priority denial
behind a normal syncfs reader. Journalled-quota checkpoints dispatched to the
worker therefore have the worker's own superblock protection; caller-owned locks
are not impersonated. Quota-enabled kernels are **not** blanket-excluded.
Actual checkpoint errors are returned to callers, not converted into retries or
success. The later upstream holder-tracking/VFS changes were not imported.

The worker uses fixed best-effort IO priority 3, with no writable sysfs priority
knob. Thread creation and priority-setting failures unwind the new worker.
Mount failure uses the existing cleanup chain, including `post_read_wq` teardown.
On remount, new checkpoint-worker allocation occurs before quota activation
changes; all later failure exits undo a newly started worker. Disabling an
existing worker is deferred until the existing fallible transitions succeed,
so a failed remount retains the previous worker and options.

## Options and observations

- `gc_merge` / `nogc_merge`: enable/disable GC merging. With background GC off
  or no GC worker available, callers retain direct GC.
- `checkpoint_merge` / `nocheckpoint_merge`: enable/disable plain-sync checkpoint
  batching. A read-only mount does not start a checkpoint worker.
- Both flags start clear on a fresh mount; explicit remount flags can toggle
  them. Their displayed mount options indicate requested policy, not proof that
  a worker is currently active.
- Where F2FS statistics are enabled, debug status reports `CP merge` counters:
  `queued` is outstanding queued requests, `issued` is worker checkpoint
  attempts/batches, `completed` is queue completions (including fallback handoff),
  and `fallback` is requests handed back for synchronous execution. These are
  independently sampled counters, **not** durable-checkpoint counts; a fallback
  caller may still be executing after its queue completion.

The supplied `/data` policy remains
`background_gc=on,flush_merge,mode=adaptive,inlinecrypt,fsync_mode=nobarrier`.
No merge feature was activated for it. Existing barrier/fsync policy and its
limitations are unchanged. Merely compiling these default-off features provides
no automatic performance gain; this work makes no throughput, latency, battery,
or durability improvement claim.

## Validation performed

- Separate A, B1 and B2 source patches replayed from the saved pre-port snapshot;
  each intermediate boundary passed its applicable extracted-source tests.
  Replay reproduced every saved final source byte exactly.
- IPU mock tests: missing selectors, invalid addresses, encrypted/plain pages,
  new/cached/detached/full BIO retries, accounting before immediate completion,
  all-temperature draining and stale-producer-reference cleanup.
- GC extracted admission/control tests: **800 requests per full run**, batching,
  spurious wakeups, stop/restart, self rejection, filesystem-freeze fallback,
  paused admission and late system-freezer/stop transitions.
- Checkpoint extracted worker/request/start/stop tests: **1,200 batched requests
  per full run**, checkpoint errors, concurrent stop, startup/priority failure,
  reason/self/GC bypass, and four quota/freeze/lock-contention fallback cases.
- Nine in-memory broken variants were rejected by runtime assertions/traps:
  null selector, missing accounting, bounce-page accounting, missing IPU drain,
  freezer admission window, missing queue accounting, missing superblock
  protection, missing worker-lifetime gate and discarded checkpoint errors.
- Full `fs/f2fs/` ARM64 object builds **and relocatable partial links** passed in
  four test configurations: device-derived baseline; encryption/verity/quota
  with ThinLTO and SCS; compression+cgroup-writeback+lockdep/checking/fault
  injection with ThinLTO and SCS; and quota/encryption/verity/statistics disabled.
- Existing filesystem backport models passed with undefined-behavior traps and
  assertions enabled. KSU, FinaSU, SUSFS and NoMount source/provenance/config
  checks passed. Hash comparison confirmed no unrelated existing file changed.
- Source whitespace checks passed. Checkpatch passed on the three source diffs
  with sign-off/commit-message checks disabled for these non-commit provenance
  diffs and the existing parser's `Opt_*` naming convention exempted.

Local compilation used **Clang/LLD 19.1.7 from Zig 0.14.1**, not GCC. A small
Python ELF-symbol reader supplied the VDSO symbol-offset preparation step.
Generated configurations alone disabled Polly and certificate/signature host
build dependencies; the repository's production configuration was not edited.
The device's compression-off policy is unchanged. The required production AOSP
`r614150` toolchain was **not** used for these local checks.

Re-run the host checks with Clang:

```sh
python3 tools/testing/selftests/fs_backport/test_f2fs_merge.py --cc clang
python3 tools/testing/selftests/fs_backport/test_f2fs_merge.py \
    --cc clang --negative cp-no-lifetime-gate
python3 tools/testing/selftests/fs_backport/test_backport.py \
    --cc 'clang -UNDEBUG -fsanitize=undefined -fsanitize-trap=all'
```

The new tests use pthreads and mocked kernel primitives, not a mounted filesystem.
They do **not** establish kernel SMP ordering, on-device lockdep, actual quota
IO, recovery after power loss, or filesystem durability. No complete image build,
new boot test, filesystem stress, performance benchmark, push or CI dispatch was
performed for this port. Production-toolchain image validation and recoverable
on-device testing remain necessary before separately deciding to activate it.

## Recoverable boundaries

`stage-a.diff`, `stage-b1.diff` and `stage-b2.diff` record only this port's source
changes, in that order, against the saved pre-port working tree—not a clean HEAD.
They are **already applied**. Do not apply them again or reset the repository to
undo this work: the starting tree contains other approved integrations. Their
preimage/postimage hashes in `UPSTREAM.json` allow checking the exact boundary;
any selective reversal must use matching files, in reverse stage order, while
preserving unrelated work. The original donor patches were not force-applied.
