# Base image with CUDA support
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Set up non-interactive frontend for package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies and Miniconda
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -tip && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc

# Set path to conda
ENV PATH /opt/conda/bin:$PATH

# Install OpenMM and related tools using Conda
RUN conda install -c conda-forge --yes \
    openmm \
    pdbfixer \
    mdtraj \
    openmmtools \
    openff-toolkit

# Set the working directory
WORKDIR /app
