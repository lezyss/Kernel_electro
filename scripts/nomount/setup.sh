#!/usr/bin/env bash
# Fetch the external NoMount source and expose it under fs/nomount.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
JSON="$ROOT/scripts/nomount/UPSTREAM.json"
PATCHES="$ROOT/scripts/nomount/patches"
LINK_DIR="$ROOT/fs/nomount"
NOMOUNT_DIR=${NOMOUNT_DIR:-$ROOT/NoMount}
NOMOUNT_REF=${NOMOUNT_REF:-latest}

usage() {
	cat <<'USAGE'
Usage: scripts/nomount/setup.sh [--cleanup]

Fetch NoMount into NOMOUNT_DIR (default: ./NoMount), apply the local
Makefile adaptation, and link the source files into fs/nomount.

NOMOUNT_REF:
  latest (default)  newest non-prerelease GitHub release; falls back to
                    the pinned commit when the GitHub API is unreachable
  pinned            commit recorded in scripts/nomount/UPSTREAM.json
  <tag|branch|sha>  explicit ref

NOMOUNT_DIR selects an existing separate checkout.
USAGE
}

case "$NOMOUNT_REF" in
pinned) REF=$(sed -n 's/.*"commit": "\([0-9a-f]\{40\}\)".*/\1/p' "$JSON" | head -1) ;;
latest) REF= ;;
*) REF=$NOMOUNT_REF ;;
esac

cleanup() {
	rm -f "$LINK_DIR/Makefile" "$LINK_DIR/nomount.c" "$LINK_DIR/nomount.h" "$LINK_DIR/LICENSE"
	echo "Removed NoMount source links under fs/nomount"
}

case "${1:-}" in
-h | --help) usage; exit 0 ;;
--cleanup) cleanup; exit 0 ;;
"") ;;
*) usage >&2; exit 2 ;;
esac

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
[[ -f "$JSON" ]] || { echo "missing $JSON" >&2; exit 1; }

if [[ -z "${REF:-}" && "$NOMOUNT_REF" == "pinned" ]]; then
	echo "no pinned NoMount commit in $JSON" >&2
	exit 1
fi

latest_release() {
	local json tag
	json=$(curl -fsSL --max-time 20 \
		https://api.github.com/repos/maxsteeel/nomount/releases/latest 2>/dev/null) || return 1
	tag=$(printf '%s' "$json" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
	[[ -n "$tag" ]] || return 1
	printf '%s' "$tag"
}

if [[ "$NOMOUNT_REF" == "latest" ]]; then
	if REF=$(latest_release); then
		echo "Resolved latest NoMount release: $REF"
	else
		REF=$(sed -n 's/.*"commit": "\([0-9a-f]\{40\}\)".*/\1/p' "$JSON" | head -1)
		echo "warning: could not resolve the latest NoMount release; falling back to $REF" >&2
	fi
fi

# Remove old links first so a failed update cannot leave stale source in use.
for f in Makefile nomount.c nomount.h LICENSE; do
	rm -f "$LINK_DIR/$f"
done

if [[ ! -d "$NOMOUNT_DIR/.git" ]]; then
	rm -rf "$NOMOUNT_DIR"
	mkdir -p "$NOMOUNT_DIR"
	git -C "$NOMOUNT_DIR" init -q
	git -C "$NOMOUNT_DIR" remote add origin https://github.com/maxsteeel/nomount.git
fi

git -C "$NOMOUNT_DIR" fetch --quiet --depth=1 origin "$REF"
git -C "$NOMOUNT_DIR" checkout --quiet --force FETCH_HEAD
git -C "$NOMOUNT_DIR" clean -qfdx

for f in "$PATCHES"/*.patch; do
	[[ -e "$f" ]] || continue
	if ! git -C "$NOMOUNT_DIR" apply --check -p1 "$f" 2>/dev/null; then
		echo "$(basename "$f") does not apply to NoMount $REF." >&2
		echo "Use NOMOUNT_REF=pinned for the verified pin, or refresh scripts/nomount/patches." >&2
		exit 1
	fi
	git -C "$NOMOUNT_DIR" apply -p1 "$f"
done

for f in Makefile nomount.c nomount.h; do
	[[ -f "$NOMOUNT_DIR/kernel/src/$f" ]] || {
		echo "NoMount checkout is missing kernel/src/$f" >&2
		exit 1
	}
	ln -s "$NOMOUNT_DIR/kernel/src/$f" "$LINK_DIR/$f"
done
[[ -f "$NOMOUNT_DIR/kernel/LICENSE" ]] && ln -s "$NOMOUNT_DIR/kernel/LICENSE" "$LINK_DIR/LICENSE"

echo "Linked NoMount $REF into fs/nomount (Kconfig is tracked locally)"
