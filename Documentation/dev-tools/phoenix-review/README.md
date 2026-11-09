# Phoenix commit-review ledger

Structured source of truth: [`ledger.json`](ledger.json).

## Recording rules

- **Permanent IDs:** `PHX-001`, `PHX-002`, etc. Never renumber old entries.
- **Batches:** `PHX-B001`, `PHX-B002`, etc.; preserve original submission order.
- **Deduplicate using the full donor SHA.** A repeated link refers to its existing ID.
- **Exclude work already implemented during qcom_sm8150 or other approved integrations**, including equivalent backports with different SHAs. No new entry or ID for excluded duplicates; inspect partial matches rather than trusting titles.
- Keep **recommendation → explicit user decision → implementation → validation → publication** separate.
- “Recommended skip” is **not** an approved skip. “Candidate” is **not** permission to apply.
- Before implementing an old review, recheck it against current Electro. Keep the old baseline/findings and append a dated reassessment.
- Update both this summary and the structured ledger as new batches/decisions arrive.

## Current checkpoint

- Last updated: **2026-10-13**.
- Reviewed Electro baseline: [`c6de0ddbe7e159a84c4906cbbf4f2c9138521c13`](https://github.com/lezyss/Kernel_electro/commit/c6de0ddbe7e159a84c4906cbbf4f2c9138521c13).
- Branch: `arena/e63a046d-kernel-electro`; target: ARM64 miatoll / Electro 4.14.
- **150 reviewed; 132 approved for adapted implementation; 18 skip/equivalent items excluded (no new skip decisions).**
- **132 integrated locally (including documented organizational/prototype subsets); 0 approved source items queued. Full miatoll build PASS;132 approved scopes published; device validation pending.**
- **User-submitted series complete through final batch PHX-B019.** This closes source review of the supplied links, not implementation or exhaustive Phoenix history review.
- Earlier history-page browsing is **not** a completed review of the whole date range.
- Existing checkpoint includes published manual-only CI, selectable/non-default BBRv3, and KSU ADBROOT=y. BBRplus stays default; ADB-root runtime toggle stays off initially. The profile now builds with the complete miatoll image; ADB-root runtime remains device-untested.
- Two pre-existing BPF runtime-test/manifest corrections remain local and outside this review/publication scope; see JSON for exact paths.

## PHX-B001 — first ten individually submitted commits

Every recommendation below is still **awaiting user decision**. Nothing was applied to Electro.

| Stable ID | Donor | Subject | Recommendation |
| --- | --- | --- | --- |
| PHX-001 | [`54ca6dd70`](https://github.com/PhoenixKernel/linux/commit/54ca6dd70e526001f2aab1364a4203ca9d2e77d2) | signal: replace sigset_to_compat() with put_compat_sigset() | Optional cleanup |
| PHX-002 | [`eab1bae8b`](https://github.com/PhoenixKernel/linux/commit/eab1bae8b35431556325e66ffe5f7e3bc125dbf2) | signal: simplify compat_sigpending() | Optional cleanup |
| PHX-003 | [`dfbd010eb`](https://github.com/PhoenixKernel/linux/commit/dfbd010ebd7ee5d94b23401792f0b4d1ea9d4b77) | signal: lift sigset size check out of do_sigpending() | Optional cleanup |
| PHX-004 | [`6737b678b`](https://github.com/PhoenixKernel/linux/commit/6737b678b5e03bf05925cbe4eabe1c61820b8e00) | get_compat_sigset() | Optional; adapt carefully |
| PHX-005 | [`ca7909051`](https://github.com/PhoenixKernel/linux/commit/ca7909051034025310156df24edc56cbe3e3b147) | parisc: switch to {get,put}_compat_sigset() | Recommend skip: other architecture |
| PHX-006 | [`89fb00af6`](https://github.com/PhoenixKernel/linux/commit/89fb00af615a2bd3c8d89992f83b6f65d561c315) | ppc: switch to {get,put}_compat_sigset() | Recommend skip: other architecture |
| PHX-007 | [`798bc1734`](https://github.com/PhoenixKernel/linux/commit/798bc1734bf35923dd14d87521329c44877c1a62) | s390: switch to {get,put}_compat_sigset() | Recommend skip: other architecture |
| PHX-008 | [`d8cdb00bb`](https://github.com/PhoenixKernel/linux/commit/d8cdb00bb77f1d2c4d383e0ce51de17671b1e8ff) | sparc: switch to {get,put}_compat_sigset() | Recommend skip: other architecture |
| PHX-009 | [`dda469bff`](https://github.com/PhoenixKernel/linux/commit/dda469bffa4816d0d4744957aef06be8364e082e) | mips: switch to {get,put}_compat_sigset() | Recommend skip: other architecture |
| PHX-010 | [`f820bcf9e`](https://github.com/PhoenixKernel/linux/commit/f820bcf9e142ae361ee5f3c8a931424846c83b07) | sched_rr_get_interval(): move compat to native, get rid of set_fs() | **First correctness candidate** |

### Detailed findings and evidence

Apply checks below establish text compatibility only. No donor target builds,
device tests, network tests or performance tests were run. All review-time
applications/adaptations used temporary copies, not production source.

### PHX-001 — `54ca6dd70e526001f2aab1364a4203ca9d2e77d2`

- **Changes:** Replace output conversion plus separate user copy with put_compat_sigset(); handle big-endian conversion in the shared helper and direct copying on little-endian systems.
- **Electro finding:** Electro still has sigset_to_compat and its old generic/SPARC call sites. Not already implemented in this form. Optional compatibility maintenance, not a demonstrated performance fix.
- **Check:** PASS: unmodified patch in a temporary source copy at the reviewed Electro baseline.
- **Reviewed order/helper prerequisites:** Independent candidate in this batch. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-002 — `eab1bae8b35431556325e66ffe5f7e3bc125dbf2`

- **Changes:** Use an endian-independent legacy compat sigpending implementation instead of invoking native sys_rt_sigpending on little-endian systems.
- **Electro finding:** Electro retains the endian split and little-endian internal syscall call. Not already implemented in this form.
- **Check:** PASS: unmodified patch in a temporary copy after PHX-001.
- **Reviewed order/helper prerequisites:** PHX-001. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-003 — `dfbd010ebd7ee5d94b23401792f0b4d1ea9d4b77`

- **Changes:** Move sigset-size checks to native/compat syscall wrappers and type do_sigpending() as taking sigset_t *.
- **Electro finding:** Electro retains size validation inside do_sigpending(void *, unsigned long). Not already implemented in this form.
- **Check:** PASS: unmodified patch in a temporary copy after PHX-001 and PHX-002.
- **Reviewed order/helper prerequisites:** PHX-001, PHX-002. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-004 — `6737b678b5e03bf05925cbe4eabe1c61820b8e00`

- **Changes:** Replace sigset_from_compat with get_compat_sigset, including its GPL export, and migrate signal, epoll, select/poll, signalfd, KVM and SPARC syscall users.
- **Electro finding:** Electro still uses sigset_from_compat in the affected paths. The unmodified patch fails in fs/select.c because existing pselect/ppoll code already uses timespec64. Preserve those time conversions and existing epoll fixes, migrate all users, and audit module users of the renamed export.
- **Check:** FAIL unmodified after PHX-001..003: fs/select.c:1310. Scratch-only adaptation applied the other files, removed two ss32 temporaries, and replaced two copy/convert sequences in select.c while preserving existing timespec64 declarations. No old helper names remained in affected files. Not compiled.
- **Reviewed order/helper prerequisites:** PHX-001. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-005 — `ca7909051034025310156df24edc56cbe3e3b147`

- **Changes:** Migrate PA-RISC signal-frame conversion to the shared helpers and remove local conversion routines.
- **Electro finding:** Only arch/parisc files change; no runtime benefit for this ARM64 miatoll target. Not a prerequisite for the generic helper migration on ARM64.
- **Check:** Textual scratch-sequence check passed, but PHX-004 had failed in that experiment. This is NOT a standalone/buildable-series validation and is not evidence for accepting the patch.
- **Reviewed order/helper prerequisites:** PHX-001, PHX-004. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-006 — `89fb00af615a2bd3c8d89992f83b6f65d561c315`

- **Changes:** Migrate PowerPC compat signal-set wrappers to the shared helpers.
- **Electro finding:** Only arch/powerpc code changes; no runtime benefit for this ARM64 miatoll target. Not a prerequisite for the generic helper migration on ARM64.
- **Check:** Textual scratch-sequence check passed, but PHX-004 had failed in that experiment. This is NOT a standalone/buildable-series validation and is not evidence for accepting the patch.
- **Reviewed order/helper prerequisites:** PHX-001, PHX-004. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-007 — `798bc1734bf35923dd14d87521329c44877c1a62`

- **Changes:** Migrate s390 compat signal frames to the shared helpers; also changes the saved sc.sregs pointer assignment.
- **Electro finding:** Only arch/s390 code changes; no runtime benefit for this ARM64 miatoll target. Old sc.sregs uses &frame->sregs; replacement uses &frame->sc. This is not merely a helper substitution and warrants a separate s390 ABI audit, not an unqualified correctness claim.
- **Check:** Textual scratch-sequence check passed, but PHX-004 had failed in that experiment. This is NOT a standalone/buildable-series validation and is not evidence for accepting the patch.
- **Reviewed order/helper prerequisites:** PHX-001, PHX-004. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-008 — `d8cdb00bb77f1d2c4d383e0ce51de17671b1e8ff`

- **Changes:** Migrate SPARC real-time compat signal-frame save/restore to the shared helpers.
- **Electro finding:** Only arch/sparc signal-frame code changes; no runtime benefit for this ARM64 miatoll target. Distinct from SPARC syscall callers migrated inside PHX-001/PHX-004.
- **Check:** Textual scratch-sequence check passed, but PHX-004 had failed in that experiment. This is NOT a standalone/buildable-series validation and is not evidence for accepting the patch.
- **Reviewed order/helper prerequisites:** PHX-001, PHX-004. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-009 — `dda469bffa4816d0d4744957aef06be8364e082e`

- **Changes:** Migrate MIPS compat signal-set copy helpers; replace constant runtime BUG_ON checks with BUILD_BUG_ON checks.
- **Electro finding:** Only arch/mips code changes; no runtime benefit for this ARM64 miatoll target. Not a prerequisite for the generic helper migration on ARM64.
- **Check:** Textual scratch-sequence check passed, but PHX-004 had failed in that experiment. This is NOT a standalone/buildable-series validation and is not evidence for accepting the patch.
- **Reviewed order/helper prerequisites:** PHX-001, PHX-004. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

### PHX-010 — `f820bcf9e142ae361ee5f3c8a931424846c83b07`

- **Changes:** Share a timespec64 kernel helper between native/compat sched_rr_get_interval wrappers; remove compat set_fs(KERNEL_DS), internal syscall call, and copyout on failure.
- **Electro finding:** Confirmed in Electro: the compat wrapper declares uninitialized struct timespec t, invokes the native syscall, then calls compat_put_timespec regardless of ret. Native negative-PID/not-found/security error paths can return before populating t. The donor copies out only on success. Required put_timespec64, compat_put_timespec64 and jiffies_to_timespec64 helpers exist. This is a correctness/hardening candidate, not scheduler tuning; no device exploit or CVE claim.
- **Check:** PASS: independent unmodified git apply --check against the actual Electro working tree. No production application, target compilation, device or performance testing.
- **Reviewed order/helper prerequisites:** Independent candidate in this batch. This is not a complete upstream dependency analysis.
- **Decision/application:** pending / not applied.

## PHX-B002 — next eleven submitted commits

Same Electro baseline as PHX-B001. All findings below are source-level review,
not build/runtime/performance proof. **All decisions remain pending; none applied.**
The final five commits are all x86-only, not just the final link. They do not
implement the ARM64 kernel's AArch32 compatibility ABI.

| Stable ID | Donor | Subject | Recommendation |
| --- | --- | --- | --- |
| PHX-011 | [`bc742667b`](https://github.com/PhoenixKernel/linux/commit/bc742667b7e5a5812676b22913ee025aed602d77) | kill iov_shorten() | Optional dead-code cleanup |
| PHX-012 | [`33bcd59cb`](https://github.com/PhoenixKernel/linux/commit/33bcd59cb608a60be2661402fffec02a91a17957) | fs: expose do_unlinkat for built-in callers | Consider **PHX-012 + PHX-013** together |
| PHX-013 | [`5531360f9`](https://github.com/PhoenixKernel/linux/commit/5531360f9ff7dfd2a9c221e12598bd1deb17be9c) | coredump: call do_unlinkat directly instead of sys_unlink | Consider **PHX-012 + PHX-013** together |
| PHX-014 | [`037634de8`](https://github.com/PhoenixKernel/linux/commit/037634de87d23413fef62c0866d3519097711324) | eventfd: convert to use anon_inode_getfd() | Optional eventfd cleanup |
| PHX-015 | [`c82b2d408`](https://github.com/PhoenixKernel/linux/commit/c82b2d40836cf635783012efee9f019f3747f902) | eventfd: fold eventfd_ctx_read() into eventfd_read() | Optional eventfd cleanup |
| PHX-016 | [`e05dd364f`](https://github.com/PhoenixKernel/linux/commit/e05dd364f9344ca30fe7d6819a463380e66b4aba) | eventfd: fold eventfd_ctx_get() into eventfd_ctx_fileget() | Optional eventfd cleanup |
| PHX-017 | [`6e35d7329`](https://github.com/PhoenixKernel/linux/commit/6e35d7329df41a298ec62a79f4deaff2942ac60a) | x86/syscalls/32: Simplify $entry == $compat entries | Recommend skip: x86-only |
| PHX-018 | [`e2a6cc6a2`](https://github.com/PhoenixKernel/linux/commit/e2a6cc6a27eec764a58558a044ea6c07c4709694) | x86/entry: Remove stale syscall prototype | Recommend skip: x86-only |
| PHX-019 | [`cd2a34165`](https://github.com/PhoenixKernel/linux/commit/cd2a3416582393554da6eed2e27629f637d8b9af) | x86/syscalls: Use proper syscall definition for sys_ioperm() | Recommend skip: x86-only |
| PHX-020 | [`da5767e8e`](https://github.com/PhoenixKernel/linux/commit/da5767e8e142655be1b11ce9940c4266cf4f1ec4) | x86/syscalls: Use COMPAT_SYSCALL_DEFINEx() macros for x86-only compat syscalls | Recommend skip: x86-only |
| PHX-021 | [`c0d53bd3b`](https://github.com/PhoenixKernel/linux/commit/c0d53bd3b6ab4e843580eef3c152619834ea6045) | x86/entry: Do not special-case clone(2) in compat entry | Recommend skip: x86-only |

### Batch conclusions

- **PHX-012 + PHX-013:** concrete removal of a coredump address-limit override;
  no demonstrated phone performance improvement or exploit claim. PHX-012
  changes SUSFS-sealed `fs/namei.c`, so an approved implementation must add a
  reviewed narrow provenance chain, not rewrite the immutable SUSFS manifest.
- **PHX-011/014/015/016:** mostly internal/dead-code cleanup. Source searches
  support the donors' in-tree caller claims, but cannot establish binary or
  external-module ABI compatibility for removed exports. PHX-014 also changes
  validation/allocation ordering under failure/resource pressure.
- **PHX-017..021:** recommend skip for ARM64. User's tentative x86 question is
  not recorded as final approval. Do not confuse x86 compat clone with our
  already-integrated generic clone3/pidfd work.
- PHX-010 from the first batch remains the stronger correctness candidate.

### Detailed findings and evidence

### PHX-011 — `bc742667b7e5a5812676b22913ee025aed602d77`

- **Changes:** Remove the unused iov_shorten implementation, its declaration and EXPORT_SYMBOL.
- **Electro finding:** Present but no in-tree source callers found: whole-workspace C/header/assembly search finds only declaration, definition and export. Optional dead-code cleanup, not an I/O algorithm upgrade. Removing an exported symbol can affect unreviewed binary or out-of-tree modules; these were not audited.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Before implementation:** Audit out-of-tree/binary module symbol requirements before export removal; ordinary target-build coverage still required.
- **Decision/application:** pending / not applied.

### PHX-012 — `33bcd59cb608a60be2661402fffec02a91a17957`

- **Changes:** Expose do_unlinkat to built-in fs callers using struct filename * instead of a userspace pathname; move getname to syscall wrappers and retain the filename until ESTALE retry completes.
- **Electro finding:** The old static user-pointer interface remains in Electro. The patch applies textually. filename_parentat already accepts struct filename *, propagates error pointers and releases the name on lookup failure; successful ESTALE retries must keep the name alive. Security-path checks, vfs_unlink2 and SUSFS hook counts are retained in scratch replay. fs/namei.c is sealed by immutable SUSFS provenance; accepting this requires a reviewed narrow overlay/chain and updated checks, not rewriting the original SUSFS manifest.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Before implementation:** If approved, adopt together with PHX-013 for a concrete built-in caller. Add a narrow reviewed SUSFS provenance overlay retaining the original fs/namei.c seal and preimage chain. Validate error-pointer ownership, ESTALE/delegation retries, security/SUSFS behavior and user unlink ABI.
- **Decision/application:** pending / not applied.

### PHX-013 — `5531360f9ff7dfd2a9c221e12598bd1deb17be9c`

- **Changes:** Use do_unlinkat(AT_FDCWD, getname_kernel(cn.corename)) for coredump cleanup instead of an internal sys_unlink call wrapped in set_fs(KERNEL_DS).
- **Electro finding:** Electro still calls sys_unlink under an address-limit override in the non-SUID-safe coredump branch. internal.h is already included. This is useful removal of an internal syscall/address-limit override, not a demonstrated exploit fix or phone performance improvement. Only the kernel-generated core-file path is affected; need_suid_safe guards remain. PHX-012 is a semantic/compilation prerequisite even though this one-file patch passes text application alone.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation. Semantic prerequisite PHX-012 remains mandatory despite independent text success.
- **Before implementation:** Requires PHX-012 before implementation; a successful one-file apply check is not compilation proof. Validate normal core-file replacement, failed lookup/unlink and unchanged SUID-safe policy; no device tests have run.
- **Decision/application:** pending / not applied.

### PHX-014 — `037634de87d23413fef62c0866d3519097711324`

- **Changes:** Fold eventfd_file_create into eventfd2 and use anon_inode_getfd; remove the old non-exported helper/declarations/stub.
- **Electro finding:** Only eventfd2 calls eventfd_file_create in the searched source; it is not an exported symbol. Existing anon_inode_getfd reserves/releases the fd, creates the file, then installs it, with no later failure point; the new failure branch frees ctx. Preserve semaphore/nonblock/cloexec handling. Allocation/validation order changes: the old code reserves an fd before flag validation/context allocation, while the donor validates/allocates first. Failure precedence/resource-pressure behavior should not be advertised as strictly identical.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Before implementation:** Test flags/count, EFD_SEMAPHORE, CLOEXEC/nonblocking, fd exhaustion/allocation failure and cleanup ownership. Keep allocator/error-precedence differences explicit; no speed claim.
- **Decision/application:** pending / not applied.

### PHX-015 — `c82b2d40836cf635783012efee9f019f3747f902`

- **Changes:** Fold the exported eventfd_ctx_read into the VFS eventfd_read implementation, preserving blocking/nonblocking/counter flow with success now represented by an 8-byte result.
- **Electro finding:** eventfd_ctx_read is exported but only called by eventfd_read in the searched source. Source flow preserves counter extraction, wait/signal handling, writable wakeup and consumption before possible copyout EFAULT; it does not introduce a new eventfd feature. Externally built/binary callers were not audited. Optional internal/API cleanup requiring counter/semaphore/nonblocking/signal/fault regression tests if adopted.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Before implementation:** Audit external/binary users of eventfd_ctx_read before removing the GPL export. Test counter/semaphore reads, blocking/signal interruption, EAGAIN/EFAULT and poll wakeups.
- **Decision/application:** pending / not applied.

### PHX-016 — `e05dd364f9344ca30fe7d6819a463380e66b4aba`

- **Changes:** Fold exported eventfd_ctx_get into eventfd_ctx_fileget and perform kref_get there; move the eventfd_ctx forward declaration outside CONFIG_EVENTFD.
- **Electro finding:** eventfd_ctx_get is exported but only used by eventfd_ctx_fileget in the searched source. Inline kref_get after the existing f_op check preserves the inspected refcount flow. The standalone donor patch fails header context; PHX-014 then PHX-016 applies without PHX-015, so PHX-015 is not a demonstrated prerequisite. Export removal still requires an external-module ABI audit.
- **Check:** FAIL independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation. Additional scratch replay PHX-014 -> PHX-016 PASS without PHX-015.
- **Independent conflict:** error: patch failed: include/linux/eventfd.h:26; error: include/linux/eventfd.h: patch does not apply
- **Before implementation:** Use PHX-014 first for donor header context or adapt that hunk deliberately; PHX-015 is not required by the tested two-patch replay. Audit external/binary users before removing eventfd_ctx_get export; test refcount/lifetime behavior.
- **Decision/application:** pending / not applied.

### PHX-017 — `6e35d7329df41a298ec62a79f4deaff2942ac60a`

- **Changes:** Drop redundant compat entries identical to native entries for x86 fork, sigsuspend and vfork.
- **Electro finding:** All changed paths are under arch/x86. The old duplicated table entries remain, but this does not affect ARM64 or its AArch32 compat ABI. No dependency from the generic PHX-011..016 changes on this x86-only cleanup was found.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Before implementation:** No implementation needed for ARM64; revisit only if the user requests an x86 maintenance scope.
- **Decision/application:** pending / not applied.

### PHX-018 — `e2a6cc6a27eec764a58558a044ea6c07c4709694`

- **Changes:** Remove a stale declaration of sys32_vm86_warning from the x86 ia32 syscall header.
- **Electro finding:** Only arch/x86/include/asm/sys_ia32.h changes. The stale declaration remains; no ARM64-phone effect. Text application success is not a reason to include it in an ARM64-focused backport.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Before implementation:** No implementation needed for ARM64; revisit only if the user requests an x86 maintenance scope.
- **Decision/application:** pending / not applied.

### PHX-019 — `cd2a3416582393554da6eed2e27629f637d8b9af`

- **Changes:** Define x86 ioperm using SYSCALL_DEFINE3 instead of a hand-written syscall function declaration.
- **Electro finding:** Only arch/x86/kernel/ioport.c changes. The old declaration remains; x86 I/O-port syscall metadata cleanup has no ARM64-phone effect.
- **Check:** PASS independent text apply; PASS text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Before implementation:** No implementation needed for ARM64; revisit only if the user requests an x86 maintenance scope.
- **Decision/application:** pending / not applied.

### PHX-020 — `da5767e8e142655be1b11ce9940c4266cf4f1ec4`

- **Changes:** Convert x86-only compat syscall entry points to COMPAT_SYSCALL_DEFINEx and update their table/header names.
- **Electro finding:** All changes are under arch/x86. Not already converted in this form. Full patch fails on current Electro, and still fails in sys_ia32.c after preceding submitted patches: Electro already delegates sys32_ftruncate64 to ksys_ftruncate, whereas donor context expects sys_ftruncate. Do not regress that existing helper conversion if x86 is ever maintained separately. No reason to adapt this for miatoll.
- **Check:** FAIL independent text apply; FAIL text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Independent conflict:** error: patch failed: arch/x86/entry/syscalls/syscall_32.tbl:199; error: arch/x86/entry/syscalls/syscall_32.tbl: patch does not apply; error: patch failed: arch/x86/ia32/sys_ia32.c:51; error: arch/x86/ia32/sys_ia32.c: patch does not apply; error: patch failed: arch/x86/include/asm/sys_ia32.h:20; error: arch/x86/include/asm/sys_ia32.h: patch does not apply
- **Sequence conflict:** error: patch failed: arch/x86/ia32/sys_ia32.c:51; error: arch/x86/ia32/sys_ia32.c: patch does not apply
- **Before implementation:** No implementation needed for ARM64; revisit only if the user requests an x86 maintenance scope.
- **Decision/application:** pending / not applied.

### PHX-021 — `c0d53bd3b6ab4e843580eef3c152619834ea6045`

- **Changes:** Replace x86 compat clone assembly argument-swapping stub with a COMPAT_SYSCALL_DEFINE5 wrapper and update the x86 syscall table/header.
- **Electro finding:** All changes are under arch/x86. Old stub32_clone still exists. The patch fails standalone context and after the submitted sequence because PHX-020 did not apply. Requires the preceding x86 compat-wrapper conversion or adaptation for its expected context. This is legacy x86 clone ABI plumbing, not ARM64 clone3 support; it does not replace our existing generic clone3/pidfd backports.
- **Check:** FAIL independent text apply; FAIL text apply after preceding successful submitted patches; reverse apply FAIL. No production application or target compilation.
- **Independent conflict:** error: patch failed: arch/x86/include/asm/sys_ia32.h:55; error: arch/x86/include/asm/sys_ia32.h: patch does not apply
- **Sequence conflict:** error: patch failed: arch/x86/include/asm/sys_ia32.h:55; error: arch/x86/include/asm/sys_ia32.h: patch does not apply
- **Before implementation:** No implementation needed for ARM64; revisit only if the user requests an x86 maintenance scope.
- **Decision/application:** pending / not applied.

## PHX-B003 — seven more submitted commits

Compared with the published `c6de0ddbe` source revision. Restored local Git
metadata was older; every touched/supporting source file was byte-verified
against the published revision rather than assuming `HEAD` represented the
working files. No source edits or branch/index alignment were needed.

**All decisions pending; none applied.** No target builds/device/performance tests.

| Stable ID | Donor | Subject | Recommendation |
| --- | --- | --- | --- |
| PHX-022 | [`fa4df3c3a`](https://github.com/PhoenixKernel/linux/commit/fa4df3c3a73c1c8a957b8f7c0ccc65bb44ae3ea6) | syscalls: define and explain goal to not call syscalls in the kernel | Optional docs only |
| PHX-023 | [`6b6a41d52`](https://github.com/PhoenixKernel/linux/commit/6b6a41d52434f76726b7ded2d6dc72e650066fa3) | kernel: use kernel_wait4() instead of sys_wait4() | Relevant optional cleanup |
| PHX-024 | [`a4a78ce04`](https://github.com/PhoenixKernel/linux/commit/a4a78ce0485f9f773ccb6debe6f578b1a155c75e) | kernel: open-code sys_rt_sigpending() in sys_sigpending() | Optional; requires PHX-003 |
| PHX-025 | [`49b527808`](https://github.com/PhoenixKernel/linux/commit/49b527808371ada059c972ac1761e45549b6ce06) | kexec: call do_kexec_load() in compat syscall directly | Defer: KEXEC scope/validation |
| PHX-026 | [`75082f61b`](https://github.com/PhoenixKernel/linux/commit/75082f61b1517f7909c508f5e5ff60704c109db7) | mm: use do_futex() instead of sys_futex() in mm_release() | Relevant optional cleanup; preserve BPF chain |
| PHX-027 | [`d568ed463`](https://github.com/PhoenixKernel/linux/commit/d568ed4635697d3c1014119ecafc717caa6023e0) | x86: use _do_fork() in compat_sys_x86_clone() | Recommend skip: x86-only |
| PHX-028 | [`67da86f11`](https://github.com/PhoenixKernel/linux/commit/67da86f11e7bb8663400972707088e91d9457dcb) | x86: remove compat_sys_x86_waitpid() | Recommend skip: x86-only |

### Batch conclusions

- **PHX-023 / PHX-026** are relevant optional internal-helper cleanups, not
  demonstrated speed improvements. Keep PID_NS off; do not alter clone3/pidfd.
- **PHX-024** demonstrates why text-apply success is not compile proof: it calls
  a one-argument helper that current Electro still defines with two arguments.
  PHX-003 and its reviewed signal-series context must be considered first.
- **PHX-025** is deferred: KEXEC is not selected by the phone defconfig. Its
  compat path also stops inheriting native exact-architecture validation.
  CAP_SYS_BOOT is still checked; this is not a demonstrated privilege bypass.
- **PHX-026** touches BPF-sealed `kernel/fork.c`; any approved implementation
  must preserve the immutable historical preimage chain through a narrow overlay.
- **PHX-027 / PHX-028** are x86-only. PHX-027 additionally uses an obsolete
  six-argument `_do_fork` API, incompatible with current `kernel_clone_args *`.
- Prior **PHX-010** remains the stronger correctness candidate across batches.

### Detailed findings and evidence

### PHX-022 — `fa4df3c3a73c1c8a957b8f7c0ccc65bb44ae3ea6`

- **Changes:** Add developer documentation and a header comment explaining that internal kernel users should call helpers rather than syscall entry points.
- **Electro finding:** Documentation/comments only: no executable behavior, syscall wrapper implementation, new feature or hard requirement imported into ARM64 4.14. Header hunk fails because Electro already has do_sys_ftruncate/ksys_ftruncate declarations before the final #endif; relocate only the comment if desired, preserving the existing helper. Optional docs, not an optimization.
- **Check:** FAIL independent text apply; FAIL text apply after preceding successful patches in this submitted batch; reverse apply FAIL. No production application or target compilation.
- **Independent conflict:** error: patch failed: include/linux/syscalls.h:952; error: include/linux/syscalls.h: patch does not apply
- **Before implementation:** Optional documentation only; adapt comment placement without deleting existing ksys_ftruncate helpers.
- **Decision/application:** pending / not applied.

### PHX-023 — `6b6a41d52434f76726b7ded2d6dc72e650066fa3`

- **Changes:** Replace internal sys_wait4 calls with existing kernel_wait4 in legacy waitpid, PID-namespace teardown and synchronous usermode-helper waiting.
- **Electro finding:** All three old call sites are present; kernel_wait4 implementation/prototype and sched/task.h includes already exist. ru is NULL at these calls, so the removed native wrapper adds no rusage copyout here. Phone-relevant UMH path remains, but PID_NS is explicitly disabled and must not be enabled merely for this patch. kernel_wait4 still takes int __user *status; the kernel-thread UMH status cast/address-space assumption remains. This is not removal of every userspace pointer or set_fs dependency.
- **Check:** PASS independent text apply; PASS text apply after preceding successful patches in this submitted batch; reverse apply FAIL. No production application or target compilation. Comment-aware scratch source guard confirms no sys_wait4 calls in touched paths; UMH __user cast remains.
- **Before implementation:** If approved, test synchronous UMH exit-status/error behavior and wait paths; retain the existing kernel-thread address-space assumption unless separately redesigned. Do not enable PID_NS; no target or device testing performed.
- **Decision/application:** pending / not applied.

### PHX-024 — `a4a78ce0485f9f773ccb6debe6f578b1a155c75e`

- **Changes:** Implement legacy native sys_sigpending with do_sigpending and copy_to_user instead of invoking sys_rt_sigpending; rename its formal output parameter in the prototype.
- **Electro finding:** Electro still has the internal sys_rt_sigpending call, but do_sigpending currently takes TWO arguments. Donor calls it with ONE, requiring PHX-003 (reviewed with PHX-001/002 beforehand). Text application alone would hide a compilation error. The added sizeof(old_sigset_t) > sizeof(*uset) guard compares the same type and is always false; do not treat it as new runtime validation. ARM64 AArch32 syscall 73 uses compat_sys_sigpending, which this patch does not modify; no direct compat-path improvement from this change alone.
- **Check:** PASS independent text apply; PASS text apply after preceding successful patches in this submitted batch; reverse apply FAIL. No production application or target compilation. Scratch replay PHX-001 -> PHX-002 -> PHX-003 -> PHX-024 PASS, with one-argument helper/calls checked; not compiled.
- **Before implementation:** Implement only as part of an explicitly approved signal-helper series; PHX-003 is a semantic/compilation prerequisite. Retest legacy/native/compat signal-mask sizes and EFAULT behavior; do not advertise the tautological size check as hardening.
- **Decision/application:** pending / not applied.

### PHX-025 — `49b527808371ada059c972ac1761e45549b6ce06`

- **Changes:** Share kexec capability/disabled/flags/segment-count validation and invoke do_kexec_load directly from the compat wrapper under kexec_mutex.
- **Electro finding:** Current compat wrapper still calls sys_kexec_load. Shared permission/disabled/flags/count checks and mutex handling are retained, but parameter behavior is NOT identical: compat now rejects KEXEC_ARCH_DEFAULT yet no longer reaches the native exact-architecture equality check formerly imposed through sys_kexec_load. This needs separate enabled-profile review, not a claim of privilege bypass (CAP_SYS_BOOT remains checked). Miatoll defconfig does not select KEXEC, and ARM64 KEXEC has no default y; no resolved configuration/target build performed. Defer for current phone scope and do not enable KEXEC.
- **Check:** PASS independent text apply; PASS text apply after preceding successful patches in this submitted batch; reverse apply FAIL. No production application or target compilation. Scratch inspection confirms compat uses shared checks/direct helper but does not retain native exact-architecture equality validation.
- **Before implementation:** Defer while KEXEC is not selected; enabling it is separate unapproved scope. If revisited, audit compat architecture-validation differences, permissions, flags, segment copyin/failure handling and locking; text-apply success is insufficient.
- **Decision/application:** pending / not applied.

### PHX-026 — `75082f61b1517f7909c508f5e5ff60704c109db7`

- **Changes:** Use do_futex directly for the clear_child_tid FUTEX_WAKE in mm_release; remove the redundant unconditional declaration and add a !CONFIG_FUTEX stub while retaining the enabled declaration.
- **Electro finding:** Electro still uses sys_futex for clear_child_tid wakeup. With FUTEX_WAKE and NULL timeout, the syscall wrapper forwards timeout=NULL, val2=0 and val3=0, matching the proposed do_futex call; shared/non-private wake semantics and wake count 1 remain. Actual header already has a second declaration inside CONFIG_FUTEX, so removing the unconditional duplicate plus adding the disabled stub is coherent. This is relevant thread-exit maintenance, not a futex algorithm or measured speed upgrade. kernel/fork.c matches the historical BPF sealed postimage: approved implementation needs a narrow provenance overlay/chain and regression checks, not silent resealing of the old BPF manifest.
- **Check:** PASS independent text apply; PASS text apply after preceding successful patches in this submitted batch; reverse apply FAIL. No production application or target compilation. Scratch diff confirms only the mm_release wake call changes in fork.c. Actual patched futex header preprocesses in both FUTEX=y (declaration) and FUTEX=n (stub) configurations using host cc after stripping includes; not a full header/kernel compile.
- **Before implementation:** Preserve immutable BPF source records; add a reviewed narrow fork.c overlay and retain the exact before-image chain. Retest clear_child_tid/pthread_join, exec/exit/vfork completion, clone3/pidfd/BPF regressions, FUTEX=y and FUTEX=n target compilation; preprocessing alone is not build proof.
- **Decision/application:** pending / not applied.

### PHX-027 — `d568ed4635697d3c1014119ecafc717caa6023e0`

- **Changes:** Replace sys_clone with an old six-argument _do_fork call in the x86 compat clone wrapper and include sched/task.h.
- **Electro finding:** Only arch/x86 code changes and compat_sys_x86_clone is not present in current source (PHX-021 was not applied). In addition to that textual prerequisite, donor calls _do_fork(flags, stack, 0, parent_tid, child_tid, tls), while Electro declares/defines _do_fork(struct kernel_clone_args *). It is incompatible as written even after creating the old wrapper. Do not regress generic clone3/pidfd code or its argument/safety handling to accommodate an unnecessary x86 patch.
- **Check:** FAIL independent text apply; FAIL text apply after preceding successful patches in this submitted batch; reverse apply FAIL. No production application or target compilation.
- **Independent conflict:** error: patch failed: arch/x86/ia32/sys_ia32.c:241; error: arch/x86/ia32/sys_ia32.c: patch does not apply
- **Before implementation:** Skip for ARM64. If x86 maintenance is explicitly requested later, adapt around current kernel_clone_args ABI after reviewing PHX-021 prerequisites; never restore the obsolete generic _do_fork API.
- **Decision/application:** pending / not applied.

### PHX-028 — `67da86f11e7bb8663400972707088e91d9457dcb`

- **Changes:** Remove the x86-only waitpid compat wrapper/prototype and route the x86 compat syscall table to native sys_waitpid.
- **Electro finding:** All three paths are under arch/x86; current tree uses sys32_waitpid, not the compat_sys_x86_waitpid name introduced by PHX-020. Text application fails until that older x86 migration is present/adapted. No ARM64/AArch32 benefit; legacy native waitpid cleanup is separately represented by PHX-023.
- **Check:** FAIL independent text apply; FAIL text apply after preceding successful patches in this submitted batch; reverse apply FAIL. No production application or target compilation.
- **Independent conflict:** error: patch failed: arch/x86/entry/syscalls/syscall_32.tbl:13; error: arch/x86/entry/syscalls/syscall_32.tbl: patch does not apply; error: patch failed: arch/x86/ia32/sys_ia32.c:169; error: arch/x86/ia32/sys_ia32.c: patch does not apply; error: patch failed: arch/x86/include/asm/sys_ia32.h:35; error: arch/x86/include/asm/sys_ia32.h: patch does not apply
- **Before implementation:** Skip for ARM64. If x86 maintenance is explicitly requested later, reassess PHX-020/name/table prerequisites and native waitpid ABI.
- **Decision/application:** pending / not applied.

## PHX-B004 — ten socket-helper extractions

Reviewed against published `c6de0ddbe`; all three affected local source files
were byte-verified against that revision despite restored local Git metadata.
All ten patches apply in the supplied order **in a temporary copy**. Only
PHX-029 applies independently as supplied; the others have header/dispatcher
context dependencies, not demonstrated semantic dependencies between operations.

**All decisions pending; none applied. No target/device/performance tests.**

| Stable ID | Donor | Helper extracted | Recommendation |
| --- | --- | --- | --- |
| PHX-029 | [`4b4a463c4`](https://github.com/PhoenixKernel/linux/commit/4b4a463c4ad2376778aaf6a13835d5746050e350) | `__sys_recvfrom()` | Optional coherent cleanup series |
| PHX-030 | [`2415e0d2f`](https://github.com/PhoenixKernel/linux/commit/2415e0d2f6b00a0c0bbf6094a9b0b6111de100c3) | `__sys_sendto()` | Optional coherent cleanup series |
| PHX-031 | [`1f36c67bd`](https://github.com/PhoenixKernel/linux/commit/1f36c67bdec073a25e798de55e2d9ebfb9f0e13a) | `__sys_accept4()` | Optional coherent cleanup series |
| PHX-032 | [`cf2e7f905`](https://github.com/PhoenixKernel/linux/commit/cf2e7f905e20175d51726cb2e40a3d1935399d5b) | `__sys_socket()` | Optional coherent cleanup series |
| PHX-033 | [`e779ac92b`](https://github.com/PhoenixKernel/linux/commit/e779ac92be7ab53f105ddb409b0071160f709747) | `__sys_bind()` | Optional coherent cleanup series |
| PHX-034 | [`482ec3da2`](https://github.com/PhoenixKernel/linux/commit/482ec3da2d9d58396a5a34274ac4322328907a1c) | `__sys_connect()` | Optional coherent cleanup series |
| PHX-035 | [`9b234998d`](https://github.com/PhoenixKernel/linux/commit/9b234998dc9a4553beb96c15fae946a321f35686) | `__sys_listen()` | Optional coherent cleanup series |
| PHX-036 | [`77911088b`](https://github.com/PhoenixKernel/linux/commit/77911088b86c7993fc8195e5b8689017f674e428) | `__sys_getsockname()` | Optional coherent cleanup series |
| PHX-037 | [`8a75a83e4`](https://github.com/PhoenixKernel/linux/commit/8a75a83e427e44522b8178021120ab64057dd3f7) | `__sys_getpeername()` | Optional coherent cleanup series |
| PHX-038 | [`afa50fd4f`](https://github.com/PhoenixKernel/linux/commit/afa50fd4f938098071d4188515563d2cdbd24cdc) | `__sys_socketpair()` | Optional coherent cleanup series |

### Batch conclusions and preservation checks

- All ten extracted helper bodies are **byte-identical** to their original
  Electro syscall bodies. Native wrappers forward once; prototypes are unique.
  Per-operation body SHA-256 values are recorded in the JSON ledger.
- Vendor `sockev_notify`/`seemp_logk_sendto` instrumentation and LSM checks remain;
  existing BPF get/setsockopt bodies are unchanged in scratch replay.
- Compat `MSG_CMSG_COMPAT` and pointer-conversion counts remain. Native/AArch32
  socket syscall tables are not changed. AArch32 slot 102 is disabled, so the
  multiplexed `socketcall` conversions alone are not a phone feature upgrade.
- Helpers still accept `__user` pointers; they are **not** kernel-address socket
  APIs or newly exported module APIs. Existing `set_fs` sites and other internal
  syscall calls remain. Do not call this a complete modern socket-stack backport.
- No TCP/BBR algorithm, buffer cap, EDT/PLB/ECN_LOW optimization or demonstrated
  throughput/latency improvement is introduced. Reasonable optional foundation
  if explicitly approved as a group; PHX-010 remains the stronger correctness item.

### Detailed findings and evidence

### PHX-029 — `4b4a463c4ad2376778aaf6a13835d5746050e350`

- **Changes:** Extract __sys_recvfrom from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_recvfrom; compat recvfrom calls native sys_recvfrom, and native recv plus socketcall also call that entry point. Donor forwards all to the helper while retaining MSG_CMSG_COMPAT in the compat recvfrom wrapper. AArch32 direct recvfrom is wired to compat_sys_recvfrom, so this path is relevant to 32-bit ARM applications. The separate compat recv wrapper still calls sys_recv after this series; not all internal syscall calls are removed.
- **Check:** PASS independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_recvfrom body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test native/compat recvfrom plus recv, MSG_CMSG_COMPAT retention, invalid fds/pointers/address lengths, EFAULT and nonblocking behavior. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-030 — `2415e0d2f6b00a0c0bbf6094a9b0b6111de100c3`

- **Changes:** Extract __sys_sendto from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_sendto; native send and socketcall routes still call sys_sendto. Existing buffer import, address copy, O_NONBLOCK -> MSG_DONTWAIT and sock_sendmsg body are retained, including vendor seemp_logk_sendto instrumentation. Source body equality is not a demonstrated send-speed improvement.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_sendto body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:363; error: include/linux/socket.h: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test send/sendto across native/compat entry paths, optional destination address, invalid lengths/pointers, O_NONBLOCK/MSG_DONTWAIT and vendor logging. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-031 — `1f36c67bdec073a25e798de55e2d9ebfb9f0e13a`

- **Changes:** Extract __sys_accept4 from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_accept4; native accept and native/compat socketcall routes use sys_accept4. Donor preserves flag validation, socket/security checks, fd/file ownership, peer-address copyout and cleanup code, plus existing socket-event behavior. No accept algorithm or new flag semantics introduced.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_accept4 body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:366; error: include/linux/socket.h: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test accept/accept4, CLOEXEC/NONBLOCK, peer-address EFAULT, allocation/fd exhaustion, LSM denial and cleanup/refcounts; preserve current vendor behavior rather than silently tuning it. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-032 — `cf2e7f905e20175d51726cb2e40a3d1935399d5b`

- **Changes:** Extract __sys_socket from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_socket. Helper extraction retains type/flag validation, sock_create, sock_map_fd error cleanup and vendor SOCKEV_SOCKET notification body. Normal user syscall entry remains defined. Compat socketcall routing changes, but that multiplexor is not exposed through this phone's AArch32 syscall slot 102.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_socket body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:368; error: include/linux/socket.h: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test native/AArch32 socket creation, type/protocol errors, CLOEXEC/NONBLOCK and fd mapping/failure cleanup. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-033 — `e779ac92be7ab53f105ddb409b0071160f709747`

- **Changes:** Extract __sys_bind from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_bind. Shared body retains move_addr_to_kernel, security_socket_bind, protocol bind, fd reference release and vendor SOCKEV_BIND behavior. No changes to binding policy, ports or address families were found in the extraction.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_bind body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:369; error: include/linux/socket.h: patch does not apply; error: patch failed: net/compat.c:726; error: net/compat.c: patch does not apply; error: patch failed: net/socket.c:2530; error: net/socket.c: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test native/AArch32 bind address validation, LSM denial, protocol errors and vendor notifications. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-034 — `482ec3da2d9d58396a5a34274ac4322328907a1c`

- **Changes:** Extract __sys_connect from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_connect. Shared body retains user-address validation, security_socket_connect, protocol connect using socket file flags, reference cleanup and vendor SOCKEV_CONNECT behavior. No TCP congestion, routing, timeout or nonblocking-connect tuning is introduced.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_connect body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:370; error: include/linux/socket.h: patch does not apply; error: patch failed: net/compat.c:729; error: net/compat.c: patch does not apply; error: patch failed: net/socket.c:2538; error: net/socket.c: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test blocking/nonblocking connect, invalid addresses, LSM denial and reference cleanup; do not infer TCP performance gains. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-035 — `9b234998dc9a4553beb96c15fae946a321f35686`

- **Changes:** Extract __sys_listen from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_listen. Shared body retains current per-netns somaxconn clamp, security_socket_listen, protocol listen, reference release and vendor SOCKEV_LISTEN behavior. This is not a backlog-size or TCP queue-tuning change.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_listen body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:372; error: include/linux/socket.h: patch does not apply; error: patch failed: net/compat.c:732; error: net/compat.c: patch does not apply; error: patch failed: net/socket.c:2546; error: net/socket.c: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test backlog clamping, LSM denial, valid/invalid descriptors and notifications; retain existing somaxconn policy. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-036 — `77911088b86c7993fc8195e5b8689017f674e428`

- **Changes:** Extract __sys_getsockname from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_getsockname. Shared body retains security_socket_getsockname, protocol local-name lookup and move_addr_to_user length/copyout behavior. No new kernel-pointer interface or module export is provided.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_getsockname body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:373; error: include/linux/socket.h: patch does not apply; error: patch failed: net/compat.c:738; error: net/compat.c: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test local-address copyout/length faults and LSM denial for native/AArch32 callers. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-037 — `8a75a83e427e44522b8178021120ab64057dd3f7`

- **Changes:** Extract __sys_getpeername from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_getpeername. Shared body retains security_socket_getpeername, protocol peer-name lookup, copyout/error handling and fd-reference release. No change to peer-address policy or transport behavior found in the extraction.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_getpeername body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:375; error: include/linux/socket.h: patch does not apply; error: patch failed: net/compat.c:741; error: net/compat.c: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test peer-address copyout/length faults, unconnected sockets and LSM denial for native/AArch32 callers. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

### PHX-038 — `afa50fd4f938098071d4188515563d2cdbd24cdc`

- **Changes:** Extract __sys_socketpair from the existing socket syscall implementation, retain a forwarding native syscall wrapper, declare the helper and redirect the reviewed native/compat internal call sites.
- **Electro finding:** Electro lacks __sys_socketpair. Shared body retains type/flag handling, socketpair creation, fd allocation, copyout, audit_fd_pair, installation order and all failure cleanup. No new AF_UNIX/IPC feature introduced; fd exhaustion and partial-copyout regression tests still required if adopted.
- **Check:** FAIL independent text apply; PASS sequential text apply in PHX-029..038 order in a temporary copy; reverse apply FAIL. The resulting __sys_socketpair body is byte-identical to the corresponding original syscall body. Wrapper forwards once; declaration is unique. Not target-compiled or runtime-tested.
- **Standalone conflict:** error: patch failed: include/linux/socket.h:377; error: include/linux/socket.h: patch does not apply; error: patch failed: net/compat.c:744; error: net/compat.c: patch does not apply; error: patch failed: net/socket.c:2580; error: net/socket.c: patch does not apply
- **Before implementation:** If approved, prefer reviewing/validating this as a coherent PHX-029..038 series; preserve Electro vendor hooks and existing BPF sockopt code. Test AF_UNIX socketpairs, flags, fd exhaustion, allocation failure, partial copyout and cleanup/audit behavior. Helpers retain __user pointers, are not EXPORT_SYMBOL APIs, and do not replace kernel socket APIs; do not use kernel addresses without separately reviewed handling.
- **Decision/application:** pending / not applied.

## PHX-B005 — eight socket-helper follow-ups

All eight are **optional maintenance**, not demonstrated bug/performance fixes.
They continue PHX-B004; none applies unmodified to the current production tree.
After replaying PHX-029..038 in a temporary copy, all eight apply in supplied
order. Independently after that B004 replay, PHX-039/040/042/043 pass while
PHX-041/044/045/046 need further preceding donor context. Distinguish these text
contexts from the real helper/signature prerequisites recorded below.

**All decisions pending; none applied. No target/device/performance tests.**

| Stable ID | Donor | Change | Recommendation |
| --- | --- | --- | --- |
| PHX-039 | [`90126e1f9`](https://github.com/PhoenixKernel/linux/commit/90126e1f98ff83ec6eaedbfea409f46f9d6dd2b4) | shutdown helper | Optional extraction |
| PHX-040 | [`799fa59de`](https://github.com/PhoenixKernel/linux/commit/799fa59dee01bd95f3ad6275701c1bd3b9af4f73) | native recvmmsg helper | Optional extraction |
| PHX-041 | [`e43ff2665`](https://github.com/PhoenixKernel/linux/commit/e43ff2665c526197099610ff0cae48c60eb5b580) | message compat-flag boundary | Optional; validate compat-flag boundary |
| PHX-042 | [`9f4ccafba`](https://github.com/PhoenixKernel/linux/commit/9f4ccafbad32a42231278633f0dbe717e1bc3ba7) | send wrapper removal | Optional; socketcall-only phone benefit limited |
| PHX-043 | [`ef0cb6ad2`](https://github.com/PhoenixKernel/linux/commit/ef0cb6ad22a2093da0166eebbc7d99d58afdf61e) | recv wrapper removal | Optional; requires PHX-029 |
| PHX-044 | [`d3126ab3a`](https://github.com/PhoenixKernel/linux/commit/d3126ab3a9b99911e158a5584d7e7c554b0eaf0c) | compat recvfrom helper | Optional; requires PHX-029 |
| PHX-045 | [`5ab8a8a32`](https://github.com/PhoenixKernel/linux/commit/5ab8a8a321c954da3e7155f0a5fbaf9c2209f04f) | compat recvmmsg helper | Optional timeout-preserving extraction |
| PHX-046 | [`c685a4750`](https://github.com/PhoenixKernel/linux/commit/c685a47509dcecac0a10d171c6a3bd6b7452e216) | compat message helpers | Optional; requires PHX-041 signature update |

### Important checks and limitations

- PHX-041 moves existing native `MSG_CMSG_COMPAT` rejection into shared helpers.
  Native wrappers/socketcall pass **true**; compat paths retain flag injection
  and pass **false**. Definitions, declarations and all known callers must move
  together. PHX-046 relies on that signature change. No new security fix claimed.
- Shutdown, native recvmmsg and compat recvmmsg extracted bodies are byte-identical
  to Electro originals. Compat message helpers retain their post-PHX-041 bodies.
  Existing native/compat timeout-copyback conditions are unchanged.
- **256 host-mock recvmmsg cases passed:** 128 with the compat flag mask and 128
  with zero mask. Actual extracted old/new bodies were compiled with mocked
  receive backend, copy helpers and time converters. Tested return counts, NULL
  timeouts, flag rejection and copy faults; **not** a Linux/ARM64 build, kernel
  configuration build, real usercopy/layout/timekeeping or device test.
- Vendor hooks, LSM call counts, socketcall audit/argument validation, compat
  pointer-conversion counts and BPF sockopt bodies were preserved by source
  guards. No direct `sys_*()`/`compat_sys_*()` invocations remain in the two
  reviewed files after the full scratch series; other kernel files were not
  migrated and existing `set_fs` sites remain.
- PHX-040's commit message mentions `sys_getsockopt` by mistake; the actual patch
  extracts native **recvmmsg** timeout handling. No getsockopt change was made.
- Generic ARM64/AArch32 paths, not x86-only. AArch32's socketcall slot remains
  disabled; direct compat recv/message/recvmmsg wrappers remain in use. No TCP,
  BBR, EDT, PLB, ECN_LOW or buffer-cap tuning is introduced.

### Detailed findings and evidence

### PHX-039 — `90126e1f98ff83ec6eaedbfea409f46f9d6dd2b4`

- **Changes:** Extract __sys_shutdown, retain the native syscall wrapper and redirect native/compat socketcall shutdown cases.
- **Electro finding:** Electro lacks __sys_shutdown and still calls sys_shutdown from socketcall dispatchers. The moved body retains fd lookup, security_socket_shutdown, protocol shutdown and reference release byte-for-byte. Direct native/AArch32 shutdown still uses the retained syscall wrapper. No shutdown policy/half-close behavior change identified.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: PASS. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-038. PHX-038 is donor header/nearby-dispatcher context, not a semantic dependency of shutdown. The extraction can be adapted independently; unmodified donor replay was checked only after the full B004 sequence.
- **Before implementation:** Test SHUT_RD/WR/RDWR, invalid how/fd values, LSM denial and protocol cleanup. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

### PHX-040 — `799fa59dee01bd95f3ad6275701c1bd3b9af4f73`

- **Changes:** Extract static do_sys_recvmmsg for native timeout copyin/copyout and use it from the syscall wrapper and native socketcall.
- **Electro finding:** Electro already has __sys_recvmmsg for the receive loop, but its native syscall owns MSG_CMSG_COMPAT rejection and user-timeout copies. do_sys_recvmmsg retains that entire syscall body byte-for-byte: NULL timeout path, flag rejection before copying/lookup, EFAULT behavior, and timeout copyback only when datagrams > 0. Internal timespec64-based receive-loop calculations remain untouched. Donor message incorrectly mentions sys_getsockopt; actual diff is recvmmsg only.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: PASS. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-031. PHX-031 supplies __sys_accept4 in adjacent donor hunk context, not a semantic recvmmsg prerequisite. Current recvmmsg types already match this patch; no timespec64-to-timespec rollback was needed.
- **Before implementation:** Test NULL/non-NULL native timeouts, invalid timeout pointer/value, partial success, copyout failure, flags and MSG_WAITFORONE. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

### PHX-041 — `e43ff2665c526197099610ff0cae48c60eb5b580`

- **Changes:** Add forbid_cmsg_compat to __sys_sendmsg, __sys_sendmmsg and __sys_recvmsg; move the native rejection into each helper and update declarations plus native/compat callers together.
- **Electro finding:** Electro rejects MSG_CMSG_COMPAT in native syscall wrappers, while existing shared helpers allow it for compat. Patch preserves that split: all native wrappers/native socketcall cases pass true; all compat message calls keep flags | MSG_CMSG_COMPAT and pass false. Each shared implementation differs only by the guard inserted before fd lookup (and before sendmmsg vlen handling). This is sensitive ancillary-data/layout policy maintenance, not a new security fix. Whole-workspace C/header search including hidden/ignored files found affected direct helper references only in these three files; no EXPORT_SYMBOL API is added.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: FAIL. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-040. PHX-040 and B004 supply donor context; the real requirement is an atomic signature/header/all-caller update across the three files. do_sys_recvmmsg retains its own native rejection, and __sys_recvmmsg does not gain this boolean. Do not cherry-pick only the new helper definitions or caller edits.
- **Before implementation:** Validate native MSG_CMSG_COMPAT rejection (including invalid fd/error precedence) and real AArch32 ancillary-data conversion, SCM_RIGHTS/SCM_CREDENTIALS, CMSG sizing/truncation and MSG_CMSG_CLOEXEC. Audit any out-of-tree source users of the changed internal signatures. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

### PHX-042 — `9f4ccafbad32a42231278633f0dbe717e1bc3ba7`

- **Changes:** Expand native/compat socketcall sys_send calls directly to __sys_sendto with NULL destination and zero address length.
- **Electro finding:** The two dispatchers still call sys_send in Electro. Expansion matches the send wrapper exactly and leaves user pointers/lengths/flags unchanged. Native/AArch32 direct send syscall wrappers are not changed here. AArch32 slot 102 is disabled, so these socketcall-only edits add little direct phone benefit.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: PASS. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-030. Real helper prerequisite: PHX-030 must provide __sys_sendto, or an equivalent reviewed extraction. Other preceding socket-helper names appear in supplied patch context; they are not a semantic requirement for sending.
- **Before implementation:** Check native/compat socketcall SYS_SEND forwarding where that ABI is enabled, no destination override, nonblocking behavior and unchanged errors. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

### PHX-043 — `ef0cb6ad22a2093da0166eebbc7d99d58afdf61e`

- **Changes:** Expand native socketcall sys_recv and direct compat recv into __sys_recvfrom calls with NULL address/length outputs.
- **Electro finding:** The compat recv wrapper still crosses into sys_recv. Patch calls __sys_recvfrom directly with flags | MSG_CMSG_COMPAT and NULL address arguments; native socketcall recv also expands identically. Unlike socketcall-only changes, compat recv is directly used by AArch32 syscall 291 on this target.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: PASS. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-029. Real helper prerequisite: PHX-029 must provide __sys_recvfrom, or an equivalent reviewed extraction. Other preceding edits supply nearby donor context.
- **Before implementation:** Test direct AArch32 recv and native recv/socketcall behavior, invalid pointers/fds, zero lengths and nonblocking receive, retaining compat flags. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

### PHX-044 — `d3126ab3a9b99911e158a5584d7e7c554b0eaf0c`

- **Changes:** Add static inline __compat_sys_recvfrom, use it from compat recv/recvfrom and bypass compat syscall wrappers in compat socketcall.
- **Electro finding:** The helper centralizes flags | MSG_CMSG_COMPAT and calls __sys_recvfrom. Direct compat recv and recvfrom retain their parameter forwarding, while socketcall keeps compat_ptr conversions and NULL outputs for SYS_RECV. User syscall definitions and AArch32 table entries remain intact; no kernel-address interface or exported module symbol is introduced.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: FAIL. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-029, PHX-043. PHX-029 is the semantic native-helper prerequisite. PHX-043 is the reviewed direct-recv predecessor for the supplied diff. PHX-041 and PHX-039 also occur in surrounding donor context, not in this helper's actual implementation.
- **Before implementation:** Test direct AArch32 recv/recvfrom, compat address/length copyout errors, NULL outputs, flags and socketcall forwarding on architectures exposing it. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

### PHX-045 — `5ab8a8a321c954da3e7155f0a5fbaf9c2209f04f`

- **Changes:** Extract static __compat_sys_recvmmsg, retain the compat syscall wrapper and use the helper from compat socketcall.
- **Electro finding:** The entire existing compat recvmmsg body is preserved byte-for-byte: compat_get_timespec, MSG_CMSG_COMPAT injection, __sys_recvmmsg call, and compat_put_timespec only after positive datagram count. This does not route a compat user timeout through the native user-timespec copier or change __sys_recvmmsg's signature. Direct AArch32 syscall 365 remains mapped to compat_sys_recvmmsg.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: FAIL. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-044. PHX-044 and neighboring socket edits supply donor text context, not a semantic dependency of the timeout-conversion helper. This extraction uses the preexisting __sys_recvmmsg and could be independently adapted; no production adaptation was made.
- **Before implementation:** Test real 32-bit timeout layout, NULL timeout, conversion/copy faults, partial datagram counts, MSG_WAITFORONE and timeout copyback behavior. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

### PHX-046 — `c685a47509dcecac0a10d171c6a3bd6b7452e216`

- **Changes:** Add static inline __compat_sys_sendmsg/sendmmsg/recvmsg, retain compat syscall wrappers and route compat socketcall cases directly to the helpers.
- **Electro finding:** Each new compat helper body is byte-identical to the corresponding post-PHX-041 compat syscall body: casts to the existing user-message types, flags | MSG_CMSG_COMPAT, and forbid_cmsg_compat=false are retained. Forwarding wrappers keep AArch32 direct sendmsg/recvmsg/sendmmsg entry names and ABI. sendmmsg helper returns long while existing backend returns int; this matches the prior compat syscall return promotion. Does not fix existing compat layout/ancillary bugs by itself.
- **Check:** FAIL unmodified standalone and B005-only ordered replay; reverse FAIL. PASS supplied-order replay after all ten B004 donors in a temporary copy. Independent after full B004: FAIL. Text/source evidence only; no target build or device test.
- **Dependencies:** PHX-041, PHX-044, PHX-045. PHX-041 is a real shared-helper signature prerequisite for the added false argument. PHX-044/045 supply adjacent helper/dispatcher context in the submitted diff. Preserve compat CMSG flag injection and false together; do not reuse this permissive path for native callers.
- **Before implementation:** Test direct AArch32 sendmsg/recvmsg/sendmmsg, CMSG conversion/alignment, SCM_RIGHTS/credentials, truncation, partial batched sends, fd errors and socketcall where supported. Recheck current source/prerequisites if approved; preserve vendor hooks, LSM/audit paths, existing BPF sockopt integration, timespec64 loop calculations and user-pointer semantics. No new module export or network performance benefit is implied.
- **Decision/application:** pending / not applied.

## PHX-B006 — ten System V IPC helper extractions

**Recommendation: defer for the current miatoll profile.** `CONFIG_SYSVIPC` is
not enabled in the checked-in defconfig, defaults to n, has no Kconfig select/
imply found in the whole tree, and is not enabled by the current CI script.
`ipc/Makefile` excludes these implementation objects without it. This is a
static profile audit, **not** a fresh resolved target `.config` or device check.
These changes do not improve Android Binder, ashmem/memfd or POSIX message queues.
Do not enable SYSVIPC or IPC namespaces just to adopt the cleanup.

All ten apply in supplied order in a temporary copy. Only PHX-047 applies
independently as supplied; later commits accumulate header/dispatcher context.
PHX-047 supplies the common `util.h` include plumbing, but the different IPC
operations do not semantically depend on one another. No socket-batch prerequisite.

**All decisions pending; none applied. No target/device/performance tests.**

| Stable ID | Donor | Helper operation | Recommendation |
| --- | --- | --- | --- |
| PHX-047 | [`5b9e3986e`](https://github.com/PhoenixKernel/linux/commit/5b9e3986ed08a0d6800f48a684782d88ad8665ab) | `semtimedop` native + compat | Defer current profile; optional enabled-profile cleanup |
| PHX-048 | [`867dc91d5`](https://github.com/PhoenixKernel/linux/commit/867dc91d5bb805fd30c22c448016536d71220a28) | `semget` | Defer current profile; optional enabled-profile cleanup |
| PHX-049 | [`c90ea2c39`](https://github.com/PhoenixKernel/linux/commit/c90ea2c39196ce5538ff47eef06ff9c5438c0cd3) | `semctl` native + compat | Defer current profile; optional enabled-profile cleanup |
| PHX-050 | [`1ff3e9557`](https://github.com/PhoenixKernel/linux/commit/1ff3e9557824b6e512b3ac98087f757138b1ef1d) | `msgget` | Defer current profile; optional enabled-profile cleanup |
| PHX-051 | [`7972b1e62`](https://github.com/PhoenixKernel/linux/commit/7972b1e626192e3bc5fa2a053d0d2bd9dce1f0a7) | `shmget` | Defer current profile; optional enabled-profile cleanup |
| PHX-052 | [`36acca62f`](https://github.com/PhoenixKernel/linux/commit/36acca62fd5518ec815a1d53efb8de61698cd093) | `shmdt` | Defer current profile; optional enabled-profile cleanup |
| PHX-053 | [`6aeca04db`](https://github.com/PhoenixKernel/linux/commit/6aeca04dbc048d30c0e1301d28ec0e802b4f4a73) | `shmctl` native + compat | Defer current profile; optional enabled-profile cleanup |
| PHX-054 | [`341579f26`](https://github.com/PhoenixKernel/linux/commit/341579f2626babfc39e8cbd8e23dd8d9a3f68f8c) | `msgctl` native + compat | Defer current profile; optional enabled-profile cleanup |
| PHX-055 | [`8ab547388`](https://github.com/PhoenixKernel/linux/commit/8ab5473888d39d6b3069aa7b2e08fca11745bd8f) | `msgrcv` native + compat | Defer current profile; optional enabled-profile cleanup |
| PHX-056 | [`e16153c15`](https://github.com/PhoenixKernel/linux/commit/e16153c158937afc49ce4b6e137774166550ec3b) | `msgsnd` native + compat | Defer current profile; optional enabled-profile cleanup |

### Preservation and applicability checks

- All **16 native/compat extracted bodies are byte-identical** to Electro's
  originals. Helper definitions/declarations match original types and syscall
  wrappers forward the original arguments in order. No new module exports.
- Inverse extraction reconstructs the full original `ipc/sem.c`, `ipc/msg.c` and
  `ipc/shm.c` modulo whitespace and equivalent unsigned spelling. The full IPC
  dispatcher differs only by callee names, shared includes and unsigned spelling.
- Existing semaphore `timespec64` conversions, IPC_64/version parsing, control
  structure copies, compat signed message size/type conversions, LSM/audit paths
  and current four-argument `do_munmap(..., NULL)` calls remain intact.
- Native ARM64 and AArch32 have direct IPC entries in source, but implementations
  are inactive in the checked-in SysV-disabled profile. AArch32 old `ipc` slot
  **117 is disabled**; no old multiplexer exposure is added.
- Other architecture-specific internal syscall callers remain outside this
  series. This is not a complete cross-architecture IPC modernization, a feature
  enablement, an IPC throughput improvement or a demonstrated correctness fix.

### Detailed findings and evidence

### PHX-047 — `5b9e3986ed08a0d6800f48a684782d88ad8665ab`

- **Changes:** Introduce ksys_semtimedop, compat_ksys_semtimedop; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves native get_timespec64 and compat_get_timespec64 conversions to struct timespec64, EFAULT handling, NULL-timeout behavior and unchanged do_semtimedop. Direct semop already calls do_semtimedop and is untouched; semaphore wait/undo/locking algorithms are not changed. Unlike earlier signal/select adaptations, no time64 rollback or adaptation was needed here. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** PASS unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** Independent. Independent of prior socket/signal batches. Adds linux/security.h, linux/ipc_namespace.h and util.h includes needed by the shared IPC declaration/header plumbing.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test native/compat timeout layouts, NULL/invalid/negative timeout, EFAULT, nsops limits, EINTR, blocking/wakeup behavior and SEM_UNDO on a separately approved SYSVIPC-enabled validation configuration. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-048 — `867dc91d5bb805fd30c22c448016536d71220a28`

- **Changes:** Introduce ksys_semget; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves IPC namespace lookup, nsems validation against current ns->sc_semmsl and ipcget with existing sem_security/sem_more_checks/newary callbacks. No semaphore limits or allocation/permission policy tuning. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test IPC_PRIVATE and existing/new keys, IPC_CREAT/EXCL, nsems bounds, namespace accounting and LSM denial. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-049 — `c90ea2c39196ce5538ff47eef06ff9c5438c0cd3`

- **Changes:** Introduce ksys_semctl, compat_ksys_semctl; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves native unsigned-long arg versus compat int arg, compat_ptr conversion, IPC_64/version parsing, user-structure copies and SETVAL endian handling. Administrative/permission paths remain in existing backends. This is not a 32-bit structure-layout or endian bug fix. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-048. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test native/compat IPC_STAT/SET/RMID, SETVAL/GETVAL/GETALL/SETALL, invalid pointers/IDs/commands, IPC_64 and permission checks; validate other endian variants if claiming cross-architecture support. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-050 — `1ff3e9557824b6e512b3ac98087f757138b1ef1d`

- **Changes:** Introduce ksys_msgget; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves current namespace selection and ipcget with existing newque/msg_security callbacks. This is System V message-queue creation, not POSIX mq_* or Android Binder IPC. No queue limits, memory accounting or wakeup policy changes. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-049. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test IPC_PRIVATE/key lookup, IPC_CREAT/EXCL, permissions, namespace/accounting and allocation limits on a SYSVIPC-enabled test configuration. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-051 — `7972b1e626192e3bc5fa2a053d0d2bd9dce1f0a7`

- **Changes:** Introduce ksys_shmget; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves size_t size, ipc namespace selection and ipcget with existing newseg/shm_security/shm_more_checks callbacks. Compat legacy SHMGET still zero-extends second through unsigned int; donor only spells out the existing unsigned cast. No new shared-memory, ashmem/memfd or hugepage optimization. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-050. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test native/compat sizes including upper 32-bit boundaries, IPC_CREAT/EXCL, permissions, resource limits and existing supported shared-memory flags. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-052 — `36acca62fd5518ec815a1d53efb8de61698cd093`

- **Changes:** Introduce ksys_shmdt; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves the complete current VMA traversal/detach implementation, address-alignment checks, killable mmap_sem locking and existing four-argument do_munmap(..., NULL) calls. Does not replace this with the older donor MM implementation or change shmat. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-051. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test valid/unaligned/stale addresses, split VMAs after mprotect/munmap, multiple segments, EINTR while acquiring mmap_sem and segment destruction/cleanup. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-053 — `6aeca04dbc048d30c0e1301d28ec0e802b4f4a73`

- **Changes:** Introduce ksys_shmctl, compat_ksys_shmctl; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves native/compat structure copies and IPC version parsing, negative ID/command checks, IPC_INFO/SHM_INFO/STAT/SET/RMID paths, and existing SHM_LOCK/UNLOCK permission/locking backend. No new IPC namespace or capability bypass. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-052. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test native/compat control structures, IPC_64, copy faults, IPC_SET/STAT/RMID, SHM_LOCK/UNLOCK and capability/LSM denial. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-054 — `341579f2626babfc39e8cbd8e23dd8d9a3f68f8c`

- **Changes:** Introduce ksys_msgctl, compat_ksys_msgctl; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves native/compat IPC version parsing, control-structure copying, IPC_INFO/MSG_INFO/STAT/SET/RMID paths and existing backend permissions/audit behavior. No change to queue statistics, MSG_COPY support or POSIX message queues. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-053. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test native/compat IPC_64 structures, invalid IDs/commands/pointers, queue statistics, IPC_SET/STAT/RMID and LSM/ownership checks. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-055 — `8ab5473888d39d6b3069aa7b2e08fca11745bd8f`

- **Changes:** Introduce ksys_msgrcv, compat_ksys_msgrcv; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves native do_msg_fill and compat_do_msg_fill selection, compat_ptr conversion and explicit sign extension of compat_ssize_t msgsz and compat_long_t msgtyp before the existing do_msgrcv backend. Legacy version-zero ipc_kludge handling and negative-size validation remain in the dispatcher/backend. No receive-selection, MSG_COPY or wakeup algorithm change. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-054. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test native/compat message type selection including negative types and 32-bit sign boundaries, invalid sizes/pointers, IPC_NOWAIT, MSG_NOERROR/MSG_COPY where supported, short buffers and legacy ipc_kludge on an architecture exposing that ABI. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

### PHX-056 — `e16153c158937afc49ce4b6e137774166550ec3b`

- **Changes:** Introduce ksys_msgsnd, compat_ksys_msgsnd; retain syscall wrappers, declare IPC-internal helpers and redirect relevant native/compat legacy ipc multiplexer callers.
- **Electro finding:** Preserves native long versus compat_long_t mtype loads, EFAULT behavior, compat_ptr and signed compat size conversion before unchanged do_msgsnd. Positive-type/size validation, permissions, queue accounting and blocking/wakeup behavior remain in existing backend; not an IPC throughput fix. Current checked-in miatoll profile does not enable SYSVIPC; these implementation objects are not included by ipc/Makefile in that profile. No current-device config was read.
- **Check:** FAIL unmodified standalone; PASS ordered PHX-047..056 replay in a temporary copy; reverse FAIL. All moved operation bodies are byte-identical, helper/declaration types and wrapper forwarding match original. Source evidence only, not target compilation/runtime equivalence.
- **Dependencies:** PHX-047, PHX-055. PHX-047 supplies shared util.h include/declaration plumbing in ipc/syscall.c; the preceding ID records donor text context in accumulated declarations/nearby dispatcher cases. This operation does not semantically require the preceding IPC operation, and can be adapted independently if equivalent header/prototype plumbing is included. No dependency on PHX-029..046 was found.
- **Before implementation:** Do not enable SYSVIPC, IPC_NS or any other feature merely to apply these cleanups; such activation is outside this review and requires a separate explicit decision. Test native/compat mtype width/sign, invalid pointers and nonpositive type, negative/oversized compat lengths, IPC_NOWAIT/full queues, interrupted waits and removal races. If approved as source maintenance, recheck current baseline and run target builds with existing miatoll settings plus separately approved SYSVIPC=y/COMPAT=y and non-compat build coverage; retain current time64, MM, LSM/audit, and IPC ABI handling. Helpers retain syscall/user-pointer semantics and are not newly exported module APIs.
- **Decision/application:** pending / not applied.

## PHX-B007 — process, compat signal, credential, scheduler and NUMA helpers

**PHX-057..060:** optional cleanup of active paths, not demonstrated performance
or correctness fixes. **PHX-061..064:** recommend defer for checked-in miatoll,
where NUMA is not enabled. General CMA/compaction migration is distinct; none of
these patches optimizes those paths. Do not enable NUMA to adopt this cleanup.

**All decisions pending; none applied. No target/device/performance tests.**

| Stable ID | Donor | Change | Recommendation |
| --- | --- | --- | --- |
| PHX-057 | [`000c490c0`](https://github.com/PhoenixKernel/linux/commit/000c490c08c5d9b9230cfee9c7a5ef2e13b3667e) | getpgid | Optional; SUSFS overlay required |
| PHX-058 | [`64aa362bd`](https://github.com/PhoenixKernel/linux/commit/64aa362bd63bd8e1939d882316e94d946273e79c) | compat sigaltstack | Optional compat signal cleanup |
| PHX-059 | [`f69026387`](https://github.com/PhoenixKernel/linux/commit/f6902638724e057f490263588a6bf5deb86e2ebe) | UID/GID helpers | Optional sensitive credential cleanup; SUSFS overlay and KSU/SELinux tests |
| PHX-060 | [`29ef73194`](https://github.com/PhoenixKernel/linux/commit/29ef7319403d8461a26f13f48bda5106f1046103) | sched_yield | Optional helper cleanup; preserve scheduler provenance |
| PHX-061 | [`7a56e8e50`](https://github.com/PhoenixKernel/linux/commit/7a56e8e5023a3a17c52bd48b6a76fa86048a480d) | migrate_pages | Defer: NUMA inactive |
| PHX-062 | [`5062971da`](https://github.com/PhoenixKernel/linux/commit/5062971da737dda15d9731321e0d94fc9d7aaa68) | move_pages | Defer: NUMA inactive |
| PHX-063 | [`1eafbad9b`](https://github.com/PhoenixKernel/linux/commit/1eafbad9bdcf9f6602122c406f9ac35fe9760880) | mbind | Defer: NUMA inactive |
| PHX-064 | [`635d81bd9`](https://github.com/PhoenixKernel/linux/commit/635d81bd947deb229b92d7da06f76f876ebdbeb0) | get/set_mempolicy | Defer: NUMA inactive |

### Checks, prerequisites and integration caveats

- PHX-057..060 apply independently and in order to current Electro in scratch.
  PHX-061..064 do not. After PHX-001+010 then this batch, all eight apply.
  Bounded tests identify **context**, not semantic feature dependencies:
  PHX-061 after010; PHX-062 after001+010+061; PHX-063/064 each after010+061.
  None of these prerequisites is approved merely because replay succeeded.
- Native/compat extracted bodies match originals; yield's final `return 0`
  stays in its native wrapper while the shared helper is void. Inverse
  reconstruction of whole touched implementation files passes. Existing
  tagged-address handling, credential/LSM checks, scheduler-class dispatch,
  ptrace/cpuset policy and user-copy marshalling remain.
- **PHX-057/059:** current `kernel/sys.c` exactly matches the historical SUSFS
  postimage. Any approved implementation needs a narrow later provenance overlay
  and test support; preserve immutable manifests. Uname spoofing code is unchanged.
- **PHX-059:** actual helpers are `__sys_set*`, despite the donor title's `ksys_*`.
  Current 4.14 KSU uses the LSM-list hook branch, not the 6.8+ static-callsite
  branch. Existing `security_task_fix_setuid(..., LSM_SETID_RES)` body is retained,
  but KSU root/manager/UID-change and SELinux behavior still needs runtime tests.
- **PHX-060:** no CASS/BORE/PELT/yield-policy change. Current `core.c` matches its
  scheduler-correctness postimage; record a later chain if adopted, including
  PHX-010 if jointly approved. No fairness/latency/freeze improvement demonstrated.
- NUMA compat wrappers still use `compat_alloc_user_space`, bitmap/pointer-array
  marshalling and existing count arithmetic. This is not new bounds hardening,
  elimination of user-stack temporaries, or a kernel-address API conversion.
- Profile conclusions use checked-in defconfig/Kconfig source, not a newly
  resolved target `.config` or running-device inspection. No config was changed.

### Detailed findings and evidence

### PHX-057 — `000c490c08c5d9b9230cfee9c7a5ef2e13b3667e`

- **Changes:** Extract static do_getpgid and forward native getpgid and optional getpgrp to it.
- **Electro finding:** Current getpgrp calls sys_getpgid(0); ARM64 COMPAT requests getpgrp, and AArch32 table uses it. Entire lookup/RCU/security_task_getpgid body is preserved, including the existing own-group pid=0 path and int retval return range. No process-group/permission change or measured speed improvement. Changes SUSFS-sealed kernel/sys.c even though uname code is untouched.
- **Check:** PASS unmodified standalone; PASS B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** Independent. Independent. No earlier Phoenix helper prerequisite. Shares the same SUSFS-protected file with PHX-059.
- **Before implementation:** Require a narrow reviewed later provenance overlay/chain for kernel/sys.c and corresponding SUSFS source-check support; do not rewrite historical UPSTREAM.json seals. Test native/AArch32 getpgid/getpgrp, nonexistent pid and LSM denial. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

### PHX-058 — `64aa362bd63bd8e1939d882316e94d946273e79c`

- **Changes:** Extract static do_compat_sigaltstack; retain compat syscall wrapper and call helper from compat_restore_altstack.
- **Electro finding:** Current compat_restore_altstack calls compat_sys_sigaltstack. AArch32 signal32 restore uses compat_restore_altstack and direct sigaltstack maps to the compat syscall. Extracted body is byte-identical: stack pointer/flags/size conversion, compat stack pointer/MINSIGSTKSZ, zeroed old-stack copyout and error handling remain. Restore still squashes every result except -EFAULT. Independent of earlier sigpending/sigset cleanups.
- **Check:** PASS unmodified standalone; PASS B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** Independent. Independent; no PHX-001/003/024 prerequisite. CONFIG_COMPAT=y makes this relevant to 32-bit Android processes.
- **Before implementation:** Test real AArch32 sigaltstack/sigreturn, SS_AUTODISARM, minimum sizes, pointer/copyout faults and preserved restore error squashing. Source equality is not signal-frame/stack-runtime validation. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

### PHX-059 — `f6902638724e057f490263588a6bf5deb86e2ebe`

- **Changes:** Extract eight __sys_set* credential helpers, retain syscall wrappers, add kernel/uid16.h and redirect legacy 16-bit UID/GID wrappers.
- **Electro finding:** Actual helper names are __sys_setregid/setgid/setreuid/setuid/setresuid/setresgid/setfsuid/setfsgid, despite the subject saying ksys_*. All eight existing bodies are byte-identical: capability/user-namespace validation, credential commit/abort and security_task_fix_setuid remain. low2highuid/low2highgid conversions and 16-bit -1 handling are unchanged. ARM64 COMPAT selects HAVE_UID16; UID16 and MULTIUSER default y and are not disabled. Existing 4.14 KSU selects lsm_hooks_list.c, whose setresuid LSM_SETID_RES hook remains reachable through the unchanged security call. The 6.8+ static hook also mentions __sys_setresuid, but is not this kernel's selected path; this patch is not a demonstrated KSU fix. kernel/sys.c has an immutable SUSFS postimage seal.
- **Check:** PASS unmodified standalone; PASS B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** Independent. Independent credential extraction, not dependent on PHX-057. New uid16 header/prototypes and both C-file edits must be kept together; CONFIG_UID16 depends on MULTIUSER, so no new no-MULTIUSER references are intended.
- **Before implementation:** Require explicit SUSFS kernel/sys.c provenance overlay/chain and validation support. Test native/legacy AArch32 UID/GID sentinels and permission failures, setfsuid/setfsgid old-ID return semantics, KSU su/manager/UID transition/umount behavior and SELinux enforcement. Do not infer root compatibility from body equality. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

### PHX-060 — `29ef7319403d8461a26f13f48bda5106f1046103`

- **Changes:** Extract static void do_sched_yield; native sched_yield calls it and returns zero; exported yield calls the helper.
- **Electro finding:** Current yield calls sys_sched_yield. The helper preserves rq locking/IRQ state, yield statistics, scheduler-class yield_task, preemption sequence and schedule(); only the final return 0 stays in the syscall wrapper. yield still sets TASK_RUNNING first. Inverse reconstruction of the entire core.c proves other scheduler source is unchanged in scratch replay, including prior CASS/BORE/PELT and scheduler-correctness integration. No yield policy, fairness, freeze/latency fix or busy-wait guarantee is introduced. Current core.c matches the scheduler-correctness manifest postimage.
- **Check:** PASS unmodified standalone; PASS B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** Independent. Independent. Preserve prior scheduler provenance with a narrow later chain; if PHX-010 is jointly adopted, account for both changes rather than overwriting the historical core.c postimage.
- **Before implementation:** Record a later scheduler provenance chain without resealing historical corrections. Test native sched_yield return zero and kernel yield across supported scheduling classes/preemption modes; no target build or scheduler-runtime validation was done. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

### PHX-061 — `7a56e8e5023a3a17c52bd48b6a76fa86048a480d`

- **Changes:** Extract static kernel_migrate_pages and relocate compat_migrate_pages from kernel/compat.c to mm/mempolicy.c.
- **Electro finding:** Native body is byte-identical, retaining credentials/CAP_SYS_NICE, cpuset/node masks, security_task_movememory, mm/task lifetime and existing migration backend. Relocated compat body changes only the final callee; compat bitmap conversion, nr_bits/maxnode arithmetic, compat_alloc_user_space and copy_to_user remain. Helpers still accept __user masks; no elimination of temporary user-stack marshalling or new bounds hardening is provided. NUMA is not enabled in checked-in miatoll, so this is inactive policy maintenance, not CMA/compaction migration tuning.
- **Check:** FAIL unmodified standalone; FAIL B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** PHX-010. PASS unmodified after PHX-010 alone: current compat sched_rr_get_interval block blocks the donor deletion hunk context. That is a textual dependency, not a semantic dependency of NUMA migration on scheduler RR. Relocation must remove the old compat definition and add the new one atomically.
- **Before implementation:** Do not enable NUMA for this cleanup. If separately approved for NUMA-enabled source maintenance, test native/compat masks and edge maxnode, permissions/cpuset, allocation and copy faults, task/MM lifetime, and appropriate NUMA/MIGRATION/COMPAT build combinations. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

### PHX-062 — `5062971da737dda15d9731321e0d94fc9d7aaa68`

- **Changes:** Extract static kernel_move_pages, include linux/compat.h, and relocate compat_move_pages to the NUMA section of mm/migrate.c.
- **Electro finding:** Native body is byte-identical, retaining flags/CAP_SYS_NICE, ptrace PTRACE_MODE_READ_REALCREDS, security_task_movememory, cpuset policy, task/MM references and status/move backend selection. Compat pointer-array marshalling changes only its final callee; existing allocation multiplication/loop/count code is not hardened. Added compat definition remains inside the surrounding CONFIG_NUMA region. General migrate.c may build for CMA/MIGRATION without NUMA; these syscall wrappers do not optimize those non-NUMA paths.
- **Check:** FAIL unmodified standalone; FAIL B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** PHX-001, PHX-010, PHX-061. After PHX-010+PHX-061, unmodified patch still FAILS until PHX-001 supplies the preceding compat-sigset context; then PASS. PHX-061 must remove the neighboring migrate_pages block for this deletion hunk. These are donor textual-context prerequisites, not semantic dependencies on signal or scheduler logic.
- **Before implementation:** Do not enable NUMA. For separately approved NUMA builds, test real AArch32 pointer arrays/count extremes, allocation and copy faults, flags/ptrace/LSM restrictions and per-page statuses; cover NUMA/COMPAT/MIGRATION combinations and syscall fallback/error behavior. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

### PHX-063 — `1eafbad9bdcf9f6602122c406f9ac35fe9760880`

- **Changes:** Extract static kernel_mbind and redirect existing compat mbind to it, retaining the native syscall wrapper.
- **Electro finding:** Native body is byte-identical, preserving current untagged_addr(start), policy/mode-flag validation, node-mask parsing and do_mbind. Compat body differs only by callee name, retaining bitmap conversion, temporary user-stack memory and nr_bits+1 convention. Current miatoll NUMA is inactive; no change to MGLRU, page reclamation, CMA, compaction or page-migration policy.
- **Check:** FAIL unmodified standalone; FAIL B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** PHX-061. PASS after PHX-010+PHX-061 without PHX-062 or other B007 edits. PHX-061 supplies the adjacent relocated compat migrate_pages context; no semantic dependency between mbind and migrate_pages extraction.
- **Before implementation:** Do not enable NUMA; if maintaining an approved enabled profile, test native/compat mask limits, mode flags, tagged/unaligned addresses, VMA policy and permission/copy faults. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

### PHX-064 — `635d81bd947deb229b92d7da06f76f876ebdbeb0`

- **Changes:** Extract static kernel_set_mempolicy and kernel_get_mempolicy; retain native wrappers and redirect compat wrappers.
- **Electro finding:** Both native bodies are byte-identical, retaining mode/flag validation, node-mask parsing, current untagged_addr(addr), policy queries and copyout. Both compat bodies change only callee names; compat bitmap conversion/copy sizes, maxnode arithmetic, temporary user-stack masks and flags remain. No new NUMA balancing, placement, allocation policy or memory-performance feature is added; NUMA is inactive in the checked-in target profile.
- **Check:** FAIL unmodified standalone; FAIL B007 ordered replay skipping failed patches; reverse FAIL. All eight PASS after PHX-001+010 then B007 supplied order in a temporary copy. Bounded additional context tests and body/inverse-reconstruction guards recorded separately. Not target-compiled or device-tested.
- **Dependencies:** PHX-061. PASS after PHX-010+PHX-061 without PHX-062/063 or other B007 edits. PHX-061 provides kernel_migrate_pages in neighboring donor context. Get/set helpers and their local callers must move together, but no functional dependence on mbind extraction was found.
- **Before implementation:** Do not enable NUMA; if maintaining an approved enabled profile, test native/compat policy flags and output bitmaps, maxnode edge cases, tagged addresses, invalid pointers and NUMA/COMPAT configurations. Recheck integrated source and all pending-user prerequisites if approved. No changes to KSU fork, scheduler policy, NUMA/config activation or unrelated sources are authorized by review.
- **Decision/application:** pending / not applied.

## PHX-B008 — ten filesystem helper extractions

Optional internal-syscall cleanup, **not demonstrated bug/performance fixes**.
Nine donors apply independently/in order in temporary copies; PHX-070 expects a
different eventfd base. All decisions pending; none applied. No target/device/
performance tests, feature activation or publication.

| Stable ID | Donor | Change | Recommendation |
| --- | --- | --- | --- |
| PHX-065 | [`e8357b311`](https://github.com/PhoenixKernel/linux/commit/e8357b311309b1ea5da9f8e5cf66557befadc520) | readlinkat | Optional; SUSFS stat.c overlay required |
| PHX-066 | [`32f933a0b`](https://github.com/PhoenixKernel/linux/commit/32f933a0b06d618204d8936e2d59c73e8440574d) | pipe2 | Optional pipe cleanup |
| PHX-067 | [`96cb68b03`](https://github.com/PhoenixKernel/linux/commit/96cb68b032eb12d6092a72932e1078c56ae41bea) | renameat2 | Optional; SUSFS namei.c overlay required |
| PHX-068 | [`cb709244e`](https://github.com/PhoenixKernel/linux/commit/cb709244ee4293aca5579dbaf2733513c1b34fdb) | futimesat | Optional native time cleanup; compat unchanged |
| PHX-069 | [`d4214ccff`](https://github.com/PhoenixKernel/linux/commit/d4214ccffc934b3ba2afae75f597ba92919db628) | signalfd4 | Optional native/compat helper cleanup |
| PHX-070 | [`505909f73`](https://github.com/PhoenixKernel/linux/commit/505909f73e15b054b7777588b88f3c0b86895a40) | eventfd2 | Adapt current body, or explicitly approve014 base |
| PHX-071 | [`97a388d57`](https://github.com/PhoenixKernel/linux/commit/97a388d5724c2759b729bed24c16a042ba7bd87a) | lookup_dcookie | Defer: PROFILING inactive |
| PHX-072 | [`1a6dbbd44`](https://github.com/PhoenixKernel/linux/commit/1a6dbbd442515375fb0661d4638006338b7d2308) | vmsplice | Optional native/compat helper cleanup |
| PHX-073 | [`a165803e6`](https://github.com/PhoenixKernel/linux/commit/a165803e6ce6b32d4d9d422b6fd355d489b9e68a) | select | Low direct phone benefit; compat select unchanged |
| PHX-074 | [`48a088616`](https://github.com/PhoenixKernel/linux/commit/48a088616118cd60115fbe65f6613b7fcdf3245a) | compat fcntl64 | Optional AArch32 fcntl helper cleanup |

### Integration findings and evidence

- **PHX-065/067:** current stat.c/namei.c match historical SUSFS postimages;
  require narrow later overlays and validation support, not resealing originals.
  Current vendor `vfs_rename2`, KSU rename-observer backend, SUSFS readlink backend,
  retry/cleanup and LSM code remain intact in scratch replay.
- **PHX-070:** donor FAIL on current eventfd body; PASS after **PHX-014 alone**,
  without015/016. That route inherits014's API-removal/error-precedence changes.
  A separate scratch-only extraction of the **current** body also passes source
  guards and keeps `eventfd_file_create` plus current allocation/error order.
  Do not force approval of014 or exported API removals merely for this helper.
- All nine direct helper bodies are byte-identical; types/arguments and inverse
  reconstruction of whole affected files pass. Donor070 is byte-identical to its
  post014 base; the independent alternative is byte-identical to current Electro.
- Current `timespec64` logic in futimesat/select remains. Compat select/old_select
  and pselect are unchanged; `kern_select` still takes `__user` arguments.
  PHX-073's message mentions `sys_umount` by mistake; no unmount change exists.
- Compat signalfd/vmsplice user-stack marshalling remains. Compat signalfd still
  calls compat_sys_signalfd4 from its legacy wrapper; not all internal syscall
  calls are removed. PHX-069 does not require the separate PHX-004 sigset change.
- PROFILING is not enabled by the checked-in profile/Kconfig/CI path, so071 is
  inactive dcookie cleanup, not a BPF/perf optimization. Native old_select is not
  requested by ARM64; AArch32 slot82 is disabled and142 uses unchanged compat
  select. Static profile audit only, not a new resolved config/device check.

### Detailed findings and evidence

### PHX-065 — `e8357b311309b1ea5da9f8e5cf66557befadc520`

- **Changes:** Extract static do_readlinkat; retain readlinkat wrapper and use the helper from readlink.
- **Electro finding:** Whole current body is retained: positive bufsiz validation, LOOKUP_EMPTY handling, user path resolution, security_inode_readlink, atime, vfs_readlink, path release and ESTALE retry. Current vfs_readlink/SUSFS open-redirect backend remains byte-identical. AArch32 readlink/readlinkat paths are relevant, but no symlink correctness/performance fix is introduced. fs/stat.c exactly matches an immutable SUSFS postimage; an approved implementation needs a narrow later overlay.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent helper extraction. Shares existing SUSFS provenance, not a functional dependency on prior Phoenix fs batches.
- **Before implementation:** Preserve immutable fs/stat.c postimage via a reviewed narrow overlay/chain and updated SUSFS validation. Test symlinks/non-symlinks, empty pathname, bufsiz/pointer errors, ESTALE, permissions and real SUSFS open-redirect/hidden-path behavior. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-066 — `32f933a0b06d618204d8936e2d59c73e8440574d`

- **Changes:** Extract static do_pipe2; retain pipe2 wrapper and use the helper from pipe with flags=0.
- **Electro finding:** Body is byte-identical: __do_pipe_flags, descriptor/file ownership, copy_to_user-before-fd_install, EFAULT cleanup and flags remain unchanged. Existing do_pipe_flags kernel-buffer API is not replaced. Native pipe2 and AArch32 pipe/pipe2 use retained wrappers; not a capacity, throughput or pipe-race fix.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent; no earlier eventfd/socket helper prerequisite.
- **Before implementation:** Test pipe/pipe2 CLOEXEC/NONBLOCK/packet flags where supported, invalid flags/output pointer, fd exhaustion/allocation failure and leak-free partial failure. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-067 — `96cb68b032eb12d6092a72932e1078c56ae41bea`

- **Changes:** Extract static do_renameat2; keep renameat2 wrapper and redirect renameat/rename to helper with zero flags.
- **Electro finding:** Current rename body is byte-identical, including RENAME_* validation/CAP_MKNOD, mount checks, locking, security_path_rename, vendor vfs_rename2(old_path.mnt,...), delegated-inode and ESTALE retries, filename ownership and cleanup. Existing vfs_rename2 and vfs_readlink backends plus SUSFS references are untouched. Current 4.14 KSU LSM-list inode_rename observer remains on the same backend path, but is not runtime-validated. fs/namei.c has an immutable SUSFS seal.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent of PHX-012 unlink-helper conversion, but both modify the same sealed namei.c. If jointly approved, retain an explicit combined/ordered provenance chain, not a resealed historical manifest.
- **Before implementation:** Require narrow SUSFS namei.c overlay/source-check support. Test native/AArch32 rename variants, exchange/noreplace/whiteout, mount/delegation/ESTALE failures, ownership cleanup, KSU rename observer and SUSFS path restrictions. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-068 — `cb709244ee4293aca5579dbaf2733513c1b34fdb`

- **Changes:** Extract static do_futimesat; retain native wrapper and use helper from native utimes.
- **Electro finding:** Existing timeval copy, tv_usec range validation, conversion into struct timespec64 and do_utimes flags/NULL-time behavior are byte-identical. Native and compat time conversion backends are not replaced. AArch32 utimes/futimesat use separate unchanged compat wrappers; this is not a direct compat-time improvement or new Y2038 fix.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent; current timespec64 body already matches donor context. No PHX-004 time64 adaptation prerequisite.
- **Before implementation:** Retain time64 backend and test NULL times, invalid microseconds (including UTIME_NOW/OMIT rejection here), timestamps, pointers, permission/read-only-filesystem failures and unchanged compat behavior. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-069 — `d4214ccffc934b3ba2afae75f597ba92919db628`

- **Changes:** Extract static do_signalfd4; retain native wrapper and redirect native signalfd plus compat signalfd4.
- **Electro finding:** Original body remains byte-identical: flags/sizemask checks, blocked-signal mask transformation excluding KILL/STOP, fd creation/update, locking and wakeups. Compat sigset_from_compat, compat_alloc_user_space/copy-to-user marshalling remain; only its final native callee changes. Separate compat signalfd still calls compat_sys_signalfd4, so not all internal compat syscall calls are removed. Relevant to direct AArch32 signalfd4.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent as supplied on current source. PHX-004 get_compat_sigset conversion is a separate optional change, not required for this extraction.
- **Before implementation:** Test native/AArch32 signalfd/signalfd4 creation and mask update, flags, signal delivery, KILL/STOP exclusion, size/copy faults, nonblocking/cloexec, wakeups and fd cleanup. Do not claim temporary user marshalling is removed. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-070 — `505909f73e15b054b7777588b88f3c0b86895a40`

- **Changes:** Extract static do_eventfd and retain eventfd2/eventfd wrappers; supplied donor assumes earlier PHX-014 anon_inode_getfd conversion.
- **Electro finding:** Unmodified donor fails because current eventfd2 has a split eventfd_file_create/descriptor-reservation body, while donor expects the post-PHX-014 inline context. PASS after PHX-014 alone; PHX-015/016 are unnecessary. That route inherits PHX-014's previously recorded allocation/validation error-precedence and helper-removal differences. A separate scratch-only extraction of the CURRENT body also passes body/signature/inverse-file guards, retaining eventfd_file_create, current exports and allocation/error ordering; it is an alternative adaptation, not applied production code.
- **Check:** FAIL standalone/ordered donor; PASS after PHX-014 alone; separate current-body-preserving adaptation source checks PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** PHX-014. PHX-014 is the tested supplied-donor base, not a semantic requirement to have a do_eventfd helper. Prefer preserving the current body if only the helper cleanup is approved; do not silently approve PHX-014 or exported-API removals in PHX-015/016.
- **Before implementation:** Choose explicit scope before implementation: independently adapted current-body extraction or separately approved PHX-014+070. Test count/semaphore/nonblock/cloexec, fd exhaustion, allocation failure and cleanup/error precedence; no target compile or eventfd runtime test performed. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-071 — `97a388d5724c2759b729bed24c16a042ba7bd87a`

- **Changes:** Extract static do_lookup_dcookie; retain native wrapper and redirect compat endian word-assembly paths.
- **Electro finding:** Original CAP_SYS_ADMIN check, cookie/live-state lookup, mutex/path allocation, d_path copyout and errors remain byte-identical. Compat u64 cookie assembly order for big/little endian is retained. PROFILING is not enabled in checked-in miatoll, has no default-y/select/imply found, and gates dcookies.o. This is inactive dcookie maintenance, not a BPF/perf-events speed improvement.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent; no feature activation or new profiling configuration is requested.
- **Before implementation:** Do not enable PROFILING just for this change. For separately approved profiling-enabled coverage, test native/compat cookie word order, CAP_SYS_ADMIN denial, live-cookie lifetime, short buffers and user-copy failures. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-072 — `1a6dbbd442515375fb0661d4638006338b7d2308`

- **Changes:** Extract static do_vmsplice; retain native wrapper and use helper after compat iovec marshalling.
- **Electro finding:** Native body is byte-identical: SPLICE_F_ALL validation, UIO_MAXIOV/zero-segment handling, fd access modes, reference cleanup and existing pipe/user backends. Compat wrapper changes only callee name; iovec conversion and temporary user-space allocation remain. No new zero-copy, pipe algorithm, throughput fix or bounds hardening.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent; no dependency on prior socket or eventfd cleanups.
- **Before implementation:** Test native/AArch32 segment limits, zero vectors, invalid iovec/base/length pointers, flags, read/write pipe directions, nonblocking partial transfers and fd/reference cleanup. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-073 — `a165803e6ce6b32d4d9d422b6fd355d489b9e68a`

- **Changes:** Extract static kern_select; retain native select wrapper and redirect native old_select.
- **Electro finding:** Original native timeval timeout handling, timespec64 deadline, core_sys_select and remaining-time copyback are byte-identical. Compat select/old_select and pselect implementations remain byte-identical, including current time64 support. ARM64 does not request native old_select; AArch32 slot82 is disabled and slot142 uses unchanged compat_sys_select. Limited direct phone benefit, not a poll/select correctness fix. Donor message incorrectly mentions sys_umount: actual patch concerns select, not unmount.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent; no PHX-004 get_compat_sigset prerequisite. Despite kern_select name, arguments are still __user fdsets/timeval, not a kernel-buffer API.
- **Before implementation:** Preserve timespec64 and user-pointer semantics. On an architecture exposing affected native paths, test timeout copyback/EFAULT, signals/restarts, fd-set errors and old_select argument copy; do not infer AArch32 compat changes or unmount behavior. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

### PHX-074 — `48a088616118cd60115fbe65f6613b7fcdf3245a`

- **Changes:** Extract static do_compat_fcntl64; retain compat fcntl64 wrapper and redirect compat fcntl after its command filter.
- **Electro finding:** Body is byte-identical: fdget_raw/O_PATH restrictions, security_file_fcntl, compat flock/flock64 conversions, overflow checks, command translation, lock operations and fd release remain. Compat fcntl still rejects F_*LK64 and OFD commands it previously rejected before forwarding; native fcntl path is unchanged. Relevant to AArch32 fd/locking operations, but no new lock ABI or bug fix is introduced.
- **Check:** PASS standalone and submitted-order replay in a temporary copy; helper body byte-identical and whole-file inverse reconstruction PASS. Reverse FAIL. No target compilation, device or performance test.
- **Dependencies:** Independent. Independent; helper retains exact compat_ulong_t arg and long result semantics. Does not remove compat syscall definitions from the ABI.
- **Before implementation:** Test real AArch32 fcntl/fcntl64, flock offsets/overflow, blocking/interrupted lock operations, OFD acceptance/rejection per entry point, O_PATH/invalid fd/commands, pointer faults, LSM denial and descriptor cleanup. Recheck current integrated source and any separately approved earlier changes; recommendations do not authorize implementation or feature activation. Helpers are internal and no new EXPORT_SYMBOL module API is added.
- **Decision/application:** pending / not applied.

## PHX-B009 — compat/fsnotify/quota and boot-facing helper extraction

All ten full donor diffs were read and per-file counts checked; full SHAs were
new against the previous 74 entries. All **18 affected files** byte-match
published `c6de0ddbe7e159a84c4906cbbf4f2c9138521c13` and remain unchanged.
Five unmodified donors (077–081) pass standalone and ordered text checks; five
need context/base adaptation. All reverse checks fail. Source checks are not
build, runtime, boot or performance validation; all replays were scratch-only.

| Stable ID | Donor | Helper/change | Recommendation |
| --- | --- | --- | --- |
| PHX-075 | [`d9ecb3163`](https://github.com/PhoenixKernel/linux/commit/d9ecb3163423a2af89796bc70f339a45f96ea93d) | add do_compat_select() helper; remove in-kernel call to compat syscall | Optional; preserve current time64 |
| PHX-076 | [`98e27753a`](https://github.com/PhoenixKernel/linux/commit/98e27753a89d40c226e34bae4cf7325f1042ced6) | add do_compat_signalfd4() helper; remove in-kernel call to compat syscall | Optional; explicit signalfd base/adaptation choice |
| PHX-077 | [`52c32d6a4`](https://github.com/PhoenixKernel/linux/commit/52c32d6a4f15211c7dc758f426e9e037b2825a7d) | add do_compat_futimesat() helper; remove in-kernel call to compat syscall | Optional compat maintenance |
| PHX-078 | [`772c9ce71`](https://github.com/PhoenixKernel/linux/commit/772c9ce714c709380bb1d129e5c86bae5a2f84ee) | add do_inotify_init() helper; remove in-kernel call to syscall | Optional active inotify maintenance |
| PHX-079 | [`27c8c4025`](https://github.com/PhoenixKernel/linux/commit/27c8c402556afec41d9a68dc4a4b54030330db9c) | add do_fanotify_mark() helper; remove in-kernel call to syscall | Defer: fanotify disabled |
| PHX-080 | [`8c94ae378`](https://github.com/PhoenixKernel/linux/commit/8c94ae378d43a8932fed6fd887c0d567ac5b41e1) | add kernel_quotactl() helper; remove in-kernel call to syscall | Optional; low direct phone benefit |
| PHX-081 | [`d1bb09903`](https://github.com/PhoenixKernel/linux/commit/d1bb09903cc25d307e0b86e3666c17b6d3aa4bd6) | use COMPAT_SYSCALL_DEFINE for sys32_quotactl() | Recommend skip: x86 quota ABI |
| PHX-082 | [`8f1d0e0db`](https://github.com/PhoenixKernel/linux/commit/8f1d0e0db1f72bc10057de130ca41af39779c661) | add ksys_mount() helper; remove in-kernel calls to sys_mount() | Defer boot-sensitive cleanup; vendor/header + SUSFS overlay needed |
| PHX-083 | [`2c77c02d8`](https://github.com/PhoenixKernel/linux/commit/2c77c02d847031af670073b6cbf116d1e14b6ccc) | add ksys_umount() helper; remove in-kernel call to sys_umount() | Defer boot-sensitive cleanup; SUSFS overlay needed |
| PHX-084 | [`d331bd755`](https://github.com/PhoenixKernel/linux/commit/d331bd755286b515fb16be2a88b6d08dfdf792dc) | add ksys_dup{,3}() helper; remove in-kernel calls to sys_dup{,3}() | Optional; explicit context adaptation/order and boot validation |

### Source-preservation and scope findings

- **075:** donor expects old `timespec` context. Scratch context-only adaptation
  keeps current `timespec64`; no 073/004 prerequisite. Compat select slot142 is
  active; removed legacy old_select cross-call is not routed at ARM64 slot82.
- **076:** supplied donor fails even after 069 alone. It passes after 069 plus
  the **004 signalfd-only fragment**, not proof of the full 004 series/build.
  A separate current-conversion extraction after 069 preserves existing
  `ss32`/copy/convert/user-stack marshalling without forcing 004.
- **077/078:** direct maintenance, preserving compat timespec64/AT_FDCWD and
  inotify flags/group/fd cleanup respectively. No native 068 prerequisite.
- **079:** compat mask word order and native checks stay; debug `__func__`
  label can change. FANOTIFY is inactive in the static profile; do not enable it.
- **080/081:** `kernel_quotactl` still takes `__user` pointers, and compat
  user-space marshalling remains. Native quota is enabled. Alignment-specific
  compat quota is x86-only here; ARM64 AArch32 routes directly to `sys_quotactl`.
  081 applies independently of 080 but has no target-phone ABI benefit.
- **082:** header conflict must preserve the existing `ksys_ftruncate` helper.
  Vendor root-mount casts/boot markers must remain. Scratch alternative also
  explicitly covers the extra `CONFIG_EARLY_SERVICES do_mount_part` caller,
  retaining all three `do_mounts.c` mount calls' arguments and diagnostics.
- **083/084:** unmodified donors pass after adapted 082, then 083. Those are
  supplied-donor textual dependencies, not fd/unmount semantic requirements
  to approve the whole group. Only `ksys_dup` is header-visible; `ksys_dup3`
  stays static. Console/initrd fd0 duplication and ordering remain.
- **082/083:** touch immutable SUSFS-sealed `fs/namespace.c`. If approved, add
  a narrow later overlay/validation chain; **never overwrite the original
  seal**. Mount/umount bodies, backend/LSM/SUSFS code and boot caller arguments
  are preserved in scratch; that does not prove KSU/NoMount behavior on-device.
- All **ten extracted helper bodies** are byte-identical to their respective
  reviewed bases; argument types/wrappers and token-normalized inverse-file
  reconstruction checks pass. The signalfd adaptation uses the post-069 base.
  Existing ftruncate helper and quota table/prototype/NI naming were checked.
- Mount/umount/quota helpers retain `__user`/address-limit conventions. No new
  kernel-buffer APIs, permission bypass, filesystem/root-layout changes,
  performance gains or security fixes are established by these refactors.
- No target build, newly resolved target config, device/boot/ABI/performance
  test, production implementation, commit, push or CI. All decisions pending.

### Detailed findings

### PHX-075 — `d9ecb3163423a2af89796bc70f339a45f96ea93d`

- **Changes:** Extract static do_compat_select; keep compat select wrapper and redirect compat old_select.
- **Electro finding:** Current compat select already uses timespec64, whereas the donor first hunk expects timespec. Only that context line was adapted in scratch: original body, compat fdsets/timeval, timeout conversion/remaining-time copyback and errors remain byte-identical. AArch32 slot142 uses compat_sys_select, but legacy slot82 is sys_ni_syscall, so the old_select cross-call removed here is not a routed ARM64 compat ABI path. No new select correctness or speed fix.
- **Check:** FAIL standalone/ordered donor at fs/select.c:1268. PASS scratch patch changing only donor context from timespec to current timespec64; original helper body/types/wrapper preserved and token-normalized inverse reconstruction PASS. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** No PHX-073 native-select or PHX-004 get_compat_sigset dependency. Textual timespec mismatch must not be resolved by reverting time64.
- **Before implementation:** Preserve existing timespec64 deadlines and compat timeval handling; test AArch32 select timeout/copyback, signals/restarts, fd-set validation and EFAULT. Do not enable unused old_select routing. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-076 — `98e27753a89d40c226e34bae4cf7325f1042ced6`

- **Changes:** Extract static do_compat_signalfd4; keep compat signalfd4 wrapper and redirect legacy compat signalfd.
- **Electro finding:** Current compat body retains ss32/copy_from_user/sigset_from_compat plus compat_alloc_user_space/copy_to_user and calls sys_signalfd4. Supplied donor expects both get_compat_sigset context from PHX-004 and native do_signalfd4 from PHX-069. Donor fails after069 alone but passes after069 plus the004 signalfd-only fragment. A separate scratch adaptation after069 extracts the CURRENT conversion body unchanged, preserving all temporary user-space marshalling and error order without forcing004. Both compat entry points are routed by ARM64 AArch32 tables.
- **Check:** FAIL standalone/ordered donor and after069 alone. PASS donor after069 +004 signalfd fragment (fragment-only fixture). PASS independently adapted current conversion after069 with byte-identical moved body and token-normalized inverse reconstruction. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** Dependencies listed describe supplied-donor context, not blanket approvals. Tested donor fixture used only004 fs/signalfd.c, not the full004 series/build (004 retains separately recorded select time64 conflict). Current-conversion alternative tested after069 does not require004; do not force the wider exported-helper migration.
- **Before implementation:** Explicitly choose donor-base conversion versus current-conversion adaptation; do not automatically approve004/069. Test AArch32 legacy signalfd/signalfd4 mask delivery/update, KILL/STOP exclusion, flags, invalid size/pointers, temporary user-space copy faults, wakeups and cleanup. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-077 — `52c32d6a4f15211c7dc758f426e9e037b2825a7d`

- **Changes:** Extract static do_compat_futimesat; keep compat futimesat wrapper and redirect compat utimes with AT_FDCWD.
- **Electro finding:** Existing timespec64 body, compat timeval conversion, invalid-microsecond checks, NULL-time behavior and do_utimes backend remain byte-identical. Compat utimes retains AT_FDCWD and existing user-pointer semantics. Both compat utimes and futimesat are routed on ARM64; this is maintenance, not a time64 fix or timestamp feature.
- **Check:** PASS standalone and ordered donor; byte-identical moved body/types/wrapper and token-normalized whole-file inverse reconstruction. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** Independent; no dependency on PHX-068 native futimesat extraction or PHX-004.
- **Before implementation:** Test AArch32 utimes/futimesat, AT_FDCWD/dirfd, NULL times, invalid microseconds/UTIME special-value rejection, timestamp range, permission/read-only errors and bad pointers; retain timespec64. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-078 — `772c9ce714c709380bb1d129e5c86bae5a2f84ee`

- **Changes:** Extract static do_inotify_init; retain inotify_init1 wrapper and forward inotify_init with flags zero.
- **Electro finding:** Same flags validation, constant consistency checks, inotify_new_group, anon_inode_getfd and failure cleanup. INOTIFY_USER is default-y and not disabled by the checked-in profile; native init1 and AArch32 init/init1 routes exist. No event-delivery, watch-limit, permission or fd semantics change is introduced by the extraction.
- **Check:** PASS standalone and ordered donor; byte-identical moved body/types/wrapper and token-normalized whole-file inverse reconstruction. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** Independent; unrelated earlier eventfd/pipe helpers are not prerequisites.
- **Before implementation:** Test legacy init/init1, invalid flags, CLOEXEC/nonblocking, fd/group allocation exhaustion and cleanup, watch delivery and reference lifetime. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-079 — `27c8c402556afec41d9a68dc4a4b54030330db9c`

- **Changes:** Extract static do_fanotify_mark; retain native wrapper and redirect compat endian mask assembly to helper.
- **Electro finding:** Native body is byte-identical; compat mask0/mask1 assembly remains endian-correct in source. Existing upper-mask validation, flags/fd/group/path/permission checks and mark handling remain. pr_debug uses __func__, so the helper can change its diagnostic function-name label. FANOTIFY is not enabled in miatoll, defaults n, and no Kconfig select/imply was found. Not an inotify optimization or permission feature activation.
- **Check:** PASS standalone and ordered donor; byte-identical moved body/types/wrapper, unchanged compat mask assembly and token-normalized whole-file inverse reconstruction. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** Independent; do not enable FANOTIFY or FANOTIFY_ACCESS_PERMISSIONS for this cleanup.
- **Before implementation:** Keep fanotify disabled unless separately requested. For future enabled coverage, target-build native/compat, test word order, high mask bits, flags, fd/path/permission errors and mark cleanup; note diagnostic helper-name change. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-080 — `8c94ae378d43a8932fed6fd887c0d567ac5b41e1`

- **Changes:** Extract global internal kernel_quotactl, declare in quotaops.h and redirect four quota compat call sites.
- **Electro finding:** Native quota control body is byte-identical, retaining user_path_at/quotactl_block/do_quotactl, permission/namespace checks, copy paths, Q_SYNC special handling and superblock/path cleanup. Despite kernel_ name, special and addr remain __user pointers; compat temporary user-space structures/marshalling remain. QUOTA=y selects QUOTACTL on miatoll, but fs/quota/compat.o is gated by QUOTACTL_COMPAT and its x86 alignment dependency, absent here; ARM64 AArch32 quotactl maps directly to sys_quotactl. Limited direct phone benefit, no quota behavior fix or exported module API.
- **Check:** PASS standalone and ordered donor; native moved body/types/wrapper, four compat callee-only changes and header/definition type match PASS. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** Independent; PHX-081 is not required. No EXPORT_SYMBOL is added; __user pointer and existing address-limit conventions are retained.
- **Before implementation:** Test native/AArch32 quotactl query/set/sync/on/off, permissions, user namespaces, special=NULL, pointer faults and superblock/path release. Exercise alignment-specific compat translation separately on a relevant x86 build if changed; do not describe this as a kernel-buffer API. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-081 — `d1bb09903cc25d307e0b86e3666c17b6d3aa4bd6`

- **Changes:** Replace sys32_quotactl declaration with COMPAT_SYSCALL_DEFINE4(quotactl32); update x86 syscall table, compat prototype and NI stub.
- **Electro finding:** Targets the x86-only alignment-specific quota compat ABI. Native ARM64 and its AArch32 quota table route remain sys_quotactl, and the ARM64 profile does not build QUOTACTL_COMPAT. Although shared quota/compat/header/NI files are touched, this is not a miatoll quota bug fix. Scratch source checks preserve function body and agree on compat_sys_quotactl32 table/prototype/stub naming; no x86/ARM64 target compilation was run.
- **Check:** PASS standalone and ordered donor. Macro conversion preserves quota compat body on reviewed sequence; x86 table/NI naming source checks PASS. Reverse FAIL. No architecture build/ABI runtime proof. No target/device/boot/performance tests.
- **Dependencies/scope:** PASS independently; no PHX-080 prerequisite. A recommended skip is not an approved user decision.
- **Before implementation:** Recommend skip for ARM64 miatoll. If separately requested for x86 portability, build quota compat both enabled/disabled and verify actual IA32 ABI entry generation/prototype/NI fallback and quota layout conversion. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-082 — `8f1d0e0db1f72bc10057de130ca41af39779c661`

- **Changes:** Extract global internal ksys_mount with __user arguments and redirect devtmpfs, root/initrd mount callers.
- **Electro finding:** Native mount body remains byte-identical: copy_mount_string/options, do_mount, cleanup/errors and lower LSM/SUSFS paths. Unmodified donor conflicts with header tail (existing do_sys_ftruncate/ksys_ftruncate) and vendor do_mount_root casts/markers. Vendor also adds CONFIG_EARLY_SERVICES do_mount_part, an extra sys_mount caller not covered by donor. Scratch alternative preserves existing header helper, root casts/markers/flags/data and all boot diagnostics, redirecting all THREE do_mounts.c calls including that explicitly identified extra caller. This does not remove __user/address-limit conventions or switch to direct do_mount/kernel_mount. fs/namespace.c is SUSFS-sealed.
- **Check:** FAIL standalone/ordered donor in include/linux/syscalls.h and init/do_mounts.c. PASS scratch vendor-preserving adaptation; mount body/types/wrapper, all boot caller argument/diagnostic tokens and existing ftruncate helper preserved. Enables subsequent unmodified083/084 in tested chain. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** Needs context/vendor adaptation, not a functional prerequisite on a pending Phoenix change. Preserve existing header helpers and review extra early-services caller explicitly rather than dropping vendor code; scope the extra rename if approved.
- **Before implementation:** Before approval/implementation, define narrow later SUSFS namespace overlay/validation support without changing immutable original seal. Preserve KSU/NoMount backend behavior and all flags/path/namespace/address-limit semantics. Target-build and boot-test normal initramfs/root and console startup; cover supported initrd, devtmpfs and CONFIG_EARLY_SERVICES variants, mount permission/LSM/SUSFS/KSU/NoMount and failure cleanup. Scratch source checks are not boot safety proof. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-083 — `2c77c02d847031af670073b6cbf116d1e14b6ccc`

- **Changes:** Extract global internal ksys_umount, retain syscall and redirect oldumount/initrd lazy detach.
- **Electro finding:** Moved body is byte-identical: allowed flags, may_mount/capability checks, user_path_mountpoint_at, mount-root/namespace/MNT_LOCKED checks, do_umount and dput/mntput_no_expire. No direct call bypasses LSM or NoMount/KSU/SUSFS backends. Header donor expects prior ksys_mount context. Same __user name/address-limit convention remains; this is not a new kernel-path unmount API or force-unmount policy. Namespace SUSFS seal requires a later overlay if approved.
- **Check:** FAIL standalone/ordered donor only in syscall header. PASS unmodified after vendor/header-adapted082. Body/types/wrapper, namespace inverse reconstruction and initrd arguments preserved in scratch chain. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** PHX-082 is tested textual header/base order; umount helper semantics do not require mount helper. Could instead adapt declaration context if separately scoped; only adapted082->unmodified083 chain was tested here.
- **Before implementation:** Preserve immutable namespace SUSFS seal and add narrow explicit later overlay/check support if approved, coordinated with082. Target-build and test umount/oldumount where routed, invalid flags, permission/LSM denial, locked/busy mounts, lazy detach, initrd old-root teardown and KSU/SUSFS/NoMount behavior. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

### PHX-084 — `d331bd755286b515fb16be2a88b6d08dfdf792dc`

- **Changes:** Extract static ksys_dup3 and global internal ksys_dup; retain syscall wrappers and redirect dup2 plus init console/initrd duplicates.
- **Electro finding:** Both moved bodies are byte-identical: fd/flags validation, locking, replacement and reference cleanup, same-fd dup2 case, fd allocation/install. Only ksys_dup is header-visible; ksys_dup3 stays file-local, with no new exports. Initial console and /linuxrc keep duplicate fd0 calls and ordering. Donor header expects082/083 declarations and initrd hunk expects082 ksys_mount context; no semantic fd dependency on mount/umount exists. Boot-sensitive maintenance, not a new fd feature or console fix.
- **Check:** FAIL standalone/ordered donor in syscall header and initrd mount context. PASS unmodified after adapted082 +083; both bodies/types/wrappers, dup2 path and boot callers preserved in scratch. Reverse FAIL. No target/device/boot/performance tests.
- **Dependencies/scope:** Dependencies describe tested supplied-donor textual context. PASS after adapted082 then083; standalone adaptation is possible in principle but not implemented/tested separately here. Do not force adoption of mount/umount cleanup for fd semantics.
- **Before implementation:** Target-build and test dup/dup2/dup3, same-fd differences, invalid fd/flags, CLOEXEC, replacement/concurrent close, fd exhaustion and refcount cleanup. Verify early console stdin/stdout/stderr and supported initrd /linuxrc startup; no boot proof from source guards. Recheck integrated source and separately approved changes before implementation. Recommendations are not approval; no feature activation, source edits, target compilation or runtime/performance proof is implied.
- **Decision/application:** pending / not applied.

## PHX-B010 — root/cwd, write and initramfs path-operation helpers

All ten full diffs read; additions/deletions checked; all full SHAs new against
84 prior entries. All **16 affected and three supporting source files** match
published `c6de0ddbe7e159a84c4906cbbf4f2c9138521c13` and remain unchanged.
All decisions below are pending; no Phoenix implementation is authorized.

| Stable ID | Donor | Helper/change | Recommendation |
| --- | --- | --- | --- |
| PHX-085 | [`5a45cea3e`](https://github.com/PhoenixKernel/linux/commit/5a45cea3e3e3b8d1afa7d83751202ccf069a4882) | ksys_chroot | Defer optional boot/root cleanup; SUSFS overlay |
| PHX-086 | [`2cd6f0122`](https://github.com/PhoenixKernel/linux/commit/2cd6f012250b1396b29c55d77a2addaaa0035a37) | ksys_write | Optional generic write cleanup; header adaptation + boot tests |
| PHX-087 | [`3e74eb7c9`](https://github.com/PhoenixKernel/linux/commit/3e74eb7c9639cb7cbca333d1f45dd80ec86d2984) | ksys_chdir | Defer optional cwd cleanup; SUSFS overlay |
| PHX-088 | [`602909556`](https://github.com/PhoenixKernel/linux/commit/602909556ba18e5912c297b072aafc8a231fc02b) | ksys_unlink | Only with explicit012 interface; boot validation |
| PHX-089 | [`14850caea`](https://github.com/PhoenixKernel/linux/commit/14850caeaf6f7255de1cf8825f348a6f5f9c685d) | hostfs_do_rmdir rename | Skip as phone improvement; pair with090 for UML portability |
| PHX-090 | [`c1a33b969`](https://github.com/PhoenixKernel/linux/commit/c1a33b9690bfe49a5c351edd545f777a8faba3ca) | ksys_rmdir / global do_rmdir | Defer; namei overlay + boot tests;089 for built-in HOSTFS |
| PHX-091 | [`0e35e7fc8`](https://github.com/PhoenixKernel/linux/commit/0e35e7fc83159497861d078a7469c311c49e8d25) | do_mkdirat / ksys_mkdir | Defer; namei overlay + archive/default-rootfs tests |
| PHX-092 | [`87dba3ac7`](https://github.com/PhoenixKernel/linux/commit/87dba3ac73f4343c35ad549e96226a9acd0f8bf4) | do_symlinkat / ksys_symlink | Defer; namei overlay + archive symlink tests |
| PHX-093 | [`883790cd7`](https://github.com/PhoenixKernel/linux/commit/883790cd7e1c4a16aac817f0140d21caf5fa3f16) | do_mknodat / ksys_mknod | Defer; namei overlay + console/device-node tests |
| PHX-094 | [`aa2f2ef1b`](https://github.com/PhoenixKernel/linux/commit/aa2f2ef1b7162aac31ce4451781771eb24b15b21) | do_linkat / ksys_link | Defer; namei overlay + archive hardlink tests |

### Key findings and validation boundaries

- **085/087:** preserve mount-aware permission checks, chroot capability/LSM
  checks, cwd/root lookup and retry cleanup. Both touch **SUSFS-sealed
  `fs/open.c`**; open redirect must remain intact. This is filesystem-root/cwd
  maintenance, not privilege bypass or root-filesystem/layout policy changes.
- **086 is not s390-only.** Generic write and compiled initramfs/ramdisk paths
  are affected. Existing fd-position handling, `vfs_write`, copy/permission
  checks, MAX_RW_COUNT and xwrite retry/short-write behavior remain.
- **088 has a real PHX-012 dependency:** current `do_unlinkat` is static and
  takes a user pathname; the wrapper needs the global `struct filename *`
  interface. A text-PASS fixture **without 012 still has incompatible source
  interfaces**. 012 remains pending with its own filename-lifetime/ESTALE and
  SUSFS provenance obligations. 013 is not required. Do not use text success
  to approve or silently force 012.
- **089 is UML/hostfs-only**, without phone runtime benefit. But 090 makes VFS
  `do_rmdir` global, colliding with the old built-in HOSTFS global name.
  Retain 089/equivalent resolution when supporting that UML configuration.
- **090–094:** preserve existing `vfs_*2` mount-aware backends, security and
  capability checks, umask/ACL, device encoding, link flags/delegations, ESTALE
  retry and reference cleanup. Touch **SUSFS-sealed `fs/namei.c`**. Add narrow
  explicit later overlays/check support if approved; never replace original
  seals. Coordinate any jointly approved 012/067 or other namei changes.
- All boot path strings/modes/device numbers, ownership/timestamps, root/cwd
  sequencing and archive hardlink/symlink argument order remain. `/dev/console`
  creation and initial-root/initramfs cleanup still need real boot validation.
- Only **089 passes unmodified standalone/ordered** on current source. All ten
  pass in a scratch chain after adapted 082 + 083 + 084 + 012. These fixtures
  approve/apply none of those prerequisites to Electro.
- **Nine independent context adaptations** also pass generated-patch/exact
  source replay. On ARM64, only 088 needs the 012 interface; the other supplied
  declaration/boot contexts must not force the entire pending cleanup chain.
  090 additionally needs 089 for built-in UML HOSTFS, not ARM64 runtime.
- **Seven moved bodies are byte-identical**; existing rmdir body/hostfs rename,
  native-to-inline forwarding, types/prototypes, token-normalized implementation
  inverse and boot/s390 callee-only changes pass source guards. `unsigned` and
  `unsigned int` are equivalent mknodat argument spellings; trace metadata type
  spelling can change. Existing ftruncate header helper stays intact.
- `ksys_*` names here retain **user-pointer/address-limit conventions**. They
  do not implement the future kernel-pointer/VFS migrations mentioned in donor
  messages or establish faster I/O, new security fixes or permission bypasses.
- Static checked-in profile enables BLK_DEV_INITRD/BLK_DEV_RAM/KSU LSM/SELinux;
  compilation gates do not prove classic initrd execution on this phone.
- Other affected-path JSON: F2FS staged-review inventory records `fs/open.c`
  as outside its approved donor feature scope, not a new active implementation
  seal. That historical decision is unchanged.
- **No target build, newly resolved config, boot/device/UML/ABI/performance
  test, production source/config edit, commit, push or CI.**

### Detailed findings

### PHX-085 — `5a45cea3e3e3b8d1afa7d83751202ccf069a4882`

- **Changes:** Extract global internal ksys_chroot, retain syscall wrapper and redirect devtmpfs/root/initrd chroot callers.
- **Electro finding:** Current body uses mount-aware inode_permission2, user_path_at with directory/follow flags, CAP_SYS_CHROOT in current user namespace, security_path_chroot, set_fs_root, path_put and ESTALE retry. All remain byte-identical in scratch. No root-privilege bypass or direct kern_path conversion: filename remains __user and old address-limit assumptions remain. Supplied boot/header context expects pending082-084. fs/open.c is SUSFS-sealed and its open-redirect backend is preserved by inverse-source checks; this is filesystem-root/cwd boot maintenance, not a filesystem-layout change.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Dependencies listed are supplied-donor context only. Independent scratch adaptation applies with current mount/dup calls untouched: retain donor implementation/devtmpfs rename, append prototype preserving existing ftruncate helper and rename only current boot chroot callees. No mount/umount/dup semantic prerequisite.
- **Before implementation:** Add narrow later SUSFS fs/open.c overlay/source validation support if approved; do not overwrite original seal or alter open redirect/KSU integration. Target-build and boot-test root/cwd handoff, supported initrd/devtmpfs variants, CAP_SYS_CHROOT/user-namespace and LSM denial, ENOTDIR/lookup failures, ESTALE and path release. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-086 — `2cd6f012250b1396b29c55d77a2addaaa0035a37`

- **Changes:** Extract global internal ssize_t ksys_write, retain native syscall wrapper and redirect initramfs/ramdisk plus s390 compat write callers.
- **Electro finding:** Generic ARM64-relevant change despite its s390 file: native write and compiled initramfs/ramdisk code are affected. fdget_pos, file_pos_read/write, vfs_write and fdput_pos body remain byte-identical. Lower access_ok, rw_verify_area/LSM, MAX_RW_COUNT, freeze/accounting/fsnotify and short-write behavior remain. xwrite EINTR/EAGAIN/partial-write loop and s390 signed-count guard are unchanged. This is not a kernel_write/filp_open migration, new throughput algorithm or removal of __user/address-limit conventions.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Donor fails only syscall-header context. Independent scratch adaptation simply appends exact prototype preserving current helpers; all other donor files apply unmodified. No chroot/mount helper semantic dependency; do not classify entire commit as s390-only.
- **Before implementation:** Target-build native/AArch32 write and active initramfs/ramdisk paths; test file-position serialization, short/zero writes, EINTR/EAGAIN, EFAULT, fd/permission failures, MAX_RW_COUNT and archive extraction. Validate s390 compat signed-count ABI separately if broad architecture coverage is claimed. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-087 — `3e74eb7c9639cb7cbca333d1f45dd80ec86d2984`

- **Changes:** Extract global internal ksys_chdir, retain native syscall wrapper and redirect devtmpfs/root/initrd cwd callers.
- **Electro finding:** Original directory/follow lookup, mount-aware inode_permission2(MAY_EXEC|MAY_CHDIR), set_fs_pwd, path_put and ESTALE retry remain byte-identical; fchdir and open redirect remain unchanged. Boot path strings and ordering relative to chroot/mount/dup are retained. Helper still accepts __user filename; no new kernel-path or permission shortcut. fs/open.c immutable SUSFS seal requires later overlay if approved.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Supplied header/devtmpfs/initrd context expects preceding helpers. Independent adaptation relocates prototype and changes only current devtmpfs/initrd chdir callees; other donor changes apply. Earlier mount/dup/chroot/write cleanups are not semantic prerequisites.
- **Before implementation:** Coordinate SUSFS fs/open.c overlay/check support with085 if jointly approved; preserve original seal and open redirect. Target-build and test boot root/cwd transitions, directory search permissions/LSM, bad paths/pointers, symlink lookup, ENOTDIR, ESTALE retry and path cleanup; cover supported devtmpfs/initrd variants. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-088 — `602909556ba18e5912c297b072aafc8a231fc02b`

- **Changes:** Add inline ksys_unlink forwarding through do_unlinkat(AT_FDCWD, getname(pathname)); redirect boot cleanup/create_dev callers.
- **Electro finding:** REAL interface prerequisite: Electro still has static do_unlinkat(int,const char __user *), but this wrapper declares/calls external do_unlinkat(int,struct filename *). PHX-012 changes both linkage and filename ownership/interface. Donor text passes after preceding boot helpers even without012, but that fixture has incompatible declaration/definition: text PASS is not build compatibility. After012, new wrapper exactly matches existing native unlink forwarding. getname is not getname_kernel; temporary user-pointer/address-limit convention remains.012 filename lifetime/ESTALE changes are inherited, not introduced by088. Initramfs cleanup/initrd image/dev-node removal arguments stay unchanged.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay after012 (required interface). Text-only PASS without012 on intermediate boot-helper base was also demonstrated, but old static/char-pointer do_unlinkat remains incompatible; not build proof. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** PHX-012 is semantic/linkage/type prerequisite, not just context, and remains pending with its own SUSFS overlay obligations. PHX-013 coredump cleanup is not required. With012 alone, independent header-context adaptation and the remaining unmodified088 files pass scratch replay; no need to force085-087.
- **Before implementation:** Require explicit approval/recheck of012, filename ownership/error-pointer/ESTALE lifetime handling and namei SUSFS overlay/check chain. Do not silently promote static do_unlinkat or pass struct filename to the old char-pointer implementation. Target-build and boot-test archive type replacement/clean_rootfs, initrd image and /dev/ram cleanup, create_dev unlink/mknod sequence, lookup/LSM denial, invalid pointers, ESTALE and reference cleanup. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-089 — `14850caeaf6f7255de1cf8825f348a6f5f9c685d`

- **Changes:** Rename hostfs do_rmdir prototype, definition and caller to hostfs_do_rmdir.
- **Electro finding:** UML-only HOSTFS is not part of the ARM64 target. All three changes are rename-only and apply independently. However090 globalizes VFS do_rmdir while hostfs_user.c currently defines another global do_rmdir with a different signature.089 prevents duplicate symbol for built-in UML HOSTFS. Thus no phone runtime benefit, but retain this portability pairing when assessing090 across the whole kernel tree. No UML build/link was run.
- **Check:** PASS standalone and submitted-order donor. Hostfs three-file rename-only guard PASS. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Standalone independent rename. Conditional prerequisite for090 when HOSTFS is built into a UML kernel; not an ARM64 runtime dependency and not blanket permission to enable HOSTFS or skip portability checks.
- **Before implementation:** Recommend skip as a standalone phone improvement. If090 is approved for cross-architecture portability, keep089 or an equivalent explicit collision resolution and validate UML HOSTFS built-in/module configurations; preserve host-side rmdir errors and caller cleanup. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-090 — `c1a33b9690bfe49a5c351edd545f777a8faba3ca`

- **Changes:** Make existing do_rmdir globally visible, declare it and add inline ksys_rmdir; redirect two initramfs cleanup callers.
- **Electro finding:** Existing do_rmdir implementation is byte-identical; only static linkage is removed. AT_FDCWD forwarding equals current native rmdir. Filename lookup, dot/root checks, mnt_want_write, locking, security_path_rmdir, vendor vfs_rmdir2(path.mnt,...), ESTALE and reference cleanup stay. fs/namei.c is SUSFS-sealed. Making do_rmdir global also requires resolving hostfs same-symbol collision for built-in UML HOSTFS (089), though HOSTFS is unavailable in the ARM64 profile. No EXPORT_SYMBOL is added.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** 012/088 are supplied internal-header/inline-wrapper/initramfs context, not semantic requirements of rmdir. Independent context adaptation passes on current ARM64 source without012/088.089 is additionally conditional for built-in UML HOSTFS; preserve that portability pairing if supporting it.
- **Before implementation:** Add explicit later namei SUSFS overlay/check support without resealing; coordinate other approved namei overlays. Target-build and boot-test initramfs cleanup, nonempty/busy/dot/root/readonly directories, permission/LSM denial, ESTALE and reference/lock cleanup; test UML HOSTFS collision resolution separately if supported. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-091 — `0e35e7fc83159497861d078a7469c311c49e8d25`

- **Changes:** Extract global internal do_mkdirat and inline ksys_mkdir; keep syscall wrappers and redirect initrd/initramfs/default-rootfs directory creation.
- **Electro finding:** Moved body remains byte-identical: user_path_create with LOOKUP_DIRECTORY, ACL-sensitive umask, security_path_mkdir, mount-aware vfs_mkdir2, done_path_create and ESTALE retry. Legacy mkdir still uses AT_FDCWD. All existing path/mode casts, /dev and staging /root creation, /old initrd directory, ownership/mode/mtime ordering remain. Namei SUSFS hooks/backends are unchanged outside extraction. No new filesystem or on-disk feature.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Supplied declaration/header/initrd context expects012/090/087. Independent relocation of added declarations plus current initrd mkdir callee rename passes without those cleanups; no mkdir semantic dependency on rmdir/chdir/unlink refactors.
- **Before implementation:** Scope explicit later namei SUSFS overlay/check support; preserve original seal and vendor mount-aware VFS. Target-build and test unpacked archive directories/default_rootfs/initrd, mode/umask/ACL, ownership/mtime ordering, existing path/type conflicts, EROFS, permission/LSM denial, ESTALE and create cleanup. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-092 — `87dba3ac73f4343c35ad549e96226a9acd0f8bf4`

- **Changes:** Extract global internal do_symlinkat and inline ksys_symlink; keep native entry points and redirect initramfs symlink creation.
- **Electro finding:** Both symlink pointers remain __user. Original getname(oldname), target-directory lookup/create, security_path_symlink, vendor vfs_symlink2(path.mnt,...), done_path_create, putname and ESTALE retry remain byte-identical. Legacy symlink and new wrapper both use AT_FDCWD. Initramfs target/path pointer order, body termination, lchown and timestamp ordering are unchanged. No new symlink-following policy or kernel-string API.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Supplied internal/header context expects preceding declarations/ksys_mkdir. Independent declaration-context adaptation passes without them; no functional dependency on unlink/rmdir/mkdir cleanup.
- **Before implementation:** Use explicit later namei SUSFS overlay/check chain without resealing. Target-build and test archive symlink targets/path order, long/empty/bad strings and user-copy errors, ownership/mtime, EEXIST/EROFS, permission/LSM denial, ESTALE and getname/path cleanup; preserve open redirect/SUSFS lookup behavior. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-093 — `883790cd7e1c4a16aac817f0140d21caf5fa3f16`

- **Changes:** Extract global internal do_mknodat and inline ksys_mknod; retain syscall wrappers and redirect create_dev/archive/default-console node creation.
- **Electro finding:** Moved body is byte-identical: may_mknod validation, ACL/umask, security_path_mknod, file/char/block/FIFO/socket branching, vendor vfs_create2/vfs_mknod2 and new_decode_dev, IMA hook and ESTALE cleanup remain. Existing CAP_MKNOD/device-cgroup/inode-security checks are in unchanged lower backends. unsigned and unsigned int are equivalent C types; spelling in mknodat syscall metadata can change, not argument width. /dev/console device5:1, encoded devices, modes and initramfs ownership/mtime ordering remain. Namei SUSFS seal still applies.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Supplied header/internal/create_dev context depends on earlier wrappers/declarations. Independent context adaptation preserves current sys_unlink call in create_dev and only changes mknod callee; no semantic prerequisite on unlink or the other creation-helper refactors.
- **Before implementation:** Use explicit later namei SUSFS overlay/check support and retain vendor vfs_*2/device-security paths. Target-build and boot-test default-rootfs /dev/console and root-device creation, archive file/node types and device encoding, permissions/CAP_MKNOD/cgroup/LSM/IMA, umask/ACL, invalid modes/devices, ESTALE and allocation/reference cleanup. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

### PHX-094 — `aa2f2ef1b7162aac31ce4451781771eb24b15b21`

- **Changes:** Extract global internal do_linkat and inline ksys_link; retain link/linkat entry points and redirect initramfs hardlink creation.
- **Electro finding:** Original linkat body stays byte-identical, including allowed flags, AT_EMPTY_PATH capability check, symlink-follow choice, cross-mount rejection, may_linkat, security_path_link, vendor vfs_link2 with mount, delegated-inode handling, ESTALE and path cleanup. Legacy link and ksys_link both pass AT_FDCWD for old/new dirfds and flags0. Archive hardlink identity lookup, old/new pathname order and maybe_link negative/success result mapping remain. User pointers remain; no vfs_link/kernel-pointer conversion or new hardlink policy.
- **Check:** FAIL standalone and submitted-order donor on current source. PASS unmodified in full scratch chain after adapted082+083+084+012 and preceding B010 donors. PASS separately generated context adaptation with exact git-apply/source replay on current source, without forcing other pending helper changes. Reverse FAIL. No target compilation, boot/device/UML runtime or performance tests.
- **Dependencies/scope:** Supplied internal/header context expects earlier declarations/ksys_mknod. Independent context relocation passes without those cleanups; no functional link-helper dependency on mknod/symlink/rmdir/unlink refactors.
- **Before implementation:** Use explicit later namei SUSFS overlay/check chain, coordinated with any approved012/067 or090-093 changes; never overwrite original seal. Target-build and boot-test cpio hardlinks, pathname order/inode identity, link counts, AT_EMPTY_PATH and symlink flags, capability/protected-hardlink/LSM denial, EXDEV, delegation/ESTALE and path/refcount cleanup. Recheck current integrated source and separately approved changes. Review recommendations do not approve implementation, activation, an entire dependency series, or publication. Helper names retain user-pointer/address-limit semantics; no new EXPORT_SYMBOL API.
- **Decision/application:** pending / not applied.

## PHX-B011 — permission/ownership, close/open and generic I/O helpers

Ten full diffs read; API per-file additions/deletions checked; full SHAs new
against 94 prior ledger entries. All **22 affected and three close-caller audit
files** byte-match published `c6de0ddbe7e159a84c4906cbbf4f2c9138521c13`
and remain unchanged. All recommendations still await explicit decisions.

| Stable ID | Donor | Helper/change | Recommendation |
| --- | --- | --- | --- |
| PHX-095 | [`04e856639`](https://github.com/PhoenixKernel/linux/commit/04e8566395326ec650285318ca083cec91e8e829) | ksys_fchmod / do_fchmodat / ksys_chmod | Optional; SUSFS open overlay + boot metadata tests |
| PHX-096 | [`a807001f1`](https://github.com/PhoenixKernel/linux/commit/a807001f131d11bc7c3413f9e5cb7d52560f46b1) | do_faccessat / ksys_access | Optional; preserve real-ID/vendor access logic + /init tests |
| PHX-097 | [`e9718e914`](https://github.com/PhoenixKernel/linux/commit/e9718e9144a6c20c68858c75c17a3d327d4e5050) | do_fchownat / ksys_fchown / ksys_(l)chown | Optional; active uid16/ownership validation + overlay |
| PHX-098 | [`7fe82662b`](https://github.com/PhoenixKernel/linux/commit/7fe82662bda4dff3ac0c7752bc8fc604048ff7fc) | ksys_ftruncate | Skip reapplication: already functionally integrated |
| PHX-099 | [`778c5d736`](https://github.com/PhoenixKernel/linux/commit/778c5d7369fe22bacc1dc8e4e17fd14b61910bbb) | ksys_close + export changes | Defer: raw restart errors + module export contract change |
| PHX-100 | [`84de2f852`](https://github.com/PhoenixKernel/linux/commit/84de2f852aaffd58f516a9822127ff6c421989d5) | ksys_open | Optional; native flags/OPEN_REDIRECT + console tests |
| PHX-101 | [`59bf3184b`](https://github.com/PhoenixKernel/linux/commit/59bf3184bc05f7a7de9fe6572005295f484011f1) | ksys_getdents64 | Optional; SUSFS readdir overlay + enumeration tests |
| PHX-102 | [`3216d7c74`](https://github.com/PhoenixKernel/linux/commit/3216d7c746cdf744e6cd2e45ae1d4c70725e9443) | ksys_ioctl | Optional; native/compat ioctl and boot/LSM tests |
| PHX-103 | [`09fa518a2`](https://github.com/PhoenixKernel/linux/commit/09fa518a2f5bdf3905cdcf2861c49f0536c04467) | ksys_lseek | Optional; compat offsets and ramdisk probes |
| PHX-104 | [`865b2f37f`](https://github.com/PhoenixKernel/linux/commit/865b2f37f73e8034e3353fdbed65e30c3dac6c6b) | ksys_read | Optional; generic read/KSU/boot tests |

### Key findings and scope boundaries

- **098 is already functionally integrated in all ten paths:** global
  `do_sys_ftruncate`, **both** declarations, exact inline wrapper, all seven
  architecture call replacements and initramfs call. New SHA is not a ledger
  duplicate, but no implementation is missing. **Skip reapplication**; do not
  add duplicate helpers or undo current code to follow the donor order.
  Presence in the baseline is not a newly applied/approved review action.
- **095** must keep the already-integrated `ksys_ftruncate` archive call,
  despite donor context expecting `sys_ftruncate`. Permission/metadata order
  remains. **096** preserves real-ID credential override/restoration and the
  vendor hidden-inode UID fence; `/init` probe remains mode0. **097** preserves
  user-namespace IDs, -1/16-bit conversions, setid clearing and NOFOLLOW.
  It is ARM64/AArch32-relevant, **not merely s390 cleanup**.
- **099 is not a pure refactor.** It removes `EXPORT_SYMBOL(sys_close)` and
  adds `EXPORT_SYMBOL(__close_fd)`. Its helper returns raw ERESTARTSYS,
  ERESTARTNOINTR, ERESTARTNOHAND and ERESTART_RESTARTBLOCK, whereas native
  `sys_close` converts those to EINTR after fd removal. Native close's body
  stays unchanged, but migrated internal callers have a different contract.
  Audit returned/boolean-tested errors and never retry an already-closed fd.
- The donor leaves `sys_close` references in **incfs**, **goldfish sync**, and
  a conditional **TAS audio** path. Current incfs=y is built-in, so that call
  alone is **not evidence this target fails to link**. Module variants and
  external/vendor importers need audit, migration or explicit old-export
  retention. A scratch scope alternative retains the old export, but does
  **not** remove the raw-error difference. No option is approved or built.
- **100** matches native open's force_o_largefile/AT_FDCWD convention and
  preserves SUSFS OPEN_REDIRECT backend/retry handling and creat flags;
  compat open/openat are unchanged. **101** preserves `buf.sb`, `filldir64`
  SUSFS hidden-entry filtering, user record/copyout and fd-position handling.
- **102** retains security_file_ioctl/native dispatch; compat ioctl conversion
  stays unchanged. MD umbrella does not mean RAID is selected. **103** retains
  off_t/whence/overflow logic and compat slot19 forwarding; `_llseek` slot140
  remains unchanged. **104** retains generic vfs_read/position/stream and
  lower KSU/LSM paths; its write-helper context does not require adopting086.
- SUSFS-sealed **`fs/open.c`** is touched by095/096/097/099/100 and sealed
  **`fs/readdir.c`** by101. If approved, add narrow explicit later overlays and
  source-check support; **never overwrite historical seals**. 098 needs no edit.
  F2FS historical inventory records open/ioctl outside its selected donor
  feature scope, not new active implementation seals.
- All unmodified standalone/submitted-order and reverse checks fail.
  **Nine independent context adaptations pass**, as does ordered adapted
  replay skipping already-present098. Earlier pending helper changes are not
  forced. 099 still includes the donor behavior/export changes in these tests.
- **Nine extracted bodies are byte-identical**; argument types/wrappers,
  token-normalized implementation inverse, boot/legacy caller renames and
  preserved native close/backend/open-redirect/getdents hooks pass source checks.
- Helpers retain **user-pointer/address-limit conventions**. No kernel-buffer
  API conversion, faster I/O, new feature activation or exploit fix is proven.
- **No target build, newly resolved config, device/boot/module/ABI/performance
  test, production edit, commit, push or CI.**

### Detailed findings

### PHX-095 — `04e8566395326ec650285318ca083cec91e8e829`

- **Changes:** Extract ksys_fchmod/do_fchmodat and inline ksys_chmod; retain native entries and redirect three initramfs permission-setting calls.
- **Electro finding:** Both moved bodies are byte-identical. Existing fd audit/refcount, chmod_common mount write, security_path_chmod, notify_change2/delegation and path/ESTALE cleanup remain. Archive ownership-before-mode and mode/timestamp ordering stay. Donor initramfs hunk expects old sys_ftruncate, but current code already calls ksys_ftruncate (098 equivalent); preserve it, never roll it back. Header/internal/boot contexts also reflect pending earlier helpers. Touches SUSFS-sealed fs/open.c; open redirect backend remains unchanged.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. Moved bodies byte-identical, argument types/order/wrappers and token-normalized inverse implementation checks PASS. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** Supplied-donor contexts, not semantic prerequisites. Independent adaptation relocates new declarations and renames current initramfs fchmod/chmod calls, preserving already-integrated ftruncate interface and pending unrelated mkdir/mknod source.
- **Before implementation:** Scope narrow later fs/open.c SUSFS overlay/check support without replacing historical seal, coordinated with any approved085/087/096/097/099/100 changes. Target-build and test archive modes, fd/path chmod, ACL/umask/setid semantics, permission/LSM denial, read-only paths, ESTALE/delegation and fd/path cleanup; verify metadata ordering during boot. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-096 — `a807001f131d11bc7c3413f9e5cb7d52560f46b1`

- **Changes:** Extract do_faccessat and inline ksys_access; retain access/faccessat and redirect the /init existence check.
- **Electro finding:** Byte-identical access body preserves prepare_creds, real uid/gid fsids/capability override, non_rcu handling, override/revert/put credentials, vendor IS_VENDOR_HIDDEN uid fence, mount-aware inode_permission2, noexec/read-only checks and ESTALE cleanup. /init probe keeps mode0 and fallback to prepare_namespace. Donor expects earlier ksys_chdir context; standalone adaptation retains current native chdir instead. No access policy fix, new faccessat flags or trusted kernel-path API. fs/open.c SUSFS seal applies.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. Moved bodies byte-identical, argument types/order/wrappers and token-normalized inverse implementation checks PASS. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** 095/087 are text context only. Independent adaptation moves prototypes and updates only the expected chdir context line; existing access body and current chdir implementation are retained. No semantic dependency on chmod/chdir cleanup.
- **Before implementation:** Use narrow later fs/open.c SUSFS overlay/check chain, preserving original seal and vendor hidden-path behavior. Target-build and test real/effective UID/GID differences, capability override and credential restoration on all errors, vendor hidden paths, noexec/read-only mounts, lookup/LSM failures and /init-present/absent boot fallback. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-097 — `e9718e9144a6c20c68858c75c17a3d327d4e5050`

- **Changes:** Extract do_fchownat/ksys_fchown and inline ksys_chown/ksys_lchown; redirect initramfs, generic uid16 and s390 legacy ownership callers.
- **Electro finding:** Not s390-only: COMPAT selects HAVE_UID16 on ARM64; UID16/MULTIUSER default y, and AArch32 ownership slots use generic uid16 wrappers. Both moved bodies remain byte-identical. User-namespace UID/GID validation and -1 handling, privilege-bit clearing, security_path_chown/notify_change2, mount-aware file-write refs, NOFOLLOW/EMPTY_PATH and delegation/ESTALE paths remain. Legacy low2highuid/gid conversion is unchanged. Archive fchown/chmod and symlink lchown ordering remains; no ownership/privilege policy change. fs/open.c sealed.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. Moved bodies byte-identical, argument types/order/wrappers and token-normalized inverse implementation checks PASS. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** Only supplied declaration/boot context depends on earlier helpers. Independent prototype relocation and current initramfs ownership callee changes pass without them. PHX-059 credential-helper cleanup is not required; do not activate new UID16 configuration.
- **Before implementation:** Define later fs/open.c SUSFS overlay/check chain without resealing and preserve existing KSU/LSM/namespace behavior. Target-build and test native/AArch32 legacy ownership, 16-bit sentinel conversion, unmapped IDs/-1, symlink and empty-path flags, setid/capability clearing, archive metadata order, permission/LSM/read-only errors and ref/delegation cleanup. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-098 — `7fe82662bda4dff3ac0c7752bc8fc604048ff7fc`

- **Changes:** Globalize do_sys_ftruncate, declare it, add inline ksys_ftruncate and redirect six architecture files plus initramfs.
- **Electro finding:** FUNCTIONAL EQUIVALENT ALREADY PRESENT in all ten touched paths: do_sys_ftruncate is global, both internal/syscall header declarations exist, inline wrapper body matches donor and all seven architecture caller replacements plus initramfs ksys_ftruncate call are present. Full donor SHA is new to ledger, not a SHA duplicate, but there is no missing implementation to add. Original/reverse patch failure is not evidence of absence; contexts/formatting differ because equivalent work is integrated ahead of this donor order.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. Equivalent-postimage source audit PASS for all ten paths, including internal prototype, global definition, exact wrapper body and all changed call sites; no adaptation/reapplication needed.No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** No implementation/dependency work needed. Preserve existing helper/prototypes/callers; do not add duplicate definitions or undo existing code to replay historical donor sequence. Presence at baseline is distinct from a newly approved/applied Phoenix review action.
- **Before implementation:** Recommend skip reapplication. Reassess only if future source comparison shows an actual missing delta; no target/device proof is claimed from this equivalence audit. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-099 — `778c5d7369fe22bacc1dc8e4e17fd14b61910bbb`

- **Changes:** Add inline ksys_close using __close_fd; migrate selected internal callers, export __close_fd and remove sys_close export.
- **Electro finding:** NOT a pure refactor: internal helper returns raw __close_fd errors; sys_close rewrites four ERESTART* values to EINTR after descriptor removal. Native close body/entry and fd backend remain unchanged, but migrated callers have different error contract. Donor also removes EXPORT_SYMBOL(sys_close) and adds EXPORT_SYMBOL(__close_fd), changing module-facing ABI. Remaining donor-unmigrated callers include incfs, goldfish sync and conditional TAS audio. Current INCREMENTAL_FS=y is built-in, so its call alone is not a target link failure; module variants/external importers require audit. Return-sensitive autofs and ramdisk callers need restart/close-once review. fs/open.c seal applies.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** Only failing current donor context is ramdisk ksys_unlink from088; existing ftruncate header already supports the new stub. Independent boot-context adaptation passes without088. Explicitly choose export compatibility and caller error policy: scratch old-export-retaining option preserves sys_close export but still leaves raw restart errors for migrated callers. No option is approved.
- **Before implementation:** Require explicit scope for removing sys_close export versus retaining compatibility; inventory/modpost/load-test in-tree module variants and out-of-tree/vendor imports. __close_fd export addition is also module API scope. Audit returned/boolean-tested close results and never retry a descriptor already removed from table. Fault-test flush ERESTART* versus EINTR, EBADF and ordinary errors; preserve native close ABI and close_range backend. If approved, add narrow fs/open.c SUSFS overlay/check support and boot-test archive/ramdisk cleanup plus relevant autofs/binfmt_misc paths. No current target failure or KSU break is asserted without module/runtime evidence. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-100 — `84de2f852aaffd58f516a9822127ff6c421989d5`

- **Changes:** Add inline ksys_open using native force_o_largefile/do_sys_open convention; redirect creat and boot/archive opens.
- **Electro finding:** Wrapper token-matches current native open: same force_o_largefile/O_LARGEFILE and do_sys_open(AT_FDCWD,...) call. creat flags remain O_CREAT|O_WRONLY|O_TRUNC. do_sys_open including SUSFS OPEN_REDIRECT filename/retry/fd cleanup remains byte-identical; compat open/openat stay unchanged. Same console/archive/ramdisk/root-device paths and flags. No getname_kernel/VFS migration, new trusted-pointer API or large-file bug fix. fs/open.c seal requires later overlay.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** close/dup/ownership helpers are supplied boot/header context only. Independent declaration relocation and current boot open callee replacements pass without those pending changes. __close_fd export/API change099 is not needed for open semantics.
- **Before implementation:** Use explicit later fs/open.c SUSFS overlay/check chain; preserve OPEN_REDIRECT/NoMount/KSU lower integration and compat open flag differences. Target-build and boot-test initial console, archive open/truncate/hardlink behavior, initrd image and root-device handling, O_LARGEFILE, fd exhaustion, bad pointers, permission/LSM and redirect retry/fd cleanup. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-101 — `59bf3184bc05f7a7de9fe6572005295f484011f1`

- **Changes:** Extract ksys_getdents64, keep native wrapper and redirect two initramfs clean_rootfs directory reads.
- **Electro finding:** Moved body byte-identical with current SUSFS additions: buf.sb assignment, filldir64 hidden-inode filter, iterate_dir, fd-position locking, record/offset/copyout and error handling remain. Compat directory implementations are unchanged. Directory enumeration and cleanup traversal policy are not fixed/optimized by this extraction. fs/readdir.c immutable SUSFS seal requires a later overlay if approved.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. Moved bodies byte-identical, argument types/order/wrappers and token-normalized inverse implementation checks PASS. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** Supplied helper declarations/close caller context only. Independent header relocation and current getdents64 callee changes pass without chmod/chown/close cleanup; no module export099 prerequisite.
- **Before implementation:** Add narrow explicit later fs/readdir.c SUSFS overlay/check support; never replace original seal or lose buf.sb/filldir64 hidden-path handling. Target-build and test native directory records, offsets/short buffers/EFAULT/interruption, fd positions and cleanup traversal; verify SUSFS-hidden entries and unchanged compat enumeration on device. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-102 — `3216d7c746cdf744e6cd2e45ae1d4c70725e9443`

- **Changes:** Extract ksys_ioctl, retain native wrapper and redirect boot floppy/initrd/ramdisk/MD ioctl calls.
- **Electro finding:** Moved body byte-identical: fdget, security_file_ioctl, do_vfs_ioctl and fdput. Native command/argument words and boot request/result handling stay; compat ioctl marshalling is unchanged. User-pointer and address-limit assumptions remain; this is not a permission bypass or kernel-buffer ioctl API. MD=y is umbrella support, not evidence software RAID/BLK_DEV_MD is enabled. No new driver/RAID activation.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. Moved bodies byte-identical, argument types/order/wrappers and token-normalized inverse implementation checks PASS. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** Prior open/close/getdents names are context only. Independent exact prototype/callee adaptation passes without those pending helpers or099 export change. Historical F2FS review marks ioctl.c outside that donor feature scope, not a new implementation seal.
- **Before implementation:** Target-build and test native/compat ioctl dispatch, bad fd/pointers, command/argument width, LSM denial and supported ramdisk size/flush requests; test separately enabled RAID/floppy variants without activating them for this cleanup. Preserve existing driver error/cleanup paths. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-103 — `09fa518a2f5bdf3905cdcf2861c49f0536c04467`

- **Changes:** Extract off_t ksys_lseek, retain native/compat wrappers and redirect four ramdisk probe seeks.
- **Electro finding:** Moved native body byte-identical: fdget_pos, whence bounds, vfs_llseek, off_t overflow handling and fdput_pos. Compat lseek changes only callee; AArch32 slot19 routes compat_sys_lseek, while slot140 _llseek path stays unchanged. Same probe offsets and return handling. No new large-offset ABI or file-position fix.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. Moved bodies byte-identical, argument types/order/wrappers and token-normalized inverse implementation checks PASS. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** Only syscall-header declaration context conflicts. Independent relocation passes; no ioctl/getdents/chown semantic dependency. Do not conflate native off_t helper with unchanged split-offset llseek ABI.
- **Before implementation:** Target-build and test native/AArch32 lseek and unchanged _llseek, signed/large offsets and overflow, invalid whence/fd, ESPIPE, shared file-position serialization and ramdisk image probe offsets. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

### PHX-104 — `865b2f37f73e8034e3353fdbed65e30c3dac6c6b`

- **Changes:** Extract ssize_t ksys_read, retain native wrapper and redirect boot ramdisk/floppy plus s390 compat read calls.
- **Electro finding:** Generic ARM64-relevant read change, not s390-only. Byte-identical fdget_pos/file_pos_read/vfs_read/file_pos_write/fdput_pos body preserves stream/position semantics. Lower user-copy/permission/rw_verify_area/accounting and KSU LSM hooks remain. s390 signed-count guard, compression-fill EOF/errors and current boot return handling stay. No kernel_read migration, new I/O algorithm or measured speed gain.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated context adaptation with git-apply check/exact-source replay; PASS ordered adapted095-104 replay skipping already-equivalent098. Moved bodies byte-identical, argument types/order/wrappers and token-normalized inverse implementation checks PASS. No target build, boot/device/module-load/ABI/performance tests.
- **Dependencies/scope:** PHX-086 is donor write-helper context, not a read-helper semantic requirement. Independent adaptation retains current write syscall context, relocates read prototype and renames only current read callers. No forced close-export/open/ioctl/lseek dependency.
- **Before implementation:** Target-build and test native/AArch32 read, EOF/short/zero/error results, EFAULT/permissions/LSM/KSU hooks, shared file positions and streams, compressed ramdisk fill and image detection; cover s390 signed-count behavior separately if broad architecture support is claimed. Recheck current integrated source and independently approved changes. Recommendations are not approvals or authorization to force a prerequisite chain, change feature configuration, implement, publish or run CI. Source preservation checks are not target/runtime proof.
- **Decision/application:** pending / no new application by this review.

## PHX-B012 — sync, namespace/session and file/MM helpers

All ten full donor diffs read and API per-file counts verified. Full SHAs are
new against 104 prior entries; current implementations checked separately.
All **39 affected and four supporting files** byte-match published
`c6de0ddbe7e159a84c4906cbbf4f2c9138521c13` and remain unchanged.

| Stable ID | Donor | Helper/change | Recommendation |
| --- | --- | --- | --- |
| PHX-105 | [`f3f6f3147`](https://github.com/PhoenixKernel/linux/commit/f3f6f3147458fbfe04cf7edff00efbe13214a2ec) | ksys_sync | Optional; not a suspend speedup (skip-sync stays) |
| PHX-106 | [`8f8f6622a`](https://github.com/PhoenixKernel/linux/commit/8f8f6622aca668fd14719096e7b859578766f688) | ksys_unshare | Defer until BPF fork overlay + namespace/boot tests |
| PHX-107 | [`75fe33594`](https://github.com/PhoenixKernel/linux/commit/75fe33594c0b923986919624bfe3749f705b0db7) | ksys_setsid | Optional; SUSFS sys.c overlay + session/boot tests |
| PHX-108 | [`84f13219a`](https://github.com/PhoenixKernel/linux/commit/84f13219a87f99c4380642619006aaf1d63280ee) | ksys_sync_file_range | Optional; not fsync/metadata durability |
| PHX-109 | [`abfe91f40`](https://github.com/PhoenixKernel/linux/commit/abfe91f4085d0338042de29538d787fb84f405f0) | ksys_truncate (pathname) | Defer: limited ARM64 benefit; SUSFS open overlay |
| PHX-110 | [`7cb890611`](https://github.com/PhoenixKernel/linux/commit/7cb8906110f4f799cff7688328efebf76c36be51) | ksys_pread64 / ksys_pwrite64 | Optional; preserve current write/iov_shorten |
| PHX-111 | [`17aeadc13`](https://github.com/PhoenixKernel/linux/commit/17aeadc134854f10945237475da20aac58d273c4) | ksys_fallocate | Optional; SUSFS open overlay; no allocation feature activation |
| PHX-112 | [`a5f88708a`](https://github.com/PhoenixKernel/linux/commit/a5f88708a87b5112590d15df8d93437909fb3685) | ksys_fadvise64_64 | Explicit disabled-config errno + PPC32 width scope/tests |
| PHX-113 | [`c718143ab`](https://github.com/PhoenixKernel/linux/commit/c718143abe34353be29c8807887af3bcd543cb97) | ksys_mmap_pgoff (MMU + NOMMU) | Optional; directly ARM64-relevant MMU/compat validation |
| PHX-114 | [`a64e52fff`](https://github.com/PhoenixKernel/linux/commit/a64e52fff7cae8a1f4929360aa8ab26bb3898313) | ksys_readahead | Optional; no cache/readahead algorithm tuning |

### Key findings and boundaries

- **105:** same sync work/order, with return0 moved into native wrapper.
  `SUSPEND_SKIP_SYNC=y` remains: **not a suspend speedup**. Sysrq maintenance
  is relevant; hibernation is not activated, and freezer/log policy stays.
- **106:** unshare flags, namespace/fs/fd/cred construction, locks, perf notice
  and rollback remain. Fork file matches immutable **BPF after-image**; use an
  explicit later overlay/delta/check chain if approved, never reseal. Clone3,
  BPF and KSU/NoMount behavior still need runtime validation. No new namespaces.
- **107/109/111:** touch immutable **SUSFS kernel/sys.c or fs/open.c** seals.
  Use narrow later overlays/check support without rewriting historical records.
  BPF excluded-path references for sys.c/readahead.c are **not** seals. F2FS
  historical open/sync inventory exclusions are not new implementation seals.
- **108:** existing range/flag/wait ordering is preserved. Range sync does not
  provide fsync/metadata crash-consistency guarantees; no durability policy fix.
- **109 is not 098:** this is still-static **pathname** truncate, unlike the
  already-integrated fd-ftruncate wrapper. New global helper has limited direct
  ARM64 benefit because native/compat truncate already use the underlying body.
- **110:** donor context assumes ksys_write and lacks current `iov_shorten`
  between pwrite64 and iterator code. Scratch adaptation preserves **both full
  current write and iov_shorten**, with only context/callee changes; no086 forced.
- **112 has two nontrivial portability distinctions:**
  - With ADVISE_SYSCALLS=n, new C helper stub returns **EINVAL**, not the old
    absent syscall's **ENOSYS**. Native/unchanged ARM64 assembly NI routes stay.
  - PPC32 `ppc_fadvise64_64` no longer narrows merged length through
    `sys_fadvise64(size_t len)` before `loff_t`. Width model: `0x100001000`
    previously narrows to4096, new helper receives4294971392. This is not an
    ARM64 bug/performance fix or PPC runtime validation.
- **113 directly changes ARM64 native mmap forwarding**, not just other arches.
  Alignment/page units, flags/file/hugepage/ref/error handling remain; both MMU
  and NOMMU source bodies checked. No MM/layout/MGLRU feature is added.
- ARM64 AArch32 assembly wrappers keep original syscall targets and split-word
  shuffles for positional I/O/range sync/advice/readahead/fallocate/mmap2. Syscall
  wrappers remain; no entry point removed. Current x86 sys32 declarations are
  preserved rather than forcing pending macro conversions.
- **114 is helper maintenance, not cache tuning**. Existing range arithmetic,
  do_readahead and actual cache algorithm remain; inherited edge cases are not
  newly fixed. **111** does not activate F2FS/ext4 allocation/checkpoint features.
- All original standalone/submitted-order/reverse checks fail textually.
  **Ten independent adaptations and ordered adapted replay pass**, without
  prior pending helpers. Ten extracted bodies byte-identical; sync side-effect
  block byte-identical except terminal return0 moved to wrapper; truncate body
  unchanged. Types/wrappers, normalized inverse implementations and caller
  argument/word assembly pass source guards, not universal semantic proof.
- No export additions/removals in this batch. No target build/resolved config,
  device/boot/suspend/ABI/PPC/NOMMU/performance test, implementation, feature
  activation, commit, push or CI. All recommendations remain pending.

### Detailed findings

### PHX-105 — `f3f6f3147458fbfe04cf7edff00efbe13214a2ec`

- **Changes:** Extract void ksys_sync, keep syscall returning zero and redirect sysrq/power/SPARC callers.
- **Electro finding:** Sync side-effect block is byte-identical; only final return0 moves into native wrapper. Same flusher/inode/filesystem/block-device wait order, laptop completion and power/reset tracing/logging remain. CONFIG_SUSPEND_SKIP_SYNC=y means pre-suspend sync remains compiled out in this profile, so this is NOT a suspend-latency improvement. MAGIC_SYSRQ=y makes sync/reset maintenance relevant; hibernation is not enabled. No new durability policy, asynchronous sync or checkpoint feature.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Sync side-effect block byte-identical; return0 preserved in native wrapper. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Only header context conflicts. Independent prototype relocation passes with original remaining donor files. No read/lseek/ioctl semantic prerequisite or need to alter SUSPEND_SKIP_SYNC/freezer timing.
- **Before implementation:** Target-build and test native sync/sysrq reset ordering and writeback under load; test enabled power variants separately without activating hibernation. Preserve skip-sync policy, suspend tracing/logs and current freezer timeout. No performance/durability claim from helper extraction. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-106 — `8f8f6622aca668fd14719096e7b859578766f688`

- **Changes:** Extract global internal ksys_unshare; keep syscall and redirect devtmpfs/initrd unshare calls.
- **Electro finding:** Original body byte-identical: dependent flag expansion, check_unshare_flags, fs/files/cred/ns allocation, namespace switching, sysvsem/IPC cleanup, task/fs locking, credential commit, perf_event_namespaces and all rollback remain. CLONE_NEWNS and CLONE_FS|CLONE_FILES boot requests/order unchanged. Does not enable USER_NS/PID_NS or alter KSU/NoMount namespace policy. kernel/fork.c exactly matches the BPF after-image seal; clone3/BPF/KSU code outside extraction is preserved by inverse-file check, not runtime validation.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Supplied header/boot contexts only. Independent prototype/current-callee adaptation passes without prior mount/open/dup/read/sync cleanup. The BPF fork provenance chain needs an explicit later delta/check, never a rewritten historical after-hash; coordinate any other approved fork overlay.
- **Before implementation:** If approved, add narrow later BPF fork.c overlay/delta and validation-chain support preserving original record and clone3/BPF/KSU behavior. Target-build and test allowed/rejected flags, shared fs/files, namespace/capability/LSM restrictions, allocation failures/rollback, perf namespace notification and devtmpfs/initrd handoff. Do not enable new namespace features. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-107 — `75fe33594c0b923986919624bfe3749f705b0db7`

- **Changes:** Extract int ksys_setsid, retain syscall and redirect initrd session creation.
- **Electro finding:** Moved body byte-identical: group/session leader checks, pid/tasklist locking, set_special_pids, controlling tty clearing, connector and autogroup notification remain. Initrd session call stays after root/cwd changes. No new session/tty policy or privilege feature. kernel/sys.c is SUSFS-sealed; spoofed uname and other integrations remain unchanged in inverse-source check.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Header/initrd helper names are context only. Independent prototype/callee adaptation passes without adopting those changes. BPF lists kernel/sys.c as excluded, not sealed; immutable SUSFS seal does apply.
- **Before implementation:** Use explicit narrow later SUSFS kernel/sys.c overlay/check support, never reseal or change uname-spoofing/root integrations. Target-build and test setsid EPERM/existing process-group cases, session/pid namespaces, controlling tty, connector/autogroup and supported initrd /linuxrc startup. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-108 — `84f13219a87f99c4380642619006aaf1d63280ee`

- **Changes:** Extract ksys_sync_file_range, retain both range-sync syscall forms and redirect six architecture C wrappers.
- **Electro finding:** Moved body byte-identical: flag/range/overflow checks, zero-length-to-EOF behavior, fd/type checks, wait-before/write/wait-after ordering and cleanup remain. Split-word argument assembly preserved; current x86 sys32 declarations are retained rather than forcing donor COMPAT_SYSCALL context. ARM64 AArch32 assembly still branches sys_sync_file_range2, whose generic forwarding uses helper after extraction. This is not fsync/metadata durability and does not change writeback algorithms.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Earlier header helpers and x86 macro names are textual context, not functional prerequisites. Independent current-x86 callee/header adaptation passes; no requirement to approve earlier x86 ABI macro conversions.
- **Before implementation:** Target-build and test native/AArch32 range/flags/word-order, zero size, negative/wrapping/large ranges, fd/type failures and wait/write errors. Do not claim metadata/crash consistency equivalent to fsync or activate F2FS checkpoint/GC changes. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-109 — `abfe91f4085d0338042de29538d787fb84f405f0`

- **Changes:** Make do_sys_truncate global and add inline ksys_truncate; redirect six architecture files, including parisc truncate64 path.
- **Electro finding:** Unlike098 fd-ftruncate, this PATH-truncate helper is not already integrated: do_sys_truncate remains static and ksys_truncate absent. Its body stays byte-identical after visibility change, with current lookup/retry, mount-aware vfs_truncate/permission/delegation cleanup unchanged. New wrapper retains __user pathname. ARM64 native/compat truncate already call this body directly, so removed external C syscall crossings are mainly other architectures; limited direct phone benefit. fs/open.c immutable SUSFS seal applies.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Truncate body byte-identical; visibility-only implementation change. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** ksys_open header context and current x86 function names require adaptation only. No semantic open-helper dependency;109 is distinct from already-present098 and should not be falsely marked duplicate.
- **Before implementation:** Prefer defer for this target unless broader internal-call cleanup is desired. If approved, use narrow later SUSFS open.c overlay/check support without resealing. Target-build and test native/compat signed/large lengths, path/pointer/permission/read-only errors, leases/ESTALE and cleanup; validate non-ARM word assembly and parisc32/64 variants separately. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-110 — `7cb8906110f4f799cff7688328efebf76c36be51`

- **Changes:** Extract ksys_pread64 and ksys_pwrite64, retain native entries and redirect seven architecture C wrapper files.
- **Electro finding:** Both bodies byte-identical: negative-offset rejection, fd access, FMODE_PREAD/PWRITE, local position/vfs_read/write and fd cleanup remain; shared file position is not newly updated. Current ARM64 compat assembly word-combining/syscall targets stay unchanged. Donor expects prior ksys_write and omits current iov_shorten between pwrite64 and do_iter_readv_writev. Adaptation changes only those contexts, preserving full current write and vector helper; never delete current code to fit donor. No new positional I/O/large-file algorithm.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Header/write-helper/x86 declaration context only. Independent adaptation passes without086 or earlier x86 macro conversions, preserving iov_shorten in place. No pread/pwrite semantic dependency on sync/unshare/setsid.
- **Before implementation:** Retain current write/iov_shorten and lower KSU/LSM/VFS paths. Target-build and test native/AArch32 split offsets, negative/large positions, short I/O/EFAULT, access modes/ESPIPE, O_APPEND behavior and shared-position invariants; compile other architecture wrappers separately. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-111 — `17aeadc134854f10945237475da20aac58d273c4`

- **Changes:** Extract ksys_fallocate, retain syscall and redirect six architecture C wrappers.
- **Electro finding:** Moved body byte-identical: fdget/vfs_fallocate/fdput and current underlying validation/security/filesystem behavior stay. Existing vendor fallocate backend/locking/mode policy remains; no F2FS/ext4 allocation feature or GC/checkpoint activation. Current ARM64 compat assembly still branches sys_fallocate; x86 current declarations preserved. fs/open.c is SUSFS-sealed.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** pread/pwrite header and x86 macro contexts only. Independent adaptation passes without positional I/O cleanup or earlier x86 conversions. Current vfs_fallocate behavior must not be replaced with donor implementation.
- **Before implementation:** Use narrow later SUSFS open.c overlay/check support preserving historical seal and backend integrations. Target-build and test native/compat offset/length/flags, unsupported modes, access/security denial, filesystem ENOSPC/read-only errors and fd cleanup; do not enable deferred F2FS features. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-112 — `a5f88708a87b5112590d15df8d93437909fb3685`

- **Changes:** Extract ksys_fadvise64_64, retain native advice entry points, add disabled-config inline stub and redirect ten architecture files.
- **Electro finding:** Enabled generic body byte-identical, retaining current advice/readahead/invalidation/cache policy and fd cleanup. Not universally behavior-neutral: CONFIG_ADVISE_SYSCALLS=n new C helper stub returns EINVAL, while prior absent syscall weak fallback is ENOSYS; native/unchanged ARM64 compat NI routes remain ENOSYS. Also PPC32 ppc_fadvise64_64 now passes full loff_t len directly rather than narrowing through sys_fadvise64(size_t len): length0x100001000 models old4096 versus new4294971392. This is a width-preserving change on PPC32, not an ARM64 bug/performance fix. Advice defaults y in current profile; no cache policy activation.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Header/x86 declaration context can be independently adapted. Retain #ifdef ADVISE_SYSCALLS/stub linkage when approved. Earlier helpers are not semantic prerequisites, but explicitly review disabled-config errno and PPC32 len-width effects instead of labeling all caller renames universally equivalent.
- **Before implementation:** Explicitly acknowledge/test disabled ADVISE_SYSCALLS C-wrapper EINVAL versus NI ENOSYS; current ARM64 enabled profile is not coverage for disabled portability. Build/test PPC32 high len words and native/compat advice variants, enabled/disabled configurations, signed/zero/large ranges, advice mapping, cache invalidation/readahead and fd cleanup. Integer-width model/source checks are not PPC runtime proof. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-113 — `c718143abe34353be29c8807887af3bcd543cb97`

- **Changes:** Extract ksys_mmap_pgoff in both MMU/NOMMU implementations; retain native/old mmap wrappers and redirect seventeen architecture files including ARM64.
- **Electro finding:** Directly ARM64-relevant: native sys_mmap now calls internal helper after the same alignment test/byte-to-page offset conversion. Both mutually exclusive MMU and NOMMU bodies byte-identical: audit/fd/hugepage/flag/error/fput and vm_mmap_pgoff handling remain. Architecture offsets/units and old_mmap user-copy remain; unchanged ARM64 mmap2 assembly still calls retained sys_mmap_pgoff wrapper. No mmap layout, MGLRU, permissions, address randomization or allocation policy change is added. NOMMU is portability code, not active ARM64 configuration.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Advice header context only. Independent prototype relocation plus remaining donor files passes without112. Keep both MMU/NOMMU variants and syscall wrappers for unchanged assembly users; do not infer x86-only scope from broad file list.
- **Before implementation:** Target-build ARM64 MMU and supported NOMMU/other architectures separately. Test native and AArch32 mmap2 alignment/offset shifts, anonymous/file/huge mappings, protections/flags, fd/ref cleanup, error return conventions, MAP_FIXED/old_mmap where routed and existing LSM/KSU/BPF-adjacent behavior. No layout or memory-management feature activation. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

### PHX-114 — `a64e52fff7cae8a1f4929360aa8ab26bb3898313`

- **Changes:** Extract ksys_readahead, retain native syscall and redirect six architecture C wrappers.
- **Electro finding:** Moved body byte-identical: fd/read-mode checks, existing offset/count page arithmetic, do_readahead and cleanup remain. Actual force_page_cache_readahead policy/limits unchanged; zero-count/overflow behavior is not newly fixed. Current ARM64 compat word shuffle/sys_readahead branch stays. mm/readahead.c appears in BPF excluded-path list, not a source seal. No new readahead sizing/cache optimization or measured speedup.
- **Check:** FAIL unmodified standalone/submitted-order donor; reverse FAIL. PASS independent generated adaptation with git-apply/exact-source replay and ordered adapted105-114 replay, without forcing prior pending Phoenix work. Moved bodies byte-identical; types/wrappers/order and token-normalized implementation inverse PASS. No target/config-build, device/boot/ABI/performance tests.
- **Dependencies/scope:** Header/mmap prototype and x86 macro contexts only. Independent current-caller/header adaptation passes without advice/mmap cleanup. No new ADVISE_SYSCALLS requirement or readahead feature activation.
- **Before implementation:** Target-build and test native/AArch32 offset word assembly, signed/zero/large counts/offsets, fd/access modes, cache-backed/unsupported files, error and ref cleanup. Preserve existing readahead policy; do not claim algorithm changes or inherited range bugs fixed. Recheck integrated source and separately approved changes. Recommendations are not approval of implementation, prerequisite chains, feature activation, publication or CI. Source checks do not establish target/runtime/ABI/performance equivalence. No EXPORT_SYMBOL additions/removals in this batch.
- **Decision/application:** pending / not applied.

## PHX-B013 — x86 tail, shared declarations and NI organization

All nine complete API patches verified against per-file counts. Full pinned
pre/post files for the large reorders/deletion/macro changes were fetched with
Git-blob SHA validation and every patch reconstructed exactly. Large moved
blocks were audited via complete declaration/signature/lexical-guard and weak
symbol inventories plus residual code—not a claim of rereading identical moved
lines individually. All **12 affected + 21 supporting paths** remain byte-equal
to published `c6de0ddbe7e159a84c4906cbbf4f2c9138521c13`.

| Stable ID | Donor | Change | Recommendation |
| --- | --- | --- | --- |
| PHX-115 | [`e310e79f6`](https://github.com/PhoenixKernel/linux/commit/e310e79f6307eca855e9333daedf889090763efc) | ksys_ioperm | recommend skip x86 only ioport cleanup |
| PHX-116 | [`a583dbce8`](https://github.com/PhoenixKernel/linux/commit/a583dbce8b4225601945fd217df2aac70aeeb094) | x86 sigreturn signed return type | recommend skip x86 only sigreturn type cleanup |
| PHX-117 | [`68f0ac29f`](https://github.com/PhoenixKernel/linux/commit/68f0ac29f53346a2df47c73b0d232c2fb75484da) | x86 SYSCALL_DEFINE0 signal returns | recommend skip x86 only signal macro conversion |
| PHX-118 | [`5f12f2512`](https://github.com/PhoenixKernel/linux/commit/5f12f2512cf83dc4572c1d2de1bdce0c871db370) | kexec prototype consolidation | defer optional consolidation already declared in syscalls header |
| PHX-119 | [`a0312c663`](https://github.com/PhoenixKernel/linux/commit/a0312c6636498c1961e9453d794957d736d66e0c) | sort native syscall prototypes | recommend defer large native header reorder |
| PHX-120 | [`4957517fb`](https://github.com/PhoenixKernel/linux/commit/4957517fb88c4660cd403d7eb95f6c6a3fcc4668) | sort compat prototypes / asmlinkage | consider optional four asmlinkage annotations defer bulk reorder |
| PHX-121 | [`f8fc059d4`](https://github.com/PhoenixKernel/linux/commit/f8fc059d4d35838b403ba6542913373a21e224c7) | compat macro prototypes / x86 header deletion | defer split shared macro from unsafe x86 pruning |
| PHX-122 | [`b683f3449`](https://github.com/PhoenixKernel/linux/commit/b683f344956bbb0939edacf1225c01b7e4860468) | sort NI fallback entries | recommend defer optional ni reorder preserve local weak symbols |
| PHX-123 | [`321f8619e`](https://github.com/PhoenixKernel/linux/commit/321f8619e85384919f4848d3bbd93eaf8bb6d466) | COND_SYSCALL prefix macros | consider optional independent ni macro cleanup |

### Checks and preservation boundaries

- Original standalone **PASS: 116, 118**. Submitted order, applying only prior
  successes: **PASS: 116, 117, 118**. All reverse checks FAIL. These are text
  checks, not proof of absence, build readiness, benefit or implementation.
- **115** passes after an explicit pending019 signature-only fixture; not an
  independent adaptation/full019 replay. **116→117** originals pass in scratch.
- **118 applies but duplicates an existing declaration.** Tested minimal
  consolidation removes only kexec.h redundancy, keeping syscalls.h declaration
  and its existing forward type. Existing compat in-kernel syscall call remains.
- **119:** donor413→412 declarations, only duplicate kexec prototype removed;
  signatures/guards otherwise unchanged. Independent sorting adaptation keeps
  current clone3, sys32_quotactl, pidfd/close_range/BPF/NI declarations and the
  existing ftruncate helper without importing pending helper APIs.
- **120:** four missing asmlinkage annotations plus redundant waitid extern
  removal, not strictly reorder-only. ARM64 C asmlinkage is empty; no demonstrated
  runtime ABI fix. Adaptation preserves current sigset_from/to_compat, rather
  than forcing pending001/004 get/put migration, and does not import081 quota ABI.
- **121 is not wholly x86-only and does not have a whole-patch PASS.** Generic
  macro-only subset passes source replay and host preprocessing for arities1–6
  (plain prototype added; alias/body unchanged; DEFINE0 untouched). Current raw
  sys32 definitions/table/header cannot be auto-prototyped by COMPAT macros.
  Keep the header/includes and legacy quota ABI; donor x86 prerequisites remain
  pending and include earlier recorded ABI caveats. ARM64 pt_regs signal-entry
  signatures are not x86 zero-argument signal handlers.
- **122:** current219 NI entries/218 unique. Adaptation retains every unique
  name, including clone3/BPF and legacy quota, and only removes duplicate madvise.
  No new guards, ENOSYS change, feature activation or madvise bug fix inferred.
- **123:** donor217 expanded names/order unchanged. Independent current-layout
  adaptation preserves219 ordered aliases; actual generic cond_syscall host
  preprocessing produces byte-identical weak alias assembly. Keep raw
  `sys32_quotactl` and `ppc_rtas` exceptions. After122, equivalent218-entry recipe
  also passes; no semantic need for prior sorting. This is not target linkage
  proof, an architecture syscall-wrapper backport or an all-nine adapted replay.
- BPF fork/SUSFS source seals stay unchanged. The supporting paths include the
  published SUSFS manifest. **Pre-existing BPF manifest metadata already differs
  from published baseline** (runtime-test hash/device smoke note); its current
  hash is recorded separately and it was not edited, reset or resealed here.
- No target/resolved-config build, device/boot/ABI/optional-config linkage or
  performance validation; no production/config changes, commit, push or CI.

### PHX-115 — `e310e79f6307eca855e9333daedf889090763efc`

- **Changes:** Extract x86 ksys_ioperm, retain syscall wrapper, change two VT I/O permission call sites and architecture header include.
- **Electro finding:** Current x86 ioport still defines raw asmlinkage sys_ioperm, not the donor SYSCALL_DEFINE3 introduced by pending019. After an explicit signature-conversion fixture, unmodified115 applies and moved helper body is byte-identical: CAP_SYS_RAWIO/range checks, IO bitmap/TSS/thread flags and cleanup retained. VT call sites/include are CONFIG_X86 guarded. No active ARM64 I/O port path or phone speed/security improvement; do not force019 just to accept this.
- **Check:** FAIL standalone/order; reverse FAIL. PASS unmodified115 after explicit019 signature-only fixture; helper body byte-identical. Not an independent current-tree adaptation.
- **Dependencies/scope:** Unmodified115 needs019 standardized-definition context. Fixture changes only the019 signature, not a full019 replay or build. An alternate raw-wrapper-preserving extraction is conceivable but was not validated; no generic ARM64 dependency.
- **Before implementation:** Retain syscall ABI, iopl and VT error mapping; build/test x86 bitmap grants/revokes, privilege denial and overflow/error paths if ever selected. No ARM64 implementation recommended.
- **Decision/application:** pending / not applied.

### PHX-116 — `a583dbce8b4225601945fd217df2aac70aeeb094`

- **Changes:** Change x86_32 sys_sigreturn declaration and definition from unsigned long to long.
- **Electro finding:** Current declaration/definition are still unsigned long, so original patch applies. Function body unchanged; signed return type aligns syscall conventions but does not establish a runtime fix on this ARM64 target. It prepares117, not ARM64 signal handling.
- **Check:** PASS original standalone/submitted order; reverse FAIL. Original116 then117 PASS in scratch, with signal bodies unchanged.
- **Dependencies/scope:** Independent supplied patch;117 expects this signed declaration/definition. Do not use a clean text check as implementation approval.
- **Before implementation:** If x86 portability work is approved, build/test x86_32 normal/bad signal frames, saved registers and syscall return conventions; no phone performance claim.
- **Decision/application:** pending / not applied.

### PHX-117 — `68f0ac29f53346a2df47c73b0d232c2fb75484da`

- **Changes:** Use SYSCALL_DEFINE0 for x86 sigreturn/rt_sigreturn and include linux/syscalls.h.
- **Electro finding:** Unmodified117 fails independently because sys_sigreturn is unsigned long; after116 it applies exactly. Both signal-frame bodies remain unchanged, but syscall macros can add tracing metadata: not merely whitespace. ARM64 native/compat signal return functions instead take struct pt_regs pointers; do not transplant this x86 zero-argument conversion to them.
- **Check:** FAIL original standalone; PASS after116 in submitted-order scratch; reverse FAIL. Exact source inverse confirms only include/definition spellings change bodies.
- **Dependencies/scope:** 116 is needed for supplied signed-type context and consistent x86_32 header. No dependency on generic header/NI sort or ARM64 entry changes.
- **Before implementation:** If selected for x86, validate syscall tracing metadata/entry assembly and signal-frame recovery on x86_32/x86_64 separately. ARM64 entry/signatures stay unchanged.
- **Decision/application:** pending / not applied.

### PHX-118 — `5f12f2512cf83dc4572c1d2de1bdce0c871db370`

- **Changes:** Move sys_kexec_load declaration from kexec.h to syscalls.h.
- **Electro finding:** Electro already declares sys_kexec_load in syscalls.h and has struct kexec_segment forward declaration. Original118 applies but produces two matching prototypes there;119 later removes that duplicate in donor history. Current kernel/kexec.c includes syscalls.h and its compat wrapper still calls sys_kexec_load: relocation is not a kernel-call/helper or address-limit migration and does not enable kexec. Scratch consolidation removes only redundant kexec.h declaration, keeping existing syscall declaration.
- **Check:** PASS original standalone/order; reverse FAIL. Scratch proves original changes syscalls.h declaration count1→2, and minimal removal-only adaptation passes exact git-apply replay.
- **Dependencies/scope:** No semantic119 dependency: current existing declaration permits a minimal removal-only consolidation. Consumers/includes and both kexec header configurations must be rechecked before selecting it.
- **Before implementation:** Prefer minimal consolidation rather than duplicate insertion. Build native/compat with KEXEC enabled/disabled and inspect all consumers; no kexec activation or in-kernel pointer API change.
- **Decision/application:** pending / not applied.

### PHX-119 — `a0312c6636498c1961e9453d794957d736d66e0c`

- **Changes:** Reorder native syscall prototypes to asm-generic syscall order and add per-source/architecture/obsolete sections.
- **Electro finding:** Complete donor pre/post inventory413→412 parsed declarations: only one duplicate sys_kexec_load prototype is removed; all remaining signatures and lexical guards match. STAT64 conditional block is split with equivalent conditions, not broadened. Donor header lacks current sys_clone3 and sys32_quotactl and carries pending helper APIs. Blind replacement would discard local entries/import unapproved helper declarations. Independent prototype-block-only scratch adaptation preserves all389 current parsed declarations/guards, exact prefix and ftruncate suffix/helper, clone3, legacy quota, close_range, pidfd, BPF and NI prototypes; no prior helper series forced.
- **Check:** FAIL original standalone/order; reverse FAIL. PASS independent preservation-aware prototype-block adaptation with exact git-apply replay and current declaration/signature/guard multiset equality.
- **Dependencies/scope:** 118 accounts for the duplicate donor prototype, not an Electro prerequisite.081 quota rename and many prior pending helper declarations are donor-context differences;098 existing ftruncate helper must stay. Sort can be independently adapted without any pending helper implementations.
- **Before implementation:** Prefer deferring churn unless explicitly wanted. If selected, retain all local prototypes/forward types/helper bodies and verify target plus compat and cross-architecture configs; no syscall implementation/ABI/performance change inferred.
- **Decision/application:** pending / not applied.

### PHX-120 — `4957517fb88c4660cd403d7eb95f6c6a3fcc4668`

- **Changes:** Reorder compat prototypes and add missing asmlinkage to msgctl, shmctl, semtimedop and rt_tgsigqueueinfo; remove redundant extern on waitid.
- **Electro finding:** Donor inventory130→130: exactly four asmlinkage additions and redundant waitid extern removal; all parameter/return types and lexical guards otherwise retained. These annotations are not mere comments, but ARM64 C asmlinkage expands empty, so no demonstrated ARM64 runtime ABI repair. IPC compat C callers still exist and are not migrated by this patch. Donor context has pending get/put_compat_sigset and compat_sys_quotactl32 APIs; current sigset_from/to_compat and legacy quota ABI must not be replaced. Independent scratch reorder/annotation adaptation preserves129 current syscall declarations with only specified annotations/extern change, all non-syscall code-token inventory, existing sigset helpers and arch_prctl.
- **Check:** FAIL original standalone/order; reverse FAIL. PASS independent current-preserving adaptation, exact git-apply replay, expected declaration/guard inventory and non-syscall code-token checks.
- **Dependencies/scope:** 001/004 sigset migration and081 x86 quota rename are header-context differences, not semantic prerequisites for sorting or four annotations. Native header sorting119 is independent.
- **Before implementation:** If useful, select four annotation corrections separately from bulk reorder. Check compat definitions/C callers and build real supported compat configurations; do not claim ARM64 calling-convention fix, helper migration or performance gain.
- **Decision/application:** pending / not applied.

### PHX-121 — `f8fc059d4d35838b403ba6542913373a21e224c7`

- **Changes:** Add explicit compat_sys prototype before alias declaration in COMPAT_SYSCALL_DEFINEx; delete x86 sys_ia32.h/includes and architecture-specific compat prototypes.
- **Electro finding:** Not wholly x86-only: generic macro affects ARM64 compat definitions for arities1–6; DEFINE0 unchanged. Isolated macro addition passes exact-source replay and host preprocessor checks for arities1–6, adding only the plain prototype with existing alias/body expansion unchanged. Whole patch fails and is not independently validated: current ia32 header/table/functions still use raw sys32_* declarations, waitpid and other legacy paths, rather than donor compat_sys_x86_* conversion chain. Generic COMPAT macros cannot auto-declare those raw definitions. arch_prctl already uses COMPAT_SYSCALL_DEFINE2, but that does not justify deleting remaining old header. Keep it and current sys32_quotactl until separately approved, ABI-correct x86 conversions.
- **Check:** FAIL original standalone/order; reverse FAIL. PASS MACRO-ONLY SUBSET exact git-apply replay and host preprocessing1–6; whole-patch/header-deletion adaptation NOT validated or recommended on current legacy x86 state.
- **Dependencies/scope:** 120 supplies sorted-header context.020/021/027/028/081 describe earlier donor x86 conversions/removals, not a proven complete or safe dependency closure;027 retains its previously recorded _do_fork ABI issue. Macro-only addition can be split without those x86 changes. Do not force pending x86 chain or imply full121 PASS.
- **Before implementation:** If desired, split shared macro addition from x86 pruning, compile ARM64 COMPAT with exact AOSP toolchain, check alias/prototype warnings and native/AArch32 behavior. Keep old x86 declarations/includes unless matching source/table conversions are explicitly approved and validated.
- **Decision/application:** pending / not applied.

### PHX-122 — `b683f344956bbb0939edacf1225c01b7e4860468`

- **Changes:** Reorder weak syscall fallbacks and add asm-generic/source/architecture/obsolete headings.
- **Electro finding:** Donor218→217 cond_syscall invocations: only duplicate sys_madvise removed; every unique fallback retained, no added guards. Electro219 invocations/218 unique symbols include legacy sys32_quotactl and clone3; donor instead has compat_sys_quotactl32. Scratch adaptation retains every current unique symbol including clone3/BPF and old quota name, removes only second madvise, and preserves exact -ENOSYS body/includes/guard context. A duplicated weak alias is not a newly working madvise implementation or a feature/errno fix.
- **Check:** FAIL original standalone/order; reverse FAIL. PASS independent current-name-preserving adaptation with exact git-apply replay;219→218 entries,218 unique unchanged; only duplicate madvise removed.
- **Dependencies/scope:** 081 explains donor quota symbol mismatch, not a required conversion for sorting. No native/compat header sort or generic helper dependency; preserve current weak symbols instead of importing rename.
- **Before implementation:** If selected, build/link optional-syscall enabled/disabled and COMPAT variants, inspect weak/strong resolution, and retain clone3, BPF, custom quota and architecture exceptions. No feature activation/performance claim.
- **Decision/application:** pending / not applied.

### PHX-123 — `321f8619e85384919f4848d3bbd93eaf8bb6d466`

- **Changes:** Add COND_SYSCALL/COND_SYSCALL_COMPAT prefix macros, convert NI entries and update adding-syscalls documentation.
- **Electro finding:** Donor217→217 expanded weak entries are identical in order and multiplicity; macro definitions only prepend sys_ or compat_sys_. ppc_rtas remains a raw exception. Independent Electro adaptation preserves all219 current ordered weak alias expansions, leaving sys32_quotactl and ppc_rtas raw; host preprocessing with actual generic cond_syscall gives byte-identical asm output. After122 current-preserving reorder, equivalent prefix recipe retains218 ordered entries. Body remains -ENOSYS; this does not introduce architecture syscall wrappers, activate syscalls or backport a new syscall ABI.
- **Check:** FAIL original standalone/order; reverse FAIL. PASS independent current-layout macro/doc adaptation and exact git-apply replay; all219 generic weak asm expansions byte-identical under host preprocessing. Post122218-entry recipe equality PASS; no target link proof.
- **Dependencies/scope:** 122 supplies unmodified donor layout but is not a semantic dependency: current unsorted file can be converted directly. Do not incorrectly prefix sys32_quotactl or ppc_rtas. Ordered122→123 test is a transformation-recipe probe, not an unmodified patch replay.
- **Before implementation:** If selected, preserve architecture cond_syscall overrides and raw exceptions, keep docs in sync, build/link native/compat optional configurations and inspect disabled-syscall ENOSYS behavior; no measurable runtime gain established.
- **Decision/application:** pending / not applied.

## PHX-B014 — file-signal ownership and generic signal type propagation

All eight complete diffs read; pinned full SHAs deduplicated against123 prior
entries and per-file API patch counts checked. Full donor124 fcntl source fetched
and Git-blob hash verified to inspect NULL handling outside its patch context.
All **13 affected + 21 supporting paths** byte-match published
`c6de0ddbe7e159a84c4906cbbf4f2c9138521c13` and remain unchanged.

| Stable ID | Donor | Change | Recommendation |
| --- | --- | --- | --- |
| PHX-124 | [`c30a65969`](https://github.com/PhoenixKernel/linux/commit/c30a65969c59223eea1320b72bcae738b686a12e) | file-signal owner PID types | block as supplied missing null task guards |
| PHX-125 | [`aa8a31362`](https://github.com/PhoenixKernel/linux/commit/aa8a3136290989e652714729f0673da9e0a28947) | carry owner type into SIGIO/SIGURG helpers | defer requires corrected owner type mapping not raw 124 |
| PHX-126 | [`c92ed7400`](https://github.com/PhoenixKernel/linux/commit/c92ed7400fbd514f473a331fc9dfb443379aa061) | do_send_sig_info enum interface | consider only coherent signal type spine with caller audit |
| PHX-127 | [`c853c685c`](https://github.com/PhoenixKernel/linux/commit/c853c685c22c0bd7f3af429fb07eb3f97d2b49db) | KDB signal correctness cleanup | consider standalone kdb correctness low priority inactive profile |
| PHX-128 | [`1c1ddc9fb`](https://github.com/PhoenixKernel/linux/commit/1c1ddc9fb51d2df595cf53ab22ee5c19716af33c) | carry type into send_signal | defer optional coherent signal type spine |
| PHX-129 | [`2e5c85198`](https://github.com/PhoenixKernel/linux/commit/2e5c8519897015ddbb210f259674988823e98c2b) | carry type into __send_signal | defer optional coherent signal type spine |
| PHX-130 | [`72b1762ba`](https://github.com/PhoenixKernel/linux/commit/72b1762ba2a039a5ad35257fd279d8092706e02d) | POSIX timer PID lookup in send_sigqueue | consider independent posix timer refactor with race validation |
| PHX-131 | [`3951007a0`](https://github.com/PhoenixKernel/linux/commit/3951007a026fa0bc9919d5c7c363bb0950a08acb) | carry type into complete_signal | defer optional coherent signal type spine |

### Blocking finding and validation boundaries

- **124 introduces an unguarded NULL task route**, not an existing Electro bug.
  Both new direct PID/TGID branches call helpers after `pid_task()` with no
  `if (p)`; `sigio_perm()` dereferences the task. A retained pid reference does
  not keep an exited task attached. Current iterator skips empty task lists.
  Donor124 full-file helper also lacks a guard; **125–131 do not repair it**.
- Extracted real dispatch functions with deterministic host stubs: dead owners
  produce **0 NULL helper calls in baseline, 4 after124 and after131**, covering
  TID/process × SIGIO/SIGURG. PGRP remains on safe iterator. Two-guard scratch
  probe restores0; all variants retain6 live callbacks and balanced modeled
  locks. This is control-flow evidence, not target crash/concurrency proof or
  permission to fix/apply anything.
- Original standalone/submitted-order **PASS127/130 only**, all reverse FAIL.
  Context-only124 adaptation (`f_modown`→existing `__f_setown` in f_delown hunk)
  then original125–131 passes text replay **while still unsafe**.
- Independent **126→128→129→130→131** recipe passes without124/125/127: preserve
  old NULL-safe owner iterator, map its bool group to enum at3 fcntl boundaries,
  omit new KDB direct-call hunk when old KDB remains. This is not a safe whole
  submitted-series PASS, nor proof of a minimal upstream dependency closure.
- Core do_send_sig_info/send_signal/__send_signal/complete_signal bodies map
  exactly to baseline under the type/group inverse; queue selection, permission
  checks, rlimits, coalescing, siginfo, fatal handling and wakeups are retained.
  **These commits do not implement later fork/group signal bookkeeping.**
- Whole-tree caller audit: Simple LMK true still equals TGID1; tile false equals
  PID0; memory-failure already passes PIDTYPE_PID. Preserve/audit these paths and
  prefer explicit enums if selected. No OOM/LMK, scheduler or reclaim tuning.
- **127** independently corrects KDB metadata/held-lock delivery. Host helper
  probe verifies held-lock send, first stopped-task warning, retry and failed
  trylock paths. KDB defaults n/not enabled here; PID_NS=n. No feature activation,
  phone namespace fix, complete parser hardening or debugger deadlock proof.
- **130** independently moves timer lookup/RCU into send_sigqueue and changes
  process lookup PID→TGID; thread-ID notifications remain PID. Timer creation
  stores the appropriate referenced leader/thread pid; current TGID links exist.
  Extracted helper/event probe passes10 modeled lookup/lock/ignore/overrun/send
  cases plus invalid-preallocation/code early exits. Missing task remains-1,
  ignored1, successful/already queued0; event ret>0 behavior remains. CPU/alarm/
  hrtimer event consumers are included in source audit. Existing rearm FIXME,
  de_thread races and softirq policy are not claimed fixed; no timing gain.
- BPF fork/pid integration and SUSFS seals preserved. Existing unrelated BPF
  smoke metadata hash is recorded and unchanged. No touched file requires a
  new sealed-source overlay for these eight. No target build/config, device,
  boot, real signal/timer races, debugger runtime or performance tests, CI,
  implementation, commit or push. Source/host models are not production proof.

### PHX-124 — `c30a65969c59223eea1320b72bcae738b686a12e`

- **Changes:** Represent F_OWNER_PID/default file ownership with TGID, F_OWNER_TID with PID rather than MAX; update TUN/TTY/lease/dnotify producers and use RCU pid_task lookup for individual/thread-group owners.
- **Electro finding:** ARM64-relevant, but introduces a blocking NULL-task route in both send_sigio and send_sigurg. A referenced fown->pid can survive after task detachment; pid_task(pid, PIDTYPE_PID) may return NULL. New direct branches invoke helpers unconditionally; sigio_perm then dereferences __task_cred(p). Original iterator skips empty task lists. Verified donor124 full-file helper also lacks a NULL guard, and125–131 do not fix it. Extracted-function host stub probe: baseline0 NULL helper calls versus donor124/final4 (TID/process × SIGIO/SIGURG); PGRP iterator stays safe. Scratch two-guard probe restores0, but is not an approved implementation or target race test. Live-target owner mapping/F_GETOWN_EX roundtrips, credentials/LSM body and deliberately preserved PID lookup remain; it does not yet convert stored task_pid to task_tgid.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS context-only124 adaptation followed by original125–131 in scratch, but sequence STILL UNSAFE. Host control-flow probe confirms missing-task routing; corrected two-guard probe only, not kernel/runtime proof.
- **Dependencies/scope:** Donor f_delown calls f_modown; Electro calls existing __f_setown. Context-only rename permits ordered replay without importing an unrelated owner-helper refactor. All five producer files and both decoder/delivery paths must be treated consistently. No need for prior Phoenix syscall-helper series. Existing exported __f_setown signature unchanged, but internal PID type meaning changes; audit any out-of-tree producer before implementation.
- **Before implementation:** Do not apply as supplied. Any later proposal must guard both task lookups, preserve RCU/owner locks and producer/decoder consistency, and test dead owner/exit/exec, TID/TGID/PGRP, fd sharing, SIGIO realtime fallback, SIGURG, TUN/TTY/leases/dnotify, namespaces and LSM denials. No claim of current Electro vulnerability or measured locking speedup.
- **Decision/application:** pending / not applied.

### PHX-125 — `aa8a3136290989e652714729f0673da9e0a28947`

- **Changes:** Pass enum pid_type into SIGIO/SIGURG helpers and derive old group predicate at do_send_sig_info calls; remove temporary group variables.
- **Electro finding:** Mostly type propagation after124. PID means thread-only and non-PID means group pending/wakeup; body behavior for live valid owners is unchanged after matching mapping. Does NOT add missing NULL checks, so124 regression persists. Applying direct fown type semantics to Electro legacy PID(process)/MAX(thread) encoding would invert thread/process meaning unless boundary conversion or124 mapping is also handled. Full original125 passes after124 context adaptation, but that fixture remains unsafe. Independent core spine avoids both124 and125.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS original125 after context-adapted124 in ordered scratch; no whole-series safety PASS, NULL route persists.
- **Dependencies/scope:** 124 supplies donor ownership semantics and lookup layout, not just a cosmetic hunk offset. Keep whole125 deferred until a corrected owner-mapping design is explicitly selected. No standalone current-preserving125 adaptation validated; do not infer that merely changing helper parameter types is sufficient.
- **Before implementation:** If owner-type series is selected, correct124 first and validate F_OWNER_TID/PID/PGRP, queued signals, fallback SIGIO, SIGURG and permission checks. No new feature or runtime gain established.
- **Decision/application:** pending / not applied.

### PHX-126 — `c92ed7400fbd514f473a331fc9dfb443379aa061`

- **Changes:** Change do_send_sig_info bool group to enum pid_type; pass actual group type, thread PID, OOM TGID and sysrq MAX while retaining boolean bridge inside.
- **Electro finding:** Generic ARM64 signal paths, including OOM and SysRq, not x86-only and not an OOM/LMK policy change. Supplied fcntl hunks expect125. Independent scratch alternative retains Electro legacy fown mapping/NULL-safe iterator and maps old group to TGID/PID at all3 fcntl calls; other donor hunks apply. This starts tested126→128→129→130→131 spine without124/125/127. Full-tree call audit finds additional Simple LMK true and tile false calls omitted by donor: actual PID enum0/TGID enum1 keeps numeric meaning; memory-failure already uses PIDTYPE_PID. Prefer explicit enum constants if implemented; no demonstrated omitted-caller behavioral bug. SysRq MAX stays a non-thread tag, never a pid_task index.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS original126 in ordered context-adapted124/125 fixture, and independent non-fcntl hunks plus recorded3-call legacy-fcntl bridge. Core function inverse and enum predicate checks PASS; no target build/link.
- **Dependencies/scope:** 125 supplies original fcntl context. Independent legacy bool→enum boundary adaptation avoids124/125, and no older signal/helper series is forced. Public declaration, definition and all callers must agree atomically; tested subset is not proof of minimal upstream closure.
- **Before implementation:** Only select for a concrete coherent signal-series purpose. Audit every caller including vendor/architecture paths and enum values; preserve PID/TGID/PGID/MAX semantics, OOM victims/marks, SysRq, pidfd/native/compat signal paths, credentials/security and exported contracts. Test actual signals/fork/exit/namespace behavior; no memory-pressure tuning or feature activation.
- **Decision/application:** pending / not applied.

### PHX-127 — `c853c685c22c0bd7f3af429fb07eb3f97d2b49db`

- **Changes:** Rename kdb_send_sig_info to kdb_send_sig; use SEND_SIG_PRIV, retain held siglock through send_signal and validate signal in kdb_kill.
- **Electro finding:** Original applies independently. Real debugger-specific correctness changes: replaces fabricated SI_USER pid/uid metadata with kernel-private signal (SI_KERNEL/zero sender), avoids dropping and reacquiring siglock, and checks validity before helper. Keeps target group leader, thread-directed pending route, busy-lock warning and stopped-task first-call warning/retry. Extracted helper host probe confirms delivery runs with siglock held, warning path unlocks, retry sends and failed trylock does not unlock another holder. Does not eliminate all scheduler/runqueue/debugger deadlock risks or fully harden inherited numeric parser extremes. KDB defaults n and is not enabled in checked-in miatoll defconfig; PID_NS explicitly n, so do not present this as an active phone namespace fix or enable either feature.
- **Check:** PASS original standalone/submitted-order; reverse FAIL. Ordered original replay plus extracted-function host lock/control-flow checks PASS. Not debugger runtime, target compilation or deadlock proof.
- **Dependencies/scope:** Independent of124–126, generic type spine or earlier pending signal work. If later128 is selected with127, its new direct KDB send_signal call must use PIDTYPE_PID; without127, old helper still routes through send_sig_info and needs no new direct-call hunk.
- **Before implementation:** Optional standalone correctness candidate if maintaining KDB. Build/test KDB on/off, valid/invalid kill input, live/stopped/exited tasks, busy siglock, repeated warning override and actual namespace metadata where supported. Preserve warnings and acknowledge debugger scheduler-lock risk; do not enable KGDB/KDB/PID_NS without authorization.
- **Decision/application:** pending / not applied.

### PHX-128 — `1c1ddc9fb51d2df595cf53ab22ee5c19716af33c`

- **Changes:** Convert send_signal group parameter to enum pid_type, update group/thread/KDB call sites and bridge to old __send_signal boolean.
- **Electro finding:** Carries already-known type one layer deeper. Native core implementation body maps back exactly to baseline under type→group inverse, including PID-namespace ancestor handling. __group_send_sig_info uses TGID, specific sends PID, do_send_sig_info retains caller type. If127 was applied, KDB false becomes PID. Independent tested spine omits new KDB hunk while retaining legacy KDB via send_sig_info, so127 is not a semantic prerequisite. No copy_process/fork implementation change, signal feature activation or measured performance gain.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS original128 after full preceding adapted fixture; PASS independent spine adaptation omitting unimplemented127 KDB hunk. Type-normalized function inverse PASS.
- **Dependencies/scope:** 126 supplies enum-typed do_send_sig_info for original call site.127 is donor direct-KDB-call context only: skip that hunk when retaining old helper. Tested126→128→129→130→131 spine avoids124/125/127.
- **Before implementation:** Keep all direct send_signal callers consistent, including whichever KDB implementation is retained. Target-build and test group/thread, native/compat/pidfd, namespace/ancestor, bad signal and concurrent exit paths. Preparatory type plumbing is not a completed fork-signal race fix.
- **Decision/application:** pending / not applied.

### PHX-129 — `2e5c8519897015ddbb210f259674988823e98c2b`

- **Changes:** Convert __send_signal to enum pid_type; select pending queue by non-PID predicate, retain bool completion/trace bridges and update credential-based sender.
- **Electro finding:** Queue selection remains private for PID and shared for non-PID. prepare_signal, allocation/rlimits, legacy coalescing, siginfo/user-namespace mapping, signalfd, errno and wakeup code map back exactly to current core body. kill_pid_info_as_cred maps former group1 to TGID. After131 completion takes type directly; trace remains boolean type!=PID. No delayed multiprocess signal tracking or copy_process modification is introduced.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS original129 in full ordered fixture and independent type spine; type-normalized complete core body inverse and queue predicate checks PASS.
- **Dependencies/scope:** 128 supplies enum type at send_signal forwarding boundary.131 later consumes rich type at completion, but129 itself retains boolean completion bridge. Do not label this alone or the whole batch as the later fork/group signal correctness feature.
- **Before implementation:** Build/test private/shared pending, realtime/legacy overflow/coalescing, signalfd, rlimit/error paths, SI_* and namespace identity, fatal/group exit, tracing and concurrent sender/fork/exit. Preserve existing security and pidfd integration; no tuning or runtime speedup inferred.
- **Decision/application:** pending / not applied.

### PHX-130 — `72b1762ba2a039a5ad35257fd279d8092706e02d`

- **Changes:** Change send_sigqueue task/bool API to pid/enum; move PID lookup and RCU scope into helper, selecting TGID for process timers and PID for SIGEV_THREAD_ID.
- **Electro finding:** Original applies independently on current Electro. Full-tree audit has one send_sigqueue caller in posix_timer_event; that event is also used by hrtimer, CPU and alarm timers. Timer creation retains a pid ref, using leader pid for ordinary process notifications (default task_tgid; explicit good_sigevent task_pid of group leader) and thread pid only for validated SIGEV_THREAD_ID. Process lookup deliberately changes PID→TGID, not just a variable rename; current TGID pid links/attachments already exist. Missing task/failed sighand lock returns internal-1; preallocated/SI_TIMER checks, ignored return1, queued overrun increment/return0, delivery/trace and posix event ret>0 are retained. RCU is now acquired inside helper after early checks and released on all acquired paths. Extracted functions pass10 PID/TGID missing/lock-failed/ignored/queued/delivered host cases plus invalid-q early exits. Does not fix existing dequeue/rearm FIXME, all de_thread/leader-exit races or softirq starvation behavior; no timer scheduling/interval change.
- **Check:** PASS original standalone/submitted-order; reverse FAIL. PASS original130 in both full ordered fixture and independent spine. Extracted-helper/posix-event host flow probe PASS with balanced modeled RCU/locks; no real concurrency or target ABI proof.
- **Dependencies/scope:** Independent supplied patch: no124–129 or prior timer/signal-helper prerequisite for applicability. Before131, enum is explicitly reduced to bool at completion/trace;131 can subsequently preserve type into completion. Existing SIGEV_THREAD_ID validation, pid ref lifetime and TGID infrastructure are required existing interfaces, not new feature enablement.
- **Before implementation:** Target-build COMPAT/POSIX_TIMERS configurations and test native/AArch32 timer_create, default/explicit process notifications, SIGEV_THREAD_ID and invalid cross-group IDs, ignored/prequeued/overrun cases, task/leader exit/de_thread/exec/delete races, CPU/alarm/hrtimer dispatch. Preserve timer rearm/interval/softirq foundation; do not claim untested timer-race fix or latency gain.
- **Decision/application:** pending / not applied.

### PHX-131 — `3951007a026fa0bc9919d5c7c363bb0950a08acb`

- **Changes:** Convert complete_signal group parameter to enum pid_type and forward type from __send_signal/send_sigqueue.
- **Electro finding:** Thread-only early return becomes type==PID; non-PID still searches the same thread group. Wants-signal selection, curr_target walk, fatal group-exit propagation, jobctl clearing and signal_wake_up are otherwise unchanged by exact inverse comparison. Enum predicate model covers PID/TGID/PGID/SID/MAX; trace still exposes bool group. No process-group/session fork bookkeeping is added, and no fork.c/BPF overlay is needed for this commit. Does not repair124 NULL lookup regression.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS original131 after129/130 in both full ordered and independent fixtures. Exact type-normalized completion inverse and predicate truth table PASS; no real wakeup/fork-race validation.
- **Dependencies/scope:** 129 and130 provide typed callers in the supplied patch. Original131 passes after both, including independent core spine that avoids124/125/127. Dependencies describe tested interfaces, not approval or a proven minimal upstream closure.
- **Before implementation:** Validate blocked/ignored group members, curr_target selection, private versus shared queues, fatal signals/core dumps, SIGKILL/SIGSTOP, tracing and concurrent fork/exit. No all-series fork/group correctness or performance claim from type propagation alone.
- **Decision/application:** pending / not applied.

## PHX-B015 — fork progress, first-run pending signals and group stops

All eight complete diffs read and API per-file counts verified; full SHAs new
against131 prior entries. **6 affected + 26 supporting paths** match published
`c6de0ddbe7e159a84c4906cbbf4f2c9138521c13` and remain unchanged.

| Stable ID | Donor | Change | Recommendation |
| --- | --- | --- | --- |
| PHX-132 | [`801093404`](https://github.com/PhoenixKernel/linux/commit/8010934043e6438f40b4355f1eece577b245b6e3) | dying PID namespace check ordering | consider low priority pid namespace ordering with BPF overlay |
| PHX-133 | [`446fa546c`](https://github.com/PhoenixKernel/linux/commit/446fa546c0b3457bb5a33f24927ac13c6bde9d80) | explicit fatal-pending fork abort | consider as required guard for later fork signal changes |
| PHX-134 | [`107667301`](https://github.com/PhoenixKernel/linux/commit/1076673012c682011156e8d409a2399ad9b9744a) | calculate pending flags at schedule_tail | consider as foundation not standalone fork speedup |
| PHX-135 | [`fe723bb4d`](https://github.com/PhoenixKernel/linux/commit/fe723bb4d061448cd33a0c6f797089077123c51b) | remove ptrace_init_task flag assignment | only with calculate sigpending never standalone |
| PHX-136 | [`baa572b94`](https://github.com/PhoenixKernel/linux/commit/baa572b94e4f73e043502a6bbb4cb60a88313a21) | new threads join ongoing group stops | consider only with fatal guard and first run pending setup |
| PHX-137 | [`2eadaa3b7`](https://github.com/PhoenixKernel/linux/commit/2eadaa3b792ce89350a5779e0838d684330b26cb) | fork progress and delayed multiprocess signals | worth targeted correctness backport only with complete validated foundation |
| PHX-138 | [`4cb413573`](https://github.com/PhoenixKernel/linux/commit/4cb413573b4e1e97fe2a4b4ec84f0b5543fc88d5) | early error return in _do_fork | defer optional control flow cleanup preserve current ABI and MGLRU |
| PHX-139 | [`9dc6b001f`](https://github.com/PhoenixKernel/linux/commit/9dc6b001f30c5ad63b3caf5a157751be46451a37) | comment on CLONE_FS and namespaces | optional comment only no runtime benefit |

### Findings and preservation boundaries

- **137 is substantive, not another cosmetic type conversion:** move initial
  pending check before expensive copy, retain late fatal abort and record
  process-group/session/broadcast signals for new non-thread processes. It is
  worth a targeted correctness backport investigation, **not blind application
  or a general phone-speed claim**. Already pending signals still restart early.
- **Cross-batch refinement:** B014's legacy fcntl bool→TGID/PID bridge sufficed
  while only group-vs-thread behavior mattered.137 uses `type > PIDTYPE_TGID`,
  so that bridge would hide PGID events. New scratch fixture retains PGID/SID
  losslessly while mapping legacy process PID→TGID/thread MAX→PID and keeping
  current NULL-safe iterator/owner ABI. **No unsafe124/125 dependency; no new
  commit here fixes124.** Previous131 records are preserved, not rewritten.
- **132/133:** dying namespace ENOMEM precedes late pending restart; explicit
  fatal helper (TIF+SIGKILL pending) returns EINTR before late ordinary restart.
  Keep fatal protection when136/137 remove blanket late restarts. PID_NS=n
  limits nested-namespace relevance; no namespace activation.
- **134/135:** first-run calculate helper locks sighand, presets flag and reuses
  current recalc. It covers actual current jobctl/private/shared/freezer logic,
  **not donor prose's unimplemented livepatch predicate**. ARM64 schedule_tail→
  ret_to_user work-mask source path supports initial pending handling, including
  native/compat.135 applies textually alone but **must not be selected without
  134**. Keep ptrace classic/seized stop state. No BORE/CASS policy changes.
- **136:** stop counter/jobctl join is before thread publication with siglock
  held, after ptrace setup. Requires133 fatal and134 first-run handling;135 is
  optional. No-stop/fatal/exiting cases do not increment counter in host model.
- **137:** initialize static/new signal heads and every stack node, register
  before copying, assign child delayed bits before PID visibility, remove node
  on success/failure under siglock. Thread/idle unlinked nodes remain initialized.
  Stop/continue cancellation tested. Only a bitmap is copied, not siginfo queues;
  collector is at out_set, so existing ignore/coalescing/overflow short-circuits
  and blocked/realtime metadata/order need explicit regression tests. No claim
  that all signal ordering is proved by a collector-only model.
- **138:** current `_do_fork(kernel_clone_args *)` is still nested; independent
  flattening preserves current ABI, pidfd alias validation, latent entropy,
  MGLRU pre-wakeup registration, cpufreq, trace/ref/child-TID/vfork order. Never
  copy donor old scalar-signature function over it. **139 is comment-only**:
  shared root/cwd filesystem context, not root privilege; checks unchanged.
- **BPF fork seal is immutable.**132/133/136–139 need explicit later delta/check
  chain if selected—even comment139 changes file hash. Keep clone3/pidfd/BPF/
  MGLRU/vendor/scheduler integration; no whole-file replacement or reseal.
  SUSFS seals and unrelated BPF smoke metadata unchanged.
- Original standalone/order PASS **134/135 only**; all reverse FAIL. Independent
  138/139 adaptations and full132–139 scratch recipes on lossless typed spine
  PASS. Extracted host128 pending/freezer +4 groupstop +5 type classes with two
  collectors PASS, as do source order/lifetime/inverse guards. These fake-primitive
  models are not real fork, RCU/locking, job-control, ptrace or freezer tests.
- No target/resolved-config build, device/boot, fork-starvation reproduction,
  signal/timer/namespace races, ABI or performance proof; **no production/config
  changes, implementation, commit, push or CI**.

### PHX-132 — `8010934043e6438f40b4355f1eece577b245b6e3`

- **Changes:** Move PIDNS_HASH_ADDING/nr_hashed guard before late pending-signal restart and document its purpose.
- **Electro finding:** Current check is after signal_pending; donor moves it first so dying namespace ENOMEM takes precedence over ERESTARTNOINTR when both apply. It retains the current old field/constant names and cleanup target; not new PID namespace support. Miatoll explicitly has PID_NS=n, reducing nested-namespace relevance, though the compiled initial-namespace guard remains. Donor trailing context skips current sched_post_fork/pidfile publication region; narrow scratch relocation preserves those hooks and current clone3/kernel_clone_args ABI. fork.c matches immutable BPF after-image, so any implementation requires explicit later delta validation, not resealing.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS generated context-preserving relocation in ordered fixture; late error precedence modeled. No namespace target/runtime proof.
- **Dependencies/scope:** Independent logic;133/136/137 use resulting donor layout. No need for B014 signal type spine just to move this guard. Prior namespace feature enablement is not authorized.
- **Before implementation:** Use narrow BPF fork overlay if selected, preserve sched_post_fork/pidfd final-check ordering, test dying namespaces with pending signals and cleanup, and keep PID_NS disabled unless separately authorized.
- **Decision/application:** pending / not applied.

### PHX-133 — `446fa546c0b3457bb5a33f24927ac13c6bde9d80`

- **Changes:** Add fatal_signal_pending(current) late abort with EINTR before ordinary restart logic.
- **Electro finding:** Uses existing helper: TIF_SIGPENDING plus private SIGKILL pending, not every signal with a fatal default disposition. With the old all-pending restart, user-visible kill termination is largely redundant, but internal error changes from ERESTARTNOINTR to EINTR; after136/137 remove late blanket restarts this is an important retained safety guard. After132, dying namespace check remains first. Standalone adaptation could place fatal guard before current restart without132, but tested fixture uses132; no standalone133 adaptation claim. Not an independent new OOM/LMK policy fix.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. Original133 PASS after context-adapted132 in scratch. Checked late namespace→fatal→publication order and modeled error distinctions.
- **Dependencies/scope:** 132 supplies original namespace-before-fatal context/precedence, not an enum-interface prerequisite.133 must remain when136 skips late restart for threads and137 removes it for processes; do not select restart removal without corresponding fatal protection.
- **Before implementation:** If selecting later series, retain this guard and validate SIGKILL/OOM during clone/fork, early and late signal windows, error cleanup, cgroups and pidfd resource handling under BPF fork overlay. No activation or runtime speedup inferred.
- **Decision/application:** pending / not applied.

### PHX-134 — `1076673012c682011156e8d409a2399ad9b9744a`

- **Changes:** Add calculate_sigpending declaration/helper and invoke it at end of schedule_tail after child-TID write.
- **Electro finding:** Original applies independently. Helper locks current sighand, presets TIF_SIGPENDING and reuses existing recalc, ensuring required flags are set even for freezer-only state where recalc deliberately does not clear. Current recalc covers jobctl/trap-freeze, unblocked private/shared signals, cgroup frozen and freezing; unlike donor message, it does not test klp_patch_pending, so no complete livepatch guarantee. ARM64 ret_from_fork calls schedule_tail then ret_to_user, whose work mask includes SIGPENDING; source path supports native/AArch32 first-user slow path. Existing finish_task_switch/balance/preempt/child-TID sequence exact-inverts when call/blank removed; no BORE/CASS scheduling policy changes. Adds locking/work to each first task run, not a free standalone performance optimization.
- **Check:** PASS original standalone/submitted-order; reverse FAIL. Original replay in ordered fixture PASS. Extracted recalc/calculate host probe128 combinations of jobctl/private/shared/blocking/cgroup-freezer/freezing PASS; scheduler exact inverse and ARM64 entry/work-mask inspection PASS, not target/runtime proof.
- **Dependencies/scope:** Independent supplied patch;135 relies on it to replace explicit ptrace flagging,136/137 rely on it to discover new child stop/pending state. Neither unrelated old syscall-helper work nor B014 typed signal spine is required for134.
- **Before implementation:** Build/test native/AArch32 and kernel-thread starts, ptrace, group stops, pending blocked/unblocked signals and freezer-only starts; check IRQ/preemption/lockdep context. Preserve BORE/CASS/PELT and freeze policy. Do not assume donor livepatch claim applies to current recalc or claim measured fork benefit.
- **Decision/application:** pending / not applied.

### PHX-135 — `fe723bb4d061448cd33a0c6f797089077123c51b`

- **Changes:** Remove explicit child TIF_SIGPENDING assignment from ptrace_init_task, retaining stop/jobctl state.
- **Electro finding:** Original patch applies alone, but is not semantically standalone: without134, a newly traced child can lose the flag that makes it take the first-user stop path. With134, schedule_tail recalculates it from JOBCTL_TRAP_STOP for seized tracing or queued SIGSTOP for classic tracing. Child ptrace linking, credentials, jobctl/stop setup and parent relations remain unchanged. No tracing feature or performance improvement.
- **Check:** PASS original standalone/submitted-order; reverse FAIL. Original135 after134 PASS; first-run flag behavior covered by source/host pending model. No actual debugger/ptrace validation.
- **Dependencies/scope:** 134 must supply reliably executed first-run pending calculation before removing the old assignment. Clean standalone text check is not implementation readiness; no requirement to select135 merely to use134/136/137.
- **Before implementation:** Never select by itself. Test classic and PTRACE_SEIZE fork/clone/exec stops, tracer attach/detach and first user instruction behavior with134 on ARM64/AArch32. Keep tracing/security relationships unchanged.
- **Decision/application:** pending / not applied.

### PHX-136 — `baa572b94e4f73e043502a6bbb4cb60a88313a21`

- **Changes:** Limit old late restart to non-CLONE_THREAD forks; add task_join_group_stop and call before publishing new thread.
- **Electro finding:** Changes thread creation behavior, not mere cleanup. Under held sighand siglock, helper copies current pending stop signo and STOP_PENDING|STOP_CONSUME into eligible child, increments group_stop_count only on successful jobctl setup, and is called after ptrace initialization but before thread-list visibility. Existing task_set_jobctl_pending refuses fatal/exiting tasks;134 makes new jobctl visible via first-run pending flag.133 is needed to keep SIGKILL abort when thread late signal restart is skipped. Source/jobctl logic concerns ongoing group stops, not a new scheduler policy or just a numeric SIGSTOP assignment. Process fork late restart remains until137. Host probe covers no-stop, successful join, fatal child and exiting child; success sets pending flag.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS donor helper/header plus current-preserving fork adaptation after133/134, with join-before-thread-publication guards and4 extracted host stop cases. Not real job-control concurrency proof.
- **Dependencies/scope:** 133 and134 provide safety/first-run interfaces.132 is original context/precedence;135 removal is not needed because extra explicit ptrace flag is harmless. No B014 typed core required for136 alone. Current clone3/scheduler/pidfd/BPF fork hooks must stay.
- **Before implementation:** Under BPF fork overlay, test clone threads during SIGSTOP/TSTP/TTIN/TTOU and SIGCONT, group-stop counters/completion, ptrace classic/seize, killed/exiting children, freezer and OOM. Preserve final fatal check, lock ordering and first-user pending handling; no measured thread creation gain claimed.
- **Decision/application:** pending / not applied.

### PHX-137 — `2eadaa3b792ce89350a5779e0838d684330b26cb`

- **Changes:** Check existing signals before expensive copying, register per-fork multiprocess signal bitmap, remove late ordinary restart and copy delayed bits to child before visibility.
- **Electro finding:** The substantive progress/correctness change B014 prepared for: avoids repeatedly discarding expensive fork work for later single-process periodic signals, and records multiprocess events for non-thread children. Already pending signals still cause early ERESTARTNOINTR; late SIGKILL and dying-namespace aborts remain. Initializes multiprocess head in init_signals and new signal_struct, initializes stack node even for unlinked thread/idle paths, registers under current siglock before copying, copies child bitmap before PID visibility, and unlinks on success/failure under siglock. Collector records type>TGID (PGID/SID/MAX), cancels opposing stop/continue bits, and copies bits rather than siginfo queues. It runs only on out_set; ignored/coalesced/overflow short-circuits and realtime metadata require explicit regression tests, not blanket all-signal correctness claims. Prior B014 bool-only fcntl bridge is insufficient now: it collapsed PGID to TGID. New scratch lossless boundary preserves legacy PID(process)→TGID, MAX(thread)→PID, PGID→PGID/SID→SID while keeping NULL-safe iterator/old ownership ABI, avoiding unsafe124 entirely. No commit here fixes124. fork.c is BPF-sealed; struct signal layout and boot/failure paths change, requiring full target validation and explicit overlay, not donor whole-file replacement.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS donor non-fork changes plus current clone-args/hook-preserving fork adaptation on lossless typed spine. Source lifetime/publication/error guards and extracted collector/pending/stop host probes PASS. No real fork-starvation reproduction, concurrency, ABI, boot or performance proof.
- **Dependencies/scope:** Tested fixture uses B014126→128→129→130→131 with lossless legacy fcntl boundary, then132/133/134/135/136.130 is context for original131 typed timer call, not inherently a fork-race fix;135 is optional redundant-flag cleanup. Rich type flow, fatal guard133, first-run pending134 and thread group-stop handling136 are substantive interfaces.132 supplies error priority/context. No unsafe124/125 or new KDB127 prerequisite. Earlier B014 bool bridge remains valid for its old boolean-only scope, but cannot be carried unchanged into137; this is a new cross-batch requirement, not a silent rewrite of prior review.
- **Before implementation:** Only pursue as an explicitly approved coherent correctness backport. Preserve BPF/clone3/pidfd/MGLRU/cpufreq and scheduler hooks; record new fork delta without resealing. Stress process-group/session/broadcast signals, fasync PGRP, blocked/ignored/already-pending/coalesced/realtime cases, stop/continue, multiple simultaneous forks, allocation/cgroup/pidfd failures, idle/kernel threads, SIGKILL, namespace teardown, ptrace/freezer and native/compat clone/clone3/vfork/exec. Measure periodic-signal progress rather than promising general phone speedup.
- **Decision/application:** pending / not applied.

### PHX-138 — `4cb413573b4e1e97fe2a4b4ec84f0b5543fc88d5`

- **Changes:** Return early for failed copy_process and flatten _do_fork success path.
- **Electro finding:** Electro still has nested success/error block, but donor uses old scalar _do_fork/copy_process ABI and lacks current pre-wakeup MGLRU registration. Independent scratch adaptation flattens current _do_fork(kernel_clone_args*) only, keeps pidfd/parent_tid alias validation, latent entropy on error, all successful operations/order, cpufreq allocation, trace/ref/child-TID/vfork handling and task_lock/lru_gen_add_mm/task_unlock before wakeup. Token equality verifies success body after removing moved declarations/dedenting. Not already fully integrated, not new clone semantics or measured performance benefit; never transplant whole donor function.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS independent generated current-ABI adaptation and exact replay after137; success-body token/order preservation PASS. Source reasoning only, no target/vfork runtime probe.
- **Dependencies/scope:** Independent of132–137 and B014 signal series. Earlier clone3/kernel_clone_args integration must be preserved rather than forced back to donor API. Still touches immutable BPF fork.c, so implementation needs explicit delta/check chain.
- **Before implementation:** Defer unless style cleanup is wanted. If selected, retain current ABI/MGLRU/validation and test error, clone3/pidfd/parent TID, VM/vfork/ref/trace cases under explicit BPF fork overlay. Do not equate flattening with speedup.
- **Decision/application:** pending / not applied.

### PHX-139 — `9dc6b001f30c5ad63b3caf5a157751be46451a37`

- **Changes:** Add explanation before existing CLONE_NEWNS|CLONE_FS rejection.
- **Electro finding:** Comment-only. Existing CLONE_NEWNS|CLONE_FS and CLONE_NEWUSER|CLONE_FS EINVAL checks remain unchanged. Root here means shared root/cwd filesystem context, not uid/root privilege. No namespace feature activation, new restriction or runtime benefit. Donor context expects137 delayed declaration and old function locals; independent comment relocation on current clone-args function passes with identical code tokens. Even a comment changes sealed fork.c file hash, so any implementation should preserve historical BPF seal and record an explicit later delta.
- **Check:** FAIL original standalone/submitted-order; reverse FAIL. PASS independent relocated comment adaptation and replay after137; code-token inverse identical.
- **Dependencies/scope:** 137 provides donor declaration context only; no semantic dependency. Independent comment relocation works without the signal series.
- **Before implementation:** Optional documentation only; do not change namespace/CLONE_FS validation or enable namespaces. Preserve root/cwd meaning and follow sealed-source delta bookkeeping if selected.
- **Decision/application:** pending / not applied.

## PHX-B016 — prior-work filter; one missing clone3 documentation block

Ten links submitted. **The functional work in nine is already covered by the
approved qcom_sm8150 clone3/checkpoint topic** and are excluded without individual duplicate records
or IDs, as requested. Source and historical-diff comparison was used, not merely
title/SHA matching. Existing implementation, UAPI, tests/build registration and
MAINTAINERS coverage are present in integrated `112f5e51e` / current source. Later
fixes (64-bit flags, stack representability, per-namespace allocation unwind,
checkpoint capability alternative) are preserved, not replaced with older donor
code. Topic notes: `Documentation/dev-tools/clone3-backport.rst`.

Only submitted **link 4** is genuinely missing: syscall-local kernel-doc.
The 17 reviewed/dedup source paths remain byte-equal to published `c6de` baseline.
This does not imply new device coverage or perfect existing selftests.

### PHX-140 — `fb7c1070b69ebc8a99a474261efef35a67f124b8`

- **Changes:** Add 11 kernel-doc comment lines before `SYSCALL_DEFINE2(clone3)`.
- **Finding:** Syscall implementation exists, this particular comment does not.
  Existing UAPI struct docs and topic RST are not function-local kernel-doc.
- **Check:** Original standalone/scratch apply PASS; reverse FAIL; C token
  stream identical. No kernel-doc/target build or runtime test.
- **Recommendation:** Optional documentation only. If selected, clarify parent
  PID/TID versus child 0 return semantics; no behavior or performance benefit.
- **Provenance:** `kernel/fork.c` still matches immutable BPF after-image
  `eb72ec173b2be08338d1db7174bfaa3d408cb8f836adadd8f9090d755ce2ad26`.
  Even comments need a later delta/check record if approved, not resealing.
- **Decision/application:** pending / not applied.

**Incidental pre-existing test issue:** integrated clone3 selftest's successful
`call_clone3()` path returns `-1` after reaping a status 0 child although callers
expect 0. Present in `112f5e51e`, confirmed with the extracted existing function and
fake syscall/waitpid only. Left unchanged; not a new duplicate-commit record,
not evidence of a kernel clone3 failure, and not a real clone/device test.

No production/config changes, implementation, commit/push or CI. Ledger now
**140 pending / 0 implementations**; prior 139 entries and 15 batches preserved.

## PHX-B017 — clone3 follow-ups, filtered against prior work

Ten links submitted; **five already-covered functional changes excluded without
new entries or IDs**. Source/provenance checks, not SHA matching alone:
existing pidfd poll typing, set_tid suite/helper/build wiring, unavailable-syscall
skips and ARM64 explicit TLS handling already exist. ARM64 userspace also already
gets `__NR_clone3=435` from the unconditional generic UAPI entry: preprocessing
before/after the proposed macro move confirms the number is unchanged. Macro
placement differs, but its functional export fix is redundant here.

The five genuinely missing/partial items retain submission positions below.
All **30** source/support paths remain identical to published `c6de`; no patch
was applied to production. Previous 140 entries and 16 batches preserved.

| Stable ID | Link | Donor | Recommendation |
|---|---:|---|---|
| PHX-141 | 3 | `ab79a5f55ad7ce03dcf090268b36b7be8768cf04` | Test-output flush candidate; preserve local failure sentinel |
| PHX-142 | 4 | `402442a82754c648578601f028aed5c89bee6159` | Partial prior coverage; correct missing accounting, **not donor arithmetic** |
| PHX-143 | 5 | `9f1d9277c35e2a21c0471855ad1ee0860f9adb46` | Optional PID-unwind regression cases; needs coherent counter integration |
| PHX-144 | 9 | `bed33cdabed91806b80e1b3a1b6c8c137cbd035e` | Native ARM32 TLS correctness candidate; not miatoll ARM64 compat path |
| PHX-145 | 10 | `45f802b4e6ffefbd3b5f1a4f39a95f0dc505add0` | Compile-time TLS assertion; audit ARM/Xtensa support before broad adoption |

### PHX-141 — flush selftest stdio before clone3 and child exit

Shared wrapper has no flushes; set_tid has four direct `_exit()` calls. Donor
last hunk would overwrite local nested-failure handling. Scratch adaptation
flushes stdout/stderr before syscall and in `child_exit`, retains sentinel255,
all capability/namespace/syscall skips and old framework compatibility. Mock
flush/status checks and independent/replay text checks PASS; original apply
and reverse FAIL. Test-output correctness only, no kernel behavior/speed gain.
Decision/application: **pending / not applied**.

### PHX-142 — exact nested test counts are still incomplete

Original false-success mode already has local protection: nested failure sends
255, parent records failure, final exit checks failure/error counts. Do not
reimplement that as new work. Exact pass/fail merging remains missing.

**Do not apply donor verbatim:** `pass += 4 - (parent_fail - child_fail)` has
reversed delta. With 10 passes, 0 parent failures and 1 child failure, it gives
**15 passes / 1 failure**, not **13 / 1**. The exact extracted unsigned-counter
model covered 20 cases; 16 with new child failures had wrong pass totals.
Normal-exit/signal handling and inherited parent failures also need care.
Original/reverse text checks FAIL. No corrected merge implementation or real
nested test was claimed. PHX-141 supplies donor helper context only, not a
semantic requirement for fixing counters. Decision: **pending / not applied**.

### PHX-143 — PID reuse after allocation-error regression tests

Missing cases request PID43 with invalid ancestor PID, then retry43 with valid
ancestor PID, and raise plan27 to29. Actual kernel already frees each allocated
PID through its own namespace; this is regression coverage, not that kernel fix.
Donor accounting hunk depends on preceding donor merge and repeats its bad delta
with6. Scratch BODY/plan-only adaptation applies independently and after141,
retains all local guards/sentinel, but **is not a completed counter-integrated
suite**. Needs correct PHX-142 interface plus six nested tests. Original/reverse
FAIL. Current miatoll `PID_NS=n` makes this suite skip; no namespace activation
or device coverage implied. Decision/application: **pending / not applied**.

### PHX-144 — explicit TLS on native32-bit ARM kernels

`arch/arm` still has `copy_thread` reading legacy `ARM_r3`; generic clone3 passes
TLS through `args.tls`. ARM advertises clone3 but lacks TLS-helper selection.
Original patch selects helper and uses explicit TLS; standalone/scratch replay
PASS, reverse FAIL. Legacy ARM `CLONE_BACKWARDS` argument plumbing already exists.
No ARM cross-build/TLS execution was run. **AArch32 apps on miatoll ARM64 use
`arch/arm64`, already converted**, not this code. Optional for native ARM kernel
support; not a phone optimization. Decision/application: **pending / not applied**.

### PHX-145 — reject clone3 builds without explicit TLS helper

Guard is absent; nearby generic compatibility wrapper is not this assertion.
Original/reverse FAIL because current helper declaration/context differs;
literal-block relocation/replay PASS without changing existing code tokens.
Extracted guard matrix accepts ARM64/x86 and modeled ARM-after144; rejects
ARM-before144 and Xtensa. **Xtensa also advertises clone3 but lacks the helper**,
so144 alone does not cover every configuration. The guard detects missing TLS
support; it does not implement it. Require an explicit reviewed architecture
support policy, not a fake Kconfig select or silent feature removal.

Even guard/comment insertion changes BPF-sealed `kernel/fork.c`; preserve seal
`eb72ec173b2be08338d1db7174bfaa3d408cb8f836adadd8f9090d755ce2ad26`
and record a later explicit delta if approved. No full Kconfig/target build or
runtime validation. Decision/application: **pending / not applied**.

**Persistent test limits:** earlier `clone3.c` successful helper return-1 bug
remains unchanged; these patches do not fix it. Old framework skips exit0, so
exit0 alone proves no coverage. No real clone/namespace/TLS operation, device,
performance or target-build proof from the source/host/preprocessor checks.
Ledger: **145 pending / 0 implementations**. No production/config edits, CI,
commit or push.

## PHX-B018 — PID errno follow-up; capability topic already covered

Ten submitted links: **eight already-implemented capability/refactor/test changes
excluded without new duplicate entries or IDs**. All eight primary changed-line
inventories match the prior approved qcom_sm8150 donors after whitespace
normalization. Current implementation, local adaptations and permissions were
checked too—not merely titles or apply/reverse status.

Already-covered scope: CAP_CHECKPOINT_RESTORE (40)/helper/SELinux mapping; set_tid
and ns_last_pid checks in target PID namespace's user namespace; map_files/tty
checks in initial user namespace; separated PR_SET_MM arithmetic/auxv/capability
checks; current-userns exe permission; and non-root capability clone3 test plus
build/ignore registration. Keep later exe permission **EPERM**, not older donor
EINVAL. Keep local direct capget/capset test instead of private libcap-layout
casting or a new libcap link dependency. No capability grants/security-policy
bypass/config activation are implied by this existing coverage.

Only links **1 and 2** are missing. All **20** inspected source/support paths
remain byte-identical to published `c6de`; prior 145 entries / 17 batches preserved.

| Stable ID | Link | Donor | Recommendation |
|---|---:|---|---|
| PHX-146 | 1 | `902f37018c61666b62634d9646571bd301b7acec` | Correctness candidate: restore late alloc_pid ENOMEM |
| PHX-147 | 2 | `11d90c92a50befc154793880d12f1b662c9d4c6c` | Optional explanation after PHX-146; comment only |

### PHX-146 — restore late PID-allocation error value

`alloc_pid()` starts with ENOMEM, but successful explicit-PID permission checking
leaves `retval=-EPERM`. If subsequent proc preparation fails or final namespace
publication is disabled, cleanup currently returns that stale permission error.
Donor adds only `retval = -ENOMEM;` after the allocation loop. It does **not**
change early invalid PID/size/reaper errors, genuine denied capabilities, IDR
collision/EEXIST, allocation failures, success, or own-namespace cleanup.

Original independent apply PASS, reverse FAIL; exact original PHX-146 → PHX-147 scratch
sequence PASS. Extracted baseline/fixed C host model covered 16 scenarios:
**four late explicit/partial-PID failures change EPERM→ENOMEM**, others retain
early errors/success; fake IDR/ref cleanup assertions unchanged. This is not
real allocation/proc failure injection or namespace/race/device validation.

Recommend as a small ABI/error-reporting correctness candidate, independent of
pending Phoenix fork/signal/test chains. Current `PID_NS=n` limits ordinary
nested-namespace relevance; no phone speedup or namespace activation claimed.
Decision/application: **pending / not applied**.

### PHX-147 — document historical ENOMEM behavior

Eight-line comment explains why namespace allocation shutdown can return ENOMEM
rather than a seemingly more descriptive error. Missing; original standalone
and reverse FAIL, original apply after PHX-146 PASS, C token stream unchanged from
PHX-146. Comment does not implement the errno fix.

Optional with PHX-146. If selected, clarify donor's “child subreaper” wording:
namespace init/reaper shutdown is meant, not any ordinary process marked by
PR_SET_CHILD_SUBREAPER. No functional/performance benefit.
Decision/application: **pending / not applied**.

### Provenance and validation limits

Both proposed changes touch BPF-sealed `kernel/pid.c`. Current immutable
historical after-image remains
`8c548c9a4893d593d7fa3512e5de87913fff7065a4f1e8a23c41969986c4485c`.
Any later approved change—including comments—needs an explicit delta/check
record, **not resealing**. `kernel/fork.c`, BPF/SUSFS metadata and pre-existing
local BPF runtime-test/manifest differences remain untouched.

No production/test/config implementation, target build, device, CI, commit or
push. Existing clone3 success-return and counter/architecture issues remain
unchanged. Ledger: **147 pending / 0 implementations**.

## PHX-B019 — final supplied batch

Four links submitted. **One already-implemented xperm compatibility change
excluded without a new duplicate entry/ID**: current evaluator already has both
warn-once replacements, exact reverse/forward identity passes, and the function
matches local original `4afc`. This is not a claim of support for every newer policy
version or permission. Three missing items follow in original submission order.

All 17 review/support source paths remain identical to published `c6de`. Existing
local BPF runtime-test/manifest differences are preserved. Prior 147 entries and
18 batches unchanged. **This completes source review of user-supplied links**,
not an exhaustive audit of the donor's entire history.

| Stable ID | Link | Donor | Recommendation |
|---|---:|---|---|
| PHX-148 | 1 | `f67711cd28bb0626017769df4d739e575ec31e00` | Correctness candidate: install pidfd outside signal/tasklist locks |
| PHX-149 | 2 | `b2d4ff353a189bb21c44bb0246b7a274decb84e8` | Defer unless ROM needs FunctionFS endpoint labeling/relabeling |
| PHX-150 | 3 | `0f1a454279f3981187f02af6ef9f5e6027549621` | Conditional securityfs per-file labels; no new relabel support |

### PHX-148 — move pidfd installation outside spinlocked region

Current `copy_process` installs pidfd while holding `sighand->siglock` and
`tasklist_lock`. This tree's `__fd_install` calls `might_sleep()` and can wait
for `resize_in_progress` after dropping sched RCU. Thus the unsafe region is
relevant even though donor's newer lockdep splat describes a different slow
path. Move only the conditional installation to after both unlocks, before fork
connectors; retain local `sched_post_fork`, final abort checks, PID publication,
clone3/pidfd semantics and exact `fput`/unused-fd error cleanup.

Original independent/reverse FAIL due local hook context. Narrow independent
relocation PASS; exact move inverse, cleanup identity and order guards PASS.
Eight pidfd/failure/resize combinations per old/new ordering: two old successful
installations under locks, zero after move; modeled failure cleanup unchanged.
Fake locks/waits are **not** real lockdep/resize/concurrency proof. Target stress
shared file tables, resize/close/dup2, native/compat clone3, pidfd lifetime and
late failure paths before claiming fixed device behavior. No speedup measured.

BPF fork seal remains
`eb72ec173b2be08338d1db7174bfaa3d408cb8f836adadd8f9090d755ce2ad26`;
future approved relocation needs explicit delta/check record, never resealing.
No pending signal-chain prerequisite. Decision: **pending / not applied**.

### PHX-149 — FunctionFS labels and in-core relabeling

Both FunctionFS classification additions are missing; original standalone PASS,
reverse FAIL. **Actual Android diff has no policycap gate**, despite the earlier
upstream wording in its message. It adds no policycap-array slot; FunctionFS
changes are unconditional in these hooks, with cgroup's existing gate retained.

Genfs labels are filesystem-type/mount-relative-path based, not unique per USB
mount. Multiple FunctionFS instances can share genfscon rules; userspace endpoint
relabeling needs correct ROM policy. Existing owner/capability, RELABELFROM,
RELABELTO, ASSOCIATE and transition checks remain, and VFS has an in-core LSM
fallback—not persistent filesystem xattrs. Current USB_CONFIGFS_F_FS selects
FunctionFS, so this can affect real USB/ADB labels rather than inert plumbing.

**Defer absent a concrete ROM requirement.** Validate enforcing policy/default
labels, ep0/data endpoints, multiple mounts, authorized/denied relabeling, USB
reconnect/recovery and KSU ADB-root compatibility. No ROM policy supplied/edited;
no permissive mode or blanket allow authorized. No general security/speed claim.
Decision/application: **pending / not applied**.

### PHX-150 — securityfs genfs labels, not chcon support

Missing `SE_SBGENFS` classification enables per-file policy labels. It does not
add securityfs to genfs-special handling, so it does **not** add relabel support
for normal GENFS securityfs mounts. Original patch follows PHX-149 for text context;
original after PHX-149 PASS, standalone/reverse FAIL. Independent securityfs-only
insertion PASS with special-handling predicate identical to baseline: **PHX-149 is
not a semantic prerequisite** and must not be imported implicitly.

Check resolved SECURITYFS configuration, actual mounts/consumers and ROM genfscon
rules first; the inspected miatoll defconfig does not explicitly select
SECURITYFS/IMA, and no resolved target configuration was built. IMA example in
message does not enable IMA. Conditional policy feature only; test labels and
allow/deny decisions without claiming new setxattr support.
Decision/application: **pending / not applied**.

**Checks/limits:** extracted classification predicates/flag statements passed
196 filesystem/cgroup-policycap/label-behavior combinations across four variants
(baseline, FunctionFS, both, securityfs-only). Other classifications unchanged;
only FunctionFS gains GENFS relabel classification. This is not a real policy
lookup/load, inode-label/access decision or USB/device test. Neither SELinux
change has target policy/boot/runtime validation.

## Historical source-review closeout (before implementation approval)

**150 recorded reviews / 150 user decisions pending / 0 Phoenix implementations.**
The user marked this as the last batch; no further intake/work is assumed.
At that historical checkpoint all recommendations were awaiting decisions. The later explicit approval and implementation progress are recorded below.
No production/test/config edits, kernel build, CI, commit or push. Earlier
blocked/conditional findings and pre-existing test defects remain unresolved;
this closeout is not blanket approval or device/performance certification.

## Approved implementation — checkpoint 01 (historical; superseded by checkpoint02)

The user explicitly authorized the preceding recommended/optional list, including
adaptation and necessary fixes. **87 items approved; this is not approval of the
45 deferred or 18 skip/equivalent recommendations**, raw donor replacements,
configuration activation, publication or CI. Conditional scope remains explicit:
PHX-137 coherent package, PHX-135 only with PHX-134, PHX-143 requires correct accounting, PHX-120 only
the annotation subset. Deferred standalone items remain untouched.

### Applied locally in phase 01

- **PHX-010:** shared RR timeslice helper, native/compat copyout only on success;
  old `set_fs` compat wrapper removed. Update helper kernel-doc for kernel buffer.
- **PHX-022:** syscall-helper documentation; place header comment above existing
  local kernel helper, without removing local declarations.
- **PHX-139/140:** filesystem-root/namespace and clone3 syscall comments; clarify
  parent PID/child 0 return semantics.
- **PHX-141:** common stdio flushes and flushing set_tid exits; preserve all local
  skip/capability checks and failure sentinel 255.
- **PHX-146/147:** restore late PID errno and explain namespace-init/reaper
  behavior without misleading ordinary-subreaper wording.
- **PHX-148:** move pidfd installation after both locks are released; retain
  sched_post_fork, final abort checks, PID publication and exact failure cleanup.
- **Incidental existing test fix:** clone3.c successful helper now returns 0;
  reject non-normal child exit before WEXITSTATUS. No duplicate review ID.

Evidence: [`implementation/phase-01.json`](implementation/phase-01.json), exact
baseline-aware [`phase-01.diff`](implementation/phase-01.diff). These are local
changes, **not commits**. Historical BPF metadata/seals remain unchanged; explicit
phase overlay records new fork/pid after-images. No stale-HEAD reset/mass staging.

### Validation and outstanding work

- PASS new extracted-source tests with five deliberate regression controls:
  RR native/compat uaccess, 16 PID cases, 5 selftest outcomes and pidfd source-order
  guards. Operations mocked; no real clone/namespace/locking/RCU proof.
- PASS all six existing BPF host suites with negative controls: core, JMP32,
  atomics, softirq, dynamic lockdep and timer lifetime.
- PASS proper ARM64 `headers_install` and all four clone3 programs compiled with
  host GCC `-Wall -Wextra -Werror` against exported UAPI. Programs not executed;
  no resolved target kernel config. Raw unexported-header build first rejected,
  then proper export used. This is not an ARM64 kernel build.
- PASS exact phase-overlay replay/inverse, unrelated existing file hashes and
  kernel-doc warning comparison. No config/SELinux/SUSFS/KSU/BPF metadata or
  pre-existing runtime-test/manifest changes introduced.
- **Exact AOSP Clang r614150 absent. No kernel build, boot/device test, CI,
  commit or push. No claim of deployment safety or performance improvement.**

**8 local applications / 79 approved still unapplied / 63 decisions pending.**
This is a staged checkpoint, not completion of the requested 87-item application.
The large signal/fork project and remaining optional cleanups are still pending;
do not move on to deferred implementation or describe all approved work as done.

## Approved implementation — checkpoint02 (historical; superseded by checkpoint03)

The user then said **“Fix and apply, make sure not break anything”** after the
45-item defer list. `PHX-APPROVAL-002` records those45 as approved for corrected
adaptation in addition to the original87; it supersedes the old deferred-discussion
sequence, not the safety/config/publication constraints. **132 approved total;
18 skip/equivalent recommendations excluded.** Historical review findings and
checkpoint01 evidence are retained, not rewritten as if unsafe donors were safe.

### Nine corrected/scoped local applications in phase02

- **121:** generic compat macro forward prototype only. Retain x86 declarations;
  deleting them without matching conversions is deliberately excluded.
- **124/125:** coherent TID/TGID/PGRP ownership producer/decoder conversion,
  correct local `f_delown` context, and **both NULL-task guards** before SIGIO/
  SIGURG dispatch. Preserve current int/group signal boundary, owner/RCU/group
  locks and permission hooks. Typed signal/fork126–137 remains queued.
- **142/143:** reject donor arithmetic. Dedicated pipe transports all six
  **child-only counter deltas**, retains parent failures, validates overflow/
  expected count/abnormal exit, and rejects missing/short reports without hanging
  after wait. Explicitly supersedes phase01's255 sentinel and its test guard.
  Two PID43 failed-ancestor/reuse cases; six nested cases, plan29. PID_NS stays off.
- **144/145:** native ARM TLS conversion and missing-TLS clone3 compile guard.
  Audit found Xtensa needed a **real** backend conversion first; adapted upstream
  [`c346b94f8c5d`](https://github.com/torvalds/linux/commit/c346b94f8c5d1b7d637522c908209de93305a8eb).
  Do not merely advertise capability. ARM64/x86 backends already support explicit
  TLS; native32 ARM conversion is not a replacement ARM64 compat backend.
- **149/150:** actual Android **unconditional FunctionFS** genfs/special labeling
  (no policycap-array ABI extension), plus securityfs genfs labels. **Securityfs
  gains no `chcon`/setxattr support.** No policy allow rules/permissive workaround.
  Enforcing ROM USB/ADB/multiple-mount and per-file label tests remain required.

Evidence: [`implementation/phase-02.json`](implementation/phase-02.json), exact
19-file replayable [`phase-02.diff`](implementation/phase-02.diff). Phase01
source/test hashes chain into this overlay; old metadata/seals remain untouched.
The SELinux hooks after-image is now explicitly changed for approved149/150,
not incorrectly described as byte-identical to checkpoint01.

### Validation performed and limits

- PASS both Phoenix host suites with **13 deliberate regression controls**:
  phase01's5 plus phase02's8. Phase02 includes75 counter assertions (ordinary host
  fork/pipe),56 real genfs predicate cases,512 extracted TLS assignments,6 generic
  compat macro arities, owner codec/dispatch and compile-guard source checks.
- PASS all six existing BPF host suites and their negative controls, rerun.
- PASS out-of-tree ARM64 UAPI `headers_install`; all four clone3 programs compile
  with host GCC `-Wall -Wextra -Werror`. **Not executed; not a kernel build.**
- PASS exact19-file forward/inverse replay, phase01 source/test hash chaining,
  unrelated pre-existing file hash preservation, `git diff --check`, and strict
  checkpatch on production/kernel+selftest paths (0errors/0warnings/0checks).
  Its new-file MAINTAINERS heuristic was reviewed: existing PIDFD API directory
  coverage includes the new clone3 header. Host mock fixtures are not the scope
  of that production-style result.
- Config defaults, manual-only CI, KSU/SUSFS, historical BPF metadata and the two
  pre-existing BPF corrections remain unchanged. Native ARM/Xtensa architecture
  capability selectors accompany real backends, not miatoll feature activation.
- **Exact AOSP Clang r614150 absent; no target kernel build, device/boot/locking/
  RCU/real clone3 namespace/enforcing-ROM tests. No commit, push or CI.**

**17 local applications / 115 approved still queued / 18 excluded skip/equivalent
recommendations.** Includes121's documented scoped subset, not full donor patch.
This is not completion of132, a deployment recommendation or a zero-breakage claim.

## Approved implementation — checkpoint03 (current)

The latest instruction authorizes **applying/fixing all115 remaining items and
then pushing to the same branch**, recorded as `PHX-PUBLISH-001`. This
supersedes historical no-publication gates in checkpoints01/02. It does not
include the18 skip/equivalent recommendations, production feature activation,
publication to main, or workflow dispatch. All115 source adaptations are now
integrated locally: **132 total / 0 queued / 18 excluded**. This includes the
011 module-only legacy ABI retention and explicitly scoped119 same-guard prototype organization,120 annotation-only
changes and121 generic-only prototype addition—not blind donor substitution.

### Integration and fixes

- Keep legacy eventfd GPL read/get exports for unaudited vendor-module ABI
  consumers while retaining folded native paths.106 extracted eventfd cases
  cover flags/allocations/refcounts/waits/signals/counter/copyout failures; the
  approved PHX014 allocation/error-precedence change remains explicit.
- Complete socket/IPC/filesystem/process/MM helper series with all in-tree
  caller conversions. Preserve native/compat ABI names and parameter types,
  time64 pselect/ppoll code, mount retry/root logic and custom hooks.
- Complete126–137 typed signal/fork dependency chain, including KDB, timers,
  fork collector initialization/removal on success and every abort, fatal
  signal handling, group-stop membership and schedule-tail recalculation.
  Retain `kernel_clone_args`, BPF hooks, phase01 pidfd placement and MGLRU.
- Include the local Simple LMK caller absent from the donor. Fix donor004's
  signed high-bit shift in big-endian sigset conversion using unsigned long.
- Native ARM's real TLS backend compiles. Its fork check exposed an existing
  malformed optional asm-clobber list; fix the IP macro position and use UAL
  `sbcscc` mnemonic spelling, without changing ARM64's different header. Xtensa remains source/host-audited.
- Preserve every native syscall prototype type/guard and legacy weak fallback;
  remove only duplicate madvise. Keep sys32 quota, clone3, BPF and ppc symbols.
- Extend SUSFS provenance via a narrow, replayable **six-file overlay**, not
  rewriting its immutable import or broadening previous manager/BPF overlays.
  All original KSU/SUSFS/NoMount hook/config-token inventories remain present.

Evidence: [`implementation/phase-03.json`](implementation/phase-03.json),
[`phase-03.diff`](implementation/phase-03.diff), helper-body audit and
`susfs-syscall-overlay.{json,diff}`. Historical phase01/02 evidence remains
unchanged and chains into phase03 before-images, including test evolution.

### Validation checkpoint

- PASS all three Phoenix host suites and **24 deliberate regression controls**.
  New coverage includes97 actual wrapper argument/return contracts,1920 signal
  collector/queue cases and800 high-bit LE/BE sigset roundtrips plus uaccess errors.
- PASS all six BPF host suites/negative controls, KSU104-file provenance/wiring,
  FinaSU, NoMount and SUSFS models/provenance with18 negative controls.
- PASS exact pinned **AOSP r614150 / Clang23.0.1 / prebuilt
  3b86e40facfff1eab4065614255d573293c10373** active ARM64 integration compilation.
- PASS compile-only optional SYSVIPC/NUMA/FANOTIFY/DEVTMPFS/KEXEC/PID_NS,
  Simple LMK, KDB and memory-failure paths in separate scratch profiles.
  **Production defconfig/defaults and manual-only CI are unchanged.**
- PASS full miatoll `dtbs`, `Image.gz-dtb`, `dtb.img`, `dtbo.img` and modules,
  including the final rebuild with legacy module exports retained. Release:
  **4.14.357-electro**. Artifact sizes/SHA256 are recorded in phase03, not committed
  as binaries. Implementation published as [`f885b9efa8df`](https://github.com/lezyss/Kernel_electro/commit/f885b9efa8df6eee4701c8f2d5c009ecf2f97af1)
  on the existing branch; no CI dispatched.
- PASS exact forward/inverse phase03 overlay replay (115 paths), source/test
  chains,128 first source preimages against the publication parent, and
  selected source-only whitespace check. Portable host checks also pass from
  the exact selected Git source tree without the two unpublished BPF fixes.
- Strict checkpatch has style diagnostics, largely moved old declarations and
  compat switch formatting. Do not describe this as a clean style check.
- **No boot/phone, actual concurrency/RCU/locking/namespace, performance or
  enforcing ROM USB/ADB/multiple-mount policy validation.** FunctionFS remains
  unconditional; securityfs still does not gain `chcon`/setxattr support.

## Post-publication handoff

1. **132 approved scopes implemented and published / 0 queued / 18 excluded.**
   Source/evidence commit: `f885b9efa8df6eee4701c8f2d5c009ecf2f97af1`. See `PHX-PUBLISH-001`.
2. Complete miatoll image/DTB/DTBO/modules and native ARM process/fork compile
   checks PASS with exact AOSP r614150. All3 Phoenix suites/24 negative controls,
   full BPF host suites and security provenance/models pass on the selected Git
   source tree. Final linked artifacts preserve the legacy module exports.
3. Publication used an isolated index/verified remote parent. The ordinary local
   HEAD/index were intentionally retained to protect unrelated workspace work.
   The two local BPF test/manifest corrections were **not** transplanted; portable
   tests pass against their published-parent versions. Do not stage or discard
   unrelated files when continuing.
4. **No CI dispatch or automatic workflow activation.** Production defaults and
   the18 excluded implementations remain unchanged. No publication to main.
5. Next: device boot/smoke, enforcing ROM USB/ADB/multiple-mount policy, real
   concurrent clone/signal/namespace/RCU/locking and external module validation.
   The build/host evidence is not a zero-breakage/performance/runtime certificate.
6. Future donor links start at unused ID151/batchB020. Preserve all150 IDs and
   immutable phase01/02 evidence; use chained successors for future changes.

Final ABI adaptation: retain `sys_close` export and module-only legacy
`iov_shorten`/`sigset_from_compat` APIs, alongside the converted native paths.
PHX011 is scoped to removing the helper from non-module builds/in-tree API use,
not deleting unaudited vendor-module ABI. Legacy sigset conversion keeps its
original kernel-pointer semantics with unsigned high-half shifts.160 iovec and
800 high-bit legacy sigset cases pass; an export-removal mutant is rejected.
