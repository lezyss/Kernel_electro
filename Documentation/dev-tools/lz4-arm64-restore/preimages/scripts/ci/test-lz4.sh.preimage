#!/usr/bin/env bash
# Pinned block-codec tests; no kernel/flashability claim follows from these.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"
TOOLCHAIN_DIR=${TOOLCHAIN_DIR:-"$ROOT/.toolchains/r614150"}
TOOLCHAIN_DIR=$(cd "$TOOLCHAIN_DIR" && pwd)
expected=3b86e40facfff1eab4065614255d573293c10373
if [[ ! -f "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt" ]] ||
   [[ "$(cat "$TOOLCHAIN_DIR/aosp-prebuilts-commit.txt")" != "$expected" ]]; then
    echo "Expected pinned AOSP r614150 toolchain ($expected)" >&2
    exit 1
fi
mkdir -p out/lz4-tests
work=$(mktemp -d "$ROOT/out/lz4-tests/upstream.XXXXXX")
trap 'rm -rf "$work"' EXIT
pin=aa4647fad575d01a874aaaadcdbe8e6a40e072f5
curl --fail --location --retry 3 "https://codeload.github.com/lz4/lz4/tar.gz/$pin" -o "$work/upstream.tar.gz"
mkdir "$work/source"
tar -xzf "$work/upstream.tar.gz" --strip-components=1 -C "$work/source"
# test_codec.py verifies every consumed upstream input against v1.11.1 hashes.
python3 -m venv "$work/venv"
"$work/venv/bin/pip" install --disable-pip-version-check -r tools/testing/selftests/lz4/requirements.txt
"$work/venv/bin/python" tools/testing/selftests/lz4/test_build.py \
    --cc "$TOOLCHAIN_DIR/bin/clang" --output out/lz4-tests/objects 2>&1 | tee out/lz4-tests/build.log
"$work/venv/bin/python" tools/testing/selftests/lz4/test_codec.py \
    --cc "$TOOLCHAIN_DIR/bin/clang" --upstream "$work/source" \
    --asan --ubsan --output out/lz4-tests/codec 2>&1 | tee out/lz4-tests/codec.log
"$work/venv/bin/python" tools/testing/selftests/lz4/test_ci.py 2>&1 | tee out/lz4-tests/scripts.log
