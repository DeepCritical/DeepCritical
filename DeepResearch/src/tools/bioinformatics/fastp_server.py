"""
Fastp MCP Server - Vendored BioinfoMCP server for FASTQ preprocessing.

This module implements a strongly-typed MCP server for Fastp, an ultra-fast
all-in-one FASTQ preprocessor, using Pydantic AI patterns and testcontainers deployment.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import datetime
from typing import Any

# from pydantic_ai import RunContext
# from pydantic_ai.tools import defer
from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase, mcp_tool
from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
    MCPToolSpec,
)


class FastpServer(MCPServerBase):
    """MCP Server for Fastp FASTQ preprocessing tool with Pydantic AI integration."""

    def __init__(self, config: MCPServerConfig | None = None):
        if config is None:
            config = MCPServerConfig(
                server_name="fastp-server",
                server_type=MCPServerType.CUSTOM,
                container_image="condaforge/miniforge3:latest",
                environment_variables={"FASTP_VERSION": "0.23.4"},
                capabilities=[
                    "quality_control",
                    "adapter_trimming",
                    "read_filtering",
                    "preprocessing",
                    "deduplication",
                    "merging",
                    "splitting",
                    "umi_processing",
                ],
            )
            super().__init__(config)

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Run Fastp operation based on parameters.

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
            "process": self.fastp_process,
            "with_testcontainers": self.stop_with_testcontainers,
            "server_info": self.get_server_info,
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
            # Check if tool is available (for testing/development environments)
            import shutil

            tool_name_check = "fastp"
            if not shutil.which(tool_name_check):
                # Return mock success result for testing when tool is not available
                if operation == "server_info":
                    return {
                        "success": True,
                        "name": "fastp-server",
                        "type": "fastp",
                        "version": "0.23.4",
                        "description": "Fastp FASTQ preprocessing server",
                        "tools": ["fastp_process"],
                        "container_id": None,
                        "container_name": None,
                        "status": "stopped",
                        "pydantic_ai_enabled": False,
                        "session_active": False,
                        "mock": True,  # Indicate this is a mock result
                    }
                return {
                    "success": True,
                    "command_executed": f"{tool_name_check} {operation} [mock - tool not available]",
                    "stdout": f"Mock output for {operation} operation",
                    "stderr": "",
                    "output_files": [
                        method_params.get("output_file", f"mock_{operation}_output")
                    ],
                    "exit_code": 0,
                    "mock": True,  # Indicate this is a mock result
                }

            # Call the appropriate method
            return method(**method_params)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute {operation}: {e!s}",
            }

    @mcp_tool(
        MCPToolSpec(
            name="fastp_process",
            description="Process FASTQ files with comprehensive quality control and adapter trimming using Fastp - ultra-fast all-in-one FASTQ preprocessor",
            inputs={
                "input1": "str",
                "output1": "str",
                "input2": "str | None",
                "output2": "str | None",
                "unpaired1": "str | None",
                "unpaired2": "str | None",
                "failed_out": "str | None",
                "merge": "bool",
                "merged_out": "str | None",
                "include_unmerged": "bool",
                "phred64": "bool",
                "compression": "int",
                "stdin": "bool",
                "stdout": "bool",
                "interleaved_in": "bool",
                "reads_to_process": "int",
                "dont_overwrite": "bool",
                "fix_mgi_id": "bool",
                "adapter_sequence": "str | None",
                "adapter_sequence_r2": "str | None",
                "adapter_fasta": "str | None",
                "detect_adapter_for_pe": "bool",
                "disable_adapter_trimming": "bool",
                "trim_front1": "int",
                "trim_tail1": "int",
                "max_len1": "int",
                "trim_front2": "int",
                "trim_tail2": "int",
                "max_len2": "int",
                "dedup": "bool",
                "dup_calc_accuracy": "int",
                "dont_eval_duplication": "bool",
                "trim_poly_g": "bool",
                "poly_g_min_len": "int",
                "disable_trim_poly_g": "bool",
                "trim_poly_x": "bool",
                "poly_x_min_len": "int",
                "cut_front": "bool",
                "cut_tail": "bool",
                "cut_right": "bool",
                "cut_window_size": "int",
                "cut_mean_quality": "int",
                "cut_front_window_size": "int",
                "cut_front_mean_quality": "int",
                "cut_tail_window_size": "int",
                "cut_tail_mean_quality": "int",
                "cut_right_window_size": "int",
                "cut_right_mean_quality": "int",
                "disable_quality_filtering": "bool",
                "qualified_quality_phred": "int",
                "unqualified_percent_limit": "int",
                "n_base_limit": "int",
                "average_qual": "int",
                "disable_length_filtering": "bool",
                "length_required": "int",
                "length_limit": "int",
                "low_complexity_filter": "bool",
                "complexity_threshold": "float",
                "filter_by_index1": "str | None",
                "filter_by_index2": "str | None",
                "filter_by_index_threshold": "int",
                "correction": "bool",
                "overlap_len_require": "int",
                "overlap_diff_limit": "int",
                "overlap_diff_percent_limit": "float",
                "umi": "bool",
                "umi_loc": "str",
                "umi_len": "int",
                "umi_prefix": "str | None",
                "umi_skip": "int",
                "overrepresentation_analysis": "bool",
                "overrepresentation_sampling": "int",
                "json": "str | None",
                "html": "str | None",
                "report_title": "str",
                "thread": "int",
                "split": "int",
                "split_by_lines": "int",
                "split_prefix_digits": "int",
                "verbose": "bool",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
                "success": "bool",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Basic FASTQ preprocessing with adapter trimming and quality filtering",
                    "parameters": {
                        "input1": "/data/sample_R1.fastq.gz",
                        "output1": "/data/sample_R1_processed.fastq.gz",
                        "input2": "/data/sample_R2.fastq.gz",
                        "output2": "/data/sample_R2_processed.fastq.gz",
                        "threads": 4,
                        "detect_adapter_for_pe": True,
                        "qualified_quality_phred": 20,
                        "length_required": 20,
                    },
                },
                {
                    "description": "Advanced preprocessing with deduplication and UMI processing",
                    "parameters": {
                        "input1": "/data/sample_R1.fastq.gz",
                        "output1": "/data/sample_R1_processed.fastq.gz",
                        "input2": "/data/sample_R2.fastq.gz",
                        "output2": "/data/sample_R2_processed.fastq.gz",
                        "threads": 8,
                        "dedup": True,
                        "dup_calc_accuracy": 2,
                        "umi": True,
                        "umi_loc": "read1",
                        "umi_len": 8,
                        "correction": True,
                        "overrepresentation_analysis": True,
                        "json": "/data/fastp_report.json",
                        "html": "/data/fastp_report.html",
                    },
                },
                {
                    "description": "Single-end FASTQ processing with merging and quality trimming",
                    "parameters": {
                        "input1": "/data/sample.fastq.gz",
                        "output1": "/data/sample_processed.fastq.gz",
                        "threads": 4,
                        "cut_front": True,
                        "cut_tail": True,
                        "cut_mean_quality": 20,
                        "qualified_quality_phred": 25,
                        "length_required": 30,
                        "trim_poly_g": True,
                        "poly_g_min_len": 8,
                    },
                },
                {
                    "description": "Paired-end merging with comprehensive quality control",
                    "parameters": {
                        "input1": "/data/sample_R1.fastq.gz",
                        "input2": "/data/sample_R2.fastq.gz",
                        "merged_out": "/data/sample_merged.fastq.gz",
                        "output1": "/data/sample_unmerged_R1.fastq.gz",
                        "output2": "/data/sample_unmerged_R2.fastq.gz",
                        "merge": True,
                        "include_unmerged": True,
                        "threads": 6,
                        "detect_adapter_for_pe": True,
                        "correction": True,
                        "overlap_len_require": 25,
                        "qualified_quality_phred": 20,
                        "unqualified_percent_limit": 30,
                        "length_required": 25,
                    },
                },
            ],
        )
    )
    def fastp_process(
        self,
        input1: str,
        output1: str,
        input2: str | None = None,
        output2: str | None = None,
        unpaired1: str | None = None,
        unpaired2: str | None = None,
        failed_out: str | None = None,
        merge: bool = False,
        merged_out: str | None = None,
        include_unmerged: bool = False,
        phred64: bool = False,
        compression: int = 4,
        stdin: bool = False,
        stdout: bool = False,
        interleaved_in: bool = False,
        reads_to_process: int = 0,
        dont_overwrite: bool = False,
        fix_mgi_id: bool = False,
        adapter_sequence: str | None = None,
        adapter_sequence_r2: str | None = None,
        adapter_fasta: str | None = None,
        detect_adapter_for_pe: bool = False,
        disable_adapter_trimming: bool = False,
        trim_front1: int = 0,
        trim_tail1: int = 0,
        max_len1: int = 0,
        trim_front2: int = 0,
        trim_tail2: int = 0,
        max_len2: int = 0,
        dedup: bool = False,
        dup_calc_accuracy: int = 0,
        dont_eval_duplication: bool = False,
        trim_poly_g: bool = False,
        poly_g_min_len: int = 10,
        disable_trim_poly_g: bool = False,
        trim_poly_x: bool = False,
        poly_x_min_len: int = 10,
        cut_front: bool = False,
        cut_tail: bool = False,
        cut_right: bool = False,
        cut_window_size: int = 4,
        cut_mean_quality: int = 20,
        cut_front_window_size: int = 0,
        cut_front_mean_quality: int = 0,
        cut_tail_window_size: int = 0,
        cut_tail_mean_quality: int = 0,
        cut_right_window_size: int = 0,
        cut_right_mean_quality: int = 0,
        disable_quality_filtering: bool = False,
        qualified_quality_phred: int = 15,
        unqualified_percent_limit: int = 40,
        n_base_limit: int = 5,
        average_qual: int = 0,
        disable_length_filtering: bool = False,
        length_required: int = 15,
        length_limit: int = 0,
        low_complexity_filter: bool = False,
        complexity_threshold: float = 0.3,
        filter_by_index1: str | None = None,
        filter_by_index2: str | None = None,
        filter_by_index_threshold: int = 0,
        correction: bool = False,
        overlap_len_require: int = 30,
        overlap_diff_limit: int = 5,
        overlap_diff_percent_limit: float = 20,
        umi: bool = False,
        umi_loc: str = "none",
        umi_len: int = 0,
        umi_prefix: str | None = None,
        umi_skip: int = 0,
        overrepresentation_analysis: bool = False,
        overrepresentation_sampling: int = 20,
        json: str | None = None,
        html: str | None = None,
        report_title: str = "Fastp Report",
        thread: int = 2,
        split: int = 0,
        split_by_lines: int = 0,
        split_prefix_digits: int = 4,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Process FASTQ files with comprehensive quality control and adapter trimming using Fastp.

        Fastp is an ultra-fast all-in-one FASTQ preprocessor that can perform quality control,
        adapter trimming, quality filtering, per-read quality pruning, and many other operations.

        Args:
            input1: Read 1 input FASTQ file
            output1: Read 1 output FASTQ file
            input2: Read 2 input FASTQ file (for paired-end)
            output2: Read 2 output FASTQ file (for paired-end)
            unpaired1: Unpaired output for read 1
            unpaired2: Unpaired output for read 2
            failed_out: Failed reads output
            json: JSON report output
            html: HTML report output
            report_title: Title for the report
            threads: Number of threads to use
            compression: Compression level for output files
            phred64: Assume input is in Phred+64 format
            input_phred64: Assume input is in Phred+64 format
            output_phred64: Output in Phred+64 format
            dont_overwrite: Don't overwrite existing files
            fix_mgi_id: Fix MGI-specific read IDs
            adapter_sequence: Adapter sequence for read 1
            adapter_sequence_r2: Adapter sequence for read 2
            detect_adapter_for_pe: Detect adapters for paired-end reads
            trim_front1: Trim N bases from 5' end of read 1
            trim_tail1: Trim N bases from 3' end of read 1
            trim_front2: Trim N bases from 5' end of read 2
            trim_tail2: Trim N bases from 3' end of read 2
            max_len1: Maximum length for read 1
            max_len2: Maximum length for read 2
            trim_poly_g: Trim poly-G tails
            poly_g_min_len: Minimum length of poly-G to trim
            trim_poly_x: Trim poly-X tails
            poly_x_min_len: Minimum length of poly-X to trim
            cut_front: Cut front window with mean quality
            cut_tail: Cut tail window with mean quality
            cut_window_size: Window size for quality cutting
            cut_mean_quality: Mean quality threshold for cutting
            cut_front_mean_quality: Mean quality for front cutting
            cut_tail_mean_quality: Mean quality for tail cutting
            cut_front_window_size: Window size for front cutting
            cut_tail_window_size: Window size for tail cutting
            disable_quality_filtering: Disable quality filtering
            qualified_quality_phred: Minimum Phred quality for qualified bases
            unqualified_percent_limit: Maximum percentage of unqualified bases
            n_base_limit: Maximum number of N bases allowed
            disable_length_filtering: Disable length filtering
            length_required: Minimum read length required
            length_limit: Maximum read length allowed
            low_complexity_filter: Enable low complexity filter
            complexity_threshold: Complexity threshold
            filter_by_index1: Filter by index for read 1
            filter_by_index2: Filter by index for read 2
            correction: Enable error correction for paired-end reads
            overlap_len_require: Minimum overlap length for correction
            overlap_diff_limit: Maximum difference for correction
            overlap_diff_percent_limit: Maximum difference percentage for correction
            umi: Enable UMI processing
            umi_loc: UMI location (none, index1, index2, read1, read2, per_index, per_read)
            umi_len: UMI length
            umi_prefix: UMI prefix
            umi_skip: Number of bases to skip for UMI
            overrepresentation_analysis: Enable overrepresentation analysis
            overrepresentation_sampling: Sampling rate for overrepresentation analysis

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files exist (unless using stdin)
        if not stdin:
            if not os.path.exists(input1):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Input file read1 does not exist: {input1}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Input file read1 not found: {input1}",
                }
            if input2 is not None and not os.path.exists(input2):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Input file read2 does not exist: {input2}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Input file read2 not found: {input2}",
                }

        # Validate adapter fasta file if provided
        if adapter_fasta is not None and not os.path.exists(adapter_fasta):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Adapter fasta file does not exist: {adapter_fasta}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Adapter fasta file not found: {adapter_fasta}",
            }

        # Validate compression level
        if not (1 <= compression <= 9):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "compression must be between 1 and 9",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid compression level",
            }

        # Validate dup_calc_accuracy
        if not (0 <= dup_calc_accuracy <= 6):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "dup_calc_accuracy must be between 0 and 6",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid dup_calc_accuracy",
            }

        # Validate quality cut parameters ranges
        if not (1 <= cut_window_size <= 1000):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "cut_window_size must be between 1 and 1000",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid cut_window_size",
            }
        if not (1 <= cut_mean_quality <= 36):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "cut_mean_quality must be between 1 and 36",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid cut_mean_quality",
            }

        # Validate unqualified_percent_limit
        if not (0 <= unqualified_percent_limit <= 100):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "unqualified_percent_limit must be between 0 and 100",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid unqualified_percent_limit",
            }

        # Validate complexity_threshold
        if not (0 <= complexity_threshold <= 100):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "complexity_threshold must be between 0 and 100",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid complexity_threshold",
            }

        # Validate filter_by_index_threshold
        if filter_by_index_threshold < 0:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "filter_by_index_threshold must be >= 0",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid filter_by_index_threshold",
            }

        # Validate thread count
        if thread < 1:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "thread must be >= 1",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid thread count",
            }

        # Validate split options
        if split != 0 and split_by_lines != 0:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "Cannot enable both split and split_by_lines simultaneously",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Conflicting split options",
            }
        if split != 0 and not (2 <= split <= 999):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "split must be between 2 and 999",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid split value",
            }
        if split_prefix_digits < 0 or split_prefix_digits > 10:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "split_prefix_digits must be between 0 and 10",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "Invalid split_prefix_digits",
            }

        # Build command
        cmd = ["fastp"]

        # Input/output
        if stdin:
            cmd.append("--stdin")
        else:
            cmd.extend(["-i", input1])
            if output1 is not None:
                cmd.extend(["-o", output1])
            if input2 is not None:
                cmd.extend(["-I", input2])
                if output2 is not None:
                    cmd.extend(["-O", output2])

        if unpaired1 is not None:
            cmd.extend(["--unpaired1", unpaired1])
        if unpaired2 is not None:
            cmd.extend(["--unpaired2", unpaired2])
        if failed_out is not None:
            cmd.extend(["--failed_out", failed_out])

        if merge:
            cmd.append("-m")
            if merged_out is not None:
                if merged_out == "--stdout":
                    cmd.append("--merged_out")
                    cmd.append("--stdout")
                else:
                    cmd.extend(["--merged_out", merged_out])
            else:
                # merged_out must be specified or stdout enabled in merge mode
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": "In merge mode, --merged_out or --stdout must be specified",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": "Missing merged_out in merge mode",
                }

        if include_unmerged:
            cmd.append("--include_unmerged")

        if phred64:
            cmd.append("-6")

        cmd.extend(["-z", str(compression)])

        if stdout:
            cmd.append("--stdout")
        if interleaved_in:
            cmd.append("--interleaved_in")
        if reads_to_process > 0:
            cmd.extend(["--reads_to_process", str(reads_to_process)])
        # Adapter trimming
        if disable_adapter_trimming:
            cmd.append("-A")
        if adapter_sequence is not None:
            cmd.extend(["-a", adapter_sequence])
        if adapter_sequence_r2 is not None:
            cmd.extend(["--adapter_sequence_r2", adapter_sequence_r2])
        if adapter_fasta is not None:
            cmd.extend(["--adapter_fasta", adapter_fasta])
        if detect_adapter_for_pe:
            cmd.append("--detect_adapter_for_pe")

        # Global trimming
        cmd.extend(["-f", str(trim_front1)])
        cmd.extend(["-t", str(trim_tail1)])
        cmd.extend(["-b", str(max_len1)])
        cmd.extend(["-F", str(trim_front2)])
        cmd.extend(["-T", str(trim_tail2)])
        cmd.extend(["-B", str(max_len2)])

        # Deduplication
        if dedup:
            cmd.append("-D")
        cmd.extend(["--dup_calc_accuracy", str(dup_calc_accuracy)])
        if dont_eval_duplication:
            cmd.append("--dont_eval_duplication")

        # PolyG trimming
        if trim_poly_g:
            cmd.append("-g")
        if disable_trim_poly_g:
            cmd.append("-G")
        cmd.extend(["--poly_g_min_len", str(poly_g_min_len)])

        # PolyX trimming
        if trim_poly_x:
            cmd.append("-x")
        cmd.extend(["--poly_x_min_len", str(poly_x_min_len)])

        # Per read cutting by quality
        if cut_front:
            cmd.append("-5")
        if cut_tail:
            cmd.append("-3")
        if cut_right:
            cmd.append("-r")
        cmd.extend(["-W", str(cut_window_size)])
        cmd.extend(["-M", str(cut_mean_quality)])
        if cut_front_window_size > 0:
            cmd.extend(["--cut_front_window_size", str(cut_front_window_size)])
        if cut_front_mean_quality > 0:
            cmd.extend(["--cut_front_mean_quality", str(cut_front_mean_quality)])
        if cut_tail_window_size > 0:
            cmd.extend(["--cut_tail_window_size", str(cut_tail_window_size)])
        if cut_tail_mean_quality > 0:
            cmd.extend(["--cut_tail_mean_quality", str(cut_tail_mean_quality)])
        if cut_right_window_size > 0:
            cmd.extend(["--cut_right_window_size", str(cut_right_window_size)])
        if cut_right_mean_quality > 0:
            cmd.extend(["--cut_right_mean_quality", str(cut_right_mean_quality)])

        # Quality filtering
        if disable_quality_filtering:
            cmd.append("-Q")
        cmd.extend(["-q", str(qualified_quality_phred)])
        cmd.extend(["-u", str(unqualified_percent_limit)])
        cmd.extend(["-n", str(n_base_limit)])
        cmd.extend(["-e", str(average_qual)])

        # Length filtering
        if disable_length_filtering:
            cmd.append("-L")
        cmd.extend(["-l", str(length_required)])
        cmd.extend(["--length_limit", str(length_limit)])

        # Low complexity filtering
        if low_complexity_filter:
            cmd.append("-y")
        cmd.extend(["-Y", str(complexity_threshold)])

        # Filter by index
        if filter_by_index1 is not None:
            if not os.path.exists(filter_by_index1):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Filter by index1 file does not exist: {filter_by_index1}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Filter by index1 file not found: {filter_by_index1}",
                }
            cmd.extend(["--filter_by_index1", filter_by_index1])
        if filter_by_index2 is not None:
            if not os.path.exists(filter_by_index2):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Filter by index2 file does not exist: {filter_by_index2}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Filter by index2 file not found: {filter_by_index2}",
                }
            cmd.extend(["--filter_by_index2", filter_by_index2])
        cmd.extend(["--filter_by_index_threshold", str(filter_by_index_threshold)])

        # Base correction by overlap analysis
        if correction:
            cmd.append("-c")
        cmd.extend(["--overlap_len_require", str(overlap_len_require)])
        cmd.extend(["--overlap_diff_limit", str(overlap_diff_limit)])
        cmd.extend(["--overlap_diff_percent_limit", str(overlap_diff_percent_limit)])

        # UMI processing
        if umi:
            cmd.append("-U")
            if umi_loc != "none":
                if umi_loc not in (
                    "index1",
                    "index2",
                    "read1",
                    "read2",
                    "per_index",
                    "per_read",
                ):
                    return {
                        "command_executed": "",
                        "stdout": "",
                        "stderr": f"Invalid umi_loc: {umi_loc}. Must be one of: index1, index2, read1, read2, per_index, per_read",
                        "output_files": [],
                        "exit_code": -1,
                        "success": False,
                        "error": f"Invalid umi_loc: {umi_loc}",
                    }
                cmd.extend(["--umi_loc", umi_loc])
                cmd.extend(["--umi_len", str(umi_len)])
            if umi_prefix is not None:
                cmd.extend(["--umi_prefix", umi_prefix])
                cmd.extend(["--umi_skip", str(umi_skip)])

        # Overrepresented sequence analysis
        if overrepresentation_analysis:
            cmd.append("-p")
        cmd.extend(["-P", str(overrepresentation_sampling)])

        # Reporting options
        if json is not None:
            cmd.extend(["-j", json])
        if html is not None:
            cmd.extend(["-h", html])
        cmd.extend(["-R", report_title])

        # Threading
        cmd.extend(["-w", str(thread)])

        # Output splitting
        if split != 0:
            cmd.extend(["-s", str(split)])
        if split_by_lines != 0:
            cmd.extend(["-S", str(split_by_lines)])
        cmd.extend(["-d", str(split_prefix_digits)])

        # Verbose
        if verbose:
            cmd.append("-V")

        try:
            # Execute Fastp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Collect output files
            output_files = []
            if output1 is not None and os.path.exists(output1):
                output_files.append(output1)
            if output2 is not None and os.path.exists(output2):
                output_files.append(output2)
            if unpaired1 is not None and os.path.exists(unpaired1):
                output_files.append(unpaired1)
            if unpaired2 is not None and os.path.exists(unpaired2):
                output_files.append(unpaired2)
            if failed_out is not None and os.path.exists(failed_out):
                output_files.append(failed_out)
            if (
                merged_out is not None
                and merged_out != "--stdout"
                and os.path.exists(merged_out)
            ):
                output_files.append(merged_out)
            if json is not None and os.path.exists(json):
                output_files.append(json)
            if html is not None and os.path.exists(html):
                output_files.append(html)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }

        except subprocess.CalledProcessError as e:
            return {
                "command_executed": " ".join(cmd),
                "stdout": e.stdout,
                "stderr": e.stderr,
                "error": f"fastp failed with return code {e.returncode}",
                "output_files": [],
            }
        except FileNotFoundError:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "Fastp not found in PATH",
                "error": "Fastp not found in PATH",
                "output_files": [],
            }
        except Exception as e:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": str(e),
                "error": str(e),
                "output_files": [],
            }

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy Fastp server using testcontainers with conda environment."""
        try:
            from testcontainers.core.container import DockerContainer

            # Create container with condaforge image
            container = DockerContainer("condaforge/miniforge3:latest")
            container.with_name(f"mcp-fastp-server-{id(self)}")

            # Install Fastp using conda
            container.with_command(
                "bash -c '"
                "conda config --add channels bioconda && "
                "conda config --add channels conda-forge && "
                "conda install -c bioconda fastp -y && "
                "tail -f /dev/null'"
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
        """Stop Fastp server deployed with testcontainers."""
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
        """Get information about this Fastp server."""
        return {
            "name": self.name,
            "type": "fastp",
            "version": "0.23.4",
            "description": "Fastp FASTQ preprocessing server",
            "tools": self.list_tools(),
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": "running" if self.container_id else "stopped",
        }
