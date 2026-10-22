#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_AMD_IMAGE:-mincer-rocm-sdk:latest}"
BUILD_DIR="$SCRIPT_DIR/build"
GPU_ARCH="${MINCER_AMD_ARCH:-gfx908}"
AMD_DEVICE="${MINCER_AMD_DEVICE:-0}"
DOCKER=(docker)

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ "$#" == 0 ]] || fail "Usage: bash run.sh"
[[ "$GPU_ARCH" =~ ^gfx[[:xdigit:]]+$ ]] ||
    fail "MINCER_AMD_ARCH must be a GPU target such as gfx908."
[[ "$AMD_DEVICE" =~ ^[0-9]+$ ]] ||
    fail "MINCER_AMD_DEVICE must be a nonnegative GPU index."
command -v docker >/dev/null ||
    fail "Docker is missing. Ask the node administrator to configure it."

case "${MINCER_USE_SUDO_DOCKER:-0}" in
    0) ;;
    1)
        command -v sudo >/dev/null ||
            fail "MINCER_USE_SUDO_DOCKER=1 requires sudo."
        DOCKER=(sudo -n docker)
        ;;
    *) fail "MINCER_USE_SUDO_DOCKER must be 0 or 1." ;;
esac
"${DOCKER[@]}" info >/dev/null 2>&1 ||
    fail "Docker is not accessible through the selected path. Ask the administrator to configure access."
"${DOCKER[@]}" image inspect "$IMAGE" >/dev/null 2>&1 ||
    fail "Image $IMAGE is missing. Run bash setup_amd.sh from the repository root."

[[ -c /dev/kfd && -r /dev/kfd && -w /dev/kfd ]] ||
    fail "This account needs read/write access to /dev/kfd. Ask the administrator; the launcher does not change host permissions."
shopt -s nullglob
render_nodes=(/dev/dri/renderD*)
(( ${#render_nodes[@]} > 0 )) ||
    fail "No GPU render nodes found under /dev/dri."
DEVICE_OPTIONS=(--device=/dev/kfd:/dev/kfd:rw)
GPU_VISIBILITY_OPTIONS=(
    --env "ROCR_VISIBLE_DEVICES=$AMD_DEVICE"
    --env "HIP_VISIBLE_DEVICES=$AMD_DEVICE"
)
for device in "${render_nodes[@]}"; do
    [[ -c "$device" && -r "$device" && -w "$device" ]] ||
        fail "This account needs read/write access to $device."
    DEVICE_OPTIONS+=(--device="$device:$device:rw")
done

mkdir -p "$BUILD_DIR"
BUILD_LOG="$BUILD_DIR/build_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
echo "Building XSBench HIP for $GPU_ARCH (compiler output saved to $BUILD_LOG)"
if ! "${DOCKER[@]}" run --rm --user "$(id -u):$(id -g)" \
    --env "GPU_ARCH=$GPU_ARCH" \
    -v "$SCRIPT_DIR:/workspace" -w /workspace "$IMAGE" \
    bash -euc 'make clean && make GPU_ARCH="$GPU_ARCH"' >"$BUILD_LOG" 2>&1; then
    echo "ERROR: XSBench HIP build failed. Full diagnostics: $BUILD_LOG" >&2
    tail -n 30 "$BUILD_LOG" >&2
    exit 1
fi

echo "Running on AMD GPU index $AMD_DEVICE (HIP/PAPI visibility restricted to that device)."
"${DOCKER[@]}" run --rm "${DEVICE_OPTIONS[@]}" "${GPU_VISIBILITY_OPTIONS[@]}" \
    --cap-drop=ALL --user 0:0 --read-only --tmpfs /tmp \
    -v "$SCRIPT_DIR:/workspace:ro" -w /workspace \
    "$IMAGE" ./XSBench -m event
echo "XSBench HIP completed successfully."
