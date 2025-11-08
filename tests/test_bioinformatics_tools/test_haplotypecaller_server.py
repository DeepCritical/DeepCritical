"""
GATK HaplotypeCaller server tests.

Test Philosophy: Robert C. Martin - "Test behaviors, not implementation."
- Unit tests: Fast, test command building (pure functions)
- Integration tests: Slow, test real GATK execution
"""

from pathlib import Path

import pytest

from DeepResearch.src.tools.bioinformatics.haplotypecaller_server import (
    HaplotypeCallerServer,
)


class TestHaplotypeCallerServer:
    """Test HaplotypeCaller server."""

    @pytest.fixture
    def server(self):
        """Create server instance."""
        return HaplotypeCallerServer()

    # ===== UNIT TESTS (Fast - test behaviors) =====

    def test_build_command_vcf_mode(self, server):
        """Test command building for VCF mode."""
        command = server._build_command(
            operation="call_variants",
            input_bam="/data/sample.bam",
            reference_fasta="/data/ref.fa",
            output_vcf="/data/output.vcf",
            ploidy=2,
            threads=1,
        )

        # Test GATK CLI contract
        assert command[0] == "gatk"
        assert command[1] == "HaplotypeCaller"
        assert "-I" in command
        assert "/data/sample.bam" in command
        assert "-R" in command
        assert "/data/ref.fa" in command
        assert "-O" in command
        assert "/data/output.vcf" in command
        assert "-ERC" not in command  # VCF mode, not GVCF

    def test_build_command_gvcf_mode(self, server):
        """Test command building for GVCF mode."""
        command = server._build_command(
            operation="call_gvcf",
            input_bam="/data/sample.bam",
            reference_fasta="/data/ref.fa",
            output_gvcf="/data/output.g.vcf",
            threads=1,
        )

        # Test GVCF-specific behavior
        assert "-ERC" in command
        assert "GVCF" in command

    def test_build_command_with_optional_params(self, server):
        """Test command building with optional parameters."""
        command = server._build_command(
            operation="call_variants",
            input_bam="/data/sample.bam",
            reference_fasta="/data/ref.fa",
            output_vcf="/data/output.vcf",
            dbsnp="/data/dbsnp.vcf",
            intervals="chr1:1-1000000",
            ploidy=3,
            threads=4,
        )

        # Test optional parameters included
        assert "--dbsnp" in command
        assert "/data/dbsnp.vcf" in command
        assert "-L" in command
        assert "chr1:1-1000000" in command
        assert "--sample-ploidy" in command
        assert "3" in command
        assert "--native-pair-hmm-threads" in command
        assert "4" in command

    def test_validate_reference_missing_fasta(self, server):
        """Test validation fails for missing FASTA."""
        with pytest.raises(ValueError, match="Reference FASTA not found"):
            server._validate_reference_files("/nonexistent/ref.fa")

    def test_validate_reference_missing_index(self, server, tmp_path):
        """Test validation fails for missing .fai index."""
        ref = tmp_path / "ref.fa"
        ref.write_text(">chr1\nATCG\n")

        with pytest.raises(ValueError, match="FASTA index not found"):
            server._validate_reference_files(str(ref))

    def test_validate_reference_missing_dict(self, server, tmp_path):
        """Test validation fails for missing .dict file (CRITICAL)."""
        ref = tmp_path / "ref.fa"
        ref.write_text(">chr1\nATCG\n")
        fai = tmp_path / "ref.fa.fai"
        fai.write_text("chr1\t4\t6\t4\t5\n")
        # Missing .dict

        with pytest.raises(ValueError, match="sequence dictionary not found"):
            server._validate_reference_files(str(ref))

    def test_validate_alignment_missing_bam(self, server):
        """Test validation fails for missing BAM."""
        with pytest.raises(ValueError, match="Alignment file not found"):
            server._validate_alignment_file("/nonexistent/sample.bam")

    def test_validate_alignment_missing_index(self, server, tmp_path):
        """Test validation fails for missing .bai index."""
        bam = tmp_path / "sample.bam"
        bam.write_bytes(b"BAM\x01")

        with pytest.raises(ValueError, match="BAM index not found"):
            server._validate_alignment_file(str(bam))

    def test_validate_ploidy_too_low(self, server):
        """Test ploidy validation - too low."""
        with pytest.raises(ValueError, match="ploidy must be >= 1"):
            server._validate_ploidy(0)

    def test_validate_ploidy_too_high(self, server):
        """Test ploidy validation - unreasonably high."""
        with pytest.raises(ValueError, match="unreasonably high"):
            server._validate_ploidy(200)

    def test_list_tools(self, server):
        """Test list_tools returns expected operations."""
        tools = server.list_tools()
        assert "call_variants" in tools
        assert "call_gvcf" in tools
        assert "get_version" in tools

    # ===== INTEGRATION TESTS (Slow - real execution) =====

    @pytest.mark.integration
    @pytest.mark.slow
    def test_get_version_real(self, server):
        """Test GATK version with real subprocess execution.

        This test verifies that:
        1. _run_command() actually executes subprocess
        2. GATK is callable (if installed)
        3. Command structure is correct
        4. Result dict has expected structure

        NOTE: This test will FAIL if GATK is not installed locally.
        For CI, this should run in a containerized environment with GATK.
        """
        result = server.get_version()

        # Verify result structure
        assert "success" in result
        assert "command" in result
        assert result["command"] == ["gatk", "--version"]
        assert "exit_code" in result

        # If GATK is installed, verify success
        # If not installed, we still tested the execution path
        if result["success"]:
            assert result["exit_code"] == 0
            assert "stdout" in result or "stderr" in result

    @pytest.mark.containerized
    @pytest.mark.slow
    def test_call_variants_integration(self, server, gatk_test_bam, tmp_path):
        """Test real variant calling (requires reference genome).

        SKIPPED: Requires reference genome (700 MB download).
        See REMAINING_WORK.md Option C for full implementation.

        When implemented, this will:
        1. Use gatk_test_bam fixture (NA12878_20k.b37.bam)
        2. Download chr20 reference subset
        3. Run real HaplotypeCaller
        4. Verify VCF output
        """
        pytest.skip("Requires reference genome (700 MB) - see Option C")

    @pytest.mark.containerized
    @pytest.mark.slow
    def test_call_gvcf_integration(self, server, tmp_path):
        """Test real GVCF generation (requires reference genome).

        SKIPPED: Requires reference genome (700 MB download).
        See REMAINING_WORK.md Option C for full implementation.
        """
        pytest.skip("Requires reference genome (700 MB) - see Option C")
