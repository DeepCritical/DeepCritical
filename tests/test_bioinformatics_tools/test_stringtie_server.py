"""
StringTie server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestStringTieServer(BaseBioinformaticsToolTest):
    """Test StringTie server functionality."""

    @property
    def tool_name(self) -> str:
        return "stringtie-server"

    @property
    def tool_class(self):
        # Use StringTieServer
        from DeepResearch.src.tools.bioinformatics.stringtie_server import (
            StringTieServer,
        )

        return StringTieServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_bam": "path/to/aligned.bam",
            "output_gtf": "path/to/transcripts.gtf",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample BAM files for testing."""
        bam_file = tmp_path / "aligned.bam"

        # Create mock BAM file
        bam_file.write_text("BAM file content")

        return {"input_bam": bam_file}

    @pytest.mark.optional
    def test_stringtie_assemble(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test StringTie assemble functionality."""
        params = {
            "operation": "assemble",
            "input_bam": str(sample_input_files["input_bam"]),
            "output_gtf": str(sample_output_dir / "transcripts.gtf"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
