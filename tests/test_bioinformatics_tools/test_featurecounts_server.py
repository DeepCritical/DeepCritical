"""
FeatureCounts MCP server component tests.

Tests for the FeatureCounts server with FastMCP integration, Pydantic AI MCP support,
and comprehensive bioinformatics functionality. Includes both containerized and
non-containerized test scenarios.
"""

from unittest.mock import patch

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)
from tests.utils.mocks.mock_data import create_mock_bam, create_mock_gtf

# Import the MCP module to test MCP functionality
try:
    import DeepResearch.src.tools.bioinformatics.featurecounts_server as featurecounts_server_module  # type: ignore

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    featurecounts_server_module = None  # type: ignore

# Check if featureCounts is available on the system
import shutil

FEATURECOUNTS_AVAILABLE = shutil.which("featureCounts") is not None


class TestFeatureCountsServer(BaseBioinformaticsToolTest):
    """Test FeatureCounts server functionality with FastMCP and Pydantic AI integration."""

    @property
    def tool_name(self) -> str:
        return "featurecounts-server"

    @property
    def tool_class(self):
        # Import the actual FeatureCounts server class
        from DeepResearch.src.tools.bioinformatics.featurecounts_server import (
            FeatureCountsServer,
        )

        return FeatureCountsServer

    @property
    def required_parameters(self) -> dict:
        return {
            "annotation_file": "path/to/genes.gtf",
            "input_files": ["path/to/aligned.bam"],
            "output_file": "counts.txt",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample BAM and GTF files for testing."""
        bam_file = tmp_path / "aligned.bam"
        gtf_file = tmp_path / "genes.gtf"

        # Create mock BAM file using utility function
        create_mock_bam(bam_file)

        # Create mock GTF annotation using utility function
        create_mock_gtf(gtf_file)

        return {"bam_file": bam_file, "gtf_file": gtf_file}

    @pytest.mark.optional
    def test_featurecounts_counting(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test featureCounts read counting functionality."""
        params = {
            "operation": "count",
            "annotation_file": str(sample_input_files["gtf_file"]),
            "input_files": [str(sample_input_files["bam_file"])],
            "output_file": str(sample_output_dir / "counts.txt"),
            "feature_type": "gene",
            "attribute_type": "gene_id",
            "threads": 1,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Skip file checks for mock results
        if result.get("mock"):
            assert "mock" in result
            return

        # Verify counts output file was created
        counts_file = sample_output_dir / "counts.txt"
        assert counts_file.exists()

        # Verify counts format (tab-separated with featureCounts header)
        content = counts_file.read_text()
        assert "Geneid" in content  # featureCounts header

    @pytest.mark.optional
    def test_featurecounts_counting_paired_end(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test featureCounts with paired-end reads."""
        params = {
            "operation": "count",
            "annotation_file": str(sample_input_files["gtf_file"]),
            "input_files": [str(sample_input_files["bam_file"])],
            "output_file": str(sample_output_dir / "counts_pe.txt"),
            "feature_type": "exon",
            "attribute_type": "gene_id",
            "threads": 1,
            "is_paired_end": True,
            "require_both_ends_mapped": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify counts output file was created
        counts_file = sample_output_dir / "counts_pe.txt"
        assert counts_file.exists()

    @pytest.mark.optional
    def test_server_info(self, tool_instance):
        """Test server info functionality."""
        info = tool_instance.get_server_info()

        assert isinstance(info, dict)
        assert "name" in info
        assert info["name"] == "featurecounts-server"  # Matches config default
        assert "version" in info
        assert "tools" in info
        assert "status" in info

    @pytest.mark.optional
    def test_mcp_tool_listing(self, tool_instance):
        """Test MCP tool listing functionality."""
        if not MCP_AVAILABLE:
            pytest.skip("MCP module not available")

        tools = tool_instance.list_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check that featurecounts_count tool is available
        assert "featurecounts_count" in tools

    @pytest.mark.optional
    def test_parameter_validation_comprehensive(self, tool_instance, sample_output_dir):
        """Test comprehensive parameter validation."""
        # Test valid parameters
        valid_params = {
            "operation": "count",
            "annotation_file": "/valid/path.gtf",
            "input_files": ["/valid/file.bam"],
            "output_file": str(sample_output_dir / "test.txt"),
        }

        # Should not raise an exception with valid params
        result = tool_instance.run(valid_params)
        assert isinstance(result, dict)

        # Test missing operation
        invalid_params = {
            "annotation_file": "/valid/path.gtf",
            "input_files": ["/valid/file.bam"],
            "output_file": str(sample_output_dir / "test.txt"),
        }

        result = tool_instance.run(invalid_params)
        assert result["success"] is False
        assert "error" in result
        assert "Missing 'operation' parameter" in result["error"]

        # Test unsupported operation
        invalid_params = {
            "operation": "unsupported_op",
            "annotation_file": "/valid/path.gtf",
            "input_files": ["/valid/file.bam"],
            "output_file": str(sample_output_dir / "test.txt"),
        }

        result = tool_instance.run(invalid_params)
        assert result["success"] is False
        assert "error" in result
        assert "Unsupported operation" in result["error"]

    @pytest.mark.optional
    def test_file_validation(self, tool_instance, sample_output_dir):
        """Test file existence validation."""
        # Test file validation by calling the method directly (bypassing mock)
        from unittest.mock import patch

        # Mock shutil.which to return a valid path so we don't get mock results
        with patch("shutil.which", return_value="/usr/bin/featureCounts"):
            # Test with non-existent annotation file
            result = tool_instance.featurecounts_count(
                annotation_file="/nonexistent/annotation.gtf",
                input_files=["/valid/file.bam"],
                output_file=str(sample_output_dir / "test.txt"),
            )

            assert result["success"] is False
            assert "Annotation file not found" in result.get("error", "")

            # Test with non-existent input file (using a valid annotation file)
            # Create a temporary valid annotation file
            valid_gtf = sample_output_dir / "valid.gtf"
            valid_gtf.write_text('chr1\ttest\tgene\t1\t100\t.\t+\t.\tgene_id "TEST";\n')

            result = tool_instance.featurecounts_count(
                annotation_file=str(valid_gtf),
                input_files=["/nonexistent/file.bam"],
                output_file=str(sample_output_dir / "test.txt"),
            )

            assert result["success"] is False
            assert "Input file not found" in result.get("error", "")

    @pytest.mark.optional
    def test_mock_functionality(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test mock functionality when featureCounts is not available."""
        # Mock shutil.which to return None (featureCounts not available)
        with patch("shutil.which", return_value=None):
            params = {
                "operation": "count",
                "annotation_file": str(sample_input_files["gtf_file"]),
                "input_files": [str(sample_input_files["bam_file"])],
                "output_file": str(sample_output_dir / "counts.txt"),
            }

            result = tool_instance.run(params)

            # Should return mock success result
            assert result["success"] is True
            assert result.get("mock") is True
            assert "featurecounts" in result["command_executed"]
            assert "[mock - tool not available]" in result["command_executed"]

    @pytest.mark.optional
    @pytest.mark.containerized
    def test_containerized_execution(
        self, tool_instance, sample_input_files, sample_output_dir, test_config
    ):
        """Test tool execution in containerized environment."""
        if not test_config.get("docker_enabled", False):
            pytest.skip("Docker tests disabled")

        # Test basic container deployment
        import asyncio

        async def test_deployment():
            deployment = await tool_instance.deploy_with_testcontainers()
            assert deployment.server_name == "featurecounts-server"
            assert deployment.status.value == "running"
            assert deployment.container_id is not None

            # Test cleanup
            stopped = await tool_instance.stop_with_testcontainers()
            assert stopped is True

        # Run the async test
        asyncio.run(test_deployment())

    @pytest.mark.optional
    def test_server_info_functionality(self, tool_instance):
        """Test server info functionality comprehensively."""
        info = tool_instance.get_server_info()

        assert info["name"] == "featurecounts-server"  # Matches config default
        assert info["type"] == "featurecounts"
        assert "version" in info
        assert isinstance(info["tools"], list)
        assert len(info["tools"]) > 0

        # Check status
        status = info["status"]
        assert status in ["running", "stopped"]

        # If container is running, check container info
        if status == "running":
            assert "container_id" in info
            assert "container_name" in info

    @pytest.mark.optional
    def test_mcp_integration(self, tool_instance):
        """Test MCP integration functionality."""
        if not MCP_AVAILABLE:
            pytest.skip("MCP module not available")

        # Test that MCP tools are properly registered
        tools = tool_instance.list_tools()
        assert len(tools) > 0
        assert isinstance(tools, list)
        assert all(isinstance(tool, str) for tool in tools)

        # Check that featurecounts_count tool is registered
        assert "featurecounts_count" in tools

        # Test that the tool has the MCP decorator by checking if it has the _mcp_tool_spec attribute
        assert hasattr(tool_instance.featurecounts_count, "_mcp_tool_spec")
        tool_spec = tool_instance.featurecounts_count._mcp_tool_spec

        # Verify MCP tool spec structure
        assert isinstance(tool_spec, dict) or hasattr(tool_spec, "name")
        if hasattr(tool_spec, "name"):
            assert tool_spec.name == "featurecounts_count"
            assert "annotation_file" in tool_spec.inputs
            assert "input_files" in tool_spec.inputs
            assert "output_file" in tool_spec.inputs
