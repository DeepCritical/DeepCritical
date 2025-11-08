"""Integration test for simple genomics discovery example."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_network
@pytest.mark.skip(
    reason="Requires manual conda environment setup (see examples/simple_genomics_discovery/README.md)"
)
def test_simple_genomics_discovery_demo():
    """Test the full genomics demo end-to-end.

    Requires:
    - Network access (downloads from S3)
    - AWS CLI installed
    - Conda installed with genomics-demo environment
    - ~5-10 minutes runtime

    This test is skipped in CI because it requires:
    1. Conda/Miniconda installation
    2. Manual environment setup (./install_tools.sh)
    3. Large data downloads (117 MB from S3)
    4. GATK, samtools, FastQC binaries

    To run locally:
    cd examples/simple_genomics_discovery
    ./download_data.sh
    ./install_tools.sh
    conda activate genomics-demo
    pytest tests/test_examples/test_simple_genomics_discovery.py::test_simple_genomics_discovery_demo -v -s
    """
    demo_dir = Path("examples/simple_genomics_discovery")

    # Step 1: Download data
    result = subprocess.run(
        ["bash", "download_data.sh"],
        check=False,
        cwd=demo_dir,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minutes
    )
    assert result.returncode == 0, f"Download failed: {result.stderr}"

    # Verify data downloaded
    assert (demo_dir / "data/human_g1k_v37.20.21.fasta").exists()
    assert (demo_dir / "data/sample.bam").exists()

    # Step 2: Run demo (assumes conda environment already set up in CI)
    result = subprocess.run(
        ["python", "agent_demo.py"],
        check=False,
        cwd=demo_dir,
        capture_output=True,
        text=True,
        timeout=600,  # 10 minutes
    )
    assert result.returncode == 0, f"Demo failed: {result.stderr}"

    # Step 3: Verify output
    vcf_file = demo_dir / "output/variants.vcf"
    assert vcf_file.exists(), "VCF output not created"

    # Check VCF has variants
    with open(vcf_file) as f:
        variant_lines = [line for line in f if not line.startswith("#")]
        assert len(variant_lines) > 0, "No variants found in VCF"
        # NA12878_20k subset contains ~40 variants on chr20
        assert 10 <= len(variant_lines) <= 100, (
            f"Unexpected variant count: {len(variant_lines)}"
        )


@pytest.mark.unit
def test_demo_files_exist():
    """Quick test that demo files exist."""
    demo_dir = Path("examples/simple_genomics_discovery")
    assert (demo_dir / "README.md").exists()
    assert (demo_dir / "download_data.sh").exists()
    assert (demo_dir / "install_tools.sh").exists()
    assert (demo_dir / "agent_demo.py").exists()
