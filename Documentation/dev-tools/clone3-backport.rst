.. SPDX-License-Identifier: GPL-2.0

==========================================
clone3 and checkpoint/restore backport notes
==========================================

Scope
=====

This tree includes the 24-commit clone3/checkpoint-restore topic reviewed from
LineageOS/android_kernel_qcom_sm8150, starting at 929183edf055 and ending with
the additional fixes 17a4db9ec43b, eb8eff544d75 and d05a02bda12f.  It provides
clone3 (syscall 435) on ARM, ARM64 (including AArch32 compat) and x86,
CLONE_CLEAR_SIGHAND, explicit PID selection, and CAP_CHECKPOINT_RESTORE (40).
It does not implement later clone3 extensions such as CLONE_INTO_CGROUP.
Unknown nonzero structure extensions are rejected, rather than accepted silently.

The version-0 64-byte and version-1 80-byte argument layouts are supported via
copy_struct_from_user().  Omitted fields are zero-filled.  Invalid exit signals,
unknown flags, incompatible signal flags and invalid stack address/size pairs
are rejected.  clone3 takes the lowest stack address and its size; on ARM64 the
kernel derives the top-of-stack pointer.  Legacy clone keeps its existing stack
pointer convention.  ARM64 uses the explicit TLS argument for both native and
compat children rather than reading a legacy syscall argument register.

Local integration
=================

* Preserve this tree's pidfd error propagation, references and cleanup.  Legacy
  clone cannot combine CLONE_PIDFD and CLONE_PARENT_SETTID.  clone3 can use both
  with distinct output pointers; aliasing those pointers is rejected.
* Keep the existing x86 stub32_clone argument swap and common sys_clone path.
  The local x86 compat clone3 table uses sys_clone3, not a newer __ia32_sys
  wrapper.  The unsupported-architecture fallback uses cond_syscall(sys_clone3).
* Pass 64-bit flags to copy_sighand, including on native 32-bit builds, and
  preserve the CONFIG_CLONE_BACKWARDS3 stack-size argument.  Reject stack
  addresses/sizes that cannot be represented by unsigned long.
* Unwind failed nested PID allocations in each allocated PID's own namespace,
  not repeatedly in the innermost namespace.  This is important when a requested
  PID collides in an ancestor namespace.

Permissions and configuration
=============================

CAP_CHECKPOINT_RESTORE is an alternative to CAP_SYS_ADMIN for the selected
checkpoint/restore operations; the existing CAP_SYS_ADMIN path remains.
Explicit PID selection and ns_last_pid use the target PID namespace's user
namespace.  map_files link following and TIOCSLCKTRMIOS check the initial user
namespace.  PR_SET_MM_MAP executable replacement checks the current user
namespace and returns EPERM for a failed capability check.  Other existing
access checks are retained.

The SELinux capability2 map includes checkpoint_restore.  Android policy must
be reviewed before granting it to a domain.  Adding the capability does not
implicitly grant it to applications or bypass SELinux/seccomp policy.

No device defconfig options are enabled by this backport.  In particular,
miatoll's PID namespaces remain disabled; namespace-dependent tests require a
separate configuration.  PR_SET_MM_MAP remains subject to
CONFIG_CHECKPOINT_RESTORE.  Existing release naming and LLVM build settings
are unchanged.

Validation and testing limits
=============================

The clone3 selftests live in tools/testing/selftests/clone3.  Export this tree's
UAPI headers before building them.  Compatibility helpers stay local to that
suite because this kernel's shared kselftest framework is older.  The
capability test uses capget/capset directly rather than libcap internals.
Known unsupported syscall/policy, namespace and capability prerequisites cause
explicit skips.  The existing framework treats skips as exit status zero, so
inspect TAP output; an exit status of zero alone does not establish coverage.

Userspace test compilation and extracted-function tests with mocked kernel
operations are not an ARM64 kernel build or a device test.  They cannot prove
page-table, scheduler, security-policy, fork/exec race or boot correctness.
Before deployment, perform the requested LLVM kernel build and run tests on
that kernel, covering native/compat clone and clone3, pidfds, TLS, stacks,
signal inheritance, PID-allocation failures and relevant security policy.
Checkpoint/namespace/capability tests need an isolated, suitably privileged
environment; do not run them in a production Android domain blindly.
