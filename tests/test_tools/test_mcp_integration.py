"""
Integration tests for MCP Server Tools.

Tests complete deployment flow with mocked testcontainers.
Real container tests are marked with @pytest.mark.containerized and @pytest.mark.slow.
"""

import pytest

from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
)
from DeepResearch.src.tools.mcp_server_tools import MCPServerManager


class TestMCPServerIntegration:
    """Integration tests with mocked containers."""

    @pytest.mark.asyncio
    async def test_full_deployment_flow(self, mcp_manager, monkeypatch):
        """
        Test complete deploy → status → execute → stop flow.

        This test verifies the entire lifecycle of an MCP server deployment
        without actually starting containers.
        """
        # CRITICAL: Ensure clean state for test isolation
        mcp_manager.deployments.clear()

        # Mock server class with testcontainer deployment behavior
        class MockFastQCServer:
            """Mock FastQC server that simulates container deployment."""

            name = "fastqc"
            description = "FastQC Quality Control"
            version = "0.12.1"

            def __init__(self, config):
                self.config = config

            async def deploy_with_testcontainers(self):
                """Simulate async deployment returning a complete MCPServerDeployment."""
                return MCPServerDeployment(
                    server_name="fastqc",
                    server_type=MCPServerType.FASTQC,
                    configuration=self.config,
                    status=MCPServerStatus.RUNNING,
                    container_id="test_container_123",
                )

            @staticmethod
            def list_tools():
                """Return list of available tools."""
                return ["quality_check"]

            @staticmethod
            def execute_tool(_tool_name, **_params):
                """Simulate tool execution."""
                return {"quality_score": 95, "passed_filters": True}

        # Inject mock server into manager's registry
        monkeypatch.setitem(mcp_manager.servers, "fastqc", MockFastQCServer)

        # 1. DEPLOY: Start the server
        config = MCPServerConfig(server_name="fastqc")
        deployment = await mcp_manager.deploy_server("fastqc", config)

        assert deployment.status == MCPServerStatus.RUNNING
        assert deployment.container_id == "test_container_123"
        assert "fastqc" in mcp_manager.deployments

        # 2. STATUS CHECK: Verify deployment is tracked
        assert mcp_manager.deployments["fastqc"].status == MCPServerStatus.RUNNING

        # 3. EXECUTE TOOL: Use deployed server
        # CRITICAL: get_server() returns class, need to instantiate
        server_class = mcp_manager.get_server("fastqc")
        server_instance = server_class(config)
        result = server_instance.execute_tool("quality_check", input="test.fastq")

        assert result["quality_score"] == 95
        assert result["passed_filters"] is True

        # 4. STOP: Clean up deployment
        stopped = mcp_manager.stop_server("fastqc")

        assert stopped is True
        assert mcp_manager.deployments["fastqc"].status == MCPServerStatus.STOPPED

    @pytest.mark.asyncio
    async def test_multiple_concurrent_deployments(self, mcp_manager, monkeypatch):
        """Test deploying multiple servers simultaneously."""
        # CRITICAL: Clear global state
        mcp_manager.deployments.clear()

        # Mock two different server classes
        class MockFastQCServer:
            def __init__(self, config):
                self.config = config

            async def deploy_with_testcontainers(self):
                return MCPServerDeployment(
                    server_name="fastqc",
                    server_type=MCPServerType.FASTQC,
                    configuration=self.config,
                    status=MCPServerStatus.RUNNING,
                    container_id="fastqc_123",
                )

        class MockSamtoolsServer:
            def __init__(self, config):
                self.config = config

            async def deploy_with_testcontainers(self):
                return MCPServerDeployment(
                    server_name="samtools",
                    server_type=MCPServerType.SAMTOOLS,
                    configuration=self.config,
                    status=MCPServerStatus.RUNNING,
                    container_id="samtools_456",
                )

        # Inject both mock servers
        monkeypatch.setitem(mcp_manager.servers, "fastqc", MockFastQCServer)
        monkeypatch.setitem(mcp_manager.servers, "samtools", MockSamtoolsServer)

        # Deploy both servers
        fastqc_config = MCPServerConfig(server_name="fastqc")
        samtools_config = MCPServerConfig(server_name="samtools")

        fastqc_deployment = await mcp_manager.deploy_server("fastqc", fastqc_config)
        samtools_deployment = await mcp_manager.deploy_server(
            "samtools", samtools_config
        )

        # Verify both are tracked
        assert "fastqc" in mcp_manager.deployments
        assert "samtools" in mcp_manager.deployments
        assert fastqc_deployment.container_id == "fastqc_123"
        assert samtools_deployment.container_id == "samtools_456"

        # Stop both
        assert mcp_manager.stop_server("fastqc") is True
        assert mcp_manager.stop_server("samtools") is True


@pytest.mark.containerized
@pytest.mark.slow
class TestMCPServerRealContainers:
    """
    Real container tests - disabled by default.

    These tests require Docker and are slow. They are marked with
    @pytest.mark.containerized and @pytest.mark.slow so they can be
    skipped during normal test runs.
    """

    @pytest.mark.skip(reason="Requires Docker and is slow")
    async def test_deploy_real_fastqc_server(self):
        """
        Smoke test: deploy real FastQC server.

        This test is skipped by default. To run it:
        1. Ensure Docker is running
        2. Run: pytest tests/test_tools/test_mcp_integration.py -m containerized -v

        WARNING: This will pull the FastQC Docker image if not present.
        """
        manager = MCPServerManager()
        manager.deployments.clear()

        config = MCPServerConfig(
            server_name="fastqc",
            container_image="biocontainers/fastqc:latest",
        )

        # This will actually deploy a container
        deployment = await manager.deploy_server("fastqc", config)

        assert deployment.status == MCPServerStatus.RUNNING
        assert deployment.container_id is not None
        assert deployment.container_id != ""

        # Cleanup
        stopped = manager.stop_server("fastqc")
        assert stopped is True
