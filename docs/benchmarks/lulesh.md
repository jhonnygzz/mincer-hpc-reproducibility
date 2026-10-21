# LULESH with Kokkos

LULESH (Livermore Unstructured Lagrangian Explicit Shock Hydrodynamics) is a hydrodynamics proxy application. This guide covers Kokkos CPU, CUDA, and AMD HIP/ROCm builds with PAPI measurements.

## Acquire the source

Clone the Kokkos Mini-Apps project outside this repository:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/kokkos/kokkos-miniapps.git \
  "$HOME/mincer-workloads/kokkos-miniapps"
```

The workload is in `lulesh-2.0/`, with backend-specific directories such as `kokkos-no-uvm_cpu`, `kokkos-no-uvm_cuda`, and `kokkos-no-uvm_amd`. There is no external benchmark dataset to download.

## Build and run upstream

Follow the upstream Kokkos Mini-Apps build requirements for the selected backend. The historical MINCER commands compiled inside a backend-specific container and ran a small case:

```bash
cd "$HOME/mincer-workloads/kokkos-miniapps/lulesh-2.0/kokkos-no-uvm_cpu"
export KOKKOS_USE_DEPRECATED_MAKEFILES=1
make clean
make -j
./lulesh.kk -s 96 -i 10
```

For CUDA or AMD, use the matching backend directory and a container/toolchain with the corresponding Kokkos backend enabled. Use the upstream [Kokkos Mini-Apps project](https://github.com/kokkos/kokkos-miniapps) for build prerequisites and current source layout.

## Run through MINCER

The PAPI examples wrap the build and executable in `run.sh`, then run the directory through MINCER. After preparing a PAPI-enabled, node-compatible `run.sh` in the selected workload directory:

```bash
python3 mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/kokkos-miniapps/lulesh-2.0/kokkos-no-uvm_cpu"
```

Change the final directory to `kokkos-no-uvm_cuda` or `kokkos-no-uvm_amd` for the GPU node. The upstream source alone does not include the MINCER-specific PAPI instrumentation used by this project. Existing launchers also mount hard-coded `/home/cc/` paths and use varying image names; correct these locally before running.

## Verify and status

The example reports a final origin-energy value and plane checks for the small case. Capture these alongside elapsed time and the PAPI output, but do not compare timings across different hardware as a pass/fail threshold. This guide is not yet validated on a Chameleon allocation.
