# PyTorch 3D U-Net with KiTS19

This guide covers the NVIDIA CUDA PyTorch 3D U-Net workflow. It is separate from the AMD ROCm/MLPerf UNet3D example, which is intentionally excluded.

## Acquire the application and data

Clone the PyTorch 3D U-Net project outside the MINCER repository:

```bash
mkdir -p "$HOME/mincer-workloads"
git clone https://github.com/wolny/pytorch-3dunet.git \
  "$HOME/mincer-workloads/pytorch-3dunet"
```

This workload uses the KiTS19 kidney tumor CT dataset. Obtain the data from its official project:

```bash
git clone https://github.com/neheller/kits19.git \
  "$HOME/mincer-workloads/kits19"
cd "$HOME/mincer-workloads/kits19"
python3 -m pip install -e .
python3 -m starter_code.get_imaging
```

The downloader retrieves the original challenge images and labels and may require substantial disk space and time. Review the KiTS19 project terms and instructions before downloading or using the data. Do not copy the downloaded `data/` directory into the MINCER repository.

## Prepare the input files

The existing MINCER configuration expects three HDF5 files named `kits19_case_00000.h5`, `kits19_case_00001.h5`, and `kits19_case_00002.h5` in the application's `kits19_data/` directory. Only a small subset of KiTS19 is needed to limit run time, but this workspace does not include a reproducible conversion script for turning the downloaded KiTS19 cases into those HDF5 files.

Before training, prepare those HDF5 inputs in the expected format (`raw` and `label` datasets) using a documented conversion process, and verify the paths in the training configuration. Do not assume that downloading KiTS19 alone creates the expected HDF5 inputs.

## Build and run

Use the CUDA/PAPI container compatible with the node. The local launcher expects the image name `cypapi_cuda_test:latest` and a fixed `/home/cc/` mount, so adjust it for the actual image and checkout.

From the MINCER repository root, after the application, configuration, data, and `run.sh` have been prepared:

```bash
python3 mincer-package/run_experiment.py \
  --path "$HOME/mincer-workloads/pytorch-3dunet"
```

The example launcher in the original workspace runs:

```bash
python3 train_with_monitoring.py --config kits19_data/kits19_config.yml
```

Review the configuration before the run: it selects `cuda:0`, lists the three HDF5 input files, and writes checkpoints under the mounted application directory. Install the required PyTorch, HDF5, and cyPAPI dependencies in the container; do not assume the base Dockerfile alone supplies the complete training environment.

## Verify and status

Capture the training completion status, validation metric, checkpoint/output locations, and any successfully collected PAPI events. Previously recorded training output and counter values are hardware-specific examples, not expected results for a different GPU. This workflow has not been validated from a clean checkout; dataset conversion and the portable launch configuration remain prerequisites.
