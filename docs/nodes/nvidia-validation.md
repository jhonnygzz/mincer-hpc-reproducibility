# NVIDIA CUDA validation

## Environment and scope

Tested October 22, 2026 on Ubuntu 24.04, Linux 6.8.0-124-generic,
Intel Xeon Gold 6126, approximately 187.4 GiB RAM, and one Quadro RTX 6000
with 24 GiB VRAM and NVIDIA driver 560.35.05. The host CUDA compiler is 12.6;
the experiment builds and runs inside CUDA 12.3.1 / Ubuntu 22.04 with PAPI 7.2.0.

The following sections validate NVIDIA XSBench, LULESH, and Gunrock only, not CPU, AMD,
other workloads, other GPUs, or unmodified upstream checkouts.

## Problems found and resolutions

| Check | Observation | Repository resolution |
| --- | --- | --- |
| Original launcher | Docker absent, misleading missing-image error | Setup checks prerequisites; explicit opt-in Ubuntu system installation |
| Python runner | `psutil` absent | Setup creates a user-local Python venv and installs it |
| Image naming | Historical build and launcher names differed | Shared `mincer-papi-cuda:latest` default |
| PAPI build | Old Dockerfile suppressed failures | Build errors now stop the image build |
| NVML component tests | Build tried `/bin/nvcc` | Set `PAPI_CUDA_ROOT=/usr/local/cuda` |
| Counter access | Default run failed at PAPI start with code -14; host restricts profiling | Check all PAPI operations; administrator-approved capability is explicit opt-in |
| Results logging | Failure could imply success; matching reference logged as skipped | Nonzero failure/mismatch status, saved diagnostics, distinct skip/pass |
| Metric identity | Missing events could shift reported values | Require this example's complete event set before reporting |

## Measured instrumented result

With administrator-approved `MINCER_ALLOW_GPU_PROFILING=1`, the full large,
event-based problem completed successfully:

| Result | Observed |
| --- | --- |
| Lookups | 17,000,000 |
| Verification checksum | 952131 (Valid) |
| FP instruction counter | 59,092,388 |
| DRAM bytes | 13,812,778,829 |
| L1 texture bytes | 5,667,477,164 |
| L2 bytes | 3,297,568,966 |
| NVML power | 133.11 W |
| NVML temperature | 27 degrees C |
| Reported simulation runtime | 0.833 seconds |

These are observations, not performance thresholds. Initialization, compilation,
and container startup are outside the reported simulation runtime. Raw generated
logs stay local and ignored rather than being committed.

A second test exported only tracked and intended non-ignored files into a new
directory (approximately 280 KiB for the entire working source tree, excluding
Git history). Setup and a full rebuild/run succeeded there without the uploaded
MINCER tree, old benchmark binaries, or old logs. The Docker build reused its
already-tested image layers. The second run again reported checksum 952131
(Valid), all four CUDA metrics, and both NVML metrics.

## Remaining limitations

- Restricted GPU profiling needs administrator approval; setup does not disable
  the host's profiling restriction or alter the GPU driver.
- PAPI event names and support vary by GPU; the example fails explicitly if its
  required metrics are unsupported.
- The default architecture is `sm_75`; adapt the Makefile for another GPU.
- Upstream binary-file I/O code emits existing unchecked-`fread` warnings.
  The tested workflow does not use binary-file mode.
- The runner captures output rather than streaming it; the script timeout is
  ten minutes. Python reference comparison is textual, not a numerical tolerance.
- The image's Ubuntu packages are not fully pinned; this is a tested workflow,
  not a byte-for-byte reproducible container build.
- Automatic system-install mode is Ubuntu-specific and was not replayed against
  a newly reimaged machine; its package/runtime steps were performed on this node.

## LULESH CUDA

The uploaded Kokkos copy was incomplete: a clean build failed on missing
`desul/atomics/Atomic_Ref.hpp`. A fresh pinned Kokkos 4.6.01 resolved compilation.
No uploaded binaries or static libraries were used.

The original LULESH source ran the 96-cubed/10-iteration case without extra
capabilities and printed the expected energy and symmetry checks, but silently
failed to collect CUDA counters. NVML assignment also failed, as it did in the
historical PDF log. This was not a successful monitoring test.

The repository now fetches pinned Mini-Apps and Kokkos revisions and applies a
small local instrumentation patch. Native CUDA events are initialized before
NVML and before Kokkos. Missing events and failed counter operations are errors,
and GPU work is fenced at measurement boundaries.

With explicitly approved `CAP_SYS_ADMIN` profiling, the patched source produced:

| Result | Observed |
| --- | --- |
| Problem size | 96 cubed / 884,736 elements |
| Iterations / MPI tasks | 10 / 1 |
| Final origin energy | 3.833852e+08 |
| MaxAbsDiff / TotalAbsDiff / MaxRelDiff | 0 / 0 / 0 |
| FP instruction count | 9,832,246 |
| DRAM bytes | 3,265,675,365 |
| L1 bytes | 1,147,284,118 |
| L2 bytes | 1,170,706,925 |
| Sampled NVML utilization / temperature | 0 percent / 26 degrees C |

A subsequent run through the new source-download/patch/launcher workflow also
completed successfully. Utilization is a sampled reading, not an integrated
activity metric; zero is not evidence that CUDA was unused. Performance values
vary. The NVML names and default architecture currently target this Quadro RTX
6000; CPU/AMD and other GPU names are not validated.

A clean source-only export (approximately 316 KiB for the entire repository
working source tree) fetched both dependencies again, rebuilt, and passed the
same numerical and complete-metric checks through MINCER. Existing Docker image
layers were reused. Repeating preparation is supported. A negative test without
the profiling capability returned status 1 with an explicit CUDA-counter startup
error instead of silently omitting metrics.

After cleanup, a further full run passed with compiler output in a separate
timestamped build log. The OpenMP macro now respects the command-line setting;
the build no longer emits the `USE_OMP` redefinition warning. Main benchmark
output was reduced to 55 lines without removing measurements or numerical checks.

## Gunrock CUDA BFS

The uploaded source revision is
`530f25443864d04c25286c053d6812a888b4d779`. The uploaded dependency Git databases
reported damaged pack/index files, so no existing dependency checkouts or
binaries were trusted. Fresh upstream source and five pinned CMake dependencies
built successfully in the existing CUDA/PAPI image.

The example follows the PDF's Chesapeake graph and source vertex 17. It builds
only the BFS target (DAWN algorithm at this revision) and adds `--validate`.
The old PDF log showed an NVML assignment failure and unchecked CUDA start calls.
The patch now checks all six metrics, synchronizes GPU work, and returns nonzero
on PAPI failures or distance mismatches.

With explicitly approved profiling capability, a complete new launcher run gave:

| Result | Observed |
| --- | --- |
| Source vertex / graph vertices | 17 / 39 |
| GPU/CPU distance mismatches | 0 |
| FP64 instructions | 0 |
| DRAM bytes | 6,325 |
| L1 bytes | 172 |
| L2 bytes | 71,130 |
| Sampled NVML utilization / temperature | 0 percent / 26 degrees C |
| Reported GPU elapsed time | 0.246368 milliseconds |

Zero FP64 instructions is expected for this BFS workload; zero sampled GPU
utilization is possible for such a short run. Neither value indicates failed
monitoring when PAPI start/stop calls succeed. Bytes/times are observations, not
thresholds. Main output is 22 lines; full CMake/compiler diagnostics are retained
in a separate timestamped build log.

A negative test without extra capability returned status 1 with an explicit
CUDA-counter startup error, not false success. Repeating source preparation
succeeded. Eight Python regression tests cover runner reporting and both quiet
launchers, including build/runtime failures and opt-in capability handling.
Other GPUs, AMD HIP, and CPU backends remain unvalidated.

A final source-only export (approximately 360 KiB for the whole repository
working tree, excluding Git history) ran `setup_cuda.sh`, downloaded fresh
Gunrock/dependency sources, rebuilt BFS, and again reported zero CPU/GPU
distance mismatches with all six measurements present. Only the existing tested
Docker image layers and Python environment were reused. This is not a test of
automatic system installation on a newly reimaged node.

## Fresh-user walkthrough, October 22, 2026

An HTTPS clone from GitHub stopped at an unavailable authentication prompt,
consistent with the documented private-repository access requirement. A clean
`git clone --no-local` from the committed local repository was used instead.
This validates the committed checkout, not GitHub authentication or anonymous
access. No ignored dependencies, binaries, or logs came from the original
checkout or uploaded MINCER tree.

From that clone, `bash setup_cuda.sh` completed, fetched fresh pinned sources,
and printed the three run commands. All three were then run through MINCER
with the previously approved `MINCER_ALLOW_GPU_PROFILING=1`:

| Workload | Exit status | Inspected correctness result | Measurements |
| --- | --- | --- | --- |
| XSBench | 0 | 17 million lookups; checksum `952131 (Valid)` | Four CUDA counters, NVML power and temperature |
| LULESH | 0 | 96 cubed, 10 iterations; energy `3.833852e+08`; all three symmetry differences zero | Four CUDA counters, NVML utilization and temperature |
| Gunrock BFS | 0 | Source 17; zero CPU/GPU distance mismatches | Four CUDA counters, NVML utilization and temperature |

The eight existing Python regression tests also passed. Generated payloads
remained ignored and the test clone's tracked working tree stayed clean.
No workload/setup implementation changes were needed. The README now includes
clone/access instructions, all three run commands, profiling guidance, and
the checks to inspect in the saved output.

This machine already had Docker, NVIDIA Container Toolkit, the tested container
layers, and the Python environment. Those were reused; this is not a clean-OS
installation test. Initial benchmark source/dependency downloads and compilation
were performed again. System installation and changes to host profiling policy
were not attempted.

## Deferred: PyTorch 3D U-Net

The three uploaded KiTS19 HDF5 inputs are truncated and cannot be opened.
Complete original copies are unavailable, and a reproducible conversion process
has not been supplied. The workflow is deferred, not validated, and excluded
from the fresh-user walkthrough. No new U-Net image build, full dataset download,
or training run was performed.
