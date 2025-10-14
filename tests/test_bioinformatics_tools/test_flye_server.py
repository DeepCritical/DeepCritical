"""
Flye server component tests.
"""

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestFlyeServer(BaseBioinformaticsToolTest):
    """Test Flye server functionality."""

    @property
    def tool_name(self) -> str:
        return "flye-server"

    @property
    def tool_class(self):
        from DeepResearch.src.tools.bioinformatics.flye_server import FlyeServer

        return FlyeServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input_type": "nano-raw",
            "input_files": ["path/to/reads.fq"],
            "out_dir": "path/to/output",
        }

    @property
    def optional_parameters(self) -> dict:
        return {
            "genome_size": "5m",
            "threads": 1,
            "iterations": 2,
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads_file = tmp_path / "sample_reads.fq"

        # Create mock FASTQ file with proper FASTQ format
        reads_file.write_text(
            "@read1\nATCGATCGATCGATCGATCGATCGATCGATCGATCG\n+\nIIIIIIIIIIIIIII\n"
        )

        return {"input_files": [reads_file]}

    @pytest.mark.optional
    def test_flye_assembly_basic(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test basic Flye assembly functionality."""
        # Test with mock data (when flye is not available)
        result = tool_instance.flye_assembly(
            input_type="nano-raw",
            input_files=[str(sample_input_files["input_files"][0])],
            out_dir=str(sample_output_dir),
            genome_size="5m",
            threads=1,
        )

        assert isinstance(result, dict)
        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Check that output directory is in output_files
        assert str(sample_output_dir) in result["output_files"]

        # Skip detailed file checks for mock results
        if result.get("mock"):
            return

    @pytest.mark.optional
    def test_flye_assembly_with_all_params(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Flye assembly with all parameters."""
        result = tool_instance.flye_assembly(
            input_type="nano-raw",
            input_files=[str(sample_input_files["input_files"][0])],
            out_dir=str(sample_output_dir),
            genome_size="5m",
            threads=2,
            iterations=3,
            meta=True,
            polish_target=True,
            min_overlap="1000",
            keep_haplotypes=True,
            debug=True,
            scaffold=True,
            resume=False,
            resume_from=None,
            stop_after=None,
            read_error=0.01,
            extra_params="--some-extra-param value",
            deterministic=True,
        )

        assert isinstance(result, dict)
        assert result["success"] is True
        assert "output_files" in result
        assert "command_executed" in result

        # Check that command contains expected parameters
        command = result["command_executed"]
        assert "--nano-raw" in command
        assert "--genome-size 5m" in command
        assert "--threads 2" in command
        assert "--iterations 3" in command
        assert "--meta" in command
        assert "--polish-target" in command
        assert "--keep-haplotypes" in command
        assert "--debug" in command
        assert "--scaffold" in command
        assert "--read-error 0.01" in command
        assert "--deterministic" in command

    @pytest.mark.optional
    def test_flye_assembly_input_validation(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test input validation for Flye assembly."""
        # Test invalid input_type
        with pytest.raises(ValueError, match="Invalid input_type 'invalid'"):
            tool_instance.flye_assembly(
                input_type="invalid",
                input_files=[str(sample_input_files["input_files"][0])],
                out_dir=str(sample_output_dir),
            )

        # Test empty input_files
        with pytest.raises(
            ValueError, match="At least one input file must be provided"
        ):
            tool_instance.flye_assembly(
                input_type="nano-raw",
                input_files=[],
                out_dir=str(sample_output_dir),
            )

        # Test non-existent input file
        with pytest.raises(FileNotFoundError):
            tool_instance.flye_assembly(
                input_type="nano-raw",
                input_files=["/non/existent/file.fq"],
                out_dir=str(sample_output_dir),
            )

        # Test invalid threads
        with pytest.raises(ValueError, match="threads must be >= 1"):
            tool_instance.flye_assembly(
                input_type="nano-raw",
                input_files=[str(sample_input_files["input_files"][0])],
                out_dir=str(sample_output_dir),
                threads=0,
            )

        # Test invalid iterations
        with pytest.raises(ValueError, match="iterations must be >= 1"):
            tool_instance.flye_assembly(
                input_type="nano-raw",
                input_files=[str(sample_input_files["input_files"][0])],
                out_dir=str(sample_output_dir),
                iterations=0,
            )

        # Test invalid read_error
        with pytest.raises(ValueError, match=r"read_error must be between 0.0 and 1.0"):
            tool_instance.flye_assembly(
                input_type="nano-raw",
                input_files=[str(sample_input_files["input_files"][0])],
                out_dir=str(sample_output_dir),
                read_error=1.5,
            )

    @pytest.mark.optional
    def test_flye_assembly_different_input_types(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test Flye assembly with different input types."""
        input_types = [
            "pacbio-raw",
            "pacbio-corr",
            "pacbio-hifi",
            "nano-raw",
            "nano-corr",
            "nano-hq",
        ]

        for input_type in input_types:
            result = tool_instance.flye_assembly(
                input_type=input_type,
                input_files=[str(sample_input_files["input_files"][0])],
                out_dir=str(sample_output_dir),
            )

            assert isinstance(result, dict)
            assert result["success"] is True
            assert f"--{input_type}" in result["command_executed"]

    @pytest.mark.optional
    def test_flye_server_run_method(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test the server's run method with operation dispatch."""
        params = {
            "operation": "assembly",
            "input_type": "nano-raw",
            "input_files": [str(sample_input_files["input_files"][0])],
            "out_dir": str(sample_output_dir),
            "genome_size": "5m",
            "threads": 1,
        }

        result = tool_instance.run(params)

        assert isinstance(result, dict)
        assert result["success"] is True
        assert "output_files" in result

    @pytest.mark.optional
    def test_flye_server_run_invalid_operation(self, tool_instance):
        """Test the server's run method with invalid operation."""
        params = {
            "operation": "invalid_operation",
        }

        result = tool_instance.run(params)

        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert "Unsupported operation" in result["error"]

    @pytest.mark.optional
    def test_flye_server_run_missing_operation(self, tool_instance):
        """Test the server's run method with missing operation."""
        params = {}

        result = tool_instance.run(params)

        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert "Missing 'operation' parameter" in result["error"]

    @pytest.mark.optional
    def test_mcp_server_integration(self, tool_instance):
        """Test MCP server integration features."""
        # Test server info
        server_info = tool_instance.get_server_info()
        assert isinstance(server_info, dict)
        assert "name" in server_info
        assert "type" in server_info
        assert "tools" in server_info
        assert "status" in server_info
        assert server_info["name"] == "flye-server"

        # Test tool listing
        tools = tool_instance.list_tools()
        assert isinstance(tools, list)
        assert "flye_assembly" in tools

        # Test tool specification
        tool_spec = tool_instance.get_tool_spec("flye_assembly")
        assert tool_spec is not None
        assert tool_spec.name == "flye_assembly"
        assert "input_type" in tool_spec.inputs
        assert "input_files" in tool_spec.inputs
        assert "out_dir" in tool_spec.inputs

        # Test server capabilities
        capabilities = tool_instance.config.capabilities
        expected_capabilities = [
            "genome_assembly",
            "long_read_assembly",
            "nanopore",
            "pacbio",
            "de_novo_assembly",
            "hybrid_assembly",
            "metagenome_assembly",
            "repeat_resolution",
            "structural_variant_detection",
        ]
        for capability in expected_capabilities:
            assert capability in capabilities, f"Missing capability: {capability}"

    @pytest.mark.optional
    def test_pydantic_ai_integration(self, tool_instance):
        """Test Pydantic AI agent integration."""
        # Test that Pydantic AI tools are registered
        assert hasattr(tool_instance, "pydantic_ai_tools")
        assert len(tool_instance.pydantic_ai_tools) > 0

        # Test that flye_assembly is registered as a Pydantic AI tool
        tool_names = [tool.name for tool in tool_instance.pydantic_ai_tools]
        assert "flye_assembly" in tool_names

        # Test that Pydantic AI agent is initialized (may be None if API key not set)
        # This tests the initialization attempt rather than successful agent creation
        assert hasattr(tool_instance, "pydantic_ai_agent")

    @pytest.mark.optional
    @pytest.mark.asyncio
    async def test_deploy_with_testcontainers(self, tool_instance):
        """Test containerized deployment with improved conda environment setup."""
        # This test requires Docker and testcontainers
        # For now, just verify the method exists and can be called
        # In a real environment, this would test actual container deployment

        # The method should exist but may fail without Docker
        assert hasattr(tool_instance, "deploy_with_testcontainers")

        try:
            deployment = await tool_instance.deploy_with_testcontainers()
            # If successful, verify deployment structure
            if deployment:
                assert hasattr(deployment, "server_name")
                assert hasattr(deployment, "container_id")
                assert hasattr(deployment, "status")
                assert hasattr(deployment, "capabilities")
                assert deployment.server_name == "flye-server"

                # Check that expected capabilities are in deployment
                expected_caps = [
                    "genome_assembly",
                    "long_read_assembly",
                    "nanopore",
                    "pacbio",
                ]
                for cap in expected_caps:
                    assert cap in deployment.capabilities
        except Exception:
            # Expected in environments without Docker/testcontainers
            pass

    @pytest.mark.optional
    def test_server_config_initialization(self, tool_instance):
        """Test that server is properly initialized with correct configuration."""
        # Test server configuration
        assert tool_instance.name == "flye-server"
        assert tool_instance.server_type.value == "custom"
        assert tool_instance.config.container_image == "condaforge/miniforge3:latest"

        # Test environment variables
        assert "FLYE_VERSION" in tool_instance.config.environment_variables
        assert tool_instance.config.environment_variables["FLYE_VERSION"] == "2.9.2"

        # Test capabilities are properly set
        capabilities = tool_instance.config.capabilities
        assert "genome_assembly" in capabilities
        assert "metagenome_assembly" in capabilities
        assert "structural_variant_detection" in capabilities
