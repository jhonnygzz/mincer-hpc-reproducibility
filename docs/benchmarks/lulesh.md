# LULESH with Kokkos

LULESH is a hydrodynamics proxy application. This repository prepares
instrumented CPU/OpenMP and NVIDIA CUDA examples from pinned upstream sources.
Both have been validated on their recorded nodes. The AMD HIP workflow below
uses a separate legacy ROCm profiling image, not XSBench's ROCprofiler SDK image.

## AMD HIP: prepare and run

With administrator-approved Docker access and read/write access to `/dev/kfd`
and the GPU render nodes, run from the repository root:

```bash
MINCER_USE_SUDO_DOCKER=1 bash setup_amd.sh --lulesh
MINCER_USE_SUDO_DOCKER=1 "$HOME/.venvs/mincer/bin/python" \
  mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/LULESH/hip"
```

Omit `MINCER_USE_SUDO_DOCKER=1` when Docker is directly accessible. Setup uses
the shared Python environment, prepares pinned dependencies, builds
`mincer-rocm-legacy:latest`, and preflights the exact five `rocm` counters and
three `rocm_smi` sensors from the PDF screenshot. The image contains ROCm 6.4.3
and PAPI 7.2.0, and does not enable `rocp_sdk`. No host packages, drivers,
security policies, or device ACLs are changed. CPU/NVIDIA setup does not
download these AMD dependencies.

The launcher always rebuilds from source, using Kokkos 4.6.01 with HIP/OpenMP
and architecture `AMD_GFX908` (MI100), then runs `-s 96 -i 10`. Build failures
stop execution rather than running an old binary. Sources are prepared from
the same pinned Mini-Apps and Kokkos revisions as the NVIDIA example below;
the original handoff sources are not build dependencies. Full checkouts and
their upstream notices remain in the ignored `build/` directory. Only generated
`build/work` is refreshed. Edit the tracked patch/helpers and rerun setup or
`bash prepare_lulesh_hip.sh`, not generated source files.

The default `MINCER_AMD_DEVICE=0` selects one physical GPU using
`ROCR_VISIBLE_DEVICES`, with HIP device `0` inside that restricted view.
The helper matches that HIP device's PCI address to its ROCm SMI index, since
SMI does not necessarily share HIP's visibility ordering. GPU index 0 is the
validated LULESH target on this MI100 node. Index 1 passes ROCm device discovery
but its legacy PAPI ROCm event initialization fails preflight with
`Insufficient memory`; do not assume it is measurable. On other systems, use a
different index only after setup preflight succeeds, and keep the selection the
same for setup and run.
`MINCER_AMD_LEGACY_IMAGE` overrides the image; `MINCER_LULESH_THREADS` overrides
the default single host OpenMP thread. Compilation uses the invoking account's
UID/GID without GPU devices. Measurement uses container root with all
capabilities dropped, explicitly passed GPU devices, read-only root/workload
filesystems, and no privileged or unconfined-seccomp option.

### AMD numerical and measurement checks

Require the 96-cubed problem (884,736 elements), exactly 10 iterations,
origin energy near `3.833852e+08`, printed symmetry diagnostics, and
`LULESH numerical correctness: PASS`. The shared CPU numerical validator also
requires finite, nonnegative element energies, relative origin-energy tolerance
`1e-6`, and plane-zero symmetry tolerance
`1e-10 * max(1, abs(a), abs(b))`.

Require `PAPI measurement: PASS`, successful process status, and all eight
event readings:

- `rocm:::SQ_INSTS_SALU:device=0`
- `rocm:::SQ_INSTS_VALU:device=0`
- `rocm:::SQ_WAVES:device=0`
- `rocm:::TCC_HIT_sum:device=0`
- `rocm:::TCC_MISS_sum:device=0`
- `rocm_smi:::busy_percent:device=<matched-index>` in percent
- `rocm_smi:::power_average:device=<matched-index>:sensor=0` in microwatts
- `rocm_smi:::temp_current:device=<matched-index>:sensor=0` in millidegrees Celsius

PAPI initializes legacy profiling before HIP/Kokkos. Required component,
event-query/addition, start/stop, synchronization, and cleanup failures return
nonzero with errors. Kokkos fences bound the measured time-stepping loop.
No partially populated event list or uninitialized values are reported.
SMI readings are endpoint samples of driver-reported values, not whole-run
averages. Power is not energy, instructions are not FLOPs, and the VALU share
of instruction counts is not GPU utilization. Only the TCC hit fraction is
derived, using hits divided by hits plus misses when the denominator is nonzero.
GPU counters and sensors can include other users' activity on the same GPU;
device selection is not exclusive scheduling.

Compiler diagnostics are saved separately under the example's
`build/build_<timestamp>.log`; MINCER saves `output.txt` and its execution log
under `experiment_logs/run_<timestamp>/`. Setup diagnostics are under the
repository's ignored `build/`. A skipped MINCER reference comparison is not
a numerical correctness pass. See the [AMD validation record](../nodes/amd-validation.md)
for actual results and validation status.

## CPU: prepare and run

From the repository root, prepare the shared Python environment, CPU PAPI image,
and pinned LULESH/Kokkos sources once:

```bash
MINCER_USE_SUDO_DOCKER=1 bash setup_cpu.sh
```

Prerequisites are Git, `patch`, Python 3 with venv support, and administrator-
configured Docker access. On the validation node the explicit
`MINCER_USE_SUDO_DOCKER=1` opt-in uses approved non-interactive `sudo -n docker`,
without asking for a password. Omit it when your account has direct Docker
access. No system packages or host counter settings are changed by setup.

**Permissions prerequisite:** this node's default `perf_event_paranoid=4`
prevents the required CPU counters, even with the profiling opt-in. Arrange
administrator-approved counter access before the measured run; see
[CPU permissions](#cpu-permissions-and-measurement-scope).

After counter access is arranged, run through MINCER:

```bash
MINCER_ALLOW_CPU_PROFILING=1 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/LULESH/cpu"
```

Inspect the printed `output.txt` path. Require both
`LULESH numerical correctness: PASS` and
`PAPI measurement (main thread): PASS`, followed by all six counters and IPC.
Numerical success alone is not a successful measurement run.

The launcher builds from source with four build jobs, runs the PDF's
`-s 96 -i 10` case, and defaults to the available CPU count (96 threads on this
node). Set `MINCER_LULESH_THREADS` to override the OpenMP thread count.
`MINCER_CPU_IMAGE` and `MINCER_VENV` have the same meanings as in the other
CPU examples. The latter selects the setup environment; use its Python
executable in the run command if overridden.

MINCER output goes under `mincer-package/examples/LULESH/cpu/experiment_logs/`;
compiler diagnostics go to timestamped `build/build_<timestamp>.log` files,
whose locations are printed. Failed builds show the last 30 diagnostic lines.
The default CPU image is `mincer-papi-cpu:latest`.

### CPU source preparation

`setup_cpu.sh` calls `prepare_lulesh_cpu.sh`, fetching the same fixed Mini-Apps
and Kokkos 4.6.01 revisions listed in the NVIDIA section below into the CPU
example's ignored `build/` directory. The handoff's application files match
that Mini-Apps revision apart from its PAPI hooks. A small local patch restores
those hooks with checked error propagation, fences measurement boundaries,
and adds numerical validation. The included `papi_metrics.cpp` and
`papi_metrics.h` replace the handoff helper's unchecked operations while
retaining its main-thread measurement scope.

The full pinned checkouts, including upstream notices, remain intact. Only
generated `build/work` sources are refreshed. Modify the tracked patch/helper
files, not generated sources, and rerun setup or `bash prepare_lulesh_cpu.sh`
after changing them. Unexpected revisions or dirty dependency checkouts are
rejected rather than overwritten. No handoff files or old binaries are needed.
The CPU build uses generic OpenMP rather than a fixed Cascade Lake architecture.

### CPU permissions and measurement scope

The default measurement container drops all capabilities and uses the invoking
UID/GID. The explicit `MINCER_ALLOW_CPU_PROFILING=1` opt-in adds only
`CAP_PERFMON` and uses container root. Its root filesystem and workload mount
are read-only. Compilation is separate and runs as the invoking UID/GID.
Neither setup nor launcher changes host policy or uses `--privileged`.

On this node, successful collection required an approved temporary host-wide
change of `perf_event_paranoid` from `4` to `0`. The original `4` was restored
and verified after each validation window. `CAP_PERFMON` alone did not enable
the required counters under policy `4`. Coordinate access with the administrator;
do not treat a shell cleanup trap as guaranteed restoration after every
interruption or machine failure.

The exact six events shown in the PDF's CPU output are required:
`PAPI_TOT_CYC`, `PAPI_TOT_INS`, `PAPI_L1_DCM`, `PAPI_L1_ICM`,
`PAPI_L1_LDM`, and `PAPI_L1_TCM`. Initialization, availability, addition,
start, stop, and cleanup are checked. Any required-counter failure returns a
nonzero result, without fabricated or zero fallback values. Real cache miss
counts may be zero; cycles and instructions must be positive.

These are main-thread counts around the Kokkos/OpenMP time-stepping loop,
not sums across workers. IPC is that thread's instructions divided by cycles.
No multiplexing or substitute events were needed on this node.

The handoff additionally tries L1 store misses and energy names that do not
appear as successful events in the PDF output. They are not claimed here.
The PDF's zero "Total Energy" is not a successful energy measurement. Its
"L1 Cache Miss Rate" divides misses by cycles, not cache accesses, so this
workflow does not repeat that misleading percentage or claim energy collection.

### CPU numerical validation

The fixed workload must complete 10 iterations on a 96-cubed mesh
(884,736 elements), with one non-MPI task. The added check requires:

- All element energies finite and nonnegative.
- Origin energy within relative tolerance `1e-6` of the PDF's rounded
  `3.833852e+08` numerical result.
- Plane-zero symmetry within `1e-10 * max(1, abs(a), abs(b))` for each pair.

Other sizes/iteration counts need their own numerical reference and are
rejected by this example's check. Timing and counter values are not thresholds.
Numerical results are checked even when monitoring fails; the overall run
then still fails. MINCER's separate textual reference comparison can say
`SKIP`, but that is not the numerical check above.

### CPU validation on the supplied node

Validated October 22, 2026 on Ubuntu 24.04.4 / Linux 6.8.0-124-generic,
dual-socket Xeon Gold 6240R, 96 logical CPUs, approximately 187 GiB RAM,
using the Ubuntu 22.04 / PAPI 7.2.0 CPU image and 96 OpenMP threads:

| Result | Observed |
| --- | ---: |
| Iterations / MPI tasks | 10 / 1 |
| Final origin energy | 3.833852e+08 |
| MaxAbsDiff / TotalAbsDiff / MaxRelDiff | 0 / 0 / 0 |
| Numerical correctness | PASS |
| PAPI_TOT_CYC, main thread | 3,921,171,081 |
| PAPI_TOT_INS, main thread | 902,396,041 |
| PAPI_L1_DCM, main thread | 26,978,676 |
| PAPI_L1_ICM, main thread | 292,870 |
| PAPI_L1_LDM, main thread | 7,382,533 |
| PAPI_L1_TCM, main thread | 27,271,546 |
| IPC, main thread | 0.230134 |
| Elapsed simulation time | 1.68 s |

A fresh source-only export fetched both dependencies again, ran platform setup,
built without old objects/libraries, and passed the same numerical and six-event
checks through MINCER. That repeat observed IPC `0.244914`; readings vary.
Both the ordinary restricted run and a policy-`4` run with profiling opted in
passed numerical checks but exited nonzero with explicit required-event errors.
All 27 package tests passed, including eight new launcher, numerical, and
compiled PAPI-error regression tests. Builds produced no compiler warnings.

This reused the host's Docker installation, cached CPU image layers, shared
Python environment, and host compiler for regression tests. It was not a clean-OS
test. No system packages, GPU setup, or shared services were changed. Temporary
PDF-rendering tools were isolated outside the repository and are not benchmark
dependencies. Host policy is back at `4`; ordinary runs still need the
administrator-managed prerequisite above.

## NVIDIA: prepare and run

From the repository root on a compatible NVIDIA node:

```bash
bash setup_cuda.sh
"$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/LULESH/cuda"
```

Setup requires Git, `patch`, Python venv support, Docker, NVIDIA Container
Toolkit, and a working NVIDIA driver. See the [node quick start](../nodes/quickstart.md)
for prerequisites and the explicit Ubuntu system-install option. Setup does not
change host profiling policy.

If setup has already built the CUDA/PAPI image, source preparation alone is:

```bash
bash prepare_lulesh_cuda.sh
```

This downloads fixed revisions of
[Kokkos Mini-Apps](https://github.com/kokkos/kokkos-miniapps/tree/870fea7443a915336d9a545b0267dd6eb5bed396)
and [Kokkos 4.6.01](https://github.com/kokkos/kokkos/tree/1b1383c6001f3bfe9fe309ca923c2d786600cc79),
then applies the local PAPI patch in a generated work directory. Upstream files,
dependency Git histories, binaries, and logs stay ignored. The generated
`build/work` sources are refreshed by preparation; do not edit them as your
authoritative source. Modify the repository's instrumentation patch instead.
Modified or unexpected dependency checkouts are rejected rather than overwritten.

## GPU profiling permission

As with XSBench, a restricted host requires administrator approval to collect
CUDA counters. After approval:

```bash
MINCER_ALLOW_GPU_PROFILING=1 "$HOME/.venvs/mincer/bin/python" \
  mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/LULESH/cuda"
```

The measurement container then uses container root with `CAP_SYS_ADMIN`, a
powerful capability, not `--privileged`. Its filesystem and workload mount are
read-only. Compilation uses the invoking user's UID/GID in a separate container
without GPU access or added capabilities.

The launcher uses `mincer-papi-cuda:latest` (override with `MINCER_CUDA_IMAGE`)
and rebuilds from source with four build jobs. The default architecture is
Turing75 and the NVML names currently target `Quadro_RTX_6000:device_0`. Other
GPUs need corresponding Makefile/event changes; unsupported events fail
explicitly rather than silently reducing the metric set.

## Expected output

The PDF's case is `./lulesh.kk -s 96 -i 10`:

- Problem size: 96 cubed, 884,736 elements, one non-MPI task.
- Iteration count: 10.
- Final origin energy: approximately `3.833852e+08` at the displayed precision.
- Plane-zero energy symmetry checks: MaxAbsDiff, TotalAbsDiff, MaxRelDiff zero
  in the validated configuration.
- CUDA FP instruction count, DRAM bytes, L1 bytes, and L2 bytes.
- NVML utilization and temperature. Utilization is a sampled value and can be
  zero even though GPU computation completed; it is not whole-run average activity.

The FP metric counts instructions, not FLOPs. Times and counters are observations,
not portable thresholds. Inspect the numerical checks separately from monitoring.
The underlying numerical checks print diagnostics; this example does not add an
automated numerical-tolerance comparison.

MINCER captures benchmark output and system information under:

```text
mincer-package/examples/LULESH/cuda/experiment_logs/run_<timestamp>/
  output.txt
  execution_log_<timestamp>.txt
```

Compiler commands and warnings are saved separately in timestamped
`build/build_<timestamp>.log` files, with the path printed in the run output.
Failed builds print the last 30 diagnostic lines and exit nonzero. Container
startup banners are omitted from the example output; the image retains its
upstream license notices. The main log focuses on PAPI measurements and numerical
checks, as in the PDF.

A skipped reference comparison is expected; it is not proof of correctness.
PAPI event setup/start/stop failures now stop the example with a nonzero status.

## Validation and the old Kokkos problem

On October 22, 2026, the uploaded Kokkos copy failed a clean build because
`desul/atomics/Atomic_Ref.hpp` was missing. Fetching pinned Kokkos 4.6.01 fixed
this; users do not need to manually replace folders.

The old LULESH code could exit successfully without collecting CUDA counters.
Its historical log also contains an NVML component initialization failure.
The patch now initializes native events before Kokkos, requires the complete
metric set, checks start/stop calls, and fences GPU work around measurement.
This enabled CUDA and NVML readings on this RTX 6000. It does not establish that
all other PAPI/Kokkos/GPU combinations are supported.

See the [NVIDIA validation record](../nodes/nvidia-validation.md) for measured
values and environment details. HIP uses the separate workflow above; the
uploaded machine-specific launchers are not portable instructions.
