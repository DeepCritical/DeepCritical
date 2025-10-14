"""
MCP Server Management Tools - Strongly typed tools for managing vendored MCP servers.

This module provides comprehensive tools for deploying, managing, and using
vendored MCP servers from the BioinfoMCP project using testcontainers and Pydantic AI patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Protocol

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

# Import all required modules
from ..datatypes.mcp import (
    MCPServerConfig,
    MCPServerStatus,
    MCPServerType,
    MCPToolExecutionRequest,
)
from ..tools.bioinformatics.bcftools_server import BCFtoolsServer
from ..tools.bioinformatics.bedtools_server import BEDToolsServer
from ..tools.bioinformatics.bowtie2_server import Bowtie2Server
from ..tools.bioinformatics.busco_server import BUSCOServer
from ..tools.bioinformatics.cutadapt_server import CutadaptServer
from ..tools.bioinformatics.deeptools_server import DeeptoolsServer
from ..tools.bioinformatics.fastp_server import FastpServer
from ..tools.bioinformatics.fastqc_server import FastQCServer
from ..tools.bioinformatics.featurecounts_server import FeatureCountsServer
from ..tools.bioinformatics.flye_server import FlyeServer
from ..tools.bioinformatics.freebayes_server import FreeBayesServer
from ..tools.bioinformatics.hisat2_server import HISAT2Server
from ..tools.bioinformatics.kallisto_server import KallistoServer
from ..tools.bioinformatics.macs3_server import MACS3Server
from ..tools.bioinformatics.meme_server import MEMEServer
from ..tools.bioinformatics.minimap2_server import Minimap2Server
from ..tools.bioinformatics.multiqc_server import MultiQCServer
from ..tools.bioinformatics.qualimap_server import QualimapServer
from ..tools.bioinformatics.salmon_server import SalmonServer
from ..tools.bioinformatics.samtools_server import SamtoolsServer
from ..tools.bioinformatics.seqtk_server import SeqtkServer
from ..tools.bioinformatics.star_server import STARServer
from ..tools.bioinformatics.stringtie_server import StringTieServer
from ..tools.bioinformatics.trimgalore_server import TrimGaloreServer
from ..utils.testcontainers_deployer import (
    TestcontainersConfig,
    TestcontainersDeployer,
)
from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class MCPServerProtocol(Protocol):
    """Protocol defining the expected interface for MCP server classes."""

    def list_tools(self) -> list[str]:
        """Return list of available tools."""
        ...

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        """Run a specific tool."""
        ...


# Placeholder classes for servers not yet implemented
class BWAServer(MCPServerProtocol):
    """Placeholder for BWA server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        raise NotImplementedError("BWA server not yet implemented")


class TopHatServer(MCPServerProtocol):
    """Placeholder for TopHat server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        raise NotImplementedError("TopHat server not yet implemented")


class HTSeqServer(MCPServerProtocol):
    """Placeholder for HTSeq server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        raise NotImplementedError("HTSeq server not yet implemented")


class PicardServer(MCPServerProtocol):
    """Placeholder for Picard server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        raise NotImplementedError("Picard server not yet implemented")


class HOMERServer(MCPServerProtocol):
    """Placeholder for HOMER server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        raise NotImplementedError("HOMER server not yet implemented")


# Configure logging
logger = logging.getLogger(__name__)

# Global server manager instance
server_manager = TestcontainersDeployer()

# Available server implementations
SERVER_IMPLEMENTATIONS = {
    # Quality Control & Preprocessing
    "fastqc": FastQCServer,
    "trimgalore": TrimGaloreServer,
    "cutadapt": CutadaptServer,
    "fastp": FastpServer,
    "multiqc": MultiQCServer,
    "qualimap": QualimapServer,
    "seqtk": SeqtkServer,
    # Sequence Alignment
    "bowtie2": Bowtie2Server,
    "bwa": BWAServer,
    "hisat2": HISAT2Server,
    "star": STARServer,
    "tophat": TopHatServer,
    "minimap2": Minimap2Server,
    # RNA-seq Quantification & Assembly
    "salmon": SalmonServer,
    "kallisto": KallistoServer,
    "stringtie": StringTieServer,
    "featurecounts": FeatureCountsServer,
    "htseq": HTSeqServer,
    # Genome Analysis & Manipulation
    "samtools": SamtoolsServer,
    "bedtools": BEDToolsServer,
    "picard": PicardServer,
    "deeptools": DeeptoolsServer,
    # ChIP-seq & Epigenetics
    "macs3": MACS3Server,
    "homer": HOMERServer,
    "meme": MEMEServer,
    # Genome Assembly
    "flye": FlyeServer,
    # Genome Assembly Assessment
    "busco": BUSCOServer,
    # Variant Analysis
    "bcftools": BCFtoolsServer,
    "freebayes": FreeBayesServer,
}


class MCPServerListRequest(BaseModel):
    """Request model for listing MCP servers."""

    include_status: bool = Field(True, description="Include server status information")
    include_tools: bool = Field(True, description="Include available tools information")


class MCPServerListResponse(BaseModel):
    """Response model for listing MCP servers."""

    servers: list[dict[str, Any]] = Field(..., description="List of available servers")
    count: int = Field(..., description="Number of servers")
    success: bool = Field(..., description="Whether the operation was successful")
    error: str | None = Field(None, description="Error message if operation failed")


class MCPServerDeployRequest(BaseModel):
    """Request model for deploying MCP servers."""

    server_name: str = Field(..., description="Name of the server to deploy")
    server_type: MCPServerType = Field(
        MCPServerType.CUSTOM, description="Type of MCP server"
    )
    container_image: str = Field("python:3.11-slim", description="Docker image to use")
    environment_variables: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    volumes: dict[str, str] = Field(default_factory=dict, description="Volume mounts")
    ports: dict[str, int] = Field(default_factory=dict, description="Port mappings")


class MCPServerDeployResponse(BaseModel):
    """Response model for deploying MCP servers."""

    deployment: dict[str, Any] = Field(..., description="Deployment information")
    container_id: str = Field(..., description="Container ID")
    status: str = Field(..., description="Deployment status")
    success: bool = Field(..., description="Whether deployment was successful")
    error: str | None = Field(None, description="Error message if deployment failed")


class MCPServerExecuteRequest(BaseModel):
    """Request model for executing MCP server tools."""

    server_name: str = Field(..., description="Name of the deployed server")
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    timeout: int = Field(300, description="Execution timeout in seconds")
    async_execution: bool = Field(False, description="Execute asynchronously")


class MCPServerExecuteResponse(BaseModel):
    """Response model for executing MCP server tools."""

    request: dict[str, Any] = Field(..., description="Original request")
    result: dict[str, Any] = Field(..., description="Execution result")
    execution_time: float = Field(..., description="Execution time in seconds")
    success: bool = Field(..., description="Whether execution was successful")
    error: str | None = Field(None, description="Error message if execution failed")


class MCPServerStatusRequest(BaseModel):
    """Request model for checking MCP server status."""

    server_name: str | None = Field(
        None, description="Specific server to check (None for all)"
    )


class MCPServerStatusResponse(BaseModel):
    """Response model for checking MCP server status."""

    status: str = Field(..., description="Server status")
    container_id: str = Field(..., description="Container ID")
    deployment_info: dict[str, Any] = Field(..., description="Deployment information")
    success: bool = Field(..., description="Whether status check was successful")


class MCPServerStopRequest(BaseModel):
    """Request model for stopping MCP servers."""

    server_name: str = Field(..., description="Name of the server to stop")


class MCPServerStopResponse(BaseModel):
    """Response model for stopping MCP servers."""

    success: bool = Field(..., description="Whether stop operation was successful")
    message: str = Field(..., description="Operation result message")
    error: str | None = Field(None, description="Error message if operation failed")


class MCPServerListTool(ToolRunner):
    """Tool for listing available MCP servers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mcp_server_list",
                description="List all available vendored MCP servers",
                inputs={
                    "include_status": "BOOLEAN",
                    "include_tools": "BOOLEAN",
                },
                outputs={
                    "servers": "JSON",
                    "count": "INTEGER",
                    "success": "BOOLEAN",
                    "error": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """List available MCP servers."""
        try:
            include_status = params.get("include_status", True)
            include_tools = params.get("include_tools", True)

            servers = []
            for server_name, server_class in SERVER_IMPLEMENTATIONS.items():
                server_info = {
                    "name": server_name,
                    "type": getattr(server_class, "__name__", "Unknown"),
                    "description": getattr(server_class, "__doc__", "").strip(),
                }

                if include_tools:
                    try:
                        server_instance: MCPServerProtocol = server_class()  # type: ignore[assignment]
                        server_info["tools"] = server_instance.list_tools()
                    except Exception as e:
                        server_info["tools"] = []
                        server_info["tools_error"] = str(e)

                if include_status:
                    # Check if server is deployed
                    try:
                        deployment = asyncio.run(
                            server_manager.get_server_status(server_name)
                        )
                        if deployment:
                            server_info["status"] = deployment.status
                            server_info["container_id"] = deployment.container_id
                        else:
                            server_info["status"] = "not_deployed"
                    except Exception as e:
                        server_info["status"] = "unknown"
                        server_info["status_error"] = str(e)

                servers.append(server_info)

            return ExecutionResult(
                success=True,
                data={
                    "servers": servers,
                    "count": len(servers),
                    "success": True,
                    "error": None,
                },
            )

        except Exception as e:
            logger.error(f"Failed to list MCP servers: {e}")
            return ExecutionResult(
                success=False,
                error=f"Failed to list MCP servers: {e!s}",
            )


class MCPServerDeployTool(ToolRunner):
    """Tool for deploying MCP servers using testcontainers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mcp_server_deploy",
                description="Deploy a vendored MCP server using testcontainers",
                inputs={
                    "server_name": "TEXT",
                    "server_type": "TEXT",
                    "container_image": "TEXT",
                    "environment_variables": "JSON",
                    "volumes": "JSON",
                    "ports": "JSON",
                },
                outputs={
                    "deployment": "JSON",
                    "container_id": "TEXT",
                    "status": "TEXT",
                    "success": "BOOLEAN",
                    "error": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Deploy an MCP server."""
        try:
            server_name = params.get("server_name", "")
            if not server_name:
                return ExecutionResult(success=False, error="Server name is required")

            # Check if server implementation exists
            if server_name not in SERVER_IMPLEMENTATIONS:
                return ExecutionResult(
                    success=False,
                    error=f"Server '{server_name}' not found. Available servers: {', '.join(SERVER_IMPLEMENTATIONS.keys())}",
                )

            # Create server configuration
            server_config = MCPServerConfig(
                server_name=server_name,
                server_type=MCPServerType(params.get("server_type", "custom")),
                container_image=params.get("container_image", "python:3.11-slim"),
                environment_variables=params.get("environment_variables", {}),
                volumes=params.get("volumes", {}),
                ports=params.get("ports", {}),
            )

            # Convert to TestcontainersConfig
            testcontainers_config = TestcontainersConfig(
                image=server_config.container_image,
                working_directory=server_config.working_directory,
                auto_remove=server_config.auto_remove,
                network_disabled=server_config.network_disabled,
                privileged=server_config.privileged,
                environment_variables=server_config.environment_variables,
                volumes=server_config.volumes,
                ports=server_config.ports,
            )

            # Deploy server
            deployment = asyncio.run(
                server_manager.deploy_server(server_name, config=testcontainers_config)
            )

            return ExecutionResult(
                success=True,
                data={
                    "deployment": deployment.model_dump(),
                    "container_id": deployment.container_id or "",
                    "status": deployment.status,
                    "success": deployment.status == MCPServerStatus.RUNNING,
                    "error": deployment.error_message or "",
                },
            )

        except Exception as e:
            logger.error(f"Failed to deploy MCP server: {e}")
            return ExecutionResult(
                success=False,
                error=f"Failed to deploy MCP server: {e!s}",
            )


class MCPServerExecuteTool(ToolRunner):
    """Tool for executing tools on deployed MCP servers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mcp_server_execute",
                description="Execute a tool on a deployed MCP server",
                inputs={
                    "server_name": "TEXT",
                    "tool_name": "TEXT",
                    "parameters": "JSON",
                    "timeout": "INTEGER",
                    "async_execution": "BOOLEAN",
                },
                outputs={
                    "result": "JSON",
                    "execution_time": "FLOAT",
                    "success": "BOOLEAN",
                    "error": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Execute a tool on an MCP server."""
        try:
            server_name = params.get("server_name", "")
            tool_name = params.get("tool_name", "")
            parameters = params.get("parameters", {})
            timeout = params.get("timeout", 300)
            async_execution = params.get("async_execution", False)

            if not server_name:
                return ExecutionResult(success=False, error="Server name is required")

            if not tool_name:
                return ExecutionResult(success=False, error="Tool name is required")

            # Create execution request
            request = MCPToolExecutionRequest(
                server_name=server_name,
                tool_name=tool_name,
                parameters=parameters,
                timeout=timeout,
                async_execution=async_execution,
            )

            # Get server deployment
            deployment = asyncio.run(server_manager.get_server_status(server_name))
            if not deployment:
                return ExecutionResult(
                    success=False, error=f"Server '{server_name}' not deployed"
                )

            if deployment.status != MCPServerStatus.RUNNING:
                return ExecutionResult(
                    success=False,
                    error=f"Server '{server_name}' is not running (status: {deployment.status})",
                )

            # Get server implementation
            server = SERVER_IMPLEMENTATIONS.get(server_name)
            if not server:
                return ExecutionResult(
                    success=False,
                    error=f"Server implementation for '{server_name}' not found",
                )

            # Execute tool
            if async_execution:
                result = asyncio.run(server().execute_tool_async(request))
            else:
                result = server().execute_tool(tool_name, **parameters)

            # Format result
            if hasattr(result, "model_dump"):
                result_data = result.model_dump()
            elif isinstance(result, dict):
                result_data = result
            else:
                result_data = {"result": str(result)}

            return ExecutionResult(
                success=True,
                data={
                    "result": result_data,
                    "execution_time": getattr(result, "execution_time", 0.0),
                    "success": True,
                    "error": None,
                },
            )

        except Exception as e:
            logger.error(f"Failed to execute MCP server tool: {e}")
            return ExecutionResult(
                success=False,
                error=f"Failed to execute MCP server tool: {e!s}",
            )


class MCPServerStatusTool(ToolRunner):
    """Tool for checking MCP server deployment status."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mcp_server_status",
                description="Check the status of deployed MCP servers",
                inputs={
                    "server_name": "TEXT",
                },
                outputs={
                    "status": "TEXT",
                    "container_id": "TEXT",
                    "deployment_info": "JSON",
                    "success": "BOOLEAN",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Check MCP server status."""
        try:
            server_name = params.get("server_name", "")

            if server_name:
                # Check specific server
                deployment = asyncio.run(server_manager.get_server_status(server_name))
                if not deployment:
                    return ExecutionResult(
                        success=False, error=f"Server '{server_name}' not deployed"
                    )

                return ExecutionResult(
                    success=True,
                    data={
                        "status": deployment.status,
                        "container_id": deployment.container_id or "",
                        "deployment_info": deployment.model_dump(),
                        "success": True,
                    },
                )
            # List all deployments
            deployments = asyncio.run(server_manager.list_servers())
            deployment_info = [d.model_dump() for d in deployments]

            return ExecutionResult(
                success=True,
                data={
                    "status": "multiple",
                    "deployments": deployment_info,
                    "count": len(deployment_info),
                    "success": True,
                },
            )

        except Exception as e:
            logger.error(f"Failed to check MCP server status: {e}")
            return ExecutionResult(
                success=False,
                error=f"Failed to check MCP server status: {e!s}",
            )


class MCPServerStopTool(ToolRunner):
    """Tool for stopping deployed MCP servers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mcp_server_stop",
                description="Stop a deployed MCP server",
                inputs={
                    "server_name": "TEXT",
                },
                outputs={
                    "success": "BOOLEAN",
                    "message": "TEXT",
                    "error": "TEXT",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """Stop an MCP server."""
        try:
            server_name = params.get("server_name", "")
            if not server_name:
                return ExecutionResult(success=False, error="Server name is required")

            # Stop server
            success = asyncio.run(server_manager.stop_server(server_name))

            if success:
                return ExecutionResult(
                    success=True,
                    data={
                        "success": True,
                        "message": f"Server '{server_name}' stopped successfully",
                        "error": "",
                    },
                )
            return ExecutionResult(
                success=False,
                error=f"Server '{server_name}' not found or already stopped",
            )

        except Exception as e:
            logger.error(f"Failed to stop MCP server: {e}")
            return ExecutionResult(
                success=False,
                error=f"Failed to stop MCP server: {e!s}",
            )


# Pydantic AI Tool Functions
def mcp_server_list_tool(ctx: RunContext[Any]) -> str:
    """
    List all available vendored MCP servers.

    This tool returns information about all vendored BioinfoMCP servers
    that can be deployed using testcontainers.

    Returns:
        JSON string containing list of available servers
    """
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    tool = MCPServerListTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"List failed: {result.error}"


def mcp_server_deploy_tool(ctx: RunContext[Any]) -> str:
    """
    Deploy a vendored MCP server using testcontainers.

    This tool deploys one of the vendored BioinfoMCP servers in an isolated container
    environment for secure execution. Available servers include quality control tools
    (fastqc, trimgalore, cutadapt, fastp, multiqc), sequence aligners (bowtie2, bwa,
    hisat2, star, tophat), RNA-seq tools (salmon, kallisto, stringtie, featurecounts, htseq),
    genome analysis tools (samtools, bedtools, picard), ChIP-seq tools (macs3, homer),
    genome assessment (busco), and variant analysis (bcftools).

    Args:
        server_name: Name of the server to deploy (see list above)
        server_type: Type of MCP server (optional)
        container_image: Docker image to use (optional, default: python:3.11-slim)
        environment_variables: Environment variables for the container (optional)
        volumes: Volume mounts (host_path:container_path) (optional)
        ports: Port mappings (container_port:host_port) (optional)

    Returns:
        JSON string containing deployment information
    """
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    tool = MCPServerDeployTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Deployment failed: {result.error}"


def mcp_server_execute_tool(ctx: RunContext[Any]) -> str:
    """
    Execute a tool on a deployed MCP server.

    This tool allows you to execute specific tools on deployed MCP servers.
    The servers must be deployed first using the mcp_server_deploy tool.

    Args:
        server_name: Name of the deployed server
        tool_name: Name of the tool to execute
        parameters: Parameters for the tool execution
        timeout: Execution timeout in seconds (optional, default: 300)
        async_execution: Execute asynchronously (optional, default: false)

    Returns:
        JSON string containing tool execution results
    """
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    tool = MCPServerExecuteTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Execution failed: {result.error}"


def mcp_server_status_tool(ctx: RunContext[Any]) -> str:
    """
    Check the status of deployed MCP servers.

    This tool provides status information for deployed MCP servers,
    including container status and deployment details.

    Args:
        server_name: Specific server to check (optional, checks all if not provided)

    Returns:
        JSON string containing server status information
    """
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    tool = MCPServerStatusTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Status check failed: {result.error}"


def mcp_server_stop_tool(ctx: RunContext[Any]) -> str:
    """
    Stop a deployed MCP server.

    This tool stops and cleans up a deployed MCP server container.

    Args:
        server_name: Name of the server to stop

    Returns:
        JSON string containing stop operation results
    """
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    tool = MCPServerStopTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Stop failed: {result.error}"


# Register tools with the global registry
def register_mcp_server_management_tools():
    """Register MCP server management tools with the global registry."""
    registry.register("mcp_server_list", MCPServerListTool)
    registry.register("mcp_server_deploy", MCPServerDeployTool)
    registry.register("mcp_server_execute", MCPServerExecuteTool)
    registry.register("mcp_server_status", MCPServerStatusTool)
    registry.register("mcp_server_stop", MCPServerStopTool)


# Auto-register when module is imported
register_mcp_server_management_tools()
