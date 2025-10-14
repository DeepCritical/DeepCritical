"""
HISAT2 server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestHISAT2Server(BaseBioinformaticsToolTest):
    """Test HISAT2 server functionality."""

    @property
    def tool_name(self) -> str:
        return "hisat2-server"

    @property
    def tool_class(self):
        # Import the actual Hisat2Server server class
        from DeepResearch.src.tools.bioinformatics.hisat2_server import HISAT2Server

        return HISAT2Server

    @property
    def required_parameters(self) -> dict:
        return {
            "index_base": "path/to/genome/index/genome",
            "reads_1": "path/to/reads_1.fq",
            "reads_2": "path/to/reads_2.fq",
            "output_name": "output.sam",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads1 = tmp_path / "reads_1.fq"
        reads2 = tmp_path / "reads_2.fq"

        # Create mock paired-end reads
        reads1.write_text(
            "@READ_001\nATCGATCGATCG\n+\nIIIIIIIIIIII\n@READ_002\nGCTAGCTAGCTA\n+\nIIIIIIIIIIII\n"
        )
        reads2.write_text(
            "@READ_001\nTAGCTAGCTAGC\n+\nIIIIIIIIIIII\n@READ_002\nATCGATCGATCG\n+\nIIIIIIIIIIII\n"
        )

        return {"reads_1": reads1, "reads_2": reads2}

    @pytest.mark.optional
    def test_hisat2_alignment(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test HISAT2 alignment functionality."""
        params = {
            "operation": "alignment",
            "index_base": "/path/to/genome/index/genome",  # Mock genome index
            "reads_1": str(sample_input_files["reads_1"]),
            "reads_2": str(sample_input_files["reads_2"]),
            "output_name": str(sample_output_dir / "hisat2_output.sam"),
            "threads": 2,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
        # Verify output SAM file was created
        sam_file = sample_output_dir / "hisat2_output.sam"
        assert sam_file.exists()

    @pytest.mark.optional
    def test_hisat2_indexing(self, tool_instance, tmp_path):
        """Test HISAT2 genome indexing functionality."""
        fasta_file = tmp_path / "genome.fa"

        # Create mock genome file
        fasta_file.write_text(">chr1\nATCGATCGATCGATCGATCGATCGATCGATCGATCG\n")

        params = {
            "fasta_file": str(fasta_file),
            "index_base": str(tmp_path / "hisat2_index" / "genome"),
            "threads": 1,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        # Check for HISAT2 index files (they have .ht2 extension)

        # Skip file checks for mock results
        if result.get("mock"):
            return

        index_dir = tmp_path / "hisat2_index"
        assert (index_dir / "genome.1.ht2").exists()
