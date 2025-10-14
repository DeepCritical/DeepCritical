# Bioinformatics Tools

DeepCritical provides comprehensive bioinformatics tools for multi-source data fusion, gene ontology analysis, protein structure analysis, and integrative biological reasoning.

## Overview

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
