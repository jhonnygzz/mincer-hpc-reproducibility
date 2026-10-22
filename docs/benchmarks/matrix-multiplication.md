# CPU matrix multiplication

This example compares row-major and column-major storage for the same 256 x 256
matrix multiplication. It reports PAPI total instructions, total cycles, and
derived IPC for each kernel. Numerical correctness is checked independently
against an analytical result for every output element; the two layouts are also
compared directly. No external dataset or reference-output file is needed.

## Platform setup

Clone the repository and prepare the shared MINCER Python environment and CPU
PAPI image once:

```bash
git clone https://github.com/jhonnygzz/mincer-hpc-reproducibility.git
cd mincer-hpc-reproducibility
MINCER_USE_SUDO_DOCKER=1 bash setup_cpu.sh
```

On this node, the approved Docker sudo path works non-interactively, so do not
run `sudo -v`; the opt-in uses `sudo -n docker`. If that fails on another node,
ask the administrator to configure Docker access. On nodes where Docker is
directly accessible, omit `MINCER_USE_SUDO_DOCKER=1`. Setup prepares the shared
`$HOME/.venvs/mincer` environment, installs `psutil`, builds the CPU PAPI image,
and lists its components. Component availability does not prove that hardware
counters can be read.

Shared CPU setup also prepares pinned LULESH/Kokkos sources, requiring Git and
`patch`; see the [CPU quick start](../nodes/quickstart.md#platform-setup).

## Run through MINCER

**Prerequisite on this CPU node:** the default `perf_event_paranoid=4` policy
blocks the PAPI instruction and cycle counters required by this example. Setup
may succeed, but the run below will fail its measurement checks until the
administrator arranges approved counter access. Do not repeat the run expecting
the profiling opt-in to bypass the host policy. See
[CPU counter permissions](#cpu-counter-permissions).

After counter access is arranged, run the selected example through the existing
MINCER runner:

```bash
MINCER_ALLOW_CPU_PROFILING=1 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/MatrixMultiplication/cpu"
```

For nodes where Docker is directly accessible, omit
`MINCER_USE_SUDO_DOCKER=1`. Inspect the printed `output.txt` path under the
example's timestamped `experiment_logs/` directory. Require PASS for row-major
correctness, column-major correctness, and matching outputs; also require successful
`PAPI_TOT_INS`, `PAPI_TOT_CYC`, and IPC for both layouts. Compiler diagnostics
are saved separately under the ignored `build/` directory. Counter failures
produce a nonzero result.

## CPU counter permissions

The normal setup and run procedure does not change host security settings or
grant capabilities automatically. On this node, the default
`perf_event_paranoid=4` prevents the validated counter collection: PAPI 7.2
disables its `perf_event` component and the default run fails without reporting
counter values.

The successful run required an administrator-approved temporary change of the
host-wide setting to `0`; the setting was restored to `4` after the run. Do not
change it yourself or rely on a shell cleanup trap to guarantee restoration
after every interruption or machine failure.

The matrix launcher requires the explicit
`MINCER_ALLOW_CPU_PROFILING=1` opt-in to add only `CAP_PERFMON` to the
measurement container; all other container capabilities are dropped. **Do not
assume `CAP_PERFMON` alone works here:** it was tested and did not enable PAPI
collection under the default policy value of `4`. Coordinate counter policy
with the administrator before enabling the container capability. If Docker
access requires an administrator-configured non-interactive sudo rule, set
`MINCER_USE_SUDO_DOCKER=1`; this uses `sudo -n docker` and does not prompt for a
password. Neither opt-in changes the host setting.

The validated [CPU XSBench](xsbench.md#included-cpu-openmp-example) and
[LULESH](lulesh.md#cpu-prepare-and-run) launchers use these same two CPU opt-in
variables and fail explicitly when required counters cannot be collected.

## Validation on the CPU node

Validated on October 22, 2026 on Ubuntu 24.04.4 / Linux 6.8.0-124-generic,
dual-socket Intel Xeon Gold 6240R, 96 logical CPUs, and 187 GiB RAM. The
instrumented source built in the Ubuntu 22.04 / PAPI 7.2.0 CPU image from the
repository and ran through MINCER. Both layouts passed the analytical
per-element check and matched each other; both required PAPI events were
collected successfully:

| Layout | PAPI_TOT_INS | PAPI_TOT_CYC | IPC |
| --- | ---: | ---: | ---: |
| Row-major | 118,032,507 | 62,840,154 | 1.878298 |
| Column-major | 118,032,513 | 76,275,624 | 1.547447 |

These are observations, not expected values or performance thresholds. The
account normally has no Docker socket access, so this run used
administrator-approved `sudo docker`. At the host's initial
`perf_event_paranoid=4`, PAPI 7.2 disabled its `perf_event` component even with
the container's `CAP_PERFMON`; the first MINCER run correctly failed without
reporting counters. For the successful run, the administrator-approved host
setting was temporarily changed to `0` and restored to `4` immediately after
MINCER completed. The scripts themselves never modify host policy.

`setup_cpu.sh` reused cached Docker image layers, including the Ubuntu/PAPI
installation; this was not a clean-OS or uncached-image test. The existing
`$HOME/.venvs/mincer` already contained `psutil`. No host packages, drivers, or
services were changed.

## Checks and remaining limitations

Require all three numerical checks to say `PASS`, and require both variants to
report successful `PAPI_TOT_INS`, `PAPI_TOT_CYC`, and `IPC` values. PAPI setup,
event availability, event addition, start, and stop failures produce explicit
errors; failed or non-positive counters are never printed as valid results.
Counter values and IPC are measurements, not performance thresholds.

The host PAPI 7.1 installation also detects the CPU `perf_event` component, but
adding either required event directly as the unprivileged host user fails with
permission status -15. The validated workflow therefore depends on the
administrator-approved temporary host policy change and container capability
described above. Other CPU models, counter policies, PAPI versions, and Docker
configurations are not validated.
