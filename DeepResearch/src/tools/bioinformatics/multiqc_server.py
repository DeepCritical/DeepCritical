"""
MultiQC MCP Server - Vendored BioinfoMCP server for report generation.

This module implements a strongly-typed MCP server for MultiQC, a tool for
aggregating results from bioinformatics tools into a single report, using
Pydantic AI patterns and testcontainers deployment.

Based on the BioinfoMCP example implementation with full feature set integration.
"""

from __future__ import annotations

import asyncio
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase, mcp_tool
from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
    MCPToolSpec,
)


class MultiQCServer(MCPServerBase):
    """MCP Server for MultiQC report generation tool with Pydantic AI integration."""

    def __init__(self, config: MCPServerConfig | None = None):
        if config is None:
            config = MCPServerConfig(
                server_name="multiqc-server",
                server_type=MCPServerType.CUSTOM,
                container_image="mcp-multiqc:latest",  # Match example Docker image
                environment_variables={
                    "MULTIQC_VERSION": "1.29"
                },  # Updated to match example version
                capabilities=["report_generation", "quality_control", "visualization"],
                working_directory="/app/workspace",
            )
        super().__init__(config)

    @mcp_tool(
        MCPToolSpec(
            name="multiqc_run",
            description="Generate MultiQC report from bioinformatics tool outputs",
            inputs={
                "analysis_directory": "Optional[Path]",
                "outdir": "Optional[Path]",
                "filename": "str",
                "force": "bool",
                "config_file": "Optional[Path]",
                "data_dir": "Optional[Path]",
                "no_data_dir": "bool",
                "no_report": "bool",
                "no_plots": "bool",
                "no_config": "bool",
                "no_title": "bool",
                "title": "Optional[str]",
                "ignore_dirs": "Optional[str]",
                "ignore_samples": "Optional[str]",
                "exclude_modules": "Optional[str]",
                "include_modules": "Optional[str]",
                "verbose": "bool",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
                "success": "bool",
                "error": "Optional[str]",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Generate MultiQC report from analysis results",
                    "parameters": {
                        "analysis_directory": "/data/analysis_results",
                        "outdir": "/data/reports",
                        "filename": "multiqc_report.html",
                        "title": "NGS Analysis Report",
                        "force": True,
                    },
                },
                {
                    "description": "Generate MultiQC report with custom configuration",
                    "parameters": {
                        "analysis_directory": "/workspace/analysis",
                        "outdir": "/workspace/output",
                        "filename": "custom_report.html",
                        "config_file": "/workspace/multiqc_config.yaml",
                        "title": "Custom MultiQC Report",
                        "verbose": True,
                    },
                },
            ],
        )
    )
    def multiqc_run(
        self,
        analysis_directory: Path | None = None,
        outdir: Path | None = None,
        filename: str = "multiqc_report.html",
        force: bool = False,
        config_file: Path | None = None,
        data_dir: Path | None = None,
        no_data_dir: bool = False,
        no_report: bool = False,
        no_plots: bool = False,
        no_config: bool = False,
        no_title: bool = False,
        title: str | None = None,
        ignore_dirs: str | None = None,
        ignore_samples: str | None = None,
        exclude_modules: str | None = None,
        include_modules: str | None = None,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Generate MultiQC report from bioinformatics tool outputs.

        This tool aggregates results from multiple bioinformatics tools into
        a single, comprehensive HTML report with interactive plots and tables.

        Args:
            analysis_directory: Directory to scan for analysis results (default: current directory)
            outdir: Output directory for the MultiQC report (default: current directory)
            filename: Name of the output report file (default: multiqc_report.html)
            force: Overwrite existing output files
            config_file: Path to a custom MultiQC config file
            data_dir: Path to a directory containing MultiQC data files
            no_data_dir: Do not use the MultiQC data directory
            no_report: Do not generate the HTML report
            no_plots: Do not generate plots
            no_config: Do not load config files
            no_title: Do not add a title to the report
            title: Custom title for the report
            ignore_dirs: Comma-separated list of directories to ignore
            ignore_samples: Comma-separated list of samples to ignore
            exclude_modules: Comma-separated list of modules to exclude
            include_modules: Comma-separated list of modules to include
            verbose: Enable verbose output

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and success status
        """
        # Validate paths
        if analysis_directory is not None:
            if not analysis_directory.exists() or not analysis_directory.is_dir():
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Analysis directory '{analysis_directory}' does not exist or is not a directory.",
                    "output_files": [],
                    "success": False,
                    "error": f"Analysis directory not found: {analysis_directory}",
                }
        else:
            analysis_directory = Path.cwd()

        if outdir is not None:
            if not outdir.exists():
                outdir.mkdir(parents=True, exist_ok=True)
        else:
            outdir = Path.cwd()

        if config_file is not None and not config_file.exists():
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Config file '{config_file}' does not exist.",
                "output_files": [],
                "success": False,
                "error": f"Config file not found: {config_file}",
            }

        if data_dir is not None and not data_dir.exists():
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Data directory '{data_dir}' does not exist.",
                "output_files": [],
                "success": False,
                "error": f"Data directory not found: {data_dir}",
            }

        # Build command
        cmd = ["multiqc"]

        # Add analysis directory
        cmd.append(str(analysis_directory))

        # Output directory
        cmd.extend(["-o", str(outdir)])

        # Filename
        if filename:
            cmd.extend(["-n", filename])

        # Flags
        if force:
            cmd.append("-f")
        if config_file:
            cmd.extend(["-c", str(config_file)])
        if data_dir:
            cmd.extend(["--data-dir", str(data_dir)])
        if no_data_dir:
            cmd.append("--no-data-dir")
        if no_report:
            cmd.append("--no-report")
        if no_plots:
            cmd.append("--no-plots")
        if no_config:
            cmd.append("--no-config")
        if no_title:
            cmd.append("--no-title")
        if title:
            cmd.extend(["-t", title])
        if ignore_dirs:
            cmd.extend(["--ignore-dir", ignore_dirs])
        if ignore_samples:
            cmd.extend(["--ignore-samples", ignore_samples])
        if exclude_modules:
            cmd.extend(["--exclude", exclude_modules])
        if include_modules:
            cmd.extend(["--include", include_modules])
        if verbose:
            cmd.append("-v")

        # Execute MultiQC report generation
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Collect output files: the main report file in outdir
            output_files = []
            output_report = outdir / filename
            if output_report.exists():
                output_files.append(str(output_report.resolve()))

            # Also check for data directory if it was created
            if not no_data_dir:
                data_dir_path = outdir / f"{Path(filename).stem}_data"
                if data_dir_path.exists():
                    output_files.append(str(data_dir_path.resolve()))

            success = result.returncode == 0
            error = (
                None
                if success
                else f"MultiQC failed with exit code {result.returncode}"
            )

            return {
                "command_executed": " ".join(shlex.quote(c) for c in cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "success": success,
                "error": error,
            }

        except FileNotFoundError:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "MultiQC not found in PATH",
                "output_files": [],
                "success": False,
                "error": "MultiQC not found in PATH",
            }
        except Exception as e:
            return {
                "command_executed": (
                    " ".join(shlex.quote(c) for c in cmd) if "cmd" in locals() else ""
                ),
                "stdout": "",
                "stderr": str(e),
                "output_files": [],
                "success": False,
                "error": str(e),
            }

    @mcp_tool(
        MCPToolSpec(
            name="multiqc_modules",
            description="List available MultiQC modules",
            inputs={
                "search_pattern": "Optional[str]",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "modules": "List[str]",
                "success": "bool",
                "error": "Optional[str]",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "List all available MultiQC modules",
                    "parameters": {},
                },
                {
                    "description": "Search for specific MultiQC modules",
                    "parameters": {
                        "search_pattern": "fastqc",
                    },
                },
            ],
        )
    )
    def multiqc_modules(
        self,
        search_pattern: str | None = None,
    ) -> dict[str, Any]:
        """
        List available MultiQC modules.

        This tool lists all available MultiQC modules that can be used
        to generate reports from different bioinformatics tools.

        Args:
            search_pattern: Optional pattern to search for specific modules

        Returns:
            Dictionary containing command executed, stdout, stderr, modules list, and success status
        """
        # Build command
        cmd = ["multiqc", "--list-modules"]

        if search_pattern:
            cmd.extend(["--search", search_pattern])

        try:
            # Execute MultiQC modules list
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Parse modules from output
            modules = []
            try:
                lines = result.stdout.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("Available modules:"):
                        modules.append(line)
            except Exception:
                pass

            success = result.returncode == 0
            error = (
                None
                if success
                else f"MultiQC failed with exit code {result.returncode}"
            )

            return {
                "command_executed": " ".join(shlex.quote(c) for c in cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "modules": modules,
                "success": success,
                "error": error,
            }

        except FileNotFoundError:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "MultiQC not found in PATH",
                "modules": [],
                "success": False,
                "error": "MultiQC not found in PATH",
            }
        except Exception as e:
            return {
                "command_executed": (
                    " ".join(shlex.quote(c) for c in cmd) if "cmd" in locals() else ""
                ),
                "stdout": "",
                "stderr": str(e),
                "modules": [],
                "success": False,
                "error": str(e),
            }

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy MultiQC server using testcontainers."""
        try:
            from testcontainers.core.container import DockerContainer

            # Create container with the correct image matching the example
            container = DockerContainer(self.config.container_image)
            container.with_name(f"mcp-multiqc-server-{id(self)}")

            # Mount workspace and output directories like the example
            if (
                hasattr(self.config, "working_directory")
                and self.config.working_directory
            ):
                workspace_path = Path(self.config.working_directory)
                workspace_path.mkdir(parents=True, exist_ok=True)
                container.with_volume_mapping(
                    str(workspace_path), "/app/workspace", mode="rw"
                )

            output_path = Path("/tmp/multiqc_output")  # Default output path
            output_path.mkdir(parents=True, exist_ok=True)
            container.with_volume_mapping(str(output_path), "/app/output", mode="rw")

            # Set environment variables
            for key, value in self.config.environment_variables.items():
                container.with_env(key, value)

            # Start container
            container.start()

            # Wait for container to be ready
            container.reload()
            max_attempts = 30
            for _attempt in range(max_attempts):
                if container.status == "running":
                    break
                await asyncio.sleep(0.5)
                container.reload()

            if container.status != "running":
                msg = f"Container failed to start after {max_attempts} attempts"
                raise RuntimeError(msg)

            # Store container info
            self.container_id = container.get_wrapped_container().id
            self.container_name = container.get_wrapped_container().name

            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                container_id=self.container_id,
                container_name=self.container_name,
                status=MCPServerStatus.RUNNING,
                created_at=datetime.now(),
                started_at=datetime.now(),
                tools_available=self.list_tools(),
                configuration=self.config,
            )

        except Exception as e:
            self.logger.exception("Failed to deploy MultiQC server")
            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                status=MCPServerStatus.FAILED,
                error_message=str(e),
                configuration=self.config,
            )

    async def stop_with_testcontainers(self) -> bool:
        """Stop MultiQC server deployed with testcontainers."""
        try:
            if self.container_id:
                from testcontainers.core.container import DockerContainer

                container = DockerContainer(self.container_id)
                container.stop()

                self.container_id = None
                self.container_name = None

                return True
            return False
        except Exception:
            self.logger.exception("Failed to stop MultiQC server")
            return False

    def get_server_info(self) -> dict[str, Any]:
        """Get information about this MultiQC server."""
        return {
            "name": self.name,
            "type": "multiqc",
            "version": self.config.environment_variables.get("MULTIQC_VERSION", "1.29"),
            "description": "MultiQC report generation server with Pydantic AI integration",
            "tools": self.list_tools(),
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": "running" if self.container_id else "stopped",
            "pydantic_ai_enabled": self.pydantic_ai_agent is not None,
            "session_active": self.session is not None,
        }
