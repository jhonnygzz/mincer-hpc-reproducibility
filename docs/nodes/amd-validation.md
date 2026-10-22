# AMD ROCm validation

## XSBench HIP environment and scope

Validated October 22, 2026 on Ubuntu 24.04.4 / Linux 6.8.0-124-generic,
dual-socket AMD EPYC 7763 host with two AMD Instinct MI100 accelerators
(`gfx908`). Both GPUs use the host `amdgpu` kernel driver. The container used
the pinned AMD `rocm/dev-ubuntu-22.04:6.4.3` image and PAPI 7.2.0 with only the
`rocp_sdk` component. `hipcc` reported HIP 6.4.43484. Docker 29.1.3 was
administrator-approved and the shared `$HOME/.venvs/mincer` environment used
Python 3.12.3 with `psutil` 7.2.2.

This record covers XSBench HIP only. AMD LULESH/Kokkos and Gunrock HIP remain
unvalidated; no work was done on U-Net. The handoff bundle passed its supplied
SHA256 checksums before use. The repository checkout was clean at the latest
published `main` commit before changes. A terminal Git pull could not
authenticate; the available checkout already matched `origin/main` at
`eedaf8774aea9e215db89ab2dbe6a9fe77577f14`.

## Provisioning and permissions

With explicit user approval, Ubuntu's `docker.io` package and dependencies
(`containerd`, `runc`) were installed. Docker/containerd were started by package
installation. No AMD host driver was installed or replaced, no host security
policy or Docker configuration was changed, and no shared Docker service was
restarted. The official ROCm 6.4.3 development image recognized both MI100s
and `gfx908`.

The account received a per-user ACL for read/write access to `/dev/kfd` and
both render nodes. The benchmark launch does not alter device ACLs. That
`/dev/kfd` ACL may not persist if the device is recreated or after reboot.
Benchmark containers explicitly pass the KFD and render devices, drop all
capabilities, use a read-only root filesystem and workload mount, and do not
use `--privileged` or relax seccomp. No `CAP_SYS_ADMIN` or `CAP_PERFMON` was
added.

PAPI's `rocp_sdk` component was active; `perf_event` was disabled by the host's
`perf_event_paranoid=4`, which is unrelated to the GPU counter run. The
preflight discovered and successfully added all eight required events together:

- `rocp_sdk:::SQ_INSTS_SALU`
- `rocp_sdk:::SQ_INSTS_VALU`
- `rocp_sdk:::TCC_HIT`
- `rocp_sdk:::TCC_MISS`
- `rocp_sdk:::TCC_EA_RDREQ_32B`
- `rocp_sdk:::TCC_EA_WRREQ_64B`
- `rocp_sdk:::SQ_INSTS_VMEM_RD`
- `rocp_sdk:::SQ_INSTS_VMEM_WR`

PAPI's ROCprofiler SDK component aggregates counters across visible GPU agents.
The launcher therefore defaults both `ROCR_VISIBLE_DEVICES` and
`HIP_VISIBLE_DEVICES` to GPU index `0`, so benchmark execution and measurements
are scoped to the same single GPU. Set `MINCER_AMD_DEVICE` consistently for
setup and run if selecting another GPU. This is important on multi-GPU hosts.

## Numerical and measurement result

The included workflow compiled from source for `gfx908` and ran through MINCER
with the PDF's default large, event-based, unionized-grid workload:
17,000,000 lookups. The checksum was **952131 (Valid)**.

The source-only export also built and ran the same workload through MINCER,
without old XSBench binaries or object files. Its recorded output was:

| Measurement | Source-only observed result |
| --- | ---: |
| Runtime | 1.118 s |
| Lookups | 17,000,000 |
| `rocp_sdk:::SQ_INSTS_SALU` | 1,081,144,180 |
| `rocp_sdk:::SQ_INSTS_VALU` | 4,879,124,496 |
| `rocp_sdk:::TCC_HIT` | 860,659,788 |
| `rocp_sdk:::TCC_MISS` | 2,219,735,386 |
| `rocp_sdk:::TCC_EA_RDREQ_32B` | 0 |
| `rocp_sdk:::TCC_EA_WRREQ_64B` | 2,125,000 |
| `rocp_sdk:::SQ_INSTS_VMEM_RD` | 773,444,434 |
| `rocp_sdk:::SQ_INSTS_VMEM_WR` | 265,625 |
| Derived TCC hit fraction | 27.94% |
| Verification checksum | 952131 (Valid) |

The read-request event returned the actual value zero; the workflow does not
replace it with a fallback. Counter counts are observations, not thresholds.
Instruction counts are not FLOPs. The workflow does not measure GPU power,
temperature, or energy. The TCC hit fraction is calculated only from the TCC
hit and miss counts, not from total memory traffic.

### Profiler shutdown limitation

PAPI initialization, event addition, `PAPI_start`, synchronized workload
execution, `PAPI_stop`, and XSBench checksum validation succeeded in the
source-only run; MINCER returned status 0. After the measurements and success
line, ROCprofiler SDK emitted:

```text
No agent found for context: 10181
```

This shutdown-time SDK diagnostic did not change the returned measurements or
exit status, but its cause has not been determined. It is retained here rather
than being suppressed or treated as proof of a clean profiler shutdown.
The source-only validation reused the host Docker daemon, shared Python
environment, and built ROCm/PAPI image; the XSBench binary and objects were
rebuilt from source. This is not a clean-OS or uncached-image test.

## Reproduction

After administrator provisioning of Docker access and GPU device permissions,
from the repository root:

```bash
MINCER_USE_SUDO_DOCKER=1 bash setup_amd.sh
MINCER_AMD_DEVICE=0 MINCER_USE_SUDO_DOCKER=1 \
  "$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/XSBench/hip"
```

Omit `MINCER_USE_SUDO_DOCKER=1` when Docker is directly accessible. Inspect
the printed MINCER `output.txt` path for the checksum and all eight event names.
Compiler details and PAPI preflight diagnostics are saved under ignored
`build/` directories. Experiment output and the MINCER execution log are under
the example's ignored `experiment_logs/run_<timestamp>/` directory.

ROCm userspace is pinned to ROCm 6.4.3 and PAPI 7.2.0 in
[`Dockerfile.amdrocpsdk`](../../Dockerfile.amdrocpsdk). Other host drivers,
GPUs, architectures, and profiler releases need separate compatibility and
event checks. Neither setup nor launch changes host permissions or profiling
policy.
