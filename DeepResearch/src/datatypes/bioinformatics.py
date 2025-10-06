"""
Bioinformatics data types for DeepCritical research workflows.

This module defines Pydantic models for various bioinformatics data sources
including GO annotations, PubMed papers, GEO datasets, and drug databases.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator


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
    definition: Optional[str] = Field(None, description="GO term definition")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names")
    is_obsolete: bool = Field(False, description="Whether the term is obsolete")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "GO:0006977",
                "name": "DNA damage response",
                "namespace": "biological_process",
                "definition": "A cellular process that results in the detection and repair of DNA damage.",
            }
        }


class GOAnnotation(BaseModel):
    """Gene Ontology annotation with paper context."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    full_text: Optional[str] = Field(
        None, description="Full text for open access papers"
    )
    gene_id: str = Field(..., description="Gene identifier (e.g., P04637)")
    gene_symbol: str = Field(..., description="Gene symbol (e.g., TP53)")
    go_term: GOTerm = Field(..., description="Associated GO term")
    evidence_code: EvidenceCode = Field(..., description="Evidence code")
    annotation_note: Optional[str] = Field(None, description="Curator annotation note")
    curator: Optional[str] = Field(None, description="Curator identifier")
    annotation_date: Optional[datetime] = Field(None, description="Date of annotation")
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "pmid": "12345678",
                "title": "p53 mediates the DNA damage response in mammalian cells",
                "abstract": "DNA damage induces p53 stabilization, leading to cell cycle arrest and apoptosis.",
                "gene_id": "P04637",
                "gene_symbol": "TP53",
                "go_term": {
                    "id": "GO:0006977",
                    "name": "DNA damage response",
                    "namespace": "biological_process",
                },
                "evidence_code": "IDA",
                "annotation_note": "Curated based on experimental results in Figure 3.",
            }
        }


class PubMedPaper(BaseModel):
    """PubMed paper representation."""

    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
    authors: List[str] = Field(default_factory=list, description="Author names")
    journal: Optional[str] = Field(None, description="Journal name")
    publication_date: Optional[datetime] = Field(None, description="Publication date")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    pmc_id: Optional[str] = Field(None, description="PMC ID for open access")
    mesh_terms: List[str] = Field(default_factory=list, description="MeSH terms")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    is_open_access: bool = Field(False, description="Whether paper is open access")
    full_text_url: Optional[HttpUrl] = Field(None, description="URL to full text")

    class Config:
        json_schema_extra = {
            "example": {
                "pmid": "12345678",
                "title": "p53 mediates the DNA damage response in mammalian cells",
                "abstract": "DNA damage induces p53 stabilization, leading to cell cycle arrest and apoptosis.",
                "authors": ["Smith, J.", "Doe, A."],
                "journal": "Nature",
                "doi": "10.1038/nature12345",
            }
        }


class GEOPlatform(BaseModel):
    """GEO platform information."""

    platform_id: str = Field(..., description="GEO platform ID (e.g., GPL570)")
    title: str = Field(..., description="Platform title")
    organism: str = Field(..., description="Organism")
    technology: str = Field(..., description="Technology type")
    manufacturer: Optional[str] = Field(None, description="Manufacturer")
    description: Optional[str] = Field(None, description="Platform description")


class GEOSample(BaseModel):
    """GEO sample information."""

    sample_id: str = Field(..., description="GEO sample ID (e.g., GSM123456)")
    title: str = Field(..., description="Sample title")
    organism: str = Field(..., description="Organism")
    source_name: Optional[str] = Field(None, description="Source name")
    characteristics: Dict[str, str] = Field(
        default_factory=dict, description="Sample characteristics"
    )
    platform_id: str = Field(..., description="Associated platform ID")
    series_id: str = Field(..., description="Associated series ID")


class GEOSeries(BaseModel):
    """GEO series (study) information."""

    series_id: str = Field(..., description="GEO series ID (e.g., GSE12345)")
    title: str = Field(..., description="Series title")
    summary: str = Field(..., description="Series summary")
    overall_design: Optional[str] = Field(None, description="Overall design")
    organism: str = Field(..., description="Organism")
    platform_ids: List[str] = Field(default_factory=list, description="Platform IDs")
    sample_ids: List[str] = Field(default_factory=list, description="Sample IDs")
    submission_date: Optional[datetime] = Field(None, description="Submission date")
    last_update_date: Optional[datetime] = Field(None, description="Last update date")
    contact_name: Optional[str] = Field(None, description="Contact name")
    contact_email: Optional[str] = Field(None, description="Contact email")
    pubmed_ids: List[str] = Field(
        default_factory=list, description="Associated PubMed IDs"
    )


class GeneExpressionProfile(BaseModel):
    """Gene expression profile from GEO."""

    gene_id: str = Field(..., description="Gene identifier")
    gene_symbol: str = Field(..., description="Gene symbol")
    expression_values: Dict[str, float] = Field(
        ..., description="Expression values by sample ID"
    )
    log2_fold_change: Optional[float] = Field(None, description="Log2 fold change")
    p_value: Optional[float] = Field(None, description="P-value")
    adjusted_p_value: Optional[float] = Field(
        None, description="Adjusted p-value (FDR)"
    )
    series_id: str = Field(..., description="Associated GEO series ID")


class DrugTarget(BaseModel):
    """Drug target information."""

    drug_id: str = Field(..., description="Drug identifier")
    drug_name: str = Field(..., description="Drug name")
    target_id: str = Field(..., description="Target identifier")
    target_name: str = Field(..., description="Target name")
    target_type: str = Field(..., description="Target type (protein, gene, etc.)")
    action: Optional[str] = Field(
        None, description="Drug action (inhibitor, activator, etc.)"
    )
    mechanism: Optional[str] = Field(None, description="Mechanism of action")
    indication: Optional[str] = Field(None, description="Therapeutic indication")
    clinical_phase: Optional[str] = Field(
        None, description="Clinical development phase"
    )


class PerturbationProfile(BaseModel):
    """Pellular perturbation profile from CMAP."""

    compound_id: str = Field(..., description="Compound identifier")
    compound_name: str = Field(..., description="Compound name")
    cell_line: str = Field(..., description="Cell line")
    concentration: Optional[float] = Field(None, description="Concentration")
    time_point: Optional[str] = Field(None, description="Time point")
    gene_expression_changes: Dict[str, float] = Field(
        ..., description="Gene expression changes"
    )
    connectivity_score: Optional[float] = Field(None, description="Connectivity score")
    p_value: Optional[float] = Field(None, description="P-value")


class ProteinStructure(BaseModel):
    """Protein structure information from PDB."""

    pdb_id: str = Field(..., description="PDB identifier")
    title: str = Field(..., description="Structure title")
    organism: str = Field(..., description="Organism")
    resolution: Optional[float] = Field(None, description="Resolution in Angstroms")
    method: Optional[str] = Field(None, description="Experimental method")
    chains: List[str] = Field(default_factory=list, description="Chain identifiers")
    sequence: Optional[str] = Field(None, description="Protein sequence")
    secondary_structure: Optional[str] = Field(None, description="Secondary structure")
    binding_sites: List[Dict[str, Any]] = Field(
        default_factory=list, description="Binding sites"
    )
    publication_date: Optional[datetime] = Field(None, description="Publication date")


class ProteinInteraction(BaseModel):
    """Protein-protein interaction from IntAct."""

    interaction_id: str = Field(..., description="Interaction identifier")
    interactor_a: str = Field(..., description="First interactor ID")
    interactor_b: str = Field(..., description="Second interactor ID")
    interaction_type: str = Field(..., description="Type of interaction")
    detection_method: Optional[str] = Field(None, description="Detection method")
    confidence_score: Optional[float] = Field(None, description="Confidence score")
    pubmed_ids: List[str] = Field(
        default_factory=list, description="Supporting PubMed IDs"
    )
    species: Optional[str] = Field(None, description="Species")


class FusedDataset(BaseModel):
    """Fused dataset combining multiple bioinformatics sources."""

    dataset_id: str = Field(..., description="Unique dataset identifier")
    name: str = Field(..., description="Dataset name")
    description: str = Field(..., description="Dataset description")
    source_databases: List[str] = Field(..., description="Source databases")
    creation_date: datetime = Field(
        default_factory=datetime.now, description="Creation date"
    )

    # Fused data components
    go_annotations: List[GOAnnotation] = Field(
        default_factory=list, description="GO annotations"
    )
    pubmed_papers: List[PubMedPaper] = Field(
        default_factory=list, description="PubMed papers"
    )
    geo_series: List[GEOSeries] = Field(default_factory=list, description="GEO series")
    gene_expression_profiles: List[GeneExpressionProfile] = Field(
        default_factory=list, description="Gene expression profiles"
    )
    drug_targets: List[DrugTarget] = Field(
        default_factory=list, description="Drug targets"
    )
    perturbation_profiles: List[PerturbationProfile] = Field(
        default_factory=list, description="Perturbation profiles"
    )
    protein_structures: List[ProteinStructure] = Field(
        default_factory=list, description="Protein structures"
    )
    protein_interactions: List[ProteinInteraction] = Field(
        default_factory=list, description="Protein interactions"
    )

    # Metadata
    total_entities: int = Field(0, description="Total number of entities")
    cross_references: Dict[str, List[str]] = Field(
        default_factory=dict, description="Cross-references between entities"
    )
    quality_metrics: Dict[str, float] = Field(
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

    class Config:
        json_schema_extra = {
            "example": {
                "dataset_id": "bio_fusion_001",
                "name": "GO + PubMed Reasoning Dataset",
                "description": "Fused dataset combining GO annotations with PubMed papers for reasoning tasks",
                "source_databases": ["GO", "PubMed", "UniProt"],
                "total_entities": 1500,
            }
        }


class ReasoningTask(BaseModel):
    """Reasoning task based on fused bioinformatics data."""

    task_id: str = Field(..., description="Task identifier")
    task_type: str = Field(..., description="Type of reasoning task")
    question: str = Field(..., description="Reasoning question")
    context: Dict[str, Any] = Field(default_factory=dict, description="Task context")
    expected_answer: Optional[str] = Field(None, description="Expected answer")
    difficulty_level: str = Field("medium", description="Difficulty level")
    required_evidence: List[EvidenceCode] = Field(
        default_factory=list, description="Required evidence codes"
    )
    supporting_data: List[str] = Field(
        default_factory=list, description="Supporting data identifiers"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "reasoning_001",
                "task_type": "gene_function_prediction",
                "question": "What is the likely function of gene X based on its GO annotations and expression profile?",
                "difficulty_level": "hard",
                "required_evidence": ["IDA", "EXP"],
            }
        }


class DataFusionRequest(BaseModel):
    """Request for data fusion operation."""

    request_id: str = Field(..., description="Request identifier")
    fusion_type: str = Field(
        ..., description="Type of fusion (GO+PubMed, GEO+CMAP, etc.)"
    )
    source_databases: List[str] = Field(..., description="Source databases to fuse")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filtering criteria"
    )
    output_format: str = Field("fused_dataset", description="Output format")
    quality_threshold: float = Field(
        0.8, ge=0.0, le=1.0, description="Quality threshold"
    )
    max_entities: Optional[int] = Field(None, description="Maximum number of entities")

    @classmethod
    def from_config(cls, config: Dict[str, Any], **kwargs) -> "DataFusionRequest":
        """Create DataFusionRequest from configuration."""
        bioinformatics_config = config.get("bioinformatics", {})
        fusion_config = bioinformatics_config.get("fusion", {})

        return cls(
            quality_threshold=fusion_config.get("default_quality_threshold", 0.8),
            max_entities=fusion_config.get("default_max_entities", 1000),
            **kwargs,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "fusion_001",
                "fusion_type": "GO+PubMed",
                "source_databases": ["GO", "PubMed", "UniProt"],
                "filters": {"evidence_codes": ["IDA"], "year_min": 2022},
                "quality_threshold": 0.9,
            }
        }


class BioinformaticsAgentDeps(BaseModel):
    """Dependencies for bioinformatics agents."""

    config: Dict[str, Any] = Field(default_factory=dict)
    data_sources: List[str] = Field(default_factory=list)
    quality_threshold: float = Field(0.8, ge=0.0, le=1.0)

    @classmethod
    def from_config(cls, config: Dict[str, Any], **kwargs) -> "BioinformaticsAgentDeps":
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
    fused_dataset: Optional[FusedDataset] = Field(None, description="Fused dataset")
    quality_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Quality metrics"
    )
    errors: List[str] = Field(default_factory=list, description="Error messages")
    processing_time: float = Field(0.0, description="Processing time in seconds")


class ReasoningResult(BaseModel):
    """Result of reasoning task."""

    success: bool = Field(..., description="Whether reasoning was successful")
    answer: str = Field(..., description="Reasoning answer")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")
    supporting_evidence: List[str] = Field(
        default_factory=list, description="Supporting evidence"
    )
    reasoning_chain: List[str] = Field(
        default_factory=list, description="Reasoning steps"
    )
