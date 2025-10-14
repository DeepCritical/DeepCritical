"""
FastQC server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestFastQCServer(BaseBioinformaticsToolTest):
    """Test FastQC server functionality."""

    @property
    def tool_name(self) -> str:
        return "fastqc-server"

    @property
    def tool_class(self):
        # Import the actual FastQCServer server class
        from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer

        return FastQCServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_files": ["path/to/reads.fq"],
            "output_dir": "path/to/output",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads_file = tmp_path / "sample_reads.fq"

        # Create mock FASTQ file
        reads_file.write_text(
            "@read1\nATCGATCGATCGATCGATCGATCGATCGATCGATCG\n+\nIIIIIIIIIIIIIII\n"
        )

        return {"input_files": [reads_file]}

    @pytest.mark.optional
    def test_run_fastqc(self, tool_instance, sample_input_files, sample_output_dir):
        """Test FastQC run functionality."""
        params = {
            "operation": "fastqc",
            "input_files": [str(sample_input_files["input_files"][0])],
            "output_dir": str(sample_output_dir),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
