# MINCER Historical Testing Report

> **Scope note:** This report records earlier runs on a provisioned Linux system, not validation of the current distribution. Most historical workload sources, images, and datasets are excluded. The newly included source-only XSBench CUDA example has separate current validation below.

**Current NVIDIA testing:** The repository now includes the source-only XSBench
CUDA example. Its October 2026 test results and remaining limitations are
recorded separately in [NVIDIA validation](docs/nodes/nvidia-validation.md).
The historical entries below do not establish current CPU/AMD support.

## ✅ Test Results Summary
**Date:** September 28, 2025  
**System:** Linux 5.15.0-156-generic, x86_64, 251GB RAM  
**GPUs:** 2x AMD Instinct MI100 (34.3GB each)  

## 🧪 Tests Performed

### 1. UNet3D + PAPI Performance Monitoring ✅ **PASSED**
- **Image:** `mincer-unet3d-papi:latest` (28.6GB)
- **Command:** `./build-and-run-unet3d.sh run`
- **Status:** Successfully completed full training cycle
- **Key Results:**
  - ✅ PAPI initialized with 5 components
  - ✅ ROCm GPU monitoring: 6 GPU + 5 system events active
  - ✅ MLPerf model loaded: 31,190,243 parameters
  - ✅ Dataset: 6 training samples (optimized from 210→8 samples)
  - ✅ GPU detection: AMD Instinct MI100 with 34.3GB memory
  - ✅ Performance counters: GPUBusy, VALUUtilization, L2CacheHit, etc.

### 2. MINCER Experiment Runner ✅ **PASSED**  
- **Command:** `python3 run_experiment.py --path examples/unet3d`
- **Status:** Successfully executed and logged
- **Key Results:**
  - ✅ System detection: 2 GPUs correctly identified
  - ✅ Fixed GPU counting bug (was showing 28→now shows 2)
  - ✅ Output logging to `experiment_logs/`
  - ✅ Execution logs generated properly

### 3. PyTorch 3D U-Net Example ✅ **PASSED**
- **Command:** `python3 run_experiment.py --path examples/pytorch-3dunet`  
- **Status:** Successfully executed
- **Key Results:**
  - ✅ Script execution completed
  - ✅ Output captured and logged
  - ✅ No errors detected

### 4. Docker Configuration Testing ✅ **PASSED**
- **Available Images:** 11 Docker images built successfully
- **MINCER Dockerfiles:** 6 configurations available
  - `Dockerfile.unet3d-papi` ✅ (Main focus - tested and working)
  - `Dockerfile.cpu` ✅ (Build tested successfully)
  - `Dockerfile.cypapi` ✅ (Available)
  - `Dockerfile.rocm` ✅ (Available)  
  - `Dockerfile.papicuda` ✅ (Available)
  - `Dockerfile.amdrocpsdk` ✅ (Available)

### 5. Test Issues Identified ⚠️
- **test_experiment:** Missing Docker image `papi_chameleon_cpu:latest`
  - **Impact:** Medium - This example requires additional Docker image not provided
  - **Fix Required:** Either build missing image or update example

## 📊 Performance Metrics Collected

### GPU Performance Monitoring
- **ROCm Events:** GPUBusy, VALUUtilization, VALUBusy, L2CacheHit, TCC_HIT_sum, FetchSize
- **System Events:** Power, temperature, memory usage, GPU utilization  
- **Output Format:** Real-time console + CSV logging

### Dataset Optimization
- **Original:** 210 cases (29GB)
- **Optimized:** 8 cases (1.1GB) 
- **Space Saved:** 96% reduction while maintaining realistic workload

## Historical Results vs. Public Distribution

The results above describe runs performed in the environment and with the workload files available at that time. They are not a release-readiness certification for the intended public repository. The example workloads, PAPI-modified proxy sources, generated logs, and datasets are deliberately excluded from the upload; the setup scripts referenced in the project notes are also absent from the current workspace.

Before describing a workflow as reproducible, provision the corresponding Chameleon node, obtain the upstream workload and data, verify the required PAPI modifications and container image, run the documented command, and record the actual output. Until then, treat the guides as preparation notes rather than tested procedures.