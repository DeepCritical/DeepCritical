"""
Unit tests for MCP Tool Runner classes.

Tests the 5 ToolRunner classes that wrap MCPServerManager functionality:
- MCPServerDeploymentTool
- MCPServerListTool
- MCPServerExecuteTool
- MCPServerStatusTool
- MCPServerStopTool
"""

import pytest

from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
)
from DeepResearch.src.tools.mcp_server_tools import (
    MCPServerDeploymentTool,
    MCPServerExecuteTool,
    MCPServerListTool,
    MCPServerStatusTool,
    MCPServerStopTool,
)


class TestMCPServerDeploymentTool:
    """Test MCPServerDeploymentTool ToolRunner."""

    def test_run_requires_server_name(self):
        """run() returns error when server_name missing."""
        tool = MCPServerDeploymentTool()
        result = tool.run({})

        assert result.success is False
        assert result.error is not None
        assert "Server name is required" in result.error

    def test_run_fails_for_nonexistent_server(self):
        """run() returns error with available servers list."""
        tool = MCPServerDeploymentTool()
        result = tool.run({"server_name": "fake_server"})

        assert result.success is False
        assert result.error is not None
        assert "fake_server" in result.error
        assert "Available servers:" in result.error

    def test_run_creates_config_from_params(self, monkeypatch):
        """run() creates MCPServerConfig with provided params."""
        tool = MCPServerDeploymentTool()

        # Track what config was passed to deploy_server
        captured_config = None

        async def mock_deploy(server_name, config):
            nonlocal captured_config
            captured_config = config
            # Return deployment with all required fields
            return MCPServerDeployment(
                server_name=server_name,
                server_type=MCPServerType.FASTQC,
                configuration=config,
                status=MCPServerStatus.RUNNING,
                container_id="test123",
            )

        # Mock the global mcp_server_manager
        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.deploy_server",
            mock_deploy,
        )

        result = tool.run(
            {
                "server_name": "fastqc",
                "container_image": "custom:image",
                "environment_variables": {"VAR": "value"},
                "volumes": {"/host": "/container"},
                "ports": {"8080": 8000},
            }
        )

        assert result.success is True
        assert captured_config is not None
        assert captured_config.server_name == "fastqc"
        assert captured_config.container_image == "custom:image"
        assert captured_config.environment_variables == {"VAR": "value"}
        assert captured_config.volumes == {"/host": "/container"}
        assert captured_config.ports == {"8080": 8000}


class TestMCPServerListTool:
    """Test MCPServerListTool ToolRunner."""

    def test_run_returns_all_servers_with_details(self, monkeypatch):
        """run() returns server details for all registered servers."""
        tool = MCPServerListTool()

        # CRITICAL: Mock server as CLASS with class attributes
        # (mcp_server_tools.py:292-300 accesses server.name, server.description, etc.)
        class MockServer:
            name = "test_server"
            description = "Test description"
            version = "1.0.0"

            @staticmethod
            def list_tools():
                return ["tool1", "tool2"]

        # Mock manager methods
        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.list_servers",
            lambda: ["test_server"],
        )
        # Return MockServer CLASS (not instance) - matches actual behavior
        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.get_server",
            lambda name: MockServer,  # Returns class, not instance!
        )

        result = tool.run({})

        assert result.success is True
        assert result.data["count"] == 1
        assert len(result.data["servers"]) == 1
        assert result.data["servers"][0]["name"] == "test_server"
        assert result.data["servers"][0]["description"] == "Test description"
        assert result.data["servers"][0]["version"] == "1.0.0"
        assert result.data["servers"][0]["tools"] == ["tool1", "tool2"]

    def test_run_handles_exceptions_gracefully(self, monkeypatch):
        """run() returns error when list_servers raises exception."""
        tool = MCPServerListTool()

        def mock_list_error():
            raise RuntimeError("Registry error")

        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.list_servers",
            mock_list_error,
        )

        result = tool.run({})

        assert result.success is False
        assert result.error is not None
        assert "Registry error" in result.error


class TestMCPServerExecuteTool:
    """Test MCPServerExecuteTool ToolRunner."""

    def test_run_requires_server_name(self):
        """run() returns error when server_name missing."""
        tool = MCPServerExecuteTool()
        result = tool.run({"tool_name": "tool"})

        assert result.success is False
        assert result.error is not None
        assert "Server name is required" in result.error

    def test_run_requires_tool_name(self):
        """run() returns error when tool_name missing."""
        tool = MCPServerExecuteTool()
        result = tool.run({"server_name": "fastqc"})

        assert result.success is False
        assert result.error is not None
        assert "Tool name is required" in result.error

    def test_run_validates_tool_exists_on_server(self, monkeypatch):
        """run() checks tool_name against server.list_tools()."""
        tool = MCPServerExecuteTool()

        # CRITICAL: Return class with static methods
        # (mcp_server_tools.py:361 calls server.list_tools())
        class MockServer:
            @staticmethod
            def list_tools():
                return ["valid_tool"]

        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.get_server",
            lambda name: MockServer,  # Returns class
        )

        result = tool.run(
            {
                "server_name": "fastqc",
                "tool_name": "invalid_tool",
            }
        )

        assert result.success is False
        assert result.error is not None
        assert "invalid_tool" in result.error
        assert "Available tools:" in result.error

    def test_run_executes_tool_with_parameters(self, monkeypatch):
        """run() calls server.execute_tool() with provided params."""
        tool = MCPServerExecuteTool()

        # Track what parameters were passed
        executed_params = None

        class MockServer:
            @staticmethod
            def list_tools():
                return ["test_tool"]

            @staticmethod
            def execute_tool(_tool_name, **params):
                nonlocal executed_params
                executed_params = params
                return {"output": "result"}

        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.get_server",
            lambda name: MockServer,
        )

        result = tool.run(
            {
                "server_name": "fastqc",
                "tool_name": "test_tool",
                "parameters": {"input": "value"},
            }
        )

        assert result.success is True
        assert executed_params is not None
        assert executed_params == {"input": "value"}
        assert result.data["result"] == {"output": "result"}


class TestMCPServerStatusTool:
    """Test MCPServerStatusTool ToolRunner."""

    def test_run_returns_error_for_undeployed_server(self, monkeypatch):
        """run() returns error when specific server not deployed."""
        tool = MCPServerStatusTool()

        # CRITICAL: Mock global deployments as empty dict
        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.deployments",
            {},
        )

        result = tool.run({"server_name": "fastqc"})

        assert result.success is False
        assert result.error is not None
        assert "not deployed" in result.error

    def test_run_returns_deployment_info_for_deployed_server(
        self, monkeypatch, fastqc_deployment
    ):
        """run() returns deployment details when server is deployed."""
        tool = MCPServerStatusTool()

        # Mock deployments dict with fastqc entry
        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.deployments",
            {"fastqc": fastqc_deployment},
        )

        result = tool.run({"server_name": "fastqc"})

        assert result.success is True
        assert result.data["status"] == MCPServerStatus.RUNNING
        assert result.data["container_id"] == "fastqc_container_456"

    def test_run_lists_all_deployments_when_no_server_name(
        self, monkeypatch, fastqc_config, mock_config
    ):
        """run() returns all deployments when server_name not provided."""
        tool = MCPServerStatusTool()

        # Create multiple deployments
        deployments = {
            "fastqc": MCPServerDeployment(
                server_name="fastqc",
                server_type=MCPServerType.FASTQC,
                configuration=fastqc_config,
                status=MCPServerStatus.RUNNING,
                container_id="abc",
            ),
            "samtools": MCPServerDeployment(
                server_name="samtools",
                server_type=MCPServerType.SAMTOOLS,
                configuration=mock_config,
                status=MCPServerStatus.STOPPED,
                container_id="def",
            ),
        }

        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.deployments",
            deployments,
        )

        result = tool.run({})

        assert result.success is True
        assert result.data["count"] == 2
        assert len(result.data["deployments"]) == 2


class TestMCPServerStopTool:
    """Test MCPServerStopTool ToolRunner."""

    def test_run_requires_server_name(self):
        """run() returns error when server_name missing."""
        tool = MCPServerStopTool()
        result = tool.run({})

        assert result.success is False
        assert result.error is not None
        assert "Server name is required" in result.error

    def test_run_fails_when_server_not_deployed(self, monkeypatch):
        """run() returns error when server not in deployments."""
        tool = MCPServerStopTool()

        # Mock stop_server to return False
        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.stop_server",
            lambda name: False,
        )

        result = tool.run({"server_name": "fastqc"})

        assert result.success is False
        assert result.error is not None
        assert "not found or already stopped" in result.error

    def test_run_succeeds_when_server_stopped(self, monkeypatch):
        """run() returns success when stop_server() returns True."""
        tool = MCPServerStopTool()

        # Mock stop_server to return True
        monkeypatch.setattr(
            "DeepResearch.src.tools.mcp_server_tools.mcp_server_manager.stop_server",
            lambda name: True,
        )

        result = tool.run({"server_name": "fastqc"})

        assert result.success is True
        assert "stopped successfully" in result.data["message"]
