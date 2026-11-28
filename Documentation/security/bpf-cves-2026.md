# BPF CVE backport audit: 64192, 68462, 98816 (2026)

This tree is nominally 4.14 but includes newer BPF, verifier and LSM backports.
Applicability below is based on the actual source, not the base kernel version.

## CVE-2026-64192 — fixed

BPF inode storage is present behind CONFIG_BPF_LSM. If the BPF LSM is not
initialized (for example, omitted from `lsm=`), its compiled `lbs_inode` size
is not converted to an offset by `security/security.c:prepare_lsm()` /
`lsm_set_blob_sizes()`. Using it as an offset can corrupt the inode security
blob, including its RCU callback.

Adapt upstream a6f0643e4f63cfaa0d5d4a69de4f132eac4b8fe4:

- Define `bpf_lsm_initialized` as `__ro_after_init`, initially false.
- Set it only after BPF security hooks are registered in `bpf_lsm_init()`.
- Reject inode-storage map allocation with `-EOPNOTSUPP` before any allocation
  or cache-index acquisition if the LSM has not initialized.
- Keep the existing allocation/error/cache management otherwise unchanged;
  this older local-storage API differs from current upstream.

This fixes the optional feature without enabling BPF_LSM in miatoll_defconfig.

## CVE-2026-68462 — vulnerable behavior already rejected

Upstream fd4cfa8c8f9a17cdec0539334d28754bc1d8a5d9 repairs the constant-offset
handling introduced by 022ac075088366b62e130da5e1b200bc93a47191. That newer
verifier permits constant nonzero `var_off`, but failed to check its signed
value when calculating the effective buffer access start.

This tree's `kernel/bpf/verifier.c:__check_buffer_access()` instead rejects:

```
if (off < 0)
        ... return -EACCES;
if (!tnum_is_const(reg->var_off) || reg->var_off.value)
        ... return -EACCES;
```

Thus a constant `var_off = -8` (or any nonzero value) cannot reach either
`check_tp_buffer_access()`'s `max_tp_access` update or
`check_buffer_access()`'s maximum-access update. Both callers invoke the
common check first. Their bookkeeping uses `off + size`, not an unsigned
negative `var_off` added to the end. The advisory's wrap-to-zero path is
absent. No verifier semantics are changed; importing the newer patch would
unnecessarily relax the existing zero-variable-offset restriction.

Regression tests exercise both callers, negative instruction offsets,
constant negative and positive variable offsets, nonconstant offsets,
unchanged access bounds after rejection, and valid zero-variable-offset
accesses. This is a finding for this specific CVE, not a general verifier
audit or claim that every possible buffer arithmetic issue is excluded.

## CVE-2026-98816 — fixed

Adapt upstream ad139384ecddb6f3e7e3c3c12765aafae0e39670:

- Use an `int` temporary while adjusting blinded backward jump offsets.
- Reject adjusted offsets below `S16_MIN` with `-ERANGE` for both JMP and
  JMP32 immediate conditional jumps, before emitting instructions.
- Propagate a negative blinding result through the existing clone-release
  error path, never passing it as a patch length.

Offsets -32768 and -32767 must fail instead of wrapping to forward jumps.
Offset -32766 remains valid after adjustment to -32768.

## Validation and limits

```
python3 tools/testing/selftests/bpf_upgrade/test_cves_2026.py
# optionally: --cc /usr/bin/clang
```

The host suite extracts the actual modified blinding functions, inode map
allocator and LSM initializer, plus the existing buffer-access functions.
It uses this tree's instruction-construction macros and BPF UAPI with
host-exported Linux types. Kernel allocation, hooks, program patching and
verifier context are mocked.

- Exhaustive signed-16-bit offsets for all 11 immediate jump conditions in
  both widths: **1,441,792 cases**, under UBSan.
- Blinding failure propagation, clone cleanup and existing patch failure.
- LSM-disabled rejection, LSM-enabled success, allocation-error propagation
  and no premature cache-index acquisition.
- Buffer-offset rejection and access-bound preservation described above.
- Six intentionally broken variants must fail: either jump-width check
  missing, missing negative-error propagation, missing inode guard,
  missing LSM initialization flag, or accepting nonzero buffer offsets.

The workflow runs this suite with its host Clang before the real ARM64
build. Local host success is not an ARM64 kernel compile, device test, RCU
stress test or proof of runtime exploit resistance. No BPF, storage,
compiler, crypto or filesystem configuration/default is changed.

## Official provenance

CVE records:

- https://github.com/CVEProject/cvelistV5/blob/main/cves/2026/64xxx/CVE-2026-64192.json
- https://github.com/CVEProject/cvelistV5/blob/main/cves/2026/68xxx/CVE-2026-68462.json
- https://github.com/CVEProject/cvelistV5/blob/main/cves/2026/98xxx/CVE-2026-98816.json

Upstream fixes used for comparison/backport:

- https://github.com/torvalds/linux/commit/a6f0643e4f63cfaa0d5d4a69de4f132eac4b8fe4
- https://github.com/torvalds/linux/commit/fd4cfa8c8f9a17cdec0539334d28754bc1d8a5d9
- https://github.com/torvalds/linux/commit/ad139384ecddb6f3e7e3c3c12765aafae0e39670
