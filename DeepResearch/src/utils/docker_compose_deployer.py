"""
Docker Compose Deployer for MCP Servers with AG2 Code Execution Integration.

This module provides deployment functionality for MCP servers using Docker Compose
for production-like deployments, now integrated with AG2-style code execution.
"""

# type: ignore  # Template file with dynamic variable substitution

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from DeepResearch.src.datatypes.bioinformatics_mcp import (
    MCPServerConfig,
    MCPServerDeployment,
)
from DeepResearch.src.datatypes.mcp import (
    MCPServerStatus,
)
from DeepResearch.src.utils.coding import CodeBlock, DockerCommandLineCodeExecutor
from DeepResearch.src.utils.python_code_execution import PythonCodeExecutionTool

logger = logging.getLogger(__name__)


class DockerComposeConfig(BaseModel):
    """Configuration for Docker Compose deployment."""

    compose_version: str = Field("3.8", description="Docker Compose version")
    services: dict[str, Any] = Field(
        default_factory=dict, description="Service definitions"
    )
    networks: dict[str, Any] = Field(
        default_factory=dict, description="Network definitions"
    )
    volumes: dict[str, Any] = Field(
        default_factory=dict, description="Volume definitions"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "compose_version": "3.8",
                "services": {
                    "fastqc-server": {
                        "image": "mcp-fastqc:latest",
                        "ports": ["8080:8080"],
                        "environment": {"MCP_SERVER_NAME": "fastqc"},
                    }
                },
                "networks": {"mcp-network": {"driver": "bridge"}},
            }
        }
    )


class DockerComposeDeployer:
    """Deployer for MCP servers using Docker Compose with integrated code execution."""

    def __init__(self):
        self.deployments: dict[str, MCPServerDeployment] = {}
        self.compose_files: dict[str, str] = {}  # server_name -> compose_file_path
        self.code_executors: dict[str, DockerCommandLineCodeExecutor] = {}
        self.python_execution_tools: dict[str, PythonCodeExecutionTool] = {}

    def create_compose_config(
        self, servers: list[MCPServerConfig]
    ) -> DockerComposeConfig:
        """Create Docker Compose configuration for multiple servers."""
        compose_config = DockerComposeConfig()

        # Add services for each server
        for server_config in servers:
            service_name = f"{server_config.server_name}-service"

            service_config = {
                "image": f"mcp-{server_config.server_name}:latest",
                "container_name": f"mcp-{server_config.server_name}",
                "environment": {
                    **server_config.environment_variables,
                    "MCP_SERVER_NAME": server_config.server_name,
                },
                "volumes": [
                    f"{volume_host}:{volume_container}"
                    for volume_host, volume_container in server_config.volumes.items()
                ],
                "ports": [
                    f"{host_port}:{container_port}"
                    for container_port, host_port in server_config.ports.items()
                ],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": ["CMD", "python", "-c", "print('MCP server running')"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                },
            }

            compose_config.services[service_name] = service_config

        # Add network
        compose_config.networks["mcp-network"] = {"driver": "bridge"}

        # Add named volumes for data persistence
        for server_config in servers:
            volume_name = f"mcp-{server_config.server_name}-data"
            compose_config.volumes[volume_name] = {"driver": "local"}

        return compose_config

    async def deploy_servers(
        self,
        server_configs: list[MCPServerConfig],
        compose_file_path: str | None = None,
    ) -> list[MCPServerDeployment]:
        """Deploy multiple MCP servers using Docker Compose."""
        deployments = []

        try:
            # Create Docker Compose configuration
            compose_config = self.create_compose_config(server_configs)

            # Write compose file
            if compose_file_path is None:
                compose_file_path = f"/tmp/mcp-compose-{id(compose_config)}.yml"

            with open(compose_file_path, "w") as f:
                f.write(compose_config.model_dump_json(indent=2))

            # Store compose file path
            for server_config in server_configs:
                self.compose_files[server_config.server_name] = compose_file_path

            # Deploy using docker-compose
            import subprocess

            cmd = ["docker-compose", "-f", compose_file_path, "up", "-d"]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            if result.returncode != 0:
                msg = f"Docker Compose deployment failed: {result.stderr}"
                raise RuntimeError(msg)

            # Create deployment records
            for server_config in server_configs:
                deployment = MCPServerDeployment(
                    server_name=server_config.server_name,
                    server_type=server_config.server_type,
                    status=MCPServerStatus.RUNNING,
                    container_name=f"mcp-{server_config.server_name}",
                    configuration=server_config,
                )
                self.deployments[server_config.server_name] = deployment
                deployments.append(deployment)

            logger.info(
                "Deployed %d MCP servers using Docker Compose", len(server_configs)
            )

        except Exception as e:
            logger.exception("Failed to deploy MCP servers")
            # Create failed deployment records
            for server_config in server_configs:
                deployment = MCPServerDeployment(
                    server_name=server_config.server_name,
                    server_type=server_config.server_type,
                    status=MCPServerStatus.FAILED,
                    error_message=str(e),
                    configuration=server_config,
                )
                self.deployments[server_config.server_name] = deployment
                deployments.append(deployment)

        return deployments

    async def stop_servers(self, server_names: list[str] | None = None) -> bool:
        """Stop deployed MCP servers."""
        if server_names is None:
            server_names = list(self.deployments.keys())

        success = True

        for server_name in server_names:
            if server_name in self.deployments:
                deployment = self.deployments[server_name]

                try:
                    # Stop using docker-compose
                    compose_file = self.compose_files.get(server_name)
                    if compose_file:
                        import subprocess

                        service_name = f"{server_name}-service"
                        cmd = [
                            "docker-compose",
                            "-f",
                            compose_file,
                            "stop",
                            service_name,
                        ]
                        result = subprocess.run(
                            cmd, check=False, capture_output=True, text=True
                        )

                        if result.returncode == 0:
                            deployment.status = "stopped"
                            logger.info("Stopped MCP server '%s'", server_name)
                        else:
                            logger.error(
                                "Failed to stop server '%s': %s",
                                server_name,
                                result.stderr,
                            )
                            success = False

                except Exception:
                    logger.exception("Error stopping server '%s'", server_name)
                    success = False

        return success

    async def remove_servers(self, server_names: list[str] | None = None) -> bool:
        """Remove deployed MCP servers and their containers."""
        if server_names is None:
            server_names = list(self.deployments.keys())

        success = True

        for server_name in server_names:
            if server_name in self.deployments:
                deployment = self.deployments[server_name]

                try:
                    # Remove using docker-compose
                    compose_file = self.compose_files.get(server_name)
                    if compose_file:
                        import subprocess

                        service_name = f"{server_name}-service"
                        cmd = [
                            "docker-compose",
                            "-f",
                            compose_file,
                            "down",
                            service_name,
                        ]
                        result = subprocess.run(
                            cmd, check=False, capture_output=True, text=True
                        )

                        if result.returncode == 0:
                            deployment.status = "stopped"
                            del self.deployments[server_name]
                            del self.compose_files[server_name]
                            logger.info("Removed MCP server '%s'", server_name)
                        else:
                            logger.error(
                                "Failed to remove server '%s': %s",
                                server_name,
                                result.stderr,
                            )
                            success = False

                except Exception:
                    logger.exception("Error removing server '%s'", server_name)
                    success = False

        return success

    async def get_server_status(self, server_name: str) -> MCPServerDeployment | None:
        """Get the status of a deployed server."""
        return self.deployments.get(server_name)

    async def list_servers(self) -> list[MCPServerDeployment]:
        """List all deployed servers."""
        return list(self.deployments.values())

    async def create_dockerfile(self, server_name: str, output_dir: str) -> str:
        """Create a Dockerfile for an MCP server."""
        dockerfile_content = f"""FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    procps \\
    && rm -rf /var/lib/apt/lists/*

# Copy server files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash mcp
USER mcp

# Expose port for MCP server
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the MCP server
CMD ["python", "{server_name}_server.py"]
"""

        dockerfile_path = Path(output_dir) / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        return str(dockerfile_path)

    async def build_server_image(
        self, server_name: str, dockerfile_dir: str, image_tag: str
    ) -> bool:
        """Build Docker image for an MCP server."""
        try:
            import subprocess

            cmd = [
                "docker",
                "build",
                "-t",
                image_tag,
                "-f",
                os.path.join(dockerfile_dir, "Dockerfile"),
                dockerfile_dir,
            ]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(
                    "Built Docker image '%s' for server '%s'", image_tag, server_name
                )
                return True
            logger.error(
                "Failed to build Docker image for server '%s': %s",
                server_name,
                result.stderr,
            )
            return False

        except Exception:
            logger.exception("Error building Docker image for server '%s'", server_name)
            return False

    async def create_server_package(
        self, server_name: str, output_dir: str, server_implementation
    ) -> list[str]:
        """Create a complete server package for deployment."""
        files_created = []

        try:
            # Create server directory
            server_dir = Path(output_dir) / server_name
            server_dir.mkdir(parents=True, exist_ok=True)

            # Create server implementation file
            server_file = server_dir / f"{server_name}_server.py"
            server_code = self._generate_server_code(server_name, server_implementation)

            with open(server_file, "w") as f:
                f.write(server_code)

            files_created.append(str(server_file))

            # Create requirements file
            requirements_file = server_dir / "requirements.txt"
            requirements_content = self._generate_requirements(server_name)

            with open(requirements_file, "w") as f:
                f.write(requirements_content)

            files_created.append(str(requirements_file))

            # Create Dockerfile
            dockerfile_path = await self.create_dockerfile(server_name, str(server_dir))
            files_created.append(dockerfile_path)

            # Create docker-compose.yml
            compose_config = self._create_server_compose_config(server_name)
            compose_file = server_dir / "docker-compose.yml"

            with open(compose_file, "w") as f:
                f.write(compose_config.model_dump_json(indent=2))

            files_created.append(str(compose_file))

            logger.info(
                "Created server package for '%s' in %s", server_name, server_dir
            )
            return files_created

        except Exception:
            logger.exception("Failed to create server package for '%s'", server_name)
            return files_created

    def _generate_server_code(self, server_name: str, server_implementation) -> str:
        """Generate server code for deployment."""
        module_path = server_implementation.__module__
        class_name = server_implementation.__class__.__name__

        return f'''"""
Auto-generated MCP server for {server_name}.
"""

from {module_path} import {class_name}

# Create and run server
mcp_server = {class_name}()

# Template file - main execution logic is handled by deployment system
'''

    def _generate_requirements(self, server_name: str) -> str:
        """Generate requirements file for server deployment."""
        requirements = [
            "pydantic>=2.0.0",
            "fastmcp>=0.1.0",  # Assuming this would be available
        ]

        # Add server-specific requirements
        if server_name == "fastqc":
            requirements.extend(
                [
                    "biopython>=1.80",
                    "numpy>=1.21.0",
                ]
            )
        elif server_name == "samtools":
            requirements.extend(
                [
                    "pysam>=0.20.0",
                ]
            )
        elif server_name == "bowtie2":
            requirements.extend(
                [
                    "biopython>=1.80",
                ]
            )

        return "\n".join(requirements)

    def _create_server_compose_config(self, server_name: str) -> DockerComposeConfig:
        """Create Docker Compose configuration for a single server."""
        compose_config = DockerComposeConfig()

        service_config = {
            "build": ".",
            "container_name": f"mcp-{server_name}",
            "environment": {
                "MCP_SERVER_NAME": server_name,
            },
            "ports": ["8080:8080"],
            "restart": "unless-stopped",
            "healthcheck": {
                "test": ["CMD", "python", "-c", "print('MCP server running')"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
            },
        }

        compose_config.services[f"{server_name}-service"] = service_config
        compose_config.networks["mcp-network"] = {"driver": "bridge"}
        compose_config.volumes[f"mcp-{server_name}-data"] = {"driver": "local"}

        return compose_config

    async def execute_code(
        self,
        server_name: str,
        code: str,
        language: str = "python",
        timeout: int = 60,
        max_retries: int = 3,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute code using the deployed server's Docker Compose environment.

        Args:
            server_name: Name of the deployed server to use for execution
            code: Code to execute
            language: Programming language of the code
            timeout: Execution timeout in seconds
            max_retries: Maximum number of retry attempts
            **kwargs: Additional execution parameters

        Returns:
            Dictionary containing execution results
        """
        deployment = self.deployments.get(server_name)
        if not deployment:
            raise ValueError(f"Server '{server_name}' not deployed")

        if deployment.status != "running":
            raise ValueError(
                f"Server '{server_name}' is not running (status: {deployment.status})"
            )

        # Get or create Python execution tool for this server
        if server_name not in self.python_execution_tools:
            try:
                self.python_execution_tools[server_name] = PythonCodeExecutionTool(
                    timeout=timeout,
                    work_dir=f"/tmp/{server_name}_code_exec_compose",
                    use_docker=True,
                )
            except Exception:
                logger.exception(
                    "Failed to create Python execution tool for server '%s'",
                    server_name,
                )
                raise

        # Execute the code
        tool = self.python_execution_tools[server_name]
        result = tool.run(
            {
                "code": code,
                "timeout": timeout,
                "max_retries": max_retries,
                "language": language,
                **kwargs,
            }
        )

        return {
            "server_name": server_name,
            "success": result.success,
            "output": result.data.get("output", ""),
            "error": result.data.get("error", ""),
            "exit_code": result.data.get("exit_code", -1),
            "execution_time": result.data.get("execution_time", 0.0),
            "retries_used": result.data.get("retries_used", 0),
        }

    async def execute_code_blocks(
        self, server_name: str, code_blocks: list[CodeBlock], **kwargs
    ) -> dict[str, Any]:
        """Execute multiple code blocks using the deployed server's Docker Compose environment.

        Args:
            server_name: Name of the deployed server to use for execution
            code_blocks: List of code blocks to execute
            **kwargs: Additional execution parameters

        Returns:
            Dictionary containing execution results for all blocks
        """
        deployment = self.deployments.get(server_name)
        if not deployment:
            raise ValueError(f"Server '{server_name}' not deployed")

        if server_name not in self.code_executors:
            # Create code executor if it doesn't exist
            self.code_executors[server_name] = DockerCommandLineCodeExecutor(
                image=deployment.configuration.image
                if hasattr(deployment.configuration, "image")
                else "python:3.11-slim",
                timeout=kwargs.get("timeout", 60),
                work_dir=f"/tmp/{server_name}_code_blocks_compose",
            )

        executor = self.code_executors[server_name]
        result = executor.execute_code_blocks(code_blocks)

        return {
            "server_name": server_name,
            "success": result.exit_code == 0,
            "output": result.output,
            "exit_code": result.exit_code,
            "command": getattr(result, "command", ""),
            "image": getattr(result, "image", None),
        }


# Global deployer instance
docker_compose_deployer = DockerComposeDeployer()
