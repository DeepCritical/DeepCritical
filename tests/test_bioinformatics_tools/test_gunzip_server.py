"""
GunzipServer component tests.

Test philosophy:
- Test behavior, not implementation
- Minimal mocking (only when necessary)
- Clean fixtures (DRY)
- Descriptive test names explain expected behavior
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from DeepResearch.src.datatypes.mcp import MCPServerStatus, MCPServerType
from tests.test_bioinformatics_tools.base.test_base_tool import (
    BaseBioinformaticsToolTest,
)


class TestGunzipServer(BaseBioinformaticsToolTest):
    """Test gunzip server functionality.

    Inherits 5 free tests from BaseBioinformaticsToolTest:
    - test_tool_initialization
    - test_tool_specification
    - test_parameter_validation
    - test_tool_execution
    - test_error_handling
    """

    # ============================================================================
    # Required Properties (BaseBioinformaticsToolTest contract)
    # ============================================================================

    @property
    def tool_name(self) -> str:
        """Server name as registered in MCPServerManager."""
        return "gunzip-server"

    @property
    def tool_class(self):
        """Server class to instantiate for testing."""
        from DeepResearch.src.tools.bioinformatics.gunzip_server import GunzipServer

        return GunzipServer

    @property
    def required_parameters(self) -> dict:
        """Minimal parameters required for a successful run."""
        return {
            "operation": "decompress",
            "input_file": "path/to/file.gz",
        }

    # ============================================================================
    # Fixtures (DRY - reusable test data)
    # ============================================================================

    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample compressed and uncompressed files.

        Returns dict with both compressed and uncompressed files
        for testing all operations.
        """
        # Create uncompressed file with FASTQ-like content
        uncompressed = tmp_path / "sample.fastq"
        fastq_content = "@READ1\nACGTACGTACGT\n+\nIIIIIIIIIIII\n"
        uncompressed.write_text(fastq_content)

        # Create properly compressed gzip file
        compressed = tmp_path / "sample.fastq.gz"
        with gzip.open(compressed, "wt") as f:
            f.write(fastq_content)

        return {
            "uncompressed_file": uncompressed,
            "compressed_file": compressed,
        }

    @pytest.fixture
    def sample_output_dir(self, tmp_path):
        """Create clean output directory for test results."""
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)
        return output_dir

    # ============================================================================
    # Server Initialization Tests (behavior: server setup)
    # ============================================================================

    def test_server_initializes_with_default_config(self, tool_instance):
        """Server creates valid configuration on instantiation."""
        # Behavior: Server is ready to use after __init__
        assert tool_instance.name == "gunzip-server"
        assert tool_instance.server_type == MCPServerType.CUSTOM
        assert tool_instance.config.container_image == "python:3.11-slim"
        assert "GZIP_VERSION" in tool_instance.config.environment_variables

    def test_server_provides_tool_metadata(self, tool_instance):
        """Server describes its capabilities correctly."""
        # Behavior: Clients can discover what server offers
        info = tool_instance.get_server_info()

        assert info["name"] == "gunzip-server"
        assert info["type"] == MCPServerType.CUSTOM.value
        assert "tools" in info
        assert "version" in info
        assert "status" in info

    def test_server_lists_available_operations(self, tool_instance):
        """Server advertises available tool operations."""
        # Behavior: Tool discovery for orchestrators
        tools = tool_instance.list_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0
        # Should include core operations
        assert "decompress" in tools

    # ============================================================================
    # Decompress Operation Tests (behavior: file decompression)
    # ============================================================================

    @pytest.mark.optional
    def test_decompresses_gzip_file(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Decompress extracts content from .gz file."""
        # Arrange
        params = {
            "operation": "decompress",
            "input_file": str(sample_input_files["compressed_file"]),
            "output_dir": str(sample_output_dir),
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: decompression succeeds
        assert result["success"] is True
        assert "output_files" in result

        # Skip file validation for mock results
        if not result.get("mock"):
            output_file = Path(result["output_files"][0])
            assert output_file.exists()
            assert output_file.suffix != ".gz"

    @pytest.mark.optional
    def test_decompress_preserves_original_when_requested(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Decompress with keep_original=True leaves source file intact."""
        # Arrange
        params = {
            "operation": "decompress",
            "input_file": str(sample_input_files["compressed_file"]),
            "output_dir": str(sample_output_dir),
            "keep_original": True,
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: both files exist
        assert result["success"] is True

        if not result.get("mock"):
            original = Path(sample_input_files["compressed_file"])
            assert original.exists(), "Original file should be preserved"

            output_file = Path(result["output_files"][0])
            assert output_file.exists(), "Decompressed file should exist"

    @pytest.mark.optional
    def test_decompress_streams_to_stdout(self, tool_instance, sample_input_files):
        """Decompress with to_stdout=True writes to stdout instead of file."""
        # Arrange
        params = {
            "operation": "decompress",
            "input_file": str(sample_input_files["compressed_file"]),
            "to_stdout": True,
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: content in stdout, original file preserved
        assert result["success"] is True
        assert "stdout" in result
        assert len(result["stdout"]) > 0

        if not result.get("mock"):
            original = Path(sample_input_files["compressed_file"])
            assert original.exists(), "to_stdout should not delete source"

    @pytest.mark.optional
    def test_decompress_overwrites_existing_file_when_forced(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Decompress with force=True replaces existing output file."""
        # Arrange - Create pre-existing output file
        input_path = Path(sample_input_files["compressed_file"])
        existing_output = sample_output_dir / input_path.stem
        existing_content = "OLD CONTENT"
        existing_output.write_text(existing_content)

        params = {
            "operation": "decompress",
            "input_file": str(sample_input_files["compressed_file"]),
            "output_dir": str(sample_output_dir),
            "force": True,
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: overwrites existing file
        assert result["success"] is True

        if not result.get("mock"):
            assert existing_output.exists()
            new_content = existing_output.read_text()
            assert new_content != existing_content, "File should be overwritten"

    # ============================================================================
    # Compress Operation Tests (behavior: file compression)
    # ============================================================================

    @pytest.mark.optional
    def test_compresses_file_to_gzip(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Compress creates valid .gz file from input."""
        # Arrange
        params = {
            "operation": "compress",
            "input_file": str(sample_input_files["uncompressed_file"]),
            "output_dir": str(sample_output_dir),
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: creates .gz file
        assert result["success"] is True
        assert "output_files" in result

        if not result.get("mock"):
            output_file = Path(result["output_files"][0])
            assert output_file.exists()
            assert output_file.suffix == ".gz"

    @pytest.mark.optional
    @pytest.mark.parametrize("level", [1, 6, 9])
    def test_compress_respects_compression_level(
        self, tool_instance, sample_input_files, sample_output_dir, level
    ):
        """Compress accepts compression levels 1-9."""
        # Arrange
        params = {
            "operation": "compress",
            "input_file": str(sample_input_files["uncompressed_file"]),
            "output_dir": str(sample_output_dir),
            "compression_level": level,
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: level flag appears in command
        assert result["success"] is True
        assert f"-{level}" in result["command_executed"]

    # ============================================================================
    # Test/List Operation Tests (behavior: file inspection)
    # ============================================================================

    @pytest.mark.optional
    def test_validates_compressed_file_integrity(
        self, tool_instance, sample_input_files
    ):
        """Test operation validates .gz file without decompressing."""
        # Arrange
        params = {
            "operation": "test",
            "input_file": str(sample_input_files["compressed_file"]),
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: integrity check succeeds
        assert result["success"] is True
        assert result["exit_code"] == 0

    @pytest.mark.optional
    def test_lists_compression_statistics(self, tool_instance, sample_input_files):
        """List operation shows compression ratio and sizes."""
        # Arrange
        params = {
            "operation": "list",
            "input_file": str(sample_input_files["compressed_file"]),
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: returns statistics
        assert result["success"] is True
        assert "stdout" in result

        if not result.get("mock"):
            output = result["stdout"].lower()
            # gzip -l outputs compression info
            assert "compressed" in output or "ratio" in output

    # ============================================================================
    # Error Handling Tests (behavior: graceful failure)
    # ============================================================================

    def test_fails_gracefully_when_input_file_missing(self, tool_instance):
        """Decompress returns error dict when input file doesn't exist."""
        # Arrange
        params = {
            "operation": "decompress",
            "input_file": "/nonexistent/path/file.gz",
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: error dict, NOT exception
        assert result["success"] is False
        assert "error" in result
        error_msg = result["error"].lower()
        assert "not found" in error_msg or "does not exist" in error_msg

    def test_rejects_invalid_operation(self, tool_instance):
        """Run returns error for unsupported operation."""
        # Arrange
        params = {
            "operation": "invalid_operation",
            "input_file": "/some/file.gz",
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: reports unsupported operation
        assert result["success"] is False
        assert "error" in result
        assert "unsupported operation" in result["error"].lower()

    def test_requires_operation_parameter(self, tool_instance):
        """Run returns error when operation parameter missing."""
        # Arrange
        params = {
            "input_file": "/some/file.gz",
            # Missing "operation"
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: reports missing parameter
        assert result["success"] is False
        assert "error" in result
        error_msg = result["error"].lower()
        assert "missing" in error_msg
        assert "operation" in error_msg

    @pytest.mark.optional
    def test_detects_corrupted_gzip_file(self, tool_instance, tmp_path):
        """Decompress fails on invalid .gz file."""
        # Arrange - Create fake .gz file
        invalid_file = tmp_path / "corrupt.gz"
        invalid_file.write_text("NOT A GZIP FILE")

        params = {
            "operation": "decompress",
            "input_file": str(invalid_file),
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: detects corruption (unless mocked)
        if not result.get("mock"):
            assert result["success"] is False or result["exit_code"] != 0

    # ============================================================================
    # Mock Functionality Tests (behavior: works without gzip binary)
    # ============================================================================

    def test_uses_mock_mode_when_gzip_unavailable(
        self, tool_instance, monkeypatch, sample_input_files
    ):
        """Server falls back to mock mode when gzip not in PATH."""
        # Arrange - Mock shutil.which to simulate missing gzip
        monkeypatch.setattr("shutil.which", lambda x: None)

        params = {
            "operation": "decompress",
            "input_file": str(sample_input_files["compressed_file"]),
        }

        # Act
        result = tool_instance.run(params)

        # Assert - Behavior: mock mode activates, still returns success
        assert result["success"] is True
        assert result.get("mock") is True
        assert "mock" in result["command_executed"].lower()

    # ============================================================================
    # Testcontainers Integration Tests (behavior: container lifecycle)
    # ============================================================================

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_deploys_container_successfully(self, tool_instance):
        """Container deployment creates running server."""
        # Arrange & Act
        deployment = await tool_instance.deploy_with_testcontainers()

        try:
            # Assert - Behavior: container is running
            assert deployment.status == MCPServerStatus.RUNNING
            assert deployment.container_id is not None
            assert deployment.container_name is not None
            assert len(deployment.tools_available) > 0
        finally:
            # Cleanup
            await tool_instance.stop_with_testcontainers()

    @pytest.mark.containerized
    @pytest.mark.asyncio
    async def test_stops_container_cleanly(self, tool_instance):
        """Container stop releases resources."""
        # Arrange - Deploy first
        await tool_instance.deploy_with_testcontainers()

        # Act
        stopped = await tool_instance.stop_with_testcontainers()

        # Assert - Behavior: container stopped, resources cleared
        assert stopped is True
        assert tool_instance.container_id is None
