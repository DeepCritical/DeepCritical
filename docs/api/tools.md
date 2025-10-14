# Tools API

This page provides comprehensive documentation for the DeepCritical tool system.

## Tool Framework

### ToolRunner
Abstract base class for all DeepCritical tools.

**Key Methods:**
- `run(parameters)`: Execute tool with given parameters
- `get_spec()`: Get tool specification
- `validate_inputs(parameters)`: Validate input parameters

**Attributes:**
- `spec`: Tool specification with metadata
- `category`: Tool category for organization

### ToolSpec
Defines tool metadata and interface specification.

**Attributes:**
- `name`: Unique tool identifier
- `description`: Human-readable description
- `category`: Tool category (search, bioinformatics, etc.)
- `inputs`: Input parameter specifications
- `outputs`: Output specifications
- `metadata`: Additional tool metadata

### ToolRegistry
Central registry for tool management and execution.

**Key Methods:**
- `register_tool(spec, runner)`: Register a new tool
- `execute_tool(name, parameters)`: Execute tool by name
- `list_tools()`: List all registered tools
- `get_tools_by_category(category)`: Get tools by category

## Tool Categories {#tool-categories}

DeepCritical organizes tools into logical categories:

- **KNOWLEDGE_QUERY**: Information retrieval tools
- **SEQUENCE_ANALYSIS**: Bioinformatics sequence tools
- **STRUCTURE_PREDICTION**: Protein structure tools
- **MOLECULAR_DOCKING**: Drug-target interaction tools
- **DE_NOVO_DESIGN**: Novel molecule design tools
- **FUNCTION_PREDICTION**: Function annotation tools
- **RAG**: Retrieval-augmented generation tools
- **SEARCH**: Web and document search tools
- **ANALYTICS**: Data analysis and visualization tools

## Execution Framework

### ExecutionResult
Results from tool execution.

**Attributes:**
- `success`: Whether execution was successful
- `data`: Main result data
- `metadata`: Additional result metadata
- `execution_time`: Time taken for execution
- `error`: Error message if execution failed

### ToolRequest
Request structure for tool execution.

**Attributes:**
- `tool_name`: Name of tool to execute
- `parameters`: Input parameters for the tool
- `metadata`: Additional request metadata

### ToolResponse
Response structure from tool execution.

**Attributes:**
- `success`: Whether execution was successful
- `data`: Tool output data
- `metadata`: Response metadata
- `citations`: Source citations if applicable

## Domain Tools {#domain-tools}

### Knowledge Query Tools {#knowledge-query-tools}

### Web Search Tools

::: DeepResearch.src.tools.websearch_tools.WebSearchTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

::: DeepResearch.src.tools.websearch_tools.ChunkedSearchTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

### Sequence Analysis Tools {#sequence-analysis-tools}

### Bioinformatics Tools

::: DeepResearch.src.tools.bioinformatics_tools.GOAnnotationTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

::: DeepResearch.src.tools.bioinformatics_tools.PubMedRetrievalTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

### Deep Search Tools

::: DeepResearch.src.tools.deepsearch_tools.DeepSearchTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

### RAG Tools

::: DeepResearch.src.tools.integrated_search_tools.RAGSearchTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

### Code Execution Tools

::: DeepResearch.src.agents.code_generation_agent.CodeGenerationAgent
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

::: DeepResearch.src.agents.code_generation_agent.CodeExecutionAgent
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

### Structure Prediction Tools {#structure-prediction-tools}

### Molecular Docking Tools {#molecular-docking-tools}

### De Novo Design Tools {#de-novo-design-tools}

### Function Prediction Tools {#function-prediction-tools}

### RAG Tools {#rag-tools}

### Search Tools {#search-tools}

### Analytics Tools {#analytics-tools}

### MCP Server Management Tools

::: DeepResearch.src.tools.mcp_server_management.MCPServerListTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

::: DeepResearch.src.tools.mcp_server_management.MCPServerDeployTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

::: DeepResearch.src.tools.mcp_server_management.MCPServerExecuteTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

::: DeepResearch.src.tools.mcp_server_management.MCPServerStatusTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

::: DeepResearch.src.tools.mcp_server_management.MCPServerStopTool
        handler: python
        options:
          docstring_style: google
          show_category_heading: true


## Enhanced MCP Server Framework

DeepCritical implements a comprehensive MCP (Model Context Protocol) server framework that integrates Pydantic AI for enhanced tool execution and reasoning capabilities. This framework supports both patterns described in the Pydantic AI MCP documentation:

1. **Agents acting as MCP clients**: Pydantic AI agents can connect to MCP servers to use their tools for research workflows
2. **Agents embedded within MCP servers**: Pydantic AI agents are integrated within MCP servers for enhanced tool execution

### Key Features

- **Pydantic AI Integration**: All MCP servers include embedded Pydantic AI agents for reasoning and tool orchestration
- **Testcontainers Deployment**: Isolated container deployment for secure, reproducible execution
- **Session Tracking**: Tool call history and session management for debugging and optimization
- **Type Safety**: Strongly-typed interfaces using Pydantic models
- **Error Handling**: Comprehensive error handling with retry logic
- **Health Monitoring**: Built-in health checks and resource management

### Architecture

The enhanced MCP server framework consists of:

- **MCPServerBase**: Base class providing Pydantic AI integration and testcontainers deployment
- **@mcp_tool decorator**: Custom decorator that creates Pydantic AI-compatible tools
- **Session Management**: MCPAgentSession for tracking tool calls and responses
- **Deployment Management**: Testcontainers-based deployment with resource limits
- **Type System**: Comprehensive Pydantic models for MCP operations

### MCP Server Base Classes

#### MCPServerBase
Enhanced base class for MCP server implementations with Pydantic AI integration.

**Key Features:**
- Pydantic AI agent integration for enhanced tool execution and reasoning
- Testcontainers deployment support with resource management
- Session tracking for tool call history and debugging
- Async/await support for concurrent tool execution
- Comprehensive error handling with retry logic
- Health monitoring and automatic recovery
- Type-safe interfaces using Pydantic models

**Key Methods:**
- `list_tools()`: List all available tools on the server
- `get_tool_spec(tool_name)`: Get specification for a specific tool
- `execute_tool(tool_name, **kwargs)`: Execute a tool with parameters
- `execute_tool_async(request)`: Execute tool asynchronously with session tracking
- `deploy_with_testcontainers()`: Deploy server using testcontainers
- `stop_with_testcontainers()`: Stop server deployed with testcontainers
- `health_check()`: Perform health check on deployed server
- `get_pydantic_ai_agent()`: Get the embedded Pydantic AI agent
- `get_session_info()`: Get session information and tool call history

**Attributes:**
- `name`: Server name
- `server_type`: Server type enum
- `config`: Server configuration (MCPServerConfig)
- `tools`: Dictionary of Pydantic AI Tool objects
- `pydantic_ai_agent`: Embedded Pydantic AI agent for reasoning
- `session`: MCPAgentSession for tracking interactions
- `container_id`: Container ID when deployed with testcontainers

### Available MCP Servers

DeepCritical includes 29 vendored MCP (Model Context Protocol) servers for common bioinformatics tools, deployed using testcontainers for isolated execution environments. The servers are built using Pydantic AI patterns and provide strongly-typed interfaces.

#### Quality Control & Preprocessing (7 servers)

##### FastQC Server

    ::: DeepResearch.src.tools.bioinformatics.fastqc_server.FastQCServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer
```

FastQC is a quality control tool for high throughput sequence data. This MCP server provides strongly-typed access to FastQC functionality with Pydantic AI integration for enhanced quality control workflows.

**Server Type:** FASTQC | **Capabilities:** Quality control, sequence analysis, FASTQ processing, Pydantic AI reasoning
**Pydantic AI Integration:** Embedded agent for automated quality assessment and report generation

**Available Tools:**
- `run_fastqc`: Run FastQC quality control on FASTQ files with comprehensive parameter support
- `check_fastqc_version`: Check the version of FastQC installed
- `list_fastqc_outputs`: List FastQC output files in a directory

##### Samtools Server

    ::: DeepResearch.src.tools.bioinformatics.samtools_server.SamtoolsServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.samtools_server import SamtoolsServer
```

Samtools is a suite of utilities for interacting with high-throughput sequencing data. This MCP server provides strongly-typed access to SAM/BAM processing tools.

**Server Type:** SAMTOOLS | **Capabilities:** Sequence analysis, BAM/SAM processing, statistics

**Available Tools:**
- `samtools_view`: Convert between SAM and BAM formats, extract regions
- `samtools_sort`: Sort BAM file by coordinate or read name
- `samtools_index`: Index a BAM file for fast random access
- `samtools_flagstat`: Generate flag statistics for a BAM file
- `samtools_stats`: Generate comprehensive statistics for a BAM file

##### Bowtie2 Server

    ::: DeepResearch.src.tools.bioinformatics.bowtie2_server.Bowtie2Server
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.bowtie2_server import Bowtie2Server
```

Bowtie2 is an ultrafast and memory-efficient tool for aligning sequencing reads to long reference sequences. This MCP server provides alignment and indexing capabilities.

**Server Type:** BOWTIE2 | **Capabilities:** Sequence alignment, index building, alignment inspection

**Available Tools:**
- `bowtie2_align`: Align sequencing reads to a reference genome
- `bowtie2_build`: Build a Bowtie2 index from a reference genome
- `bowtie2_inspect`: Inspect a Bowtie2 index

##### MACS3 Server

    ::: DeepResearch.src.tools.bioinformatics.macs3_server.MACS3Server
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.macs3_server import MACS3Server
```

MACS3 (Model-based Analysis of ChIP-Seq) is a tool for identifying transcription factor binding sites and histone modifications from ChIP-seq data.

**Server Type:** MACS3 | **Capabilities:** ChIP-seq peak calling, transcription factor binding sites

**Available Tools:**
- `macs3_callpeak`: Call peaks from ChIP-seq data using MACS3
- `macs3_bdgcmp`: Compare two bedGraph files to generate fold enrichment tracks
- `macs3_filterdup`: Filter duplicate reads from BAM files

##### HOMER Server

    ::: DeepResearch.src.tools.bioinformatics.homer_server.HOMERServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

HOMER (Hypergeometric Optimization of Motif EnRichment) is a suite of tools for Motif Discovery and next-gen sequencing analysis.

**Server Type:** HOMER | **Capabilities:** Motif discovery, ChIP-seq analysis, NGS analysis

**Available Tools:**
- `homer_findMotifs`: Find motifs in genomic regions using HOMER
- `homer_annotatePeaks`: Annotate peaks with genomic features
- `homer_mergePeaks`: Merge overlapping peaks

##### HISAT2 Server

    ::: DeepResearch.src.tools.bioinformatics.hisat2_server.HISAT2Server
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

HISAT2 is a fast and sensitive alignment program for mapping next-generation sequencing reads against a population of human genomes.

**Server Type:** HISAT2 | **Capabilities:** RNA-seq alignment, spliced alignment

**Available Tools:**
- `hisat2_build`: Build HISAT2 index from genome FASTA file
- `hisat2_align`: Align RNA-seq reads to reference genome

##### BEDTools Server

    ::: DeepResearch.src.tools.bioinformatics.bedtools_server.BEDToolsServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

BEDTools is a suite of utilities for comparing, summarizing, and intersecting genomic features in BED format.

**Server Type:** BEDTOOLS | **Capabilities:** Genomic interval operations, BED file manipulation

**Available Tools:**
- `bedtools_intersect`: Find overlapping intervals between two BED files
- `bedtools_merge`: Merge overlapping intervals in a BED file
- `bedtools_closest`: Find closest intervals between two BED files

##### STAR Server

    ::: DeepResearch.src.tools.bioinformatics.star_server.STARServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

STAR (Spliced Transcripts Alignment to a Reference) is a fast RNA-seq read mapper with support for splice-junctions.

**Server Type:** STAR | **Capabilities:** RNA-seq alignment, transcriptome analysis, spliced alignment

**Available Tools:**
- `star_genomeGenerate`: Generate STAR genome index from reference genome
- `star_alignReads`: Align RNA-seq reads to reference genome using STAR

##### BWA Server

    ::: DeepResearch.src.tools.bioinformatics.bwa_server.BWAServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

BWA (Burrows-Wheeler Aligner) is a software package for mapping low-divergent sequences against a large reference genome.

**Server Type:** BWA | **Capabilities:** DNA sequence alignment, short read alignment

**Available Tools:**
- `bwa_index`: Build BWA index from reference genome FASTA file
- `bwa_mem`: Align DNA sequencing reads using BWA-MEM algorithm
- `bwa_aln`: Align DNA sequencing reads using BWA-ALN algorithm

##### MultiQC Server

    ::: DeepResearch.src.tools.bioinformatics.multiqc_server.MultiQCServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

MultiQC is a tool to aggregate results from bioinformatics analyses across many samples into a single report.

**Server Type:** MULTIQC | **Capabilities:** Report generation, quality control visualization

**Available Tools:**
- `multiqc_run`: Generate MultiQC report from bioinformatics tool outputs
- `multiqc_modules`: List available MultiQC modules

##### Salmon Server

    ::: DeepResearch.src.tools.bioinformatics.salmon_server.SalmonServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Salmon is a tool for quantifying the expression of transcripts using RNA-seq data.

**Server Type:** SALMON | **Capabilities:** RNA-seq quantification, transcript abundance estimation

**Available Tools:**
- `salmon_index`: Build Salmon index from transcriptome FASTA
- `salmon_quant`: Quantify RNA-seq reads using Salmon pseudo-alignment

##### StringTie Server

    ::: DeepResearch.src.tools.bioinformatics.stringtie_server.StringTieServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

StringTie is a fast and highly efficient assembler of RNA-seq alignments into potential transcripts.

**Server Type:** STRINGTIE | **Capabilities:** Transcript assembly, quantification, differential expression

**Available Tools:**
- `stringtie_assemble`: Assemble transcripts from RNA-seq alignments
- `stringtie_merge`: Merge transcript assemblies from multiple runs

##### FeatureCounts Server

    ::: DeepResearch.src.tools.bioinformatics.featurecounts_server.FeatureCountsServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

FeatureCounts is a highly efficient general-purpose read summarization program that counts mapped reads for genomic features.

**Server Type:** FEATURECOUNTS | **Capabilities:** Read counting, gene expression quantification

**Available Tools:**
- `featurecounts_count`: Count reads overlapping genomic features

##### TrimGalore Server

    ::: DeepResearch.src.tools.bioinformatics.trimgalore_server.TrimGaloreServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Trim Galore is a wrapper script to automate quality and adapter trimming as well as quality control.

**Server Type:** TRIMGALORE | **Capabilities:** Adapter trimming, quality filtering, FASTQ preprocessing

**Available Tools:**
- `trimgalore_trim`: Trim adapters and low-quality bases from FASTQ files

##### Kallisto Server

    ::: DeepResearch.src.tools.bioinformatics.kallisto_server.KallistoServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Kallisto is a program for quantifying abundances of transcripts from RNA-seq data.

**Server Type:** KALLISTO | **Capabilities:** Fast RNA-seq quantification, pseudo-alignment

**Available Tools:**
- `kallisto_index`: Build Kallisto index from transcriptome
- `kallisto_quant`: Quantify RNA-seq reads using pseudo-alignment

##### HTSeq Server

    ::: DeepResearch.src.tools.bioinformatics.htseq_server.HTSeqServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

HTSeq is a Python package for analyzing high-throughput sequencing data.

**Server Type:** HTSEQ | **Capabilities:** Read counting, gene expression analysis

**Available Tools:**
- `htseq_count`: Count reads overlapping genomic features using HTSeq

##### TopHat Server

    ::: DeepResearch.src.tools.bioinformatics.tophat_server.TopHatServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

TopHat is a fast splice junction mapper for RNA-seq reads.

**Server Type:** TOPHAT | **Capabilities:** RNA-seq splice-aware alignment, junction discovery

**Available Tools:**
- `tophat_align`: Align RNA-seq reads to reference genome

##### Picard Server

    ::: DeepResearch.src.tools.bioinformatics.picard_server.PicardServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Picard is a set of command line tools for manipulating high-throughput sequencing data.

**Server Type:** PICARD | **Capabilities:** SAM/BAM processing, duplicate marking, quality control

**Available Tools:**
- `picard_mark_duplicates`: Mark duplicate reads in BAM files
- `picard_collect_alignment_summary_metrics`: Collect alignment summary metrics

##### BCFtools Server

    ::: DeepResearch.src.tools.bioinformatics.bcftools_server.BCFtoolsServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.bcftools_server import BCFtoolsServer
```

BCFtools is a suite of programs for manipulating variant calls in the Variant Call Format (VCF) and its binary counterpart BCF. This MCP server provides strongly-typed access to BCFtools with Pydantic AI integration for variant analysis workflows.

**Server Type:** BCFTOOLS | **Capabilities:** Variant analysis, VCF processing, genomics, Pydantic AI reasoning
**Pydantic AI Integration:** Embedded agent for automated variant filtering and analysis

**Available Tools:**
- `bcftools_view`: View, subset and filter VCF/BCF files
- `bcftools_stats`: Parse VCF/BCF files and generate statistics
- `bcftools_filter`: Filter VCF/BCF files using arbitrary expressions

##### BEDTools Server

    ::: DeepResearch.src.tools.bioinformatics.bedtools_server.BEDToolsServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.bedtools_server import BEDToolsServer
```

BEDtools is a suite of utilities for comparing, summarizing, and intersecting genomic features in BED format. This MCP server provides strongly-typed access to BEDtools with Pydantic AI integration for genomic interval analysis.

**Server Type:** BEDTOOLS | **Capabilities:** Genomics, BED operations, interval arithmetic, Pydantic AI reasoning
**Pydantic AI Integration:** Embedded agent for automated genomic analysis workflows

**Available Tools:**
- `bedtools_intersect`: Find overlapping intervals between genomic features
- `bedtools_merge`: Merge overlapping/adjacent intervals

##### Cutadapt Server

    ::: DeepResearch.src.tools.bioinformatics.cutadapt_server.CutadaptServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.cutadapt_server import CutadaptServer
```

Cutadapt is a tool for removing adapter sequences, primers, and poly-A tails from high-throughput sequencing reads. This MCP server provides strongly-typed access to Cutadapt with Pydantic AI integration for sequence preprocessing workflows.

**Server Type:** CUTADAPT | **Capabilities:** Adapter trimming, sequence preprocessing, FASTQ processing, Pydantic AI reasoning
**Pydantic AI Integration:** Embedded agent for automated adapter detection and trimming

**Available Tools:**
- `cutadapt_trim`: Remove adapters and low-quality bases from FASTQ files

##### Fastp Server

    ::: DeepResearch.src.tools.bioinformatics.fastp_server.FastpServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.fastp_server import FastpServer
```

Fastp is an ultra-fast all-in-one FASTQ preprocessor that can perform quality control, adapter trimming, quality filtering, per-read quality pruning, and many other operations. This MCP server provides strongly-typed access to Fastp with Pydantic AI integration.

**Server Type:** FASTP | **Capabilities:** FASTQ preprocessing, quality control, adapter trimming, Pydantic AI reasoning
**Pydantic AI Integration:** Embedded agent for automated quality control workflows

**Available Tools:**
- `fastp_process`: Comprehensive FASTQ preprocessing and quality control

##### BUSCO Server

    ::: DeepResearch.src.tools.bioinformatics.busco_server.BUSCOServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

```python
from DeepResearch.src.tools.bioinformatics.busco_server import BUSCOServer
```

BUSCO (Benchmarking Universal Single-Copy Orthologs) assesses genome assembly and annotation completeness by searching for single-copy orthologs. This MCP server provides strongly-typed access to BUSCO with Pydantic AI integration for genome quality assessment.

**Server Type:** BUSCO | **Capabilities:** Genome completeness assessment, ortholog detection, quality metrics, Pydantic AI reasoning
**Pydantic AI Integration:** Embedded agent for automated genome quality analysis

**Available Tools:**
- `busco_run`: Assess genome assembly completeness using BUSCO

##### DeepTools Server

    ::: DeepResearch.src.tools.bioinformatics.deeptools_server.DeepToolsServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

deepTools is a suite of user-friendly tools for the exploration of deep-sequencing data.

**Server Type:** DEEPTOOLS | **Capabilities:** NGS data analysis, visualization, quality control

**Available Tools:**
- `deeptools_bamCoverage`: Generate coverage tracks from BAM files
- `deeptools_computeMatrix`: Compute matrices for heatmaps from BAM files

##### FreeBayes Server

    ::: DeepResearch.src.tools.bioinformatics.freebayes_server.FreeBayesServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

FreeBayes is a Bayesian genetic variant detector designed to find small polymorphisms.

**Server Type:** FREEBAYES | **Capabilities:** Variant calling, SNP detection, indel detection

**Available Tools:**
- `freebayes_call`: Call variants from BAM files using FreeBayes

##### Flye Server

    ::: DeepResearch.src.tools.bioinformatics.flye_server.FlyeServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Flye is a de novo assembler for single-molecule sequencing reads.

**Server Type:** FLYE | **Capabilities:** Genome assembly, long-read assembly

**Available Tools:**
- `flye_assemble`: Assemble genome from long-read sequencing data

##### MEME Server

    ::: DeepResearch.src.tools.bioinformatics.meme_server.MEMEServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

MEME (Multiple EM for Motif Elicitation) is a tool for discovering motifs in a group of related DNA or protein sequences.

**Server Type:** MEME | **Capabilities:** Motif discovery, sequence analysis

**Available Tools:**
- `meme_discover`: Discover motifs in DNA or protein sequences

##### Minimap2 Server

    ::: DeepResearch.src.tools.bioinformatics.minimap2_server.Minimap2Server
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Minimap2 is a versatile pairwise aligner for nucleotide sequences.

**Server Type:** MINIMAP2 | **Capabilities:** Sequence alignment, long-read alignment

**Available Tools:**
- `minimap2_align`: Align sequences using minimap2 algorithm

##### Qualimap Server

    ::: DeepResearch.src.tools.bioinformatics.qualimap_server.QualimapServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Qualimap is a platform-independent application written in Java and R that provides both a Graphical User Interface (GUI) and a command-line interface to facilitate the quality control of alignment sequencing data.

**Server Type:** QUALIMAP | **Capabilities:** Quality control, alignment analysis, RNA-seq analysis

**Available Tools:**
- `qualimap_bamqc`: Generate quality control report for BAM files
- `qualimap_rnaseq`: Generate RNA-seq quality control report

##### Seqtk Server

    ::: DeepResearch.src.tools.bioinformatics.seqtk_server.SeqtkServer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Seqtk is a fast and lightweight tool for processing sequences in the FASTA or FASTQ format.

**Server Type:** SEQTK | **Capabilities:** FASTA/FASTQ processing, sequence manipulation

**Available Tools:**
- `seqtk_seq`: Convert and manipulate FASTA/FASTQ files
- `seqtk_subseq`: Extract subsequences from FASTA/FASTQ files

#### Deployment
```python
from DeepResearch.src.tools.bioinformatics.fastqc_server import FastQCServer
from DeepResearch.datatypes.mcp import MCPServerConfig

config = MCPServerConfig(
    server_name="fastqc-server",
    server_type="fastqc",
    container_image="python:3.11-slim",
)

server = FastQCServer(config)
deployment = await server.deploy_with_testcontainers()
```

#### Available Servers by Category

**Quality Control & Preprocessing:**
- FastQC, TrimGalore, Cutadapt, Fastp, MultiQC, Qualimap, Seqtk

**Sequence Alignment:**
- Bowtie2, BWA, HISAT2, STAR, TopHat, Minimap2

**RNA-seq Quantification & Assembly:**
- Salmon, Kallisto, StringTie, FeatureCounts, HTSeq

**Genome Analysis & Manipulation:**
- Samtools, BEDTools, Picard, DeepTools

**ChIP-seq & Epigenetics:**
- MACS3, HOMER, MEME

**Genome Assembly:**
- Flye

**Genome Assembly Assessment:**
- BUSCO

**Variant Analysis:**
- BCFtools, FreeBayes

### Enhanced MCP Server Management Tools

DeepCritical provides comprehensive tools for managing MCP server deployments using testcontainers with Pydantic AI integration:

#### MCPServerListTool
Lists all available vendored MCP servers.

**Features:**
- Lists all 29 MCP servers with descriptions and capabilities
- Shows deployment status and available tools
- Supports filtering and detailed information

#### MCPServerDeployTool
Deploys vendored MCP servers using testcontainers.

**Features:**
- Deploys any of the 29 MCP servers in isolated containers
- Supports custom configurations and resource limits
- Provides detailed deployment information

#### MCPServerExecuteTool
Executes tools on deployed MCP servers.

**Features:**
- Executes specific tools on deployed MCP servers
- Supports synchronous and asynchronous execution
- Provides comprehensive error handling and retry logic
- Returns detailed execution results

#### MCPServerStatusTool
Checks deployment status of MCP servers.

**Features:**
- Checks deployment status of individual servers or all servers
- Provides container and deployment information
- Supports health monitoring

#### MCPServerStopTool
Stops deployed MCP servers.

**Features:**
- Stops and cleans up deployed MCP server containers
- Provides confirmation of stop operations
- Handles resource cleanup

#### TestcontainersDeployer
::: DeepResearch.src.utils.testcontainers_deployer.TestcontainersDeployer
        handler: python
        options:
          docstring_style: google
          show_category_heading: true

Core deployment infrastructure for MCP servers using testcontainers with integrated code execution.

**Features:**
- **MCP Server Deployment**: Deploy bioinformatics servers (FastQC, SAMtools, Bowtie2) in isolated containers
- **Testcontainers Integration**: Isolated container environments for secure, reproducible execution
- **Code Execution**: AG2-style code execution within deployed containers
- **Health Monitoring**: Built-in health checks and automatic recovery
- **Resource Management**: Configurable CPU, memory, and timeout limits
- **Multi-Server Support**: Deploy multiple servers simultaneously with resource optimization

**Key Methods:**
- `deploy_server()`: Deploy MCP servers with custom configurations
- `execute_code()`: Execute code within deployed server containers
- `execute_code_blocks()`: Execute multiple code blocks with container isolation
- `health_check()`: Perform health monitoring on deployed servers
- `stop_server()`: Gracefully stop and cleanup deployed servers

**Configuration:**
```yaml
# Testcontainers configuration
testcontainers:
  image: "python:3.11-slim"
  working_directory: "/workspace"
  auto_remove: true
  privileged: false
  environment_variables:
    PYTHONPATH: "/workspace"
  volumes:
    /tmp/mcp_data: "/workspace/data"
```

## Usage Examples

### Creating a Custom Tool

```python
from deepresearch.tools import ToolRunner, ToolSpec, ToolCategory
from deepresearch.datatypes import ExecutionResult

class CustomAnalysisTool(ToolRunner):
    """Custom tool for data analysis."""

    def __init__(self):
        super().__init__(ToolSpec(
            name="custom_analysis",
            description="Performs custom data analysis",
            category=ToolCategory.ANALYTICS,
            inputs={
                "data": "dict",
                "analysis_type": "str",
                "parameters": "dict"
            },
            outputs={
                "result": "dict",
                "statistics": "dict"
            }
        ))

    def run(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """Execute the analysis.

        Args:
            parameters: Tool parameters including data, analysis_type, and parameters

        Returns:
            ExecutionResult with analysis results
        """
        try:
            data = parameters["data"]
            analysis_type = parameters["analysis_type"]

            # Perform analysis
            result = self._perform_analysis(data, analysis_type, parameters)

            return ExecutionResult(
                success=True,
                data={
                    "result": result,
                    "statistics": self._calculate_statistics(result)
                }
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )

    def _perform_analysis(self, data: Dict, analysis_type: str, params: Dict) -> Dict:
        """Perform the actual analysis logic."""
        # Implementation here
        return {"analysis": "completed"}

    def _calculate_statistics(self, result: Dict) -> Dict:
        """Calculate statistics for the result."""
        # Implementation here
        return {"stats": "calculated"}
```

### Registering and Using Tools

```python
from deepresearch.tools import ToolRegistry

# Get global registry
registry = ToolRegistry.get_instance()

# Register custom tool
registry.register_tool(
    tool_spec=CustomAnalysisTool().get_spec(),
    tool_runner=CustomAnalysisTool()
)

# Use the tool
result = registry.execute_tool("custom_analysis", {
    "data": {"key": "value"},
    "analysis_type": "statistical",
    "parameters": {"confidence": 0.95}
})

if result.success:
    print(f"Analysis result: {result.data}")
else:
    print(f"Analysis failed: {result.error}")
```

### Tool Categories and Organization

```python
from deepresearch.tools import ToolCategory

# Available categories
categories = [
    ToolCategory.KNOWLEDGE_QUERY,    # Information retrieval
    ToolCategory.SEQUENCE_ANALYSIS,  # Bioinformatics sequence tools
    ToolCategory.STRUCTURE_PREDICTION, # Protein structure tools
    ToolCategory.MOLECULAR_DOCKING,  # Drug-target interaction
    ToolCategory.DE_NOVO_DESIGN,     # Novel molecule design
    ToolCategory.FUNCTION_PREDICTION, # Function annotation
    ToolCategory.RAG,               # Retrieval-augmented generation
    ToolCategory.SEARCH,            # Web and document search
    ToolCategory.ANALYTICS,         # Data analysis and visualization
    ToolCategory.CODE_EXECUTION,    # Code execution environments
]
```
