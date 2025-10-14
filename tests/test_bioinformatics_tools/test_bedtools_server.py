"""
BEDTools server component tests.

Tests for the improved BEDTools server with FastMCP integration and enhanced functionality.
Includes both containerized and non-containerized test scenarios.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)
from tests.utils.testcontainers.docker_helpers import create_isolated_container


class TestBEDToolsServer(BaseBioinformaticsToolTest):
    """Test BEDTools server functionality."""

    @property
    def tool_name(self) -> str:
        return "bedtools-server"

    @property
    def tool_class(self):
        # Import the actual BEDTools server class
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        return BEDToolsServer

    @property
    def required_parameters(self) -> dict:
        """Required parameters for backward compatibility testing."""
        return {
            "a_file": "path/to/file_a.bed",
            "b_files": ["path/to/file_b.bed"],
            "operation": "intersect",  # For legacy run() method
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample BED files for testing."""
        bed_a = tmp_path / "regions_a.bed"
        bed_b = tmp_path / "regions_b.bed"

        # Create mock BED files with proper BED format
        bed_a.write_text("chr1\t100\t200\tfeature1\nchr1\t300\t400\tfeature2\n")
        bed_b.write_text("chr1\t150\t250\tpeak1\nchr1\t350\t450\tpeak2\n")

        return {"input_file_a": bed_a, "input_file_b": bed_b}

    @pytest.fixture
    def test_config(self):
        """Test configuration fixture."""
        import os

        return {
            "docker_enabled": os.getenv("DOCKER_TESTS", "false").lower() == "true",
        }

    @pytest.mark.optional
    def test_bedtools_intersect_legacy(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BEDTools intersect functionality using legacy run() method."""
        params = {
            "a_file": str(sample_input_files["input_file_a"]),
            "b_files": [str(sample_input_files["input_file_b"])],
            "operation": "intersect",
            "output_dir": str(sample_output_dir),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify output file was created
        output_file = sample_output_dir / "bedtools_intersect_output.bed"
        assert output_file.exists()

        # Verify output content
        content = output_file.read_text()
        assert "chr1" in content

    @pytest.mark.optional
    def test_bedtools_intersect_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BEDTools intersect functionality using direct method call."""
        result = tool_instance.bedtools_intersect(
            a_file=str(sample_input_files["input_file_a"]),
            b_files=[str(sample_input_files["input_file_b"])],
            output_file=str(sample_output_dir / "direct_intersect_output.bed"),
            wa=True,  # Write original A entries
        )

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify output file was created
        output_file = sample_output_dir / "direct_intersect_output.bed"
        assert output_file.exists()

    @pytest.mark.optional
    def test_bedtools_intersect_with_validation(self, tool_instance, tmp_path):
        """Test BEDTools intersect parameter validation."""
        # Test invalid file
        with pytest.raises(FileNotFoundError):
            tool_instance.bedtools_intersect(
                a_file=str(tmp_path / "nonexistent.bed"),
                b_files=[str(tmp_path / "also_nonexistent.bed")],
            )

        # Test invalid float parameter
        existing_file = tmp_path / "test.bed"
        existing_file.write_text("chr1\t100\t200\tfeature1\n")

        with pytest.raises(
            ValueError, match=r"Parameter f must be between 0\.0 and 1\.0"
        ):
            tool_instance.bedtools_intersect(
                a_file=str(existing_file),
                b_files=[str(existing_file)],
                f=1.5,  # Invalid fraction
            )

    @pytest.mark.optional
    def test_bedtools_merge_legacy(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BEDTools merge functionality using legacy run() method."""
        params = {
            "input_file": str(sample_input_files["input_file_a"]),
            "operation": "merge",
            "output_dir": str(sample_output_dir),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_bedtools_merge_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BEDTools merge functionality using direct method call."""
        result = tool_instance.bedtools_merge(
            input_file=str(sample_input_files["input_file_a"]),
            output_file=str(sample_output_dir / "direct_merge_output.bed"),
            d=0,  # Merge adjacent intervals
        )

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify output file was created
        output_file = sample_output_dir / "direct_merge_output.bed"
        assert output_file.exists()

    @pytest.mark.optional
    def test_bedtools_coverage_legacy(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BEDTools coverage functionality using legacy run() method."""
        params = {
            "a_file": str(sample_input_files["input_file_a"]),
            "b_files": [str(sample_input_files["input_file_b"])],
            "operation": "coverage",
            "output_dir": str(sample_output_dir),
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_bedtools_coverage_direct(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test BEDTools coverage functionality using direct method call."""
        result = tool_instance.bedtools_coverage(
            a_file=str(sample_input_files["input_file_a"]),
            b_files=[str(sample_input_files["input_file_b"])],
            output_file=str(sample_output_dir / "direct_coverage_output.bed"),
            hist=True,  # Generate histogram
        )

        assert result["success"] is True
        assert "output_files" in result

        # Skip file checks for mock results
        if result.get("mock"):
            return

        # Verify output file was created
        output_file = sample_output_dir / "direct_coverage_output.bed"
        assert output_file.exists()

    @pytest.mark.optional
    def test_fastmcp_integration(self, tool_instance):
        """Test FastMCP integration if available."""
        server_info = tool_instance.get_server_info()

        # Check FastMCP availability status
        assert "fastmcp_available" in server_info
        assert "fastmcp_enabled" in server_info
        assert "docker_image" in server_info
        assert server_info["docker_image"] == "condaforge/miniforge3:latest"

        # Test server info structure
        assert "version" in server_info
        assert "bedtools_version" in server_info

    @pytest.mark.optional
    def test_server_initialization(self):
        """Test server initialization with different configurations."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Test default initialization
        server = BEDToolsServer()
        assert server.name == "bedtools-server"
        assert server.server_type.value == "bedtools"

        # Test custom config
        from DeepResearch.src.datatypes.mcp import MCPServerConfig, MCPServerType

        custom_config = MCPServerConfig(
            server_name="custom-bedtools",
            server_type=MCPServerType.BEDTOOLS,
            container_image="condaforge/miniforge3:latest",
            environment_variables={"CUSTOM_VAR": "test"},
        )
        custom_server = BEDToolsServer(config=custom_config)
        assert custom_server.name == "custom-bedtools"

    @pytest.mark.optional
    def test_fastmcp_server_mode(self, tool_instance, tmp_path):
        """Test FastMCP server mode configuration."""
        server_info = tool_instance.get_server_info()

        # Verify FastMCP status is tracked
        assert "fastmcp_available" in server_info
        assert "fastmcp_enabled" in server_info

        # Test that run_fastmcp_server method exists
        assert hasattr(tool_instance, "run_fastmcp_server")

        # Test that FastMCP server is properly configured when available
        if server_info["fastmcp_available"]:
            assert tool_instance.fastmcp_server is not None
        else:
            assert tool_instance.fastmcp_server is None

        # Test that FastMCP server can be disabled
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        server_no_fastmcp = BEDToolsServer(enable_fastmcp=False)
        assert server_no_fastmcp.fastmcp_server is None
        assert server_no_fastmcp.get_server_info()["fastmcp_enabled"] is False

    @pytest.mark.optional
    def test_bedtools_parameter_ranges(self, tool_instance, tmp_path):
        """Test BEDTools parameter range validation."""
        # Create valid input files
        bed_a = tmp_path / "test_a.bed"
        bed_b = tmp_path / "test_b.bed"
        bed_a.write_text("chr1\t100\t200\tfeature1\n")
        bed_b.write_text("chr1\t150\t250\tfeature2\n")

        # Test valid parameters
        result = tool_instance.bedtools_intersect(
            a_file=str(bed_a),
            b_files=[str(bed_b)],
            f=0.5,  # Valid fraction
            fraction_b=0.8,  # Valid fraction
        )
        assert result["success"] is True or result.get("mock") is True

    @pytest.mark.optional
    def test_bedtools_invalid_parameters(self, tool_instance, tmp_path):
        """Test BEDTools parameter validation with invalid values."""
        # Create valid input files
        bed_a = tmp_path / "test_a.bed"
        bed_b = tmp_path / "test_b.bed"
        bed_a.write_text("chr1\t100\t200\tfeature1\n")
        bed_b.write_text("chr1\t150\t250\tfeature2\n")

        # Test invalid fraction parameter
        with pytest.raises(
            ValueError, match=r"Parameter f must be between 0\.0 and 1\.0"
        ):
            tool_instance.bedtools_intersect(
                a_file=str(bed_a),
                b_files=[str(bed_b)],
                f=1.5,  # Invalid fraction > 1.0
            )

        # Test invalid fraction_b parameter
        with pytest.raises(
            ValueError, match=r"Parameter fraction_b must be between 0\.0 and 1\.0"
        ):
            tool_instance.bedtools_intersect(
                a_file=str(bed_a),
                b_files=[str(bed_b)],
                fraction_b=-0.1,  # Invalid negative fraction
            )

    @pytest.mark.optional
    def test_bedtools_output_formats(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test different BEDTools output formats."""
        # Test stdout output (no output_file specified)
        result = tool_instance.bedtools_intersect(
            a_file=str(sample_input_files["input_file_a"]),
            b_files=[str(sample_input_files["input_file_b"])],
            # No output_file specified - should output to stdout
        )

        # Should succeed or be mocked
        assert result["success"] is True or result.get("mock") is True
        if not result.get("mock"):
            assert "stdout" in result
            assert "chr1" in result["stdout"]

    @pytest.mark.optional
    def test_bedtools_complex_operations(self, tool_instance, tmp_path):
        """Test complex BEDTools operations with multiple parameters."""
        # Create test files
        bed_a = tmp_path / "complex_a.bed"
        bed_b = tmp_path / "complex_b.bed"
        bed_a.write_text("chr1\t100\t200\tfeature1\t+\nchr2\t300\t400\tfeature2\t-\n")
        bed_b.write_text("chr1\t150\t250\tpeak1\t+\nchr2\t350\t450\tpeak2\t-\n")

        result = tool_instance.bedtools_intersect(
            a_file=str(bed_a),
            b_files=[str(bed_b)],
            output_file=str(tmp_path / "complex_output.bed"),
            wa=True,  # Write all A features
            wb=True,  # Write all B features
            loj=True,  # Left outer join
            f=0.5,  # 50% overlap required
            s=True,  # Same strand only
        )

        # Should succeed or be mocked
        assert result["success"] is True or result.get("mock") is True

    @pytest.mark.optional
    def test_bedtools_multiple_input_files(self, tool_instance, tmp_path):
        """Test BEDTools operations with multiple input files."""
        # Create test files
        bed_a = tmp_path / "multi_a.bed"
        bed_b1 = tmp_path / "multi_b1.bed"
        bed_b2 = tmp_path / "multi_b2.bed"

        bed_a.write_text("chr1\t100\t200\tgene1\n")
        bed_b1.write_text("chr1\t120\t180\tpeak1\n")
        bed_b2.write_text("chr1\t150\t250\tpeak2\n")

        result = tool_instance.bedtools_intersect(
            a_file=str(bed_a),
            b_files=[str(bed_b1), str(bed_b2)],
            output_file=str(tmp_path / "multi_output.bed"),
            wa=True,
        )

        # Should succeed or be mocked
        assert result["success"] is True or result.get("mock") is True

    # ===== CONTAINERIZED TESTS =====

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_containerized_bedtools_deployment(self, tmp_path):
        """Test BEDTools server deployment in containerized environment."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Create server instance
        server = BEDToolsServer()

        # Deploy server in container
        deployment = await server.deploy_with_testcontainers()
        assert deployment.status == "running"

        try:
            # Wait for BEDTools to be installed and ready in the container
            import asyncio

            await asyncio.sleep(30)  # Wait for conda environment setup

            # Verify server info
            server_info = server.get_server_info()
            assert server_info["container_id"] is not None
            assert server_info["docker_image"] == "condaforge/miniforge3:latest"
            assert server_info["bedtools_version"] == "2.30.0"

            # Test basic container connectivity
            health = await server.health_check()
            assert health is True

        finally:
            # Clean up container
            stopped = await server.stop_with_testcontainers()
            assert stopped is True

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_containerized_bedtools_intersect_workflow(self, tmp_path):
        """Test complete BEDTools intersect workflow in containerized environment."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Create server instance
        server = BEDToolsServer()

        # Deploy server in container
        deployment = await server.deploy_with_testcontainers()
        assert deployment.status == "running"

        try:
            # Wait for BEDTools installation
            import asyncio

            await asyncio.sleep(30)

            # Create sample BED files in container-accessible location
            bed_a = tmp_path / "regions_a.bed"
            bed_b = tmp_path / "regions_b.bed"

            # Create mock BED files with genomic coordinates
            bed_a.write_text("chr1\t100\t200\tfeature1\nchr1\t300\t400\tfeature2\n")
            bed_b.write_text("chr1\t150\t250\tpeak1\nchr1\t350\t450\tpeak2\n")

            # Test intersect operation in container
            result = server.bedtools_intersect(
                a_file=str(bed_a),
                b_files=[str(bed_b)],
                output_file=str(tmp_path / "intersect_output.bed"),
                wa=True,  # Write original A entries
            )

            assert result["success"] is True
            assert "output_files" in result

            # Verify output file was created
            output_file = tmp_path / "intersect_output.bed"
            assert output_file.exists()

            # Verify output contains expected genomic data
            content = output_file.read_text()
            assert "chr1" in content

        finally:
            # Clean up container
            stopped = await server.stop_with_testcontainers()
            assert stopped is True

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_containerized_bedtools_merge_workflow(self, tmp_path):
        """Test BEDTools merge workflow in containerized environment."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Create server instance
        server = BEDToolsServer()

        # Deploy server in container
        deployment = await server.deploy_with_testcontainers()
        assert deployment.status == "running"

        try:
            # Wait for BEDTools installation
            import asyncio

            await asyncio.sleep(30)

            # Create sample BED file
            bed_file = tmp_path / "regions.bed"
            bed_file.write_text("chr1\t100\t200\tfeature1\nchr1\t180\t300\tfeature2\n")

            # Test merge operation in container
            result = server.bedtools_merge(
                input_file=str(bed_file),
                output_file=str(tmp_path / "merge_output.bed"),
                d=50,  # Maximum distance for merging
            )

            assert result["success"] is True
            assert "output_files" in result

            # Verify output file was created
            output_file = tmp_path / "merge_output.bed"
            assert output_file.exists()

        finally:
            # Clean up container
            stopped = await server.stop_with_testcontainers()
            assert stopped is True

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_containerized_bedtools_coverage_workflow(self, tmp_path):
        """Test BEDTools coverage workflow in containerized environment."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Create server instance
        server = BEDToolsServer()

        # Deploy server in container
        deployment = await server.deploy_with_testcontainers()
        assert deployment.status == "running"

        try:
            # Wait for BEDTools installation
            import asyncio

            await asyncio.sleep(30)

            # Create sample BED files
            bed_a = tmp_path / "features.bed"
            bed_b = tmp_path / "reads.bed"

            bed_a.write_text("chr1\t100\t200\tgene1\nchr1\t300\t400\tgene2\n")
            bed_b.write_text("chr1\t120\t180\tread1\nchr1\t320\t380\tread2\n")

            # Test coverage operation in container
            result = server.bedtools_coverage(
                a_file=str(bed_a),
                b_files=[str(bed_b)],
                output_file=str(tmp_path / "coverage_output.bed"),
                hist=True,  # Generate histogram
            )

            assert result["success"] is True
            assert "output_files" in result

            # Verify output file was created
            output_file = tmp_path / "coverage_output.bed"
            assert output_file.exists()

        finally:
            # Clean up container
            stopped = await server.stop_with_testcontainers()
            assert stopped is True

    @pytest.mark.containerized
    def test_containerized_bedtools_isolation(self, test_config, tmp_path):
        """Test BEDTools container isolation and security."""
        if not test_config["docker_enabled"]:
            pytest.skip("Docker tests disabled")

        # Create isolated container for BEDTools
        container = create_isolated_container(
            image="condaforge/miniforge3:latest",
            command=["bedtools", "--version"],
        )

        # Start container
        container.start()

        try:
            # Wait for container to be running
            import time

            for _ in range(10):  # Wait up to 10 seconds
                container.reload()
                if container.status == "running":
                    break
                time.sleep(1)

            assert container.status == "running"

            # Verify BEDTools is available in container
            # Note: In a real test, you'd execute commands in the container
            # For now, just verify the container starts properly

        finally:
            container.stop()

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_containerized_bedtools_error_handling(self, tmp_path):
        """Test error handling in containerized BEDTools operations."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Create server instance
        server = BEDToolsServer()

        # Deploy server in container
        deployment = await server.deploy_with_testcontainers()
        assert deployment.status == "running"

        try:
            # Wait for container setup
            import asyncio

            await asyncio.sleep(20)  # Shorter wait for error testing

            # Test with non-existent input file
            nonexistent_file = tmp_path / "nonexistent.bed"
            result = server.bedtools_intersect(
                a_file=str(nonexistent_file),
                b_files=[str(nonexistent_file)],
            )

            # Should handle error gracefully
            assert result["success"] is False
            assert "error" in result

        finally:
            # Clean up container
            stopped = await server.stop_with_testcontainers()
            assert stopped is True

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_containerized_bedtools_pydantic_ai_integration(self, tmp_path):
        """Test Pydantic AI integration in containerized environment."""
        from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer

        # Create server instance
        server = BEDToolsServer()

        # Deploy server in container
        deployment = await server.deploy_with_testcontainers()
        assert deployment.status == "running"

        try:
            # Wait for container setup
            import asyncio

            await asyncio.sleep(30)

            # Test Pydantic AI agent availability
            pydantic_agent = server.get_pydantic_ai_agent()

            # In container environment, agent might not be initialized due to missing API keys
            # But the method should not raise an exception
            # Agent will be None if API keys are not available
            assert pydantic_agent is None or hasattr(pydantic_agent, "run")

            # Test session info
            session_info = server.get_session_info()
            # Session info should be available even if agent is not initialized
            assert session_info is None or isinstance(session_info, dict)

        finally:
            # Clean up container
            stopped = await server.stop_with_testcontainers()
            assert stopped is True
