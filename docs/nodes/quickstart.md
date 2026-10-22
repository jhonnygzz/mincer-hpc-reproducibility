# Node quick start and hardware profiles

The Cascade Lake CPU, AMD Instinct MI100, and NVIDIA RTX 6000 are the hardware profiles used for the project owner's planned validation on Chameleon. They are examples, not requirements for MINCER users: users should run the relevant CPU, AMD, or NVIDIA workflow on their **own** Linux nodes with compatible processors/GPUs, drivers, and container support.

Adapt image versions, GPU architecture/compiler options, device access, thread counts, benchmark sizes, memory needs, and PAPI event selection to your hardware and administrator policies. A command that works on one of the three example nodes may need adjustment or may not be supported on another node. Begin with a small smoke test; do not start with the large medical-imaging workload.

The matrix-multiplication, XSBench, and LULESH CPU workflows have been validated
on one Xeon Gold 6240R node; the AMD commands below remain test plans.
See the [CPU validation record](cpu-validation.md) and
[README's CPU walkthrough](../../README.md#start-on-cpu) for the measured
results and shortest setup/run procedure.
The XSBench, LULESH, and Gunrock CUDA setup/run workflows have an
[NVIDIA validation record](nvidia-validation.md). Start with the
[README's NVIDIA walkthrough](../../README.md#start-with-xsbench-on-nvidia);
the external upstream smoke tests below are optional, not additional required
steps for those three instrumented examples.

## 1. Get the repository

The GitHub repository is private. The repository owner must add each tester's GitHub account as a collaborator before they clone it. On the node, authenticate with GitHub CLI (`gh auth login --web`) or the site's approved Git credential method, then clone over HTTPS. GitHub account passwords are not accepted for Git operations; never put an access token in a command, URL, or shared log.

```bash
git clone https://github.com/jhonnygzz/mincer-hpc-reproducibility.git \
  "$HOME/mincer-hpc-reproducibility"
cd "$HOME/mincer-hpc-reproducibility"
```

For the included CPU and NVIDIA workflows, continue to the applicable platform
setup below. Those setup scripts create the shared `$HOME/.venvs/mincer`
environment and install `psutil`; no separate activation, pip upgrade, or manual
Python setup is needed.

For standalone MINCER utilities or draft backends without platform setup,
create a user-local Python environment manually:

```bash
python3 --version
python3 -m venv "$HOME/.venvs/mincer"
source "$HOME/.venvs/mincer/bin/activate"
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

If this node's direct Docker check is denied but the administrator has approved
non-interactive sudo Docker access, check with `sudo -n docker version` instead.
The CPU commands below select that path explicitly with
`MINCER_USE_SUDO_DOCKER=1`; omit the variable when direct access works.

Record the output in your test notes, but remove usernames, access tokens, and other private values before sharing logs.

## CPU profile: Cascade Lake R

Use this section as the project's CPU validation profile. On another CPU node,
check the host's compiler, available memory, operating system, and PAPI/perf
permissions.

### Platform setup

From the repository root, prepare the shared MINCER Python environment and CPU
PAPI image once:

```bash
MINCER_USE_SUDO_DOCKER=1 bash setup_cpu.sh
```

Setup also fetches pinned LULESH/Kokkos sources into an ignored build directory;
it requires Git and `patch` in addition to Python venv support and Docker.

This node's approved Docker path works without an interactive `sudo -v`
authentication step. The opt-in uses non-interactive `sudo -n docker`; if it
does not work on another node, ask its administrator to configure Docker access
rather than entering a password into the benchmark command.

### Run a selected example

**Counter-access prerequisite:** on this node, the default
`perf_event_paranoid=4` policy prevents the required PAPI instruction and cycle
measurements. Setup can complete while the example still fails. Ask the
administrator to arrange approved counter access before running; the profiling
opt-in does not bypass host policy. See the
[CPU counter permissions](../benchmarks/matrix-multiplication.md#cpu-counter-permissions)
details and the [shared CPU validation record](cpu-validation.md#counter-access-prerequisite).

After counter access is arranged, run the selected example through MINCER:

```bash
MINCER_ALLOW_CPU_PROFILING=1 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/MatrixMultiplication/cpu"
```

Inspect the printed `output.txt` path under the workload's timestamped
`experiment_logs/` directory. Matrix multiplication must report PASS for both
numerical checks and matching outputs, and successful `PAPI_TOT_INS`,
`PAPI_TOT_CYC`, and IPC values for each layout. Counter failures produce a
nonzero result rather than fabricated measurements.

On this node,
`MINCER_ALLOW_CPU_PROFILING=1` and `MINCER_USE_SUDO_DOCKER=1` are explicit
opt-ins, and the default policy `perf_event_paranoid=4` prevents validated
PAPI collection. The successful run required administrator-managed temporary
policy access. Neither setup nor benchmark launchers change host policy.

### XSBench OpenMP

**Counter-access prerequisite:** the node's default `perf_event_paranoid=4`
blocks the PAPI instruction and cycle events required for a complete XSBench
run. Package/DRAM energy may still be collected, but missing performance
counters make the run fail. Ask the administrator to arrange approved counter
access before running; the profiling opt-in cannot override host policy. See
the [XSBench CPU permissions](../benchmarks/xsbench.md#cpu-permissions-and-measurement-scope).

Run the included XSBench source through MINCER:

```bash
MINCER_ALLOW_CPU_PROFILING=1 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/openmp-threading"
```

Inspect the printed `output.txt` path. Require `954318 (Valid)` and successful
package/DRAM energy, total cycles, total instructions, and IPC results. The
validated run used 96 threads and about 5.6 GiB of host memory. See the
[XSBench guide](../benchmarks/xsbench.md) for the recorded results and the
scope of the per-socket and main-thread counters. The CPU opt-ins and setup do
not change host counter policy.

### LULESH Kokkos/OpenMP

The same administrator-managed counter-access prerequisite applies; policy
`4` blocks the six required cycle/instruction/L1 events. After access is
arranged, run without repeating platform setup:

```bash
MINCER_ALLOW_CPU_PROFILING=1 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/LULESH/cpu"
```

Inspect the printed `output.txt` path. Require numerical correctness PASS for
the 96-cubed/10-iteration case, origin energy near `3.833852e+08`, symmetry
checks, and PAPI measurement PASS with all six events and IPC.
See the [LULESH CPU guide](../benchmarks/lulesh.md#cpu-prepare-and-run) for exact
tolerances, measured results, and main-thread counter scope. This example does
not claim energy measurement.

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
