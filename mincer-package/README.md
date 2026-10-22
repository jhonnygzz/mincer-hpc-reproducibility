# MINCER utilities

The Python utilities in this directory collect basic environment information and run a workload script while saving its output. They do not install benchmark source, build Docker images, download data, or automatically instrument a program with PAPI.

## Requirements

- Python 3
- `psutil` (`python3 -m pip install psutil`)
- Linux for running experiments: the experiment runner invokes scripts with `/bin/bash`

## Generate an environment manifest

From the repository root:

```bash
python3 mincer-package/mincer_package.py \
  --path /path/to/workload \
  --output manifest.json
```

The JSON file records detected OS, CPU, memory, GPU information, available monitoring tools, and selected files in the workload directory. GPU/PAPI detection depends on the relevant utilities and drivers being available on the host.

## Run and log an experiment

The workload directory must contain a `run.sh` by default:

```bash
python3 mincer-package/run_experiment.py --path /path/to/workload
```

Choose another script with `--script`:

```bash
python3 mincer-package/run_experiment.py \
  --path /path/to/workload \
  --script run-benchmark.sh
```

The runner stores captured standard output and standard error and a system-information log in a timestamped `experiment_logs/run_<timestamp>/` directory beneath the workload directory. Output is captured, not streamed live. It has a 10-minute script timeout. Failed runs save diagnostics and return a nonzero exit status, as do reference mismatches. It does not compare results unless `--reference` is supplied.

For end-to-end requirements and external benchmark/data acquisition, see the [benchmark guides](../docs/benchmarks/README.md).

## Check output against a reference

`self_test.py` executes a workload script and can compare the captured output with a supplied reference file:

```bash
python3 mincer-package/self_test.py \
  --path /path/to/workload \
  --script run.sh \
  --reference /path/to/reference.txt
```

Use `--output` to change the generated output filename. A textual comparison is only appropriate when output is deterministic; timings and other hardware-dependent performance values will commonly differ across nodes.
