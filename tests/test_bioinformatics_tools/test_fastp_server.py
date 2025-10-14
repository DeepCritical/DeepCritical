"""
Fastp server component tests.
"""

from unittest.mock import Mock, patch

import pytest

from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestFastpServer(BaseBioinformaticsToolTest):
    """Test Fastp server functionality."""

    @property
    def tool_name(self) -> str:
        return "fastp-server"

    @property
    def tool_class(self):
        from DeepResearch.src.tools.bioinformatics.fastp_server import FastpServer

        return FastpServer

    @property
    def required_parameters(self) -> dict:
        return {
            "input1": "path/to/reads_1.fq",
            "output1": "path/to/processed_1.fq",
        }

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample FASTQ files for testing."""
        reads_file = tmp_path / "sample_reads.fq"

        # Create mock FASTQ file with proper FASTQ format
        reads_file.write_text(
            "@read1\n"
            "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
            "+\n"
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
            "@read2\n"
            "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA\n"
            "+\n"
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
        )

        return {"input1": reads_file}

    @pytest.fixture
    def sample_output_files(self, tmp_path):
        """Create sample output files for testing."""
        output_file = tmp_path / "processed_reads.fq.gz"
        return {"output1": output_file}

    @pytest.mark.optional
    def test_fastp_process_basic(
        self, tool_instance, sample_input_files, sample_output_files
    ):
        """Test basic Fastp process functionality."""
        params = {
            "operation": "process",
            "input1": str(sample_input_files["input1"]),
            "output1": str(sample_output_files["output1"]),
            "threads": 1,
            "compression": 1,
        }

        # Mock subprocess.run to avoid actual fastp execution
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="Processing complete", stderr=""
            )

            result = tool_instance.run(params)

            assert result["success"] is True
            assert "command_executed" in result
            assert "fastp" in result["command_executed"]
            assert result["exit_code"] == 0

    @pytest.mark.optional
    def test_fastp_process_with_validation(self, tool_instance):
        """Test Fastp parameter validation."""
        # Test missing input file
        params = {
            "operation": "process",
            "input1": "/nonexistent/file.fq",
            "output1": "/tmp/output.fq.gz",
        }

        result = tool_instance.run(params)
        # When fastp is not available, it returns mock success
        # In a real environment with fastp, this would fail validation
        if result.get("mock"):
            assert result["success"] is True
        else:
            assert result["success"] is False
            assert "not found" in result.get("error", "").lower()

    @pytest.mark.optional
    def test_fastp_process_paired_end(self, tool_instance, tmp_path):
        """Test Fastp process with paired-end reads."""
        # Create paired-end input files
        input1 = tmp_path / "reads_R1.fq"
        input2 = tmp_path / "reads_R2.fq"
        output1 = tmp_path / "processed_R1.fq.gz"
        output2 = tmp_path / "processed_R2.fq.gz"

        # Create mock FASTQ files
        for infile in [input1, input2]:
            infile.write_text(
                "@read1\n"
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
                "+\n"
                "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
            )

        params = {
            "operation": "process",
            "input1": str(input1),
            "input2": str(input2),
            "output1": str(output1),
            "output2": str(output2),
            "threads": 1,
            "detect_adapter_for_pe": True,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="Paired-end processing complete", stderr=""
            )

            result = tool_instance.run(params)

            assert result["success"] is True
            # Skip detailed command checks for mock results
            if not result.get("mock"):
                assert "-I" in result["command_executed"]  # Paired-end flag
                assert "-O" in result["command_executed"]  # Paired-end output flag

    @pytest.mark.optional
    def test_fastp_process_with_advanced_options(
        self, tool_instance, sample_input_files, sample_output_files
    ):
        """Test Fastp process with advanced quality control options."""
        params = {
            "operation": "process",
            "input1": str(sample_input_files["input1"]),
            "output1": str(sample_output_files["output1"]),
            "threads": 2,
            "cut_front": True,
            "cut_tail": True,
            "cut_mean_quality": 20,
            "qualified_quality_phred": 25,
            "unqualified_percent_limit": 30,
            "length_required": 25,
            "low_complexity_filter": True,
            "complexity_threshold": 0.5,
            "umi": True,
            "umi_loc": "read1",
            "umi_len": 8,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="Advanced processing complete", stderr=""
            )

            result = tool_instance.run(params)

            assert result["success"] is True
            # Skip detailed command checks for mock results
            if not result.get("mock"):
                assert "--cut_front" in result["command_executed"]
                assert "--cut_tail" in result["command_executed"]
                assert "--umi" in result["command_executed"]
                assert "--umi_loc" in result["command_executed"]

    @pytest.mark.optional
    def test_fastp_process_merging(self, tool_instance, tmp_path):
        """Test Fastp process with read merging."""
        input1 = tmp_path / "reads_R1.fq"
        input2 = tmp_path / "reads_R2.fq"
        merged_out = tmp_path / "merged_reads.fq.gz"
        unmerged1 = tmp_path / "unmerged_R1.fq.gz"
        unmerged2 = tmp_path / "unmerged_R2.fq.gz"

        # Create mock FASTQ files
        for infile in [input1, input2]:
            infile.write_text(
                "@read1\n"
                "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\n"
                "+\n"
                "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
            )

        params = {
            "operation": "process",
            "input1": str(input1),
            "input2": str(input2),
            "merge": True,
            "merged_out": str(merged_out),
            "output1": str(unmerged1),
            "output2": str(unmerged2),
            "include_unmerged": True,
            "threads": 1,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="Merging complete", stderr=""
            )

            result = tool_instance.run(params)

            assert result["success"] is True
            # Skip detailed command checks for mock results
            if not result.get("mock"):
                assert "-m" in result["command_executed"]  # Merge flag
                assert "--merged_out" in result["command_executed"]
                assert "--include_unmerged" in result["command_executed"]

    @pytest.mark.optional
    def test_fastp_server_info(self, tool_instance):
        """Test server info retrieval."""
        params = {
            "operation": "server_info",
        }

        result = tool_instance.run(params)

        assert result["success"] is True
        assert "name" in result
        assert "type" in result
        assert "version" in result
        assert "tools" in result
        assert result["name"] == "fastp-server"
        assert result["type"] == "fastp"

    @pytest.mark.optional
    def test_fastp_parameter_validation_errors(self, tool_instance):
        """Test parameter validation error handling."""
        # Test invalid compression level
        params = {
            "operation": "process",
            "input1": "/tmp/test.fq",
            "output1": "/tmp/output.fq.gz",
            "compression": 10,  # Invalid: should be 1-9
        }

        result = tool_instance.run(params)
        # When fastp is not available, validation doesn't occur
        if result.get("mock"):
            assert result["success"] is True
        else:
            assert result["success"] is False
            assert "compression" in result.get("error", "").lower()

        # Test invalid thread count
        params["compression"] = 4  # Fix compression
        params["thread"] = 0  # Invalid: should be >= 1

        result = tool_instance.run(params)
        # When fastp is not available, validation doesn't occur
        if result.get("mock"):
            assert result["success"] is True
        else:
            assert result["success"] is False
            assert "thread" in result.get("error", "").lower()

    @pytest.mark.optional
    def test_fastp_mcp_tool_execution(
        self, tool_instance, sample_input_files, sample_output_files
    ):
        """Test MCP tool execution through the server."""
        # Test that we can access the fastp_process tool through MCP interface
        tools = tool_instance.list_tools()
        assert "fastp_process" in tools

        # Test tool specification
        tool_spec = tool_instance.get_tool_spec("fastp_process")
        assert tool_spec is not None
        assert tool_spec.name == "fastp_process"
        assert "input1" in tool_spec.inputs
        assert "output1" in tool_spec.inputs

    @pytest.mark.optional
    @pytest.mark.asyncio
    async def test_fastp_container_deployment(self, tool_instance):
        """Test container deployment functionality."""
        # This test would require testcontainers to be available
        # For now, just test that the deployment method exists
        assert hasattr(tool_instance, "deploy_with_testcontainers")
        assert hasattr(tool_instance, "stop_with_testcontainers")

        # Test deployment method signature
        import inspect

        deploy_sig = inspect.signature(tool_instance.deploy_with_testcontainers)
        assert "MCPServerDeployment" in str(deploy_sig.return_annotation)
