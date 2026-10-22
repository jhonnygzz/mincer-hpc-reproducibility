# MINCER: Reproducible HPC Performance Experiments

MINCER is a research toolkit for documenting HPC computing environments and capturing experiment output alongside performance measurements from PAPI and GPU monitoring components.

## What this repository contains

- MINCER's environment-manifest and experiment-log utilities in `mincer-package/`.
- Dockerfiles for CPU, NVIDIA CUDA, and AMD ROCm/PAPI environments.
- Human-readable guides for acquiring and running the benchmark workloads.
- A [node quick start](docs/nodes/quickstart.md) with Cascade Lake CPU, MI100, and RTX 6000 hardware profiles. These are validation targets; MINCER users should adapt the steps to their own nodes.

The small PAPI-instrumented XSBench CUDA example is included with its upstream license. LULESH CUDA uses pinned upstream downloads plus a small instrumentation patch. Other benchmark source trees, datasets, model weights, generated binaries, container images, and experiment logs are excluded. Follow [the benchmark guides](docs/benchmarks/README.md) for those workloads.

## Start with XSBench on NVIDIA

On a Linux node with a working NVIDIA driver, Docker, NVIDIA Container Toolkit, and Python venv support:

```bash
bash setup_cuda.sh
"$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/cuda"
```

On Ubuntu 22.04/24.04, `bash setup_cuda.sh --install-system` can install Docker,
NVIDIA Container Toolkit, and Python venv support **with administrator approval**.
It uses sudo, adds NVIDIA's package repository when needed, and restarts Docker;
it refuses that restart when Docker has running containers. It does not install
GPU drivers, change Docker group membership, or change host profiling policy.

Setup also downloads pinned LULESH and Kokkos sources into an ignored build
directory. For that example, see the [LULESH CUDA guide](docs/benchmarks/lulesh.md).

If the host restricts GPU profiling, the default experiment fails explicitly.
Only with administrator approval, use the opt-in capability described in the
[XSBench guide](docs/benchmarks/xsbench.md). See the
[NVIDIA validation record](docs/nodes/nvidia-validation.md) for actual results and limitations.

## Current status

The XSBench and LULESH CUDA workflows have been tested on a Quadro RTX 6000; see the validation record above. Other workload guides remain preparation drafts. CPU and AMD setup scripts are not yet provided.

Historical launchers for other workloads contain machine-specific paths and image names. The included XSBench CUDA launcher instead uses its own directory and the image built by `setup_cuda.sh`. Confirm event support and dataset preparation for other workloads before treating measurements as reproducible.

The AMD ROCm/MLPerf 3D U-Net example is intentionally omitted from the run guides. The separate PyTorch 3D U-Net/KiTS19 guide covers the NVIDIA workflow.

## Requirements

The measurement workloads target Linux. GPU examples additionally require a compatible GPU, host drivers, and the matching container runtime/device access:

- NVIDIA: CUDA-capable GPU, NVIDIA driver, Docker, and NVIDIA Container Toolkit.
- AMD: ROCm-compatible GPU and ROCm drivers on the host, Docker, and access to `/dev/kfd` and `/dev/dri`.
- CPU: Docker and permission to access the host performance counters. PAPI `perf_event` access is controlled by host kernel/security settings.

The Dockerfiles provide tool environments; they do not provision Chameleon resources or download benchmark datasets.

## Build the base images

Run these commands from the repository root on a Linux machine with Docker:

```bash
docker build -f Dockerfile.cpu -t mincer-papi-cpu:latest .
docker build -f Dockerfile.papicuda -t mincer-papi-cuda:latest .
docker build -f Dockerfile.cypapi -t mincer-cypapi-cuda:latest .
docker build -f Dockerfile.rocm -t mincer-papi-rocm:latest .
docker build -f Dockerfile.amdrocpsdk -t mincer-rocm-sdk:latest .
```

These are baseline image names for a clean setup. The historical example scripts expect other names (for example, `papi_chameleon_cpu`, `final_dock`, and `amd_papi_test1`) and in some cases use fixed host paths. Adjust the script/image configuration to match your checkout and node; building a Dockerfile alone does not make those scripts portable.

## Run the MINCER utilities

The manifest generator and experiment runner are Python 3 scripts. Install `psutil` in the selected Python environment if it is not already available:

```bash
python3 -m pip install psutil
```

Generate a manifest for a workload directory:

```bash
python3 mincer-package/mincer_package.py \
  --path /path/to/workload \
  --output manifest.json
```

Run a workload directory that contains a `run.sh` script:

```bash
python3 mincer-package/run_experiment.py --path /path/to/workload
```

The runner records system information and captured script output in a timestamped `experiment_logs/` directory beneath the workload. By default it looks for `run.sh`; a different script can be selected with `--script`. The runner does not build the required image, fetch the workload, or download/convert datasets.

See [MINCER package usage](mincer-package/README.md) and [benchmark run guides](docs/benchmarks/README.md) for the limits and per-workload instructions.

For fresh Chameleon allocations, start with the [node-specific quick start](docs/nodes/quickstart.md).

## Testing and provenance

[`TESTING_REPORT.md`](TESTING_REPORT.md) records historical results from a previously provisioned Linux/AMD MI100 environment. Those results do not validate this cleaned, source-free distribution or the draft guides. Re-run the benchmarks on the provisioned Chameleon nodes and add current system details and logs only after verifying that they contain no sensitive information or large artifacts.

## Attribution

The benchmark guides link to the original upstream projects and the KiTS19 dataset. Follow each upstream project's license and citation requirements when downloading, running, or redistributing its source or data. Do not commit third-party benchmark sources or datasets to this repository.
