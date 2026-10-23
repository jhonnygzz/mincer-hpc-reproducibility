# Gunrock BFS on NVIDIA CUDA

This example reproduces the PDF's CUDA Gunrock BFS workload with the Chesapeake
graph and PAPI counters. It uses Gunrock's `bfs` target, whose selected algorithm
at this revision is DAWN. The AMD HIP variant is future work, not validated here.

## Prepare and run

From the repository root on a compatible NVIDIA node:

```bash
bash setup_cuda.sh
"$HOME/.venvs/mincer/bin/python" mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/Gunrock/cuda"
```

If the CUDA/PAPI image and Python environment are already prepared, source
preparation alone is:

```bash
bash prepare_gunrock_cuda.sh
```

With explicit administrator approval on a host that restricts GPU counters:

```bash
MINCER_ALLOW_GPU_PROFILING=1 "$HOME/.venvs/mincer/bin/python" \
  mincer-package/run_experiment.py \
  --path "$PWD/mincer-package/examples/Gunrock/cuda"
```

This is the same opt-in `CAP_SYS_ADMIN` mechanism documented for
[XSBench](xsbench.md). It is a powerful capability and must not be used without
approval. The measurement container has a read-only filesystem and workload
mount. Compilation runs separately as the invoking user, without GPU access or
additional capabilities. Neither setup nor the launcher disables host profiling
restrictions or replaces drivers.

See the [node quick start](../nodes/quickstart.md) for host prerequisites and the
explicit Ubuntu system-install option. Git, `patch`, and `tar` are also required.

## Lightweight, repeatable source preparation

The preparation script downloads the tested Gunrock source and applies the local
instrumentation patch. That patch also pins five CMake dependencies (CCCL,
ModernGPU, cxxopts, nlohmann/json, and CMake Modules) to fixed revisions,
rather than following moving branches.

The unmodified upstream checkout and generated working source stay under ignored
`build/` directories. Re-running preparation refreshes generated work files;
edit the repository's patch, not `build/work`, to retain instrumentation changes.
Modified or unexpected upstream checkouts are rejected instead of overwritten.
All upstream license notices remain in the downloaded source.

The Chesapeake Matrix Market graph is already in the pinned source tree; no
separate dataset download is needed. Its header describes a symmetric 39-by-39
graph with 170 stored entries. The launcher builds only the BFS target, not
every Gunrock example or unit test. Initial CMake configuration requires network
access to fetch dependencies.

The default image is `mincer-papi-cuda:latest`, with CUDA 12.3.1, PAPI 7.2.0, and
CMake 3.27.7. `MINCER_CUDA_IMAGE` overrides the image name. The CUDA architecture
is 75 and NVML event names target `Quadro_RTX_6000:device_0`; other GPUs require
matching architecture and supported event names.

## Expected results and differences from the PDF

The benchmark uses the PDF's graph and fixes source vertex **17**, as shown in
the PDF screenshot, rather than choosing a random source. It additionally
passes `--validate` so every GPU distance is compared against the CPU reference:

```text
=== CUDA Performance Results (Run 1) ===
  FP64 instructions: 0
  DRAM bytes: ...
  L1 cache bytes: ...
  L2 cache bytes: ...
=== NVML Monitoring ===
  GPU utilization (%): ...
  Temperature (C): ...
Source : 17
GPU distances[:39] = ...
CPU Distances[:39] = ...
Number of errors : 0
=== Gunrock CUDA BFS Test Complete ===
```

The important correctness result is `Number of errors : 0`. Distance mismatches
return a nonzero exit status. The FP64 instruction count may legitimately be zero
for this graph-traversal workload; it is not a FLOP total. CUDA byte totals and
timings vary and are not portable thresholds. NVML utilization is a sampled
reading, not an average over this very short traversal, so zero is possible.

The instrumentation initializes native CUDA/NVML events before graph allocation and requires all six
metrics, with checked setup/start/stop calls and synchronization boundaries.
Missing measurements cause a visible failure instead of an apparent success.

## Logs and failures

The main captured output stays focused on measurements, distances, and validation:

```text
mincer-package/examples/Gunrock/cuda/experiment_logs/run_<timestamp>/
  output.txt
  execution_log_<timestamp>.txt
```

Compiler and CMake details are saved separately in `build/build_<timestamp>.log`;
the main output prints its path. A failed build prints its last 30 diagnostic
lines and exits nonzero. Nothing is silently suppressed, but successful compiler
commands and container startup banners do not obscure results.
