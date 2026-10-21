# Matrix-multiplication reproducibility example

This CPU example compares row-major and column-major matrix multiplication and reports PAPI hardware counters such as total instructions and total cycles. It demonstrates MINCER's experiment logging and is not a separate third-party benchmark release.

## Requirements

- A Linux CPU node with Docker.
- The `mincer-papi-cpu` image built from `Dockerfile.cpu` (or an equivalent PAPI CPU image).
- The MINCER-specific matrix source files and a `run.sh` that compiles and executes both variants. They are not included in the source-free GitHub distribution; preserve or recreate them locally before running.

The existing example launcher expects the image name `papi_chameleon_cpu`. Either tag the built image with that name or update the local `run.sh` to use the image you built.

## Run

Place the local matrix example in a directory such as `$HOME/mincer-workloads/matrix-multiplication`, with its `run.sh` at the top level. From the MINCER repository root:

```bash
python3 mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/matrix-multiplication"
```

If the launcher has a different name:

```bash
python3 mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/matrix-multiplication" \
  --script run-matrix.sh
```

The run script should compile both variants in the container and execute them sequentially. The example collects PAPI counters, derived IPC/cache miss rates, and timestamped output under `experiment_logs/`.

## Data and validation

No external dataset is needed. No reference file is currently provided for this example, so the output comparison is skipped. The local source archive and PAPI-enabled `run.sh` are needed to make this exact MINCER example self-contained; this guide alone does not recreate those custom files.

## Status

The workflow is not validated on a new node. Verify compilation, counter permissions, and the output directory before recording results.
