#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_CPU_IMAGE:-mincer-papi-cpu:latest}"
VENV="${MINCER_VENV:-$HOME/.venvs/mincer}"
DOCKER=(docker)

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

[[ "$#" == 0 ]] || fail "Usage: bash setup_cpu.sh"
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
command -v python3 >/dev/null ||
    fail "Python 3 is missing. Ask the node administrator to provide Python 3 and venv support."

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install psutil
"${DOCKER[@]}" build -f "$ROOT/Dockerfile.cpu" -t "$IMAGE" "$ROOT"
"${DOCKER[@]}" run --rm "$IMAGE" papi_component_avail

echo "CPU PAPI image and MINCER Python environment are ready."
echo "Component listing does not prove hardware-counter access."
echo "Run a selected CPU example through MINCER after reviewing its permissions requirements:"
echo "\"$VENV/bin/python\" \"$ROOT/mincer-package/run_experiment.py\" --path /path/to/example"
