# Bioinformatics Tools

DeepCritical provides comprehensive bioinformatics tools including 30 MCP (Model Context Protocol) servers that wrap CLI bioinformatics tools in containerized, type-safe, AI-callable interfaces. These servers enable seamless integration of genomics pipelines with AI agents.

## Overview

The bioinformatics tools ecosystem consists of two layers:

1. **MCP Bioinformatics Servers** (30 servers): Containerized CLI tool wrappers for sequence alignment, quality control, variant calling, quantification, and data processing
2. **High-Level Analysis Tools**: Multi-source data fusion, gene ontology analysis, protein structure analysis, and integrative biological reasoning

## MCP Bioinformatics Servers

### What are MCP Servers?

MCP (Model Context Protocol) servers wrap command-line bioinformatics tools in:
- **Type-safe interfaces**: Pydantic validation for all inputs/outputs
- **Docker containers**: Reproducible, isolated execution environments
- **AI-callable tools**: Direct integration with Pydantic AI agents
- **Mock mode**: CI-compatible testing without installing tools

### Server Architecture

All 30 MCP servers follow a consistent pattern:
```python
from DeepResearch.src.tools.bioinformatics.gunzip_server import GunzipServer

# Deploy server with testcontainers
server = GunzipServer(docker_enabled=True)
await server.deploy_with_testcontainers()

# Execute operations
result = await server.decompress(
    input_file="sample.fastq.gz",
    output_file="sample.fastq",
    keep_original=True
)
```

### Available MCP Servers (30 Total)

#### Data Processing & Compression
- **gunzip** - Compress/decompress gzip files (FASTQ.gz, genome archives)
  - Primary operations: decompress, compress, test, list
  - Use case: 99% of genomics data is distributed as .gz
  - Container: python:3.11-slim with gzip v1.10

#### Sequence Alignment
- **bwa** - Burrows-Wheeler Aligner for short reads
- **bowtie2** - Fast aligner for gapped, local, and paired-end alignment
- **hisat2** - Graph-based alignment for RNA-seq
- **star** - Ultrafast RNA-seq aligner
- **minimap2** - Long-read alignment and assembly

#### Quality Control
- **fastqc** - Quality assessment for high-throughput sequence data
- **multiqc** - Aggregate reports from multiple bioinformatics tools
- **qualimap** - Quality control of alignment sequencing data
- **trimgalore** - Adapter and quality trimming
- **fastp** - All-in-one FASTQ preprocessor

#### Variant Calling
- **freebayes** - Bayesian genetic variant detector
- **bcftools** - VCF/BCF manipulation and variant calling
- **gatk** - Genome Analysis Toolkit for variant discovery
- **varscan** - Variant detection in massively parallel sequencing

#### Quantification
- **salmon** - Fast transcript-level quantification
- **kallisto** - Near-optimal RNA-seq quantification
- **featurecounts** - Read assignment to genomic features
- **htseq** - Framework for high-throughput sequencing data

#### Assembly & Annotation
- **stringtie** - Transcript assembly and quantification
- **cufflinks** - Transcriptome assembly from RNA-seq
- **augustus** - Gene prediction in eukaryotes
- **prokka** - Rapid prokaryotic genome annotation

#### Utilities
- **samtools** - SAM/BAM/CRAM manipulation
- **bedtools** - Genome arithmetic operations
- **blast** - Basic Local Alignment Search Tool
- **vcftools** - VCF file manipulation
- **picard** - Java tools for high-throughput sequencing

#### Specialized
- **mafft** - Multiple sequence alignment
- **muscle** - Multiple sequence alignment by log-expectation
- **hmmer** - Protein homology detection via HMMs

### Using MCP Servers

#### Basic Usage Pattern

```python
from DeepResearch.src.tools.bioinformatics.gunzip_server import GunzipServer
from pathlib import Path

async def process_genomics_data():
    # Initialize server
    gunzip = GunzipServer(
        docker_enabled=True,
        mock_mode=False  # Set to True for testing without Docker
    )

    # Deploy container
    await gunzip.deploy_with_testcontainers()

    try:
        # Decompress FASTQ.gz file
        result = await gunzip.decompress(
            input_file="/data/sample.fastq.gz",
            output_file="/data/sample.fastq",
            keep_original=True,  # Keep .gz file
            force=False,  # Don't overwrite existing files
            to_stdout=False  # Write to file, not stdout
        )

        if result["success"]:
            print(f"Decompressed: {result['output_file']}")
            print(f"Original size: {result['compressed_size']}")
            print(f"Decompressed size: {result['decompressed_size']}")
            print(f"Compression ratio: {result['compression_ratio']}")
        else:
            print(f"Error: {result['error']}")

    finally:
        # Cleanup container
        await gunzip.cleanup()
```

#### Mock Mode (CI/Testing)

```python
# Mock mode returns synthetic success responses without requiring Docker
gunzip = GunzipServer(mock_mode=True)

result = await gunzip.decompress(
    input_file="sample.fastq.gz",
    output_file="sample.fastq"
)
# Returns: {"success": True, "mock": True, ...}
```

#### Integration with Pydantic AI Agents

All MCP servers are automatically callable from Pydantic AI agents:

```python
from pydantic_ai import Agent
from DeepResearch.src.tools.mcp_server_tools import MCPServerManager

# Agent with access to all 30 bioinformatics tools
agent = Agent(
    model="anthropic:claude-sonnet-4-0",
    tools=[MCPServerManager().get_all_tools()]
)

# Agent can now call tools directly
result = await agent.run(
    "Decompress sample.fastq.gz and run quality control with FastQC"
)
```

### Detailed Example: GunzipServer

The gunzip server provides comprehensive gzip compression/decompression capabilities essential for genomics workflows.

#### Operations

**1. Decompress (.gz → file)**
```python
result = await gunzip.decompress(
    input_file="sample.fastq.gz",
    output_file="sample.fastq",  # Optional: inferred if not provided
    keep_original=True,  # Keep .gz file after decompression
    force=False,  # Don't overwrite existing output
    to_stdout=False  # Write to file, not stdout
)

# Returns:
{
    "success": True,
    "operation": "decompress",
    "input_file": "sample.fastq.gz",
    "output_file": "sample.fastq",
    "compressed_size": 1234567,
    "decompressed_size": 4567890,
    "compression_ratio": 27.0,
    "duration_seconds": 2.3
}
```

**2. Compress (file → .gz)**
```python
result = await gunzip.compress(
    input_file="sample.fastq",
    output_file="sample.fastq.gz",  # Optional: inferred if not provided
    compression_level=6,  # 1 (fast) to 9 (best compression)
    keep_original=True,  # Keep original file
    force=False
)

# Returns:
{
    "success": True,
    "operation": "compress",
    "input_file": "sample.fastq",
    "output_file": "sample.fastq.gz",
    "original_size": 4567890,
    "compressed_size": 1234567,
    "compression_ratio": 27.0,
    "compression_level": 6,
    "duration_seconds": 3.1
}
```

**3. Test Integrity**
```python
result = await gunzip.test(input_file="sample.fastq.gz")

# Returns:
{
    "success": True,
    "operation": "test",
    "input_file": "sample.fastq.gz",
    "is_valid": True,
    "file_size": 1234567
}
```

**4. List Compression Info**
```python
result = await gunzip.list(input_file="sample.fastq.gz")

# Returns:
{
    "success": True,
    "operation": "list",
    "input_file": "sample.fastq.gz",
    "compressed_size": 1234567,
    "decompressed_size": 4567890,
    "compression_ratio": 27.0,
    "compression_method": "deflate"
}
```

#### Error Handling

All operations return error information without raising exceptions:

```python
result = await gunzip.decompress(input_file="missing.gz")

# Returns:
{
    "success": False,
    "error": "File not found: missing.gz",
    "operation": "decompress",
    "input_file": "missing.gz"
}
```

#### Configuration

```python
from DeepResearch.src.datatypes.bioinformatics_mcp import MCPServerConfig

config = MCPServerConfig(
    name="gunzip",
    description="Compress/decompress gzip files for genomics workflows",
    version="1.10",
    image="python:3.11-slim",  # Includes gzip v1.10
    tag="latest",
    registry="docker.io",
    volumes={"/tmp": "/tmp"},  # Map host /tmp to container /tmp
    environment={},
    docker_enabled=True,
    mock_mode=False
)

gunzip = GunzipServer(config=config)
```

### Best Practices

#### 1. Always Use Testcontainers for Isolation
```python
async with gunzip.deploy_with_testcontainers():
    # Container is automatically cleaned up after this block
    result = await gunzip.decompress(...)
```

#### 2. Enable Mock Mode for CI/Testing
```python
@pytest.mark.optional  # Skip if Docker not available
async def test_gunzip_decompress():
    gunzip = GunzipServer(mock_mode=not docker_available())
    result = await gunzip.decompress(...)
    assert result["success"]
```

#### 3. Validate Inputs with Pydantic
All MCP servers use Pydantic validation:
```python
# This will raise ValidationError before execution
result = await gunzip.compress(
    input_file="",  # Invalid: empty string
    compression_level=10  # Invalid: must be 1-9
)
```

#### 4. Handle Large Files Efficiently
```python
# Stream to stdout for large files
result = await gunzip.decompress(
    input_file="large.fastq.gz",
    to_stdout=True,  # Stream instead of writing file
    keep_original=True
)
```

#### 5. Check Operation Success
```python
result = await gunzip.decompress(input_file="sample.gz")

if not result["success"]:
    logger.error(f"Decompression failed: {result['error']}")
    return

# Proceed with success case
process_decompressed_file(result["output_file"])
```

### Testing MCP Servers

All MCP servers inherit comprehensive test suites:

```python
import pytest
from DeepResearch.src.tools.bioinformatics.gunzip_server import GunzipServer
from tests.test_bioinformatics_tools.base.test_base_tool import BaseBioinformaticsToolTest

class TestGunzipServer(BaseBioinformaticsToolTest):
    """Test suite for gunzip server.

    Inherits 5 standard tests:
    - test_tool_initialization
    - test_server_config_valid
    - test_mock_mode_enabled
    - test_docker_disabled_mode
    - test_deploy_with_testcontainers (optional)
    """

    @pytest.fixture
    def tool_class(self):
        return GunzipServer

    @pytest.mark.optional
    async def test_decompress_success(self, tool_instance):
        """Test successful decompression."""
        result = await tool_instance.decompress(
            input_file="sample.fastq.gz",
            keep_original=True
        )
        assert result["success"]
        assert result["operation"] == "decompress"
        assert "decompressed_size" in result
```

### Configuration Reference

#### Environment Variables
```bash
# Docker configuration
DOCKER_ENABLED=true
DOCKER_TIMEOUT=300

# Resource limits
MCP_SERVER_MEMORY_LIMIT="2g"
MCP_SERVER_CPU_LIMIT="2.0"

# Volumes
MCP_SERVER_DATA_DIR="/tmp/mcp_data"
```

#### YAML Configuration
```yaml
# configs/bioinformatics/mcp_servers.yaml
mcp_servers:
  gunzip:
    enabled: true
    docker_enabled: true
    image: "python:3.11-slim"
    tag: "latest"
    volumes:
      /tmp: /tmp
    timeout: 300

  fastqc:
    enabled: true
    docker_enabled: true
    image: "quay.io/biocontainers/fastqc"
    tag: "0.12.1"

  # ... 28 more servers
```

---

## High-Level Analysis Tools

The bioinformatics tools integrate multiple biological databases and provide sophisticated analysis capabilities for gene function prediction, protein analysis, and biological data integration.

## Data Sources

### Gene Ontology (GO)
```python
from deepresearch.tools.bioinformatics import GOAnnotationTool

# Initialize GO annotation tool
go_tool = GOAnnotationTool()

# Query GO annotations
annotations = await go_tool.query_annotations(
    gene_id="TP53",
    evidence_codes=["IDA", "EXP", "TAS"],
    organism="human",
    max_results=100
)

# Process annotations
for annotation in annotations:
    print(f"GO Term: {annotation.go_id}")
    print(f"Term Name: {annotation.term_name}")
    print(f"Evidence: {annotation.evidence_code}")
    print(f"Reference: {annotation.reference}")
```

### PubMed Integration
```python
from deepresearch.tools.bioinformatics import PubMedTool

# Initialize PubMed tool
pubmed_tool = PubMedTool()

# Search literature
papers = await pubmed_tool.search_and_fetch(
    query="TP53 AND cancer AND apoptosis",
    max_results=50,
    include_abstracts=True,
    year_min=2020
)

# Analyze papers
for paper in papers:
    print(f"PMID: {paper.pmid}")
    print(f"Title: {paper.title}")
    print(f"Abstract: {paper.abstract[:200]}...")
```

### UniProt Integration
```python
from deepresearch.tools.bioinformatics import UniProtTool

# Initialize UniProt tool
uniprot_tool = UniProtTool()

# Get protein information
protein_info = await uniprot_tool.get_protein_info(
    accession="P04637",
    include_sequences=True,
    include_features=True
)

print(f"Protein Name: {protein_info.name}")
print(f"Function: {protein_info.function}")
print(f"Sequence Length: {len(protein_info.sequence)}")
```

## Analysis Tools

### GO Enrichment Analysis
```python
from deepresearch.tools.bioinformatics import GOEnrichmentTool

# Initialize enrichment tool
enrichment_tool = GOEnrichmentTool()

# Perform enrichment analysis
enrichment_results = await enrichment_tool.analyze_enrichment(
    gene_list=["TP53", "BRCA1", "EGFR", "MYC"],
    background_genes=["TP53", "BRCA1", "EGFR", "MYC", "RB1", "APC"],
    organism="human",
    p_value_threshold=0.05
)

# Display results
for result in enrichment_results:
    print(f"GO Term: {result.go_id}")
    print(f"P-value: {result.p_value}")
    print(f"Enrichment Ratio: {result.enrichment_ratio}")
```

### Protein-Protein Interaction Analysis
```python
from deepresearch.tools.bioinformatics import InteractionTool

# Initialize interaction tool
interaction_tool = InteractionTool()

# Get protein interactions
interactions = await interaction_tool.get_interactions(
    protein_id="P04637",
    interaction_types=["physical", "genetic"],
    confidence_threshold=0.7,
    max_interactions=50
)

# Analyze interaction network
for interaction in interactions:
    print(f"Interactor: {interaction.interactor}")
    print(f"Interaction Type: {interaction.interaction_type}")
    print(f"Confidence: {interaction.confidence}")
```

### Pathway Analysis
```python
from deepresearch.tools.bioinformatics import PathwayTool

# Initialize pathway tool
pathway_tool = PathwayTool()

# Analyze pathways
pathway_results = await pathway_tool.analyze_pathways(
    gene_list=["TP53", "BRCA1", "EGFR"],
    pathway_databases=["KEGG", "Reactome", "WikiPathways"],
    organism="human"
)

# Display pathway information
for pathway in pathway_results:
    print(f"Pathway: {pathway.name}")
    print(f"Database: {pathway.database}")
    print(f"Genes in pathway: {len(pathway.genes)}")
```

## Structure Analysis Tools

### Structure Prediction
```python
from deepresearch.tools.bioinformatics import StructurePredictionTool

# Initialize structure prediction tool
structure_tool = StructurePredictionTool()

# Predict protein structure
structure_result = await structure_tool.predict_structure(
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    method="alphafold2",
    include_confidence=True,
    use_templates=True
)

print(f"pLDDT Score: {structure_result.plddt_score}")
print(f"Structure Quality: {structure_result.quality}")
```

### Structure Comparison
```python
from deepresearch.tools.bioinformatics import StructureComparisonTool

# Initialize comparison tool
comparison_tool = StructureComparisonTool()

# Compare structures
comparison_result = await comparison_tool.compare_structures(
    structure1_pdb="1tup.pdb",
    structure2_pdb="predicted_structure.pdb",
    comparison_method="tm_align",
    include_visualization=True
)

print(f"RMSD: {comparison_result.rmsd}")
print(f"TM Score: {comparison_result.tm_score}")
print(f"Alignment Length: {comparison_result.alignment_length}")
```

## Integration Tools

### Multi-Source Data Fusion
```python
from deepresearch.tools.bioinformatics import DataFusionTool

# Initialize fusion tool
fusion_tool = DataFusionTool()

# Fuse multiple data sources
fused_data = await fusion_tool.fuse_data_sources(
    go_annotations=go_annotations,
    literature=papers,
    interactions=interactions,
    expression_data=expression_data,
    quality_threshold=0.8,
    max_entities=1000
)

print(f"Fused entities: {len(fused_data.entities)}")
print(f"Confidence scores: {fused_data.confidence_scores}")
```

### Evidence Integration
```python
from deepresearch.tools.bioinformatics import EvidenceIntegrationTool

# Initialize evidence integration tool
evidence_tool = EvidenceIntegrationTool()

# Integrate evidence from multiple sources
integrated_evidence = await evidence_tool.integrate_evidence(
    go_evidence=go_evidence,
    literature_evidence=lit_evidence,
    experimental_evidence=exp_evidence,
    computational_evidence=comp_evidence,
    evidence_weights={
        "IDA": 1.0,
        "EXP": 0.9,
        "TAS": 0.8,
        "IMP": 0.7
    }
)

print(f"Integrated confidence: {integrated_evidence.confidence}")
print(f"Evidence summary: {integrated_evidence.evidence_summary}")
```

## Advanced Analysis

### Gene Set Enrichment Analysis (GSEA)
```python
from deepresearch.tools.bioinformatics import GSEATool

# Initialize GSEA tool
gsea_tool = GSEATool()

# Perform GSEA
gsea_results = await gsea_tool.perform_gsea(
    gene_expression_data=expression_matrix,
    gene_sets=["hallmark_pathways", "go_biological_process"],
    permutations=1000,
    p_value_threshold=0.05
)

# Analyze results
for result in gsea_results:
    print(f"Gene Set: {result.gene_set_name}")
    print(f"ES Score: {result.enrichment_score}")
    print(f"P-value: {result.p_value}")
    print(f"FDR: {result.fdr}")
```

### Network Analysis
```python
from deepresearch.tools.bioinformatics import NetworkAnalysisTool

# Initialize network tool
network_tool = NetworkAnalysisTool()

# Analyze interaction network
network_analysis = await network_tool.analyze_network(
    interactions=interaction_data,
    analysis_types=["centrality", "clustering", "community_detection"],
    include_visualization=True
)

print(f"Network nodes: {network_analysis.node_count}")
print(f"Network edges: {network_analysis.edge_count}")
print(f"Clustering coefficient: {network_analysis.clustering_coefficient}")
```

## Configuration

### Tool Configuration
```yaml
# configs/bioinformatics/tools.yaml
bioinformatics_tools:
  go_annotation:
    api_base_url: "https://api.geneontology.org"
    cache_enabled: true
    cache_ttl: 3600
    max_requests_per_minute: 60

  pubmed:
    api_base_url: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    max_results: 100
    include_abstracts: true
    request_delay: 0.5

  uniprot:
    api_base_url: "https://rest.uniprot.org"
    include_sequences: true
    include_features: true

  structure_prediction:
    alphafold:
      max_model_len: 2000
      use_gpu: true
      recycle_iterations: 3

    esmfold:
      model_size: "650M"
      use_templates: true
```

### Database Configuration
```yaml
# configs/bioinformatics/data_sources.yaml
data_sources:
  go:
    enabled: true
    evidence_codes: ["IDA", "EXP", "TAS", "IMP"]
    year_min: 2020
    quality_threshold: 0.85

  pubmed:
    enabled: true
    max_results: 100
    include_full_text: false
    year_min: 2020

  string_db:
    enabled: true
    confidence_threshold: 0.7
    max_interactions: 1000

  kegg:
    enabled: true
    organism_codes: ["hsa", "mmu", "sce"]
```

## Usage Examples

### Gene Function Analysis
```python
# Comprehensive gene function analysis
async def analyze_gene_function(gene_id: str):
    # Get GO annotations
    go_annotations = await go_tool.query_annotations(gene_id)

    # Get literature
    literature = await pubmed_tool.search_and_fetch(f"{gene_id} function")

    # Get interactions
    interactions = await interaction_tool.get_interactions(gene_id)

    # Fuse and analyze
    fused_result = await fusion_tool.fuse_data_sources(
        go_annotations=go_annotations,
        literature=literature,
        interactions=interactions
    )

    return fused_result
```

### Protein Structure-Function Analysis
```python
# Analyze protein structure and function
async def analyze_protein_structure_function(protein_id: str):
    # Get protein information
    protein_info = await uniprot_tool.get_protein_info(protein_id)

    # Predict structure if not available
    if not protein_info.pdb_id:
        structure = await structure_tool.predict_structure(protein_info.sequence)
    else:
        structure = await pdb_tool.get_structure(protein_info.pdb_id)

    # Analyze functional sites
    functional_sites = await function_tool.predict_functional_sites(structure)

    # Integrate findings
    integrated_analysis = await evidence_tool.integrate_evidence(
        sequence_evidence=protein_info,
        structure_evidence=structure,
        functional_evidence=functional_sites
    )

    return integrated_analysis
```

## Best Practices

1. **Data Quality**: Always validate data quality from external sources
2. **Evidence Integration**: Use multiple evidence types for robust conclusions
3. **Cross-Validation**: Validate findings across different data sources
4. **Performance Optimization**: Use caching and batch processing for large datasets
5. **Error Handling**: Implement robust error handling for API failures

## Troubleshooting

### Common Issues

**API Rate Limits:**
```python
# Configure request delays
go_tool.configure_request_delay(1.0)  # 1 second between requests
pubmed_tool.configure_request_delay(0.5)  # 0.5 seconds between requests
```

**Data Quality Issues:**
```python
# Enable quality filtering
fusion_tool.enable_quality_filtering(
    min_confidence=0.8,
    require_multiple_sources=True,
    validate_temporal_consistency=True
)
```

**Large Dataset Handling:**
```python
# Use batch processing
results = await batch_tool.process_batch(
    data_list=large_dataset,
    batch_size=100,
    max_workers=4
)
```

For more detailed information, see the [Tool Development Guide](../../development/tool-development.md) and [Data Types API Reference](../../api/datatypes.md).
