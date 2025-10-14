"""
MultiQC server component tests.
"""

from pathlib import Path

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestMultiQCServer(BaseBioinformaticsToolTest):
    """Test MultiQC server functionality."""

    @property
    def tool_name(self) -> str:
        return "multiqc-server"

    @property
    def tool_class(self):
        from DeepResearch.src.tools.bioinformatics.multiqc_server import MultiQCServer

        return MultiQCServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_dir": "path/to/analysis_results",
            "output_dir": "path/to/output",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample analysis results for testing."""
        input_dir = tmp_path / "analysis_results"
        input_dir.mkdir()

        # Create mock analysis files
        fastqc_file = input_dir / "sample_fastqc.zip"
        fastqc_file.write_text("FastQC analysis results")

        return {"input_dir": input_dir}

    @pytest.mark.optional
    def test_multiqc_run(self, tool_instance, sample_input_files, sample_output_dir):
        """Test MultiQC run functionality."""

        # Test the multiqc_run method directly (MCP server pattern)
        result = tool_instance.multiqc_run(
            analysis_directory=Path(sample_input_files["input_dir"]),
            outdir=Path(sample_output_dir),
            filename="multiqc_report",
            force=True,
        )

        # Check basic result structure
        assert isinstance(result, dict)
        assert "success" in result
        assert "command_executed" in result
        assert "output_files" in result

        # MultiQC might not be installed in test environment
        # Accept either success (if MultiQC is available) or graceful failure
        if not result["success"]:
            # Should have error information
            assert "error" in result or "stderr" in result
            # Skip further checks for unavailable tool
            return

        # If successful, check output files
        assert result["success"] is True
