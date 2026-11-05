# Suspend-state validation backport

This covers only AzyrRuthless/kernel_xiaomi_sm6250 commit
`a71e6b492f9683cf7c2df84cad52fe6d2e57023e`, “PM: suspend: Use valid_state()
consistently”, authored by Rafael J. Wysocki. The production change follows
that commit: require an `enter` callback in `valid_state()` and use that
predicate for non-s2idle states in `sleep_state_supported()`.

No wakelock wrapper/GC change, mem_sleep restriction, noirq/cpuidle sequencing
change, or extra idle-CPU wakeup is included. The existing 10-second freezing
timeout is preserved.

Run on a Linux host with Python 3 and GCC/Clang plus its UBSan runtime:

```sh
python3 tools/testing/selftests/suspend_validation/test_backport.py \
    --cc cc --self-test-negatives
```

The runner extracts both actual predicates from `kernel/power/suspend.c` and
compiles them into a UBSan-enabled host model. It checks 320 combinations of
ops presence, valid/enter callback presence, per-state callback results, and
s2idle/standby/mem states. It verifies callback short-circuiting, that validation
never invokes `enter`, and that s2idle stays supported independently of platform
callbacks. Two optional negative controls restore each legacy predicate and
must fail assertions. All binaries are generated outside the source tree.

This is an extracted-function test with mocked platform operations, not a full
ARM64 kernel build or device suspend/resume test. It does not establish battery,
latency, or hardware suspend correctness. No push or CI is required by this test.
