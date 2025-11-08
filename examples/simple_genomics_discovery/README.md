# Simple Genomics Discovery Demo

End-to-end demonstration of GATK HaplotypeCaller variant calling using real genomic data.

## What This Does

Processes a pre-aligned BAM file to find genetic variants:

1. **Quality Control:** FastQC checks data quality
2. **Verification:** SAMtools validates BAM integrity
3. **Variant Calling:** GATK HaplotypeCaller identifies genetic differences
4. **Output:** VCF file with variants on chromosome 20

## What This Does NOT Do

- ❌ Does not include read alignment (starts with pre-aligned BAM)
- ❌ Does not demonstrate STAR or BWA aligners
- ❌ Does not include FASTQ processing

**Why?** This demo focuses on proving GATK HaplotypeCaller integration works. Starting from BAM is standard for variant calling tutorials and keeps setup simple.

## Prerequisites

- **AWS CLI:** For downloading data (`brew install awscli` on macOS)
- **Conda/Miniconda:** For installing tools ([installation guide](https://docs.conda.io/en/latest/miniconda.html))
- **~150 MB disk space:** For data + tools

## Quick Start

### 1. Download Data (~117 MB, 2 minutes)

```bash
./download_data.sh
```

Downloads from public AWS S3 (no account needed):
- chr20+21 b37 reference (108 MB)
- NA12878 test BAM (8.8 MB)

### 2. Install Tools

```bash
./install_tools.sh
conda activate genomics-demo
```

Installs via bioconda:
- GATK 4.6.1.0
- SAMtools 1.22
- FastQC 0.11.9

### 3. Run Pipeline

```bash
python agent_demo.py
```

Expected runtime: 3-5 minutes

### 4. Check Results

```bash
ls -lh output/
head -100 output/variants.vcf
open output/sample_fastqc.html  # macOS
```

## Agentic Workflow (NEW)

The genomics agent uses Pydantic AI + MCP servers to dynamically choose tools based on your natural language prompt.

### Setup

```bash
# Install Python dependencies (uses uv)
uv sync --dev

# Set API key
export ANTHROPIC_API_KEY="your-key"
```

### Run Agent

```bash
# Using uv (recommended)
uv run python run_agent_demo.py "Find variants in sample.bam on chr20"

# The agent will:
# 1. Analyze your prompt
# 2. Decide which MCP server tools to call
# 3. Execute the workflow (FastQC → SAMtools → GATK)
# 4. Return structured results
```

### Example Prompts

- `"Run quality control on sample.bam"`
- `"Validate sample.bam with samtools"`
- `"Find variants in sample.bam on chromosome 20"`
- `"Complete genomics analysis: QC, validation, and variant calling"`

### Architecture

The agent registers methods from existing MCP servers as tools:

- `FastQCServer.run_fastqc()` → `run_fastqc` tool
- `SamtoolsServer.samtools_flagstat()` → `run_samtools_flagstat` tool
- `HaplotypeCallerServer.call_variants()` → `run_haplotypecaller` tool

**No code duplication** - all tool logic is in the MCP servers.

**Key files:**
- `genomics_agent.py` - Agent with MCP server integration
- `genomics_deps.py` - Agent dependencies
- `run_agent_demo.py` - Demo CLI script

## Output Files

- `output/sample_fastqc.html` - Quality control report
- `output/variants.vcf` - Genetic variants (standard VCF format)

**Expected results:**
- ~40 variants from the NA12878 chr20 subset
- VCF ready for annotation/analysis

## Data Provenance

- **Reference:** GRCh37/b37 chr20+21 (Genome Reference Consortium)
- **Sample:** NA12878 (1000 Genomes Project reference individual)
- **Source:** Broad Institute public test data
- **Build:** GRCh37/b37 (contig naming: "20" not "chr20")

## Troubleshooting

### "aws: command not found"

Install AWS CLI:
```bash
# macOS
brew install awscli

# Linux
pip install awscli

# Windows
# Download from: https://aws.amazon.com/cli/
```

### "gatk: command not found"

Activate the conda environment:
```bash
conda activate genomics-demo
```

### "Reference sequence dictionary not found"

Re-run download script to get all required files:
```bash
rm -rf data/
./download_data.sh
```

### GATK fails with contig mismatch

Ensure you downloaded the b37 reference (not GRCh38). The BAM uses b37 naming ("20") not GRCh38 naming ("chr20").

## Technical Details

- **Reference build:** GRCh37/b37 (NOT GRCh38)
- **Contig naming:** "20", "21" (NOT "chr20", "chr21")
- **Why b37?** Test BAM is aligned to b37 - reference must match
- **Why chr20+21?** Small enough for fast demos (108 MB vs 3 GB full genome)

## Next Steps

- Annotate variants with VEP/SnpEff
- Query ClinVar for clinical significance
- Filter by quality (QUAL > 30, DP > 10)
- Integrate with DeepResearch agent
- Scale to full genome (swap reference)

## Citation

If you use this demo data:

```
1000 Genomes Project Consortium. (2015). A global reference for human genetic variation.
Nature, 526(7571), 68-74.

McKenna et al. (2010). The Genome Analysis Toolkit: a MapReduce framework for analyzing
next-generation DNA sequencing data. Genome Research, 20(9), 1297-1303.
```
