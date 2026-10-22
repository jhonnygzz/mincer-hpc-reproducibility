#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE="$ROOT/mincer-package/examples/Gunrock/cuda"
BUILD="$EXAMPLE/build"
REVISION=530f25443864d04c25286c053d6812a888b4d779

for tool in git patch tar; do
    command -v "$tool" >/dev/null || {
        echo "ERROR: $tool missing. Ask your administrator to install git, patch, and tar." >&2
        exit 1
    }
done
mkdir -p "$BUILD"
if [[ ! -e "$BUILD/upstream" ]]; then
    git init "$BUILD/upstream"
    git -C "$BUILD/upstream" remote add origin https://github.com/gunrock/gunrock.git
    git -C "$BUILD/upstream" fetch --depth 1 origin "$REVISION"
    git -C "$BUILD/upstream" checkout --detach FETCH_HEAD
fi
[[ "$(git -C "$BUILD/upstream" rev-parse HEAD)" == "$REVISION" ]] || {
    echo "ERROR: Unexpected Gunrock revision in $BUILD/upstream." >&2
    exit 1
}
[[ -z "$(git -C "$BUILD/upstream" status --porcelain)" ]] || {
    echo "ERROR: Modified Gunrock dependency; refusing to overwrite it." >&2
    exit 1
}
mkdir -p "$BUILD/work"
# Refresh only generated work files; keep the upstream checkout untouched.
git -C "$BUILD/upstream" archive HEAD | tar -xf - -C "$BUILD/work"
(cd "$BUILD/work" && patch --batch --fuzz=0 -p1 < "$EXAMPLE/monitoring.patch")
if [[ ! -f "$BUILD/work/datasets/chesapeake/chesapeake.mtx" ]]; then
    echo "ERROR: The pinned Gunrock source is missing the Chesapeake graph." >&2
    exit 1
fi
echo "Gunrock CUDA sources prepared. Run with MINCER at: $EXAMPLE"
