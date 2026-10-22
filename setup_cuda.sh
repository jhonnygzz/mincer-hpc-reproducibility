#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${MINCER_CUDA_IMAGE:-mincer-papi-cuda:latest}"
VENV="${MINCER_VENV:-$HOME/.venvs/mincer}"

fail() { echo "ERROR: $*" >&2; exit 1; }

if [[ "${1:-}" == "--install-system" && "$#" == 1 ]]; then
    . /etc/os-release
    [[ "$ID" == ubuntu && ( "$VERSION_ID" == 22.04 || "$VERSION_ID" == 24.04 ) ]] ||
        fail "Automatic system installation supports Ubuntu 22.04/24.04 only."
    command -v nvidia-smi >/dev/null || fail "Ask your administrator to install the NVIDIA driver first."
    nvidia-smi >/dev/null
    sudo apt-get update
    sudo apt-get install -y docker.io python3-venv curl gnupg git patch
    if ! command -v nvidia-ctk >/dev/null; then
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey |
            sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
        curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
        sudo apt-get update
        sudo apt-get install -y nvidia-container-toolkit
    fi
    sudo systemctl start docker
    [[ -z "$(sudo docker ps -q)" ]] ||
        fail "Docker has running containers; ask the administrator to configure NVIDIA runtime without disrupting them."
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
elif [[ "$#" != 0 ]]; then
    fail "Usage: bash setup_cuda.sh [--install-system]. The option installs packages and restarts Docker."
fi

command -v nvidia-smi >/dev/null || fail "NVIDIA driver/nvidia-smi missing; contact your administrator."
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
command -v docker >/dev/null ||
    fail "Docker missing. With administrator approval, run: bash setup_cuda.sh --install-system"
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
    "${DOCKER[@]}" info >/dev/null ||
        fail "Docker unavailable; ask your administrator to start/configure it."
fi
command -v nvidia-ctk >/dev/null ||
    fail "NVIDIA Container Toolkit missing. Use --install-system with administrator approval."
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install psutil
"${DOCKER[@]}" build -f "$ROOT/Dockerfile.papicuda" -t "$IMAGE" "$ROOT"
"${DOCKER[@]}" run --rm --gpus all "$IMAGE" \
    bash -euc 'nvidia-smi; papi_component_avail; papi_avail'
echo "Image and GPU checks completed. Counter collection still requires the benchmark test."
bash "$ROOT/prepare_lulesh_cuda.sh"
echo "Run: \"$VENV/bin/python\" \"$ROOT/mincer-package/run_experiment.py\" --path \"$ROOT/mincer-package/examples/XSBench/cuda\""
echo "LULESH: \"$VENV/bin/python\" \"$ROOT/mincer-package/run_experiment.py\" --path \"$ROOT/mincer-package/examples/LULESH/cuda\""
