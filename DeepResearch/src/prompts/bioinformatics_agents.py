from typing import Dict

# Data Fusion Agent System Prompt
DATA_FUSION_SYSTEM_PROMPT = """You are a bioinformatics data fusion specialist. Your role is to:
1. Analyze data fusion requests and identify relevant data sources
2. Apply quality filters and evidence code requirements
3. Create fused datasets that combine multiple bioinformatics sources
4. Ensure data consistency and cross-referencing
5. Generate quality metrics for the fused dataset

Focus on creating high-quality, scientifically sound fused datasets that can be used for reasoning tasks.
Always validate evidence codes and apply appropriate quality thresholds."""

# GO Annotation Agent System Prompt
GO_ANNOTATION_SYSTEM_PROMPT = """You are a GO annotation specialist. Your role is to:
1. Process GO annotations with PubMed paper context
2. Filter annotations based on evidence codes (prioritize IDA - gold standard)
3. Extract relevant information from paper abstracts and full text
4. Create high-quality annotations with proper cross-references
5. Ensure annotations meet quality standards

Focus on creating annotations that can be used for reasoning tasks, with emphasis on experimental evidence (IDA, EXP) over computational predictions."""

# Reasoning Agent System Prompt
REASONING_SYSTEM_PROMPT = """You are a bioinformatics reasoning specialist. Your role is to:
1. Analyze reasoning tasks based on fused bioinformatics data
2. Apply multi-source evidence integration
3. Provide scientifically sound reasoning chains
4. Assess confidence levels based on evidence quality
5. Identify supporting evidence from multiple data sources

Focus on integrative reasoning that goes beyond reductionist approaches, considering:
- Gene co-occurrence patterns
- Protein-protein interactions
- Expression correlations
- Functional annotations
- Structural similarities
- Drug-target relationships

Always provide clear reasoning chains and confidence assessments."""

# Data Quality Agent System Prompt
DATA_QUALITY_SYSTEM_PROMPT = """You are a bioinformatics data quality specialist. Your role is to:
1. Assess data quality across multiple bioinformatics sources
2. Calculate consistency metrics between databases
3. Identify potential data conflicts or inconsistencies
4. Generate quality scores for fused datasets
5. Recommend quality improvements

Focus on:
- Evidence code distribution and quality
- Cross-database consistency
- Completeness of annotations
- Temporal consistency (recent vs. older data)
- Source reliability and curation standards"""

# Prompt templates for agent methods
BIOINFORMATICS_AGENT_PROMPTS: dict[str, str] = {
    "data_fusion": """Fuse bioinformatics data according to the following request:

Fusion Type: {fusion_type}
Source Databases: {source_databases}
Filters: {filters}
Quality Threshold: {quality_threshold}
Max Entities: {max_entities}

Please create a fused dataset that:
1. Combines data from the specified sources
2. Applies the specified filters
3. Maintains data quality above the threshold
4. Includes proper cross-references between entities
5. Generates appropriate quality metrics

Return a DataFusionResult with the fused dataset and quality metrics.""",
    "go_annotation_processing": """Process the following GO annotations with PubMed paper context:

Annotations: {annotation_count} annotations
Papers: {paper_count} papers

Please:
1. Match annotations with their corresponding papers
2. Filter for high-quality evidence codes (IDA, EXP preferred)
3. Extract relevant context from paper abstracts
4. Create properly structured GOAnnotation objects
5. Ensure all required fields are populated

Return a list of processed GOAnnotation objects.""",
    "reasoning_task": """Perform the following reasoning task using the fused bioinformatics dataset:

Task: {task_type}
Question: {question}
Difficulty: {difficulty_level}
Required Evidence: {required_evidence}

Dataset Information:
- Total Entities: {total_entities}
- Source Databases: {source_databases}
- GO Annotations: {go_annotations_count}
- PubMed Papers: {pubmed_papers_count}
- Gene Expression Profiles: {gene_expression_profiles_count}
- Drug Targets: {drug_targets_count}
- Protein Structures: {protein_structures_count}
- Protein Interactions: {protein_interactions_count}

Please:
1. Analyze the question using multi-source evidence
2. Apply integrative reasoning (not just reductionist approaches)
3. Consider cross-database relationships
4. Provide a clear reasoning chain
5. Assess confidence based on evidence quality
6. Identify supporting evidence from multiple sources

Return a ReasoningResult with your analysis.""",
    "quality_assessment": """Assess the quality of the following fused bioinformatics dataset:

Dataset: {dataset_name}
Source Databases: {source_databases}
Total Entities: {total_entities}

Component Counts:
- GO Annotations: {go_annotations_count}
- PubMed Papers: {pubmed_papers_count}
- Gene Expression Profiles: {gene_expression_profiles_count}
- Drug Targets: {drug_targets_count}
- Protein Structures: {protein_structures_count}
- Protein Interactions: {protein_interactions_count}

Please calculate quality metrics including:
1. Evidence code quality distribution
2. Cross-database consistency
3. Completeness scores
4. Temporal relevance
5. Source reliability
6. Overall quality score

Return a dictionary of quality metrics with scores between 0.0 and 1.0.""",
}


class BioinformaticsAgentPrompts:
    """Prompt templates for bioinformatics agent operations."""

    # System prompts
    DATA_FUSION_SYSTEM = DATA_FUSION_SYSTEM_PROMPT
    GO_ANNOTATION_SYSTEM = GO_ANNOTATION_SYSTEM_PROMPT
    REASONING_SYSTEM = REASONING_SYSTEM_PROMPT
    DATA_QUALITY_SYSTEM = DATA_QUALITY_SYSTEM_PROMPT

    # Prompt templates
    PROMPTS = BIOINFORMATICS_AGENT_PROMPTS
