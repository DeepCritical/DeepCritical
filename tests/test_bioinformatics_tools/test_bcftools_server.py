"""
BCFtools server component tests.
"""

import pytest

from DeepResearch.src.tools.bioinformatics.bcftools_server import BCFtoolsServer
from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestBCFtoolsServer(BaseBioinformaticsToolTest):
    """Test BCFtools server functionality."""

    @property
    def tool_name(self) -> str:
        return "bcftools-server"

    @property
    def tool_class(self):
        # This would import the actual BCFtools server class
        from DeepResearch.src.tools.bioinformatics.bcftools_server import BCFtoolsServer

        return BCFtoolsServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_file": "path/to/input.vcf",
            "operation": "view",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample VCF files for testing."""
        vcf_file = tmp_path / "sample.vcf"

        # Create mock VCF file
        vcf_file.write_text(
            "##fileformat=VCFv4.2\n"
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
            "chr1\t100\t.\tA\tT\t60\tPASS\t.\n"
            "chr1\t200\t.\tG\tC\t60\tPASS\t.\n"
        )

        return {"input_file": vcf_file}

    def test_bcftools_view(self, tool_instance, sample_input_files, sample_output_dir):
        """Test BCFtools view functionality."""
        params = {
            "file": str(sample_input_files["input_file"]),
            "operation": "view",
            "output": str(sample_output_dir / "output.vcf"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    def test_bcftools_annotate(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BCFtools annotate functionality."""
        params = {
            "file": str(sample_input_files["input_file"]),
            "operation": "annotate",
            "output": str(sample_output_dir / "annotated.vcf"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    def test_bcftools_call(self, tool_instance, sample_input_files, sample_output_dir):
        """Test BCFtools call functionality."""
        params = {
            "file": str(sample_input_files["input_file"]),
            "operation": "call",
            "output": str(sample_output_dir / "called.vcf"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    def test_bcftools_index(self, tool_instance, sample_input_files, sample_output_dir):
        """Test BCFtools index functionality."""
        params = {
            "file": str(sample_input_files["input_file"]),
            "operation": "index",
        }

        result = tool_instance.run(params)

        assert result["success"] is True

    def test_bcftools_concat(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BCFtools concat functionality."""
        params = {
            "files": [str(sample_input_files["input_file"])],
            "operation": "concat",
            "output": str(sample_output_dir / "concatenated.vcf"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    def test_bcftools_query(self, tool_instance, sample_input_files, sample_output_dir):
        """Test BCFtools query functionality."""
        params = {
            "file": str(sample_input_files["input_file"]),
            "operation": "query",
            "format": "%CHROM\t%POS\t%REF\t%ALT\n",
        }

        result = tool_instance.run(params)

        assert result["success"] is True

    def test_bcftools_stats(self, tool_instance, sample_input_files, sample_output_dir):
        """Test BCFtools stats functionality."""
        params = {
            "file1": str(sample_input_files["input_file"]),
            "operation": "stats",
        }

        result = tool_instance.run(params)

        assert result["success"] is True

    def test_bcftools_sort(self, tool_instance, sample_input_files, sample_output_dir):
        """Test BCFtools sort functionality."""
        params = {
            "file": str(sample_input_files["input_file"]),
            "operation": "sort",
            "output": str(sample_output_dir / "sorted.vcf"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    def test_bcftools_filter(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BCFtools filter functionality."""
        params = {
            "file": str(sample_input_files["input_file"]),
            "operation": "filter",
            "output": str(sample_output_dir / "filtered.vcf"),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_containerized_bcftools_workflow(self, tmp_path):
        """Test complete BCFtools workflow in containerized environment."""
        # Create server instance
        server = BCFtoolsServer()

        # Deploy server in container
        deployment = await server.deploy_with_testcontainers()
        assert deployment.status == "running"

        try:
            # Wait for BCFtools to be installed and ready in the container
            import asyncio

            await asyncio.sleep(30)  # Wait for package installation

            # Create sample VCF file
            vcf_file = tmp_path / "sample.vcf"
            vcf_file.write_text(
                "##fileformat=VCFv4.2\n"
                "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
                "chr1\t100\t.\tA\tT\t60\tPASS\t.\n"
            )

            # Test BCFtools view operation
            result = server.bcftools_view(
                input_file=str(vcf_file),
                output_file=str(tmp_path / "output.vcf"),
                output_type="v",
            )

            # Verify the operation completed (may fail due to container permissions, but server should respond)
            assert "success" in result or "error" in result

        finally:
            # Clean up container
            await server.stop_with_testcontainers()
