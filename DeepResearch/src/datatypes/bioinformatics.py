"""
Bioinformatics data types for DeepCritical research workflows.

This module defines Pydantic models for various bioinformatics data sources
including GO annotations, PubMed papers, GEO datasets, and drug databases.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EvidenceCode(str, Enum):
    """Gene Ontology evidence codes."""

    IDA = "IDA"  # Inferred from Direct Assay (gold standard)
    EXP = "EXP"  # Inferred from Experiment
    IPI = "IPI"  # Inferred from Physical Interaction
    IMP = "IMP"  # Inferred from Mutant Phenotype
    IGI = "IGI"  # Inferred from Genetic Interaction
    IEP = "IEP"  # Inferred from Expression Pattern
    ISS = "ISS"  # Inferred from Sequence or Structural Similarity
    ISO = "ISO"  # Inferred from Sequence Orthology
    ISA = "ISA"  # Inferred from Sequence Alignment
    ISM = "ISM"  # Inferred from Sequence Model
    IGC = "IGC"  # Inferred from Genomic Context
    IBA = "IBA"  # Inferred from Biological aspect of Ancestor
    IBD = "IBD"  # Inferred from Biological aspect of Descendant
    IKR = "IKR"  # Inferred from Key Residues
    IRD = "IRD"  # Inferred from Rapid Divergence
    RCA = "RCA"  # Reviewed Computational Analysis
    TAS = "TAS"  # Traceable Author Statement
    NAS = "NAS"  # Non-traceable Author Statement
    IC = "IC"  # Inferred by Curator
    ND = "ND"  # No biological Data available
    IEA = "IEA"  # Inferred from Electronic Annotation


class GOTerm(BaseModel):
    """Gene Ontology term representation."""

    id: str = Field(..., description="GO term ID (e.g., GO:0006977)")
    name: str = Field(..., description="GO term name")
    namespace: str = Field(
        ...,
        description="GO namespace (biological_process, molecular_function, cellular_component)",
    )
    definition: str | None = Field(None, description="GO term definition")
    synonyms: list[str] = Field(default_factory=list, description="Alternative names")
    is_obsolete: bool = Field(False, description="Whether the term is obsolete")

    model_config = ConfigDict(json_schema_extra={})


class GOAnnotation(BaseModel):
    """Gene Ontology annotation with paper context."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    full_text: str | None = Field(None, description="Full text for open access papers")
    gene_id: str = Field(..., description="Gene identifier (e.g., P04637)")
    gene_symbol: str = Field(..., description="Gene symbol (e.g., TP53)")
    go_term: GOTerm = Field(..., description="Associated GO term")
    evidence_code: EvidenceCode = Field(..., description="Evidence code")
    annotation_note: str | None = Field(None, description="Curator annotation note")
    curator: str | None = Field(None, description="Curator identifier")
    annotation_date: datetime | None = Field(None, description="Date of annotation")
    confidence_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Confidence score"
    )

    model_config = ConfigDict(json_schema_extra={})


class PubMedPaper(BaseModel):
    """PubMed paper representation."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    authors: list[str] = Field(default_factory=list, description="Author names")
    journal: str | None = Field(None, description="Journal name")
    publication_date: datetime | None = Field(None, description="Publication date")
    doi: str | None = Field(None, description="Digital Object Identifier")
    pmc_id: str | None = Field(None, description="PMC ID for open access")
    mesh_terms: list[str] = Field(default_factory=list, description="MeSH terms")
    keywords: list[str] = Field(default_factory=list, description="Keywords")
    is_open_access: bool = Field(False, description="Whether paper is open access")
    full_text_url: HttpUrl | None = Field(None, description="URL to full text")

    model_config = ConfigDict(json_schema_extra={})


class GEOPlatform(BaseModel):
    """GEO platform information."""

    platform_id: str = Field(..., description="GEO platform ID (e.g., GPL570)")
    title: str = Field(..., description="Platform title")
    organism: str = Field(..., description="Organism")
    technology: str = Field(..., description="Technology type")
    manufacturer: str | None = Field(None, description="Manufacturer")
    description: str | None = Field(None, description="Platform description")


class GEOSample(BaseModel):
    """GEO sample information."""

    sample_id: str = Field(..., description="GEO sample ID (e.g., GSM123456)")
    title: str = Field(..., description="Sample title")
    organism: str = Field(..., description="Organism")
    source_name: str | None = Field(None, description="Source name")
    characteristics: dict[str, str] = Field(
        default_factory=dict, description="Sample characteristics"
    )
    platform_id: str = Field(..., description="Associated platform ID")
    series_id: str = Field(..., description="Associated series ID")


class GEOSeries(BaseModel):
    """GEO series (study) information."""

    series_id: str = Field(..., description="GEO series ID (e.g., GSE12345)")
    title: str = Field(..., description="Series title")
    summary: str = Field(..., description="Series summary")
    overall_design: str | None = Field(None, description="Overall design")
    organism: str = Field(..., description="Organism")
    platform_ids: list[str] = Field(default_factory=list, description="Platform IDs")
    sample_ids: list[str] = Field(default_factory=list, description="Sample IDs")
    submission_date: datetime | None = Field(None, description="Submission date")
    last_update_date: datetime | None = Field(None, description="Last update date")
    contact_name: str | None = Field(None, description="Contact name")
    contact_email: str | None = Field(None, description="Contact email")
    pubmed_ids: list[str] = Field(
        default_factory=list, description="Associated PubMed IDs"
    )


class GeneExpressionProfile(BaseModel):
    """Gene expression profile from GEO."""

    gene_id: str = Field(..., description="Gene identifier")
    gene_symbol: str = Field(..., description="Gene symbol")
    expression_values: dict[str, float] = Field(
        ..., description="Expression values by sample ID"
    )
    log2_fold_change: float | None = Field(None, description="Log2 fold change")
    p_value: float | None = Field(None, description="P-value")
    adjusted_p_value: float | None = Field(None, description="Adjusted p-value (FDR)")
    series_id: str = Field(..., description="Associated GEO series ID")


class DrugTarget(BaseModel):
    """Drug target information."""

    drug_id: str = Field(..., description="Drug identifier")
    drug_name: str = Field(..., description="Drug name")
    target_id: str = Field(..., description="Target identifier")
    target_name: str = Field(..., description="Target name")
    target_type: str = Field(..., description="Target type (protein, gene, etc.)")
    action: str | None = Field(
        None, description="Drug action (inhibitor, activator, etc.)"
    )
    mechanism: str | None = Field(None, description="Mechanism of action")
    indication: str | None = Field(None, description="Therapeutic indication")
    clinical_phase: str | None = Field(None, description="Clinical development phase")


class PerturbationProfile(BaseModel):
    """Pellular perturbation profile from CMAP."""

    compound_id: str = Field(..., description="Compound identifier")
    compound_name: str = Field(..., description="Compound name")
    cell_line: str = Field(..., description="Cell line")
    concentration: float | None = Field(None, description="Concentration")
    time_point: str | None = Field(None, description="Time point")
    gene_expression_changes: dict[str, float] = Field(
        ..., description="Gene expression changes"
    )
    connectivity_score: float | None = Field(None, description="Connectivity score")
    p_value: float | None = Field(None, description="P-value")


class ProteinStructure(BaseModel):
    """Protein structure information from PDB."""

    pdb_id: str = Field(..., description="PDB identifier")
    title: str = Field(..., description="Structure title")
    organism: str = Field(..., description="Organism")
    resolution: float | None = Field(None, description="Resolution in Angstroms")
    method: str | None = Field(None, description="Experimental method")
    chains: list[str] = Field(default_factory=list, description="Chain identifiers")
    sequence: str | None = Field(None, description="Protein sequence")
    secondary_structure: str | None = Field(None, description="Secondary structure")
    binding_sites: list[dict[str, Any]] = Field(
        default_factory=list, description="Binding sites"
    )
    publication_date: datetime | None = Field(None, description="Publication date")


class ProteinInteraction(BaseModel):
    """Protein-protein interaction from IntAct."""

    interaction_id: str = Field(..., description="Interaction identifier")
    interactor_a: str = Field(..., description="First interactor ID")
    interactor_b: str = Field(..., description="Second interactor ID")
    interaction_type: str = Field(..., description="Type of interaction")
    detection_method: str | None = Field(None, description="Detection method")
    confidence_score: float | None = Field(None, description="Confidence score")
    pubmed_ids: list[str] = Field(
        default_factory=list, description="Supporting PubMed IDs"
    )
    species: str | None = Field(None, description="Species")


class FusedDataset(BaseModel):
    """Fused dataset combining multiple bioinformatics sources."""

    dataset_id: str = Field(..., description="Unique dataset identifier")
    name: str = Field(..., description="Dataset name")
    description: str = Field(..., description="Dataset description")
    source_databases: list[str] = Field(..., description="Source databases")
    creation_date: datetime = Field(
        default_factory=datetime.now, description="Creation date"
    )

    # Fused data components
    go_annotations: list[GOAnnotation] = Field(
        default_factory=list, description="GO annotations"
    )
    pubmed_papers: list[PubMedPaper] = Field(
        default_factory=list, description="PubMed papers"
    )
    geo_series: list[GEOSeries] = Field(default_factory=list, description="GEO series")
    gene_expression_profiles: list[GeneExpressionProfile] = Field(
        default_factory=list, description="Gene expression profiles"
    )
    drug_targets: list[DrugTarget] = Field(
        default_factory=list, description="Drug targets"
    )
    perturbation_profiles: list[PerturbationProfile] = Field(
        default_factory=list, description="Perturbation profiles"
    )
    protein_structures: list[ProteinStructure] = Field(
        default_factory=list, description="Protein structures"
    )
    protein_interactions: list[ProteinInteraction] = Field(
        default_factory=list, description="Protein interactions"
    )

    # Metadata
    total_entities: int = Field(0, description="Total number of entities")
    cross_references: dict[str, list[str]] = Field(
        default_factory=dict, description="Cross-references between entities"
    )
    quality_metrics: dict[str, float] = Field(
        default_factory=dict, description="Quality metrics"
    )

    @field_validator("total_entities", mode="before")
    @classmethod
    def calculate_total_entities(cls, v, info):
        """Calculate total entities from all components."""
        total = 0
        for field_name in [
            "go_annotations",
            "pubmed_papers",
            "geo_series",
            "gene_expression_profiles",
            "drug_targets",
            "perturbation_profiles",
            "protein_structures",
            "protein_interactions",
        ]:
            if info.data and field_name in info.data:
                total += len(info.data[field_name])
        return total

    model_config = ConfigDict(json_schema_extra={})


class ReasoningTask(BaseModel):
    """Reasoning task based on fused bioinformatics data."""

    task_id: str = Field(..., description="Task identifier")
    task_type: str = Field(..., description="Type of reasoning task")
    question: str = Field(..., description="Reasoning question")
    context: dict[str, Any] = Field(default_factory=dict, description="Task context")
    expected_answer: str | None = Field(None, description="Expected answer")
    difficulty_level: str = Field("medium", description="Difficulty level")
    required_evidence: list[EvidenceCode] = Field(
        default_factory=list, description="Required evidence codes"
    )
    supporting_data: list[str] = Field(
        default_factory=list, description="Supporting data identifiers"
    )

    model_config = ConfigDict(json_schema_extra={})


class DataFusionRequest(BaseModel):
    """Request for data fusion operation."""

    request_id: str = Field(..., description="Request identifier")
    fusion_type: str = Field(
        ..., description="Type of fusion (GO+PubMed, GEO+CMAP, etc.)"
    )
    source_databases: list[str] = Field(..., description="Source databases to fuse")
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Filtering criteria"
    )
    output_format: str = Field("fused_dataset", description="Output format")
    quality_threshold: float = Field(
        0.8, ge=0.0, le=1.0, description="Quality threshold"
    )
    max_entities: int | None = Field(None, description="Maximum number of entities")

    @classmethod
    def from_config(cls, config: dict[str, Any], **kwargs) -> DataFusionRequest:
        """Create DataFusionRequest from configuration."""
        bioinformatics_config = config.get("bioinformatics", {})
        fusion_config = bioinformatics_config.get("fusion", {})

        return cls(
            quality_threshold=fusion_config.get("default_quality_threshold", 0.8),
            max_entities=fusion_config.get("default_max_entities", 1000),
            **kwargs,
        )

    model_config = ConfigDict(json_schema_extra={})


class BioinformaticsAgentDeps(BaseModel):
    """Dependencies for bioinformatics agents."""

    config: dict[str, Any] = Field(default_factory=dict)
    data_sources: list[str] = Field(default_factory=list)
    quality_threshold: float = Field(0.8, ge=0.0, le=1.0)

    @classmethod
    def from_config(cls, config: dict[str, Any], **kwargs) -> BioinformaticsAgentDeps:
        """Create dependencies from configuration."""
        bioinformatics_config = config.get("bioinformatics", {})
        quality_config = bioinformatics_config.get("quality", {})

        return cls(
            config=config,
            quality_threshold=quality_config.get("default_threshold", 0.8),
            **kwargs,
        )


class DataFusionResult(BaseModel):
    """Result of data fusion operation."""

    success: bool = Field(..., description="Whether fusion was successful")
    fused_dataset: FusedDataset | None = Field(None, description="Fused dataset")
    quality_metrics: dict[str, float] = Field(
        default_factory=dict, description="Quality metrics"
    )
    errors: list[str] = Field(default_factory=list, description="Error messages")
    processing_time: float = Field(0.0, description="Processing time in seconds")


class ReasoningResult(BaseModel):
    """Result of reasoning task."""

    success: bool = Field(..., description="Whether reasoning was successful")
    answer: str = Field(..., description="Reasoning answer")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    supporting_evidence: list[str] = Field(
        default_factory=list, description="Supporting evidence"
    )
    reasoning_chain: list[str] = Field(
        default_factory=list, description="Reasoning steps"
    )
