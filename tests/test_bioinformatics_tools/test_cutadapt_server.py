"""
Cutadapt server component tests.
"""

from unittest.mock import patch

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestCutadaptServer(BaseBioinformaticsToolTest):
    """Test Cutadapt server functionality."""

    @property
    def tool_name(self) -> str:
        return "cutadapt-server"

    @property
    def tool_class(self):
        # Import the actual CutadaptServer server class
        from DeepResearch.src.tools.bioinformatics.cutadapt_server import CutadaptServer

        return CutadaptServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_file": "path/to/reads.fq",
            "output_file": "path/to/trimmed.fq",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads_file = tmp_path / "sample_reads.fq"

        # Create mock FASTQ file
        reads_file.write_text(
            "@read1\n"
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
            "+\n"
            "IIIIIIIIIIIIIII\n"
            "@read2\n"
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n"
            "+\n"
            "IIIIIIIIIIIIIII\n"
        )

        return {"input_files": [reads_file]}

    @pytest.mark.optional
    def test_cutadapt_trim(self, tool_instance, sample_input_files, sample_output_dir):
        """Test Cutadapt trim functionality."""
        # Use run_tool method if available (for class-based servers)
        if hasattr(tool_instance, "run_tool"):
            # For testing, we'll mock the subprocess call
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = type(
                    "MockResult",
                    (),
                    {"stdout": "Trimmed reads: 100", "stderr": "", "returncode": 0},
                )()

                result = tool_instance.run_tool(
                    "cutadapt",
                    input_file=sample_input_files["input_files"][0],
                    output_file=sample_output_dir / "trimmed.fq",
                    quality_cutoff="20",
                    minimum_length="20",
                )

                assert "command_executed" in result
                assert "output_files" in result
                assert len(result["output_files"]) > 0
        else:
            # Fallback for direct MCP function testing
            pytest.skip("Direct MCP function testing not implemented")
