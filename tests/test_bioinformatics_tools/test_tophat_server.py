"""
TopHat server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestTopHatServer(BaseBioinformaticsToolTest):
    """Test TopHat server functionality."""

    @property
    def tool_name(self) -> str:
        return "hisat2-server"

    @property
    def tool_class(self):
        # Use HISAT2Server as TopHat equivalent
        from DeepResearch.src.tools.bioinformatics.hisat2_server import HISAT2Server

        return HISAT2Server

    @property
    def required_parameters(self) -> dict:
        return {
            "index": "path/to/index",
            "mate1": "path/to/reads_1.fq",
            "output_dir": "path/to/output",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads_file = tmp_path / "reads_1.fq"

        # Create mock FASTQ file
        reads_file.write_text("@read1\nATCGATCGATCG\n+\nIIIIIIIIIIII\n")

        return {"mate1": reads_file}

    @pytest.mark.optional
    def test_tophat_align(self, tool_instance, sample_input_files, sample_output_dir):
        """Test TopHat align functionality using HISAT2."""
        params = {
            "operation": "align",
            "index": "test_index",
            "fastq_files": [str(sample_input_files["mate1"])],
            "output_file": str(sample_output_dir / "aligned.sam"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
