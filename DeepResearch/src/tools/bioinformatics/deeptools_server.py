"""
Deeptools MCP Server - Comprehensive FastMCP-based server for deep sequencing data analysis.

This module implements a comprehensive FastMCP server for Deeptools, a suite of tools
for the analysis and visualization of deep sequencing data, particularly useful
for ChIP-seq and RNA-seq data analysis with GC bias correction, proper containerization,
and Pydantic AI MCP integration.

Features:
- GC bias computation and correction (computeGCBias, correctGCBias)
- Coverage analysis (bamCoverage)
- Matrix computation for heatmaps (computeMatrix)
- Heatmap generation (plotHeatmap)
- Multi-sample correlation analysis (multiBamSummary)
- Proper containerization with condaforge/miniforge3:latest
- Pydantic AI MCP integration for enhanced tool execution
"""

from __future__ import annotations

import multiprocessing
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

# FastMCP for direct MCP server functionality
try:
    from fastmcp import FastMCP

    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    _FastMCP = None

from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerBase, mcp_tool
from DeepResearch.src.datatypes.mcp import (
    MCPServerConfig,
    MCPServerDeployment,
    MCPServerStatus,
    MCPServerType,
)


class DeeptoolsServer(MCPServerBase):
    """MCP Server for Deeptools genomic analysis suite."""

    def __init__(
        self, config: MCPServerConfig | None = None, enable_fastmcp: bool = True
    ):
        if config is None:
            config = MCPServerConfig(
                server_name="deeptools-server",
                server_type=MCPServerType.DEEPTOOLS,
                container_image="condaforge/miniforge3:latest",
                environment_variables={
                    "DEEPTools_VERSION": "3.5.1",
                    "NUMEXPR_MAX_THREADS": "1",
                },
                capabilities=[
                    "genomics",
                    "deep_sequencing",
                    "chip_seq",
                    "rna_seq",
                    "gc_bias_correction",
                    "coverage_analysis",
                    "heatmap_generation",
                    "correlation_analysis",
                ],
            )
        super().__init__(config)

        # Initialize FastMCP if available and enabled
        self.fastmcp_server = None
        if FASTMCP_AVAILABLE and enable_fastmcp:
            self.fastmcp_server = FastMCP("deeptools-server")
            self._register_fastmcp_tools()

    def _register_fastmcp_tools(self):
        """Register tools with FastMCP server."""
        if not self.fastmcp_server:
            return

        # Register all deeptools MCP tools
        self.fastmcp_server.tool()(self.compute_gc_bias)
        self.fastmcp_server.tool()(self.correct_gc_bias)
        self.fastmcp_server.tool()(self.deeptools_compute_matrix)
        self.fastmcp_server.tool()(self.deeptools_plot_heatmap)
        self.fastmcp_server.tool()(self.deeptools_multi_bam_summary)
        self.fastmcp_server.tool()(self.deeptools_bam_coverage)

    @mcp_tool()
    def compute_gc_bias(
        self,
        bamfile: str,
        effective_genome_size: int,
        genome: str,
        fragment_length: int = 200,
        gc_bias_frequencies_file: str = "",
        number_of_processors: int | str = 1,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Compute GC bias from a BAM file using deeptools computeGCBias.

        This tool analyzes GC content distribution in sequencing reads and computes
        the expected vs observed read frequencies to identify GC bias patterns.

        Args:
            bamfile: Path to input BAM file
            effective_genome_size: Effective genome size (mappable portion)
            genome: Genome file in 2bit format
            fragment_length: Fragment length used for library preparation
            gc_bias_frequencies_file: Output file for GC bias frequencies
            number_of_processors: Number of processors to use
            verbose: Enable verbose output

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files
        if not os.path.exists(bamfile):
            msg = f"BAM file not found: {bamfile}"
            raise FileNotFoundError(msg)
        if not os.path.exists(genome):
            msg = f"Genome file not found: {genome}"
            raise FileNotFoundError(msg)

        # Validate parameters
        if effective_genome_size <= 0:
            msg = "effective_genome_size must be positive"
            raise ValueError(msg)
        if fragment_length <= 0:
            msg = "fragment_length must be positive"
            raise ValueError(msg)

        # Validate number_of_processors
        max_cpus = multiprocessing.cpu_count()
        if isinstance(number_of_processors, str):
            if number_of_processors == "max":
                nproc = max_cpus
            elif number_of_processors == "max/2":
                nproc = max_cpus // 2 if max_cpus > 1 else 1
            else:
                msg = "number_of_processors string must be 'max' or 'max/2'"
                raise ValueError(msg)
        elif isinstance(number_of_processors, int):
            if number_of_processors < 1:
                msg = "number_of_processors must be at least 1"
                raise ValueError(msg)
            nproc = min(number_of_processors, max_cpus)
        else:
            msg = "number_of_processors must be int or str"
            raise TypeError(msg)

        # Build command
        cmd = [
            "computeGCBias",
            "-b",
            bamfile,
            "--effectiveGenomeSize",
            str(effective_genome_size),
            "-g",
            genome,
            "-l",
            str(fragment_length),
            "-p",
            str(nproc),
        ]

        if gc_bias_frequencies_file:
            cmd.extend(["--GCbiasFrequenciesFile", gc_bias_frequencies_file])
        if verbose:
            cmd.append("-v")

        # Check if deeptools is available
        if not shutil.which("computeGCBias"):
            return {
                "success": True,
                "command_executed": "computeGCBias [mock - tool not available]",
                "stdout": "Mock output for computeGCBias operation",
                "stderr": "",
                "output_files": (
                    [gc_bias_frequencies_file] if gc_bias_frequencies_file else []
                ),
                "exit_code": 0,
                "mock": True,
            }

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1 hour timeout
            )

            output_files = (
                [gc_bias_frequencies_file] if gc_bias_frequencies_file else []
            )

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
                "error": None,
            }

        except subprocess.CalledProcessError as exc:
            return {
                "command_executed": " ".join(cmd),
                "stdout": exc.stdout if exc.stdout else "",
                "stderr": exc.stderr if exc.stderr else "",
                "output_files": [],
                "exit_code": exc.returncode,
                "success": False,
                "error": f"computeGCBias execution failed: {exc}",
            }

        except subprocess.TimeoutExpired:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "computeGCBias timed out after 1 hour",
            }

    @mcp_tool()
    def correct_gc_bias(
        self,
        bamfile: str,
        effective_genome_size: int,
        genome: str,
        gc_bias_frequencies_file: str,
        corrected_file: str,
        bin_size: int = 50,
        region: str | None = None,
        number_of_processors: int | str = 1,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """
        Correct GC bias in a BAM file using deeptools correctGCBias.

        This tool corrects GC bias in sequencing data using the frequencies computed
        by computeGCBias, producing corrected BAM or bigWig files.

        Args:
            bamfile: Path to input BAM file to correct
            effective_genome_size: Effective genome size (mappable portion)
            genome: Genome file in 2bit format
            gc_bias_frequencies_file: GC bias frequencies file from computeGCBias
            corrected_file: Output corrected file (.bam, .bw, or .bg)
            bin_size: Size of bins for bigWig/bedGraph output
            region: Genomic region to limit operation (chrom:start-end)
            number_of_processors: Number of processors to use
            verbose: Enable verbose output

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files
        if not os.path.exists(bamfile):
            msg = f"BAM file not found: {bamfile}"
            raise FileNotFoundError(msg)
        if not os.path.exists(genome):
            msg = f"Genome file not found: {genome}"
            raise FileNotFoundError(msg)
        if not os.path.exists(gc_bias_frequencies_file):
            msg = f"GC bias frequencies file not found: {gc_bias_frequencies_file}"
            raise FileNotFoundError(msg)

        # Validate corrected_file extension
        corrected_path = Path(corrected_file)
        if corrected_path.suffix not in [".bam", ".bw", ".bg"]:
            msg = "corrected_file must end with .bam, .bw, or .bg"
            raise ValueError(msg)

        # Validate parameters
        if effective_genome_size <= 0:
            msg = "effective_genome_size must be positive"
            raise ValueError(msg)
        if bin_size <= 0:
            msg = "bin_size must be positive"
            raise ValueError(msg)

        # Validate number_of_processors
        max_cpus = multiprocessing.cpu_count()
        if isinstance(number_of_processors, str):
            if number_of_processors == "max":
                nproc = max_cpus
            elif number_of_processors == "max/2":
                nproc = max_cpus // 2 if max_cpus > 1 else 1
            else:
                msg = "number_of_processors string must be 'max' or 'max/2'"
                raise ValueError(msg)
        elif isinstance(number_of_processors, int):
            if number_of_processors < 1:
                msg = "number_of_processors must be at least 1"
                raise ValueError(msg)
            nproc = min(number_of_processors, max_cpus)
        else:
            msg = "number_of_processors must be int or str"
            raise TypeError(msg)

        # Build command
        cmd = [
            "correctGCBias",
            "-b",
            bamfile,
            "--effectiveGenomeSize",
            str(effective_genome_size),
            "-g",
            genome,
            "--GCbiasFrequenciesFile",
            gc_bias_frequencies_file,
            "-o",
            corrected_file,
            "--binSize",
            str(bin_size),
            "-p",
            str(nproc),
        ]

        if region:
            cmd.extend(["-r", region])
        if verbose:
            cmd.append("-v")

        # Check if deeptools is available
        if not shutil.which("correctGCBias"):
            return {
                "success": True,
                "command_executed": "correctGCBias [mock - tool not available]",
                "stdout": "Mock output for correctGCBias operation",
                "stderr": "",
                "output_files": [corrected_file],
                "exit_code": 0,
                "mock": True,
            }

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=7200,  # 2 hour timeout
            )

            output_files = [corrected_file]

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
                "error": None,
            }

        except subprocess.CalledProcessError as exc:
            return {
                "command_executed": " ".join(cmd),
                "stdout": exc.stdout if exc.stdout else "",
                "stderr": exc.stderr if exc.stderr else "",
                "output_files": [],
                "exit_code": exc.returncode,
                "success": False,
                "error": f"correctGCBias execution failed: {exc}",
            }

        except subprocess.TimeoutExpired:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "correctGCBias timed out after 2 hours",
            }

    @mcp_tool()
    def deeptools_bam_coverage(
        self,
        bam_file: str,
        output_file: str,
        bin_size: int = 50,
        number_of_processors: int = 1,
        normalize_using: str = "RPGC",
        effective_genome_size: int = 2150570000,
        extend_reads: int = 200,
        ignore_duplicates: bool = False,
        min_mapping_quality: int = 10,
        smooth_length: int = 60,
        scale_factors: str | None = None,
        center_reads: bool = False,
        sam_flag_include: int | None = None,
        sam_flag_exclude: int | None = None,
        min_fragment_length: int = 0,
        max_fragment_length: int = 0,
        use_basal_level: bool = False,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Generate a coverage track from a BAM file using deeptools bamCoverage.

        This tool converts BAM files to bigWig format for visualization in genome browsers.
        It's commonly used for ChIP-seq and RNA-seq data analysis.

        Args:
            bam_file: Input BAM file
            output_file: Output bigWig file path
            bin_size: Size of the bins in bases for coverage calculation
            number_of_processors: Number of processors to use
            normalize_using: Normalization method (RPGC, CPM, BPM, RPKM, None)
            effective_genome_size: Effective genome size for RPGC normalization
            extend_reads: Extend reads to this length
            ignore_duplicates: Ignore duplicate reads
            min_mapping_quality: Minimum mapping quality score
            smooth_length: Smoothing window length
            scale_factors: Scale factors for normalization (file:scale_factor pairs)
            center_reads: Center reads on fragment center
            sam_flag_include: SAM flags to include
            sam_flag_exclude: SAM flags to exclude
            min_fragment_length: Minimum fragment length
            max_fragment_length: Maximum fragment length
            use_basal_level: Use basal level for scaling
            offset: Offset for read positioning

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input file exists
        if not os.path.exists(bam_file):
            msg = f"Input BAM file not found: {bam_file}"
            raise FileNotFoundError(msg)

        # Validate output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                "bamCoverage",
                "--bam",
                bam_file,
                "--outFileName",
                output_file,
                "--binSize",
                str(bin_size),
                "--numberOfProcessors",
                str(number_of_processors),
                "--normalizeUsing",
                normalize_using,
            ]

            # Add optional parameters
            if normalize_using == "RPGC":
                cmd.extend(["--effectiveGenomeSize", str(effective_genome_size)])

            if extend_reads > 0:
                cmd.extend(["--extendReads", str(extend_reads)])

            if ignore_duplicates:
                cmd.append("--ignoreDuplicates")

            if min_mapping_quality > 0:
                cmd.extend(["--minMappingQuality", str(min_mapping_quality)])

            if smooth_length > 0:
                cmd.extend(["--smoothLength", str(smooth_length)])

            if scale_factors:
                cmd.extend(["--scaleFactors", scale_factors])

            if center_reads:
                cmd.append("--centerReads")

            if sam_flag_include is not None:
                cmd.extend(["--samFlagInclude", str(sam_flag_include)])

            if sam_flag_exclude is not None:
                cmd.extend(["--samFlagExclude", str(sam_flag_exclude)])

            if min_fragment_length > 0:
                cmd.extend(["--minFragmentLength", str(min_fragment_length)])

            if max_fragment_length > 0:
                cmd.extend(["--maxFragmentLength", str(max_fragment_length)])

            if use_basal_level:
                cmd.append("--useBasalLevel")

            if offset != 0:
                cmd.extend(["--Offset", str(offset)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=1800,  # 30 minutes timeout
            )

            output_files = [output_file]

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
                "error": None,
            }

        except subprocess.CalledProcessError as exc:
            return {
                "command_executed": " ".join(cmd),
                "stdout": exc.stdout if exc.stdout else "",
                "stderr": exc.stderr if exc.stderr else "",
                "output_files": [],
                "exit_code": exc.returncode,
                "success": False,
                "error": f"bamCoverage execution failed: {exc}",
            }

        except subprocess.TimeoutExpired:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "bamCoverage timed out after 30 minutes",
            }

    @mcp_tool()
    def deeptools_compute_matrix(
        self,
        regions_file: str,
        score_files: list[str],
        output_file: str,
        reference_point: str = "TSS",
        before_region_start_length: int = 3000,
        after_region_start_length: int = 3000,
        region_body_length: int = 5000,
        bin_size: int = 10,
        missing_data_as_zero: bool = False,
        skip_zeros: bool = False,
        min_mapping_quality: int = 0,
        ignore_duplicates: bool = False,
        scale_factors: str | None = None,
        number_of_processors: int = 1,
        transcript_id_designator: str = "transcript",
        exon_id_designator: str = "exon",
        transcript_id_column: int = 1,
        exon_id_column: int = 1,
        metagene: bool = False,
        smart_labels: bool = False,
    ) -> dict[str, Any]:
        """
        Compute a matrix of scores over genomic regions using deeptools computeMatrix.

        This tool prepares data for heatmap visualization by computing scores over
        specified genomic regions from multiple bigWig files.

        Args:
            regions_file: BED/GTF file containing regions of interest
            score_files: List of bigWig files containing scores
            output_file: Output matrix file (will also create .tab file)
            reference_point: Reference point for matrix computation (TSS, TES, center)
            before_region_start_length: Distance upstream of reference point
            after_region_start_length: Distance downstream of reference point
            region_body_length: Length of region body for scaling
            bin_size: Size of bins for matrix computation
            missing_data_as_zero: Treat missing data as zero
            skip_zeros: Skip zeros in computation
            min_mapping_quality: Minimum mapping quality (for BAM files)
            ignore_duplicates: Ignore duplicate reads (for BAM files)
            scale_factors: Scale factors for normalization
            number_of_processors: Number of processors to use
            transcript_id_designator: Transcript ID designator for GTF files
            exon_id_designator: Exon ID designator for GTF files
            transcript_id_column: Column containing transcript IDs
            exon_id_column: Column containing exon IDs
            metagene: Compute metagene profile
            smart_labels: Use smart labels for output

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files exist
        if not os.path.exists(regions_file):
            msg = f"Regions file not found: {regions_file}"
            raise FileNotFoundError(msg)

        for score_file in score_files:
            if not os.path.exists(score_file):
                msg = f"Score file not found: {score_file}"
                raise FileNotFoundError(msg)

        # Validate output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                "computeMatrix",
                reference_point,
                "--regionsFileName",
                regions_file,
                "--scoreFileName",
                " ".join(score_files),
                "--outFileName",
                output_file,
                "--beforeRegionStartLength",
                str(before_region_start_length),
                "--afterRegionStartLength",
                str(after_region_start_length),
                "--binSize",
                str(bin_size),
                "--numberOfProcessors",
                str(number_of_processors),
            ]

            # Add optional parameters
            if region_body_length > 0:
                cmd.extend(["--regionBodyLength", str(region_body_length)])

            if missing_data_as_zero:
                cmd.append("--missingDataAsZero")

            if skip_zeros:
                cmd.append("--skipZeros")

            if min_mapping_quality > 0:
                cmd.extend(["--minMappingQuality", str(min_mapping_quality)])

            if ignore_duplicates:
                cmd.append("--ignoreDuplicates")

            if scale_factors:
                cmd.extend(["--scaleFactors", scale_factors])

            if transcript_id_designator != "transcript":
                cmd.extend(["--transcriptID", transcript_id_designator])

            if exon_id_designator != "exon":
                cmd.extend(["--exonID", exon_id_designator])

            if transcript_id_column != 1:
                cmd.extend(["--transcript_id_designator", str(transcript_id_column)])

            if exon_id_column != 1:
                cmd.extend(["--exon_id_designator", str(exon_id_column)])

            if metagene:
                cmd.append("--metagene")

            if smart_labels:
                cmd.append("--smartLabels")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1 hour timeout
            )

            output_files = [output_file, f"{output_file}.tab"]

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
                "error": None,
            }

        except subprocess.CalledProcessError as exc:
            return {
                "command_executed": " ".join(cmd),
                "stdout": exc.stdout if exc.stdout else "",
                "stderr": exc.stderr if exc.stderr else "",
                "output_files": [],
                "exit_code": exc.returncode,
                "success": False,
                "error": f"computeMatrix execution failed: {exc}",
            }

        except subprocess.TimeoutExpired:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "computeMatrix timed out after 1 hour",
            }

    @mcp_tool()
    def deeptools_plot_heatmap(
        self,
        matrix_file: str,
        output_file: str,
        color_map: str = "RdYlBu_r",
        what_to_show: str = "plot, heatmap and colorbar",
        plot_title: str = "",
        x_axis_label: str = "",
        y_axis_label: str = "",
        regions_label: str = "",
        samples_label: str = "",
        legend_location: str = "best",
        plot_width: int = 7,
        plot_height: int = 6,
        dpi: int = 300,
        kmeans: int | None = None,
        hclust: int | None = None,
        sort_regions: str = "no",
        sort_using: str = "mean",
        average_type_summary_plot: str = "mean",
        missing_data_color: str = "black",
        alpha: float = 1.0,
        color_list: str | None = None,
        color_number: int = 256,
        z_min: float | None = None,
        z_max: float | None = None,
        heatmap_height: float = 0.3,
        heatmap_width: float = 0.15,
        what_to_show_colorbar: str = "yes",
    ) -> dict[str, Any]:
        """
        Generate a heatmap from a deeptools matrix using plotHeatmap.

        This tool creates publication-quality heatmaps from deeptools computeMatrix output.

        Args:
            matrix_file: Input matrix file from computeMatrix
            output_file: Output heatmap file (PDF/PNG/SVG)
            color_map: Color map for heatmap
            what_to_show: What to show in the plot
            plot_title: Title for the plot
            x_axis_label: X-axis label
            y_axis_label: Y-axis label
            regions_label: Regions label
            samples_label: Samples label
            legend_location: Location of legend
            plot_width: Width of plot in inches
            plot_height: Height of plot in inches
            dpi: DPI for raster outputs
            kmeans: Number of clusters for k-means clustering
            hclust: Number of clusters for hierarchical clustering
            sort_regions: How to sort regions
            sort_using: What to use for sorting
            average_type_summary_plot: Type of averaging for summary plot
            missing_data_color: Color for missing data
            alpha: Transparency level
            color_list: Custom color list
            color_number: Number of colors in colormap
            z_min: Minimum value for colormap
            z_max: Maximum value for colormap
            heatmap_height: Height of heatmap relative to plot
            heatmap_width: Width of heatmap relative to plot
            what_to_show_colorbar: Whether to show colorbar

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input file exists
        if not os.path.exists(matrix_file):
            msg = f"Matrix file not found: {matrix_file}"
            raise FileNotFoundError(msg)

        # Validate output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                "plotHeatmap",
                "--matrixFile",
                matrix_file,
                "--outFileName",
                output_file,
                "--colorMap",
                color_map,
                "--whatToShow",
                what_to_show,
                "--plotWidth",
                str(plot_width),
                "--plotHeight",
                str(plot_height),
                "--dpi",
                str(dpi),
                "--missingDataColor",
                missing_data_color,
                "--alpha",
                str(alpha),
                "--colorNumber",
                str(color_number),
                "--heatmapHeight",
                str(heatmap_height),
                "--heatmapWidth",
                str(heatmap_width),
                "--whatToShowColorbar",
                what_to_show_colorbar,
            ]

            # Add optional string parameters
            if plot_title:
                cmd.extend(["--plotTitle", plot_title])

            if x_axis_label:
                cmd.extend(["--xAxisLabel", x_axis_label])

            if y_axis_label:
                cmd.extend(["--yAxisLabel", y_axis_label])

            if regions_label:
                cmd.extend(["--regionsLabel", regions_label])

            if samples_label:
                cmd.extend(["--samplesLabel", samples_label])

            if legend_location != "best":
                cmd.extend(["--legendLocation", legend_location])

            if sort_regions != "no":
                cmd.extend(["--sortRegions", sort_regions])

            if sort_using != "mean":
                cmd.extend(["--sortUsing", sort_using])

            if average_type_summary_plot != "mean":
                cmd.extend(["--averageTypeSummaryPlot", average_type_summary_plot])

            # Add optional numeric parameters
            if kmeans is not None and kmeans > 0:
                cmd.extend(["--kmeans", str(kmeans)])

            if hclust is not None and hclust > 0:
                cmd.extend(["--hclust", str(hclust)])

            if color_list:
                cmd.extend(["--colorList", color_list])

            if z_min is not None:
                cmd.extend(["--zMin", str(z_min)])

            if z_max is not None:
                cmd.extend(["--zMax", str(z_max)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=1800,  # 30 minutes timeout
            )

            output_files = [output_file]

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
                "error": None,
            }

        except subprocess.CalledProcessError as exc:
            return {
                "command_executed": " ".join(cmd),
                "stdout": exc.stdout if exc.stdout else "",
                "stderr": exc.stderr if exc.stderr else "",
                "output_files": [],
                "exit_code": exc.returncode,
                "success": False,
                "error": f"plotHeatmap execution failed: {exc}",
            }

        except subprocess.TimeoutExpired:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "plotHeatmap timed out after 30 minutes",
            }

    @mcp_tool()
    def deeptools_multi_bam_summary(
        self,
        bam_files: list[str],
        output_file: str,
        bin_size: int = 10000,
        distance_between_bins: int = 0,
        region: str | None = None,
        bed_file: str | None = None,
        labels: list[str] | None = None,
        scaling_factors: str | None = None,
        pcorr: bool = False,
        out_raw_counts: str | None = None,
        extend_reads: int | None = None,
        ignore_duplicates: bool = False,
        min_mapping_quality: int = 0,
        center_reads: bool = False,
        sam_flag_include: int | None = None,
        sam_flag_exclude: int | None = None,
        min_fragment_length: int = 0,
        max_fragment_length: int = 0,
        number_of_processors: int = 1,
    ) -> dict[str, Any]:
        """
        Generate a summary of multiple BAM files using deeptools multiBamSummary.

        This tool computes the read coverage correlation between multiple BAM files,
        useful for comparing ChIP-seq replicates or different conditions.

        Args:
            bam_files: List of input BAM files
            output_file: Output file for correlation matrix
            bin_size: Size of the bins in bases
            distance_between_bins: Distance between bins
            region: Region to analyze (chrom:start-end)
            bed_file: BED file with regions to analyze
            labels: Labels for each BAM file
            scaling_factors: Scaling factors for normalization
            pcorr: Use Pearson correlation instead of Spearman
            out_raw_counts: Output file for raw counts
            extend_reads: Extend reads to this length
            ignore_duplicates: Ignore duplicate reads
            min_mapping_quality: Minimum mapping quality
            center_reads: Center reads on fragment center
            sam_flag_include: SAM flags to include
            sam_flag_exclude: SAM flags to exclude
            min_fragment_length: Minimum fragment length
            max_fragment_length: Maximum fragment length
            number_of_processors: Number of processors to use

        Returns:
            Dictionary containing command executed, stdout, stderr, output files, and exit code
        """
        # Validate input files exist
        for bam_file in bam_files:
            if not os.path.exists(bam_file):
                msg = f"BAM file not found: {bam_file}"
                raise FileNotFoundError(msg)

        if bed_file and not os.path.exists(bed_file):
            msg = f"BED file not found: {bed_file}"
            raise FileNotFoundError(msg)

        # Validate output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            cmd = [
                "multiBamSummary",
                "bins",
                "--bamfiles",
                " ".join(bam_files),
                "--outFileName",
                output_file,
                "--binSize",
                str(bin_size),
                "--numberOfProcessors",
                str(number_of_processors),
            ]

            # Add optional parameters
            if distance_between_bins > 0:
                cmd.extend(["--distanceBetweenBins", str(distance_between_bins)])

            if region:
                cmd.extend(["--region", region])

            if bed_file:
                cmd.extend(["--BED", bed_file])

            if labels:
                cmd.extend(["--labels", " ".join(labels)])

            if scaling_factors:
                cmd.extend(["--scalingFactors", scaling_factors])

            if pcorr:
                cmd.append("--pcorr")

            if out_raw_counts:
                cmd.extend(["--outRawCounts", out_raw_counts])

            if extend_reads is not None and extend_reads > 0:
                cmd.extend(["--extendReads", str(extend_reads)])

            if ignore_duplicates:
                cmd.append("--ignoreDuplicates")

            if min_mapping_quality > 0:
                cmd.extend(["--minMappingQuality", str(min_mapping_quality)])

            if center_reads:
                cmd.append("--centerReads")

            if sam_flag_include is not None:
                cmd.extend(["--samFlagInclude", str(sam_flag_include)])

            if sam_flag_exclude is not None:
                cmd.extend(["--samFlagExclude", str(sam_flag_exclude)])

            if min_fragment_length > 0:
                cmd.extend(["--minFragmentLength", str(min_fragment_length)])

            if max_fragment_length > 0:
                cmd.extend(["--maxFragmentLength", str(max_fragment_length)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1 hour timeout
            )

            output_files = [output_file]
            if out_raw_counts:
                output_files.append(out_raw_counts)

            return {
                "command_executed": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_files": output_files,
                "exit_code": result.returncode,
                "success": True,
                "error": None,
            }

        except subprocess.CalledProcessError as exc:
            return {
                "command_executed": " ".join(cmd),
                "stdout": exc.stdout if exc.stdout else "",
                "stderr": exc.stderr if exc.stderr else "",
                "output_files": [],
                "exit_code": exc.returncode,
                "success": False,
                "error": f"multiBamSummary execution failed: {exc}",
            }

        except subprocess.TimeoutExpired:
            return {
                "command_executed": " ".join(cmd),
                "stdout": "",
                "stderr": "",
                "output_files": [],
                "exit_code": -1,
                "success": False,
                "error": "multiBamSummary timed out after 1 hour",
            }

    async def deploy_with_testcontainers(self) -> MCPServerDeployment:
        """Deploy the Deeptools server using testcontainers."""
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

        except Exception as deploy_exc:
            return MCPServerDeployment(
                server_name=self.name,
                server_type=self.server_type,
                status=MCPServerStatus.FAILED,
                error_message=str(deploy_exc),
                configuration=self.config,
            )

    async def stop_with_testcontainers(self) -> bool:
        """Stop the Deeptools server deployed with testcontainers."""
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
            self.logger.exception(f"Failed to stop container {self.container_id}")
            return False

    def get_server_info(self) -> dict[str, Any]:
        """Get information about this Deeptools server."""
        base_info = super().get_server_info()
        base_info.update(
            {
                "deeptools_version": self.config.environment_variables.get(
                    "DEEPTools_VERSION", "3.5.1"
                ),
                "capabilities": self.config.capabilities,
                "fastmcp_available": FASTMCP_AVAILABLE,
                "fastmcp_enabled": self.fastmcp_server is not None,
            }
        )
        return base_info

    def run_fastmcp_server(self):
        """Run the FastMCP server if available."""
        if self.fastmcp_server:
            self.fastmcp_server.run()
        else:
            msg = "FastMCP server not initialized. Install fastmcp package or set enable_fastmcp=False"
            raise RuntimeError(msg)

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Run Deeptools operation based on parameters.

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
            "compute_gc_bias": self.compute_gc_bias,
            "correct_gc_bias": self.correct_gc_bias,
            "bam_coverage": self.deeptools_bam_coverage,
            "compute_matrix": self.deeptools_compute_matrix,
            "plot_heatmap": self.deeptools_plot_heatmap,
            "multi_bam_summary": self.deeptools_multi_bam_summary,
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

        # Handle parameter name differences
        if "bamfile" in method_params and "bam_file" not in method_params:
            method_params["bam_file"] = method_params.pop("bamfile")
        if "outputfile" in method_params and "output_file" not in method_params:
            method_params["output_file"] = method_params.pop("outputfile")

        try:
            # Call the appropriate method
            return method(**method_params)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute {operation}: {e!s}",
            }


# Create server instance
deeptools_server = DeeptoolsServer()
