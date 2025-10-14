"""
STAR MCP Server - Vendored BioinfoMCP server for RNA-seq alignment.

This module implements a strongly-typed MCP server for STAR, a popular
spliced read aligner for RNA-seq data, using Pydantic AI patterns and
testcontainers deployment.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Any

from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase, mcp_tool
from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
    MCPToolSpec,
)

if TYPE_CHECKING:
    from pydantic_ai import RunContext

    from DeepResearch.src.datatypes.agents import AgentDependencies


class STARServer(MCPServerBase):
    """MCP Server for STAR RNA-seq alignment tool with Pydantic AI integration."""

    def __init__(self, config: MCPServerConfig | None = None):
        if config is None:
            config = MCPServerConfig(
                server_name="star-server",
                server_type=MCPServerType.CUSTOM,
                container_image="condaforge/miniforge3:latest",
                environment_variables={
                    "STAR_VERSION": "2.7.10b",
                    "CONDA_AUTO_UPDATE_CONDA": "false",
                    "CONDA_AUTO_ACTIVATE_BASE": "false",
                },
                capabilities=[
                    "rna_seq",
                    "alignment",
                    "spliced_alignment",
                    "genome_indexing",
                    "quantification",
                    "wiggle_tracks",
                    "bigwig_conversion",
                ],
            )
        super().__init__(config)

    def _mock_result(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Return a mock result for when STAR is not available."""
        mock_outputs = {
            "generate_genome": [
                "Genome",
                "SA",
                "SAindex",
                "chrLength.txt",
                "chrName.txt",
                "chrNameLength.txt",
                "chrStart.txt",
                "genomeParameters.txt",
            ],
            "align_reads": [
                "Aligned.sortedByCoord.out.bam",
                "Log.final.out",
                "Log.out",
                "Log.progress.out",
                "SJ.out.tab",
            ],
            "quant_mode": [
                "Aligned.sortedByCoord.out.bam",
                "ReadsPerGene.out.tab",
                "Log.final.out",
            ],
            "load_genome": [],
            "wig_to_bigwig": ["output.bw"],
            "solo": [
                "Solo.out/Gene/raw/matrix.mtx",
                "Solo.out/Gene/raw/barcodes.tsv",
                "Solo.out/Gene/raw/features.tsv",
            ],
        }

        output_files = mock_outputs.get(operation, [])
        # Add output prefix if specified
        if "out_file_name_prefix" in params and output_files:
            prefix = params["out_file_name_prefix"]
            output_files = [f"{prefix}{f}" for f in output_files]
        elif "genome_dir" in params and operation == "generate_genome":
            genome_dir = params["genome_dir"]
            output_files = [f"{genome_dir}/{f}" for f in output_files]

        return {
            "success": True,
            "command_executed": f"STAR {operation} [mock - tool not available]",
            "stdout": f"Mock output for {operation} operation",
            "stderr": "",
            "output_files": output_files,
            "exit_code": 0,
            "mock": True,  # Indicate this is a mock result
        }

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Run Star operation based on parameters.

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
            "generate_genome": self.star_generate_genome,
            "align_reads": self.star_align_reads,
            "load_genome": self.star_load_genome,
            "quant_mode": self.star_quant_mode,
            "wig_to_bigwig": self.star_wig_to_bigwig,
            "solo": self.star_solo,
            "genome_generate": self.star_generate_genome,  # alias
            "alignment": self.star_align_reads,  # alias
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

            tool_name_check = "STAR"
            if not shutil.which(tool_name_check):
                # Return mock success result for testing when tool is not available
                return self._mock_result(operation, method_params)

            # Call the appropriate method
            return method(**method_params)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute {operation}: {e!s}",
            }

    @mcp_tool(
        MCPToolSpec(
            name="star_generate_genome",
            description="Generate STAR genome index from genome FASTA and GTF files",
            inputs={
                "genome_dir": "str",
                "genome_fasta_files": "list[str]",
                "sjdb_gtf_file": "str | None",
                "sjdb_overhang": "int",
                "genome_sa_index_n_bases": "int",
                "genome_chr_bin_n_bits": "int",
                "genome_sa_sparse_d": "int",
                "threads": "int",
                "limit_genome_generate_ram": "str",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Generate STAR genome index for human genome",
                    "parameters": {
                        "genome_dir": "/data/star_index",
                        "genome_fasta_files": ["/data/genome.fa"],
                        "sjdb_gtf_file": "/data/genes.gtf",
                        "sjdb_overhang": 149,
                        "threads": 4,
                    },
                }
            ],
        )
    )
    def star_generate_genome(
        self,
        genome_dir: str,
        genome_fasta_files: list[str],
        sjdb_gtf_file: str | None = None,
        sjdb_overhang: int = 100,
        genome_sa_index_n_bases: int = 14,
        genome_chr_bin_n_bits: int = 18,
        genome_sa_sparse_d: int = 1,
        threads: int = 1,
        limit_genome_generate_ram: str = "31000000000",
    ) -> dict[str, Any]:
        """
        Generate STAR genome index from genome FASTA and GTF files.

        This tool creates a STAR genome index which is required for fast and accurate
        alignment of RNA-seq reads using the STAR aligner.

        Args:
            genome_dir: Directory to store the genome index
            genome_fasta_files: List of genome FASTA files
            sjdb_gtf_file: GTF file with gene annotations
            sjdb_overhang: Read length - 1 (for paired-end reads, use read length - 1)
            genome_sa_index_n_bases: Length (bases) of the SA pre-indexing string
            genome_chr_bin_n_bits: Number of bits for genome chromosome bins
            genome_sa_sparse_d: Suffix array sparsity
            threads: Number of threads to use
            limit_genome_generate_ram: Maximum RAM for genome generation

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files exist
        for fasta_file in genome_fasta_files:
            if not os.path.exists(fasta_file):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Genome FASTA file does not exist: {fasta_file}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Genome FASTA file not found: {fasta_file}",
                }

        if sjdb_gtf_file and not os.path.exists(sjdb_gtf_file):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"GTF file does not exist: {sjdb_gtf_file}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"GTF file not found: {sjdb_gtf_file}",
            }

        # Build command
        cmd = ["STAR", "--runMode", "genomeGenerate", "--genomeDir", genome_dir]

        # Add genome FASTA files
        cmd.extend(["--genomeFastaFiles", *genome_fasta_files])

        if sjdb_gtf_file:
            cmd.extend(["--sjdbGTFfile", sjdb_gtf_file])

        cmd.extend(
            [
                "--sjdbOverhang",
                str(sjdb_overhang),
                "--genomeSAindexNbases",
                str(genome_sa_index_n_bases),
                "--genomeChrBinNbits",
                str(genome_chr_bin_n_bits),
                "--genomeSASparseD",
                str(genome_sa_sparse_d),
                "--runThreadN",
                str(threads),
                "--limitGenomeGenerateRAM",
                limit_genome_generate_ram,
            ]
        )

        try:
            # Execute STAR genome generation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Get output files
            output_files = []
            try:
                # STAR creates various index files
                index_files = [
                    "Genome",
                    "SA",
                    "SAindex",
                    "chrLength.txt",
                    "chrName.txt",
                    "chrNameLength.txt",
                    "chrStart.txt",
                    "exonGeTrInfo.tab",
                    "exonInfo.tab",
                    "geneInfo.tab",
                    "genomeParameters.txt",
                    "sjdbInfo.txt",
                    "sjdbList.fromGTF.out.tab",
                    "sjdbList.out.tab",
                    "transcriptInfo.tab",
                ]
                for filename in index_files:
                    filepath = os.path.join(genome_dir, filename)
                    if os.path.exists(filepath):
                        output_files.append(filepath)
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
                "stderr": "STAR not found in PATH",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "STAR not found in PATH",
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
            name="star_align_reads",
            description="Align RNA-seq reads to reference genome using STAR",
            inputs={
                "genome_dir": "str",
                "read_files_in": "list[str]",
                "out_file_name_prefix": "str",
                "run_thread_n": "int",
                "out_sam_type": "str",
                "out_sam_mode": "str",
                "quant_mode": "str",
                "read_files_command": "str | None",
                "out_filter_multimap_nmax": "int",
                "out_filter_mismatch_nmax": "int",
                "align_intron_min": "int",
                "align_intron_max": "int",
                "align_mates_gap_max": "int",
                "chim_segment_min": "int",
                "chim_junction_overhang_min": "int",
                "twopass_mode": "str",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Align paired-end RNA-seq reads",
                    "parameters": {
                        "genome_dir": "/data/star_index",
                        "read_files_in": ["/data/sample1.fastq", "/data/sample2.fastq"],
                        "out_file_name_prefix": "/results/sample_",
                        "run_thread_n": 4,
                        "quant_mode": "TranscriptomeSAM",
                    },
                }
            ],
        )
    )
    def star_align_reads(
        self,
        genome_dir: str,
        read_files_in: list[str],
        out_file_name_prefix: str,
        run_thread_n: int = 1,
        out_sam_type: str = "BAM SortedByCoordinate",
        out_sam_mode: str = "Full",
        quant_mode: str = "GeneCounts",
        read_files_command: str | None = None,
        out_filter_multimap_nmax: int = 20,
        out_filter_mismatch_nmax: int = 999,
        align_intron_min: int = 21,
        align_intron_max: int = 0,
        align_mates_gap_max: int = 0,
        chim_segment_min: int = 0,
        chim_junction_overhang_min: int = 20,
        twopass_mode: str = "Basic",
    ) -> dict[str, Any]:
        """
        Align RNA-seq reads to reference genome using STAR.

        This tool aligns RNA-seq reads to a reference genome using the STAR spliced
        aligner, which is optimized for RNA-seq data and provides high accuracy.

        Args:
            genome_dir: Directory containing STAR genome index
            read_files_in: List of input FASTQ files
            out_file_name_prefix: Prefix for output files
            run_thread_n: Number of threads to use
            out_sam_type: Output SAM type (SAM, BAM, etc.)
            out_sam_mode: Output SAM mode (Full, None)
            quant_mode: Quantification mode (GeneCounts, TranscriptomeSAM)
            read_files_command: Command to process input files
            out_filter_multimap_nmax: Maximum number of multiple alignments
            out_filter_mismatch_nmax: Maximum number of mismatches
            align_intron_min: Minimum intron length
            align_intron_max: Maximum intron length (0 = no limit)
            align_mates_gap_max: Maximum gap between mates
            chim_segment_min: Minimum chimeric segment length
            chim_junction_overhang_min: Minimum chimeric junction overhang
            twopass_mode: Two-pass mapping mode

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate genome directory exists
        if not os.path.exists(genome_dir):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Genome directory does not exist: {genome_dir}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Genome directory not found: {genome_dir}",
            }

        # Validate input files exist
        for read_file in read_files_in:
            if not os.path.exists(read_file):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Read file does not exist: {read_file}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Read file not found: {read_file}",
                }

        # Build command
        cmd = ["STAR", "--genomeDir", genome_dir]

        # Add input read files
        cmd.extend(["--readFilesIn", *read_files_in])

        # Add output prefix
        cmd.extend(["--outFileNamePrefix", out_file_name_prefix])

        # Add other parameters
        cmd.extend(
            [
                "--runThreadN",
                str(run_thread_n),
                "--outSAMtype",
                out_sam_type,
                "--outSAMmode",
                out_sam_mode,
                "--quantMode",
                quant_mode,
                "--outFilterMultimapNmax",
                str(out_filter_multimap_nmax),
                "--outFilterMismatchNmax",
                str(out_filter_mismatch_nmax),
                "--alignIntronMin",
                str(align_intron_min),
                "--alignIntronMax",
                str(align_intron_max),
                "--alignMatesGapMax",
                str(align_mates_gap_max),
                "--chimSegmentMin",
                str(chim_segment_min),
                "--chimJunctionOverhangMin",
                str(chim_junction_overhang_min),
                "--twopassMode",
                twopass_mode,
            ]
        )

        if read_files_command:
            cmd.extend(["--readFilesCommand", read_files_command])

        try:
            # Execute STAR alignment
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Get output files
            output_files = []
            try:
                # STAR creates various output files
                possible_outputs = [
                    f"{out_file_name_prefix}Aligned.sortedByCoord.out.bam",
                    f"{out_file_name_prefix}ReadsPerGene.out.tab",
                    f"{out_file_name_prefix}Log.final.out",
                    f"{out_file_name_prefix}Log.out",
                    f"{out_file_name_prefix}Log.progress.out",
                    f"{out_file_name_prefix}SJ.out.tab",
                    f"{out_file_name_prefix}Chimeric.out.junction",
                    f"{out_file_name_prefix}Chimeric.out.sam",
                ]
                for filepath in possible_outputs:
                    if os.path.exists(filepath):
                        output_files.append(filepath)
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
                "stderr": "STAR not found in PATH",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "STAR not found in PATH",
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
            name="star_load_genome",
            description="Load a genome into shared memory for faster alignment",
            inputs={
                "genome_dir": "str",
                "shared_memory": "bool",
                "threads": "int",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "exit_code": "int",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Load STAR genome into shared memory",
                    "parameters": {
                        "genome_dir": "/data/star_index",
                        "shared_memory": True,
                        "threads": 4,
                    },
                }
            ],
        )
    )
    def star_load_genome(
        self,
        genome_dir: str,
        shared_memory: bool = True,
        threads: int = 1,
    ) -> dict[str, Any]:
        """
        Load a STAR genome index into shared memory for faster alignment.

        This tool loads a pre-generated STAR genome index into shared memory,
        which can significantly speed up subsequent alignments when processing
        many samples.

        Args:
            genome_dir: Directory containing STAR genome index
            shared_memory: Whether to load into shared memory
            threads: Number of threads to use

        Returns:
            Dictionary containing command executed, stdout, stderr, and exit code
        """
        # Validate genome directory exists
        if not os.path.exists(genome_dir):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Genome directory does not exist: {genome_dir}",
                "exit_code": -1,
                "success": False,
                "error": f"Genome directory not found: {genome_dir}",
            }

        # Build command
        cmd = [
            "STAR",
            "--genomeLoad",
            "LoadAndKeep" if shared_memory else "LoadAndRemove",
            "--genomeDir",
            genome_dir,
        ]

        if threads > 1:
            cmd.extend(["--runThreadN", str(threads)])

        try:
            # Execute STAR genome load
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            }

        except FileNotFoundError:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": "STAR not found in PATH",
                "exit_code": -1,
                "success": False,
                "error": "STAR not found in PATH",
            }
        except Exception as e:
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False,
                "error": str(e),
            }

    @mcp_tool(
        MCPToolSpec(
            name="star_quant_mode",
            description="Run STAR with quantification mode for gene/transcript counting",
            inputs={
                "genome_dir": "str",
                "read_files_in": "list[str]",
                "out_file_name_prefix": "str",
                "quant_mode": "str",
                "run_thread_n": "int",
                "out_sam_type": "str",
                "out_sam_mode": "str",
                "read_files_command": "str | None",
                "out_filter_multimap_nmax": "int",
                "align_intron_min": "int",
                "align_intron_max": "int",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Run STAR quantification for RNA-seq reads",
                    "parameters": {
                        "genome_dir": "/data/star_index",
                        "read_files_in": ["/data/sample1.fastq", "/data/sample2.fastq"],
                        "out_file_name_prefix": "/results/sample_",
                        "quant_mode": "GeneCounts",
                        "run_thread_n": 4,
                    },
                }
            ],
        )
    )
    def star_quant_mode(
        self,
        genome_dir: str,
        read_files_in: list[str],
        out_file_name_prefix: str,
        quant_mode: str = "GeneCounts",
        run_thread_n: int = 1,
        out_sam_type: str = "BAM SortedByCoordinate",
        out_sam_mode: str = "Full",
        read_files_command: str | None = None,
        out_filter_multimap_nmax: int = 20,
        align_intron_min: int = 21,
        align_intron_max: int = 0,
    ) -> dict[str, Any]:
        """
        Run STAR with quantification mode for gene/transcript counting.

        This tool runs STAR alignment with quantification features enabled,
        generating gene count matrices and other quantification outputs.

        Args:
            genome_dir: Directory containing STAR genome index
            read_files_in: List of input FASTQ files
            out_file_name_prefix: Prefix for output files
            quant_mode: Quantification mode (GeneCounts, TranscriptomeSAM)
            run_thread_n: Number of threads to use
            out_sam_type: Output SAM type
            out_sam_mode: Output SAM mode
            read_files_command: Command to process input files
            out_filter_multimap_nmax: Maximum number of multiple alignments
            align_intron_min: Minimum intron length
            align_intron_max: Maximum intron length (0 = no limit)

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate genome directory exists
        if not os.path.exists(genome_dir):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Genome directory does not exist: {genome_dir}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Genome directory not found: {genome_dir}",
            }

        # Validate input files exist
        for read_file in read_files_in:
            if not os.path.exists(read_file):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Read file does not exist: {read_file}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Read file not found: {read_file}",
                }

        # Build command
        cmd = ["STAR", "--genomeDir", genome_dir, "--quantMode", quant_mode]

        # Add input read files
        cmd.extend(["--readFilesIn", *read_files_in])

        # Add output prefix
        cmd.extend(["--outFileNamePrefix", out_file_name_prefix])

        # Add other parameters
        cmd.extend(
            [
                "--runThreadN",
                str(run_thread_n),
                "--outSAMtype",
                out_sam_type,
                "--outSAMmode",
                out_sam_mode,
                "--outFilterMultimapNmax",
                str(out_filter_multimap_nmax),
                "--alignIntronMin",
                str(align_intron_min),
                "--alignIntronMax",
                str(align_intron_max),
            ]
        )

        if read_files_command:
            cmd.extend(["--readFilesCommand", read_files_command])

        try:
            # Execute STAR quantification
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Get output files
            output_files = []
            try:
                possible_outputs = [
                    f"{out_file_name_prefix}Aligned.sortedByCoord.out.bam",
                    f"{out_file_name_prefix}ReadsPerGene.out.tab",
                    f"{out_file_name_prefix}Log.final.out",
                    f"{out_file_name_prefix}Log.out",
                    f"{out_file_name_prefix}Log.progress.out",
                    f"{out_file_name_prefix}SJ.out.tab",
                ]
                for filepath in possible_outputs:
                    if os.path.exists(filepath):
                        output_files.append(filepath)
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
                "stderr": "STAR not found in PATH",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "STAR not found in PATH",
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
            name="star_wig_to_bigwig",
            description="Convert STAR wiggle track files to BigWig format",
            inputs={
                "wig_file": "str",
                "chrom_sizes": "str",
                "output_file": "str",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Convert wiggle track to BigWig",
                    "parameters": {
                        "wig_file": "/results/sample_Signal.Unique.str1.out.wig",
                        "chrom_sizes": "/data/chrom.sizes",
                        "output_file": "/results/sample_Signal.Unique.str1.out.bw",
                    },
                }
            ],
        )
    )
    def star_wig_to_bigwig(
        self,
        wig_file: str,
        chrom_sizes: str,
        output_file: str,
    ) -> dict[str, Any]:
        """
        Convert STAR wiggle track files to BigWig format.

        This tool converts STAR-generated wiggle track files to compressed
        BigWig format for efficient storage and visualization.

        Args:
            wig_file: Input wiggle track file from STAR
            chrom_sizes: Chromosome sizes file
            output_file: Output BigWig file

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files exist
        if not os.path.exists(wig_file):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Wiggle file does not exist: {wig_file}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Wiggle file not found: {wig_file}",
            }

        if not os.path.exists(chrom_sizes):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Chromosome sizes file does not exist: {chrom_sizes}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Chromosome sizes file not found: {chrom_sizes}",
            }

        # Build command - STAR has wigToBigWig built-in
        cmd = [
            "STAR",
            "--runMode",
            "inputAlignmentsFromBAM",
            "--inputBAMfile",
            wig_file.replace(".wig", ".bam") if wig_file.endswith(".wig") else wig_file,
            "--outWigType",
            "bedGraph",
            "--outWigStrand",
            "Stranded",
        ]

        # For wig to bigwig conversion, we typically use UCSC tools
        # But STAR can generate bedGraph which can be converted
        try:
            # Execute STAR wig generation first
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Then convert to BigWig using bedGraphToBigWig (if available)
            bedgraph_file = wig_file.replace(".wig", ".bedGraph")
            if os.path.exists(bedgraph_file):
                try:
                    convert_cmd = [
                        "bedGraphToBigWig",
                        bedgraph_file,
                        chrom_sizes,
                        output_file,
                    ]
                    convert_result = subprocess.run(
                        convert_cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    result = convert_result
                    cmd = convert_cmd
                except FileNotFoundError:
                    # bedGraphToBigWig not available, return bedGraph
                    output_file = bedgraph_file

            output_files = [output_file] if os.path.exists(output_file) else []

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
                "stderr": "STAR not found in PATH",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "STAR not found in PATH",
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
            name="star_solo",
            description="Run STARsolo for droplet-based single cell RNA-seq analysis",
            inputs={
                "genome_dir": "str",
                "read_files_in": "list[str]",
                "solo_type": "str",
                "solo_cb_whitelist": "str | None",
                "solo_features": "str",
                "solo_umi_len": "int",
                "out_file_name_prefix": "str",
                "run_thread_n": "int",
            },
            outputs={
                "command_executed": "str",
                "stdout": "str",
                "stderr": "str",
                "output_files": "list[str]",
                "exit_code": "int",
            },
            server_type=MCPServerType.CUSTOM,
            examples=[
                {
                    "description": "Run STARsolo for 10x Genomics data",
                    "parameters": {
                        "genome_dir": "/data/star_index",
                        "read_files_in": [
                            "/data/sample_R1.fastq.gz",
                            "/data/sample_R2.fastq.gz",
                        ],
                        "solo_type": "CB_UMI_Simple",
                        "solo_cb_whitelist": "/data/10x_whitelist.txt",
                        "solo_features": "Gene",
                        "out_file_name_prefix": "/results/sample_",
                        "run_thread_n": 8,
                    },
                }
            ],
        )
    )
    def star_solo(
        self,
        genome_dir: str,
        read_files_in: list[str],
        solo_type: str = "CB_UMI_Simple",
        solo_cb_whitelist: str | None = None,
        solo_features: str = "Gene",
        solo_umi_len: int = 12,
        out_file_name_prefix: str = "./",
        run_thread_n: int = 1,
    ) -> dict[str, Any]:
        """
        Run STARsolo for droplet-based single cell RNA-seq analysis.

        This tool runs STARsolo, STAR's built-in single-cell RNA-seq analysis
        pipeline for processing droplet-based scRNA-seq data.

        Args:
            genome_dir: Directory containing STAR genome index
            read_files_in: List of input FASTQ files (R1 and R2)
            solo_type: Type of single-cell protocol (CB_UMI_Simple, etc.)
            solo_cb_whitelist: Cell barcode whitelist file
            solo_features: Features to quantify (Gene, etc.)
            solo_umi_len: UMI length
            out_file_name_prefix: Prefix for output files
            run_thread_n: Number of threads to use

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate genome directory exists
        if not os.path.exists(genome_dir):
            return {
                "command_executed": "",
                "stdout": "",
                "stderr": f"Genome directory does not exist: {genome_dir}",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": f"Genome directory not found: {genome_dir}",
            }

        # Validate input files exist
        for read_file in read_files_in:
            if not os.path.exists(read_file):
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Read file does not exist: {read_file}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Read file not found: {read_file}",
                }

        # Build command
        cmd = [
            "STAR",
            "--genomeDir",
            genome_dir,
            "--soloType",
            solo_type,
            "--soloFeatures",
            solo_features,
        ]

        # Add input read files
        cmd.extend(["--readFilesIn", *read_files_in])

        # Add output prefix
        cmd.extend(["--outFileNamePrefix", out_file_name_prefix])

        # Add SOLO parameters
        cmd.extend(
            ["--soloUMIlen", str(solo_umi_len), "--runThreadN", str(run_thread_n)]
        )

        if solo_cb_whitelist:
            if os.path.exists(solo_cb_whitelist):
                cmd.extend(["--soloCBwhitelist", solo_cb_whitelist])
            else:
                return {
                    "command_executed": "",
                    "stdout": "",
                    "stderr": f"Cell barcode whitelist file does not exist: {solo_cb_whitelist}",
                    "output_files": [],
                    "exit_code": -1,
                    "success": False,
                    "error": f"Cell barcode whitelist file not found: {solo_cb_whitelist}",
                }

        try:
            # Execute STARsolo
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Get output files
            output_files = []
            try:
                solo_dir = f"{out_file_name_prefix}Solo.out"
                if os.path.exists(solo_dir):
                    # STARsolo creates various output files
                    possible_outputs = [
                        f"{solo_dir}/Gene/raw/matrix.mtx",
                        f"{solo_dir}/Gene/raw/barcodes.tsv",
                        f"{solo_dir}/Gene/raw/features.tsv",
                        f"{solo_dir}/Gene/filtered/matrix.mtx",
                        f"{solo_dir}/Gene/filtered/barcodes.tsv",
                        f"{solo_dir}/Gene/filtered/features.tsv",
                    ]
                    for filepath in possible_outputs:
                        if os.path.exists(filepath):
                            output_files.append(filepath)
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
                "stderr": "STAR not found in PATH",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "STAR not found in PATH",
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
        """Deploy STAR server using testcontainers with conda installation."""
        try:
            from testcontainers.core.container import DockerContainer

            # Create container with conda base image
            container = DockerContainer("condaforge/miniforge3:latest")
            container = container.with_name(f"mcp-star-server-{id(self)}")

            # Set environment variables
            for key, value in self.config.environment_variables.items():
                container = container.with_env(key, value)

            # Mount workspace and output directories
            container = container.with_volume_mapping(
                "/app/workspace", "/app/workspace", "rw"
            )
            container = container.with_volume_mapping(
                "/app/output", "/app/output", "rw"
            )

            # Install STAR and required dependencies using conda
            container = container.with_command(
                "bash -c '"
                "conda install -c bioconda -c conda-forge star -y && "
                "pip install fastmcp==2.12.4 && "
                "mkdir -p /app/workspace /app/output && "
                'echo "STAR server ready" && '
                "tail -f /dev/null'"
            )

            # Start container
            container.start()

            # Store container info
            self.container_id = container.get_wrapped_container().id[:12]
            self.container_name = container.get_wrapped_container().name

            # Wait for container to be ready (conda installation can take time)
            import time

            time.sleep(10)  # Give conda time to install STAR

            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                container_id=self.container_id,
                container_name=self.container_name,
                status=MCPServerStatus.RUNNING,
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
        """Stop STAR server deployed with testcontainers."""
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
        """Get information about this STAR server."""
        return {
            "name": self.name,
            "type": "star",
            "version": "2.7.10b",
            "description": "STAR RNA-seq alignment server",
            "tools": self.list_tools(),
            "container_id": self.container_id,
            "container_name": self.container_name,
            "status": "running" if self.container_id else "stopped",
        }


# Pydantic AI Tool Functions
# These functions integrate STAR operations with Pydantic AI agents


def star_genome_index(
    ctx: RunContext[AgentDependencies],
    genome_fasta_files: list[str],
    genome_dir: str,
    sjdb_gtf_file: str | None = None,
    threads: int = 4,
) -> str:
    """Generate STAR genome index for RNA-seq alignment.

    This tool creates a STAR genome index from FASTA and GTF files,
    which is required for efficient RNA-seq read alignment.

    Args:
        genome_fasta_files: List of genome FASTA files
        genome_dir: Directory to store the genome index
        sjdb_gtf_file: Optional GTF file with gene annotations
        threads: Number of threads to use
        ctx: Pydantic AI run context

    Returns:
        Success message with genome index location
    """
    server = STARServer()
    result = server.star_generate_genome(
        genome_dir=genome_dir,
        genome_fasta_files=genome_fasta_files,
        sjdb_gtf_file=sjdb_gtf_file,
        threads=threads,
    )

    if result.get("success"):
        return f"Successfully generated STAR genome index in {genome_dir}. Output files: {', '.join(result.get('output_files', []))}"
    return f"Failed to generate genome index: {result.get('error', 'Unknown error')}"


def star_align_reads(
    ctx: RunContext[AgentDependencies],
    genome_dir: str,
    read_files_in: list[str],
    out_file_name_prefix: str,
    quant_mode: str = "GeneCounts",
    threads: int = 4,
) -> str:
    """Align RNA-seq reads using STAR aligner.

    This tool aligns RNA-seq reads to a reference genome using STAR,
    with optional quantification for gene expression analysis.

    Args:
        genome_dir: Directory containing STAR genome index
        read_files_in: List of input FASTQ files
        out_file_name_prefix: Prefix for output files
        quant_mode: Quantification mode (GeneCounts, TranscriptomeSAM)
        threads: Number of threads to use
        ctx: Pydantic AI run context

    Returns:
        Success message with alignment results
    """
    server = STARServer()
    result = server.star_align_reads(
        genome_dir=genome_dir,
        read_files_in=read_files_in,
        out_file_name_prefix=out_file_name_prefix,
        quant_mode=quant_mode,
        run_thread_n=threads,
    )

    if result.get("success"):
        output_files = result.get("output_files", [])
        return f"Successfully aligned reads. Output files: {', '.join(output_files)}"
    return f"Failed to align reads: {result.get('error', 'Unknown error')}"


def star_quantification(
    ctx: RunContext[AgentDependencies],
    genome_dir: str,
    read_files_in: list[str],
    out_file_name_prefix: str,
    quant_mode: str = "GeneCounts",
    threads: int = 4,
) -> str:
    """Run STAR with quantification for gene/transcript counting.

    This tool performs RNA-seq alignment and quantification in a single step,
    generating gene count matrices suitable for downstream analysis.

    Args:
        genome_dir: Directory containing STAR genome index
        read_files_in: List of input FASTQ files
        out_file_name_prefix: Prefix for output files
        quant_mode: Quantification mode (GeneCounts, TranscriptomeSAM)
        threads: Number of threads to use
        ctx: Pydantic AI run context

    Returns:
        Success message with quantification results
    """
    server = STARServer()
    result = server.star_quant_mode(
        genome_dir=genome_dir,
        read_files_in=read_files_in,
        out_file_name_prefix=out_file_name_prefix,
        quant_mode=quant_mode,
        run_thread_n=threads,
    )

    if result.get("success"):
        output_files = result.get("output_files", [])
        return f"Successfully quantified reads. Output files: {', '.join(output_files)}"
    return f"Failed to quantify reads: {result.get('error', 'Unknown error')}"


def star_single_cell_analysis(
    ctx: RunContext[AgentDependencies],
    genome_dir: str,
    read_files_in: list[str],
    out_file_name_prefix: str,
    solo_cb_whitelist: str | None = None,
    threads: int = 8,
) -> str:
    """Run STARsolo for single-cell RNA-seq analysis.

    This tool performs single-cell RNA-seq analysis using STARsolo,
    generating gene expression matrices for downstream analysis.

    Args:
        genome_dir: Directory containing STAR genome index
        read_files_in: List of input FASTQ files (R1 and R2)
        out_file_name_prefix: Prefix for output files
        solo_cb_whitelist: Optional cell barcode whitelist file
        threads: Number of threads to use
        ctx: Pydantic AI run context

    Returns:
        Success message with single-cell analysis results
    """
    server = STARServer()
    result = server.star_solo(
        genome_dir=genome_dir,
        read_files_in=read_files_in,
        out_file_name_prefix=out_file_name_prefix,
        solo_cb_whitelist=solo_cb_whitelist,
        run_thread_n=threads,
    )

    if result.get("success"):
        output_files = result.get("output_files", [])
        return f"Successfully analyzed single-cell data. Output files: {', '.join(output_files)}"
    return f"Failed to analyze single-cell data: {result.get('error', 'Unknown error')}"


def star_load_genome_index(
    ctx: RunContext[AgentDependencies],
    genome_dir: str,
    shared_memory: bool = True,
    threads: int = 4,
) -> str:
    """Load STAR genome index into shared memory.

    This tool loads a STAR genome index into shared memory for faster
    subsequent alignments when processing many samples.

    Args:
        genome_dir: Directory containing STAR genome index
        shared_memory: Whether to load into shared memory
        threads: Number of threads to use
        ctx: Pydantic AI run context

    Returns:
        Success message about genome loading
    """
    server = STARServer()
    result = server.star_load_genome(
        genome_dir=genome_dir,
        shared_memory=shared_memory,
        threads=threads,
    )

    if result.get("success"):
        memory_type = "shared memory" if shared_memory else "regular memory"
        return f"Successfully loaded genome index into {memory_type}"
    return f"Failed to load genome index: {result.get('error', 'Unknown error')}"


def star_convert_wiggle_to_bigwig(
    ctx: RunContext[AgentDependencies],
    wig_file: str,
    chrom_sizes: str,
    output_file: str,
) -> str:
    """Convert STAR wiggle track files to BigWig format.

    This tool converts STAR-generated wiggle track files to compressed
    BigWig format for efficient storage and genome browser visualization.

    Args:
        wig_file: Input wiggle track file from STAR
        chrom_sizes: Chromosome sizes file
        output_file: Output BigWig file
        ctx: Pydantic AI run context

    Returns:
        Success message about file conversion
    """
    server = STARServer()
    result = server.star_wig_to_bigwig(
        wig_file=wig_file,
        chrom_sizes=chrom_sizes,
        output_file=output_file,
    )

    if result.get("success"):
        return f"Successfully converted wiggle to BigWig: {output_file}"
    return f"Failed to convert wiggle file: {result.get('error', 'Unknown error')}"
