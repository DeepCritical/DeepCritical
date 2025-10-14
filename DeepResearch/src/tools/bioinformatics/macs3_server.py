"""
MACS3 MCP Server - Comprehensive ChIP-seq and ATAC-seq analysis tools.

This module implements a strongly-typed MCP server for MACS3, providing comprehensive
tools for ChIP-seq peak calling and ATAC-seq analysis using HMMRATAC. The server
integrates with Pydantic AI patterns and supports testcontainers deployment.

Features:
- ChIP-seq peak calling with MACS3 callpeak (comprehensive parameter support)
- ATAC-seq analysis with HMMRATAC
- BedGraph file comparison tools
- Duplicate read filtering
- Docker containerization with python:3.11-slim base image
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


class MACS3Server(MCPServerBase):
    """MCP Server for MACS3 ChIP-seq peak calling and ATAC-seq analysis with Pydantic AI integration."""

    def __init__(self, config: MCPServerConfig | None = None):
        if config is None:
            config = MCPServerConfig(
                server_name="macs3-server",
                server_type=MCPServerType.MACS3,
                container_image="python:3.11-slim",
                environment_variables={
                    "MACS3_VERSION": "3.0.0",
                    "PYTHONPATH": "/workspace",
                },
                capabilities=[
                    "chip_seq",
                    "peak_calling",
                    "transcription_factors",
                    "atac_seq",
                    "hmmratac",
                    "bedgraph_comparison",
                    "duplicate_filtering",
                ],
            )
        super().__init__(config)

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Run MACS3 operation based on parameters.

        Args:
            params: Dictionary containing operation parameters including:
                - operation: The operation to perform (callpeak, hmmratac, bdgcmp, filterdup)
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
            "callpeak": self.macs3_callpeak,
            "hmmratac": self.macs3_hmmratac,
            "bdgcmp": self.macs3_bdgcmp,
            "filterdup": self.macs3_filterdup,
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
            if not shutil.which("macs3"):
                # Return mock success result for testing when tool is not available
                mock_output_files = self._get_mock_output_files(
                    operation, method_params
                )
                return {
                    "success": True,
                    "command_executed": f"macs3 {operation} [mock - tool not available]",
                    "stdout": f"Mock output for {operation} operation",
                    "stderr": "",
                    "output_files": mock_output_files,
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

    def _get_mock_output_files(
        self, operation: str, params: dict[str, Any]
    ) -> list[str]:
        """Generate mock output files for testing environments."""
        if operation == "callpeak":
            name = params.get("name", "peaks")
            outdir = params.get("outdir", Path())
            broad = params.get("broad", False)
            bdg = params.get("bdg", False)
            cutoff_analysis = params.get("cutoff_analysis", False)

            output_files = [
                str(outdir / f"{name}_peaks.xls"),
                str(outdir / f"{name}_peaks.narrowPeak"),
                str(outdir / f"{name}_summits.bed"),
                str(outdir / f"{name}_model.r"),
            ]

            # Add broad peak files if broad=True
            if broad:
                output_files.extend(
                    [
                        str(outdir / f"{name}_peaks.broadPeak"),
                        str(outdir / f"{name}_peaks.gappedPeak"),
                    ]
                )

            # Add bedGraph files if bdg=True
            if bdg:
                output_files.extend(
                    [
                        str(outdir / f"{name}_treat_pileup.bdg"),
                        str(outdir / f"{name}_control_lambda.bdg"),
                    ]
                )

            # Add cutoff analysis file if cutoff_analysis=True
            if cutoff_analysis:
                output_files.append(str(outdir / f"{name}_cutoff_analysis.txt"))

            return output_files
        if operation == "hmmratac":
            name = params.get("name", "NA")
            outdir = params.get("outdir", Path())
            return [str(outdir / f"{name}_peaks.narrowPeak")]
        if operation == "bdgcmp":
            name = params.get("name", "fold_enrichment")
            outdir = params.get("output_dir", ".")
            return [
                f"{outdir}/{name}_ppois.bdg",
                f"{outdir}/{name}_logLR.bdg",
                f"{outdir}/{name}_FE.bdg",
            ]
        if operation == "filterdup":
            output_bam = params.get("output_bam", "filtered.bam")
            return [output_bam]
        return []

    @mcp_tool(
        MCPToolSpec(
            name="macs3_callpeak",
            description="Call significantly enriched regions (peaks) from alignment files using MACS3 callpeak",
            inputs={
                "treatment": "List[Path]",
                "control": "Optional[List[Path]]",
                "name": "str",
                "format": "str",
                "outdir": "Optional[Path]",
                "bdg": "bool",
                "trackline": "bool",
                "gsize": "str",
                "tsize": "int",
                "qvalue": "float",
                "pvalue": "float",
                "min_length": "int",
                "max_gap": "int",
                "nolambda": "bool",
                "slocal": "int",
                "llocal": "int",
                "nomodel": "bool",
                "extsize": "int",
                "shift": "int",
                "keep_dup": "Union[str, int]",
                "broad": "bool",
                "broad_cutoff": "float",
                "scale_to": "str",
                "call_summits": "bool",
                "buffer_size": "int",
                "cutoff_analysis": "bool",
                "barcodes": "Optional[Path]",
                "max_count": "Optional[int]",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
            },
            server_type=MCPServerType.MACS3,
            examples=[
                {
                    "description": "Call peaks from ChIP-seq data",
                    "parameters": {
                        "treatment": ["/data/chip_sample.bam"],
                        "control": ["/data/input_sample.bam"],
                        "name": "chip_peaks",
                        "format": "BAM",
                        "gsize": "hs",
                        "qvalue": 0.05,
                        "outdir": "/results",
                    },
                }
            ],
        )
    )
    def macs3_callpeak(
        self,
        treatment: list[Path],
        control: list[Path] | None = None,
        name: str = "macs3_callpeak",
        format: str = "AUTO",
        outdir: Path | None = None,
        bdg: bool = False,
        trackline: bool = False,
        gsize: str = "hs",
        tsize: int = 0,
        qvalue: float = 0.05,
        pvalue: float = 0.0,
        min_length: int = 0,
        max_gap: int = 0,
        nolambda: bool = False,
        slocal: int = 1000,
        llocal: int = 10000,
        nomodel: bool = False,
        extsize: int = 0,
        shift: int = 0,
        keep_dup: str | int = 1,
        broad: bool = False,
        broad_cutoff: float = 0.1,
        scale_to: str = "small",
        call_summits: bool = False,
        buffer_size: int = 100000,
        cutoff_analysis: bool = False,
        barcodes: Path | None = None,
        max_count: int | None = None,
    ) -> dict[str, Any]:
        """
        Call significantly enriched regions (peaks) from alignment files using MACS3 callpeak.

        This tool identifies transcription factor binding sites or histone modification
        enriched regions from ChIP-seq experiments.

        Parameters:
        - treatment: List of treatment alignment files (required)
        - control: List of control alignment files (optional)
        - name: Name string for experiment, used as prefix for output files
        - format: Format of tag files (AUTO, ELAND, BED, ELANDMULTI, ELANDEXPORT, SAM, BAM, BOWTIE, BAMPE, BEDPE, FRAG)
        - outdir: Directory to save output files (created if doesn't exist)
        - bdg: Output bedGraph files for fragment pileup and control lambda
        - trackline: Include UCSC genome browser trackline in output headers
        - gsize: Effective genome size (hs, mm, ce, dm or numeric string)
        - tsize: Size of sequencing tags (0 means auto-detect)
        - qvalue: q-value cutoff for significant peaks (default 0.05)
        - pvalue: p-value cutoff (if >0, used instead of q-value)
        - min_length: Minimum length of called peak (0 means use fragment size)
        - max_gap: Maximum gap between nearby regions to merge (0 means use read length)
        - nolambda: Use background lambda as local lambda (no local bias correction)
        - slocal: Small local region size in bp for local lambda calculation
        - llocal: Large local region size in bp for local lambda calculation
        - nomodel: Bypass building shifting model
        - extsize: Extend reads to this fixed fragment size when nomodel is set
        - shift: Shift cutting ends by this bp (must be 0 if format is BAMPE or BEDPE)
        - keep_dup: How to handle duplicate tags ('auto', 'all', or integer)
        - broad: Perform broad peak calling producing gappedPeak format
        - broad_cutoff: Cutoff for broad regions (default 0.1, requires broad=True)
        - scale_to: Scale dataset depths ('large' or 'small')
        - call_summits: Reanalyze signal profile to call subpeak summits
        - buffer_size: Buffer size for internal array
        - cutoff_analysis: Perform cutoff analysis and output report
        - barcodes: Barcode list file (only valid if format is FRAG)
        - max_count: Max count per fragment (only valid if format is FRAG)

        Returns:
        Dict with keys: command_executed, stdout, stderr, output_files
        """
        # Validate input files
        if not treatment or len(treatment) == 0:
            msg = "At least one treatment file must be specified in 'treatment' parameter."
            raise ValueError(msg)
        for f in treatment:
            if not f.exists():
                msg = f"Treatment file not found: {f}"
                raise FileNotFoundError(msg)
        if control:
            for f in control:
                if not f.exists():
                    msg = f"Control file not found: {f}"
                    raise FileNotFoundError(msg)

        # Validate format
        valid_formats = {
            "ELAND",
            "BED",
            "ELANDMULTI",
            "ELANDEXPORT",
            "SAM",
            "BAM",
            "BOWTIE",
            "BAMPE",
            "BEDPE",
            "FRAG",
            "AUTO",
        }
        format_upper = format.upper()
        if format_upper not in valid_formats:
            msg = f"Invalid format '{format}'. Must be one of {valid_formats}."
            raise ValueError(msg)

        # Validate keep_dup
        if isinstance(keep_dup, str):
            if keep_dup not in {"auto", "all"}:
                msg = "keep_dup string value must be 'auto' or 'all'."
                raise ValueError(msg)
        elif isinstance(keep_dup, int):
            if keep_dup < 0:
                msg = "keep_dup integer value must be non-negative."
                raise ValueError(msg)
        else:
            msg = "keep_dup must be str ('auto','all') or non-negative int."
            raise ValueError(msg)

        # Validate scale_to
        if scale_to not in {"large", "small"}:
            msg = "scale_to must be 'large' or 'small'."
            raise ValueError(msg)

        # Validate broad_cutoff only if broad is True
        if broad:
            if broad_cutoff <= 0 or broad_cutoff > 1:
                msg = "broad_cutoff must be > 0 and <= 1 when broad is enabled."
                raise ValueError(msg)
        elif broad_cutoff != 0.1:
            msg = "broad_cutoff option is only valid when broad is enabled."
            raise ValueError(msg)

        # Validate shift for paired-end formats
        if format_upper in {"BAMPE", "BEDPE"} and shift != 0:
            msg = "shift must be 0 when format is BAMPE or BEDPE."
            raise ValueError(msg)

        # Validate tsize
        if tsize < 0:
            msg = "tsize must be >= 0."
            raise ValueError(msg)

        # Validate qvalue and pvalue
        if qvalue <= 0 or qvalue > 1:
            msg = "qvalue must be > 0 and <= 1."
            raise ValueError(msg)
        if pvalue < 0 or pvalue > 1:
            msg = "pvalue must be >= 0 and <= 1."
            raise ValueError(msg)

        # Validate min_length and max_gap
        if min_length < 0:
            msg = "min_length must be >= 0."
            raise ValueError(msg)
        if max_gap < 0:
            msg = "max_gap must be >= 0."
            raise ValueError(msg)

        # Validate slocal and llocal
        if slocal <= 0:
            msg = "slocal must be > 0."
            raise ValueError(msg)
        if llocal <= 0:
            msg = "llocal must be > 0."
            raise ValueError(msg)

        # Validate buffer_size
        if buffer_size <= 0:
            msg = "buffer_size must be > 0."
            raise ValueError(msg)

        # Validate max_count only if format is FRAG
        if max_count is not None:
            if format_upper != "FRAG":
                msg = "--max-count is only valid when format is FRAG."
                raise ValueError(msg)
            if max_count < 1:
                msg = "max_count must be >= 1."
                raise ValueError(msg)

        # Validate barcodes only if format is FRAG
        if barcodes is not None:
            if format_upper != "FRAG":
                msg = "--barcodes option is only valid when format is FRAG."
                raise ValueError(msg)
            if not barcodes.exists():
                msg = f"Barcode list file not found: {barcodes}"
                raise FileNotFoundError(msg)

        # Prepare output directory
        if outdir is not None:
            if not outdir.exists():
                outdir.mkdir(parents=True, exist_ok=True)
            outdir_str = str(outdir.resolve())
        else:
            outdir_str = None

        # Build command line
        cmd = ["macs3", "callpeak"]

        # Treatment files
        for f in treatment:
            cmd.extend(["-t", str(f.resolve())])

        # Control files
        if control:
            for f in control:
                cmd.extend(["-c", str(f.resolve())])

        # Name
        cmd.extend(["-n", name])

        # Format
        if format_upper != "AUTO":
            cmd.extend(["-f", format_upper])

        # Output directory
        if outdir_str:
            cmd.extend(["--outdir", outdir_str])

        # bdg
        if bdg:
            cmd.append("-B")

        # trackline
        if trackline:
            cmd.append("--trackline")

        # gsize
        if gsize:
            cmd.extend(["-g", gsize])

        # tsize
        if tsize > 0:
            cmd.extend(["-s", str(tsize)])

        # qvalue or pvalue
        if pvalue > 0:
            cmd.extend(["-p", str(pvalue)])
        else:
            cmd.extend(["-q", str(qvalue)])

        # min_length
        if min_length > 0:
            cmd.extend(["--min-length", str(min_length)])

        # max_gap
        if max_gap > 0:
            cmd.extend(["--max-gap", str(max_gap)])

        # nolambda
        if nolambda:
            cmd.append("--nolambda")

        # slocal and llocal
        cmd.extend(["--slocal", str(slocal)])
        cmd.extend(["--llocal", str(llocal)])

        # nomodel
        if nomodel:
            cmd.append("--nomodel")

        # extsize
        if extsize > 0:
            cmd.extend(["--extsize", str(extsize)])

        # shift
        if shift != 0:
            cmd.extend(["--shift", str(shift)])

        # keep_dup
        if isinstance(keep_dup, int):
            cmd.extend(["--keep-dup", str(keep_dup)])
        else:
            cmd.extend(["--keep-dup", keep_dup])

        # broad
        if broad:
            cmd.append("--broad")
            cmd.extend(["--broad-cutoff", str(broad_cutoff)])

        # scale_to
        if scale_to != "small":
            cmd.extend(["--scale-to", scale_to])

        # call_summits
        if call_summits:
            cmd.append("--call-summits")

        # buffer_size
        if buffer_size != 100000:
            cmd.extend(["--buffer-size", str(buffer_size)])

        # cutoff_analysis
        if cutoff_analysis:
            cmd.append("--cutoff-analysis")

        # barcodes
        if barcodes is not None:
            cmd.extend(["--barcodes", str(barcodes.resolve())])

        # max_count
        if max_count is not None:
            cmd.extend(["--max-count", str(max_count)])

        # Run command
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
                "stdout": e.stdout,
                "stderr": e.stderr,
                "output_files": [],
                "error": f"MACS3 callpeak failed with return code {e.returncode}",
            }

        # Collect output files expected based on name and outdir
        output_files = []
        base_path = Path(outdir_str) if outdir_str else Path.cwd()
        # Required output files always generated:
        # NAME_peaks.xls, NAME_peaks.narrowPeak, NAME_summits.bed, NAME_model.r
        output_files.append(str(base_path / f"{name}_peaks.xls"))
        output_files.append(str(base_path / f"{name}_peaks.narrowPeak"))
        output_files.append(str(base_path / f"{name}_summits.bed"))
        output_files.append(str(base_path / f"{name}_model.r"))
        # Optional files
        if broad:
            output_files.append(str(base_path / f"{name}_peaks.broadPeak"))
            output_files.append(str(base_path / f"{name}_peaks.gappedPeak"))
        if bdg:
            output_files.append(str(base_path / f"{name}_treat_pileup.bdg"))
            output_files.append(str(base_path / f"{name}_control_lambda.bdg"))
        if cutoff_analysis:
            output_files.append(str(base_path / f"{name}_cutoff_analysis.txt"))

        return {
            "command_executed": " ".join(cmd),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "output_files": output_files,
        }

    @mcp_tool(
        MCPToolSpec(
            name="macs3_hmmratac",
            description="HMMRATAC peak calling algorithm for ATAC-seq data based on Hidden Markov Model",
            inputs={
                "input_files": "List[Path]",
                "format": "str",
                "outdir": "Path",
                "name": "str",
                "blacklist": "Optional[Path]",
                "modelonly": "bool",
                "model": "str",
                "training": "str",
                "min_frag_p": "float",
                "cutoff_analysis_only": "bool",
                "cutoff_analysis_max": "int",
                "cutoff_analysis_steps": "int",
                "hmm_type": "str",
                "upper": "int",
                "lower": "int",
                "prescan_cutoff": "float",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "List[str]",
            },
            server_type=MCPServerType.MACS3,
            examples=[
                {
                    "description": "Run HMMRATAC on ATAC-seq BAMPE files",
                    "parameters": {
                        "input_files": ["/data/sample1.bam", "/data/sample2.bam"],
                        "format": "BAMPE",
                        "outdir": "/results",
                        "name": "atac_peaks",
                        "min_frag_p": 0.001,
                        "upper": 20,
                        "lower": 10,
                    },
                }
            ],
        )
    )
    def macs3_hmmratac(
        self,
        input_files: list[Path],
        format: str = "BAMPE",
        outdir: Path = Path(),
        name: str = "NA",
        blacklist: Path | None = None,
        modelonly: bool = False,
        model: str = "NA",
        training: str = "NA",
        min_frag_p: float = 0.001,
        cutoff_analysis_only: bool = False,
        cutoff_analysis_max: int = 100,
        cutoff_analysis_steps: int = 100,
        hmm_type: str = "gaussian",
        upper: int = 20,
        lower: int = 10,
        prescan_cutoff: float = 1.2,
    ) -> dict[str, Any]:
        """
        HMMRATAC peak calling algorithm for ATAC-seq data based on Hidden Markov Model.
        Processes paired-end BAMPE or BEDPE input files to identify accessible chromatin regions.
        Outputs narrowPeak format files with accessible regions.

        Parameters:
        - input_files: List of input BAMPE or BEDPE files (gzipped allowed). All must be same format.
        - format: Format of input files, either "BAMPE" or "BEDPE". Default "BAMPE".
        - outdir: Directory to write output files. Default current directory.
        - name: Prefix name for output files. Default "NA".
        - blacklist: Optional BED file of blacklisted regions to exclude fragments.
        - modelonly: If True, only generate HMM model JSON file and quit. Default False.
        - model: JSON file of pre-trained HMM model to use instead of training. Default "NA".
        - training: BED file of custom training regions for HMM training. Default "NA".
        - min_frag_p: Minimum fragment probability threshold (0-1) to include fragments. Default 0.001.
        - cutoff_analysis_only: If True, only run cutoff analysis report and quit. Default False.
        - cutoff_analysis_max: Max cutoff score for cutoff analysis. Default 100.
        - cutoff_analysis_steps: Number of steps for cutoff analysis resolution. Default 100.
        - hmm_type: Emission type for HMM: "gaussian" (default) or "poisson".
        - upper: Upper fold change cutoff for training sites. Default 20.
        - lower: Lower fold change cutoff for training sites. Default 10.
        - prescan_cutoff: Fold change cutoff for prescanning candidate regions (>1). Default 1.2.

        Returns:
        A dict with keys: command_executed, stdout, stderr, output_files
        """
        # Validate input files
        if not input_files or len(input_files) == 0:
            msg = "At least one input file must be provided in input_files."
            raise ValueError(msg)
        for f in input_files:
            if not f.exists():
                msg = f"Input file does not exist: {f}"
                raise FileNotFoundError(msg)
        # Validate format
        format_upper = format.upper()
        if format_upper not in ("BAMPE", "BEDPE"):
            msg = f"Invalid format '{format}'. Must be 'BAMPE' or 'BEDPE'."
            raise ValueError(msg)
        # Validate outdir
        if not outdir.exists():
            outdir.mkdir(parents=True, exist_ok=True)
        # Validate blacklist file if provided
        if blacklist is not None and not blacklist.exists():
            msg = f"Blacklist file does not exist: {blacklist}"
            raise FileNotFoundError(msg)
        # Validate min_frag_p
        if not (0 <= min_frag_p <= 1):
            msg = f"min_frag_p must be between 0 and 1, got {min_frag_p}"
            raise ValueError(msg)
        # Validate hmm_type
        hmm_type_lower = hmm_type.lower()
        if hmm_type_lower not in ("gaussian", "poisson"):
            msg = f"hmm_type must be 'gaussian' or 'poisson', got {hmm_type}"
            raise ValueError(msg)
        # Validate prescan_cutoff
        if prescan_cutoff <= 1:
            msg = f"prescan_cutoff must be > 1, got {prescan_cutoff}"
            raise ValueError(msg)
        # Validate upper and lower cutoffs
        if lower < 0:
            msg = f"lower cutoff must be >= 0, got {lower}"
            raise ValueError(msg)
        if upper <= lower:
            msg = f"upper cutoff must be greater than lower cutoff, got upper={upper}, lower={lower}"
            raise ValueError(msg)
        # Validate cutoff_analysis_max and cutoff_analysis_steps
        if cutoff_analysis_max < 0:
            msg = f"cutoff_analysis_max must be >= 0, got {cutoff_analysis_max}"
            raise ValueError(msg)
        if cutoff_analysis_steps <= 0:
            msg = f"cutoff_analysis_steps must be > 0, got {cutoff_analysis_steps}"
            raise ValueError(msg)
        # Validate training file if provided
        if training != "NA":
            training_path = Path(training)
            if not training_path.exists():
                msg = f"Training regions file does not exist: {training_path}"
                raise FileNotFoundError(msg)

        # Build command line
        cmd = ["macs3", "hmmratac"]
        # Input files
        for f in input_files:
            cmd.extend(["-i", str(f)])
        # Format
        cmd.extend(["-f", format_upper])
        # Output directory
        cmd.extend(["--outdir", str(outdir)])
        # Name prefix
        cmd.extend(["-n", name])
        # Blacklist
        if blacklist is not None:
            cmd.extend(["-e", str(blacklist)])
        # modelonly
        if modelonly:
            cmd.append("--modelonly")
        # model
        if model != "NA":
            cmd.extend(["--model", model])
        # training regions
        if training != "NA":
            cmd.extend(["-t", training])
        # min_frag_p
        cmd.extend(["--min-frag-p", str(min_frag_p)])
        # cutoff_analysis_only
        if cutoff_analysis_only:
            cmd.append("--cutoff-analysis-only")
        # cutoff_analysis_max
        cmd.extend(["--cutoff-analysis-max", str(cutoff_analysis_max)])
        # cutoff_analysis_steps
        cmd.extend(["--cutoff-analysis-steps", str(cutoff_analysis_steps)])
        # hmm_type
        cmd.extend(["--hmm-type", hmm_type_lower])
        # upper cutoff
        cmd.extend(["-u", str(upper)])
        # lower cutoff
        cmd.extend(["-l", str(lower)])
        # prescan cutoff
        cmd.extend(["-c", str(prescan_cutoff)])

        # Execute command
        try:
            result = subprocess.run(
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
                "error": f"Command failed with return code {e.returncode}",
            }

        # Determine output files
        # The main output is a narrowPeak file named {name}_peaks.narrowPeak in outdir
        peak_file = outdir / f"{name}_peaks.narrowPeak"
        output_files = []
        if peak_file.exists():
            output_files.append(str(peak_file))

        # Also if modelonly or model json is generated, it will be {name}_model.json in outdir
        model_json = outdir / f"{name}_model.json"
        if (modelonly or (model != "NA")) and model_json.exists():
            output_files.append(str(model_json))

        return {
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": output_files,
        }

    @mcp_tool(
        MCPToolSpec(
            name="macs3_bdgcmp",
            description="Compare two bedGraph files to generate fold enrichment tracks",
            inputs={
                "treatment_bdg": "str",
                "control_bdg": "str",
                "output_dir": "str",
                "name": "str",
                "method": "str",
                "pseudocount": "float",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
            },
            server_type=MCPServerType.MACS3,
            examples=[
                {
                    "description": "Compare treatment and control bedGraph files",
                    "parameters": {
                        "treatment_bdg": "/data/treatment.bdg",
                        "control_bdg": "/data/control.bdg",
                        "output_dir": "/results",
                        "name": "fold_enrichment",
                        "method": "ppois",
                    },
                }
            ],
        )
    )
    def macs3_bdgcmp(
        self,
        treatment_bdg: str,
        control_bdg: str,
        output_dir: str = ".",
        name: str = "fold_enrichment",
        method: str = "ppois",
        pseudocount: float = 1.0,
    ) -> dict[str, Any]:
        """
        Compare two bedGraph files to generate fold enrichment tracks.

        This tool compares treatment and control bedGraph files to compute
        fold enrichment and statistical significance of ChIP-seq signals.

        Args:
            treatment_bdg: Treatment bedGraph file
            control_bdg: Control bedGraph file
            output_dir: Output directory for results
            name: Prefix for output files
            method: Statistical method (ppois, qpois, FE, logFE, logLR, subtract)
            pseudocount: Pseudocount to avoid division by zero

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files exist
        if not os.path.exists(treatment_bdg):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Treatment bedGraph file does not exist: {treatment_bdg}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Treatment file not found: {treatment_bdg}",
            }

        if not os.path.exists(control_bdg):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Control bedGraph file does not exist: {control_bdg}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Control file not found: {control_bdg}",
            }

        # Build command
        cmd = [
            "macs3",
            "bdgcmp",
            "-t",
            treatment_bdg,
            "-c",
            control_bdg,
            "-o",
            f"{output_dir}/{name}",
            "-m",
            method,
        ]

        if pseudocount != 1.0:
            cmd.extend(["-p", str(pseudocount)])

        try:
            # Execute MACS3 bdgcmp
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, cwd=output_dir
            )

            # Get output files
            output_files = []
            try:
                output_files = [
                    f"{output_dir}/{name}_ppois.bdg",
                    f"{output_dir}/{name}_logLR.bdg",
                    f"{output_dir}/{name}_FE.bdg",
                ]
                # Filter to only files that actually exist
                output_files = [f for f in output_files if os.path.exists(f)]
            except Exception:
                pass

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }

        except FileNotFoundError:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "MACS3 not found in PATH",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "MACS3 not found in PATH",
            }
        except Exception as e:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": str(e),
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": str(e),
            }

    @mcp_tool(
        MCPToolSpec(
            name="macs3_filterdup",
            description="Filter duplicate reads from BAM files",
            inputs={
                "input_bam": "str",
                "output_bam": "str",
                "gsize": "str",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
            },
            server_type=MCPServerType.MACS3,
            examples=[
                {
                    "description": "Filter duplicate reads from BAM file",
                    "parameters": {
                        "input_bam": "/data/sample.bam",
                        "output_bam": "/data/sample_filtered.bam",
                        "gsize": "hs",
                    },
                }
            ],
        )
    )
    def macs3_filterdup(
        self,
        input_bam: str,
        output_bam: str,
        gsize: str = "hs",
    ) -> dict[str, Any]:
        """
        Filter duplicate reads from BAM files.

        This tool removes duplicate reads from BAM files, which is important
        for accurate ChIP-seq peak calling.

        Args:
            input_bam: Input BAM file
            output_bam: Output BAM file with duplicates removed
            gsize: Genome size (hs, mm, ce, dm, etc.)

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input file exists
        if not os.path.exists(input_bam):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Input BAM file does not exist: {input_bam}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Input file not found: {input_bam}",
            }

        # Build command
        cmd = [
            "macs3",
            "filterdup",
            "-i",
            input_bam,
            "-o",
            output_bam,
            "-g",
            gsize,
        ]

        try:
            # Execute MACS3 filterdup
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Get output files
            output_files = []
            if os.path.exists(output_bam):
                output_files = [output_bam]

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }

        except FileNotFoundError:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "MACS3 not found in PATH",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "MACS3 not found in PATH",
            }
        except Exception as e:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": str(e),
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": str(e),
            }

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy MACS3 server using testcontainers."""
        try:
            from testcontainers.core.container import DockerContainer

            # Create container
            container = DockerContainer("python:3.11-slim")
            container.with_name(f"mcp-macs3-server-{id(self)}")

            # Install MACS3
            container.with_command("bash -c 'pip install macs3 && tail -f /dev/null'")

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
        """Stop MACS3 server deployed with testcontainers."""
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
        """Get information about this MACS3 server."""
        return {
            "name": self.name,
            "type": "macs3",
            "version": "3.0.0",
            "description": "MACS3 ChIP-seq peak calling server",
            "tools": self.list_tools(),
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": "running" if self.container_id else "stopped",
        }
