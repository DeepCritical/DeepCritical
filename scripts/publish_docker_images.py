#!/usr/bin/env python3
"""
Script to build and publish bioinformatics Docker images to Docker Hub.
"""

import argparse
import asyncio
import os
import subprocess

# Docker Hub configuration - uses environment variables with defaults
DOCKER_HUB_USERNAME = os.getenv(
    "DOCKER_HUB_USERNAME", "tonic01"
)  # Replace with your Docker Hub username
DOCKER_HUB_REPO = os.getenv("DOCKER_HUB_REPO", "deepcritical-bioinformatics")
TAG = os.getenv("DOCKER_TAG", "latest")

# List of bioinformatics tools to build
BIOINFORMATICS_TOOLS = [
    "bcftools",
    "bedtools",
    "bowtie2",
    "busco",
    "bwa",
    "cutadapt",
    "deeptools",
    "fastp",
    "fastqc",
    "featurecounts",
    "flye",
    "freebayes",
    "hisat2",
    "homer",
    "htseq",
    "kallisto",
    "macs3",
    "meme",
    "minimap2",
    "multiqc",
    "picard",
    "qualimap",
    "salmon",
    "samtools",
    "seqtk",
    "star",
    "stringtie",
    "tophat",
    "trimgalore",
]


def check_image_exists(tool_name: str) -> bool:
    """Check if a Docker Hub image exists."""
    image_name = f"{DOCKER_HUB_USERNAME}/{DOCKER_HUB_REPO}-{tool_name}:{TAG}"
    try:
        # Try to pull the image manifest to check if it exists
        result = subprocess.run(
            ["docker", "manifest", "inspect", image_name],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


async def build_and_publish_image(tool_name: str):
    """Build and publish a single Docker image."""

    dockerfile_path = f"docker/bioinformatics/Dockerfile.{tool_name}"
    image_name = f"{DOCKER_HUB_USERNAME}/{DOCKER_HUB_REPO}-{tool_name}:{TAG}"

    try:
        # Build the image
        build_cmd = ["docker", "build", "-f", dockerfile_path, "-t", image_name, "."]

        subprocess.run(build_cmd, check=True, capture_output=True, text=True)

        # Tag as latest
        tag_cmd = [
            "docker",
            "tag",
            image_name,
            f"{DOCKER_HUB_USERNAME}/{DOCKER_HUB_REPO}-{tool_name}:latest",
        ]
        subprocess.run(tag_cmd, check=True)

        # Push to Docker Hub
        push_cmd = ["docker", "push", image_name]
        subprocess.run(push_cmd, check=True)

        # Push latest tag
        latest_image = f"{DOCKER_HUB_USERNAME}/{DOCKER_HUB_REPO}-{tool_name}:latest"
        push_latest_cmd = ["docker", "push", latest_image]
        subprocess.run(push_latest_cmd, check=True)

        return True

    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False


async def check_images_only():
    """Check which Docker Hub images exist without building."""

    available_images = []
    missing_images = []

    for tool in BIOINFORMATICS_TOOLS:
        if check_image_exists(tool):
            available_images.append(tool)
        else:
            missing_images.append(tool)

    if missing_images:
        for tool in missing_images:
            pass


async def main():
    """Main function to build and publish all images."""
    parser = argparse.ArgumentParser(
        description="Build and publish bioinformatics Docker images"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check which images exist on Docker Hub",
    )
    args = parser.parse_args()

    if args.check_only:
        await check_images_only()
        return

    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return

    # Check if Docker daemon is running
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return

    successful_builds = 0
    failed_builds = 0

    # Build and publish each image
    for tool in BIOINFORMATICS_TOOLS:
        success = await build_and_publish_image(tool)
        if success:
            successful_builds += 1
        else:
            failed_builds += 1

    if failed_builds > 0:
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
