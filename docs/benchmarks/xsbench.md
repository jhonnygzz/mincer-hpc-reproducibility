# XSBench

XSBench is a proxy application for the continuous-energy neutron cross-section lookup kernel. This guide covers CPU/OpenMP, NVIDIA CUDA, and AMD HIP runs with performance counters.

## Included NVIDIA CUDA example

The repository includes a small source-only XSBench v20 CUDA example with MINCER's
PAPI instrumentation. Upstream copyright and the MIT license are preserved in
[`LICENSE`](../../mincer-package/examples/XSBench/LICENSE). Builds, binaries, and
logs stay ignored. CPU and HIP examples are not yet included or tested here.

From the repository root:

```bash
bash setup_cuda.sh
"$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/cuda"
```

The setup creates a user-local Python environment, builds `mincer-papi-cuda:latest`
with CUDA 12.3.1 and PAPI 7.2.0, and displays GPU/component diagnostics. GPU native
events are distinct from CPU presets: `papi_avail` reporting zero CPU presets does
not mean that CUDA/NVML native events are unavailable.

Docker, NVIDIA Container Toolkit, a working host NVIDIA driver, and Python venv
support must exist first. With administrator approval on Ubuntu 22.04/24.04,
`bash setup_cuda.sh --install-system` installs these prerequisites except the
driver. It restarts Docker only if no containers are running. Review this script
before authorizing system changes. Setup does not change host profiling policy.

### Restricted profiling

On hosts with `RmProfilingAdminOnly: 1` in `/proc/driver/nvidia/params`, collecting
CUDA counters may require administrator-approved capability access. The default
launcher does not request extra capabilities and fails rather than print invalid
measurements. After explicit administrator approval:

```bash
MINCER_ALLOW_GPU_PROFILING=1 "$HOME/.venvs/mincer/bin/python" \
  mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/cuda"
```

This runs the measurement container as container root with `CAP_SYS_ADMIN`, a
powerful capability. It is not `--privileged`; the workload mount and container
root filesystem are read-only, with a temporary writable `/tmp`. Compilation
runs separately with the invoking user's UID/GID. Do not use this option on
shared infrastructure without permission; an administrator may instead provide
an approved profiling environment.

### Expected results

The launcher rebuilds from source and runs `./XSBench -m event`: the PDF's default
large, unionized-grid problem with 17,000,000 lookups. Allow roughly 6 GB of GPU
memory plus host initialization memory and time. The default Makefile targets
`sm_75` (the Quadro RTX 6000); other architectures may need a Makefile change.
The instrumented run requires all four CUDA events and both NVML events; missing
events or failed start/stop calls are errors, not partial successes.

Expect `Verification checksum: 952131 (Valid)`, four CUDA counter values, NVML
power in watts and temperature, and runtime/throughput. Floating-point instruction
counts are not FLOP counts, and watts are not joules. Traffic ratios compare
separate memory levels, not fractions of a single total. Runtime includes
monitoring overhead; values are not formal profiler measurements.

Captured output and diagnostics are saved in:

```text
mincer-package/examples/XSBench/cuda/experiment_logs/run_<timestamp>/
  output.txt
  execution_log_<timestamp>.txt
```

No textual reference is supplied because timings and measurements vary. A skipped
reference comparison is not a correctness pass: inspect the checksum and metrics.
See the [validation record](../nodes/nvidia-validation.md) for tested results and
known limitations. `MINCER_CUDA_IMAGE` overrides the image for setup and launcher;
`MINCER_VENV` overrides the Python environment location for setup.

## Other backends and upstream smoke tests

### Acquire the upstream source

Clone the upstream project outside the MINCER repository:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/ANL-CESAR/XSBench.git \
  "$HOME/mincer-workloads/XSBench"
```

XSBench generates its problem data during initialization; no separate dataset download is needed. The Chesapeake graph dataset used by Gunrock is unrelated.

### Build and run upstream XSBench

Choose the implementation directory appropriate for the node. The upstream project documents `make` and the standard executable invocation:

```bash
cd "$HOME/mincer-workloads/XSBench/openmp-threading"
make
./XSBench
```

For an NVIDIA node, use the CUDA implementation directory and a CUDA-enabled compiler/runtime:

```bash
cd "$HOME/mincer-workloads/XSBench/cuda"
make
./XSBench -m event
```

For an AMD node, use the HIP implementation directory and ROCm/HIP compiler:

```bash
cd "$HOME/mincer-workloads/XSBench/hip"
make
./XSBench -s small -m event
```

Exact command-line options and compiler settings are documented in the upstream [XSBench README](https://github.com/ANL-CESAR/XSBench).

### Run external variants through MINCER

The historical PAPI example directories used custom `run.sh` scripts. Once the PAPI-enabled variant and a launcher compatible with the node are available in the workload directory, invoke it from the MINCER repository root:

```bash
python3 mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/XSBench/openmp-threading"
```

Use the `cuda` or `hip` directory for the corresponding accelerator. The experiment runner requires `run.sh`; cloning upstream XSBench does not by itself provide MINCER's PAPI instrumentation or a guaranteed compatible launcher. The historical scripts also expect specific Docker image tags and should be checked/updated before use.

### Data, checks, and status

No external dataset is required. Record the verification checksum and whether XSBench reports it as valid. Previously recorded CPU and accelerator output values are hardware-specific examples, not thresholds for a new node.

These external CPU/HIP procedures remain unvalidated; the included CUDA example's results are recorded above. When a MINCER CPU XSBench launcher is implemented, it must use the shared CPU opt-ins `MINCER_ALLOW_CPU_PROFILING=1` (counter capability) and `MINCER_USE_SUDO_DOCKER=1` (only if sudo Docker is required), matching the matrix example. Check available memory, PAPI component/event availability, and node permissions. The larger CPU problem size may require several gigabytes of memory; select a smaller size if node resources require it.
