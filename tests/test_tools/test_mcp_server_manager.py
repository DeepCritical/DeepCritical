"""
Unit tests for MCPServerManager.

Tests server registry operations, deployment lifecycle, and state management
without actual container deployment.
"""

import pytest

from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
)
from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer
from DeepResearch.src.tools.mcp_server_management import SERVER_IMPLEMENTATIONS
from DeepResearch.src.tools.mcp_server_tools import (
    MCP_STUB_SERVER_NAMES,
    MCPServerManager,
)
from DeepResearch.src.utils.testcontainers_deployer import (
    TestcontainersDeployer as MCPTestcontainersDeployer,
)

ISSUE_130_RECONCILED_SERVER_KEYS = {
    "deeptools",
    "gunzip",
    "haplotypecaller",
    "mafft",
    "multiqc",
}


class TestMCPServerManager:
    """Test MCPServerManager server registry and lifecycle."""

    def test_lists_all_registered_servers(self, mcp_manager):
        """Verify the manager lists the full registered server set."""
        servers = mcp_manager.list_servers()

        assert set(servers) == set(mcp_manager.servers)
        assert "fastqc" in servers
        assert "salmon" in servers
        assert "freebayes" in servers
        assert "gunzip" in servers
        assert "haplotypecaller" in servers
        assert "mafft" in servers

    def test_issue_130_reconciled_servers_are_publicly_discoverable(self):
        """Existing issue #130 servers are aligned across public registries."""
        manager = MCPServerManager()
        deployer = MCPTestcontainersDeployer()

        for server_key in ISSUE_130_RECONCILED_SERVER_KEYS:
            assert server_key in manager.list_implemented()
            assert server_key in SERVER_IMPLEMENTATIONS
            assert server_key in deployer.server_implementations
            assert server_key not in MCP_STUB_SERVER_NAMES

    def test_management_map_matches_manager_registry(self):
        """Public management tools do not drift from MCPServerManager keys."""
        manager = MCPServerManager()

        assert set(SERVER_IMPLEMENTATIONS) == set(manager.servers)

    def test_get_server_returns_class_for_valid_name(self, mcp_manager):
        """get_server() returns server class when name exists."""
        server_class = mcp_manager.get_server("fastqc")

        assert server_class is not None
        assert server_class == FastQCServer

    def test_get_server_returns_none_for_invalid_name(self, mcp_manager):
        """get_server() returns None when server doesn't exist."""
        server_class = mcp_manager.get_server("nonexistent_server")

        assert server_class is None

    def test_stop_server_returns_false_when_not_deployed(self, mcp_manager):
        """stop_server() returns False if server not in deployments."""
        result = mcp_manager.stop_server("fastqc")

        assert result is False

    def test_stop_server_updates_status_when_deployed(
        self, mcp_manager, fastqc_deployment
    ):
        """stop_server() sets status to STOPPED for deployed servers."""
        # Manually add deployment (no real container)
        mcp_manager.deployments["fastqc"] = fastqc_deployment

        result = mcp_manager.stop_server("fastqc")

        assert result is True
        assert mcp_manager.deployments["fastqc"].status == MCPServerStatus.STOPPED

    @pytest.mark.asyncio
    async def test_deploy_server_fails_for_nonexistent_server(self, mcp_manager):
        """deploy_server() returns FAILED deployment for invalid server."""
        config = MCPServerConfig(server_name="fake_server")

        deployment = await mcp_manager.deploy_server("fake_server", config)

        assert deployment.status == MCPServerStatus.FAILED
        assert deployment.error_message is not None
        assert "fake_server" in deployment.error_message
        assert "not found" in deployment.error_message
        assert deployment.configuration == config
        assert deployment.server_type == config.server_type

    @pytest.mark.asyncio
    async def test_deploy_server_catches_exceptions(self, mcp_manager, monkeypatch):
        """deploy_server() returns FAILED deployment on exception."""

        # Mock server class to raise exception during __init__
        class FaultyServer:
            def __init__(self, config):
                raise ValueError("Deployment error")

        # Inject faulty server into manager's registry
        monkeypatch.setitem(mcp_manager.servers, "test_server", FaultyServer)
        config = MCPServerConfig(server_name="test_server")

        deployment = await mcp_manager.deploy_server("test_server", config)

        assert deployment.status == MCPServerStatus.FAILED
        assert deployment.error_message is not None
        assert "Deployment error" in deployment.error_message
        assert deployment.configuration == config
        assert deployment.server_type == config.server_type
