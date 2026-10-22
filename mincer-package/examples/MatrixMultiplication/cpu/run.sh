#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_CPU_IMAGE:-mincer-papi-cpu:latest}"
BUILD_DIR="$SCRIPT_DIR/build"
DOCKER=(docker)

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

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
echo "Building matrix multiplication (compiler output saved to $BUILD_LOG)"
if ! "${DOCKER[@]}" run --rm --user "$(id -u):$(id -g)" \
    -v "$SCRIPT_DIR:/work" -w /work "$IMAGE" \
    bash -euc 'gcc -O2 -std=c11 -Wall -Wextra -Wpedantic -Werror \
        -I/usr/local/include matrix_multiplication.c matrix_kernels.c \
        -L/usr/local/lib -Wl,-rpath,/usr/local/lib -lpapi \
        -o build/matrix_multiplication' >"$BUILD_LOG" 2>&1; then
    echo "ERROR: Matrix multiplication build failed. Full diagnostics: $BUILD_LOG" >&2
    tail -n 30 "$BUILD_LOG" >&2
    exit 1
fi

"${DOCKER[@]}" run --rm "${PROFILE_OPTIONS[@]}" --read-only --tmpfs /tmp \
    -v "$SCRIPT_DIR:/work:ro" -w /work "$IMAGE" \
    /work/build/matrix_multiplication
