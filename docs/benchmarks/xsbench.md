# XSBench

XSBench is a proxy application for the continuous-energy neutron cross-section
lookup kernel. This guide covers the validated CPU/OpenMP, NVIDIA CUDA, and AMD
HIP examples.

## Included NVIDIA CUDA example

The repository includes a small source-only XSBench v20 CUDA example with MINCER's
PAPI instrumentation. Upstream copyright and the MIT license are preserved in
[`LICENSE`](../../mincer-package/examples/XSBench/LICENSE). Builds, binaries, and
logs stay ignored. The CPU/OpenMP implementation from the verified handoff
bundle is included as source with PAPI instrumentation.

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

## Included AMD HIP example

The source-only AMD HIP implementation is under
[`hip`](../../mincer-package/examples/XSBench/hip/). It preserves the upstream
MIT license and instruments the PDF's eight `rocp_sdk` GPU events. The AMD
container is pinned to ROCm 6.4.3 and PAPI 7.2.0; other AMD nodes must verify
their GPU architecture, host driver compatibility, device permissions, and
event support independently.

On an AMD node with approved Docker access and read/write access to `/dev/kfd`
and the GPU render nodes, prepare the shared Python environment, build the
image, and preflight the complete event set once. By default, both HIP and PAPI
see only GPU index `0`, preventing PAPI's multi-agent aggregation from combining
counts from another visible GPU:

```bash
MINCER_USE_SUDO_DOCKER=1 bash setup_amd.sh
```

Omit `MINCER_USE_SUDO_DOCKER=1` when Docker is directly accessible. Setup does
not install host packages or drivers, change device permissions or host policy,
request extra capabilities, or use `--privileged`. Run the example through
MINCER. Set the same `MINCER_AMD_DEVICE` value for setup and run to select
another GPU index:

```bash
MINCER_USE_SUDO_DOCKER=1 "$HOME/.venvs/mincer/bin/python" \
  mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/hip"
```

The launcher builds for `gfx908` by default; use `MINCER_AMD_ARCH` only when
the node's compatible architecture is different. It targets device index `0`
by default, configurable with `MINCER_AMD_DEVICE`. It runs the PDF's default
large event-based case (17,000,000 lookups), not the historical launcher's
small case. Require `Verification checksum: 952131 (Valid)` and one measured
raw count for each of these exact event names:
`SQ_INSTS_SALU`, `SQ_INSTS_VALU`, `TCC_HIT`, `TCC_MISS`,
`TCC_EA_RDREQ_32B`, `TCC_EA_WRREQ_64B`, `SQ_INSTS_VMEM_RD`, and
`SQ_INSTS_VMEM_WR`. The output also derives a TCC hit fraction from the hit
and miss counts. These are not FLOP counts; the workflow does not sample power
or temperature. Failed initialization, event addition, start/stop,
synchronization, cleanup, or checksum validation produces a nonzero result.

MINCER saves output and its execution log under
`mincer-package/examples/XSBench/hip/experiment_logs/run_<timestamp>/`.
Compiler and PAPI preflight diagnostics are retained under the ignored
repository `build/` directory. See the [AMD validation record](../nodes/amd-validation.md)
for the tested node, observed results, measurement scope, and source-only test.

## Included CPU OpenMP example

The source-only CPU implementation is under
[`openmp-threading`](../../mincer-package/examples/XSBench/openmp-threading/).
It keeps the handoff's XSBench v20 source and MIT license, adds checked PAPI
measurement of the PDF's package/DRAM energy and total cycles/instructions, and
runs through MINCER. No separate dataset download is needed.

### Platform setup and run

From the repository root, prepare the shared CPU PAPI image and MINCER Python
environment once:

```bash
MINCER_USE_SUDO_DOCKER=1 bash setup_cpu.sh
```

On the validation node, this uses the administrator-approved non-interactive
`sudo -n docker` path; it does not prompt for a Linux password. Omit
`MINCER_USE_SUDO_DOCKER=1` when Docker is directly available to your account.
Setup does not change host counter policy.

Shared CPU setup also fetches pinned LULESH/Kokkos sources and requires Git and
`patch`; see the [CPU quick start](../nodes/quickstart.md#platform-setup).

**Counter-access prerequisite:** at this node's default
`perf_event_paranoid=4`, PAPI's required `PAPI_TOT_CYC` and `PAPI_TOT_INS`
events are unavailable. Package/DRAM energy can be read, but the full
measurement run correctly fails when CPU performance counters cannot be
collected. Arrange administrator-approved counter access before the measured
run; the profiling opt-in does not change host policy.

After approved counter access is arranged, invoke the included example through
MINCER:

```bash
MINCER_ALLOW_CPU_PROFILING=1 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/openmp-threading"
```

The launcher builds from source on each run and uses the PDF's large,
history-based, unionized-grid case: 500,000 particle histories, 34 lookups per
history (17,000,000 total), and the node's available thread count (96 on the
validated node). Set `MINCER_XSBENCH_THREADS` to override the thread count.
The problem uses about 5.6 GiB of host memory. Compiler diagnostics go to the
ignored `build/` directory; MINCER prints the timestamped `output.txt` location
under `experiment_logs/`.

Require `Verification checksum: 954318 (Valid)`, `PAPI RAPL energy
measurement: PASS`, and `PAPI performance measurement (main thread): PASS`,
including positive package/DRAM energy, `PAPI_TOT_CYC`, `PAPI_TOT_INS`, and IPC.
A valid checksum does not imply measurement success; required measurement
failures produce a nonzero run result.

### CPU permissions and measurement scope

The launcher drops all container capabilities by default. The explicit
`MINCER_ALLOW_CPU_PROFILING=1` opt-in adds only `CAP_PERFMON` and runs the
measurement container as container root; the root filesystem and workload
mount are read-only. Host `/sys` is mounted read-only so PAPI can discover the
RAPL uncore events. This is not `--privileged`, and neither setup nor launcher
changes host policy.

On the validation node, the successful full run required an
administrator-approved temporary change of `perf_event_paranoid` from `4` to
`0`; it was restored to `4` immediately after the run. Do not change this
setting yourself or assume `CAP_PERFMON` alone overrides the default policy.
Coordinate a counter-access window with the node administrator before running.
Do not rely on a shell cleanup trap as a guarantee of restoration after every
interruption or machine failure.

RAPL energy values are system energy for socket 0, not process-attributed
energy or whole-node totals. PAPI total cycles/instructions are attached to
XSBench's main thread while the OpenMP simulation runs; they are not sums over
all OpenMP workers. The derived cycle rate is not CPU frequency. These readings
are observations, not thresholds; other node models, policies, PAPI versions,
and container configurations may differ.

### CPU validation on the supplied node

Validated on October 22, 2026 on Ubuntu 24.04.4 / Linux 6.8.0-124-generic,
dual-socket Intel Xeon Gold 6240R, with Ubuntu 22.04 / PAPI 7.2.0 container
image and 96 OpenMP threads. The correctness checksum was valid and all exact
PDF-required measurements were collected:

| Metric | Observed result |
| --- | ---: |
| Verification checksum | 954318 (Valid) |
| Total lookups | 17,000,000 |
| Runtime | 1.667 s |
| Package energy, socket 0 | 933.996003 J |
| DRAM energy, socket 0 | 53.335491 J |
| Package + DRAM energy, socket 0 | 987.331494 J |
| Average package power, socket 0 | 560.140 W |
| Average DRAM power, socket 0 | 31.987 W |
| Average package + DRAM power, socket 0 | 592.127 W |
| PAPI_TOT_CYC, main thread | 5,208,251,732 |
| PAPI_TOT_INS, main thread | 838,689,162 |
| Main-thread cycle rate over simulation wall time | 3.124 Gcycles/s |
| Main-thread instruction rate over simulation wall time | 502.983 MIPS |
| IPC, main thread | 0.161031 |

The upstream Makefile compiles successfully but GCC warns about unchecked
`fread` return values in the optional binary-read path in `io.c`; the validated
default run uses generated data and binary mode is off.

The successful run used the host policy value `0` only for the administrator-
approved run window; the policy was verified restored to `4` afterward. The
default-policy test produced checksum `941535 (Valid)` for the upstream small
case and collected socket-0 RAPL energy, but correctly failed the required CPU
performance-counter checks. The report above is one measurement, not a
performance threshold.

Before committing, a source-only export passed all 19 package unit tests and
built XSBench without existing objects or binaries. Its small history-based run
again produced `941535 (Valid)` and exited nonzero for inaccessible CPU counters
under the unchanged policy `4`. This check reused the host Docker installation,
the existing CPU PAPI image, and the shared Python environment; it was not a
clean-OS test. The full measured run above was not repeated for this check.

## Other backends and upstream smoke tests

The external source steps below are optional and are not needed for the
included CPU/OpenMP or CUDA workflows. Use them only when testing an upstream
variant outside those validated examples.

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

For AMD, use the included, instrumented workflow above rather than the
historical external HIP launcher. The AMD PDF's large event-based run is the
validated case; an independent upstream clone does not contain MINCER's PAPI
instrumentation.

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

The included CPU/OpenMP, CUDA, and AMD HIP workflows are validated only on
their respective recorded nodes. The CPU launcher uses the shared opt-ins
`MINCER_ALLOW_CPU_PROFILING=1` (counter capability) and
`MINCER_USE_SUDO_DOCKER=1` (only if approved sudo Docker is needed), matching
the matrix example. Check available memory, PAPI event availability, and node
permissions before adapting the workflow to another CPU or GPU.
