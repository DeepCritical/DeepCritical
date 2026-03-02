"""
MAFFT MCP Server - Multiple sequence alignment using Fast Fourier Transform.

This module implements a strongly-typed MCP server for MAFFT, providing comprehensive
tools for multiple sequence alignment of biological sequences. The server integrates
with Pydantic AI patterns and supports testcontainers deployment.

Features:
- Multiple alignment algorithms (FFT-NS-1, FFT-NS-2, L-INS-i, G-INS-i, E-INS-i)
- Automatic algorithm selection based on input size and type
- Multiple output format support (FASTA, ClustalW, Phylip)
- Large dataset handling with progressive alignment
- Docker containerization with biocontainers/mafft image
- Pydantic AI agent integration capabilities
"""

from __future__ import annotations

import asyncio
import os
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


class MAFFTServer(MCPServerBase):
    """MCP Server for MAFFT multiple sequence alignment with Pydantic AI integration."""

    def __init__(self, config: MCPServerConfig | None = None):
        if config is None:
            config = MCPServerConfig(
                server_name="mafft-server",
                server_type=MCPServerType.CUSTOM,
                container_image="biocontainers/mafft:latest",
                environment_variables={
                    "MAFFT_VERSION": "7.526",
                },
                capabilities=[
                    "multiple_sequence_alignment",
                    "protein_alignment",
                    "nucleotide_alignment",
                    "phylogenetic_analysis",
                    "conserved_region_identification",
                    "progressive_alignment",
                    "iterative_refinement",
                ],
            )
        super().__init__(config)

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Run MAFFT operation based on parameters.

        Args:
            params: Dictionary containing operation parameters including:
                - operation: The operation to perform (align, add, merge)
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

        operation_methods = {
            "align": self.mafft_align,
            "add": self.mafft_add,
            "merge": self.mafft_merge,
        }

        if operation not in operation_methods:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}",
            }

        method = operation_methods[operation]

        method_params = params.copy()
        method_params.pop("operation", None)

        try:
            if not shutil.which("mafft"):
                mock_output_files = self._get_mock_output_files(
                    operation, method_params
                )
                return {
                    "success": True,
                    "command_executed": f"mafft {operation} [mock - tool not available]",
                    "stdout": f"Mock output for {operation} operation",
                    "stderr": "",
                    "output_files": mock_output_files,
                    "exit_code": 0,
                    "mock": True,
                }

            return method(**method_params)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute {operation}: {e!s}",
            }

    def _get_mock_output_files(
        self, operation: str, params: dict[str, Any]
    ) -> list[str]:
        """Generate mock output files for testing environments."""
        output_file = params.get("output_file")
        if output_file:
            return [str(output_file)]
        if operation == "align":
            input_fasta = params.get("input_fasta", "input.fasta")
            return [str(Path(input_fasta).with_suffix(".aligned.fasta"))]
        if operation == "add":
            existing_alignment = params.get("existing_alignment", "existing.fasta")
            return [str(Path(existing_alignment).with_suffix(".added.fasta"))]
        if operation == "merge":
            return ["merged_alignment.fasta"]
        return []

    @mcp_tool(
        MCPToolSpec(
            name="mafft_align",
            description="Perform multiple sequence alignment on FASTA sequences using MAFFT with automatic or manual algorithm selection",
            inputs={
                "input_fasta": "str",
                "output_file": "Optional[str]",
                "algorithm": "str",
                "maxiterate": "int",
                "thread": "int",
                "output_format": "str",
                "op": "float",
                "ep": "float",
                "bl": "str",
                "jtt": "bool",
                "tm": "bool",
                "fmodel": "bool",
                "clustalout": "bool",
                "reorder": "bool",
                "treeout": "bool",
                "quiet": "bool",
                "amino": "bool",
                "nuc": "bool",
                "adjustdirection": "bool",
                "adjustdirectionaccurately": "bool",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Auto-select alignment algorithm",
                    "parameters": {
                        "input_fasta": "/data/sequences.fasta",
                        "output_file": "/results/aligned.fasta",
                        "algorithm": "auto",
                    },
                },
                {
                    "description": "L-INS-i high-accuracy alignment for small datasets",
                    "parameters": {
                        "input_fasta": "/data/proteins.fasta",
                        "output_file": "/results/aligned.fasta",
                        "algorithm": "linsi",
                        "maxiterate": 1000,
                    },
                },
            ],
        )
    )
    def mafft_align(
        self,
        input_fasta: str,
        output_file: str | None = None,
        algorithm: str = "auto",
        maxiterate: int = 0,
        thread: int = 1,
        output_format: str = "fasta",
        op: float = 1.53,
        ep: float = 0.0,
        bl: str = "62",
        jtt: bool = False,
        tm: bool = False,
        fmodel: bool = False,
        clustalout: bool = False,
        reorder: bool = False,
        treeout: bool = False,
        quiet: bool = False,
        amino: bool = False,
        nuc: bool = False,
        adjustdirection: bool = False,
        adjustdirectionaccurately: bool = False,
    ) -> dict[str, Any]:
        """
        Perform multiple sequence alignment on FASTA sequences using MAFFT.

        Supports multiple alignment strategies optimized for different use cases:
        - auto: Automatically select the best algorithm based on data size
        - fftns1: FFT-NS-1 — fast, progressive method
        - fftns2: FFT-NS-2 — progressive with iterative refinement
        - linsi: L-INS-i — accurate, for sequences with one alignable domain
        - ginsi: G-INS-i — accurate, for sequences with global homology
        - einsi: E-INS-i — accurate, for sequences with multiple conserved domains

        Parameters:
        - input_fasta: Path to input multi-FASTA file (required)
        - output_file: Path to output aligned file (if None, stdout is captured)
        - algorithm: Alignment algorithm to use (auto, fftns1, fftns2, linsi, ginsi, einsi)
        - maxiterate: Maximum number of iterative refinement cycles (0 = default)
        - thread: Number of threads to use (default 1, -1 = auto-detect)
        - output_format: Output format — fasta, clustal, phylip
        - op: Gap opening penalty (default 1.53)
        - ep: Gap extension penalty (default 0.0)
        - bl: BLOSUM matrix number for amino acids (30, 45, 62, 80)
        - jtt: Use JTT substitution model for amino acids
        - tm: Use transmembrane substitution model
        - fmodel: Incorporate amino acid/nucleotide composition into scoring
        - clustalout: Output in ClustalW format
        - reorder: Output in alignment order rather than input order
        - treeout: Output guide tree in Newick format
        - quiet: Suppress progress output
        - amino: Force amino acid alignment mode
        - nuc: Force nucleotide alignment mode
        - adjustdirection: Adjust sequence direction using 6-mer counting (fast)
        - adjustdirectionaccurately: Adjust sequence direction using alignment (accurate)

        Returns:
        Dict with keys: command_executed, stdout, stderr, output_files
        """
        input_path = Path(input_fasta)
        if not input_path.is_file():
            msg = f"Input FASTA file not found: {input_fasta}"
            raise FileNotFoundError(msg)

        valid_algorithms = {"auto", "fftns1", "fftns2", "linsi", "ginsi", "einsi"}
        algorithm_lower = algorithm.lower()
        if algorithm_lower not in valid_algorithms:
            msg = f"Invalid algorithm '{algorithm}'. Must be one of {valid_algorithms}."
            raise ValueError(msg)

        if maxiterate < 0:
            msg = "maxiterate must be >= 0."
            raise ValueError(msg)

        if thread < -1 or thread == 0:
            msg = "thread must be >= 1 or -1 for auto-detect."
            raise ValueError(msg)

        valid_formats = {"fasta", "clustal", "phylip"}
        output_format_lower = output_format.lower()
        if output_format_lower not in valid_formats:
            msg = f"Invalid output_format '{output_format}'. Must be one of {valid_formats}."
            raise ValueError(msg)

        if op < 0:
            msg = "Gap opening penalty (op) must be >= 0."
            raise ValueError(msg)

        if ep < 0:
            msg = "Gap extension penalty (ep) must be >= 0."
            raise ValueError(msg)

        valid_bl = {"30", "45", "62", "80"}
        if bl not in valid_bl:
            msg = f"Invalid BLOSUM matrix '{bl}'. Must be one of {valid_bl}."
            raise ValueError(msg)

        if adjustdirection and adjustdirectionaccurately:
            msg = "Cannot use both --adjustdirection and --adjustdirectionaccurately."
            raise ValueError(msg)

        cmd = ["mafft"]

        algorithm_flags = {
            "auto": ["--auto"],
            "fftns1": ["--retree", "1"],
            "fftns2": ["--retree", "2"],
            "linsi": [
                "--localpair",
                "--maxiterate",
                str(maxiterate if maxiterate > 0 else 1000),
            ],
            "ginsi": [
                "--globalpair",
                "--maxiterate",
                str(maxiterate if maxiterate > 0 else 1000),
            ],
            "einsi": [
                "--genafpair",
                "--maxiterate",
                str(maxiterate if maxiterate > 0 else 1000),
            ],
        }
        cmd.extend(algorithm_flags[algorithm_lower])

        if maxiterate > 0 and algorithm_lower not in {"linsi", "ginsi", "einsi"}:
            cmd.extend(["--maxiterate", str(maxiterate)])

        if thread != 1:
            cmd.extend(["--thread", str(thread)])

        if op != 1.53:
            cmd.extend(["--op", str(op)])

        if ep != 0.0:
            cmd.extend(["--ep", str(ep)])

        if bl != "62":
            cmd.extend(["--bl", bl])

        if jtt:
            cmd.append("--jtt")

        if tm:
            cmd.append("--tm")

        if fmodel:
            cmd.append("--fmodel")

        if output_format_lower == "clustal" or clustalout:
            cmd.append("--clustalout")

        if output_format_lower == "phylip":
            cmd.append("--phylipout")

        if reorder:
            cmd.append("--reorder")

        if treeout:
            cmd.append("--treeout")

        if quiet:
            cmd.append("--quiet")

        if amino:
            cmd.append("--amino")

        if nuc:
            cmd.append("--nuc")

        if adjustdirection:
            cmd.append("--adjustdirection")

        if adjustdirectionaccurately:
            cmd.append("--adjustdirectionaccurately")

        cmd.append(str(input_path.resolve()))

        try:
            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout if e.stdout else "",
                "stderr": e.stderr if e.stderr else "",
                "output_files": [],
                "error": f"MAFFT align failed with return code {e.returncode}",
            }

        output_files = []
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(completed.stdout)
            output_files.append(str(output_path.resolve()))

        if treeout:
            tree_file = Path(str(input_path) + ".tree")
            if tree_file.exists():
                output_files.append(str(tree_file.resolve()))

        return {
            "command_executed": " ".join(cmd),
            "stdout": completed.stdout if not output_file else "",
            "stderr": completed.stderr,
            "output_files": output_files,
        }

    @mcp_tool(
        MCPToolSpec(
            name="mafft_add",
            description="Add new sequences to an existing MAFFT alignment without re-aligning the original sequences",
            inputs={
                "new_sequences": "str",
                "existing_alignment": "str",
                "output_file": "Optional[str]",
                "add_method": "str",
                "thread": "int",
                "reorder": "bool",
                "quiet": "bool",
                "amino": "bool",
                "nuc": "bool",
                "keeplength": "bool",
                "mapout": "bool",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Add new sequences to existing alignment",
                    "parameters": {
                        "new_sequences": "/data/new_seqs.fasta",
                        "existing_alignment": "/data/existing_alignment.fasta",
                        "output_file": "/results/updated_alignment.fasta",
                        "add_method": "add",
                    },
                }
            ],
        )
    )
    def mafft_add(
        self,
        new_sequences: str,
        existing_alignment: str,
        output_file: str | None = None,
        add_method: str = "add",
        thread: int = 1,
        reorder: bool = False,
        quiet: bool = False,
        amino: bool = False,
        nuc: bool = False,
        keeplength: bool = False,
        mapout: bool = False,
    ) -> dict[str, Any]:
        """
        Add new sequences to an existing alignment without re-aligning original sequences.

        This is useful for incrementally building alignments as new sequences become
        available, without disturbing a curated base alignment.

        Parameters:
        - new_sequences: Path to FASTA file with new sequences to add (required)
        - existing_alignment: Path to existing aligned FASTA file (required)
        - output_file: Path to save the updated alignment (if None, stdout is captured)
        - add_method: Method for adding sequences (add, addfragments, addprofile)
        - thread: Number of threads (default 1, -1 = auto-detect)
        - reorder: Output in alignment order
        - quiet: Suppress progress output
        - amino: Force amino acid mode
        - nuc: Force nucleotide mode
        - keeplength: Keep alignment length (do not extend for new sequences)
        - mapout: Output correspondence table for added sequences

        Returns:
        Dict with keys: command_executed, stdout, stderr, output_files
        """
        new_seq_path = Path(new_sequences)
        if not new_seq_path.is_file():
            msg = f"New sequences file not found: {new_sequences}"
            raise FileNotFoundError(msg)

        existing_path = Path(existing_alignment)
        if not existing_path.is_file():
            msg = f"Existing alignment file not found: {existing_alignment}"
            raise FileNotFoundError(msg)

        valid_add_methods = {"add", "addfragments", "addprofile"}
        add_method_lower = add_method.lower()
        if add_method_lower not in valid_add_methods:
            msg = f"Invalid add_method '{add_method}'. Must be one of {valid_add_methods}."
            raise ValueError(msg)

        if thread < -1 or thread == 0:
            msg = "thread must be >= 1 or -1 for auto-detect."
            raise ValueError(msg)

        cmd = ["mafft"]

        add_flags = {
            "add": "--add",
            "addfragments": "--addfragments",
            "addprofile": "--addprofile",
        }
        cmd.extend([add_flags[add_method_lower], str(new_seq_path.resolve())])

        if thread != 1:
            cmd.extend(["--thread", str(thread)])

        if reorder:
            cmd.append("--reorder")

        if quiet:
            cmd.append("--quiet")

        if amino:
            cmd.append("--amino")

        if nuc:
            cmd.append("--nuc")

        if keeplength:
            cmd.append("--keeplength")

        if mapout:
            cmd.append("--mapout")

        cmd.append(str(existing_path.resolve()))

        try:
            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout if e.stdout else "",
                "stderr": e.stderr if e.stderr else "",
                "output_files": [],
                "error": f"MAFFT add failed with return code {e.returncode}",
            }

        output_files = []
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(completed.stdout)
            output_files.append(str(output_path.resolve()))

        return {
            "command_executed": " ".join(cmd),
            "stdout": completed.stdout if not output_file else "",
            "stderr": completed.stderr,
            "output_files": output_files,
        }

    @mcp_tool(
        MCPToolSpec(
            name="mafft_merge",
            description="Merge multiple pre-aligned sequence groups into a single alignment using MAFFT merge",
            inputs={
                "input_fasta": "str",
                "merge_table": "str",
                "output_file": "Optional[str]",
                "thread": "int",
                "quiet": "bool",
                "amino": "bool",
                "nuc": "bool",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Merge pre-aligned sequence groups",
                    "parameters": {
                        "input_fasta": "/data/all_sequences.fasta",
                        "merge_table": "/data/merge_table.txt",
                        "output_file": "/results/merged_alignment.fasta",
                    },
                }
            ],
        )
    )
    def mafft_merge(
        self,
        input_fasta: str,
        merge_table: str,
        output_file: str | None = None,
        thread: int = 1,
        quiet: bool = False,
        amino: bool = False,
        nuc: bool = False,
    ) -> dict[str, Any]:
        """
        Merge multiple pre-aligned sequence groups into a single alignment.

        Uses MAFFT's merge functionality to combine sub-alignments that were
        aligned separately (e.g., different gene families or species groups).

        Parameters:
        - input_fasta: Path to input multi-FASTA file containing all sequences (required)
        - merge_table: Path to merge table file specifying group memberships (required)
        - output_file: Path to save merged alignment (if None, stdout is captured)
        - thread: Number of threads (default 1, -1 = auto-detect)
        - quiet: Suppress progress output
        - amino: Force amino acid mode
        - nuc: Force nucleotide mode

        Returns:
        Dict with keys: command_executed, stdout, stderr, output_files
        """
        input_path = Path(input_fasta)
        if not input_path.is_file():
            msg = f"Input FASTA file not found: {input_fasta}"
            raise FileNotFoundError(msg)

        merge_table_path = Path(merge_table)
        if not merge_table_path.is_file():
            msg = f"Merge table file not found: {merge_table}"
            raise FileNotFoundError(msg)

        if thread < -1 or thread == 0:
            msg = "thread must be >= 1 or -1 for auto-detect."
            raise ValueError(msg)

        cmd = ["mafft", "--merge", str(merge_table_path.resolve())]

        if thread != 1:
            cmd.extend(["--thread", str(thread)])

        if quiet:
            cmd.append("--quiet")

        if amino:
            cmd.append("--amino")

        if nuc:
            cmd.append("--nuc")

        cmd.append(str(input_path.resolve()))

        try:
            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout if e.stdout else "",
                "stderr": e.stderr if e.stderr else "",
                "output_files": [],
                "error": f"MAFFT merge failed with return code {e.returncode}",
            }

        output_files = []
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(completed.stdout)
            output_files.append(str(output_path.resolve()))

        return {
            "command_executed": " ".join(cmd),
            "stdout": completed.stdout if not output_file else "",
            "stderr": completed.stderr,
            "output_files": output_files,
        }

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy MAFFT server using testcontainers."""
        try:
            from testcontainers.core.container import DockerContainer

            container = DockerContainer("biocontainers/mafft:latest")
            container.with_name(f"mcp-mafft-server-{id(self)}")

            container.with_command("bash -c 'tail -f /dev/null'")

            container.start()

            container.reload()
            while container.status != "running":
                await asyncio.sleep(0.1)
                container.reload()

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
        """Stop MAFFT server deployed with testcontainers."""
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
        """Get information about this MAFFT server."""
        return {
            "name": self.name,
            "type": "mafft",
            "version": "7.526",
            "description": "MAFFT multiple sequence alignment server",
            "tools": self.list_tools(),
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": "running" if self.container_id else "stopped",
        }
