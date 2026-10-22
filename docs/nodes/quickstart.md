# Node quick start and hardware profiles

The Cascade Lake CPU, AMD Instinct MI100, and NVIDIA RTX 6000 are the hardware profiles used for the project owner's planned validation on Chameleon. They are examples, not requirements for MINCER users: users should run the relevant CPU, AMD, or NVIDIA workflow on their **own** Linux nodes with compatible processors/GPUs, drivers, and container support.

Adapt image versions, GPU architecture/compiler options, device access, thread counts, benchmark sizes, memory needs, and PAPI event selection to your hardware and administrator policies. A command that works on one of the three example nodes may need adjustment or may not be supported on another node. Begin with a small smoke test; do not start with the large medical-imaging workload.

The CPU and AMD commands below are a test plan, not verified results. The XSBench,
LULESH, and Gunrock CUDA setup/run workflows have an
[NVIDIA validation record](nvidia-validation.md). Start with the
[README's NVIDIA walkthrough](../../README.md#start-with-xsbench-on-nvidia);
the external upstream smoke tests below are optional, not additional required
steps for those three instrumented examples.

## 1. Get the repository and prepare Python

The GitHub repository is private. The repository owner must add each tester's GitHub account as a collaborator before they clone it. On the node, authenticate with GitHub CLI (`gh auth login --web`) or the site's approved Git credential method, then clone over HTTPS. GitHub account passwords are not accepted for Git operations; never put an access token in a command, URL, or shared log.

```bash
git clone https://github.com/jhonnygzz/mincer-hpc-reproducibility.git \
  "$HOME/mincer-hpc-reproducibility"
cd "$HOME/mincer-hpc-reproducibility"
```

Create a user-local Python environment for MINCER:

```bash
python3 --version
python3 -m venv "$HOME/.venvs/mincer"
source "$HOME/.venvs/mincer/bin/activate"
python -m pip install --upgrade pip
python -m pip install psutil
```

If `venv` is unavailable, ask the node administrator to install the matching Python venv package; avoid installing packages into the system Python.

> **Do not run `mincer-package/bootstrap.sh` as a setup shortcut.** It removes `/opt/papi` before installing PAPI and may overwrite a system or administrator-managed PAPI installation.

## 2. Common first checks

Run these before building an image. If Docker is missing or access is denied, ask the node administrator rather than changing system permissions yourself.

```bash
hostname
date -Is
uname -a
lscpu
free -h
docker version
```

Record the output in your test notes, but remove usernames, access tokens, and other private values before sharing logs.

## CPU profile: Cascade Lake R

Use this section as the project's CPU validation profile. On another CPU node, check the host's compiler, available memory, operating system, and PAPI/perf permissions. Adjust the `-t 4` example thread count to suit the node.

### Check the CPU PAPI image

From the repository root:

```bash
docker build -f Dockerfile.cpu -t mincer-papi-cpu:latest .
docker run --rm mincer-papi-cpu:latest papi_avail
docker run --rm mincer-papi-cpu:latest papi_component_avail
```

The CPU image installs PAPI with the `powercap` component. These commands check what the image exposes; they do not prove that CPU hardware counters are available to a container. Check the node's PAPI/perf permissions with its administrator if counter access fails. Do not change `perf_event_paranoid` or grant privileged container access without approval.

### XSBench CPU smoke test

Download XSBench outside the MINCER checkout:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/ANL-CESAR/XSBench.git \
  "$HOME/mincer-workloads/XSBench"
```

Build and run a small OpenMP problem in the CPU container:

```bash
docker run --rm \
  -v "$HOME/mincer-workloads/XSBench:/work/XSBench" \
  -w /work/XSBench/openmp-threading \
  mincer-papi-cpu:latest \
  bash -lc 'make clean && make && ./XSBench -s small -t 4'
```

Look for a successful run and a valid verification checksum. The upstream source is not the MINCER PAPI-instrumented variant, so this smoke test validates compilation/execution, not the historical PAPI measurements.

### Capture a run with MINCER

Add a small launcher to the downloaded workload directory (not to this repository):

```bash
cat > "$HOME/mincer-workloads/XSBench/openmp-threading/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run --rm \
  -v "$SCRIPT_DIR:/work" \
  -w /work \
  mincer-papi-cpu:latest \
  bash -lc 'make clean && make && ./XSBench -s small -t 4'
EOF
```

From the MINCER repository root, with the Python environment activated:

```bash
python mincer-package/mincer_package.py \
  --path "$HOME/mincer-workloads/XSBench/openmp-threading" \
  --output "$HOME/mincer-workloads/XSBench/mincer-manifest.json"
python mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/XSBench/openmp-threading"
```

The MINCER output is written under the external workload's `experiment_logs/` directory. For another CPU workload, see [LULESH](../benchmarks/lulesh.md) and [matrix multiplication](../benchmarks/matrix-multiplication.md); the matrix source/launcher must be supplied separately.

## AMD GPU profile: MI100

Use this section as the project's AMD validation profile. For another AMD accelerator, verify that its GPU architecture is supported by the host driver, ROCm container, and benchmark toolchain. Update architecture-specific compiler options when needed.

### Check host GPU and container access

On the host:

```bash
rocminfo
rocm-smi
ls -l /dev/kfd /dev/dri
```

Confirm the expected MI100 appears and that the account has approved access to the GPU device files. Do not install or replace host GPU drivers from inside a container.

### Build and check the ROCm/PAPI image

From the repository root:

```bash
docker build -f Dockerfile.rocm -t mincer-papi-rocm:latest .
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --security-opt seccomp=unconfined \
  mincer-papi-rocm:latest \
  bash -lc 'rocminfo && papi_component_avail && papi_avail'
```

The Dockerfile installs a ROCm 6.4.3 user-space stack. Confirm that it is compatible with the provisioned host driver before building or running. If the build or device check fails, save the error and ask the node administrator to confirm the supported host/ROCm combination; do not attempt to install kernel drivers inside the container.

### XSBench HIP smoke test

If XSBench is not already on this node, clone it outside the MINCER checkout:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/ANL-CESAR/XSBench.git \
  "$HOME/mincer-workloads/XSBench"
```

Compile and run the small HIP example:

```bash
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --security-opt seccomp=unconfined \
  -v "$HOME/mincer-workloads/XSBench:/work/XSBench" \
  -w /work/XSBench/hip \
  mincer-papi-rocm:latest \
  bash -lc 'make clean && make && ./XSBench -s small -m event'
```

Check that the program completes and reports a valid checksum. As with the CPU smoke test, an upstream checkout does not contain MINCER's custom PAPI instrumentation. Only add a `run.sh` and invoke `run_experiment.py` after the uninstrumented smoke test works; the launcher must pass the GPU device options above and compile/run in the container.

For example, create this launcher in the external HIP workload directory:

```bash
cat > "$HOME/mincer-workloads/XSBench/hip/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  --security-opt seccomp=unconfined \
  -v "$SCRIPT_DIR:/work" \
  -w /work \
  mincer-papi-rocm:latest \
  bash -lc 'make clean && make && ./XSBench -s small -m event'
EOF
```

Then, from the MINCER repository root:

```bash
python mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/XSBench/hip"
```

Then continue with the AMD variants in [LULESH](../benchmarks/lulesh.md) and [Gunrock](../benchmarks/gunrock.md). The AMD ROCm/MLPerf 3D U-Net example is excluded from this repository's test instructions.

## NVIDIA GPU profile: RTX 6000

For the included, PAPI-instrumented XSBench example, start with:

```bash
bash setup_cuda.sh
"$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/cuda"
```

See the [XSBench guide](../benchmarks/xsbench.md) for administrator-approved
profiling permissions and optional system installation. The upstream smoke test
below is separate and does not include MINCER instrumentation.

The same setup also prepares [LULESH CUDA](../benchmarks/lulesh.md) and
[Gunrock CUDA](../benchmarks/gunrock.md), including pinned sources and PAPI
patches. Their launchers are under `mincer-package/examples/LULESH/cuda`
and `mincer-package/examples/Gunrock/cuda`. Both keep verbose compiler details
in separate build logs while the main output focuses on measurements and
correctness checks.

Use this section as the project's NVIDIA validation profile. For another NVIDIA GPU, verify that its compute capability is supported by the selected CUDA toolkit and benchmark build flags. Select a compatible CUDA image/runtime rather than assuming CUDA 12.3.1 works on every host.

### Check host GPU and NVIDIA Container Toolkit

On the host:

```bash
nvidia-smi
docker run --rm --gpus all \
  nvidia/cuda:12.3.1-devel-ubuntu22.04 nvidia-smi
```

The second command checks that Docker can pass the GPU to a CUDA 12.3.1 container. If the node's driver/runtime combination is incompatible, stop and ask the node administrator which CUDA image version is supported.

### Build and check the CUDA/PAPI image

From the repository root:

```bash
docker build -f Dockerfile.papicuda -t mincer-papi-cuda:latest .
docker run --rm --gpus all mincer-papi-cuda:latest \
  bash -lc 'nvidia-smi && papi_component_avail && papi_avail'
```

The Dockerfile now propagates PAPI build/install failures. A successful Docker build alone still does not prove counter access; confirm components and run the instrumented benchmark.

### XSBench CUDA smoke test

If XSBench is not already on this node, clone it outside the MINCER checkout:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/ANL-CESAR/XSBench.git \
  "$HOME/mincer-workloads/XSBench"
```

Compile and run a small event-based CUDA problem:

```bash
docker run --rm --gpus all \
  -v "$HOME/mincer-workloads/XSBench:/work/XSBench" \
  -w /work/XSBench/cuda \
  mincer-papi-cuda:latest \
  bash -lc 'make clean && make && ./XSBench -s small -m event'
```

If compilation reports an unsupported GPU architecture, check the CUDA architecture flags in that checkout's Makefile and use a value supported by the RTX 6000 and installed CUDA toolkit. Record the checksum and whether it is valid. The ordinary upstream checkout is a smoke test, not the custom PAPI-enabled variant.

To capture the smoke test with MINCER, create a launcher in the external CUDA workload directory:

```bash
cat > "$HOME/mincer-workloads/XSBench/cuda/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker run --rm --gpus all \
  -v "$SCRIPT_DIR:/work" \
  -w /work \
  mincer-papi-cuda:latest \
  bash -lc 'make clean && make && ./XSBench -s small -m event'
EOF
```

Then, from the MINCER repository root:

```bash
python mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/XSBench/cuda"
```

The [Gunrock guide](../benchmarks/gunrock.md) is another NVIDIA GPU test.
[PyTorch 3D U-Net](../benchmarks/pytorch-3dunet.md) is deferred and not validated:
its uploaded HDF5 inputs are truncated, complete originals are unavailable, and
data conversion remains undocumented. It is excluded from the current walkthrough.

## What to send back after each node test

For each workload, report:

1. Node type, date, OS/kernel, CPU/GPU model, and driver/runtime versions.
2. Exact command, exit status, and relevant build/runtime errors.
3. Whether the benchmark completed and whether its checksum or correctness validation passed.
4. PAPI components/events that were actually available, separately from events that failed.
5. The path to the generated MINCER log. Keep dataset files, model weights, tokens, and private credentials out of the repository and shared logs.
