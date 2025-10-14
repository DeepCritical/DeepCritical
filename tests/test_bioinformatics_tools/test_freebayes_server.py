"""
FreeBayes server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)
from tests.utils.mocks.mock_data import create_mock_bam, create_mock_fasta


class TestFreeBayesServer(BaseBioinformaticsToolTest):
    """Test FreeBayes server functionality."""

    @property
    def tool_name(self) -> str:
        return "freebayes-server"

    @property
    def tool_class(self):
        # Import the actual FreebayesServer server class
        from DeepResearch.src.tools.bioinformatics.freebayes_server import (
            FreeBayesServer,
        )

        return FreeBayesServer

    @property
    def required_parameters(self) -> dict:
        return {
            "fasta_reference": "path/to/reference.fa",
            "bam_files": ["path/to/aligned.bam"],
            "vcf_output": "variants.vcf",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample BAM and reference files for testing."""
        bam_file = tmp_path / "aligned.bam"
        ref_file = tmp_path / "reference.fa"

        # Create mock BAM file using utility function
        create_mock_bam(bam_file)

        # Create mock reference FASTA using utility function
        create_mock_fasta(ref_file)

        return {"bam_file": bam_file, "reference": ref_file}

    @pytest.mark.optional
    def test_freebayes_variant_calling(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test FreeBayes variant calling functionality."""
        import shutil

        # Skip test if freebayes is not available and not using mock
        if not shutil.which("freebayes"):
            # Test mock functionality when tool is not available
            params = {
                "operation": "variant_calling",
                "fasta_reference": str(sample_input_files["reference"]),
                "bam_files": [str(sample_input_files["bam_file"])],
                "vcf_output": str(sample_output_dir / "variants.vcf"),
                "region": "chr1:1-20",
            }

            result = tool_instance.run(params)

            assert "command_executed" in result
            assert "mock" in result
            assert result["mock"] is True
            assert (
                "freebayes variant_calling [mock - tool not available]"
                in result["command_executed"]
            )
            assert "output_files" in result
            assert len(result["output_files"]) == 1
            return

        # Test with actual tool when available
        vcf_output = sample_output_dir / "variants.vcf"

        result = tool_instance.freebayes_variant_calling(
            fasta_reference=sample_input_files["reference"],
            bam_files=[sample_input_files["bam_file"]],
            vcf_output=vcf_output,
            region="chr1:1-20",
        )

        assert "command_executed" in result
        assert "output_files" in result

        # Verify VCF output file was created
        assert vcf_output.exists()

        # Verify VCF format
        content = vcf_output.read_text()
        assert "#CHROM" in content  # VCF header
