# Approved Azyr selection checks

Run from the kernel root:

```sh
python3 tools/testing/selftests/azyr_selected/test_selected.py
```

Requires Python3, Git, GCC and UBSan. Does not download a compiler, build a kernel,
modify source or execute hardware. Generates only temporary source/binaries and
reconstructs preimages from `Documentation/dev-tools/azyr-sm6250-selected.diff`.

Compiles extracted current functions, not alternate production implementations:

- #46:36 newly-idle/runnable/pending-wakeup/hotplug/other-idle cases.
- #48:240,000 old/new scheduler delta/inverse comparisons with two modeled load
  scales, cached/uncached inverse weights and deterministic edge/random values.
- #78:450 policy get/put cases over topology match branches and NULL returns.
- #94:18 occupied-slot counts, checking references, cleared slots and stat transfer.
- #92:36 producer/CFQ/BFQ clock-offset, equal-time and boundary combinations.
- #98:2 enabled+pending GIC IRQ recording cases with console debug on/off.
- Seven compiled negative controls must fail at runtime. Structural assertions
  additionally check the selected verity flags, inline marker, suspend debug
  flag, removed GPU IRQ debug wrapper, IOMMU log and PM recorder.

Mocks adapt kernel primitives, clock samples, registers, masks, allocation and
statistics. They do not prove memory ordering, races, full sysfs/driver behavior,
clock synchronization or pointer lifetime on real hardware. Scheduler arithmetic
uses a widened multiplication adapter; modeled scales are not a32-bit binary or
production AArch64 instruction test. The GIC fixture models one IRQ, not a real
interrupt controller. The #94 model does not promise complete callback idempotence.

These are host correctness/regression checks, not a production AOSP r614150
fullClang/noGCC build, boot, dm-verity runtime activation, GPU stress, suspend,
power or performance validation. See `Documentation/dev-tools/azyr-sm6250-selected.md`
and its validation JSON for exact scope, provenance and remaining device tests.
