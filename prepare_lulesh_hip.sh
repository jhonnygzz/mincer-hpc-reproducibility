#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE="$ROOT/mincer-package/examples/LULESH/hip"
BUILD="$EXAMPLE/build"
for tool in git patch; do
    command -v "$tool" >/dev/null || {
        echo "ERROR: $tool missing. Ask the administrator to install git and patch." >&2
        exit 1
    }
done
mkdir -p "$BUILD"
fetch_source() {
    local url="$1" directory="$2" revision="$3"
    if [[ ! -e "$directory" ]]; then
        git init "$directory"
        git -C "$directory" remote add origin "$url"
        git -C "$directory" fetch --depth 1 origin "$revision"
        git -C "$directory" checkout --detach FETCH_HEAD
    fi
    [[ "$(git -C "$directory" rev-parse HEAD)" == "$revision" ]] || {
        echo "ERROR: Unexpected revision in $directory." >&2
        exit 1
    }
    [[ -z "$(git -C "$directory" status --porcelain)" ]] || {
        echo "ERROR: Modified dependency in $directory; refusing to overwrite it." >&2
        exit 1
    }
}
fetch_source https://github.com/kokkos/kokkos-miniapps.git "$BUILD/miniapps" \
    870fea7443a915336d9a545b0267dd6eb5bed396
fetch_source https://github.com/kokkos/kokkos.git "$BUILD/kokkos" \
    1b1383c6001f3bfe9fe309ca923c2d786600cc79
[[ -f "$BUILD/kokkos/tpls/desul/include/desul/atomics/Atomic_Ref.hpp" ]] || {
    echo "ERROR: Incomplete Kokkos dependency: missing desul Atomic_Ref.hpp." >&2
    exit 1
}
mkdir -p "$BUILD/work/includes"
cp "$BUILD/miniapps/lulesh-2.0/kokkos-no-uvm/"*.cc \
    "$BUILD/miniapps/lulesh-2.0/kokkos-no-uvm/"*.h "$BUILD/work/"
cp "$BUILD/miniapps/lulesh-2.0/kokkos-no-uvm/includes/Timer.hxx" \
    "$BUILD/miniapps/lulesh-2.0/kokkos-no-uvm/includes/cycle.h" "$BUILD/work/includes/"
cp "$EXAMPLE/Makefile" "$EXAMPLE/papi_metrics.h" "$BUILD/work/"
cp "$ROOT/mincer-package/examples/LULESH/cpu/validate_result.h" "$BUILD/work/"
(cd "$BUILD/work" && patch --batch --fuzz=0 -p1 < "$EXAMPLE/monitoring.patch")
echo "LULESH HIP sources prepared at $EXAMPLE"
