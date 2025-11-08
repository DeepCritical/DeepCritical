"""GATK test fixtures - downloads from public AWS S3.

Industry standard pattern used by BioConda, bcbio-nextgen, and GATK itself.
Test data is downloaded once and cached locally in tests/fixtures/gatk/cache/.

Data source: s3://gatk-test-data/ (public bucket, no authentication required)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

CACHE_DIR = Path(__file__).parent / "cache"


@pytest.fixture(scope="session")
def gatk_test_bam():
    """Download NA12878_20k.b37.bam (8.8 MB) from public S3.

    Downloads once per session and caches in tests/fixtures/gatk/cache/.
    No authentication required (--no-sign-request).

    Returns:
        Path: Path to cached BAM file
    """
    bam_file = CACHE_DIR / "NA12878_20k.b37.bam"

    if not bam_file.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Download from public S3 bucket (no auth required)
        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                "s3://gatk-test-data/wgs_bam/NA12878_20k_b37/NA12878_20k.b37.bam",
                str(bam_file),
                "--no-sign-request",
            ],
            check=True,
            capture_output=True,
        )

    return bam_file


@pytest.fixture(scope="session")
def gatk_test_bam_index():
    """Download NA12878_20k.b37.bam.bai (BAM index) from public S3.

    Returns:
        Path: Path to cached BAM index file
    """
    bai_file = CACHE_DIR / "NA12878_20k.b37.bam.bai"

    if not bai_file.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                "s3://gatk-test-data/wgs_bam/NA12878_20k_b37/NA12878_20k.b37.bam.bai",
                str(bai_file),
                "--no-sign-request",
            ],
            check=True,
            capture_output=True,
        )

    return bai_file


@pytest.fixture(scope="session")
def gatk_test_reference():
    """Download chr20+21 b37 reference subset (108 MB) from public S3.

    Downloads human_g1k_v37.20.21.fasta which contains chromosomes 20 and 21
    from the b37 reference build. Matches the b37 BAM files in our test fixtures.

    Downloads once per session and caches in tests/fixtures/gatk/cache/.
    No authentication required (--no-sign-request).

    Returns:
        tuple[Path, Path, Path]: Paths to (fasta, fai, dict) files
    """
    fasta_file = CACHE_DIR / "human_g1k_v37.20.21.fasta"
    fai_file = CACHE_DIR / "human_g1k_v37.20.21.fasta.fai"
    dict_file = CACHE_DIR / "human_g1k_v37.20.21.dict"

    if not fasta_file.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Download FASTA
        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                "s3://gatk-test-data/mutect2/human_g1k_v37.20.21.fasta",
                str(fasta_file),
                "--no-sign-request",
            ],
            check=True,
            capture_output=True,
        )

        # Download FASTA index
        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                "s3://gatk-test-data/mutect2/human_g1k_v37.20.21.fasta.fai",
                str(fai_file),
                "--no-sign-request",
            ],
            check=True,
            capture_output=True,
        )

        # Download sequence dictionary
        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                "s3://gatk-test-data/mutect2/human_g1k_v37.20.21.dict",
                str(dict_file),
                "--no-sign-request",
            ],
            check=True,
            capture_output=True,
        )

    return fasta_file, fai_file, dict_file
