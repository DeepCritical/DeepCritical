"""
Genomics Agent with MCP Server Integration.

This agent uses Pydantic AI to let an LLM decide which bioinformatics tools
to call based on natural language prompts. Tools are backed by MCP servers.

Reference: burner_docs/haplotype_agent/02_implementation_plan.md
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

# Import existing MCP servers
from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer
from DeepResearch.src.tools.bioinformatics.haplotypecaller_server import (
    HaplotypeCallerServer,
)
from DeepResearch.src.tools.bioinformatics.samtools_server import SamtoolsServer
from examples.simple_genomics_discovery.genomics_deps import GenomicsAgentDeps

# For testing without API key
try:
    from pydantic_ai.models.test import TestModel
except ImportError:
    TestModel = None  # type: ignore[assignment,misc]

# Instantiate MCP servers (Phase 2: MCP Integration)
fastqc_server = FastQCServer()
samtools_server = SamtoolsServer()
haplotypecaller_server = HaplotypeCallerServer()


class GenomicsAnalysisResult(BaseModel):
    """Structured result from genomics analysis."""

    analysis_type: str  # "qc_only", "variant_calling", "full_pipeline"
    success: bool
    tools_used: list[str]
    output_files: dict[str, str]  # name -> path
    summary: str
    error: str | None = None
    variants_found: int | None = None


# Create Pydantic AI agent (Phase 3: Agent Creation)
# Use TestModel for testing/CI (no API key needed), real model from config otherwise
from DeepResearch.src.utils.config_loader import ModelConfigLoader

_model_config = ModelConfigLoader()
_model = (
    TestModel()
    if (not os.getenv("ANTHROPIC_API_KEY") and TestModel is not None)
    else _model_config.get_default_llm_model()
)

genomics_agent = Agent[GenomicsAgentDeps, GenomicsAnalysisResult](
    model=_model,
    deps_type=GenomicsAgentDeps,
    output_type=GenomicsAnalysisResult,  # CORRECT API per 03_code_patterns.md
    system_prompt="""
You are a genomics bioinformatics expert. You have access to these tools:

1. **run_fastqc**: Quality control for FASTQ/BAM files
   - Use this FIRST to check data quality
   - Returns HTML report with quality metrics
   - Backed by FastQCServer MCP server

2. **run_samtools_flagstat**: BAM file statistics
   - Use this to validate BAM files
   - Returns read counts, mapping stats
   - Backed by SamtoolsServer MCP server

3. **run_haplotypecaller**: Variant calling with GATK HaplotypeCaller
   - Use this AFTER QC to find variants
   - Requires: BAM file, reference genome, region
   - Returns: VCF file with variants
   - Backed by HaplotypeCallerServer MCP server

WORKFLOW GUIDELINES:
- For variant calling: ALWAYS run QC first, then validation, then variant calling
- For QC only: Just run run_fastqc
- For BAM validation: Run run_samtools_flagstat
- Always provide clear summaries of results

Return structured results with:
- analysis_type: Type of analysis performed
- tools_used: List of tools called
- output_files: Paths to all output files
- summary: Human-readable summary
- variants_found: Number of variants (if applicable)
""",
)


# Register MCP server methods as agent tools (Phase 4: Tool Registration)


@genomics_agent.tool
async def run_fastqc(
    ctx: RunContext[GenomicsAgentDeps], bam_file: str, output_dir: str | None = None
) -> dict[str, Any]:
    """
    Run FastQC quality control on a BAM file.

    Args:
        ctx: Agent run context with dependencies
        bam_file: Name of BAM file (in data_dir)
        output_dir: Output directory (defaults to ctx.deps.output_dir)

    Returns:
        Dictionary with QC results from FastQCServer
    """
    # Track tool usage
    ctx.deps.tools_called.append("fastqc")

    # Resolve paths
    bam_path = ctx.deps.data_dir / bam_file
    out_dir = ctx.deps.output_dir if output_dir is None else Path(output_dir)

    # Validate file exists
    if not bam_path.exists():
        return {
            "success": False,
            "error": f"BAM file not found: {bam_file}",
            "tool": "fastqc",
        }

    # Call MCP server (don't duplicate subprocess logic)
    try:
        result = fastqc_server.run_fastqc(
            input_files=[str(bam_path)],
            output_dir=str(out_dir),
            extract=False,
            threads=4,
        )
        return result
    except Exception as e:
        return {"success": False, "error": f"FastQC failed: {e}", "tool": "fastqc"}


@genomics_agent.tool
async def run_samtools_flagstat(
    ctx: RunContext[GenomicsAgentDeps], bam_file: str
) -> dict[str, Any]:
    """
    Run samtools flagstat to get BAM file statistics.

    Args:
        ctx: Agent run context with dependencies
        bam_file: Name of BAM file (in data_dir)

    Returns:
        Dictionary with BAM statistics from SamtoolsServer
    """
    # Track tool usage
    ctx.deps.tools_called.append("samtools_flagstat")

    # Resolve path
    bam_path = ctx.deps.data_dir / bam_file

    # Validate file exists
    if not bam_path.exists():
        return {
            "success": False,
            "error": f"BAM file not found: {bam_file}",
            "tool": "samtools_flagstat",
        }

    # Call MCP server (ACTUAL method name and parameter)
    try:
        result = samtools_server.samtools_flagstat(
            input_file=str(bam_path)  # FIXED: parameter is input_file not bam_file
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Samtools flagstat failed: {e}",
            "tool": "samtools_flagstat",
        }


@genomics_agent.tool
async def run_haplotypecaller(
    ctx: RunContext[GenomicsAgentDeps],
    bam_file: str,
    reference: str | None = None,
    output_vcf: str = "variants.vcf",
    region: str | None = None,
) -> dict[str, Any]:
    """
    Run GATK HaplotypeCaller for variant calling.

    Args:
        ctx: Agent run context with dependencies
        bam_file: Name of BAM file (in data_dir)
        reference: Reference genome (defaults to ctx.deps.reference_genome)
        output_vcf: Output VCF filename
        region: Genomic region (e.g., "20" for chr20)

    Returns:
        Dictionary with variant calling results from HaplotypeCallerServer
    """
    # Track tool usage
    ctx.deps.tools_called.append("haplotypecaller")

    # Resolve paths
    bam_path = ctx.deps.data_dir / bam_file
    ref_path = ctx.deps.reference_genome if reference is None else Path(reference)
    vcf_path = ctx.deps.output_dir / output_vcf

    # Validate files exist
    if not bam_path.exists():
        return {
            "success": False,
            "error": f"BAM file not found: {bam_file}",
            "tool": "haplotypecaller",
        }

    if not ref_path.exists():
        return {
            "success": False,
            "error": f"Reference genome not found: {ref_path}",
            "tool": "haplotypecaller",
        }

    # Call MCP server (ACTUAL method name is call_variants)
    try:
        result = haplotypecaller_server.call_variants(
            input_bam=str(bam_path),
            reference_fasta=str(
                ref_path
            ),  # FIXED: parameter is reference_fasta not reference
            output_vcf=str(vcf_path),
            intervals=region,  # FIXED: intervals is str not list[str]
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"GATK HaplotypeCaller failed: {e}",
            "tool": "haplotypecaller",
        }


# Main entry point (Phase 5: Entry Point)
async def run_genomics_analysis(
    prompt: str, data_dir: Path, output_dir: Path, reference_genome: Path
) -> GenomicsAnalysisResult:
    """
    Run genomics analysis based on natural language prompt.

    Args:
        prompt: User's analysis request
        data_dir: Directory with input data
        output_dir: Directory for results
        reference_genome: Path to reference FASTA

    Returns:
        Structured analysis results (GenomicsAnalysisResult)
    """
    deps = GenomicsAgentDeps(
        data_dir=data_dir, output_dir=output_dir, reference_genome=reference_genome
    )

    result = await genomics_agent.run(prompt, deps=deps)
    return result.output  # CORRECT API per 03_code_patterns.md
