"""
TrimGalore server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestTrimGaloreServer(BaseBioinformaticsToolTest):
    """Test TrimGalore server functionality."""

    @property
    def tool_name(self) -> str:
        return "cutadapt-server"

    @property
    def tool_class(self):
        # Check if cutadapt is available
        import shutil

        if not shutil.which("cutadapt"):
            pytest.skip("cutadapt not available on system")

        # Use CutadaptServer as TrimGalore equivalent
        from DeepResearch.src.tools.bioinformatics.cutadapt_server import CutadaptServer

        return CutadaptServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_files": ["path/to/reads_1.fq"],
            "output_dir": "path/to/output",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads_file = tmp_path / "reads_1.fq"

        # Create mock FASTQ file
        reads_file.write_text(
            "@read1\nATCGATCGATCGATCGATCGATCGATCGATCGATCG\n+\nIIIIIIIIIIIIIII\n"
        )

        return {"input_files": [reads_file]}

    @pytest.mark.optional
    def test_trimgalore_trim(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test TrimGalore trim functionality."""
        params = {
            "operation": "trim",
            "input_files": [str(sample_input_files["input_files"][0])],
            "output_dir": str(sample_output_dir),
            "quality": 20,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return
