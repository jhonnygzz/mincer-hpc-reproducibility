# MINCER: Reproducible HPC Performance Experiments

MINCER is a research toolkit for documenting HPC computing environments and capturing experiment output alongside performance measurements from PAPI and GPU monitoring components.

## What this repository contains

- MINCER's environment-manifest and experiment-log utilities in `mincer-package/`.
- Dockerfiles for CPU, NVIDIA CUDA, and AMD ROCm/PAPI environments.
- Human-readable guides for acquiring and running the benchmark workloads.
- A [node quick start](docs/nodes/quickstart.md) with Cascade Lake CPU, MI100, and RTX 6000 hardware profiles. These are validation targets; MINCER users should adapt the steps to their own nodes.

The PAPI-instrumented XSBench CPU/OpenMP and CUDA examples are included with
their upstream license, as is the CPU matrix multiplication source. LULESH and
Gunrock CUDA use pinned upstream downloads plus small instrumentation patches;
LULESH CPU/OpenMP uses the same pinned dependencies with CPU instrumentation.
Other benchmark source trees, datasets, model weights, generated binaries,
container images, and experiment logs are excluded. Follow [the benchmark
guides](docs/benchmarks/README.md) for those workloads.

The CPU matrix multiplication example and `setup_cpu.sh` provide a separate
CPU-only starting point. It has been validated through MINCER on one Xeon Gold
6240R node, with analytical numerical checks and actual PAPI measurements; see
the [matrix guide](docs/benchmarks/matrix-multiplication.md) for the observed
results and the administrator-approved counter-access requirements.

The CPU XSBench OpenMP example is also validated through MINCER on that node.
Its guide records the checksum, package/DRAM RAPL energy, main-thread PAPI
counters, and the node's administrator-managed counter-access prerequisite.

CPU LULESH/Kokkos is also validated on that node, including numerical checks
and the PDF's six cycle/instruction/L1 counters. CPU setup prepares its pinned
sources. See the [CPU quick start](docs/nodes/quickstart.md#cpu-profile-cascade-lake-r)
for the shared setup/run procedure and counter-access prerequisite.

## Start on CPU

The repository is private, so your GitHub account needs access and an approved
authentication method before cloning. Never put tokens in clone URLs or logs.

```bash
git clone https://github.com/jhonnygzz/mincer-hpc-reproducibility.git
cd mincer-hpc-reproducibility
```

With Git, `patch`, Python 3 with venv support, and administrator-configured
Docker access, set up once:

```bash
MINCER_USE_SUDO_DOCKER=1 bash setup_cpu.sh
```

This node uses approved non-interactive `sudo -n docker`; omit
`MINCER_USE_SUDO_DOCKER=1` from setup and run commands when Docker is directly
accessible. Setup creates the shared Python environment, builds the CPU PAPI
image, and fetches pinned LULESH/Kokkos sources. No GPU setup is needed.

**Before running:** this node's default `perf_event_paranoid=4` blocks the
required instruction/cycle measurements. Arrange administrator-approved
[counter access](docs/nodes/cpu-validation.md#counter-access-prerequisite)
first. Neither setup nor the profiling opt-in changes host policy.

After access is arranged, run a selected example through MINCER:

```bash
MINCER_ALLOW_CPU_PROFILING=1 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/MatrixMultiplication/cpu"
```

Change only `--path` to select another CPU example; no repeat setup is needed:

| Example | Path relative to the repository | Required checks |
| --- | --- | --- |
| Matrix multiplication | `mincer-package/examples/MatrixMultiplication/cpu` | Both layouts correct, outputs match, instructions/cycles and IPC for each |
| XSBench | `mincer-package/examples/XSBench/openmp-threading` | `954318 (Valid)`, package/DRAM energy PASS, main-thread performance PASS |
| LULESH | `mincer-package/examples/LULESH/cpu` | Numerical correctness PASS, all six main-thread PAPI counters and IPC |

Open the printed output/log location. Builds and runs are captured rather than
streamed, so the terminal may be quiet while MINCER works. A numerical PASS or
`SKIP: No reference file provided` alone does not establish measurement success.
See the [CPU validation record](docs/nodes/cpu-validation.md) for observed
results, failure diagnostics, measurement scope, and fresh-source test limits.

## Start with XSBench on NVIDIA

First clone the repository and enter it:

```bash
git clone https://github.com/jhonnygzz/mincer-hpc-reproducibility.git
cd mincer-hpc-reproducibility
```

The repository is currently private: the owner must grant your GitHub account
access, and you must authenticate using GitHub CLI or an approved Git credential
method before cloning. Never put a token in the clone URL or shared logs.

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

Setup also prepares pinned LULESH/Kokkos and Gunrock sources in ignored build
directories. Run them from the same repository root without repeating setup:

```bash
"$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/LULESH/cuda"
"$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/Gunrock/cuda"
```

If the host restricts GPU profiling, the default experiment fails explicitly.
Only with administrator approval, use the opt-in capability described in the
[XSBench guide](docs/benchmarks/xsbench.md). See the
[NVIDIA validation record](docs/nodes/nvidia-validation.md) for actual results and limitations.

After approval, prefix **each** run command with `MINCER_ALLOW_GPU_PROFILING=1`.
Setup alone does not authorize counter access. Initial builds/downloads can take
several minutes, and MINCER captures output rather than displaying live progress.

For each run, open the printed `output.txt` path under the workload's
`experiment_logs/` directory. Check XSBench's `952131 (Valid)` checksum,
LULESH's origin energy near `3.833852e+08` and zero symmetry differences, and
Gunrock's `Number of errors : 0`. Each example must also print four CUDA
measurements and two NVML measurements. A skipped reference comparison is
normal, but does not establish correctness. See the
[LULESH guide](docs/benchmarks/lulesh.md) and
[Gunrock guide](docs/benchmarks/gunrock.md) for details and build-log locations.

## Current status

The XSBench, LULESH, and Gunrock CUDA workflows have been tested on a Quadro
RTX 6000; see the validation record above. CPU matrix multiplication,
XSBench OpenMP, and LULESH/Kokkos are validated on the same CPU node; see the
[CPU validation record](docs/nodes/cpu-validation.md).
AMD workflows remain drafts. AMD setup is not provided.

Historical launchers for other workloads contain machine-specific paths and image names. The included XSBench CUDA launcher instead uses its own directory and the image built by `setup_cuda.sh`. Confirm event support and dataset preparation for other workloads before treating measurements as reproducible.

The AMD ROCm/MLPerf 3D U-Net example is intentionally omitted from the run guides.
The separate NVIDIA PyTorch 3D U-Net/KiTS19 workflow is **deferred, not validated**:
the uploaded HDF5 inputs are truncated, complete originals are unavailable, and
reproducible data conversion remains missing. It is not part of this quick start.

## Requirements

The measurement workloads target Linux. GPU examples additionally require a compatible GPU, host drivers, and the matching container runtime/device access:

- NVIDIA: CUDA-capable GPU, NVIDIA driver, Docker, and NVIDIA Container Toolkit.
- AMD: ROCm-compatible GPU and ROCm drivers on the host, Docker, and access to `/dev/kfd` and `/dev/dri`.
- CPU: Git, `patch`, Python venv support, Docker, and permission to access host performance counters. PAPI
  `perf_event` access is controlled by host kernel/security settings; see the
  [CPU matrix guide](docs/benchmarks/matrix-multiplication.md) and
  [XSBench guide](docs/benchmarks/xsbench.md).

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

[`TESTING_REPORT.md`](TESTING_REPORT.md) records historical results from a previously provisioned Linux/AMD MI100 environment. Current NVIDIA results are recorded separately in the [NVIDIA validation record](docs/nodes/nvidia-validation.md). Re-run benchmarks on each target node; historical output does not establish support for another hardware/software configuration. Share logs only after checking for sensitive information and large artifacts.

## Attribution

The benchmark guides link to the original upstream projects and the KiTS19 dataset. Follow each upstream project's license and citation requirements when downloading, running, or redistributing its source or data. Do not commit third-party benchmark sources or datasets to this repository.
