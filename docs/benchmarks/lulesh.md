# LULESH with Kokkos

LULESH is a hydrodynamics proxy application. This repository prepares an
instrumented NVIDIA CUDA example from pinned upstream sources. CPU and AMD
variants remain planned and are not validated here.

When a MINCER CPU LULESH launcher is implemented, it must use the shared CPU
opt-ins `MINCER_ALLOW_CPU_PROFILING=1` (counter capability) and
`MINCER_USE_SUDO_DOCKER=1` (only if sudo Docker is required), matching the
matrix example. Host counter policy remains administrator-managed.

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
values and environment details. CPU/HIP upstream builds are separate future
workflows; the uploaded machine-specific launchers are not portable instructions.
