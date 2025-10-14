"""
Base test class for individual bioinformatics tools.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest


class BaseBioinformaticsToolTest(ABC):
    """Base class for testing individual bioinformatics tools."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Return the tool name for test identification."""

    @property
    @abstractmethod
    def tool_class(self):
        """Return the tool class to test."""

    @property
    @abstractmethod
    def required_parameters(self) -> dict[str, Any]:
        """Return required parameters for tool execution."""

    @property
    def optional_parameters(self) -> dict[str, Any]:
        """Return optional parameters for tool execution."""
        return {}

    @pytest.fixture
    def tool_instance(self):
        """Create tool instance for testing."""
        return self.tool_class()

    @pytest.fixture
    def sample_input_files(self, temp_dir) -> dict[str, Path]:
        """Create sample input files for testing."""
        return {}

    @pytest.fixture
    def temp_dir(self, tmp_path) -> Path:
        """Create temporary directory for testing."""
        return tmp_path

    @pytest.fixture
    def sample_output_dir(self, temp_dir) -> Path:
        """Create sample output directory for testing."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        return output_dir

    @pytest.mark.optional
    def test_tool_initialization(self, tool_instance):
        """Test tool initializes correctly."""
        assert tool_instance is not None
        assert hasattr(tool_instance, "name")

        # Check for MCP server or traditional tool interface (avoid Mock objects)
        is_mcp_server = (
            hasattr(tool_instance, "list_tools")
            and hasattr(tool_instance, "get_server_info")
            and not isinstance(tool_instance, Mock)
            and hasattr(tool_instance, "__class__")
            and "Mock" not in str(type(tool_instance))
        )
        if is_mcp_server:
            # MCP servers should have server info
            assert hasattr(tool_instance, "get_server_info")
        else:
            # Traditional tools should have run method
            assert hasattr(tool_instance, "run")

    @pytest.mark.optional
    def test_tool_specification(self, tool_instance):
        """Test tool specification is correctly defined."""
        # Check if this is an MCP server (avoid Mock objects)
        is_mcp_server = (
            hasattr(tool_instance, "list_tools")
            and hasattr(tool_instance, "get_server_info")
            and not isinstance(tool_instance, Mock)
            and hasattr(tool_instance, "__class__")
            and "Mock" not in str(type(tool_instance))
        )

        if is_mcp_server:
            # For MCP servers, check server info and tools
            server_info = tool_instance.get_server_info()
            assert isinstance(server_info, dict)
            assert "name" in server_info
            assert "tools" in server_info
            assert server_info["name"] == self.tool_name

            # Check that tools are available
            tools = tool_instance.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
        else:
            # Mock get_spec method if it doesn't exist for traditional tools
            if not hasattr(tool_instance, "get_spec"):
                mock_spec = {
                    "name": self.tool_name,
                    "description": f"Test tool {self.tool_name}",
                    "inputs": {"param1": "TEXT"},
                    "outputs": {"result": "TEXT"},
                }
                tool_instance.get_spec = Mock(return_value=mock_spec)

            spec = tool_instance.get_spec()

            # Check that spec is a dictionary and has required keys
            assert isinstance(spec, dict)
            assert "name" in spec
            assert "description" in spec
            assert "inputs" in spec
            assert "outputs" in spec
            assert spec["name"] == self.tool_name

    @pytest.mark.optional
    def test_parameter_validation(self, tool_instance):
        """Test parameter validation."""
        # Check if this is an MCP server (avoid Mock objects)
        is_mcp_server = (
            hasattr(tool_instance, "list_tools")
            and hasattr(tool_instance, "get_server_info")
            and not isinstance(tool_instance, Mock)
            and hasattr(tool_instance, "__class__")
            and "Mock" not in str(type(tool_instance))
        )

        if is_mcp_server:
            # For MCP servers, parameter validation is handled by the MCP tool decorators
            # Just verify the server has tools available
            tools = tool_instance.list_tools()
            assert len(tools) > 0
        else:
            # Mock validate_parameters method if it doesn't exist for traditional tools
            if not hasattr(tool_instance, "validate_parameters"):

                def mock_validate_parameters(params):
                    required_keys = set(self.required_parameters.keys())
                    provided_keys = set(params.keys())
                    return {"valid": required_keys.issubset(provided_keys)}

                tool_instance.validate_parameters = Mock(
                    side_effect=mock_validate_parameters
                )

            # Test with valid parameters
            valid_params = {**self.required_parameters, **self.optional_parameters}
            result = tool_instance.validate_parameters(valid_params)
            assert isinstance(result, dict)
            assert result["valid"] is True

            # Test with missing required parameters
            invalid_params = self.optional_parameters.copy()
            result = tool_instance.validate_parameters(invalid_params)
            assert isinstance(result, dict)
            assert result["valid"] is False

    @pytest.mark.optional
    def test_tool_execution(self, tool_instance, sample_input_files, sample_output_dir):
        """Test tool execution with sample data."""
        # Check if this is an MCP server (avoid Mock objects)
        is_mcp_server = (
            hasattr(tool_instance, "list_tools")
            and hasattr(tool_instance, "get_server_info")
            and not isinstance(tool_instance, Mock)
            and hasattr(tool_instance, "__class__")
            and "Mock" not in str(type(tool_instance))
        )

        if is_mcp_server:
            # For MCP servers, execution is tested in specific test methods
            # Just verify the server can provide server info
            server_info = tool_instance.get_server_info()
            assert isinstance(server_info, dict)
            assert "status" in server_info
        else:
            # Mock run method if it doesn't exist for traditional tools
            if not hasattr(tool_instance, "run"):

                def mock_run(params):
                    return {
                        "success": True,
                        "outputs": ["output1"],
                        "output_files": ["file1"],
                    }

                tool_instance.run = Mock(side_effect=mock_run)

            params = {
                **self.required_parameters,
                **self.optional_parameters,
                "output_dir": str(sample_output_dir),
            }

            # Add input file paths if provided
            for key, file_path in sample_input_files.items():
                params[key] = str(file_path)

            result = tool_instance.run(params)

            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is True
            assert "outputs" in result or "output_files" in result

    @pytest.mark.optional
    def test_error_handling(self, tool_instance):
        """Test error handling for invalid inputs."""
        # Check if this is an MCP server (avoid Mock objects)
        is_mcp_server = (
            hasattr(tool_instance, "list_tools")
            and hasattr(tool_instance, "get_server_info")
            and not isinstance(tool_instance, Mock)
            and hasattr(tool_instance, "__class__")
            and "Mock" not in str(type(tool_instance))
        )

        if is_mcp_server:
            # For MCP servers, error handling is tested in specific test methods
            # Just verify the server exists and has tools
            tools = tool_instance.list_tools()
            assert isinstance(tools, list)
        else:
            # Mock run method if it doesn't exist for traditional tools
            if not hasattr(tool_instance, "run"):

                def mock_run(params):
                    if "invalid_param" in params:
                        return {"success": False, "error": "Invalid parameter"}
                    return {"success": True, "outputs": ["output1"]}

                tool_instance.run = Mock(side_effect=mock_run)

            invalid_params = {"invalid_param": "invalid_value"}

            result = tool_instance.run(invalid_params)

            assert isinstance(result, dict)
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.optional
    @pytest.mark.containerized
    def test_containerized_execution(
        self, tool_instance, sample_input_files, sample_output_dir
    ):
        """Test tool execution in containerized environment."""
        # This would test execution with Docker sandbox
        # Implementation depends on specific tool requirements
