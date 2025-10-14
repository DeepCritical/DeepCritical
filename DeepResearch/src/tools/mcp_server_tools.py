"""
MCP Server Tools - Tools for managing vendored BioinfoMCP servers.

This module provides strongly-typed tools for deploying, managing, and using
vendored MCP servers from the BioinfoMCP project using testcontainers.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
)
from DeepResearch.src.tools.bioinformatics.bcftools_server import BCFtoolsServer
from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer
from DeepResearch.src.tools.bioinformatics.bowtie2_server import Bowtie2Server
from DeepResearch.src.tools.bioinformatics.busco_server import BUSCOServer
from DeepResearch.src.tools.bioinformatics.cutadapt_server import CutadaptServer
from DeepResearch.src.tools.bioinformatics.deeptools_server import DeeptoolsServer
from DeepResearch.src.tools.bioinformatics.fastp_server import FastpServer
from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer
from DeepResearch.src.tools.bioinformatics.featurecounts_server import (
    FeatureCountsServer,
)
from DeepResearch.src.tools.bioinformatics.flye_server import FlyeServer
from DeepResearch.src.tools.bioinformatics.freebayes_server import FreeBayesServer
from DeepResearch.src.tools.bioinformatics.hisat2_server import HISAT2Server
from DeepResearch.src.tools.bioinformatics.kallisto_server import KallistoServer
from DeepResearch.src.tools.bioinformatics.macs3_server import MACS3Server
from DeepResearch.src.tools.bioinformatics.meme_server import MEMEServer
from DeepResearch.src.tools.bioinformatics.minimap2_server import Minimap2Server
from DeepResearch.src.tools.bioinformatics.multiqc_server import MultiQCServer
from DeepResearch.src.tools.bioinformatics.qualimap_server import QualimapServer
from DeepResearch.src.tools.bioinformatics.salmon_server import SalmonServer
from DeepResearch.src.tools.bioinformatics.samtools_server import SamtoolsServer
from DeepResearch.src.tools.bioinformatics.seqtk_server import SeqtkServer
from DeepResearch.src.tools.bioinformatics.star_server import STARServer
from DeepResearch.src.tools.bioinformatics.stringtie_server import StringTieServer
from DeepResearch.src.tools.bioinformatics.trimgalore_server import TrimGaloreServer

from .base import ExecutionResult, ToolRunner, ToolSpec, registry


# Placeholder classes for servers not yet implemented
class BWAServer:
    """Placeholder for BWA server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        msg = "BWA server not yet implemented"
        raise NotImplementedError(msg)


class TopHatServer:
    """Placeholder for TopHat server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        msg = "TopHat server not yet implemented"
        raise NotImplementedError(msg)


class HTSeqServer:
    """Placeholder for HTSeq server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        msg = "HTSeq server not yet implemented"
        raise NotImplementedError(msg)


class PicardServer:
    """Placeholder for Picard server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        msg = "Picard server not yet implemented"
        raise NotImplementedError(msg)


class HOMERServer:
    """Placeholder for HOMER server - not yet implemented."""

    def list_tools(self) -> list[str]:
        return []

    def run_tool(self, tool_name: str, **kwargs) -> Any:
        msg = "HOMER server not yet implemented"
        raise NotImplementedError(msg)


class MCPServerManager:
    """Manager for vendored MCP servers."""

    def __init__(self):
        self.deployments: dict[str, MCPServerDeployment] = {}
        self.servers = {
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

    def get_server(self, server_name: str):
        """Get a server instance by name."""
        return self.servers.get(server_name)

    def list_servers(self) -> list[str]:
        """List all available servers."""
        return list(self.servers.keys())

    async def deploy_server(
        self, server_name: str, config: MCPServerConfig
    ) -> MCPServerDeployment:
        """Deploy an MCP server using testcontainers."""
        server_class = self.get_server(server_name)
        if not server_class:
            return MCPServerDeployment(
                server_name=server_name,
                status=MCPServerStatus.FAILED,
                error_message=f"Server {server_name} not found",
            )

        try:
            server = server_class(config)
            deployment = await server.deploy_with_testcontainers()
            self.deployments[server_name] = deployment
            return deployment

        except Exception as e:
            return MCPServerDeployment(
                server_name=server_name,
                status=MCPServerStatus.FAILED,
                error_message=str(e),
            )

    def stop_server(self, server_name: str) -> bool:
        """Stop a deployed MCP server."""
        if server_name in self.deployments:
            deployment = self.deployments[server_name]
            deployment.status = "stopped"
            return True
        return False


# Global server manager instance
mcp_server_manager = MCPServerManager()


@dataclass
class MCPServerDeploymentTool(ToolRunner):
    """Tool for deploying MCP servers using testcontainers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mcp_server_deploy",
                description="Deploy a vendored MCP server using testcontainers",
                inputs={
                    "server_name": "TEXT",
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

            # Get server instance
            server = mcp_server_manager.get_server(server_name)
            if not server:
                return ExecutionResult(
                    success=False,
                    error=f"Server '{server_name}' not found. Available servers: {', '.join(mcp_server_manager.list_servers())}",
                )

            # Create configuration
            config = MCPServerConfig(
                server_name=server_name,
                container_image=params.get("container_image", "python:3.11-slim"),
                environment_variables=params.get("environment_variables", {}),
                volumes=params.get("volumes", {}),
                ports=params.get("ports", {}),
            )

            # Deploy server
            deployment = asyncio.run(
                mcp_server_manager.deploy_server(server_name, config)
            )

            return ExecutionResult(
                success=True,
                data={
                    "deployment": deployment.model_dump(),
                    "container_id": deployment.container_id or "",
                    "status": deployment.status,
                    "success": deployment.status == "running",
                    "error": deployment.error_message or "",
                },
            )

        except Exception as e:
            return ExecutionResult(success=False, error=f"Deployment failed: {e!s}")


@dataclass
class MCPServerListTool(ToolRunner):
    """Tool for listing available MCP servers."""

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="mcp_server_list",
                description="List all available vendored MCP servers",
                inputs={},
                outputs={
                    "servers": "JSON",
                    "count": "INTEGER",
                    "success": "BOOLEAN",
                },
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        """List available MCP servers."""
        try:
            servers = mcp_server_manager.list_servers()

            server_details = []
            for server_name in servers:
                server = mcp_server_manager.get_server(server_name)
                if server:
                    server_details.append(
                        {
                            "name": server.name,
                            "description": server.description,
                            "version": server.version,
                            "tools": server.list_tools(),
                        }
                    )

            return ExecutionResult(
                success=True,
                data={
                    "servers": server_details,
                    "count": len(servers),
                    "success": True,
                },
            )

        except Exception as e:
            return ExecutionResult(
                success=False, error=f"Failed to list servers: {e!s}"
            )


@dataclass
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
                },
                outputs={
                    "result": "JSON",
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

            if not server_name:
                return ExecutionResult(success=False, error="Server name is required")

            if not tool_name:
                return ExecutionResult(success=False, error="Tool name is required")

            # Get server instance
            server = mcp_server_manager.get_server(server_name)
            if not server:
                return ExecutionResult(
                    success=False, error=f"Server '{server_name}' not found"
                )

            # Check if tool exists
            available_tools = server.list_tools()
            if tool_name not in available_tools:
                return ExecutionResult(
                    success=False,
                    error=f"Tool '{tool_name}' not found on server '{server_name}'. Available tools: {', '.join(available_tools)}",
                )

            # Execute tool
            result = server.execute_tool(tool_name, **parameters)

            return ExecutionResult(
                success=True,
                data={
                    "result": result,
                    "success": True,
                    "error": "",
                },
            )

        except Exception as e:
            return ExecutionResult(success=False, error=f"Tool execution failed: {e!s}")


@dataclass
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
                deployment = mcp_server_manager.deployments.get(server_name)
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
            deployments = []
            for name, deployment in mcp_server_manager.deployments.items():
                deployments.append(
                    {
                        "server_name": name,
                        "status": deployment.status,
                        "container_id": deployment.container_id or "",
                    }
                )

            return ExecutionResult(
                success=True,
                data={
                    "status": "multiple",
                    "deployments": deployments,
                    "count": len(deployments),
                    "success": True,
                },
            )

        except Exception as e:
            return ExecutionResult(success=False, error=f"Status check failed: {e!s}")


@dataclass
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
            success = mcp_server_manager.stop_server(server_name)

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
            return ExecutionResult(success=False, error=f"Stop failed: {e!s}")


# Pydantic AI Tool Functions
def mcp_server_deploy_tool(ctx: Any) -> str:
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
        container_image: Docker image to use (optional, default: python:3.11-slim)
        environment_variables: Environment variables for the container (optional)
        volumes: Volume mounts (host_path:container_path) (optional)
        ports: Port mappings (container_port:host_port) (optional)

    Returns:
        JSON string containing deployment information
    """
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    tool = MCPServerDeploymentTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Deployment failed: {result.error}"


def mcp_server_list_tool(ctx: Any) -> str:
    """
    List all available vendored MCP servers.

    This tool returns information about all vendored BioinfoMCP servers
    that can be deployed using testcontainers.

    Returns:
        JSON string containing list of available servers
    """
    tool = MCPServerListTool()
    result = tool.run({})

    if result.success:
        return json.dumps(result.data)
    return f"List failed: {result.error}"


def mcp_server_execute_tool(ctx: Any) -> str:
    """
    Execute a tool on a deployed MCP server.

    This tool allows you to execute specific tools on deployed MCP servers.
    The servers must be deployed first using the mcp_server_deploy tool.

    Args:
        server_name: Name of the deployed server
        tool_name: Name of the tool to execute
        parameters: Parameters for the tool execution

    Returns:
        JSON string containing tool execution results
    """
    params = ctx.deps if isinstance(ctx.deps, dict) else {}

    tool = MCPServerExecuteTool()
    result = tool.run(params)

    if result.success:
        return json.dumps(result.data)
    return f"Execution failed: {result.error}"


def mcp_server_status_tool(ctx: Any) -> str:
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


def mcp_server_stop_tool(ctx: Any) -> str:
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
def register_mcp_server_tools():
    """Register MCP server tools with the global registry."""
    registry.register("mcp_server_deploy", MCPServerDeploymentTool)
    registry.register("mcp_server_list", MCPServerListTool)
    registry.register("mcp_server_execute", MCPServerExecuteTool)
    registry.register("mcp_server_status", MCPServerStatusTool)
    registry.register("mcp_server_stop", MCPServerStopTool)


# Auto-register when module is imported
register_mcp_server_tools()
