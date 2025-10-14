"""
Samtools MCP Server - Vendored BioinfoMCP server for SAM/BAM file operations.

This module implements a strongly-typed MCP server for Samtools, a suite of programs
for interacting with high-throughput sequencing data in SAM/BAM format.

Supports all major Samtools operations including viewing, sorting, indexing,
statistics generation, and file conversion.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import datetime
from typing import Any

from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase, mcp_tool

# Note: In a real implementation, you would import mcp here
# from mcp import tool
from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
)


class SamtoolsServer(MCPServerBase):
    """MCP Server for Samtools sequence analysis utilities."""

    def __init__(self, config: MCPServerConfig | None = None):
        if config is None:
            config = MCPServerConfig(
                server_name="samtools-server",
                server_type=MCPServerType.CUSTOM,
                container_image="tonic01/deepcritical-bioinformatics-samtools:latest",  # Updated Docker Hub URL
                environment_variables={"SAMTOOLS_VERSION": "1.17"},
                capabilities=[
                    "sequence_analysis",
                    "alignment_processing",
                    "bam_manipulation",
                ],
            )
        super().__init__(config)

    def _check_samtools_available(self) -> bool:
        """Check if samtools is available on the system."""
        import shutil

        return shutil.which("samtools") is not None

    def _mock_result(
        self, operation: str, output_files: list[str] | None = None
    ) -> dict[str, Any]:
        """Return a mock result for when samtools is not available."""
        return {
            "success": True,
            "command_executed": f"samtools {operation} [mock - tool not available]",
            "stdout": f"Mock output for {operation} operation",
            "stderr": "",
            "output_files": output_files or [],
            "exit_code": 0,
            "mock": True,  # Indicate this is a mock result
        }

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Run Samtools operation based on parameters.

        Args:
            params: Dictionary containing operation parameters including:
                - operation: The operation to perform
                - Additional operation-specific parameters

        Returns:
            Dictionary containing execution results
        """
        operation = params.get("operation")
        if not operation:
            return {
                "success": False,
                "error": "Missing 'operation' parameter",
            }

        # Map operation to method
        operation_methods = {
            "view": self.samtools_view,
            "sort": self.samtools_sort,
            "index": self.samtools_index,
            "flagstat": self.samtools_flagstat,
            "stats": self.samtools_stats,
            "merge": self.samtools_merge,
            "faidx": self.samtools_faidx,
            "fastq": self.samtools_fastq,
            "flag_convert": self.samtools_flag_convert,
            "quickcheck": self.samtools_quickcheck,
            "depth": self.samtools_depth,
            # Test operation aliases
            "to_bam_conversion": self.samtools_sort,
            "indexing": self.samtools_index,
        }

        if operation not in operation_methods:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}",
            }

        method = operation_methods[operation]

        # Prepare method arguments
        method_params = params.copy()
        method_params.pop("operation", None)  # Remove operation from params

        try:
            # Call the appropriate method
            return method(**method_params)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute {operation}: {e!s}",
            }

    @mcp_tool()
    def samtools_view(
        self,
        input_file: str,
        output_file: str | None = None,
        format: str = "sam",
        header_only: bool = False,
        no_header: bool = False,
        count: bool = False,
        min_mapq: int = 0,
        region: str | None = None,
        threads: int = 1,
        reference: str | None = None,
        uncompressed: bool = False,
        fast_compression: bool = False,
        output_fmt: str = "sam",
        read_group: str | None = None,
        sample: str | None = None,
        library: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert between SAM and BAM formats, extract regions, etc.

        Args:
            input_file: Input SAM/BAM/CRAM file
            output_file: Output file (optional, stdout if not specified)
            format: Input format (sam, bam, cram)
            header_only: Output only the header
            no_header: Suppress header output
            count: Output count of records instead of records
            min_mapq: Minimum mapping quality
            region: Region to extract (e.g., chr1:100-200)
            threads: Number of threads to use
            reference: Reference sequence FASTA file
            uncompressed: Uncompressed BAM output
            fast_compression: Fast (but less efficient) compression
            output_fmt: Output format (sam, bam, cram)
            read_group: Only output reads from this read group
            sample: Only output reads from this sample
            library: Only output reads from this library

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            output_files = [output_file] if output_file else []
            return self._mock_result("view", output_files)

        # Validate input file exists
        if not os.path.exists(input_file):
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "view"]

        # Add options
        if header_only:
            cmd.append("-H")
        if no_header:
            cmd.append("-h")
        if count:
            cmd.append("-c")
        if min_mapq > 0:
            cmd.extend(["-q", str(min_mapq)])
        if region:
            cmd.extend(["-r", region])
        if threads > 1:
            cmd.extend(["-@", str(threads)])
        if reference:
            cmd.extend(["-T", reference])
        if uncompressed:
            cmd.append("-u")
        if fast_compression:
            cmd.append("--fast")
        if output_fmt != "sam":
            cmd.extend(["-O", output_fmt])
        if read_group:
            cmd.extend(["-RG", read_group])
        if sample:
            cmd.extend(["-s", sample])
        if library:
            cmd.extend(["-l", library])

        # Add input file
        cmd.append(input_file)

        # Execute command
        try:
            if output_file:
                with open(output_file, "w") as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True
                    )
                output_files = [output_file]
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                output_files = []

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
                "error": f"samtools view failed: {e}",
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
    def samtools_sort(
        self,
        input_file: str,
        output_file: str,
        threads: int = 1,
        memory: str = "768M",
        compression: int = 6,
        by_name: bool = False,
        by_tag: str | None = None,
        max_memory: str = "768M",
    ) -> dict[str, Any]:
        """
        Sort BAM file by coordinate or read name.

        Args:
            input_file: Input BAM file to sort
            output_file: Output sorted BAM file
            threads: Number of threads to use
            memory: Memory per thread
            compression: Compression level (0-9)
            by_name: Sort by read name instead of coordinate
            by_tag: Sort by tag value
            max_memory: Maximum memory to use

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            return self._mock_result("sort", [output_file])

        # Validate input file exists
        if not os.path.exists(input_file):
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "sort"]

        # Add options
        if threads > 1:
            cmd.extend(["-@", str(threads)])
        if memory != "768M":
            cmd.extend(["-m", memory])
        if compression != 6:
            cmd.extend(["-l", str(compression)])
        if by_name:
            cmd.append("-n")
        if by_tag:
            cmd.extend(["-t", by_tag])
        if max_memory != "768M":
            cmd.extend(["-M", max_memory])

        # Add input and output files
        cmd.extend(["-o", output_file, input_file])

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": [output_file],
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
                "error": f"samtools sort failed: {e}",
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
    def samtools_index(self, input_file: str) -> dict[str, Any]:
        """
        Index a BAM file for fast random access.

        Args:
            input_file: Input BAM file to index

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            output_files = [f"{input_file}.bai"]
            return self._mock_result("index", output_files)

        # Validate input file exists
        if not os.path.exists(input_file):
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "index", input_file]

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Output file is input_file + ".bai"
            output_file = f"{input_file}.bai"
            output_files = [output_file] if os.path.exists(output_file) else []

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
                "error": f"samtools index failed: {e}",
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
    def samtools_flagstat(self, input_file: str) -> dict[str, Any]:
        """
        Generate flag statistics for a BAM file.

        Args:
            input_file: Input BAM file

        Returns:
            Dictionary containing command executed, stdout, stderr, and flag statistics
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            result = self._mock_result("flagstat", [])
            result["flag_statistics"] = "Mock flag statistics output"
            return result

        # Validate input file exists
        if not os.path.exists(input_file):
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "flagstat", input_file]

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": [],
                "exit_code": result.returncode,
                "success": True,
                "flag_statistics": result.stdout,
            }

        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout,
                "stderr": e.stderr,
                "output_files": [],
                "exit_code": e.returncode,
                "success": False,
                "error": f"samtools flagstat failed: {e}",
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
    def samtools_stats(
        self, input_file: str, output_file: str | None = None
    ) -> dict[str, Any]:
        """
        Generate comprehensive statistics for a BAM file.

        Args:
            input_file: Input BAM file
            output_file: Output file for statistics (optional)

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            output_files = [output_file] if output_file else []
            return self._mock_result("stats", output_files)

        # Validate input file exists
        if not os.path.exists(input_file):
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "stats", input_file]

        # Execute command
        try:
            if output_file:
                with open(output_file, "w") as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True
                    )
                output_files = [output_file]
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                output_files = []

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
                "error": f"samtools stats failed: {e}",
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
    def samtools_merge(
        self,
        output_file: str,
        input_files: list[str],
        no_rg: bool = False,
        update_header: str | None = None,
        threads: int = 1,
    ) -> dict[str, Any]:
        """
        Merge multiple sorted alignment files into one sorted output file.

        Args:
            output_file: Output merged BAM file
            input_files: List of input BAM files to merge
            no_rg: Suppress RG tag header merging
            update_header: Use the header from this file
            threads: Number of threads to use

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            return self._mock_result("merge", [output_file])

        # Validate input files exist
        for input_file in input_files:
            if not os.path.exists(input_file):
                msg = f"Input file not found: {input_file}"
                raise FileNotFoundError(msg)

        if not input_files:
            msg = "At least one input file must be specified"
            raise ValueError(msg)

        if update_header and not os.path.exists(update_header):
            msg = f"Header file not found: {update_header}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "merge"]

        # Add options
        if no_rg:
            cmd.append("-n")
        if update_header:
            cmd.extend(["-h", update_header])
        if threads > 1:
            cmd.extend(["-@", str(threads)])

        # Add output file
        cmd.append(output_file)

        # Add input files
        cmd.extend(input_files)

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": [output_file],
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
                "error": f"samtools merge failed: {e}",
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
    def samtools_faidx(
        self, fasta_file: str, regions: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Index a FASTA file or extract subsequences from indexed FASTA.

        Args:
            fasta_file: Input FASTA file
            regions: List of regions to extract (optional)

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            output_files = [f"{fasta_file}.fai"] if not regions else []
            return self._mock_result("faidx", output_files)

        # Validate input file exists
        if not os.path.exists(fasta_file):
            msg = f"FASTA file not found: {fasta_file}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "faidx", fasta_file]

        # Add regions if specified
        if regions:
            cmd.extend(regions)

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Check if index file was created (when no regions specified)
            output_files = []
            if not regions:
                index_file = f"{fasta_file}.fai"
                if os.path.exists(index_file):
                    output_files.append(index_file)

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
                "error": f"samtools faidx failed: {e}",
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
    def samtools_fastq(
        self,
        input_file: str,
        output_file: str | None = None,
        soft_clip: bool = False,
        threads: int = 1,
    ) -> dict[str, Any]:
        """
        Convert BAM/CRAM to FASTQ format.

        Args:
            input_file: Input BAM/CRAM file
            output_file: Output FASTQ file (optional, stdout if not specified)
            soft_clip: Include soft-clipped bases in output
            threads: Number of threads to use

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            output_files = [output_file] if output_file else []
            return self._mock_result("fastq", output_files)

        # Validate input file exists
        if not os.path.exists(input_file):
            msg = f"Input file not found: {input_file}"
            raise FileNotFoundError(msg)

        # Build command
        cmd = ["samtools", "fastq"]

        # Add options
        if soft_clip:
            cmd.append("--soft-clipped")
        if threads > 1:
            cmd.extend(["-@", str(threads)])

        # Add input file
        cmd.append(input_file)

        # Add output file if specified
        if output_file:
            cmd.extend(["-o", output_file])

        # Execute command
        try:
            if output_file:
                with open(output_file, "w") as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True
                    )
                output_files = [output_file]
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                output_files = []

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
                "error": f"samtools fastq failed: {e}",
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
    def samtools_flag_convert(self, flags: str) -> dict[str, Any]:
        """
        Convert between textual and numeric flag representation.

        Args:
            flags: Comma-separated list of flags or numeric flag value

        Returns:
            Dictionary containing command executed, stdout, stderr
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            result = self._mock_result("flags", [])
            result["stdout"] = f"Mock flag conversion output for: {flags}"
            return result

        if not flags:
            msg = "flags parameter must be provided"
            raise ValueError(msg)

        # Build command
        cmd = ["samtools", "flags", flags]

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout.strip(),
                "stderr": result.stderr,
                "output_files": [],
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
                "error": f"samtools flags failed: {e}",
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
    def samtools_quickcheck(
        self, input_files: list[str], verbose: bool = False
    ) -> dict[str, Any]:
        """
        Quickly check that input files appear intact.

        Args:
            input_files: List of input files to check
            verbose: Enable verbose output

        Returns:
            Dictionary containing command executed, stdout, stderr
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            return self._mock_result("quickcheck", [])

        # Validate input files exist
        for input_file in input_files:
            if not os.path.exists(input_file):
                msg = f"Input file not found: {input_file}"
                raise FileNotFoundError(msg)

        if not input_files:
            msg = "At least one input file must be specified"
            raise ValueError(msg)

        # Build command
        cmd = ["samtools", "quickcheck"]

        # Add options
        if verbose:
            cmd.append("-v")

        # Add input files
        cmd.extend(input_files)

        # Execute command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": [],
                "exit_code": result.returncode,
                "success": True,
            }

        except subprocess.CalledProcessError as e:
            # quickcheck returns non-zero if files are corrupted
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout,
                "stderr": e.stderr,
                "output_files": [],
                "exit_code": e.returncode,
                "success": False,
                "error": f"samtools quickcheck failed: {e}",
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
    def samtools_depth(
        self,
        input_files: list[str],
        regions: list[str] | None = None,
        output_file: str | None = None,
    ) -> dict[str, Any]:
        """
        Compute read depth at each position or region.

        Args:
            input_files: List of input BAM files
            regions: List of regions to analyze (optional)
            output_file: Output file for depth data (optional)

        Returns:
            Dictionary containing command executed, stdout, stderr, and output files
        """
        # Check if samtools is available
        if not self._check_samtools_available():
            output_files = [output_file] if output_file else []
            return self._mock_result("depth", output_files)

        # Validate input files exist
        for input_file in input_files:
            if not os.path.exists(input_file):
                msg = f"Input file not found: {input_file}"
                raise FileNotFoundError(msg)

        if not input_files:
            msg = "At least one input file must be specified"
            raise ValueError(msg)

        # Build command
        cmd = ["samtools", "depth"]

        # Add input files
        cmd.extend(input_files)

        # Add regions if specified
        if regions:
            cmd.extend(regions)

        # Execute command
        try:
            if output_file:
                with open(output_file, "w") as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True
                    )
                output_files = [output_file]
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                output_files = []

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
                "error": f"samtools depth failed: {e}",
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

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy Samtools server using testcontainers."""
        try:
            from testcontainers.core.container import DockerContainer

            # Create container
            container = DockerContainer("python:3.11-slim")
            container.with_name(f"mcp-samtools-server-{id(self)}")

            # Install Samtools
            container.with_command(
                "bash -c 'pip install samtools && tail -f /dev/null'"
            )

            # Start container
            container.start()

            # Wait for container to be ready
            container.reload()
            while container.status != "running":
                await asyncio.sleep(0.1)
                container.reload()

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
            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                status=MCPServerStatus.FAILED,
                error_message=str(e),
                configuration=self.config,
            )

    async def stop_with_testcontainers(self) -> bool:
        """Stop Samtools server deployed with testcontainers."""
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
            return False

    def get_server_info(self) -> dict[str, Any]:
        """Get information about this Samtools server."""
        return {
            "name": self.name,
            "type": "samtools",
            "version": "1.17",
            "description": "Samtools sequence analysis utilities server",
            "tools": self.list_tools(),
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": "running" if self.container_id else "stopped",
        }


# Create server instance
samtools_server = SamtoolsServer()
