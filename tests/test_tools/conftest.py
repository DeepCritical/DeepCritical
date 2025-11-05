"""
Fixtures for MCP Server Tools tests.

Provides fixtures with proper test isolation and state management.
"""

import pytest

from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
)
from DeepResearch.src.tools.mcp_server_tools import MCPServerManager


@pytest.fixture
def mcp_manager():
    """
    Fresh MCPServerManager instance with clean deployments.

    CRITICAL: Clears global deployments dict to prevent cross-test contamination.
    The mcp_server_manager singleton shares state, so isolation is essential.
    """
    manager = MCPServerManager()
    # Clear global state for test isolation
    manager.deployments.clear()
    return manager


@pytest.fixture
def mock_config():
    """Mock MCPServerConfig for testing."""
    return MCPServerConfig(server_name="test_server")


@pytest.fixture
def mock_deployment(mock_config):
    """
    Mock MCPServerDeployment for testing.

    CRITICAL: Includes required 'server_type' and 'configuration' fields
    to satisfy Pydantic validation.
    """
    return MCPServerDeployment(
        server_name="test_server",
        server_type=MCPServerType.CUSTOM,
        configuration=mock_config,
        status=MCPServerStatus.RUNNING,
        container_id="test_container_123",
    )


@pytest.fixture
def fastqc_config():
    """FastQC-specific config for integration tests."""
    return MCPServerConfig(
        server_name="fastqc",
        container_image="biocontainers/fastqc:latest",
    )


@pytest.fixture
def fastqc_deployment(fastqc_config):
    """
    FastQC deployment for status/stop tests.

    CRITICAL: Includes all required Pydantic fields.
    """
    return MCPServerDeployment(
        server_name="fastqc",
        server_type=MCPServerType.FASTQC,
        configuration=fastqc_config,
        status=MCPServerStatus.RUNNING,
        container_id="fastqc_container_456",
    )
