# Original SUSFS upstream: 2.4.0 update review

## Source selection

User requested using the original simonpunk repository, rather than treating a
third-party non-GKI port as the primary upstream source:

- Repository: https://gitlab.com/simonpunk/susfs4ksu
- Reference branch: `gki-android12-5.10`
- Observed version-bump commit: `45a057536ddba12fd59fb583a8f5375f83be703e`
- Version announced by that commit: **2.4.0**.
- The release message identifies official KernelSU synchronization at
  `019a3c0103a8f8d56675546016c4073d0fd18352`, and manager32620+ due to UAPI
  changes. This is an upstream statement, not proof of our bridge compatibility.

References checked:

- https://gitlab.com/simonpunk/susfs4ksu/-/commit/45a057536ddba12fd59fb583a8f5375f83be703e
- https://gitlab.com/simonpunk/susfs4ksu/-/tree/gki-android12-5.10
- https://gitlab.com/simonpunk/susfs4ksu/-/tree/kernel-4.14

The original repository also has a `kernel-4.14` branch. Its observed tip was
`77905b5a071e6f3669e3b1814cea30147c0801da` (February2025). The existence of that
branch does not establish that it contains the current2.4.0 series.

**The 5.10 branch is an upstream/backport reference, not a ready-to-apply non-GKI
4.14 patch.** Its own compatibility documentation says patches can differ even
between kernels of the same version. No claim is made that upstream officially
recommends this branch as a drop-in for all non-GKI kernels.

## Historical pre-update Electro baseline

Before this approved update, Electro reported **SUSFS v2.3.0 / NON-GKI**. The existing32-file import and
corrected KSU bridge were adapted from:

- manipvlator/los_kernel_xiaomi_sm6150:
  `c931cae8ca19e4b738e3d9eda8fec4cdb7947473`;
- manipvlator/KernelSU bridge:
  `fcd50c8f367c470fa8e17eb64fbb8c7ce7527061`.

Those remain historical provenance records, not the authoritative original
2.4.0 source. Do not rewrite their import seals or pretend an original-upstream
update was already applied. The local backslashxx KSU v3.3.1-38 update does not
itself upgrade SUSFS.

## Review requirements used for the approved implementation

1. Obtain and hash the original pinned2.4.0 source/patch artifacts. The web
   release/README inspection alone is not a byte-verified source import.
2. Compare with the actual integrated2.3.0 source and all local corrections,
   not merely the visible version constant or a third-party port's commit list.
3. Review mount/kstat/open-redirect restructuring, lifecycle/RCU/locking and
   SELinux changes against Electro4.14 and the Phoenix syscall-helper series.
4. Adapt the official-KSU bridge to **retained backslashxx KSU**, preserving
   authorization, manager certificate binding/FinaSU, NoMount and native/compat
   hooks. Do not apply the official sucompat/manual-hook patch blindly or
   replace the fork/hook strategy.
5. Review the new priority-UID-filter command/configuration separately. Do not
   silently enable a new feature under the old approved feature defaults.
6. Check kernel/userspace command layouts and tool/module compatibility; the
   numeric KSU version alone does not prove UAPI or runtime compatibility.
7. Keep immutable historical evidence and add explicit source/hash successors,
   regression controls, pinned-AOSP build evidence and device-validation limits.

## Status

The user subsequently approved the backport. The local tree now reports
**v2.4.0 / NON-GKI**, adapted from the byte-verified original commit above while
retaining backslashxx KSU, FinaSU/NoMount and the existing feature defaults.
The generic priority-UID filter Kconfig default remains n; the user subsequently
approved enabling it in the miatoll production defconfig. The initial backport
validation receipt predates that opt-in and does not validate an enabled build.

See [the implementation/adaptation map](backport-2.4.0.md), the new closed
20-source successor `backport-2.4.0.{json,diff}`, and
`backport-2.4.0-validation.json` for validation and its limits. The original
2.3.0 import seals remain historical, immutable evidence. No push or CI dispatch
is part of this approved local update.
