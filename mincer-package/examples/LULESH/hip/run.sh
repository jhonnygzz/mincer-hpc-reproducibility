#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_AMD_LEGACY_IMAGE:-mincer-rocm-legacy:latest}"
AMD_DEVICE="${MINCER_AMD_DEVICE:-0}"
THREADS="${MINCER_LULESH_THREADS:-1}"
DOCKER=(docker)
fail() { echo "ERROR: $*" >&2; exit 1; }

[[ "$#" == 0 ]] || fail "Usage: bash run.sh"
[[ "$AMD_DEVICE" =~ ^[0-9]+$ ]] || fail "MINCER_AMD_DEVICE must be a nonnegative index."
[[ "$THREADS" =~ ^[1-9][0-9]*$ ]] || fail "MINCER_LULESH_THREADS must be a positive integer."
[[ -f "$SCRIPT_DIR/build/work/lulesh.cc" ]] ||
    fail "Sources missing. Run bash setup_amd.sh --lulesh from the repository root."
command -v docker >/dev/null || fail "Docker missing; ask the node administrator."
case "${MINCER_USE_SUDO_DOCKER:-0}" in
    0) ;;
    1) DOCKER=(sudo -n docker) ;;
    *) fail "MINCER_USE_SUDO_DOCKER must be 0 or 1." ;;
esac
"${DOCKER[@]}" info >/dev/null 2>&1 || fail "Docker access unavailable."
"${DOCKER[@]}" image inspect "$IMAGE" >/dev/null 2>&1 ||
    fail "Image $IMAGE missing. Run bash setup_amd.sh --lulesh."
[[ -c /dev/kfd && -r /dev/kfd && -w /dev/kfd ]] ||
    fail "Read/write /dev/kfd access required; ask the administrator."
shopt -s nullglob
nodes=(/dev/dri/renderD*)
(( ${#nodes[@]} > 0 )) || fail "No GPU render nodes found."
DEVICES=(--device=/dev/kfd:/dev/kfd:rw)
for device in "${nodes[@]}"; do
    [[ -r "$device" && -w "$device" ]] || fail "Read/write access required for $device."
    DEVICES+=(--device="$device:$device:rw")
done

BUILD_LOG="$SCRIPT_DIR/build/build_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
echo "Building LULESH HIP for gfx908 (compiler output saved to $BUILD_LOG)"
if ! "${DOCKER[@]}" run --rm --user "$(id -u):$(id -g)" \
    -v "$SCRIPT_DIR:/workspace" -w /workspace/build/work "$IMAGE" \
    bash -euc 'export KOKKOS_USE_DEPRECATED_MAKEFILES=1; make clean; make -j4' \
    >"$BUILD_LOG" 2>&1; then
    echo "ERROR: LULESH HIP build failed. Full diagnostics: $BUILD_LOG" >&2
    tail -n 30 "$BUILD_LOG" >&2
    exit 1
fi
echo "Running LULESH HIP on AMD GPU index $AMD_DEVICE."
"${DOCKER[@]}" run --rm "${DEVICES[@]}" --cap-drop=ALL --user 0:0 \
    --read-only --tmpfs /tmp \
    -e "ROCR_VISIBLE_DEVICES=$AMD_DEVICE" -e HIP_VISIBLE_DEVICES=0 \
    -e "OMP_NUM_THREADS=$THREADS" -e OMP_PROC_BIND=false \
    -v "$SCRIPT_DIR/build/work:/work:ro" -w /work "$IMAGE" \
    ./lulesh.kk -s 96 -i 10
