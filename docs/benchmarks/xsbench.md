# XSBench

XSBench is a proxy application for the continuous-energy neutron cross-section lookup kernel. This guide covers CPU/OpenMP, NVIDIA CUDA, and AMD HIP runs with performance counters.

## Acquire the source

Clone the upstream project outside the MINCER repository:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/ANL-CESAR/XSBench.git \
  "$HOME/mincer-workloads/XSBench"
```

XSBench generates its problem data during initialization; no separate dataset download is needed. The Chesapeake graph dataset used by Gunrock is unrelated.

## Build and run upstream XSBench

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

For an AMD node, use the HIP implementation directory and ROCm/HIP compiler:

```bash
cd "$HOME/mincer-workloads/XSBench/hip"
make
./XSBench -s small -m event
```

Exact command-line options and compiler settings are documented in the upstream [XSBench README](https://github.com/ANL-CESAR/XSBench).

## Run through MINCER

The historical PAPI example directories used custom `run.sh` scripts. Once the PAPI-enabled variant and a launcher compatible with the node are available in the workload directory, invoke it from the MINCER repository root:

```bash
python3 mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/XSBench/openmp-threading"
```

Use the `cuda` or `hip` directory for the corresponding accelerator. The experiment runner requires `run.sh`; cloning upstream XSBench does not by itself provide MINCER's PAPI instrumentation or a guaranteed compatible launcher. The historical scripts also expect specific Docker image tags and should be checked/updated before use.

## Data, checks, and status

No external dataset is required. Record the verification checksum and whether XSBench reports it as valid. Previously recorded CPU and accelerator output values are hardware-specific examples, not thresholds for a new node.

This guide has not been run on Chameleon. Check available memory, PAPI component/event availability, and node permissions. The larger CPU problem size may require several gigabytes of memory; select a smaller size if node resources require it.
