#!/usr/bin/env bash
# Provision KernelSU without tracking its source in this kernel tree.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
JSON="$ROOT/scripts/kernelsu/UPSTREAM.json"
PATCH_DIR="$ROOT/scripts/kernelsu/patches"
KSU_DIR=${KSU_DIR:-"$ROOT/KernelSU"}
LINK="$ROOT/drivers/kernelsu"
KSU_REF=${KSU_REF:-latest}

usage() {
	cat <<'USAGE'
Usage: scripts/kernelsu/setup.sh [--cleanup]

Fetches KernelSU and applies scripts/kernelsu/patches/*.patch.
By default KSU_REF=latest resolves the latest non-prerelease GitHub
release.  Set KSU_REF=pinned for the verified UPSTREAM.json commit, or
KSU_REF=<tag|branch|sha> for a specific ref.  Set KSU_DIR to use another
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

# Drop an old link before touching the checkout, so a failed update cannot
# leave a build pointing at an unpatched tree.
if [[ -L "$LINK" ]]; then
	rm -f "$LINK"
elif [[ -e "$LINK" ]]; then
	echo "$LINK exists and is not a symlink; remove it first" >&2
	exit 1
fi

PIN_COMMIT=$(sed -n 's/^[[:space:]]*"commit": "\([0-9a-f]\{40\}\)".*/\1/p' "$JSON" | head -n1)
PIN_TAG=$(sed -n 's/^[[:space:]]*"tag": "\([^"]*\)".*/\1/p' "$JSON" | head -n1)
[[ ${#PIN_COMMIT} -eq 40 ]] || { echo "no 40-hex commit in $JSON" >&2; exit 1; }

latest_release() {
	local tag
	tag=$(curl -fsSL --max-time 20 \
		-H 'Accept: application/vnd.github+json' \
		-H 'User-Agent: kernel-electro' \
		https://api.github.com/repos/Baka-SU/BakaSU/releases/latest 2>/dev/null |
		sed -n 's/.*"tag_name":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1) || true
	if [[ -z "$tag" ]]; then
		tag=$(curl -fsSL --max-time 20 \
			-H 'Accept: application/vnd.github+json' \
			-H 'User-Agent: kernel-electro' \
			'https://api.github.com/repos/Baka-SU/BakaSU/releases?per_page=1' 2>/dev/null |
			sed -n 's/.*"tag_name":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1) || true
	fi
	printf '%s\n' "$tag"
}

case "$KSU_REF" in
latest)
	REF=$(latest_release)
	if [[ -z "$REF" ]]; then
		echo "warning: could not resolve the latest release; using pinned ${PIN_TAG:-$PIN_COMMIT}" >&2
		REF=$PIN_COMMIT
	fi
	;;
pinned)
	REF=$PIN_COMMIT
	;;
*)
	REF=$KSU_REF
	;;
esac

if [[ -e "$KSU_DIR" && ! -d "$KSU_DIR/.git" ]]; then
	echo "$KSU_DIR exists but is not a git checkout; remove it or set KSU_DIR" >&2
	exit 1
fi

if [[ ! -d "$KSU_DIR/.git" ]]; then
	git clone --quiet https://github.com/Baka-SU/BakaSU.git "$KSU_DIR"
fi

if ! git -C "$KSU_DIR" fetch --quiet --depth=1 origin "$REF"; then
	echo "failed to fetch KernelSU ref $REF" >&2
	exit 1
fi
git -C "$KSU_DIR" checkout --quiet --force FETCH_HEAD
git -C "$KSU_DIR" clean --quiet -fdx
COMMIT=$(git -C "$KSU_DIR" rev-parse --short HEAD)

shopt -s nullglob
patches=("$PATCH_DIR"/*.patch)
for patch in "${patches[@]}"; do
	echo "Applying $(basename "$patch") to $REF"
	if ! git -C "$KSU_DIR" apply --whitespace=nowarn "$patch"; then
		echo "error: $(basename "$patch") does not apply to KernelSU $REF." >&2
		echo "Rebase scripts/kernelsu/patches, or use KSU_REF=pinned for the verified pin." >&2
		exit 1
	fi
done

[[ -f "$KSU_DIR/kernel/Makefile" ]] || { echo "KernelSU/kernel/Makefile missing" >&2; exit 1; }

ln -s "$KSU_DIR/kernel" "$LINK"

echo "KernelSU $REF ($COMMIT) ready at $KSU_DIR"
echo "Linked drivers/kernelsu -> $KSU_DIR/kernel"
