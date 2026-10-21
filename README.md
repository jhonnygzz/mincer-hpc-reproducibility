# MINCER: Reproducible HPC Performance Experiments

MINCER is a research toolkit for documenting computing environments and capturing experiment output alongside performance measurements from PAPI and GPU monitoring components.

## What this repository contains

- MINCER's environment-manifest and experiment-log utilities in `mincer-package/`.
- Dockerfiles for CPU, NVIDIA CUDA, and AMD ROCm/PAPI environments.
- Human-readable guides for acquiring and running the benchmark workloads.

Benchmark source trees, datasets, model weights, generated binaries, container images, and experiment logs are not part of the intended GitHub upload. Download workloads and data separately by following [the benchmark guides](docs/benchmarks/README.md). The root `.gitignore` excludes the current local benchmark tree and common generated data/artifacts.

## Current status

The run instructions are a preparation draft based on available project notes and files. They have **not** been validated on a newly provisioned Chameleon node. The setup scripts (`setup_cpu.sh`, `setup_cuda.sh`, and `setup_amd.sh`) are not present in this workspace.

The original example launch scripts also contain machine-specific absolute paths and expect PAPI-instrumented benchmark copies and image tags that are not consistently built by the Dockerfiles here. The guides call out these prerequisites rather than claiming that a fresh clone can run every PAPI example unchanged. Confirm paths, image tags, PAPI events, and dataset preparation on the target node before treating measurements as reproducible.

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

## Testing and provenance

[`TESTING_REPORT.md`](TESTING_REPORT.md) records historical results from a previously provisioned Linux/AMD MI100 environment. Those results do not validate this cleaned, source-free distribution or the draft guides. Re-run the benchmarks on the provisioned Chameleon nodes and add current system details and logs only after verifying that they contain no sensitive information or large artifacts.

## Attribution

The benchmark guides link to the original upstream projects and the KiTS19 dataset. Follow each upstream project's license and citation requirements when downloading, running, or redistributing its source or data. Do not commit third-party benchmark sources or datasets to this repository.
