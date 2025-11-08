#!/usr/bin/env bash
set -euo pipefail

echo "🔧 Installing bioinformatics tools"
echo "===================================="
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "❌ conda not found"
    echo ""
    echo "Please install Miniconda first:"
    echo "  macOS:   brew install miniconda"
    echo "  Linux:   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && bash Miniconda3-latest-Linux-x86_64.sh"
    echo "  Windows: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create conda environment (skip if already exists)
echo "📦 Setting up conda environment 'genomics-demo'..."
if conda env list | grep -q "^genomics-demo "; then
    echo "   Environment already exists, skipping creation..."
else
    conda create -n genomics-demo -y python=3.11
fi

# Activate environment
echo "🔄 Activating environment..."
eval "$(conda shell.bash hook)"
conda activate genomics-demo

# Install bioinformatics tools from bioconda
echo "📥 Installing tools from bioconda channel..."
conda install -c conda-forge -c bioconda -y \
    gatk4=4.6.1.0 \
    samtools=1.22 \
    fastqc=0.11.9

echo ""
echo "✅ Installation complete!"
echo ""
echo "Installed tools:"
gatk --version 2>&1 | head -1
samtools --version | head -1
fastqc --version

echo ""
echo "To use these tools, activate the environment:"
echo "  conda activate genomics-demo"
