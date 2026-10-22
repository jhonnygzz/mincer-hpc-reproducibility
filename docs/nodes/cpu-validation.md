# CPU validation

## Environment and scope

Validated October 22, 2026 on a Chameleon bare-metal node running Ubuntu
24.04.4 / Linux 6.8.0-124-generic, with two Intel Xeon Gold 6240R sockets,
96 logical CPUs, and approximately 187 GiB RAM. Builds and measurements used
the repository's Ubuntu 22.04 / PAPI 7.2.0 CPU image. XSBench and LULESH used
96 OpenMP threads.

This record covers CPU matrix multiplication, XSBench OpenMP, and LULESH
Kokkos/OpenMP on that node only. It does not validate AMD, other processors,
other PAPI configurations, or a clean operating-system installation.
The separate [NVIDIA record](nvidia-validation.md) covers CUDA workflows.

## New-user procedure

Follow the [README CPU walkthrough](../../README.md#start-on-cpu):

1. Obtain access to the private repository, authenticate, clone, and enter it.
2. Run `setup_cpu.sh` once with the approved Docker access path. It creates the
   shared Python environment, builds the CPU image, and prepares pinned
   LULESH/Kokkos sources. It needs Git, `patch`, Python venv support, Docker,
   and network access to fetch dependencies. No GPU setup or dataset is needed.
3. Satisfy the counter-access prerequisite below, separately from setup.
4. Run any selected example using the shared Python executable and
   `mincer-package/run_experiment.py --path ...`.
5. Inspect numerical checks and actual measurements in the printed log location.

Each launcher builds from source. MINCER captures output rather than streaming
it; initial builds can take several minutes. A script has a ten-minute timeout.
Successful runs print an `output.txt` path under the selected example's
`experiment_logs/run_<timestamp>/`, plus an execution-log path. On failure,
MINCER prints diagnostics and the execution-log path and saves the error in
`output.txt` in the same run directory. Compiler diagnostics are separate
timestamped files under the example's `build/` directory.

## Counter-access prerequisite

On this node, the default `perf_event_paranoid=4` prevents required
`PAPI_TOT_INS` and `PAPI_TOT_CYC` collection. Setup can complete while measured
runs still fail. A PAPI component listing is not proof of usable counters.

Successful measurements required separately approved temporary host-wide
policy access at value `0`, plus the explicit
`MINCER_ALLOW_CPU_PROFILING=1` container opt-in. Policy was restored to `4`
and verified after validation. This opt-in adds only `CAP_PERFMON` and uses
container root for measurement; **CAP_PERFMON alone did not work under policy
`4`**. The default measurement containers drop all capabilities. Workload and
root-filesystem mounts are read-only; XSBench additionally mounts host `/sys`
read-only for RAPL event discovery.

Ask the node administrator to arrange counter access before running. Setup and
launchers do not modify host policy, use `--privileged`, or silently skip
required measurements. No temporary sysctl wrapper is part of the normal
user procedure. A shell cleanup trap cannot guarantee restoration after every
interruption or machine failure.

Docker access is a separate prerequisite. This account used approved
`MINCER_USE_SUDO_DOCKER=1`, selecting non-interactive `sudo -n docker`.
No `sudo -v` or Linux-password prompt is needed for that configured path.
On another node, omit this variable if direct Docker works; if neither path
works, ask its administrator rather than guessing a password or weakening
permissions. Neither CPU opt-in grants host counter access automatically.

## Validated results

All three examples passed numerical checks and their required PAPI measurements
through MINCER during approved access. Counts and timings below are observations,
not portable performance thresholds.

| Example | Numerical result | Actual measurement |
| --- | --- | --- |
| [Matrix multiplication](../benchmarks/matrix-multiplication.md#validation-on-the-cpu-node) | Both layouts pass analytical per-element checks and match | Row: 118,032,507 instructions / 62,840,154 cycles, IPC 1.878298; column: 118,032,513 / 76,275,624, IPC 1.547447 |
| [XSBench](../benchmarks/xsbench.md#cpu-validation-on-the-supplied-node) | Large history-based case, 17 million lookups, `954318 (Valid)` | Main-thread 838,689,162 instructions / 5,208,251,732 cycles, IPC 0.161031; socket-0 package 933.996003 J and DRAM 53.335491 J |
| [LULESH](../benchmarks/lulesh.md#cpu-validation-on-the-supplied-node) | 96 cubed, 10 iterations; origin energy `3.833852e+08`, zero symmetry differences, automated numerical PASS | Main-thread 902,396,041 instructions / 3,921,171,081 cycles, IPC 0.230134; all four required L1 counters collected |

See the linked guides for complete readings, exact commands, and numerical
tolerances. XSBench/LULESH CPU counters are main-thread counts, not sums across
OpenMP workers. XSBench energy is system socket-0 energy, not process-attributed
or whole-node energy. Matrix and LULESH do not claim energy collection.
LULESH reports L1 miss counts, not a cache-access miss percentage.

## Failure checks and fresh-source validation

- At unchanged policy `4`, numerical checks still passed but missing required
  CPU counters made each workflow exit nonzero. Tests with profiling opted in
  also failed explicitly. No fabricated counter values were reported.
- XSBench could collect socket-0 package/DRAM energy at policy `4` in the tested
  configuration; that partial success did not make its overall run successful.
- Source-only exports built without old benchmark objects or binaries.
  Matrix passed its clean-source workflow. XSBench's pre-commit export built
  and passed the small-case checksum `941535 (Valid)` while correctly failing
  inaccessible CPU counters; its full measured run was not repeated in that
  export. LULESH fetched both pinned dependencies again, repeated setup,
  and passed the full numerical/six-counter MINCER run.
- The final package regression suite passed **27 tests**, including numerical
  rejection cases, launcher capability opt-ins, visible build/runtime failures,
  and checked PAPI error propagation. Earlier XSBench checkpoint testing had
  19 tests before LULESH's eight tests were added.
- These checks reused host Docker, cached CPU image layers, and the shared
  Python environment. Compiled regression tests also used the host compiler.
  They were not clean-OS or fully uncached-image tests.

No system packages, drivers, or shared services were changed. The only host
policy changes were the separately approved temporary measurement windows.
Generated dependencies, binaries, compiler logs, and experiment logs stay
ignored rather than being committed.

## Troubleshooting and remaining limits

| Symptom | Meaning and next action |
| --- | --- |
| Docker access or non-interactive sudo fails | Ask the administrator to configure the chosen Docker path; do not add interactive sudo authentication to the launcher |
| Image or LULESH sources missing | Run platform setup from the repository root; after changing LULESH patches/helpers, repeat preparation |
| PAPI event unavailable/component disabled, with numerical PASS | Measurement failed; check policy and approved access before repeating |
| Unsupported required event on another CPU | Do not substitute silently; review the experiment requirements before changing the metric set |
| `SKIP: No reference file provided` | Only MINCER's textual comparison was skipped; inspect the example's independent numerical and measurement checks |

Other nodes need their own validation. XSBench's optional binary-input path
emits upstream unchecked-`fread` warnings and was not used. Container OS
packages are not fully pinned, so this is a tested workflow, not a
byte-for-byte reproducible image.
