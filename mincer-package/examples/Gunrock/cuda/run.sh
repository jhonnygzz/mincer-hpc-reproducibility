#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_CUDA_IMAGE:-mincer-papi-cuda:latest}"
[[ -f "$SCRIPT_DIR/build/work/examples/algorithms/bfs/bfs.cu" ]] || {
    echo "ERROR: Sources missing. Run bash setup_cuda.sh from the repository root." >&2
    exit 1
}
command -v docker >/dev/null || {
    echo "ERROR: Docker missing. Run bash setup_cuda.sh first." >&2
    exit 1
}
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
    "${DOCKER[@]}" info >/dev/null
fi
"${DOCKER[@]}" image inspect "$IMAGE" >/dev/null
PROFILE_OPTIONS=(--user "$(id -u):$(id -g)")
case "${MINCER_ALLOW_GPU_PROFILING:-0}" in
    0) ;;
    1)
        echo "WARNING: Explicitly approved GPU profiling with CAP_SYS_ADMIN."
        PROFILE_OPTIONS=(--cap-add SYS_ADMIN)
        ;;
    *) echo "ERROR: MINCER_ALLOW_GPU_PROFILING must be 0 or 1." >&2; exit 1 ;;
esac
echo "=== Gunrock CUDA BFS Performance Test ==="
echo "Date: $(date -Is)"
echo "Image: $("${DOCKER[@]}" image inspect --format '{{.Id}}' "$IMAGE")"
BUILD_LOG="$SCRIPT_DIR/build/build_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
echo "Building Gunrock BFS (compiler output saved to $BUILD_LOG)"
if ! "${DOCKER[@]}" run --rm --user "$(id -u):$(id -g)" \
    --entrypoint bash -e HOME=/tmp \
    -v "$SCRIPT_DIR:/workspace" -w /workspace "$IMAGE" -euc '
        cmake -S build/work -B build/compiled \
            -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=75 \
            -DESSENTIALS_BUILD_TESTS=OFF -DESSENTIALS_BUILD_BENCHMARKS=OFF
        cmake --build build/compiled --target bfs -j4
    ' > "$BUILD_LOG" 2>&1; then
    echo "ERROR: Gunrock build failed. Full diagnostics: $BUILD_LOG" >&2
    tail -n 30 "$BUILD_LOG" >&2
    exit 1
fi
"${DOCKER[@]}" run --rm --gpus all "${PROFILE_OPTIONS[@]}" \
    --entrypoint /workspace/build/compiled/bin/bfs \
    --read-only --tmpfs /tmp \
    -v "$SCRIPT_DIR:/workspace:ro" -w /workspace "$IMAGE" \
    --market /workspace/build/work/datasets/chesapeake/chesapeake.mtx \
    --src 17 --validate
echo "=== Gunrock CUDA BFS Test Complete ==="
