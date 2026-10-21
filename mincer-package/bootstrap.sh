#!/bin/bash

set -e

echo "Starting MINCER bootstrap setup..."

# Install perf if missing
if ! command -v perf &> /dev/null; then
    echo "Installing perf..."
    sudo apt-get update
    sudo apt-get install -y linux-tools-common linux-tools-generic linux-tools-$(uname -r)
else
    echo "perf already installed."
fi

# Remove existing PAPI and install v7.0.0
PAPI_DIR="/opt/papi"
echo "Installing/upgrading PAPI to version 7.0.0 at $PAPI_DIR..."
sudo rm -rf "$PAPI_DIR"  # Force remove old version
mkdir -p /tmp/papi_install && cd /tmp/papi_install
wget http://icl.utk.edu/projects/papi/downloads/papi-7.0.0.tar.gz
tar -xzf papi-7.0.0.tar.gz
cd papi-7.0.0/src
./configure --prefix="$PAPI_DIR"
make -j$(nproc)          # Speed up compilation
sudo make install

# Update environment variables
export PATH="$PAPI_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$PAPI_DIR/lib:$LD_LIBRARY_PATH"
export CPATH="$PAPI_DIR/include:$CPATH"

# Verify installation
echo "PAPI version installed: $(papi_version)"
echo "Bootstrap complete. You can now use perf and PAPI tools."