"""
Gunzip MCP Server - Vendored BioinfoMCP server for gzip/gunzip compression utilities.

This module implements a strongly-typed MCP server for gzip/gunzip, providing
bioinformatics-focused compression and decompression capabilities for FASTQ,
genome, and other genomic data files commonly distributed in gzip format.

Capabilities:
- Decompress .gz files (gunzip)
- Compress files to .gz format (gzip)
- Test compressed file integrity (gzip -t)
- List compression statistics (gzip -l)

Scientific Use Cases:
- Decompress FASTQ.gz files for analysis (99% of FASTQ files distributed as .gz)
- Decompress reference genome archives
- Compress pipeline outputs for efficient storage
- Validate data integrity before processing
"""

from __future__ import annotations

import shutil
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


class GunzipServer(MCPServerBase):
    """MCP Server for gzip/gunzip compression utilities with Pydantic AI integration.

    Provides bioinformatics-focused compression and decompression capabilities
    for genomic data files commonly distributed in gzip format.

    Implementation Note:
    - Limit concurrent operations to 5-6 files to avoid overwhelming filesystem
    - gzip/gunzip stream data (safe for large 10GB+ genomic files)
    - Mock mode activates when gzip/gunzip not in PATH (CI compatibility)
    """

    def __init__(self, config: MCPServerConfig | None = None):
        """Initialize gunzip server with configuration.

        Args:
            config: Optional MCPServerConfig. If None, uses default config.
        """
        if config is None:
            config = MCPServerConfig(
                server_name="gunzip-server",
                server_type=MCPServerType.CUSTOM,
                container_image="python:3.11-slim",  # gzip v1.10 pre-installed
                environment_variables={
                    "GZIP_VERSION": "1.10",  # Debian 11 default
                },
                capabilities=[
                    "decompress",
                    "compress",
                    "test_integrity",
                    "list_info",
                    "stream_to_stdout",
                ],
                working_directory="/workspace",
            )
        super().__init__(config)

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run gunzip/gzip operation based on parameters.

        Args:
            params: Operation parameters including:
                - operation: str (decompress, compress, test, list)
                - input_file: str (path to input file)
                - output_dir: str (optional, output directory)
                - keep_original: bool (optional, -k flag)
                - to_stdout: bool (optional, -c flag)
                - force: bool (optional, -f flag)
                - compression_level: int (optional, 1-9 for compress)

        Returns:
            dict containing:
                - success: bool
                - command_executed: str
                - stdout: str
                - stderr: str
                - output_files: list[str]
                - exit_code: int
                - error: str (if success=False)
                - mock: bool (if using mock mode)
        """
        operation = params.get("operation")
        if not operation:
            return {
                "success": False,
                "error": "Missing 'operation' parameter",
            }

        # Map operation to method
        operation_methods = {
            "decompress": self.decompress,
            "compress": self.compress,
            "test": self.test_integrity,
            "list": self.list_info,
        }

        if operation not in operation_methods:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}. "
                f"Supported: {list(operation_methods.keys())}",
            }

        method = operation_methods[operation]

        # Prepare method arguments
        method_params = params.copy()
        method_params.pop("operation", None)  # Remove operation from params

        try:
            # Check if tool is available (for testing/development environments)
            tool_available = shutil.which("gzip") or shutil.which("gunzip")

            if not tool_available:
                # Return mock success result when tool not available
                return self._mock_operation(operation, method_params)

            # Call the appropriate method
            return method(**method_params)

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute {operation}: {e!s}",
            }

    @mcp_tool(
        MCPToolSpec(
            name="decompress",
            description="Decompress gzip-compressed files (.gz) for bioinformatics analysis",
            inputs={
                "input_file": "str - Path to .gz compressed file",
                "output_dir": "str - Output directory (optional)",
                "keep_original": "bool - Keep original .gz file (default: False)",
                "to_stdout": "bool - Write to stdout instead of file (default: False)",
                "force": "bool - Force overwrite existing files (default: False)",
            },
            outputs={
                "command_executed": "str - Shell command that was executed",
                "stdout": "str - Standard output",
                "stderr": "str - Standard error",
                "output_files": "List[str] - Paths to decompressed files",
                "exit_code": "int - Exit code (0 = success)",
                "success": "bool - Operation success status",
            },
            version="1.0.0",
            required_tools=["gunzip"],
            category="compression",
            server_type=MCPServerType.CUSTOM,
            command_template="gunzip [options] {input_file}",
            validation_rules={
                "input_file": {"type": "file_exists", "extensions": [".gz"]},
                "output_dir": {"type": "directory", "writable": True},
            },
            examples=[
                {
                    "description": "Decompress FASTQ.gz file",
                    "inputs": {
                        "input_file": "/data/sample.fastq.gz",
                        "output_dir": "/results/",
                    },
                    "outputs": {
                        "success": True,
                        "output_files": ["/results/sample.fastq"],
                    },
                },
            ],
        )
    )
    def decompress(
        self,
        input_file: str,
        output_dir: str | None = None,
        keep_original: bool = False,
        to_stdout: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Decompress gzip file.

        Args:
            input_file: Path to .gz compressed file
            output_dir: Output directory (gunzip decompresses in-place, so we copy first)
            keep_original: Keep original .gz file (-k flag)
            to_stdout: Write to stdout instead of file (-c flag)
            force: Force overwrite existing files (-f flag)

        Returns:
            dict with execution results
        """
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Handle output_dir (gunzip decompresses in-place, so we copy to output_dir first)
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Copy to output_dir, then decompress the copy
            working_file = output_path / input_path.name
            shutil.copy2(input_file, working_file)
            input_to_decompress = str(working_file)
        else:
            # Decompress in-place beside input file
            input_to_decompress = input_file

        # Build command
        cmd = self._build_command(
            binary="gunzip",
            input_file=input_to_decompress,
            keep_original=keep_original,
            to_stdout=to_stdout,
            force=force,
        )

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Determine output file(s)
            output_files = []
            if not to_stdout:
                # gunzip removes .gz extension
                decompressed_file = Path(input_to_decompress).with_suffix("")
                if decompressed_file.exists():
                    output_files.append(str(decompressed_file))

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
            }

        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout,
                "stderr": e.stderr,
                "output_files": [],
                "exit_code": e.returncode,
                "success": False,
                "error": f"gunzip execution failed: {e}",
            }

        except Exception as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": str(e),
            }

    @mcp_tool(
        MCPToolSpec(
            name="compress",
            description="Compress files using gzip for efficient storage",
            inputs={
                "input_file": "str - Path to file to compress",
                "output_dir": "str - Output directory (optional)",
                "keep_original": "bool - Keep original file (default: False)",
                "compression_level": "int - Compression level 1-9 (default: 6)",
                "force": "bool - Force overwrite existing files (default: False)",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
                "exit_code": "int",
                "success": "bool",
            },
            version="1.0.0",
            required_tools=["gzip"],
            category="compression",
            server_type=MCPServerType.CUSTOM,
            command_template="gzip [options] {input_file}",
            validation_rules={
                "input_file": {"type": "file_exists"},
                "compression_level": {"min": 1, "max": 9},
            },
        )
    )
    def compress(
        self,
        input_file: str,
        output_dir: str | None = None,
        keep_original: bool = False,
        compression_level: int = 6,
        force: bool = False,
    ) -> dict[str, Any]:
        """Compress file with gzip.

        Args:
            input_file: Path to file to compress
            output_dir: Output directory (gzip compresses in-place, so we copy first)
            keep_original: Keep original file (-k flag)
            compression_level: Compression level 1-9 (default: 6)
            force: Force overwrite existing files (-f flag)

        Returns:
            dict with execution results
        """
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Handle output_dir (gzip compresses in-place, so we copy to output_dir first)
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Copy to output_dir, then compress the copy
            working_file = output_path / input_path.name
            shutil.copy2(input_file, working_file)
            input_to_compress = str(working_file)
        else:
            # Compress in-place beside input file
            input_to_compress = input_file

        # Build command
        cmd = self._build_command(
            binary="gzip",
            input_file=input_to_compress,
            keep_original=keep_original,
            force=force,
            compression_level=compression_level,
        )

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Determine output file(s)
            output_files = []
            compressed_file = Path(input_to_compress).with_suffix(
                f"{input_path.suffix}.gz"
            )
            if compressed_file.exists():
                output_files.append(str(compressed_file))

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
            }

        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout,
                "stderr": e.stderr,
                "output_files": [],
                "exit_code": e.returncode,
                "success": False,
                "error": f"gzip execution failed: {e}",
            }

        except Exception as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": str(e),
            }

    @mcp_tool()
    def test_integrity(self, input_file: str) -> dict[str, Any]:
        """Test integrity of gzip file without decompressing.

        Args:
            input_file: Path to .gz file to test

        Returns:
            dict with success=True if file is valid, False otherwise
        """
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command: gzip -t
        cmd = ["gzip", "-t", input_file]

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": True,
            }

        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout,
                "stderr": e.stderr,
                "exit_code": e.returncode,
                "success": False,
                "error": "gzip -t failed: file may be corrupted",
            }

        except Exception as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "success": False,
                "error": str(e),
            }

    @mcp_tool()
    def list_info(self, input_file: str) -> dict[str, Any]:
        """List compression statistics for gzip file.

        Args:
            input_file: Path to .gz file

        Returns:
            dict with compression ratio and size info in stdout
        """
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command: gzip -l
        cmd = ["gzip", "-l", input_file]

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": True,
            }

        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout,
                "stderr": e.stderr,
                "exit_code": e.returncode,
                "success": False,
                "error": f"gzip -l failed: {e}",
            }

        except Exception as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "success": False,
                "error": str(e),
            }

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy the gunzip server using testcontainers."""
        try:
            from testcontainers.core.container import DockerContainer
            from testcontainers.core.waiting_utils import wait_for_logs

            # Create container
            container_name = f"mcp-{self.name}-{id(self)}"
            container = DockerContainer(self.config.container_image)
            container.with_name(container_name)

            # Set environment variables
            for key, value in self.config.environment_variables.items():
                container.with_env(key, value)

            # Add volume for data exchange
            container.with_volume_mapping("/tmp", "/tmp")

            # Start container
            container.start()

            # Wait for container to be ready
            wait_for_logs(container, "Python", timeout=30)

            # Update deployment info
            deployment = MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                container_id=container.get_wrapped_container().id,
                container_name=container_name,
                status=MCPServerStatus.RUNNING,
                created_at=datetime.now(),
                started_at=datetime.now(),
                tools_available=self.list_tools(),
                configuration=self.config,
            )

            self.container_id = container.get_wrapped_container().id
            self.container_name = container_name

            return deployment

        except Exception as e:
            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                status=MCPServerStatus.FAILED,
                error_message=str(e),
                configuration=self.config,
            )

    async def stop_with_testcontainers(self) -> bool:
        """Stop the gunzip server deployed with testcontainers."""
        if not self.container_id:
            return False

        try:
            from testcontainers.core.container import DockerContainer

            container = DockerContainer(self.container_id)
            container.stop()

            self.container_id = None
            self.container_name = None

            return True

        except Exception:
            self.logger.exception("Failed to stop container %s", self.container_id)
            return False

    def _build_command(
        self,
        binary: str,
        input_file: str,
        keep_original: bool = False,
        to_stdout: bool = False,
        force: bool = False,
        compression_level: int | None = None,
    ) -> list[str]:
        """Build command list for subprocess execution.

        Args:
            binary: Command binary name ("gzip" or "gunzip")
            input_file: Input file path
            keep_original: -k flag
            to_stdout: -c flag
            force: -f flag
            compression_level: -1 to -9 flag

        Returns:
            Command as list of strings for subprocess.run()
        """
        cmd = [binary]

        # Add flags
        if keep_original:
            cmd.append("-k")
        if to_stdout:
            cmd.append("-c")
        if force:
            cmd.append("-f")
        if compression_level is not None:
            cmd.append(f"-{compression_level}")

        # Add input file
        cmd.append(input_file)

        return cmd

    def _mock_operation(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Generate mock result when tool is unavailable.

        Args:
            operation: Operation name (decompress, compress, etc.)
            params: Operation parameters

        Returns:
            Mock result dict with mock=True flag
        """
        input_file = params.get("input_file", "mock_input.gz")

        # Generate realistic mock command
        if operation == "decompress":
            mock_cmd = f"gunzip [mock - tool not available] {input_file}"
            output_file = Path(input_file).with_suffix("")
        elif operation == "compress":
            mock_cmd = f"gzip [mock - tool not available] {input_file}"
            output_file = Path(input_file).with_suffix(f"{Path(input_file).suffix}.gz")
        else:
            mock_cmd = f"gzip -{operation[0]} [mock - tool not available] {input_file}"
            output_file = None

        return {
            "success": True,
            "command_executed": mock_cmd,
            "stdout": f"Mock output for {operation} operation",
            "stderr": "",
            "output_files": [str(output_file)] if output_file else [],
            "exit_code": 0,
            "mock": True,
        }


# Create server instance
gunzip_server = GunzipServer()
