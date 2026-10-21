#!/usr/bin/env python3

import os
import json
import platform
import argparse
import psutil


import subprocess

def detect_metrics():
    detected = []

    def is_tool_available(cmd):
        return subprocess.call(
            f"type {cmd}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) == 0

    if is_tool_available("papi_avail"):
        detected.append("PAPI")

    if is_tool_available("nvidia-smi"):
        try:
            out = subprocess.check_output("nvidia-smi --query-gpu=name --format=csv,noheader", shell=True)
            gpu_names = out.decode().strip().split("\n")
            detected.extend([f"GPU::{gpu}" for gpu in gpu_names])
        except Exception:
            detected.append("GPU::Unknown")

    if is_tool_available("perf"):
        detected.append("perf")

    return detected


def detect_gpus():
    """Detect NVIDIA CUDA and AMD GPUs"""
    gpus = []
    
    # Detect NVIDIA GPUs
    def detect_nvidia_gpus():
        nvidia_gpus = []
        if subprocess.call("type nvidia-smi", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            try:
                # Get GPU names and memory info
                result = subprocess.check_output(
                    "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits", 
                    shell=True, text=True
                )
                for line in result.strip().split('\n'):
                    if line.strip():
                        parts = line.split(', ')
                        if len(parts) >= 3:
                            name = parts[0].strip()
                            memory_mb = parts[1].strip()
                            driver = parts[2].strip()
                            nvidia_gpus.append({
                                'type': 'NVIDIA CUDA',
                                'name': name,
                                'memory_mb': memory_mb,
                                'driver': driver
                            })
            except Exception as e:
                print(f"Warning: Could not get NVIDIA GPU details: {e}")
        return nvidia_gpus
    
    # Detect AMD GPUs
    def detect_amd_gpus():
        amd_gpus = []
        # Try rocm-smi for AMD GPUs
        if subprocess.call("type rocm-smi", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            try:
                result = subprocess.check_output("rocm-smi --showid --showproductname", shell=True, text=True)
                lines = result.strip().split('\n')
                
                # Parse GPU information by grouping properties for each GPU[x]
                gpu_info = {}
                for line in lines:
                    if line.strip() and not line.startswith('=') and ':' in line:
                        # Extract GPU index and property
                        if 'GPU[' in line:
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                gpu_id = parts[0].strip()  # e.g., "GPU[0]"
                                property_name = parts[1].strip()  # e.g., "Device Name"
                                property_value = parts[2].strip()  # e.g., "AMD Instinct MI100"
                                
                                if gpu_id not in gpu_info:
                                    gpu_info[gpu_id] = {}
                                gpu_info[gpu_id][property_name] = property_value
                
                # Create GPU entries from collected information
                for gpu_id, properties in gpu_info.items():
                    device_name = properties.get('Device Name', 'Unknown AMD GPU')
                    card_series = properties.get('Card Series', device_name)
                    
                    amd_gpus.append({
                        'type': 'AMD ROCm',
                        'name': f"{gpu_id}: {device_name}",
                        'memory_mb': 'Unknown',  # Could be enhanced with --showmeminfo
                        'driver': 'ROCm'
                    })
                        
            except Exception as e:
                print(f"Warning: Could not get AMD GPU details: {e}")
        
        # Fallback: check lspci for AMD GPUs if rocm-smi not available
        if not amd_gpus:
            try:
                result = subprocess.check_output("lspci | grep -i 'vga.*amd\\|vga.*radeon\\|3d.*amd\\|3d.*radeon'", shell=True, text=True)
                for line in result.strip().split('\n'):
                    if line.strip():
                        # Extract GPU name from lspci output
                        parts = line.split(':')
                        if len(parts) >= 3:
                            gpu_info = parts[2].strip()
                            amd_gpus.append({
                                'type': 'AMD GPU',
                                'name': gpu_info,
                                'memory_mb': 'Unknown',
                                'driver': 'Unknown'
                            })
            except Exception:
                pass
                
        return amd_gpus
    
    # Combine both GPU types
    gpus.extend(detect_nvidia_gpus())
    gpus.extend(detect_amd_gpus())
    
    return gpus

def get_system_info():
    gpus = detect_gpus()
    
    system_info = {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or platform.machine(),
        "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2)
    }
    
    if gpus:
        system_info["gpus"] = gpus
    else:
        system_info["gpus"] = "No GPUs detected"
        
    return system_info

def find_scripts(directory):
    script_list = []
    for filename in os.listdir(directory):
        if filename.endswith(('.sh', '.py', '.ipynb', '.yml', '.txt')):
            script_list.append(filename)
    return script_list

def generate_manifest(path, output_file):
    system_info = get_system_info()
    scripts_found = find_scripts(path)

    manifest = {
        "experiment_name": os.path.basename(os.path.abspath(path)),
        "hardware": {
            "cpu": system_info["cpu"],
            "ram_gb": system_info["ram_gb"]
        },
        "os": system_info["os"],
        "metrics": detect_metrics(),
        "scripts": scripts_found,
        "reproducibility_notes": "Auto-generated manifest. Please edit to add measurement tools and details."
    }

    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest written to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate reproducibility manifest for a MINCER experiment.")
    parser.add_argument("--path", type=str, required=True, help="Path to the experiment folder")
    parser.add_argument("--output", type=str, default="manifest.json", help="Output manifest file name")
    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print("Error: Provided path is not a directory.")
        return

    generate_manifest(args.path, args.output)

if __name__ == "__main__":
    main()
