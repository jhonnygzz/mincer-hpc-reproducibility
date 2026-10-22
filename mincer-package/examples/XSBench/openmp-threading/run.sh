#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_CPU_IMAGE:-mincer-papi-cpu:latest}"
BUILD_DIR="$SCRIPT_DIR/build"
THREADS="${MINCER_XSBENCH_THREADS:-$(nproc)}"
DOCKER=(docker)

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ "$THREADS" =~ ^[1-9][0-9]*$ ]] ||
    fail "MINCER_XSBENCH_THREADS must be a positive integer."
command -v docker >/dev/null ||
    fail "Docker is missing. Ask the node administrator to configure Docker."
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
    fail "Docker is not accessible through the selected path. Ask the administrator to configure direct access or approved non-interactive sudo Docker access."
"${DOCKER[@]}" image inspect "$IMAGE" >/dev/null 2>&1 ||
    fail "Image $IMAGE is missing. Run bash setup_cpu.sh from the repository root."

PROFILE_OPTIONS=(--cap-drop=ALL --user "$(id -u):$(id -g)")
case "${MINCER_ALLOW_CPU_PROFILING:-0}" in
    0) ;;
    1)
        echo "WARNING: CPU profiling capability enabled; host counter policy must also permit access."
        PROFILE_OPTIONS=(--cap-drop=ALL --cap-add=PERFMON --user 0:0)
        ;;
    *) fail "MINCER_ALLOW_CPU_PROFILING must be 0 or 1." ;;
esac

mkdir -p "$BUILD_DIR"
BUILD_LOG="$BUILD_DIR/build_$(date -u +%Y-%m-%dT%H-%M-%S-%N).log"
echo "Building XSBench OpenMP (compiler output saved to $BUILD_LOG)"
if ! "${DOCKER[@]}" run --rm --user "$(id -u):$(id -g)" \
    -v "$SCRIPT_DIR:/work" -w /work "$IMAGE" \
    bash -euc 'make clean && make' >"$BUILD_LOG" 2>&1; then
    echo "ERROR: XSBench build failed. Full diagnostics: $BUILD_LOG" >&2
    tail -n 30 "$BUILD_LOG" >&2
    exit 1
fi

"${DOCKER[@]}" run --rm "${PROFILE_OPTIONS[@]}" --read-only --tmpfs /tmp \
    --mount type=bind,src=/sys,dst=/sys,readonly \
    -v "$SCRIPT_DIR:/work:ro" -w /work "$IMAGE" \
    ./XSBench -m history -s large -p 500000 -l 34 -G unionized -t "$THREADS"
