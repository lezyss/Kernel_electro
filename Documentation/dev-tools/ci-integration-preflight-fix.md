# CI integration preflight after KSU+50 / NoMount23

## Report and evidence boundary

Reported run: https://github.com/lezyss/Kernel_electro/actions/runs/43623426173

GitHub metadata identifies commit `71788e7277f41df95cd57d2abb5d31f4e84abe61`,
branch `arena/e63a046d-kernel-electro`, and failure in **Build with Clang and
LLVM tools** after toolchain verification succeeded. Run logs and build-detail
artifacts could not be downloaded here: GitHub redirects them to external
Actions/Azure storage hosts inaccessible from this sandbox. Therefore the exact
remote traceback and any subsequent compiler errors are not confirmed.

The checked-in build script's preflight commands reproduce three independent
blockers locally, before target compilation:

1. `python3 tools/testing/selftests/kernelsu/test_integration.py --config out/.config`
   fails with `No such file or directory: /tmp/ksu50-base-.../tree/out/.config`.
   The historical source replays deliberately exclude build output, but the
   legacy checker resolves the relative config against its replay root.
2. Giving that historical checker an absolute generated config then fails
   `missing CONFIG_KSU_FEATURE_SULOG=y`. The current KSU+50 source intentionally
   removed that selector; its absence in the actual output config is correct.
   Adding an obsolete selector to appease the checker would be wrong.
3. Directly running `susfs/test_backport_240.py` against current KSU+50 fails
   `SUSFS 2.4 successor: source changed: drivers/kernelsu/feature/selinux_hide.c`.
   Those models require the exact pre-KSU+50 SUSFS2.4 postimage, not updated KSU.

## Scoped fix

`scripts/ci/build-kernel.sh` now invokes `scripts/ci/check-integrations.py` and
logs all preflight output to `out/integrations.log` (already covered by the
workflow's existing `out/*.log` artifact pattern). `set -euo pipefail` is retained.

The new dispatcher:

- Resolves the actual output config to an existing absolute path before any
  subprocess/replay. It never fabricates or rewrites config selectors.
- Uses `kernelsu/test_update50.py --config ... --self-test-negatives --historical`
  for current KSU policy/source checks and explicit historical regression tests.
- Retains NoMount resolved-config integrity checks and adds current API23
  behavioral/negative models. Its legacy config CLI gets an absolute path.
- Retains SUSFS config/overlay checks with absolute config paths and runs
  SUSFS2.4 exact-source models only inside `update50.reviewed_base()`, which
  verifies and composes NoMount23 / KSU+50 inverse and forward provenance replay.
- Preserves conditional checks for integrations requested by the source defconfig.

No production kernel source, defconfig, compiler pin, workflow triggers, old
receipt, old test or provenance seal was changed. Compiler arguments remain
full AOSP Clang/LLVM for production. Host GCC is used by the existing extracted
models only, not as a replacement production compiler. No check was disabled.

## Local validation

Generate the output config using available host tools (NOT target build proof):

```sh
make O=out ARCH=arm64 HOSTCC=gcc CC=gcc vendor/xiaomi/miatoll_defconfig
scripts/config --file out/.config --disable LLVM_POLLY
make O=out ARCH=arm64 HOSTCC=gcc CC=gcc olddefconfig
python3 scripts/ci/check-integrations.py --config out/.config \
  --defconfig arch/arm64/configs/vendor/xiaomi/miatoll_defconfig --cc gcc
python3 tools/testing/selftests/ci/test_integrations.py
bash -n scripts/ci/build-kernel.sh
```

Results: the real preflight exits zero, including current KSU/FinaSU/SUSFS models,
current NoMount23 models and historical replay/negative suites. The dispatcher
has nine passing tests for current-vs-historical selection, relative-to-absolute
config handling, no config rewriting, correct SUSFS replay/compiler forwarding,
disabled integrations, missing config, failure propagation and shell wiring.
Additional actual CLI checks reject both `CONFIG_KSU_FEATURE_SULOG=y` and removal
of `CONFIG_KSU_ENABLE_FULL_UID_CHECKS=y` from otherwise generated configs.

See `ci-integration-preflight-fix-results.log` for the successful preflight and
regression output. No production AOSP target compiler is installed here. No
full target compile/link, boot, device test, push or CI rerun is claimed by these
local results. A fresh production build remains necessary to discover any
compiler/linker issues beyond the corrected preflight.
