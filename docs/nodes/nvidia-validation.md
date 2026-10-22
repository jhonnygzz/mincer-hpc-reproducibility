# XSBench CUDA validation

## Environment and scope

Tested October 22, 2026 on Ubuntu 24.04, Linux 6.8.0-124-generic,
Intel Xeon Gold 6126, approximately 187.4 GiB RAM, and one Quadro RTX 6000
with 24 GiB VRAM and NVIDIA driver 560.35.05. The host CUDA compiler is 12.6;
the experiment builds and runs inside CUDA 12.3.1 / Ubuntu 22.04 with PAPI 7.2.0.

This validates the NVIDIA XSBench example only, not CPU, AMD, other workloads,
other GPUs, or an unmodified upstream XSBench checkout.

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
