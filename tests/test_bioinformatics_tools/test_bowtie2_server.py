"""
Bowtie2 server component tests.

Tests for the improved Bowtie2 server with FastMCP integration, Pydantic AI MCP support,
and comprehensive bioinformatics functionality. Includes both containerized and
non-containerized test scenarios.
"""

from unittest.mock import patch

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)
from tests.utils.mocks.mock_data import create_mock_fasta, create_mock_fastq
from tests.utils.testcontainers.docker_helpers import create_isolated_container

# Import the MCP module to test MCP functionality
try:
    import DeepResearch.src.tools.bioinformatics.bowtie2_server as bowtie2_server_module

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    bowtie2_server_module = None  # type: ignore[assignment]

# Check if bowtie2 is available on the system
import shutil

BOWTIE2_AVAILABLE = shutil.which("bowtie2") is not None


class TestBowtie2Server(BaseBioinformaticsToolTest):
    """Test Bowtie2 server functionality with FastMCP and Pydantic AI integration."""

    @property
    def tool_name(self) -> str:
        return "bowtie2-server"

    @property
    def tool_class(self):
        if not BOWTIE2_AVAILABLE:
            pytest.skip("Bowtie2 not available on system")
        # Import the actual Bowtie2 server class
        from DeepResearch.src.tools.bioinformatics.bowtie2_server import Bowtie2Server

        return Bowtie2Server

    @property
    def required_parameters(self) -> dict:
        """Required parameters for backward compatibility testing."""
        return {
            "index_base": "path/to/index",  # Updated parameter name
            "unpaired_files": ["path/to/reads.fq"],  # Updated parameter name
            "sam_output": "path/to/output.sam",  # Updated parameter name
            "operation": "align",  # For legacy run() method
        }

    @pytest.fixture
    def test_config(self):
        """Test configuration fixture."""
        import os

        return {
            "docker_enabled": os.getenv("DOCKER_TESTS", "false").lower() == "true",
            "mcp_enabled": MCP_AVAILABLE,
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ and FASTA files for testing."""
        # Create reference genome FASTA
        reference_file = tmp_path / "reference.fa"
        create_mock_fasta(reference_file, num_sequences=5)

        # Create unpaired reads FASTQ
        unpaired_reads = tmp_path / "unpaired_reads.fq"
        create_mock_fastq(unpaired_reads, num_reads=100)

        # Create paired-end reads
        mate1_reads = tmp_path / "mate1_reads.fq"
        mate2_reads = tmp_path / "mate2_reads.fq"
        create_mock_fastq(mate1_reads, num_reads=100)
        create_mock_fastq(mate2_reads, num_reads=100)

        return {
            "reference_file": reference_file,
            "unpaired_reads": unpaired_reads,
            "mate1_reads": mate1_reads,
            "mate2_reads": mate2_reads,
        }

    @pytest.mark.optional
    def test_bowtie2_align_legacy(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Bowtie2 align functionality using legacy run() method."""
        # First build an index
        build_params = {
            "operation": "build",
            "reference_in": [str(sample_input_files["reference_file"])],
            "index_base": str(sample_output_dir / "test_index"),
            "threads": 1,
        }

        build_result = tool_instance.run(build_params)
        assert build_result["success"] is True

        # Now align using unpaired reads
        align_params = {
            "operation": "align",
            "index_base": str(sample_output_dir / "test_index"),
            "unpaired_files": [str(sample_input_files["unpaired_reads"])],
            "sam_output": str(sample_output_dir / "aligned.sam"),
            "threads": 1,
        }

        result = tool_instance.run(align_params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify output file was created
        output_file = sample_output_dir / "aligned.sam"
        assert output_file.exists()

    @pytest.mark.optional
    @pytest.mark.skipif(not BOWTIE2_AVAILABLE, reason="Bowtie2 not available on system")
    def test_bowtie2_align_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Bowtie2 align functionality using direct method call."""
        # Build index first
        index_result = tool_instance.bowtie2_build(
            reference_in=[str(sample_input_files["reference_file"])],
            index_base=str(sample_output_dir / "direct_test_index"),
            threads=1,
        )
        assert index_result["success"] is True

        # Now align using direct method call with comprehensive parameters
        result = tool_instance.bowtie2_align(
            index_base=str(sample_output_dir / "direct_test_index"),
            unpaired_files=[str(sample_input_files["unpaired_reads"])],
            sam_output=str(sample_output_dir / "direct_aligned.sam"),
            threads=1,
            very_sensitive=True,
            quiet=True,
        )

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Verify output file was created
        output_file = sample_output_dir / "direct_aligned.sam"
        assert output_file.exists()

    @pytest.mark.optional
    @pytest.mark.skipif(not BOWTIE2_AVAILABLE, reason="Bowtie2 not available on system")
    def test_bowtie2_align_paired_end(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Bowtie2 paired-end alignment."""
        # Build index first
        index_result = tool_instance.bowtie2_build(
            reference_in=[str(sample_input_files["reference_file"])],
            index_base=str(sample_output_dir / "paired_test_index"),
            threads=1,
        )
        assert index_result["success"] is True

        # Align paired-end reads
        result = tool_instance.bowtie2_align(
            index_base=str(sample_output_dir / "paired_test_index"),
            mate1_files=str(sample_input_files["mate1_reads"]),
            mate2_files=str(sample_input_files["mate2_reads"]),
            sam_output=str(sample_output_dir / "paired_aligned.sam"),
            threads=1,
            fr=True,  # Forward-reverse orientation
            quiet=True,
        )

        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_bowtie2_build_legacy(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Bowtie2 build functionality using legacy run() method."""
        params = {
            "operation": "build",
            "reference_in": [str(sample_input_files["reference_file"])],
            "index_base": str(sample_output_dir / "legacy_test_index"),
            "threads": 1,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify index files were created
        expected_files = [
            sample_output_dir / "legacy_test_index.1.bt2",
            sample_output_dir / "legacy_test_index.2.bt2",
            sample_output_dir / "legacy_test_index.3.bt2",
            sample_output_dir / "legacy_test_index.4.bt2",
            sample_output_dir / "legacy_test_index.rev.1.bt2",
            sample_output_dir / "legacy_test_index.rev.2.bt2",
        ]

        for expected_file in expected_files:
            if result.get("mock"):
                continue  # Skip file checks for mock results
            assert expected_file.exists(), (
                f"Expected index file {expected_file} not found"
            )

    @pytest.mark.optional
    @pytest.mark.skipif(not BOWTIE2_AVAILABLE, reason="Bowtie2 not available on system")
    def test_bowtie2_build_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Bowtie2 build functionality using direct method call."""
        result = tool_instance.bowtie2_build(
            reference_in=[str(sample_input_files["reference_file"])],
            index_base=str(sample_output_dir / "direct_build_index"),
            threads=1,
            large_index=False,
            packed=False,
            quiet=True,
        )

        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Verify index files were created
        expected_files = [
            sample_output_dir / "direct_build_index.1.bt2",
            sample_output_dir / "direct_build_index.2.bt2",
            sample_output_dir / "direct_build_index.3.bt2",
            sample_output_dir / "direct_build_index.4.bt2",
            sample_output_dir / "direct_build_index.rev.1.bt2",
            sample_output_dir / "direct_build_index.rev.2.bt2",
        ]

        for expected_file in expected_files:
            assert expected_file.exists(), (
                f"Expected index file {expected_file} not found"
            )

    @pytest.mark.optional
    @pytest.mark.skipif(not BOWTIE2_AVAILABLE, reason="Bowtie2 not available on system")
    def test_bowtie2_inspect_legacy(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Bowtie2 inspect functionality using legacy run() method."""
        # First build an index to inspect
        build_result = tool_instance.bowtie2_build(
            reference_in=[str(sample_input_files["reference_file"])],
            index_base=str(sample_output_dir / "inspect_test_index"),
            threads=1,
        )
        assert build_result["success"] is True

        # Now inspect the index
        params = {
            "operation": "inspect",
            "index_base": str(sample_output_dir / "inspect_test_index"),
            "summary": True,
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "stdout" in result

    @pytest.mark.optional
    @pytest.mark.skipif(not BOWTIE2_AVAILABLE, reason="Bowtie2 not available on system")
    def test_bowtie2_inspect_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Bowtie2 inspect functionality using direct method call."""
        # Build index first
        build_result = tool_instance.bowtie2_build(
            reference_in=[str(sample_input_files["reference_file"])],
            index_base=str(sample_output_dir / "direct_inspect_index"),
            threads=1,
        )
        assert build_result["success"] is True

        # Inspect with summary
        result = tool_instance.bowtie2_inspect(
            index_base=str(sample_output_dir / "direct_inspect_index"),
            summary=True,
            verbose=True,
        )

        assert result["success"] is True
        assert "stdout" in result
        assert "command_executed" in result

        # Inspect with names
        names_result = tool_instance.bowtie2_inspect(
            index_base=str(sample_output_dir / "direct_inspect_index"),
            names=True,
        )

        assert names_result["success"] is True
        assert "stdout" in names_result

    @pytest.mark.optional
    def test_bowtie2_parameter_validation(self, tool_instance, tmp_path):
        """Test Bowtie2 parameter validation."""
        # Create a dummy file for testing
        dummy_file = tmp_path / "dummy.fq"
        dummy_file.write_text("@read1\nATCG\n+\nIIII\n")

        # Test invalid mutually exclusive parameters for align
        with pytest.raises(ValueError, match="mutually exclusive"):
            tool_instance.bowtie2_align(
                index_base="test_index",
                unpaired_files=[str(dummy_file)],
                end_to_end=True,
                local=True,  # Cannot specify both
                sam_output=str(tmp_path / "output.sam"),
            )

        # Test invalid k and a combination
        with pytest.raises(ValueError, match="mutually exclusive"):
            tool_instance.bowtie2_align(
                index_base="test_index",
                unpaired_files=[str(dummy_file)],
                k=5,
                a=True,  # Cannot specify both
                sam_output=str(tmp_path / "output.sam"),
            )

        # Test invalid seed length for align
        with pytest.raises(ValueError, match="-N must be 0 or 1"):
            tool_instance.bowtie2_align(
                index_base="test_index",
                unpaired_files=[str(dummy_file)],
                mismatches_seed=2,  # Invalid value
                sam_output=str(tmp_path / "output.sam"),
            )

    @pytest.mark.optional
    def test_pydantic_ai_integration(self, tool_instance):
        """Test Pydantic AI MCP integration."""
        # Check that Pydantic AI tools are registered
        assert hasattr(tool_instance, "pydantic_ai_tools")
        assert isinstance(tool_instance.pydantic_ai_tools, list)
        assert len(tool_instance.pydantic_ai_tools) == 3  # align, build, inspect

        # Check that each tool has proper attributes
        for tool in tool_instance.pydantic_ai_tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "function")

        # Check server info includes Pydantic AI status
        server_info = tool_instance.get_server_info()
        assert "pydantic_ai_enabled" in server_info
        assert "session_active" in server_info

    @pytest.mark.optional
    @pytest.mark.skipif(not MCP_AVAILABLE, reason="FastMCP not available")
    def test_fastmcp_integration(self, tool_instance):
        """Test FastMCP server integration."""
        # Check that FastMCP server is available (may be None if FastMCP failed to initialize)
        assert hasattr(tool_instance, "fastmcp_server")

        # Check that run_fastmcp_server method exists
        assert hasattr(tool_instance, "run_fastmcp_server")

        # If FastMCP server was successfully initialized, check it has tools
        if tool_instance.fastmcp_server is not None:
            # Additional checks could be added here if FastMCP is available
            pass

    @pytest.mark.optional
    def test_server_info_comprehensive(self, tool_instance):
        """Test comprehensive server information."""
        server_info = tool_instance.get_server_info()

        required_keys = [
            "name",
            "type",
            "version",
            "description",
            "tools",
            "container_id",
            "container_name",
            "status",
            "capabilities",
            "pydantic_ai_enabled",
            "session_active",
            "docker_image",
            "bowtie2_version",
        ]

        for key in required_keys:
            assert key in server_info, f"Missing required key: {key}"

        assert server_info["name"] == "bowtie2-server"
        assert server_info["type"] == "bowtie2"
        assert "tools" in server_info
        assert isinstance(server_info["tools"], list)
        assert len(server_info["tools"]) == 3  # align, build, inspect

    @pytest.mark.optional
    @pytest.mark.containerized
    def test_containerized_execution(
        self, tool_instance, sample_input_files, sample_output_dir, test_config
    ):
        """Test tool execution in containerized environment."""
        if not test_config["docker_enabled"]:
            pytest.skip("Docker tests disabled")

        # This would test execution with Docker sandbox
        # Implementation depends on specific tool requirements
        with create_isolated_container(
            image="condaforge/miniforge3:latest",
            tool_name="bowtie2",
            workspace=sample_output_dir,
        ) as container:
            # Test basic functionality in container
            assert container is not None

    @pytest.mark.optional
    def test_error_handling_comprehensive(self, tool_instance, sample_output_dir):
        """Test comprehensive error handling."""
        # Test missing index file
        with pytest.raises(FileNotFoundError):
            tool_instance.bowtie2_align(
                index_base="nonexistent_index",
                unpaired_files=["test.fq"],
                sam_output=str(sample_output_dir / "error.sam"),
            )

        # Test invalid file paths
        with pytest.raises(FileNotFoundError):
            tool_instance.bowtie2_build(
                reference_in=["nonexistent.fa"],
                index_base=str(sample_output_dir / "error_index"),
            )

    @pytest.mark.optional
    def test_mock_functionality(self, tool_instance, sample_output_dir):
        """Test mock functionality when bowtie2 is not available."""
        # Mock shutil.which to return None (bowtie2 not available)
        with patch("shutil.which", return_value=None):
            result = tool_instance.run(
                {
                    "operation": "align",
                    "index_base": "test_index",
                    "unpaired_files": ["test.fq"],
                    "sam_output": str(sample_output_dir / "mock.sam"),
                }
            )

            # Should return mock success
            assert result["success"] is True
            assert result["mock"] is True
            assert "command_executed" in result
            assert "bowtie2 align [mock" in result["command_executed"]
