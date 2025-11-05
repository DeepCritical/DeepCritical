"""
Unit tests for Pydantic AI wrapper functions.

Tests the wrapper functions that adapt ToolRunner classes for Pydantic AI agents:
- mcp_server_deploy_tool
- mcp_server_list_tool
- mcp_server_execute_tool
- mcp_server_status_tool
- mcp_server_stop_tool
"""

import json

import pytest

from DeepResearch.src.tools.base import ExecutionResult
from DeepResearch.src.tools.mcp_server_tools import (
    MCPServerDeploymentTool,
    MCPServerExecuteTool,
    MCPServerListTool,
    MCPServerStatusTool,
    MCPServerStopTool,
    mcp_server_deploy_tool,
    mcp_server_execute_tool,
    mcp_server_list_tool,
    mcp_server_status_tool,
    mcp_server_stop_tool,
)


class MockContext:
    """Mock Pydantic AI context for testing."""

    def __init__(self, deps=None):
        self.deps = deps if deps is not None else {}


class TestPydanticAIDeployTool:
    """Test mcp_server_deploy_tool() wrapper function."""

    def test_returns_json_on_success(self, monkeypatch):
        """mcp_server_deploy_tool() returns JSON string on success."""

        def mock_run(self, params):
            return ExecutionResult(
                success=True, data={"status": "running", "container_id": "abc123"}
            )

        monkeypatch.setattr(MCPServerDeploymentTool, "run", mock_run)

        ctx = MockContext(deps={"server_name": "fastqc"})
        result = mcp_server_deploy_tool(ctx)

        assert isinstance(result, str)
        data = json.loads(result)
        assert data["status"] == "running"
        assert data["container_id"] == "abc123"

    def test_returns_error_string_on_failure(self, monkeypatch):
        """mcp_server_deploy_tool() returns error string on failure."""

        def mock_run(self, params):
            return ExecutionResult(success=False, error="Server not found")

        monkeypatch.setattr(MCPServerDeploymentTool, "run", mock_run)

        ctx = MockContext(deps={"server_name": "fake"})
        result = mcp_server_deploy_tool(ctx)

        assert isinstance(result, str)
        assert "Deployment failed:" in result
        assert "Server not found" in result

    def test_extracts_params_from_context_deps(self, monkeypatch):
        """mcp_server_deploy_tool() uses ctx.deps as params."""
        captured_params = None

        def mock_run(self, params):
            nonlocal captured_params
            captured_params = params
            return ExecutionResult(success=True, data={"status": "running"})

        monkeypatch.setattr(MCPServerDeploymentTool, "run", mock_run)

        expected_params = {
            "server_name": "fastqc",
            "container_image": "custom:image",
        }
        ctx = MockContext(deps=expected_params)
        mcp_server_deploy_tool(ctx)

        assert captured_params == expected_params


class TestPydanticAIListTool:
    """Test mcp_server_list_tool() wrapper function."""

    def test_returns_json_on_success(self, monkeypatch):
        """mcp_server_list_tool() returns JSON string with server list."""

        def mock_run(self, params):
            return ExecutionResult(
                success=True,
                data={
                    "servers": [{"name": "fastqc", "version": "0.12.1"}],
                    "count": 1,
                },
            )

        monkeypatch.setattr(MCPServerListTool, "run", mock_run)

        ctx = MockContext()
        result = mcp_server_list_tool(ctx)

        assert isinstance(result, str)
        data = json.loads(result)
        assert data["count"] == 1
        assert len(data["servers"]) == 1

    def test_returns_error_string_on_failure(self, monkeypatch):
        """mcp_server_list_tool() returns error string on failure."""

        def mock_run(self, params):
            return ExecutionResult(success=False, error="Registry error")

        monkeypatch.setattr(MCPServerListTool, "run", mock_run)

        ctx = MockContext()
        result = mcp_server_list_tool(ctx)

        assert isinstance(result, str)
        assert "List failed:" in result
        assert "Registry error" in result


class TestPydanticAIExecuteTool:
    """Test mcp_server_execute_tool() wrapper function."""

    def test_returns_json_on_success(self, monkeypatch):
        """mcp_server_execute_tool() returns JSON string with execution result."""

        def mock_run(self, params):
            return ExecutionResult(
                success=True, data={"result": {"quality_score": 95}, "success": True}
            )

        monkeypatch.setattr(MCPServerExecuteTool, "run", mock_run)

        ctx = MockContext(
            deps={
                "server_name": "fastqc",
                "tool_name": "quality_check",
                "parameters": {"input": "file.fastq"},
            }
        )
        result = mcp_server_execute_tool(ctx)

        assert isinstance(result, str)
        data = json.loads(result)
        assert data["result"]["quality_score"] == 95

    def test_returns_error_string_on_failure(self, monkeypatch):
        """mcp_server_execute_tool() returns error string on failure."""

        def mock_run(self, params):
            return ExecutionResult(success=False, error="Tool not found")

        monkeypatch.setattr(MCPServerExecuteTool, "run", mock_run)

        ctx = MockContext(deps={"server_name": "fastqc", "tool_name": "invalid_tool"})
        result = mcp_server_execute_tool(ctx)

        assert isinstance(result, str)
        assert "Execution failed:" in result
        assert "Tool not found" in result

    def test_extracts_params_from_context_deps(self, monkeypatch):
        """mcp_server_execute_tool() passes ctx.deps to tool runner."""
        captured_params = None

        def mock_run(self, params):
            nonlocal captured_params
            captured_params = params
            return ExecutionResult(success=True, data={"result": "success"})

        monkeypatch.setattr(MCPServerExecuteTool, "run", mock_run)

        expected_params = {
            "server_name": "fastqc",
            "tool_name": "qc",
            "parameters": {"input": "file.fastq"},
        }
        ctx = MockContext(deps=expected_params)
        mcp_server_execute_tool(ctx)

        assert captured_params == expected_params


class TestPydanticAIStatusTool:
    """Test mcp_server_status_tool() wrapper function."""

    def test_returns_json_on_success(self, monkeypatch):
        """mcp_server_status_tool() returns JSON string with status info."""

        def mock_run(self, params):
            return ExecutionResult(
                success=True,
                data={
                    "status": "running",
                    "container_id": "abc123",
                    "deployment_info": {},
                },
            )

        monkeypatch.setattr(MCPServerStatusTool, "run", mock_run)

        ctx = MockContext(deps={"server_name": "fastqc"})
        result = mcp_server_status_tool(ctx)

        assert isinstance(result, str)
        data = json.loads(result)
        assert data["status"] == "running"
        assert data["container_id"] == "abc123"

    def test_returns_error_string_on_failure(self, monkeypatch):
        """mcp_server_status_tool() returns error string on failure."""

        def mock_run(self, params):
            return ExecutionResult(success=False, error="Server not deployed")

        monkeypatch.setattr(MCPServerStatusTool, "run", mock_run)

        ctx = MockContext(deps={"server_name": "fastqc"})
        result = mcp_server_status_tool(ctx)

        assert isinstance(result, str)
        assert "Status check failed:" in result
        assert "Server not deployed" in result


class TestPydanticAIStopTool:
    """Test mcp_server_stop_tool() wrapper function."""

    def test_returns_json_on_success(self, monkeypatch):
        """mcp_server_stop_tool() returns JSON string with stop result."""

        def mock_run(self, params):
            return ExecutionResult(
                success=True, data={"success": True, "message": "Server stopped"}
            )

        monkeypatch.setattr(MCPServerStopTool, "run", mock_run)

        ctx = MockContext(deps={"server_name": "fastqc"})
        result = mcp_server_stop_tool(ctx)

        assert isinstance(result, str)
        data = json.loads(result)
        assert data["success"] is True
        assert "stopped" in data["message"]

    def test_returns_error_string_on_failure(self, monkeypatch):
        """mcp_server_stop_tool() returns error string on failure."""

        def mock_run(self, params):
            return ExecutionResult(success=False, error="Server not found")

        monkeypatch.setattr(MCPServerStopTool, "run", mock_run)

        ctx = MockContext(deps={"server_name": "fastqc"})
        result = mcp_server_stop_tool(ctx)

        assert isinstance(result, str)
        assert "Stop failed:" in result
        assert "Server not found" in result
