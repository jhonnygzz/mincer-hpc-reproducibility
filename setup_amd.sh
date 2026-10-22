#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_AMD_IMAGE:-mincer-rocm-sdk:latest}"
VENV="${MINCER_VENV:-$HOME/.venvs/mincer}"
BUILD_DIR="$ROOT/build"
HIP_DIR="$ROOT/mincer-package/examples/XSBench/hip"
AMD_DEVICE="${MINCER_AMD_DEVICE:-0}"
DOCKER=(docker)

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ "$#" == 0 ]] || fail "Usage: bash setup_amd.sh"
[[ "$AMD_DEVICE" =~ ^[0-9]+$ ]] ||
    fail "MINCER_AMD_DEVICE must be a nonnegative GPU index."
command -v docker >/dev/null ||
    fail "Docker is missing. Ask the node administrator to configure it."
command -v python3 >/dev/null ||
    fail "Python 3 is missing. Ask the node administrator to provide Python 3 and venv support."
[[ -c /dev/kfd && -r /dev/kfd && -w /dev/kfd ]] ||
    fail "This account needs read/write access to /dev/kfd. Ask the node administrator; setup does not change host permissions."

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
        fail "This account needs read/write access to $device. Ask the node administrator."
    DEVICE_OPTIONS+=(--device="$device:$device:rw")
done

if [[ ! -x "$VENV/bin/python" ]]; then
    python3 -m venv "$VENV" ||
        fail "Could not create $VENV. Ask the administrator to provide Python venv support."
fi
if ! "$VENV/bin/python" -c 'import psutil' >/dev/null 2>&1; then
    "$VENV/bin/python" -m pip install psutil
fi

mkdir -p "$BUILD_DIR"
BUILD_LOG="$BUILD_DIR/amd-image-build_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
echo "Building $IMAGE (details saved to $BUILD_LOG)"
if ! "${DOCKER[@]}" build -f "$ROOT/Dockerfile.amdrocpsdk" \
    -t "$IMAGE" "$ROOT" >"$BUILD_LOG" 2>&1; then
    echo "ERROR: AMD image build failed. Full diagnostics: $BUILD_LOG" >&2
    tail -n 40 "$BUILD_LOG" >&2
    exit 1
fi

GPU_LOG="$BUILD_DIR/amd-gpu-check_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
if ! "${DOCKER[@]}" run --rm "${DEVICE_OPTIONS[@]}" "${GPU_VISIBILITY_OPTIONS[@]}" \
    --cap-drop=ALL --user 0:0 --read-only --tmpfs /tmp:rw,exec,nosuid,size=64m \
    "$IMAGE" rocminfo \
    >"$GPU_LOG" 2>&1; then
    echo "ERROR: ROCm GPU discovery failed. Full diagnostics: $GPU_LOG" >&2
    tail -n 30 "$GPU_LOG" >&2
    exit 1
fi
GPU_ARCHES="$(grep -E 'Name:[[:space:]]+gfx[[:xdigit:]]+([[:space:]]|$)' \
    "$GPU_LOG" | awk '{print $2}' | sort -u || true)"
[[ -n "$GPU_ARCHES" ]] ||
    fail "rocminfo found no AMD GPU architecture. Diagnostics: $GPU_LOG"
echo "ROCm GPU architecture(s): $(tr '\n' ' ' <<<"$GPU_ARCHES")"

COMPONENT_LOG="$BUILD_DIR/amd-papi-components_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
if ! "${DOCKER[@]}" run --rm "${DEVICE_OPTIONS[@]}" "${GPU_VISIBILITY_OPTIONS[@]}" \
    --cap-drop=ALL --user 0:0 --read-only --tmpfs /tmp:rw,exec,nosuid,size=64m \
    "$IMAGE" papi_component_avail >"$COMPONENT_LOG" 2>&1; then
    echo "ERROR: PAPI component inspection failed. Full diagnostics: $COMPONENT_LOG" >&2
    tail -n 30 "$COMPONENT_LOG" >&2
    exit 1
fi
grep -F 'rocp_sdk' "$COMPONENT_LOG" ||
    fail "PAPI rocp_sdk is not listed. Diagnostics: $COMPONENT_LOG"

EVENT_LOG="$BUILD_DIR/amd-papi-events_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
if ! "${DOCKER[@]}" run --rm "${DEVICE_OPTIONS[@]}" "${GPU_VISIBILITY_OPTIONS[@]}" \
    --cap-drop=ALL --user 0:0 --read-only --tmpfs /tmp:rw,exec,nosuid,size=64m \
    -v "$HIP_DIR:/workspace:ro" -w /workspace "$IMAGE" bash -euc '
        g++ -std=c++14 -I/usr/local/include \
            check_rocp_sdk_events.cpp rocp_sdk_events.cpp \
            -L/usr/local/lib -Wl,-rpath,/usr/local/lib -lpapi \
            -o /tmp/check_rocp_sdk_events
        /tmp/check_rocp_sdk_events
    ' >"$EVENT_LOG" 2>&1; then
    echo "ERROR: Required rocp_sdk events are unavailable or cannot be added together. Full diagnostics: $EVENT_LOG" >&2
    tail -n 40 "$EVENT_LOG" >&2
    exit 1
fi
grep -E '^PAPI rocp_sdk|^  rocp_sdk|^All required' "$EVENT_LOG"

echo "AMD image and selected-GPU checks are ready. The launcher rechecks events before collection."
if [[ "${MINCER_USE_SUDO_DOCKER:-0}" == 1 ]]; then
    echo "Run: MINCER_AMD_DEVICE=$AMD_DEVICE MINCER_USE_SUDO_DOCKER=1 \"$VENV/bin/python\" \"$ROOT/mincer-package/run_experiment.py\" --path \"$ROOT/mincer-package/examples/XSBench/hip\""
else
    echo "Run: MINCER_AMD_DEVICE=$AMD_DEVICE \"$VENV/bin/python\" \"$ROOT/mincer-package/run_experiment.py\" --path \"$ROOT/mincer-package/examples/XSBench/hip\""
fi
