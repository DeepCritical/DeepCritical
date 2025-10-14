"""
Cutadapt MCP Server - Pydantic AI compatible MCP server for adapter trimming.

This module implements an MCP server for Cutadapt, a tool for trimming adapters
from high-throughput sequencing reads, following Pydantic AI MCP integration patterns.

This server can be used with Pydantic AI agents via MCPServerStdio toolset.

Usage with Pydantic AI:
```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

# Create MCP server toolset
cutadapt_server = MCPServerStdio(
    command='python',
    args=['cutadapt_server.py'],
    tool_prefix='cutadapt'
)

# Create agent with Cutadapt tools
agent = Agent(
    'openai:gpt-4o',
    toolsets=[cutadapt_server]
)

# Use Cutadapt tools in agent queries
async def main():
    async with agent:
        result = await agent.run(
            'Trim adapters from reads in /data/reads.fq with quality cutoff 20'
        )
        print(result.data)
```

Run the MCP server:
```bash
python cutadapt_server.py
```

The server exposes the following tool:
- cutadapt: Trim adapters from high-throughput sequencing reads
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal

# Type-only imports for conditional dependencies
if TYPE_CHECKING:
    from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase
    from DeepResearch.src.datatypes.mcp import MCPServerConfig, MCPServerType

try:
    from fastmcp import FastMCP

    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    _FastMCP = None

# Import base classes - may not be available in all environments
try:
    from DeepResearch.src.datatypes.bioinformatics_mcp import (
        MCPServerBase,  # type: ignore[import]
    )
    from DeepResearch.src.datatypes.mcp import (  # type: ignore[import]
        MCPServerConfig,
        MCPServerDeployment,
        MCPServerStatus,
        MCPServerType,
    )

    BASE_CLASS_AVAILABLE = True
except ImportError:
    # Fallback for environments without the full MCP framework
    BASE_CLASS_AVAILABLE = False
    MCPServerBase = object  # type: ignore[assignment]
    MCPServerConfig = type(None)  # type: ignore[assignment]
    MCPServerDeployment = type(None)  # type: ignore[assignment]
    MCPServerStatus = type(None)  # type: ignore[assignment]
    MCPServerType = type(None)  # type: ignore[assignment]

# Create MCP server instance if FastMCP is available
mcp = FastMCP("cutadapt-server") if FASTMCP_AVAILABLE else None


# Define the cutadapt function
def cutadapt(
    input_file: Path,
    output_file: Path | None = None,
    adapter: str | None = None,
    front_adapter: str | None = None,
    anywhere_adapter: str | None = None,
    adapter_2: str | None = None,
    front_adapter_2: str | None = None,
    anywhere_adapter_2: str | None = None,
    error_rate: float = 0.1,
    no_indels: bool = False,
    times: int = 1,
    overlap: int = 3,
    match_read_wildcards: bool = False,
    no_match_adapter_wildcards: bool = False,
    action: Literal["trim", "retain", "mask", "lowercase", "none"] = "trim",
    revcomp: bool = False,
    cut: list[int] | None = None,
    quality_cutoff: str | None = None,
    nextseq_trim: int | None = None,
    quality_base: int = 33,
    poly_a: bool = False,
    length: int | None = None,
    trim_n: bool = False,
    length_tag: str | None = None,
    strip_suffix: list[str] | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    rename: str | None = None,
    zero_cap: bool = False,
    minimum_length: str | None = None,
    maximum_length: str | None = None,
    max_n: float | None = None,
    max_expected_errors: float | None = None,
    discard_trimmed: bool = False,
    discard_untrimmed: bool = False,
    discard_casava: bool = False,
    quiet: bool = False,
    report: Literal["full", "minimal"] = "full",
    json_report: Path | None = None,
    fasta: bool = False,
    compression_level_1: bool = False,
    info_file: Path | None = None,
    rest_file: Path | None = None,
    wildcard_file: Path | None = None,
    too_short_output: Path | None = None,
    too_long_output: Path | None = None,
    untrimmed_output: Path | None = None,
    cores: int = 1,
    # Paired-end options
    adapter_r2: str | None = None,
    front_adapter_r2: str | None = None,
    anywhere_adapter_r2: str | None = None,
    cut_r2: int | None = None,
    quality_cutoff_r2: str | None = None,
):
    """
    Cutadapt trims adapters from high-throughput sequencing reads.
    Supports single-end and paired-end reads, multiple adapter types, quality trimming,
    filtering, and output options including compression and JSON reports.

    Parameters:
    - input_file: Path to input FASTA, FASTQ or unaligned BAM (single-end only).
    - output_file: Path to output file (FASTA/FASTQ). If omitted, writes to stdout.
    - adapter: 3' adapter sequence to trim from read 1.
    - front_adapter: 5' adapter sequence to trim from read 1.
    - anywhere_adapter: adapter sequence that can appear anywhere in read 1.
    - adapter_2: alias for adapter (3' adapter for read 1).
    - front_adapter_2: alias for front_adapter (5' adapter for read 1).
    - anywhere_adapter_2: alias for anywhere_adapter (anywhere adapter for read 1).
    - error_rate: max allowed error rate or number of errors (default 0.1).
    - no_indels: disallow indels in adapter matching.
    - times: number of times to search for adapters (default 1).
    - overlap: minimum overlap length for adapter matching (default 3).
    - match_read_wildcards: interpret IUPAC wildcards in reads.
    - no_match_adapter_wildcards: do not interpret wildcards in adapters.
    - action: action on adapter match: trim, retain, mask, lowercase, none (default trim).
    - revcomp: check read and reverse complement for adapter matches.
    - cut: list of integers to remove fixed bases from reads (positive from start, negative from end).
    - quality_cutoff: quality trimming cutoff(s) as string "[5'CUTOFF,]3'CUTOFF".
    - nextseq_trim: NextSeq-specific quality trimming cutoff.
    - quality_base: quality encoding base (default 33).
    - poly_a: trim poly-A tails from R1 and poly-T heads from R2.
    - length: shorten reads to this length (positive trims end, negative trims start).
    - trim_n: trim N bases from 5' and 3' ends.
    - length_tag: tag in header to update with trimmed read length.
    - strip_suffix: list of suffixes to remove from read names.
    - prefix: prefix to add prefix to read names.
    - suffix: suffix to add to read names.
    - rename: template to rename reads.
    - zero_cap: change negative quality values to zero.
    - minimum_length: minimum length filter, can be "LEN" or "LEN:LEN2" for paired.
    - maximum_length: maximum length filter, can be "LEN" or "LEN:LEN2" for paired.
    - max_n: max allowed N bases (int or fraction).
    - max_expected_errors: max expected errors filter.
    - discard_trimmed: discard reads with adapter matches.
    - discard_untrimmed: discard reads without adapter matches.
    - discard_casava: discard reads failing CASAVA filter.
    - quiet: suppress non-error messages.
    - report: report type: full or minimal (default full).
    - json_report: path to JSON report output.
    - fasta: force FASTA output.
    - compression_level_1: use compression level 1 for gzip output.
    - info_file: write detailed adapter match info to file (single-end only).
    - rest_file: write "rest" of reads after adapter match to file.
    - wildcard_file: write adapter bases matching wildcards to file.
    - too_short_output: write reads too short to this file.
    - too_long_output: write reads too long to this file.
    - untrimmed_output: write untrimmed reads to this file.
    - cores: number of CPU cores to use (0 for autodetect).
    - adapter_r2: 3' adapter for read 2 (paired-end).
    - front_adapter_r2: 5' adapter for read 2 (paired-end).
    - anywhere_adapter_r2: anywhere adapter for read 2 (paired-end).
    - cut_r2: fixed base removal length for read 2.
    - quality_cutoff_r2: quality trimming cutoff for read 2.

        Returns:
    Dictionary with command executed, stdout, stderr, and list of output files.
    """
    # Validate input file
    if not input_file.exists():
        msg = f"Input file {input_file} does not exist."
        raise FileNotFoundError(msg)
    if output_file is not None:
        output_dir = output_file.parent
        if not output_dir.exists():
            msg = f"Output directory {output_dir} does not exist."
            raise FileNotFoundError(msg)

    # Validate numeric parameters
    if error_rate < 0:
        msg = "error_rate must be >= 0"
        raise ValueError(msg)
    if times < 1:
        msg = "times must be >= 1"
        raise ValueError(msg)
    if overlap < 1:
        msg = "overlap must be >= 1"
        raise ValueError(msg)
    if quality_base not in (33, 64):
        msg = "quality_base must be 33 or 64"
        raise ValueError(msg)
    if cores < 0:
        msg = "cores must be >= 0"
        raise ValueError(msg)
    if nextseq_trim is not None and nextseq_trim < 0:
        msg = "nextseq_trim must be >= 0"
        raise ValueError(msg)

    # Validate cut parameters
    if cut is not None:
        if not isinstance(cut, list):
            msg = "cut must be a list of integers"
            raise ValueError(msg)
        for c in cut:
            if not isinstance(c, int):
                msg = "cut list elements must be integers"
                raise ValueError(msg)

    # Validate strip_suffix
    if strip_suffix is not None:
        if not isinstance(strip_suffix, list):
            msg = "strip_suffix must be a list of strings"
            raise ValueError(msg)
        for s in strip_suffix:
            if not isinstance(s, str):
                msg = "strip_suffix list elements must be strings"
                raise ValueError(msg)

    # Build command line
    cmd = ["cutadapt"]

    # Multi-core
    cmd += ["-j", str(cores)]

    # Adapters for read 1
    if adapter is not None:
        cmd += ["-a", adapter]
    if front_adapter is not None:
        cmd += ["-g", front_adapter]
    if anywhere_adapter is not None:
        cmd += ["-b", anywhere_adapter]

    # Aliases for adapters (if provided)
    if adapter_2 is not None:
        cmd += ["-a", adapter_2]
    if front_adapter_2 is not None:
        cmd += ["-g", front_adapter_2]
    if anywhere_adapter_2 is not None:
        cmd += ["-b", anywhere_adapter_2]

    # Adapters for read 2 (paired-end)
    if adapter_r2 is not None:
        cmd += ["-A", adapter_r2]
    if front_adapter_r2 is not None:
        cmd += ["-G", front_adapter_r2]
    if anywhere_adapter_r2 is not None:
        cmd += ["-B", anywhere_adapter_r2]

    # Error rate
    cmd += ["-e", str(error_rate)]

    # No indels
    if no_indels:
        cmd.append("--no-indels")

    # Times
    cmd += ["-n", str(times)]

    # Overlap
    cmd += ["-O", str(overlap)]

    # Wildcards
    if match_read_wildcards:
        cmd.append("--match-read-wildcards")
    if no_match_adapter_wildcards:
        cmd.append("-N")

    # Action
    cmd += ["--action", action]

    # Reverse complement
    if revcomp:
        cmd.append("--revcomp")

    # Cut bases
    if cut is not None:
        for c in cut:
            cmd += ["-u", str(c)]

    # Quality cutoff
    if quality_cutoff is not None:
        cmd += ["-q", quality_cutoff]

    # Quality cutoff for read 2
    if quality_cutoff_r2 is not None:
        cmd += ["-Q", quality_cutoff_r2]

    # NextSeq trim
    if nextseq_trim is not None:
        cmd += ["--nextseq-trim", str(nextseq_trim)]

    # Quality base
    cmd += ["--quality-base", str(quality_base)]

    # Poly-A trimming
    if poly_a:
        cmd.append("--poly-a")

    # Length shortening
    if length is not None:
        cmd += ["-l", str(length)]

    # Trim N
    if trim_n:
        cmd.append("--trim-n")

    # Length tag
    if length_tag is not None:
        cmd += ["--length-tag", length_tag]

    # Strip suffix
    if strip_suffix is not None:
        for s in strip_suffix:
            cmd += ["--strip-suffix", s]

    # Prefix and suffix
    if prefix is not None:
        cmd += ["-x", prefix]
    if suffix is not None:
        cmd += ["-y", suffix]

    # Rename
    if rename is not None:
        cmd += ["--rename", rename]

    # Zero cap
    if zero_cap:
        cmd.append("-z")

    # Minimum length
    if minimum_length is not None:
        cmd += ["-m", minimum_length]

    # Maximum length
    if maximum_length is not None:
        cmd += ["-M", maximum_length]

    # Max N bases
    if max_n is not None:
        cmd += ["--max-n", str(max_n)]

    # Max expected errors
    if max_expected_errors is not None:
        cmd += ["--max-ee", str(max_expected_errors)]

    # Discard trimmed
    if discard_trimmed:
        cmd.append("--discard-trimmed")

    # Discard untrimmed
    if discard_untrimmed:
        cmd.append("--discard-untrimmed")

    # Discard casava
    if discard_casava:
        cmd.append("--discard-casava")

    # Quiet
    if quiet:
        cmd.append("--quiet")

    # Report type
    cmd += ["--report", report]

    # JSON report
    if json_report is not None:
        if json_report.suffix != ".cutadapt.json":
            msg = "JSON report file must have extension '.cutadapt.json'"
            raise ValueError(msg)
        cmd += ["--json", str(json_report)]

    # Force fasta output
    if fasta:
        cmd.append("--fasta")

    # Compression level 1 (deprecated option -Z)
    if compression_level_1:
        cmd.append("-Z")

    # Info file (single-end only)
    if info_file is not None:
        cmd += ["--info-file", str(info_file)]

    # Rest file
    if rest_file is not None:
        cmd += ["-r", str(rest_file)]

    # Wildcard file
    if wildcard_file is not None:
        cmd += ["--wildcard-file", str(wildcard_file)]

    # Too short output
    if too_short_output is not None:
        cmd += ["--too-short-output", str(too_short_output)]

    # Too long output
    if too_long_output is not None:
        cmd += ["--too-long-output", str(too_long_output)]

    # Untrimmed output
    if untrimmed_output is not None:
        cmd += ["--untrimmed-output", str(untrimmed_output)]

    # Cut bases for read 2
    if cut_r2 is not None:
        cmd += ["-U", str(cut_r2)]

    # Input and output files
    cmd.append(str(input_file))
    if output_file is not None:
        cmd += ["-o", str(output_file)]

    # Run command
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
            "stdout": e.stdout,
            "stderr": e.stderr,
            "output_files": [],
            "error": f"Cutadapt failed with exit code {e.returncode}",
        }

    # Collect output files
    output_files = []
    if output_file is not None:
        output_files.append(str(output_file))
    if json_report is not None:
        output_files.append(str(json_report))
    if info_file is not None:
        output_files.append(str(info_file))
    if rest_file is not None:
        output_files.append(str(rest_file))
    if wildcard_file is not None:
        output_files.append(str(wildcard_file))
    if too_short_output is not None:
        output_files.append(str(too_short_output))
    if too_long_output is not None:
        output_files.append(str(too_long_output))
    if untrimmed_output is not None:
        output_files.append(str(untrimmed_output))

    return {
        "command_executed": " ".join(cmd),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output_files": output_files,
    }


# Register the tool with FastMCP if available
if FASTMCP_AVAILABLE and mcp:
    cutadapt_tool = mcp.tool()(cutadapt)


class CutadaptServer(MCPServerBase if BASE_CLASS_AVAILABLE else object):
    """MCP Server for Cutadapt adapter trimming tool."""

    def __init__(self, config=None, enable_fastmcp: bool = True):
        # Set name attribute for compatibility
        self.name = "cutadapt-server"

        if BASE_CLASS_AVAILABLE and config is None and MCPServerConfig is not None:
            config = MCPServerConfig(
                server_name="cutadapt-server",
                server_type=MCPServerType.CUSTOM if MCPServerType else "custom",  # type: ignore[union-attr]
                container_image="condaforge/miniforge3:latest",
                environment_variables={"CUTADAPT_VERSION": "4.4"},
                capabilities=[
                    "adapter_trimming",
                    "quality_filtering",
                    "read_processing",
                ],
            )

        if BASE_CLASS_AVAILABLE:
            super().__init__(config)

        # Initialize FastMCP if available and enabled
        self.fastmcp_server = None
        if FASTMCP_AVAILABLE and enable_fastmcp:
            self.fastmcp_server = FastMCP("cutadapt-server")
            self._register_fastmcp_tools()

    def _register_fastmcp_tools(self):
        """Register tools with FastMCP server."""
        if not self.fastmcp_server:
            return

        # Register the cutadapt tool
        self.fastmcp_server.tool()(cutadapt)

    def get_server_info(self):
        """Get server information."""
        return {
            "name": "cutadapt-server",
            "version": "1.0.0",
            "description": "Cutadapt adapter trimming server",
            "tools": ["cutadapt"],
            "status": "running" if self.fastmcp_server else "stopped",
        }

    def list_tools(self):
        """List available tools."""
        # Always return available tools, regardless of FastMCP status
        return ["cutadapt"]

    def run_tool(self, tool_name: str, **kwargs):
        """Run a specific tool."""
        if tool_name == "cutadapt":
            return cutadapt(**kwargs)  # type: ignore[call-arg]
        msg = f"Unknown tool: {tool_name}"
        raise ValueError(msg)

    def run(self, params: dict):
        """Run method for compatibility with test framework."""
        operation = params.get("operation", "cutadapt")
        if operation == "trim":
            # Map trim operation to cutadapt
            output_dir = Path(params.get("output_dir", "/tmp"))
            return self.run_tool(
                "cutadapt",
                input_file=Path(params["input_files"][0]),
                output_file=output_dir / "trimmed.fq",
                adapter=params.get("adapter"),
                quality_cutoff=str(params.get("quality", 20)),
            )
        return self.run_tool(
            operation, **{k: v for k, v in params.items() if k != "operation"}
        )

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy the server using testcontainers."""
        # Implementation for testcontainers deployment
        # This is a placeholder - actual implementation would use testcontainers
        from datetime import datetime

        return MCPServerDeployment(
            server_name="cutadapt-server",
            server_type=MCPServerType.CUSTOM,
            container_id="cutadapt-test-container",
            status=MCPServerStatus.RUNNING,
            configuration=self.config,
            started_at=datetime.now(),
        )

    async def stop_with_testcontainers(self) -> bool:
        """Stop the server deployed with testcontainers."""
        # Implementation for stopping testcontainers deployment
        # This is a placeholder - actual implementation would stop the container
        return True


if __name__ == "__main__":
    if mcp is not None:
        mcp.run()
