"""
BWA MCP Server - Pydantic AI compatible MCP server for DNA sequence alignment.

This module implements an MCP server for BWA (Burrows-Wheeler Aligner),
a fast and accurate short read aligner for DNA sequencing data, following
Pydantic AI MCP integration patterns.

This server can be used with Pydantic AI agents via MCPServerStdio toolset.

Usage with Pydantic AI:
```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

# Create MCP server toolset
bwa_server = MCPServerStdio(
    command='python',
    args=['bwa_server.py'],
    tool_prefix='bwa'
)

# Create agent with BWA tools
agent = Agent(
    'openai:gpt-4o',
    toolsets=[bwa_server]
)

# Use BWA tools in agent queries
async def main():
    async with agent:
        result = await agent.run(
            'Index the reference genome at /data/hg38.fa and align reads from /data/reads.fq'
        )
        print(result.data)
```

Run the MCP server:
```bash
python bwa_server.py
```

The server exposes the following tools:
- bwa_index: Index database sequences in FASTA format
- bwa_mem: Align 70bp-1Mbp query sequences with BWA-MEM algorithm
- bwa_aln: Find SA coordinates using BWA-backtrack algorithm
- bwa_samse: Generate SAM alignments from single-end reads
- bwa_sampe: Generate SAM alignments from paired-end reads
- bwa_bwasw: Align sequences using BWA-SW algorithm
"""

from __future__ import annotations

import subprocess
from pathlib import Path

try:
    from fastmcp import FastMCP
except ImportError:
    # Fallback for environments without fastmcp
    _FastMCP = None

# Create MCP server instance
try:
    mcp = FastMCP("bwa-server")
except NameError:
    mcp = None


# MCP Tool definitions using FastMCP
# Define the functions first, then apply decorators if FastMCP is available


def bwa_index(
    in_db_fasta: Path,
    p: str | None = None,
    a: str = "is",
):
    """
    Index database sequences in the FASTA format using bwa index.
    -p STR: Prefix of the output database [default: same as db filename]
    -a STR: Algorithm for constructing BWT index. Options: 'is' (default), 'bwtsw'.
    """
    if not in_db_fasta.exists():
        msg = f"Input fasta file {in_db_fasta} does not exist"
        raise FileNotFoundError(msg)
    if a not in ("is", "bwtsw"):
        msg = "Parameter 'a' must be either 'is' or 'bwtsw'"
        raise ValueError(msg)

    cmd = ["bwa", "index"]
    if p:
        cmd += ["-p", p]
    cmd += ["-a", a]
    cmd.append(str(in_db_fasta))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        output_files = []
        prefix = p if p else in_db_fasta.with_suffix("").name
        # BWA index creates multiple files with extensions: .amb, .ann, .bwt, .pac, .sa
        for ext in [".amb", ".ann", ".bwt", ".pac", ".sa"]:
            f = Path(prefix + ext)
            if f.exists():
                output_files.append(str(f.resolve()))
        return {
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": output_files,
        }
    except subprocess.CalledProcessError as e:
        return {
            "command_executed": " ".join(cmd),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "output_files": [],
            "error": f"bwa index failed with return code {e.returncode}",
        }


def bwa_mem(
    db_prefix: Path,
    reads_fq: Path,
    mates_fq: Path | None = None,
    a: bool = False,
    c_flag: bool = False,
    h: bool = False,
    m: bool = False,
    p: bool = False,
    t: int = 1,
    k: int = 19,
    w: int = 100,
    d: int = 100,
    r: float = 1.5,
    c_value: int = 10000,
    a_penalty: int = 1,
    b_penalty: int = 4,
    o_penalty: int = 6,
    e_penalty: int = 1,
    l_penalty: int = 5,
    u_penalty: int = 9,
    r_string: str | None = None,
    v: int = 3,
    t_value: int = 30,
):
    """
    Align 70bp-1Mbp query sequences with the BWA-MEM algorithm.
    Supports single-end, paired-end, and interleaved paired-end reads.
    Parameters correspond to bwa mem options.
    """
    if not db_prefix.exists():
        msg = f"Database prefix {db_prefix} does not exist"
        raise FileNotFoundError(msg)
    if not reads_fq.exists():
        msg = f"Reads file {reads_fq} does not exist"
        raise FileNotFoundError(msg)
    if mates_fq and not mates_fq.exists():
        msg = f"Mates file {mates_fq} does not exist"
        raise FileNotFoundError(msg)
    if t < 1:
        msg = "Number of threads 't' must be >= 1"
        raise ValueError(msg)
    if k < 1:
        msg = "Minimum seed length 'k' must be >= 1"
        raise ValueError(msg)
    if w < 1:
        msg = "Band width 'w' must be >= 1"
        raise ValueError(msg)
    if d < 0:
        msg = "Off-diagonal X-dropoff 'd' must be >= 0"
        raise ValueError(msg)
    if r <= 0:
        msg = "Trigger re-seeding ratio 'r' must be > 0"
        raise ValueError(msg)
    if c_value < 0:
        msg = "Discard MEM occurrence 'c_value' must be >= 0"
        raise ValueError(msg)
    if (
        a_penalty < 0
        or b_penalty < 0
        or o_penalty < 0
        or e_penalty < 0
        or l_penalty < 0
        or u_penalty < 0
    ):
        msg = "Scoring penalties must be non-negative"
        raise ValueError(msg)
    if v < 0:
        msg = "Verbose level 'v' must be >= 0"
        raise ValueError(msg)
    if t_value < 0:
        msg = "Minimum output alignment score 't_value' must be >= 0"
        raise ValueError(msg)

    cmd = ["bwa", "mem"]
    if a:
        cmd.append("-a")
    if c_flag:
        cmd.append("-C")
    if h:
        cmd.append("-H")
    if m:
        cmd.append("-M")
    if p:
        cmd.append("-p")
    cmd += ["-t", str(t)]
    cmd += ["-k", str(k)]
    cmd += ["-w", str(w)]
    cmd += ["-d", str(d)]
    cmd += ["-r", str(r)]
    cmd += ["-c", str(c_value)]
    cmd += ["-A", str(a_penalty)]
    cmd += ["-B", str(b_penalty)]
    cmd += ["-O", str(o_penalty)]
    cmd += ["-E", str(e_penalty)]
    cmd += ["-L", str(l_penalty)]
    cmd += ["-U", str(u_penalty)]
    if r_string:
        # Replace literal \t with tab character
        r_fixed = r_string.replace("\\t", "\t")
        cmd += ["-R", r_fixed]
    cmd += ["-v", str(v)]
    cmd += ["-T", str(t_value)]
    cmd.append(str(db_prefix))
    cmd.append(str(reads_fq))
    if mates_fq and not p:
        cmd.append(str(mates_fq))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # bwa mem outputs SAM to stdout
        return {
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": [],
        }
    except subprocess.CalledProcessError as e:
        return {
            "command_executed": " ".join(cmd),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "output_files": [],
            "error": f"bwa mem failed with return code {e.returncode}",
        }


def bwa_aln(
    in_db_fasta: Path,
    in_query_fq: Path,
    n: float = 0.04,
    o: int = 1,
    e: int = -1,
    d: int = 16,
    i: int = 5,
    seed_length: int | None = None,
    k: int = 2,
    t: int = 1,
    m: int = 3,
    o_penalty2: int = 11,
    e_penalty: int = 4,
    r: int = 0,
    c_flag: bool = False,
    n_value: bool = False,
    q: int = 0,
    i_flag: bool = False,
    b_penalty: int = 0,
    b: bool = False,
    zero: bool = False,
    one: bool = False,
    two: bool = False,
):
    """
    Find the SA coordinates of the input reads using bwa aln (BWA-backtrack).
    Parameters correspond to bwa aln options.
    """
    if not in_db_fasta.exists():
        msg = f"Input fasta file {in_db_fasta} does not exist"
        raise FileNotFoundError(msg)
    if not in_query_fq.exists():
        msg = f"Input query file {in_query_fq} does not exist"
        raise FileNotFoundError(msg)
    if n < 0:
        msg = "Maximum edit distance 'n' must be non-negative"
        raise ValueError(msg)
    if o < 0:
        msg = "Maximum number of gap opens 'o' must be non-negative"
        raise ValueError(msg)
    if e < -1:
        msg = "Maximum number of gap extensions 'e' must be >= -1"
        raise ValueError(msg)
    if d < 0:
        msg = "Disallow long deletion 'd' must be non-negative"
        raise ValueError(msg)
    if i < 0:
        msg = "Disallow indel near ends 'i' must be non-negative"
        raise ValueError(msg)
    if seed_length is not None and seed_length < 1:
        msg = "Seed length 'seed_length' must be positive or None"
        raise ValueError(msg)
    if k < 0:
        msg = "Maximum edit distance in seed 'k' must be non-negative"
        raise ValueError(msg)
    if t < 1:
        msg = "Number of threads 't' must be >= 1"
        raise ValueError(msg)
    if m < 0 or o_penalty2 < 0 or e_penalty < 0 or r < 0 or q < 0 or b_penalty < 0:
        msg = "Penalty and threshold parameters must be non-negative"
        raise ValueError(msg)

    cmd = ["bwa", "aln"]
    cmd += ["-n", str(n)]
    cmd += ["-o", str(o)]
    cmd += ["-e", str(e)]
    cmd += ["-d", str(d)]
    cmd += ["-i", str(i)]
    if seed_length is not None:
        cmd += ["-l", str(seed_length)]
    cmd += ["-k", str(k)]
    cmd += ["-t", str(t)]
    cmd += ["-M", str(m)]
    cmd += ["-O", str(o_penalty2)]
    cmd += ["-E", str(e_penalty)]
    cmd += ["-R", str(r)]
    if c_flag:
        cmd.append("-c")
    if n_value:
        cmd.append("-N")
    cmd += ["-q", str(q)]
    if i_flag:
        cmd.append("-I")
    if b_penalty > 0:
        cmd += ["-B", str(b_penalty)]
    if b:
        cmd.append("-b")
    if zero:
        cmd.append("-0")
    if one:
        cmd.append("-1")
    if two:
        cmd.append("-2")
    cmd.append(str(in_db_fasta))
    cmd.append(str(in_query_fq))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # bwa aln outputs .sai to stdout
        return {
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": [],
        }
    except subprocess.CalledProcessError as exc:
        return {
            "command_executed": " ".join(cmd),
            "stdout": exc.stdout,
            "stderr": exc.stderr,
            "output_files": [],
            "error": f"bwa aln failed with return code {exc.returncode}",
        }


def bwa_samse(
    in_db_fasta: Path,
    in_sai: Path,
    in_fq: Path,
    n: int = 3,
    r: str | None = None,
):
    """
    Generate alignments in the SAM format given single-end reads using bwa samse.
    -n INT: Maximum number of alignments to output in XA tag [3]
    -r STR: Specify the read group header line (e.g. '@RG\\tID:foo\\tSM:bar')
    """
    if not in_db_fasta.exists():
        msg = f"Input fasta file {in_db_fasta} does not exist"
        raise FileNotFoundError(msg)
    if not in_sai.exists():
        msg = f"Input sai file {in_sai} does not exist"
        raise FileNotFoundError(msg)
    if not in_fq.exists():
        msg = f"Input fastq file {in_fq} does not exist"
        raise FileNotFoundError(msg)
    if n < 0:
        msg = "Maximum number of alignments 'n' must be non-negative"
        raise ValueError(msg)

    cmd = ["bwa", "samse"]
    cmd += ["-n", str(n)]
    if r:
        r_fixed = r.replace("\\t", "\t")
        cmd += ["-r", r_fixed]
    cmd.append(str(in_db_fasta))
    cmd.append(str(in_sai))
    cmd.append(str(in_fq))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # bwa samse outputs SAM to stdout
        return {
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": [],
        }
    except subprocess.CalledProcessError as e:
        return {
            "command_executed": " ".join(cmd),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "output_files": [],
            "error": f"bwa samse failed with return code {e.returncode}",
        }


def bwa_sampe(
    in_db_fasta: Path,
    in1_sai: Path,
    in2_sai: Path,
    in1_fq: Path,
    in2_fq: Path,
    a: int = 500,
    o: int = 100000,
    n: int = 3,
    n_value: int = 10,
    p_flag: bool = False,
    r: str | None = None,
):
    """
    Generate alignments in the SAM format given paired-end reads using bwa sampe.
    -a INT: Maximum insert size for proper pair [500]
    -o INT: Maximum occurrences of a read for pairing [100000]
    -n INT: Max alignments in XA tag for properly paired reads [3]
    -N INT: Max alignments in XA tag for discordant pairs [10]
    -P: Load entire FM-index into memory
    -r STR: Specify the read group header line
    """
    for f in [in_db_fasta, in1_sai, in2_sai, in1_fq, in2_fq]:
        if not f.exists():
            msg = f"Input file {f} does not exist"
            raise FileNotFoundError(msg)
    if a < 0 or o < 0 or n < 0 or n_value < 0:
        msg = "Parameters a, o, n, n_value must be non-negative"
        raise ValueError(msg)

    cmd = ["bwa", "sampe"]
    cmd += ["-a", str(a)]
    cmd += ["-o", str(o)]
    if p_flag:
        cmd.append("-P")
    cmd += ["-n", str(n)]
    cmd += ["-N", str(n_value)]
    if r:
        r_fixed = r.replace("\\t", "\t")
        cmd += ["-r", r_fixed]
    cmd.append(str(in_db_fasta))
    cmd.append(str(in1_sai))
    cmd.append(str(in2_sai))
    cmd.append(str(in1_fq))
    cmd.append(str(in2_fq))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # bwa sampe outputs SAM to stdout
        return {
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": [],
        }
    except subprocess.CalledProcessError as e:
        return {
            "command_executed": " ".join(cmd),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "output_files": [],
            "error": f"bwa sampe failed with return code {e.returncode}",
        }


def bwa_bwasw(
    in_db_fasta: Path,
    in_fq: Path,
    mate_fq: Path | None = None,
    a: int = 1,
    b: int = 3,
    q: int = 5,
    r: int = 2,
    t: int = 1,
    w: int = 33,
    t_value: int = 37,
    c: float = 5.5,
    z: int = 1,
    s: int = 3,
    n_hits: int = 5,
):
    """
    Align query sequences using bwa bwasw (BWA-SW algorithm).
    Supports single-end and paired-end (Illumina short-insert) reads.
    """
    if not in_db_fasta.exists():
        msg = f"Input fasta file {in_db_fasta} does not exist"
        raise FileNotFoundError(msg)
    if not in_fq.exists():
        msg = f"Input fastq file {in_fq} does not exist"
        raise FileNotFoundError(msg)
    if mate_fq and not mate_fq.exists():
        msg = f"Mate fastq file {mate_fq} does not exist"
        raise FileNotFoundError(msg)
    if t < 1:
        msg = "Number of threads 't' must be >= 1"
        raise ValueError(msg)
    if w < 1:
        msg = "Band width 'w' must be >= 1"
        raise ValueError(msg)
    if t_value < 0:
        msg = "Minimum score threshold 't_value' must be >= 0"
        raise ValueError(msg)
    if c < 0:
        msg = "Coefficient 'c' must be >= 0"
        raise ValueError(msg)
    if z < 1:
        msg = "Z-best heuristics 'z' must be >= 1"
        raise ValueError(msg)
    if s < 1:
        msg = "Maximum SA interval size 's' must be >= 1"
        raise ValueError(msg)
    if n_hits < 0:
        msg = "Minimum number of seeds 'n_hits' must be >= 0"
        raise ValueError(msg)

    cmd = ["bwa", "bwasw"]
    cmd += ["-a", str(a)]
    cmd += ["-b", str(b)]
    cmd += ["-q", str(q)]
    cmd += ["-r", str(r)]
    cmd += ["-t", str(t)]
    cmd += ["-w", str(w)]
    cmd += ["-T", str(t_value)]
    cmd += ["-c", str(c)]
    cmd += ["-z", str(z)]
    cmd += ["-s", str(s)]
    cmd += ["-N", str(n_hits)]
    cmd.append(str(in_db_fasta))
    cmd.append(str(in_fq))
    if mate_fq:
        cmd.append(str(mate_fq))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # bwa bwasw outputs SAM to stdout
        return {
            "command_executed": " ".join(cmd),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": [],
        }
    except subprocess.CalledProcessError as e:
        return {
            "command_executed": " ".join(cmd),
            "stdout": e.stdout,
            "stderr": e.stderr,
            "output_files": [],
            "error": f"bwa bwasw failed with return code {e.returncode}",
        }


# Apply MCP decorators if FastMCP is available
if mcp:
    # Re-bind the functions with MCP decorators
    bwa_index = mcp.tool()(bwa_index)  # type: ignore[assignment]
    bwa_mem = mcp.tool()(bwa_mem)  # type: ignore[assignment]
    bwa_aln = mcp.tool()(bwa_aln)  # type: ignore[assignment]
    bwa_samse = mcp.tool()(bwa_samse)  # type: ignore[assignment]
    bwa_sampe = mcp.tool()(bwa_sampe)  # type: ignore[assignment]
    bwa_bwasw = mcp.tool()(bwa_bwasw)  # type: ignore[assignment]

# Main execution
if __name__ == "__main__":
    if mcp:
        mcp.run()
    else:
        pass
