# Gunrock BFS

Gunrock is a GPU graph-processing framework. This guide covers CUDA BFS and HIP/ROCm BFS runs instrumented with PAPI.

## Acquire the sources

For the CUDA implementation:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/gunrock/gunrock.git \
  "$HOME/mincer-workloads/gunrock-cuda"
```

For the AMD HIP port:

```bash
git clone --branch hip-develop https://github.com/AMD-HPC/gunrock.git \
  "$HOME/mincer-workloads/gunrock-hip"
```

The example uses the small Chesapeake Matrix Market graph at `datasets/chesapeake/chesapeake.mtx`, which may be distributed with the Gunrock source tree. Check that path exists in the checked-out revision; otherwise follow that revision's dataset documentation.

## Build and run upstream

Gunrock requires the matching accelerator compiler and CMake. The upstream CUDA quick start builds an algorithm and runs it with the Chesapeake graph:

```bash
cd "$HOME/mincer-workloads/gunrock-cuda"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target bfs -j"$(nproc)"
./build/bin/bfs --market datasets/chesapeake/chesapeake.mtx
```

For the HIP port, follow the checked-out branch's HIP-specific setup and build instructions. The upstream instructions include building the `bfs` target and passing the same graph file.

## Run through MINCER

The PAPI-enabled workflow uses a custom `bfs_papi` executable for AMD and PAPI changes for CUDA. Those modifications are not in this source-free repository and are not guaranteed to be present in the upstream clone. Once the appropriate PAPI-enabled source and a compatible `run.sh` are available, run the selected workload directory through MINCER:

```bash
python3 mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/gunrock-cuda"
```

Use `gunrock-hip` for AMD. The launcher must build/run the instrumented variant and use the image prepared for that node. Update the historical launcher's absolute mount paths and image tags rather than using its original `/home/cc/` paths unchanged.

## Verify and status

Record BFS distances, elapsed time, and CUDA or ROCm event values. An earlier CUDA run showed an NVML component initialization failure while CUDA event collection continued; verify component initialization on the provisioned node and record which counters actually succeeded. Compare GPU and CPU distances for the AMD run. Timings and event totals are hardware-specific. This guide is untested on a fresh Chameleon allocation.
