"""
Base test class for MCP bioinformatics servers.
"""

import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import pytest


class BaseBioinformaticsServerTest(ABC):
    """Base class for testing bioinformatics MCP servers."""

    @property
    @abstractmethod
    def server_class(self):
        """Return the server class to test."""

    @property
    @abstractmethod
    def server_name(self) -> str:
        """Return the server name for test identification."""

    @property
    @abstractmethod
    def required_tools(self) -> list:
        """Return list of required tools for the server."""

    @pytest.fixture
    def server_instance(self):
        """Create server instance for testing."""
        return self.server_class()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.optional
    def test_server_initialization(self, server_instance):
        """Test server initializes correctly."""
        assert server_instance is not None
        assert hasattr(server_instance, "name")
        assert hasattr(server_instance, "version")

    @pytest.mark.optional
    def test_server_tools_registration(self, server_instance):
        """Test that all required tools are registered."""
        registered_tools = server_instance.get_registered_tools()
        tool_names = [tool.name for tool in registered_tools]

        for required_tool in self.required_tools:
            assert required_tool in tool_names, f"Tool {required_tool} not registered"

    @pytest.mark.optional
    def test_server_capabilities(self, server_instance):
        """Test server capabilities reporting."""
        capabilities = server_instance.get_capabilities()

        assert "name" in capabilities
        assert "version" in capabilities
        assert "tools" in capabilities
        assert capabilities["name"] == self.server_name

    @pytest.mark.optional
    @pytest.mark.containerized
    def test_containerized_server_deployment(self, server_instance, temp_dir):
        """Test server deployment in containerized environment."""
        # This would test deployment with testcontainers
        # Implementation depends on specific server requirements

    @pytest.mark.optional
    def test_error_handling(self, server_instance):
        """Test error handling for invalid inputs."""
        # Test with invalid parameters
        result = server_instance.handle_request(
            {"method": "invalid_method", "params": {}}
        )

        assert "error" in result or result.get("success") is False
