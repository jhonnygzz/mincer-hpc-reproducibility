#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_CUDA_IMAGE:-mincer-papi-cuda:latest}"
command -v docker >/dev/null || {
    echo "ERROR: Docker missing. Run bash setup_cuda.sh from the repository root." >&2
    exit 1
}
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
    "${DOCKER[@]}" info >/dev/null
fi
"${DOCKER[@]}" image inspect "$IMAGE" >/dev/null 2>&1 || {
    echo "ERROR: Image $IMAGE missing. Run bash setup_cuda.sh first." >&2
    exit 1
}
echo "=== XSBench CUDA Performance and Power Test ==="
echo "Date: $(date -Is)"
echo "Image: $("${DOCKER[@]}" image inspect --format '{{.Id}}' "$IMAGE")"
"${DOCKER[@]}" run --rm --gpus all \
    --user "$(id -u):$(id -g)" \
    -v "$SCRIPT_DIR:/workspace" -w /workspace \
    "$IMAGE" bash -euc '
        make clean
        make
    '
PROFILE_OPTIONS=(--user "$(id -u):$(id -g)")
case "${MINCER_ALLOW_GPU_PROFILING:-0}" in
    0) ;;
    1)
        echo "WARNING: Explicitly approved GPU profiling with CAP_SYS_ADMIN."
        PROFILE_OPTIONS=(--cap-add SYS_ADMIN)
        ;;
    *) echo "ERROR: MINCER_ALLOW_GPU_PROFILING must be 0 or 1." >&2; exit 1 ;;
esac
"${DOCKER[@]}" run --rm --gpus all "${PROFILE_OPTIONS[@]}" \
    --read-only --tmpfs /tmp \
    -v "$SCRIPT_DIR:/workspace:ro" -w /workspace \
    "$IMAGE" ./XSBench -m event
echo "=== XSBench CUDA Test Complete ==="
