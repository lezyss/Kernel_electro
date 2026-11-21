#!/usr/bin/env bash
# Provision the pinned backslashxx KernelSU source without tracking it here.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
JSON="$ROOT/scripts/kernelsu/UPSTREAM.json"
PATCH_DIR="$ROOT/scripts/kernelsu/patches"
KSU_DIR=${KSU_DIR:-"$ROOT/KernelSU"}
LINK="$ROOT/drivers/kernelsu"

usage() {
	cat <<'USAGE'
Usage: scripts/kernelsu/setup.sh [--cleanup]

Fetches the KernelSU revision pinned in scripts/kernelsu/UPSTREAM.json,
applies scripts/kernelsu/patches/*.patch, and links
KernelSU/kernel to drivers/kernelsu.  Set KSU_DIR to use another
checkout location.  --cleanup removes only the drivers/kernelsu link.
USAGE
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
	usage
	exit 0
fi

if [[ ${1:-} == --cleanup ]]; then
	[[ -L "$LINK" ]] && rm -f "$LINK"
	echo "Removed $LINK"
	exit 0
fi
if [[ $# -ne 0 ]]; then
	usage >&2
	exit 2
fi

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
[[ -f "$JSON" ]] || { echo "missing $JSON" >&2; exit 1; }

PIN=$(sed -n 's/^[[:space:]]*"commit": "\([0-9a-f]\{40\}\)".*/\1/p' "$JSON" | head -n1)
[[ ${#PIN} -eq 40 ]] || { echo "no 40-hex commit in $JSON" >&2; exit 1; }

if [[ -e "$KSU_DIR" && ! -d "$KSU_DIR/.git" ]]; then
	echo "$KSU_DIR exists but is not a git checkout; remove it or set KSU_DIR" >&2
	exit 1
fi

if [[ ! -d "$KSU_DIR/.git" ]]; then
	git clone --quiet https://github.com/backslashxx/KernelSU.git "$KSU_DIR"
fi

git -C "$KSU_DIR" fetch --quiet --depth=1 origin "$PIN"
git -C "$KSU_DIR" checkout --quiet --force "$PIN"
git -C "$KSU_DIR" clean --quiet -fdx

shopt -s nullglob
patches=("$PATCH_DIR"/*.patch)
if [[ ${#patches[@]} -eq 0 ]]; then
	echo "no local patches found in $PATCH_DIR" >&2
	exit 1
fi
for patch in "${patches[@]}"; do
	echo "Applying $(basename "$patch")"
	git -C "$KSU_DIR" apply --whitespace=nowarn "$patch"
done

[[ -f "$KSU_DIR/kernel/Makefile" ]] || { echo "KernelSU/kernel/Makefile missing" >&2; exit 1; }

rm -rf "$LINK"
ln -s "$KSU_DIR/kernel" "$LINK"

echo "KernelSU $PIN ready at $KSU_DIR"
echo "Linked drivers/kernelsu -> $KSU_DIR/kernel"
