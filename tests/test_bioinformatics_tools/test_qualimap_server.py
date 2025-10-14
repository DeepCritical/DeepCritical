"""
Qualimap server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestQualimapServer(BaseBioinformaticsToolTest):
    """Test Qualimap server functionality."""

    @property
    def tool_name(self) -> str:
        return "qualimap-server"

    @property
    def tool_class(self):
        # Use QualimapServer
        from DeepResearch.src.tools.bioinformatics.qualimap_server import QualimapServer

        return QualimapServer

    @property
    def required_parameters(self) -> dict:
        return {
            "bam_file": "path/to/sample.bam",
            "output_dir": "path/to/output",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample BAM files for testing."""
        bam_file = tmp_path / "sample.bam"

        # Create mock BAM file
        bam_file.write_text("BAM file content")

        return {"bam_file": bam_file}

    @pytest.mark.optional
    def test_qualimap_bamqc(self, tool_instance, sample_input_files, sample_output_dir):
        """Test Qualimap bamqc functionality."""
        params = {
            "operation": "bamqc",
            "bam_file": str(sample_input_files["bam_file"]),
            "output_dir": str(sample_output_dir),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
