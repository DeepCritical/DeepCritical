"""Reuse-first scientific document processing orchestration."""

from __future__ import annotations

import json
import mimetypes
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import unquote, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .adapters import (
    AdaptedDocument,
    BioCAdapter,
    JATSLocatorAdapter,
    NativeTextLocator,
)
from .alignment import DoclingGrobidAligner, ScholarlyAlignmentOverlay
from .clients import (
    DEFAULT_DOCLING_MAX_RESPONSE_BYTES,
    DEFAULT_GROBID_MAX_RESPONSE_BYTES,
    ContainerOCRmyPDFRunner,
    DoclingServeClient,
    GrobidClient,
    OCRmyPDFRunner,
    ParserServiceError,
)
from .models import (
    ArtifactLocationRole,
    ArtifactRelationship,
    ComponentDescriptor,
    ContentSpanSet,
    DataProductRef,
    DiagnosticSeverity,
    DoclingInputFormat,
    DocumentArtifact,
    ExecutionCheckpoint,
    IntakeQuarantineRecord,
    LicenseMetadata,
    MemoryMeasurement,
    MemoryMeasurementStatus,
    OciDigest,
    ProcessingDiagnostic,
    ProcessingRun,
    ProcessingRunDiagnosticManifest,
    ProcessingRunStatus,
    RemediationStatus,
    ResourceUsage,
    RuntimeAttestation,
    RuntimeAttestationSource,
    Sha256,
    configuration_sha256,
    sha256_bytes,
    utc_now,
)
from .preflight import (
    PreflightDecision,
    PreflightDiagnostic,
    PreflightDiagnosticCode,
    PreflightLimits,
    PreflightResult,
    SourceSnapshotError,
    preflight_bytes,
    preflight_stream,
    too_large_result,
    verified_open_path,
)
from .products import product_id_for
from .routing import DocumentRouter, InputFormat, ProcessingStage
from .storage import (
    BlobTooLargeError,
    ContentAddressedStore,
    RecordNotFoundError,
    StoredBlob,
)
from .validation import (
    DoclingQualityReport,
    DoclingQualityValidator,
    QualitySeverity,
    align_bioc_content_spans,
    align_jats_content_spans,
    build_docling_content_spans,
    build_pdf_content_spans,
    probably_image_only,
    validate_content_integrity,
)

if TYPE_CHECKING:
    from .orchestration import (
        PipelineSpec,
        StageExecutor,
    )


def _default_docling_options() -> dict[str, Any]:
    """Return the complete Docling conversion defaults sent by the client."""

    return {
        "to_formats": ["json"],
        "image_export_mode": "embedded",
        "do_ocr": True,
        "table_mode": "accurate",
    }


_COMPONENT_CAPABILITIES = {
    "document-preflight": "document.preflight",
    "document-router": "document.route",
    "document-fallback-policy": "document.route",
    "jats-locator-adapter": "document.adapt",
    "bioc-adapter": "document.adapt",
    "docling": "document.parse",
    "grobid": "document.parse.scholarly",
    "ocrmypdf": "document.ocr",
    "docling-grobid-aligner": "document.align",
    "docling-content-integrity": "document.validate",
}


def _component_descriptor(
    component_id: str,
    component_version: str,
) -> ComponentDescriptor:
    return ComponentDescriptor(
        component_id=component_id,
        component_version=component_version,
        capability=_COMPONENT_CAPABILITIES.get(component_id, "document.process"),
    )


class DocumentProcessingConfig(BaseModel):
    """Pinned parser identity, routing, and quality policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    docling_version: str = "2.113.0"
    docling_serve_version: str = "1.21.0"
    docling_container_image: str = "quay.io/docling-project/docling-serve-cpu:v1.21.0"
    docling_container_digest: OciDigest | None = None
    docling_model_versions: dict[str, str] = Field(default_factory=dict)
    docling_model_hashes: dict[str, Sha256] = Field(default_factory=dict)
    docling_options: dict[str, Any] = Field(default_factory=_default_docling_options)
    docling_max_response_bytes: int = Field(
        default=DEFAULT_DOCLING_MAX_RESPONSE_BYTES, gt=0, strict=True
    )
    grobid_version: str = "0.9.0"
    grobid_enabled: bool = True
    grobid_container_image: str = "deepcritical/grobid:0.9.0-full-p0-c2"
    grobid_container_digest: OciDigest | None = None
    grobid_model_versions: dict[str, str] = Field(default_factory=dict)
    grobid_model_hashes: dict[str, Sha256] = Field(default_factory=dict)
    grobid_max_response_bytes: int = Field(
        default=DEFAULT_GROBID_MAX_RESPONSE_BYTES, gt=0, strict=True
    )
    grobid_minimum_text_characters: int = Field(default=100, ge=0)
    ocrmypdf_version: str = "17.4.1"
    ocr_enabled: bool = True
    ocr_mode: Literal["container_cli", "local_cli"] = "container_cli"
    ocr_container_image: str = "jbarlow83/ocrmypdf:v17.4.1"
    ocr_container_digest: OciDigest | None = None
    ocr_languages: tuple[str, ...] = ("eng",)
    detect_image_only_pdfs: bool = True
    minimum_text_characters_per_page: int = Field(default=20, ge=0)
    image_only_page_ratio: float = Field(default=0.8, ge=0, le=1)
    minimum_pdf_locator_coverage: float = Field(default=0.95, ge=0.95, le=1)
    alignment_minimum_score: float = Field(default=0.72, ge=0, le=1)
    managed_parsers_enabled: bool = False
    require_runtime_identity: bool = True
    preflight_enabled: bool = True
    max_source_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    max_pdf_pages: int = Field(default=1_000, gt=0)
    allow_encrypted_pdfs: bool = False
    require_pdf_page_count: bool = True
    quarantine_on_pdf_structure_uncertainty: bool = True
    quarantine_on_fallback_exhaustion: bool = True
    allow_source_symlinks: bool = False
    reject_extension_only_detection: bool = True
    memory_measurement_required: bool = False

    @field_validator("docling_options")
    @classmethod
    def _expand_docling_options(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Persist the effective options rather than client-side implicit defaults."""

        return {**_default_docling_options(), **value}

    @model_validator(mode="after")
    def _validate_reproducibility_configuration(self) -> DocumentProcessingConfig:
        inventories = (
            (
                "Docling",
                self.docling_model_versions,
                self.docling_model_hashes,
            ),
            (
                "GROBID",
                self.grobid_model_versions,
                self.grobid_model_hashes,
            ),
        )
        for name, versions, hashes in inventories:
            if versions.keys() != hashes.keys():
                raise ValueError(
                    f"{name} model version and hash inventories must have identical keys"
                )
        to_formats = self.docling_options.get("to_formats")
        if not isinstance(to_formats, (list, tuple)) or "json" not in to_formats:
            raise ValueError("Docling options must request serialized JSON output")
        if not self.ocr_languages:
            raise ValueError("at least one OCR language must be configured")
        return self


class ArtifactMetadataConflictError(ValueError):
    """An immutable artifact identity was reused with conflicting metadata."""


def _source_snapshot_failure(
    code: PreflightDiagnosticCode,
    message: str,
    source: Path,
    *,
    byte_size: int | None = None,
    error_type: str | None = None,
) -> PreflightResult:
    details: dict[str, str | int | bool] = {"path": str(source)}
    if error_type is not None:
        details["error_type"] = error_type
    return PreflightResult(
        decision=PreflightDecision.QUARANTINE,
        byte_size=byte_size,
        diagnostics=(
            PreflightDiagnostic(
                code=code,
                severity=DiagnosticSeverity.FATAL,
                message=message,
                details=details,
            ),
        ),
    )


class SourcePreflightError(ValueError):
    """A source could not be safely snapshotted into an artifact."""

    def __init__(
        self,
        result: PreflightResult,
        quarantine_record: IntakeQuarantineRecord | None = None,
    ) -> None:
        super().__init__(
            result.diagnostics[0].message if result.diagnostics else "preflight failed"
        )
        self.result = result
        self.quarantine_record = quarantine_record


class ProcessingRunCommitIncompleteError(RuntimeError):
    """A durable processing run still needs its diagnostic manifest reconciled."""

    def __init__(self, run_id: str) -> None:
        super().__init__(
            f"processing run {run_id} is durable but diagnostic reconciliation is incomplete"
        )
        self.run_id = run_id


@dataclass(frozen=True, slots=True)
class DocumentProcessingResult:
    artifact: DocumentArtifact
    status: ProcessingRunStatus
    route: tuple[str, ...]
    processing_runs: tuple[ProcessingRun, ...]
    diagnostics: tuple[ProcessingDiagnostic, ...]
    docling_document_sha256: str | None = None
    grobid_tei_sha256: str | None = None
    alignment_sha256: str | None = None
    content_integrity_sha256: str | None = None
    content_span_count: int = 0
    derivative_artifact_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _DoclingStage:
    run: ProcessingRun
    document: dict[str, Any]
    report: DoclingQualityReport
    content_span_count: int


@dataclass(frozen=True, slots=True)
class _GrobidStage:
    run: ProcessingRun
    tei_xml: bytes | None
    usable: bool


@dataclass(frozen=True, slots=True)
class _OCRStage:
    run: ProcessingRun
    derivative: DocumentArtifact | None


@dataclass(frozen=True, slots=True)
class _PipelineContext:
    pipeline_run_id: str
    repetition_group_id: str | None
    pipeline_attempt_id: str | None
    force_reprocess: bool


_PIPELINE_CONTEXT: ContextVar[_PipelineContext | None] = ContextVar(
    "document_processing_pipeline_context",
    default=None,
)


# This contract is intentionally broader than an individual ProcessingRun's
# ``configuration``. Individual configurations contain immutable input hashes
# and explain which conditional branch actually ran. The policy snapshot is the
# static contract used to judge whether two workflows were comparable.
_OUTPUT_POLICY_SCHEMA_VERSION = "deepcritical-document-output-policy-v2"
_OUTPUT_POLICY_ROUTING_VERSION = "deterministic-document-router-v1"
_PDF_CONTENT_SPAN_ALGORITHM = "provenance-charspan-v2"
_OUTPUT_POLICY_ALGORITHM_VERSIONS: dict[str, str] = {
    "bioc_locator_alignment": "normalized-exact-v1",
    "content_integrity": "explicit-content-integrity-v1",
    "docling_quality_validation": "docling-quality-v2",
    "grobid_docling_alignment": "token-sequence-v2",
    "jats_locator_alignment": "normalized-exact-v1",
    "pdf_content_spans": _PDF_CONTENT_SPAN_ALGORITHM,
    "preflight": "bounded-input-inspection-v1",
}
_OUTPUT_POLICY_CONTRACT_SCHEMAS: dict[str, str] = {
    "content_span": "1",
    "diagnostic_manifest": "1",
    "docling_document": "DoclingDocument",
}
_RUNTIME_ATTESTATION_SCHEMA_VERSION = "deepcritical-runtime-attestation-v1"
_REMOTE_ATTESTATION_CONTRACT_VERSION = (
    "deepcritical-authenticated-runtime-attestation-reporter-v1"
)
_OCR_DIGEST_RUNNER_VERSION = "deepcritical-container-ocr-runner-v1"

# Runtime supervisors must report these canonical component names with exact
# version values. In particular, a version embedded in an unrelated component
# value is not evidence for one of these named components.
_DOCLING_COMPONENT_KEYS = ("docling", "docling_serve")
_GROBID_COMPONENT_KEYS = ("grobid",)
_OCR_COMPONENT_KEYS = ("ocrmypdf",)


class DocumentProcessor:
    """Route, parse, validate, align, and persist an immutable artifact."""

    def __init__(
        self,
        store: ContentAddressedStore,
        *,
        docling: DoclingServeClient | None = None,
        grobid: GrobidClient | None = None,
        ocrmypdf: OCRmyPDFRunner | ContainerOCRmyPDFRunner | None = None,
        config: DocumentProcessingConfig | None = None,
        pipeline_spec: PipelineSpec | None = None,
        stage_executor: StageExecutor | None = None,
    ) -> None:
        self.store = store
        self.config = config or DocumentProcessingConfig()
        self.docling = docling or DoclingServeClient()
        self.grobid = grobid or GrobidClient()
        if ocrmypdf is not None:
            self.ocrmypdf = ocrmypdf
        elif self.config.ocr_mode == "container_cli":
            self.ocrmypdf = ContainerOCRmyPDFRunner(
                self.config.ocr_container_image,
                languages=self.config.ocr_languages,
                expected_digest=self.config.ocr_container_digest,
                require_digest_addressed=self.config.require_runtime_identity,
            )
        else:
            self.ocrmypdf = OCRmyPDFRunner(languages=self.config.ocr_languages)
        self.router = DocumentRouter(
            reject_extension_only=self.config.reject_extension_only_detection
        )
        self.bioc_adapter = BioCAdapter()
        self.jats_adapter = JATSLocatorAdapter()
        self.validator = DoclingQualityValidator(
            self.config.minimum_pdf_locator_coverage
        )
        self.aligner = DoclingGrobidAligner(self.config.alignment_minimum_score)
        from .document_pipeline import build_document_pipeline

        (
            self.component_registry,
            self.compiled_pipeline,
            self.pipeline_orchestrator,
        ) = build_document_pipeline(
            self,
            pipeline_spec=pipeline_spec,
            executor=stage_executor,
        )
        self.pipeline_spec = self.compiled_pipeline.spec

    def ingest_path(
        self,
        path: str | Path,
        *,
        acquisition_uri: str | None = None,
        media_type: str | None = None,
        identifiers: dict[str, str] | None = None,
        license: LicenseMetadata | None = None,
        relationship: ArtifactRelationship = ArtifactRelationship.SOURCE,
        parent_artifact_id: str | None = None,
    ) -> DocumentArtifact:
        source = Path(path).absolute()
        resolved_media_type = (
            media_type
            or mimetypes.guess_type(source.name)[0]
            or "application/octet-stream"
        )
        resolved_acquisition_uri = acquisition_uri or source.as_uri()
        unsafe_snapshot_codes = {
            PreflightDiagnosticCode.SOURCE_NOT_FOUND,
            PreflightDiagnosticCode.SOURCE_STAT_FAILED,
            PreflightDiagnosticCode.SOURCE_NOT_REGULAR_FILE,
            PreflightDiagnosticCode.SOURCE_SYMLINK_NOT_ALLOWED,
            PreflightDiagnosticCode.SOURCE_TOO_LARGE,
            PreflightDiagnosticCode.SOURCE_READ_FAILED,
            PreflightDiagnosticCode.SOURCE_SNAPSHOT_CHANGED,
        }
        try:
            with verified_open_path(
                source,
                limits=self._preflight_limits(),
            ) as verified:
                source_stream = verified.stream
                opened_stat = verified.opened_stat
                preflight = (
                    preflight_stream(
                        source_stream,
                        byte_size=opened_stat.st_size,
                        limits=self._preflight_limits(),
                        filename=source.name,
                        media_type=resolved_media_type,
                    )
                    if self.config.preflight_enabled
                    else None
                )
                if preflight is not None and (
                    preflight.byte_size is None
                    or any(
                        item.code in unsafe_snapshot_codes
                        for item in preflight.diagnostics
                    )
                ):
                    raise SourceSnapshotError(preflight)
                source_stream.seek(0)
                read_limit = (
                    self.config.max_source_bytes + 1
                    if self.config.preflight_enabled
                    else -1
                )
                content = source_stream.read(read_limit)
                if (
                    self.config.preflight_enabled
                    and len(content) > self.config.max_source_bytes
                ):
                    raise BlobTooLargeError(
                        max_bytes=self.config.max_source_bytes,
                        observed_bytes=len(content),
                    )
            blob = self.store.put_blob(
                content,
                max_bytes=(
                    self.config.max_source_bytes
                    if self.config.preflight_enabled
                    else None
                ),
            )
        except FileNotFoundError as exc:
            result = _source_snapshot_failure(
                PreflightDiagnosticCode.SOURCE_NOT_FOUND,
                "Source path does not exist.",
                source,
                error_type=type(exc).__name__,
            )
            quarantine = self._record_intake_quarantine(
                source,
                acquisition_uri=resolved_acquisition_uri,
                media_type=resolved_media_type,
                result=result,
            )
            raise SourcePreflightError(result, quarantine) from exc
        except SourceSnapshotError as exc:
            quarantine = self._record_intake_quarantine(
                source,
                acquisition_uri=resolved_acquisition_uri,
                media_type=resolved_media_type,
                result=exc.result,
            )
            raise SourcePreflightError(exc.result, quarantine) from exc
        except OSError as exc:
            result = _source_snapshot_failure(
                PreflightDiagnosticCode.SOURCE_READ_FAILED,
                "Source could not be opened or read.",
                source,
                error_type=type(exc).__name__,
            )
            quarantine = self._record_intake_quarantine(
                source,
                acquisition_uri=resolved_acquisition_uri,
                media_type=resolved_media_type,
                result=result,
            )
            raise SourcePreflightError(result, quarantine) from exc
        except BlobTooLargeError as exc:
            result = too_large_result(exc.observed_bytes, exc.max_bytes)
            quarantine = self._record_intake_quarantine(
                source,
                acquisition_uri=resolved_acquisition_uri,
                media_type=resolved_media_type,
                result=result,
            )
            raise SourcePreflightError(result, quarantine) from exc
        normalized_identifiers = {**(identifiers or {}), "filename": source.name}
        artifact = self._ingest_blob(
            blob,
            acquisition_uri=resolved_acquisition_uri,
            media_type=resolved_media_type,
            identifiers=normalized_identifiers,
            license=license,
            relationship=relationship,
            parent_artifact_id=parent_artifact_id,
        )
        if preflight is not None:
            self._record_preflight(artifact, preflight)
        return artifact

    def _record_intake_quarantine(
        self,
        source: str | Path,
        *,
        acquisition_uri: str,
        media_type: str,
        result: PreflightResult,
    ) -> IntakeQuarantineRecord:
        if result.decision is not PreflightDecision.QUARANTINE:
            raise ValueError("only rejected source intake can be quarantined")
        result_blob = self.store.put_blob(
            _canonical_json_bytes(result.model_dump(mode="json"))
        )
        policy_hash = configuration_sha256(
            self._preflight_limits().model_dump(mode="json")
        )
        identity = {
            "source_path": str(source),
            "acquisition_uri": acquisition_uri,
            "media_type": media_type,
            "preflight_result_sha256": result_blob.sha256,
            "preflight_policy_sha256": policy_hash,
        }
        intake_id = f"intake-{configuration_sha256(identity)}"
        try:
            existing = self.store.get_intake_quarantine(intake_id)
        except RecordNotFoundError:
            existing = None
        record = IntakeQuarantineRecord(
            intake_id=intake_id,
            source_path=str(source),
            acquisition_uri=acquisition_uri,
            media_type=media_type,
            observed_byte_size=result.byte_size,
            preflight_result_sha256=result_blob.sha256,
            preflight_policy_sha256=policy_hash,
            reason_codes=tuple(item.code.value for item in result.diagnostics),
            created_at=(existing.created_at if existing is not None else utc_now()),
        )
        if existing is not None:
            if existing != record:
                raise ArtifactMetadataConflictError(
                    f"intake quarantine {intake_id} has conflicting immutable metadata"
                )
            return existing
        self.store.save_intake_quarantine(record)
        return record

    def ingest_bytes(
        self,
        content: bytes,
        *,
        acquisition_uri: str,
        media_type: str,
        identifiers: dict[str, str] | None = None,
        license: LicenseMetadata | None = None,
        relationship: ArtifactRelationship = ArtifactRelationship.SOURCE,
        parent_artifact_id: str | None = None,
        created_by_run_id: str | None = None,
    ) -> DocumentArtifact:
        preflight = (
            preflight_bytes(
                content,
                limits=self._preflight_limits(),
                filename=(identifiers or {}).get("filename"),
                media_type=media_type,
            )
            if self.config.preflight_enabled
            else None
        )
        if preflight is not None and any(
            diagnostic.code is PreflightDiagnosticCode.SOURCE_TOO_LARGE
            for diagnostic in preflight.diagnostics
        ):
            quarantine = self._record_intake_quarantine(
                f"bytes-sha256:{sha256_bytes(content)}",
                acquisition_uri=acquisition_uri,
                media_type=media_type,
                result=preflight,
            )
            raise SourcePreflightError(preflight, quarantine)
        blob = self.store.put_blob(content)
        artifact = self._ingest_blob(
            blob,
            acquisition_uri=acquisition_uri,
            media_type=media_type,
            identifiers=identifiers,
            license=license,
            relationship=relationship,
            parent_artifact_id=parent_artifact_id,
            created_by_run_id=created_by_run_id,
        )
        if preflight is not None:
            self._record_preflight(artifact, preflight)
        return artifact

    def _ingest_blob(
        self,
        blob: StoredBlob,
        *,
        acquisition_uri: str,
        media_type: str,
        identifiers: dict[str, str] | None,
        license: LicenseMetadata | None,
        relationship: ArtifactRelationship,
        parent_artifact_id: str | None,
        created_by_run_id: str | None = None,
    ) -> DocumentArtifact:
        artifact_id = _artifact_id(
            blob.sha256,
            acquisition_uri=acquisition_uri,
            relationship=relationship,
            parent_artifact_id=parent_artifact_id,
        )
        try:
            existing = self.store.get_artifact(artifact_id)
        except RecordNotFoundError:
            pass
        else:
            if existing.raw_location.created_by_run_id != created_by_run_id:
                raise ArtifactMetadataConflictError(
                    f"artifact {artifact_id} already exists with different immutable creator lineage"
                )
            expected = DocumentArtifact(
                artifact_id=artifact_id,
                source_sha256=blob.sha256,
                acquisition_uri=acquisition_uri,
                identifiers=identifiers or {},
                license=license,
                media_type=media_type,
                relationship=relationship,
                parent_artifact_id=parent_artifact_id,
                raw_location=existing.raw_location,
                derived_locations=existing.derived_locations,
                created_at=existing.created_at,
            )
            if expected != existing:
                raise ArtifactMetadataConflictError(
                    f"artifact {artifact_id} already exists with different immutable metadata"
                )
            return existing
        artifact = DocumentArtifact(
            artifact_id=artifact_id,
            source_sha256=blob.sha256,
            acquisition_uri=acquisition_uri,
            identifiers=identifiers or {},
            license=license,
            media_type=media_type,
            relationship=relationship,
            parent_artifact_id=parent_artifact_id,
            raw_location=blob.as_location(
                media_type=media_type,
                role=ArtifactLocationRole.RAW,
                created_by_run_id=created_by_run_id,
            ),
        )
        self.store.save_artifact(artifact)
        return artifact

    def _preflight_limits(self) -> PreflightLimits:
        return PreflightLimits(
            max_source_bytes=self.config.max_source_bytes,
            max_pdf_pages=self.config.max_pdf_pages,
            allow_encrypted_pdfs=self.config.allow_encrypted_pdfs,
            require_pdf_page_count=self.config.require_pdf_page_count,
            quarantine_on_pdf_structure_uncertainty=(
                self.config.quarantine_on_pdf_structure_uncertainty
            ),
            allow_symlinks=self.config.allow_source_symlinks,
        )

    def _preflight_configuration(self, artifact: DocumentArtifact) -> dict[str, Any]:
        return {
            "preflight_version": "1",
            "source_sha256": artifact.source_sha256,
            "limits": self._preflight_limits().model_dump(mode="json"),
        }

    def _source_data_products(
        self, artifact: DocumentArtifact
    ) -> tuple[DataProductRef, ...]:
        """Resolve the exact product that created a derivative source blob."""

        producer_run_id = artifact.raw_location.created_by_run_id
        if producer_run_id is None:
            return ()
        producer = self.store.get_processing_run(producer_run_id)
        products = tuple(
            product
            for product in producer.outputs
            if product.blob_sha256 == artifact.source_sha256
        )
        if len(products) != 1:
            raise ValueError(
                f"derivative artifact {artifact.artifact_id!r} must resolve to "
                "exactly one producer output"
            )
        return products

    @staticmethod
    def _source_artifact_ids(
        artifact: DocumentArtifact,
        inputs: tuple[DataProductRef, ...],
    ) -> tuple[str, ...]:
        """Preserve direct and inherited artifact lineage in stable order."""

        return tuple(
            dict.fromkeys(
                (
                    artifact.artifact_id,
                    *(
                        source_artifact_id
                        for product in inputs
                        for source_artifact_id in product.source_artifact_ids
                    ),
                )
            )
        )

    def _record_preflight(
        self, artifact: DocumentArtifact, result: PreflightResult
    ) -> tuple[ProcessingRun, PreflightResult]:
        configuration = self._preflight_configuration(artifact)
        config_hash = configuration_sha256(configuration)
        previous = self.store.list_processing_runs(
            artifact_id=artifact.artifact_id,
            component_id="document-preflight",
            configuration_sha256=config_hash,
        )
        reusable = self._select_reusable_run(
            previous,
            statuses=frozenset(
                {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.QUARANTINED}
            ),
            required_outputs=("preflight_result",),
        )
        if reusable is not None:
            run = reusable
            self._reconcile_run_diagnostics(artifact, run)
            persisted = PreflightResult.model_validate_json(
                self.store.read_blob(run.require_output("preflight_result").blob_sha256)
            )
            return run, persisted

        payload = _canonical_json_bytes(result.model_dump(mode="json"))
        output = self.store.put_blob(payload)
        now = utc_now()
        run_id = _run_id()
        inputs = self._source_data_products(artifact)
        run = ProcessingRun(
            run_id=run_id,
            artifact_id=artifact.artifact_id,
            stage_id="document-preflight",
            component=_component_descriptor("document-preflight", "1"),
            configuration=configuration,
            configuration_sha256=config_hash,
            started_at=now,
            finished_at=now,
            status=(
                ProcessingRunStatus.COMPLETE
                if result.may_proceed
                else ProcessingRunStatus.QUARANTINED
            ),
            resource_usage=ResourceUsage(input_bytes=result.byte_size),
            warnings=tuple(item.message for item in result.diagnostics),
            inputs=inputs,
            outputs=self.store.data_product_refs(
                {"preflight_result": output.sha256},
                producer_run_id=run_id,
                source_artifact_ids=self._source_artifact_ids(artifact, inputs),
            ),
            completed_stages=("bounded_input_inspection", "policy_decision"),
        )
        diagnostics = tuple(
            self._build_diagnostic(
                artifact,
                run.run_id,
                severity=item.severity,
                stage="preflight",
                code=item.code.value,
                message=item.message,
                details=dict(item.details),
            )
            for item in result.diagnostics
        )
        return self._commit_processing_run(artifact, run, diagnostics), result

    def _load_or_run_preflight(
        self, artifact: DocumentArtifact
    ) -> tuple[ProcessingRun, PreflightResult]:
        configuration = self._preflight_configuration(artifact)
        runs = self.store.list_processing_runs(
            artifact_id=artifact.artifact_id,
            component_id="document-preflight",
            configuration_sha256=configuration_sha256(configuration),
        )
        reusable = self._select_reusable_run(
            runs,
            statuses=frozenset(
                {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.QUARANTINED}
            ),
            required_outputs=("preflight_result",),
        )
        if reusable is not None:
            run = reusable
            self._reconcile_run_diagnostics(artifact, run)
            result = PreflightResult.model_validate_json(
                self.store.read_blob(run.require_output("preflight_result").blob_sha256)
            )
            return run, result

        if artifact.raw_location.byte_size > self.config.max_source_bytes:
            result = PreflightResult(
                decision=PreflightDecision.QUARANTINE,
                byte_size=artifact.raw_location.byte_size,
                diagnostics=(
                    PreflightDiagnostic(
                        code=PreflightDiagnosticCode.SOURCE_TOO_LARGE,
                        severity=DiagnosticSeverity.FATAL,
                        message="Source exceeds the configured byte limit.",
                        details={
                            "actual_bytes": artifact.raw_location.byte_size,
                            "max_source_bytes": self.config.max_source_bytes,
                        },
                    ),
                ),
            )
        else:
            result = preflight_bytes(
                self.store.read_blob(artifact.source_sha256),
                limits=self._preflight_limits(),
                filename=artifact.identifiers.get("filename"),
                media_type=artifact.media_type,
            )
        return self._record_preflight(artifact, result)

    async def process_path(
        self,
        path: str | Path,
        *,
        force_reprocess: bool = False,
        repetition_group_id: str | None = None,
        pipeline_attempt_id: str | None = None,
        **ingest_kwargs: Any,
    ) -> DocumentProcessingResult:
        artifact = self.ingest_path(path, **ingest_kwargs)
        return await self.process_artifact(
            artifact.artifact_id,
            force_reprocess=force_reprocess,
            repetition_group_id=repetition_group_id,
            pipeline_attempt_id=pipeline_attempt_id,
        )

    async def process_artifact(
        self,
        artifact_id: str,
        *,
        force_reprocess: bool = False,
        repetition_group_id: str | None = None,
        pipeline_attempt_id: str | None = None,
    ) -> DocumentProcessingResult:
        normalized_repetition_group_id = _optional_workflow_identifier(
            repetition_group_id, "repetition_group_id"
        )
        normalized_attempt_id = _optional_workflow_identifier(
            pipeline_attempt_id, "pipeline_attempt_id"
        )
        if repetition_group_id is not None and not force_reprocess:
            raise ValueError(
                "repetition_group_id requires force_reprocess so benchmark attempts are independent"
            )
        if normalized_attempt_id is not None and not force_reprocess:
            raise ValueError("pipeline_attempt_id requires force_reprocess")
        if normalized_repetition_group_id is not None and normalized_attempt_id is None:
            raise ValueError(
                "benchmark repetition groups require pipeline_attempt_id so retries "
                "resume one attempt and independent attempts remain isolated"
            )
        output_policy_sha256 = self._current_output_policy_sha256()
        pipeline_run_id = (
            _forced_pipeline_run_id(
                artifact_id,
                output_policy_sha256=output_policy_sha256,
                repetition_group_id=normalized_repetition_group_id,
                pipeline_attempt_id=normalized_attempt_id,
            )
            if force_reprocess and normalized_attempt_id is not None
            else f"workflow-{uuid.uuid4()}"
        )
        context = _PipelineContext(
            pipeline_run_id=pipeline_run_id,
            repetition_group_id=normalized_repetition_group_id,
            pipeline_attempt_id=normalized_attempt_id,
            force_reprocess=force_reprocess,
        )
        token = _PIPELINE_CONTEXT.set(context)
        try:
            return await self._process_artifact_once(artifact_id)
        finally:
            _PIPELINE_CONTEXT.reset(token)

    async def _process_artifact_once(
        self,
        artifact_id: str,
    ) -> DocumentProcessingResult:
        context = _PIPELINE_CONTEXT.get()
        if context is None:
            raise RuntimeError("document pipeline execution context is missing")
        execution = await self.pipeline_orchestrator.execute(
            self.compiled_pipeline,
            {"artifact_id": artifact_id},
            pipeline_run_id=context.pipeline_run_id,
        )
        for stage in self.compiled_pipeline.stages:
            result = execution.results[stage.spec.stage_id].outputs.get("result")
            if isinstance(result, DocumentProcessingResult):
                return result
        raise RuntimeError("document pipeline completed without a terminal result")

    def _run_jats_locator_adapter(
        self,
        artifact: DocumentArtifact,
        content: bytes,
    ) -> tuple[tuple[NativeTextLocator, ...], ProcessingRun]:
        configuration = {
            "adapter_version": "1",
            "input_format": InputFormat.JATS.value,
            "input_sha256": sha256_bytes(content),
        }
        reusable = self._reusable_run(artifact, "jats-locator-adapter", configuration)
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            return (
                tuple(
                    NativeTextLocator(**item)
                    for item in json.loads(
                        self.store.read_blob(
                            reusable.require_output(
                                "native_locator_overlay"
                            ).blob_sha256
                        )
                    )
                ),
                reusable,
            )

        started = utc_now()
        started_clock = time.perf_counter()
        try:
            locators = self.jats_adapter.extract_locators(content)
            overlay_bytes = _canonical_json_bytes(_native_locator_payload(locators))
            overlay = self.store.put_blob(overlay_bytes)
            warning_message = "JATS parsing produced no native textual locators"
            warnings = () if locators else (warning_message,)
            run_id = _run_id()
            inputs = self._source_data_products(artifact)
            run = ProcessingRun(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                stage_id="jats-locator-adapter",
                component=_component_descriptor("jats-locator-adapter", "1"),
                configuration=configuration,
                configuration_sha256=configuration_sha256(configuration),
                started_at=started,
                finished_at=utc_now(),
                status=(
                    ProcessingRunStatus.COMPLETE
                    if locators
                    else ProcessingRunStatus.PARTIAL
                ),
                resource_usage=ResourceUsage(
                    wall_time_seconds=time.perf_counter() - started_clock,
                    input_bytes=len(content),
                    output_bytes=len(overlay_bytes),
                ),
                inputs=inputs,
                outputs=self.store.data_product_refs(
                    {"native_locator_overlay": overlay.sha256},
                    producer_run_id=run_id,
                    source_artifact_ids=self._source_artifact_ids(artifact, inputs),
                ),
                warnings=warnings,
                completed_stages=("parse_jats", "preserve_native_locators"),
            )
            diagnostics: tuple[ProcessingDiagnostic, ...] = ()
            if not locators:
                diagnostics = (
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.ERROR,
                        stage="jats_locator_adapter",
                        code="JATS_NATIVE_LOCATORS_EMPTY",
                        message=warning_message,
                    ),
                )
            run = self._commit_processing_run(artifact, run, diagnostics)
            return locators, run
        except ProcessingRunCommitIncompleteError:
            raise
        except Exception as exc:
            run = self._save_failed_run(
                artifact,
                component_id="jats-locator-adapter",
                component_version="1",
                configuration=configuration,
                started_at=started,
                started_clock=started_clock,
                error=exc,
            )
            return (), run

    def _run_bioc_adapter(
        self,
        artifact: DocumentArtifact,
        content: bytes,
        input_format: InputFormat,
    ) -> tuple[AdaptedDocument | None, ProcessingRun]:
        configuration = {
            "adapter_version": "1",
            "input_format": input_format.value,
            "input_sha256": sha256_bytes(content),
        }
        reusable = self._reusable_run(artifact, "bioc-adapter", configuration)
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            adapted = AdaptedDocument(
                content=self.store.read_blob(
                    reusable.require_output("html_projection").blob_sha256
                ),
                filename="bioc-document.html",
                media_type="text/html",
                native_format=input_format,
                locator_overlay=tuple(
                    NativeTextLocator(**item)
                    for item in json.loads(
                        self.store.read_blob(
                            reusable.require_output(
                                "native_locator_overlay"
                            ).blob_sha256
                        )
                    )
                ),
            )
            return adapted, reusable

        started = utc_now()
        started_clock = time.perf_counter()
        try:
            adapted = self.bioc_adapter.adapt(content, input_format=input_format)
            projection = self.store.put_blob(adapted.content)
            overlay_bytes = _canonical_json_bytes(adapted.overlay_json())
            overlay = self.store.put_blob(overlay_bytes)
            warning_message = "BioC parsing produced no native textual locators"
            warnings = () if adapted.locator_overlay else (warning_message,)
            finished = utc_now()
            run_id = _run_id()
            inputs = self._source_data_products(artifact)
            run = ProcessingRun(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                stage_id="bioc-adapter",
                component=_component_descriptor("bioc-adapter", "1"),
                configuration=configuration,
                configuration_sha256=configuration_sha256(configuration),
                started_at=started,
                finished_at=finished,
                status=(
                    ProcessingRunStatus.COMPLETE
                    if adapted.locator_overlay
                    else ProcessingRunStatus.PARTIAL
                ),
                resource_usage=ResourceUsage(
                    wall_time_seconds=time.perf_counter() - started_clock,
                    input_bytes=len(content),
                    output_bytes=len(adapted.content) + len(overlay_bytes),
                ),
                inputs=inputs,
                outputs=self.store.data_product_refs(
                    {
                        "html_projection": projection.sha256,
                        "native_locator_overlay": overlay.sha256,
                    },
                    producer_run_id=run_id,
                    source_artifact_ids=self._source_artifact_ids(artifact, inputs),
                ),
                warnings=warnings,
                completed_stages=("parse_bioc", "project_html", "preserve_offsets"),
            )
            diagnostics: tuple[ProcessingDiagnostic, ...] = ()
            if not adapted.locator_overlay:
                diagnostics = (
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.ERROR,
                        stage="bioc_adapter",
                        code="BIOC_NATIVE_LOCATORS_EMPTY",
                        message=warning_message,
                    ),
                )
            run = self._commit_processing_run(artifact, run, diagnostics)
            return adapted, run
        except ProcessingRunCommitIncompleteError:
            raise
        except Exception as exc:
            run = self._save_failed_run(
                artifact,
                component_id="bioc-adapter",
                component_version="1",
                configuration=configuration,
                started_at=started,
                started_clock=started_clock,
                error=exc,
            )
            return None, run

    def _runtime_trust_policy(self) -> dict[str, dict[str, Any]]:
        """Return non-secret expectations for task-bound runtime evidence.

        Reporter endpoints and credentials are deliberately excluded. A reporter
        identity is part of the output contract because changing the trusted
        observer must invalidate processing-run reuse just like changing a model or
        parser image does.
        """

        def remote_policy(client: Any) -> dict[str, Any]:
            reporter = getattr(client, "runtime_reporter", None)
            raw_reporter_id = getattr(reporter, "expected_reporter_id", None)
            expected_reporter_id = (
                raw_reporter_id.strip()
                if isinstance(raw_reporter_id, str) and raw_reporter_id.strip()
                else None
            )
            return {
                "reporter_configured": reporter is not None,
                "expected_reporter_id": expected_reporter_id,
                "expected_source": (
                    RuntimeAttestationSource.AUTHENTICATED_DEPLOYMENT_REPORTER.value
                ),
                "attestation_contract_version": (_REMOTE_ATTESTATION_CONTRACT_VERSION),
                "attestation_schema_version": _RUNTIME_ATTESTATION_SCHEMA_VERSION,
            }

        return {
            "docling": remote_policy(self.docling),
            "grobid": remote_policy(self.grobid),
            "ocrmypdf": {
                "reporter_configured": self.config.ocr_mode == "container_cli",
                "expected_reporter_id": _OCR_DIGEST_RUNNER_VERSION,
                "expected_source": (
                    RuntimeAttestationSource.DIGEST_ADDRESSED_OCI_INVOCATION.value
                ),
                "attestation_contract_version": _OCR_DIGEST_RUNNER_VERSION,
                "attestation_schema_version": _RUNTIME_ATTESTATION_SCHEMA_VERSION,
                "local_digest_runner_version": _OCR_DIGEST_RUNNER_VERSION,
            },
        }

    def _expected_component_versions(
        self, component_id: Literal["docling", "grobid", "ocrmypdf"]
    ) -> dict[str, str]:
        """Return exact versions under the canonical attestation component keys."""

        if component_id == "docling":
            values = (self.config.docling_version, self.config.docling_serve_version)
            return dict(zip(_DOCLING_COMPONENT_KEYS, values, strict=True))
        if component_id == "grobid":
            return {_GROBID_COMPONENT_KEYS[0]: self.config.grobid_version}
        return {_OCR_COMPONENT_KEYS[0]: self.config.ocrmypdf_version}

    def _runtime_attestation_warnings(
        self,
        component_id: Literal["docling", "grobid", "ocrmypdf"],
        attestation: RuntimeAttestation | None,
        resolution_error: str | None,
    ) -> tuple[str, ...]:
        """Compare observed evidence with expectations without echoing config."""

        if not self.config.require_runtime_identity:
            return ()
        warnings: list[str] = []
        if attestation is None:
            detail = resolution_error or "runtime_attestation_unavailable"
            return (f"{component_id} task-bound runtime attestation missing: {detail}",)

        if component_id == "docling":
            expected_digest = self.config.docling_container_digest
            expected_versions = self.config.docling_model_versions
            expected_hashes = self.config.docling_model_hashes
        elif component_id == "grobid":
            expected_digest = self.config.grobid_container_digest
            expected_versions = self.config.grobid_model_versions
            expected_hashes = self.config.grobid_model_hashes
        else:
            expected_digest = (
                self.config.ocr_container_digest
                if self.config.ocr_mode == "container_cli"
                else None
            )
            expected_versions = {}
            expected_hashes = {}

        trust_policy = self._runtime_trust_policy()[component_id]
        expected_reporter_id = trust_policy["expected_reporter_id"]
        if trust_policy["reporter_configured"] is not True:
            warnings.append(
                f"{component_id} runtime attestation reporter is not configured"
            )
        if expected_reporter_id is None:
            warnings.append(
                f"{component_id} expected runtime reporter ID is not configured"
            )
        elif attestation.reporter_id != expected_reporter_id:
            warnings.append(
                f"{component_id} attested reporter differs from current trust policy"
            )
        if attestation.source.value != trust_policy["expected_source"]:
            warnings.append(
                f"{component_id} attested source differs from current trust policy"
            )
        if attestation.schema_version != trust_policy["attestation_schema_version"]:
            warnings.append(
                f"{component_id} attestation schema differs from current trust policy"
            )

        if attestation.component_id != component_id:
            warnings.append("runtime attestation parser identity does not match")
        if component_id == "docling":
            expected_image = self.config.docling_container_image
        elif component_id == "grobid":
            expected_image = self.config.grobid_container_image
        else:
            expected_image = self.config.ocr_container_image
        if (
            attestation.container_reference.split("@", maxsplit=1)[0]
            != (expected_image.split("@", maxsplit=1)[0])
        ):
            warnings.append(
                f"{component_id} attested container reference differs from expectation"
            )
        if expected_digest is None:
            warnings.append(
                f"{component_id} expected container digest is not configured"
            )
        elif attestation.container_digest != expected_digest:
            warnings.append(
                f"{component_id} attested container digest differs from expectation"
            )
        for component, expected in self._expected_component_versions(
            component_id
        ).items():
            if attestation.component_versions.get(component) != expected:
                warnings.append(
                    f"{component_id} expected component {component!r} version "
                    f"{expected!r} was not attested exactly"
                )
        if component_id in {"docling", "grobid"} and not expected_hashes:
            warnings.append(f"{component_id} expected model hash inventory is empty")
        if attestation.model_versions != expected_versions:
            warnings.append(
                f"{component_id} attested model versions differ from expectation"
            )
        if attestation.model_hashes != expected_hashes:
            warnings.append(
                f"{component_id} attested model hashes differ from expectation"
            )
        return tuple(dict.fromkeys(warnings))

    async def _run_docling(
        self,
        artifact: DocumentArtifact,
        content: bytes,
        *,
        filename: str,
        media_type: str,
        input_format: InputFormat,
        native_locators: tuple[NativeTextLocator, ...],
        inputs: tuple[DataProductRef, ...],
    ) -> _DoclingStage | None:
        configuration = {
            "serve_version": self.config.docling_serve_version,
            "expected_docling_version": self.config.docling_version,
            "container_image": self.config.docling_container_image,
            "container_digest": self.config.docling_container_digest,
            "model_versions": self.config.docling_model_versions,
            "model_hashes": self.config.docling_model_hashes,
            "input_sha256": sha256_bytes(content),
            "input_format": input_format.value,
            "options": self.config.docling_options,
            "minimum_pdf_locator_coverage": self.config.minimum_pdf_locator_coverage,
            "quality_validator_version": "docling-quality-v2",
            "content_span_schema_version": "1",
        }
        native_locator_bytes = (
            _canonical_json_bytes(_native_locator_payload(native_locators))
            if native_locators
            else None
        )
        if input_format is InputFormat.JATS:
            configuration.update(
                {
                    "jats_locator_alignment_algorithm": "normalized-exact-v1",
                    "native_locator_overlay_sha256": sha256_bytes(
                        native_locator_bytes or b"[]"
                    ),
                }
            )
        elif input_format in {InputFormat.BIOC_JSON, InputFormat.BIOC_XML}:
            configuration.update(
                {
                    "bioc_locator_alignment_algorithm": "normalized-exact-v1",
                    "native_locator_overlay_sha256": sha256_bytes(
                        native_locator_bytes or b"[]"
                    ),
                }
            )
        elif input_format is InputFormat.PDF:
            configuration["pdf_span_algorithm"] = _PDF_CONTENT_SPAN_ALGORITHM
        config_hash = configuration_sha256(configuration)
        output_policy_sha256 = self._current_output_policy_sha256()
        pipeline_context = _PIPELINE_CONTEXT.get()
        force_attempt_id = (
            configuration_sha256(
                {
                    "schema": "deepcritical-forced-checkpoint-attempt-v1",
                    "repetition_group_id": pipeline_context.repetition_group_id,
                    "pipeline_attempt_id": (
                        pipeline_context.pipeline_attempt_id
                        or pipeline_context.pipeline_run_id
                    ),
                }
            )
            if pipeline_context is not None and pipeline_context.force_reprocess
            else None
        )
        checkpoint_id = _execution_checkpoint_id(
            artifact.artifact_id,
            "docling",
            config_hash,
            output_policy_sha256=output_policy_sha256,
            attempt_id=force_attempt_id,
        )
        reusable = self._reusable_run(artifact, "docling", configuration)
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            self.store.delete_execution_checkpoint(checkpoint_id)
            document = json.loads(
                self.store.read_blob(
                    reusable.require_output("docling_document").blob_sha256
                )
            )
            report = self.validator.validate(
                document, require_pdf_geometry=input_format is InputFormat.PDF
            )
            span_set = ContentSpanSet.model_validate_json(
                self.store.read_blob(
                    reusable.require_output("content_spans").blob_sha256
                )
            )
            return _DoclingStage(reusable, document, report, len(span_set.spans))

        started = utc_now()
        started_clock = time.perf_counter()
        checkpoint: ExecutionCheckpoint | None = None
        try:
            try:
                checkpoint = self.store.get_execution_checkpoint(checkpoint_id)
            except RecordNotFoundError:
                checkpoint = None
            if checkpoint is not None and not _checkpoint_matches_invocation(
                checkpoint,
                artifact_id=artifact.artifact_id,
                component_id="docling",
                configuration_sha256=config_hash,
                output_policy_sha256=output_policy_sha256,
                pipeline_context=pipeline_context,
            ):
                raise RuntimeError(
                    "persisted Docling checkpoint does not match the current "
                    "artifact, policy, parser configuration, or workflow attempt"
                )

            def persist_remote_task(task_id: str) -> None:
                self.store.save_execution_checkpoint(
                    ExecutionCheckpoint(
                        checkpoint_id=checkpoint_id,
                        artifact_id=artifact.artifact_id,
                        component_id="docling",
                        configuration_sha256=config_hash,
                        output_policy_sha256=output_policy_sha256,
                        pipeline_run_id=(
                            pipeline_context.pipeline_run_id
                            if pipeline_context is not None
                            else None
                        ),
                        repetition_group_id=(
                            pipeline_context.repetition_group_id
                            if pipeline_context is not None
                            else None
                        ),
                        pipeline_attempt_id=(
                            pipeline_context.pipeline_attempt_id
                            if pipeline_context is not None
                            else None
                        ),
                        remote_task_id=task_id,
                    )
                )

            result = await self.docling.convert(
                content,
                filename=filename,
                media_type=media_type,
                options=self.config.docling_options,
                resume_task_id=(
                    checkpoint.remote_task_id if checkpoint is not None else None
                ),
                on_task_submitted=persist_remote_task,
            )
            attestation = result.runtime_attestation
            provenance_warnings = self._runtime_attestation_warnings(
                "docling", attestation, result.runtime_attestation_error
            )
            component_versions = (
                dict(attestation.component_versions) if attestation is not None else {}
            )
            document = result.document
            report = self.validator.validate(
                document, require_pdf_geometry=input_format is InputFormat.PDF
            )
            run_id = _run_id()
            raw_bytes = _canonical_json_bytes(result.raw_response)
            document_bytes = _canonical_json_bytes(document)
            raw_blob = self.store.put_blob(raw_bytes)
            document_blob = self.store.put_blob(document_bytes)
            representation_product_id = product_id_for(
                name="docling_document",
                blob_sha256=document_blob.sha256,
                producer_run_id=run_id,
            )
            jats_alignment = None
            bioc_alignment = None
            if input_format is InputFormat.PDF:
                spans = build_pdf_content_spans(
                    document,
                    artifact_id=artifact.artifact_id,
                    processing_run_id=run_id,
                    representation_product_id=representation_product_id,
                )
            elif input_format is InputFormat.JATS:
                jats_alignment = align_jats_content_spans(
                    document,
                    native_locators,
                    artifact_id=artifact.artifact_id,
                    processing_run_id=run_id,
                    representation_product_id=representation_product_id,
                )
                spans = jats_alignment.spans
            elif input_format in {InputFormat.BIOC_JSON, InputFormat.BIOC_XML}:
                bioc_alignment = align_bioc_content_spans(
                    document,
                    native_locators,
                    artifact_id=artifact.artifact_id,
                    processing_run_id=run_id,
                    representation_product_id=representation_product_id,
                )
                spans = bioc_alignment.spans
            else:
                docling_input_formats: dict[InputFormat, DoclingInputFormat] = {
                    InputFormat.HTML: "html",
                    InputFormat.DOCX: "docx",
                    InputFormat.PPTX: "pptx",
                    InputFormat.XLSX: "xlsx",
                    InputFormat.IMAGE: "image",
                }
                try:
                    docling_input_format = docling_input_formats[input_format]
                except KeyError as exc:
                    raise ValueError(
                        f"unsupported Docling input format: {input_format.value}"
                    ) from exc
                spans = build_docling_content_spans(
                    document,
                    artifact_id=artifact.artifact_id,
                    processing_run_id=run_id,
                    input_format=docling_input_format,
                    representation_product_id=representation_product_id,
                )

            span_set = ContentSpanSet(
                artifact_id=artifact.artifact_id,
                processing_run_id=run_id,
                representation_product_id=representation_product_id,
                spans=spans,
            )
            spans_bytes = _canonical_json_bytes(span_set.model_dump(mode="json"))
            spans_blob = self.store.put_blob(spans_bytes)
            output_digests = {
                "docling_response": raw_blob.sha256,
                "docling_document": document_blob.sha256,
                "content_spans": spans_blob.sha256,
            }
            additional_output_bytes = 0
            attestation_sha256 = None
            if attestation is not None:
                attestation_bytes = _canonical_json_bytes(
                    attestation.model_dump(mode="json")
                )
                attestation_blob = self.store.put_blob(attestation_bytes)
                attestation_sha256 = attestation_blob.sha256
                output_digests["runtime_attestation"] = attestation_blob.sha256
                additional_output_bytes += len(attestation_bytes)
            if native_locator_bytes is not None:
                locator_blob = self.store.put_blob(native_locator_bytes)
                output_digests["native_locator_overlay"] = locator_blob.sha256
                additional_output_bytes += len(native_locator_bytes)
            if jats_alignment is not None:
                alignment_bytes = _canonical_json_bytes(
                    {
                        "algorithm": "normalized-exact-v1",
                        "aligned_count": jats_alignment.aligned_count,
                        "unaligned_count": jats_alignment.unaligned_count,
                        "records": [
                            record.to_dict() for record in jats_alignment.records
                        ],
                    }
                )
                alignment_blob = self.store.put_blob(alignment_bytes)
                output_digests["jats_locator_alignment"] = alignment_blob.sha256
                additional_output_bytes += len(alignment_bytes)
            if bioc_alignment is not None:
                alignment_bytes = _canonical_json_bytes(
                    {
                        "algorithm": "normalized-exact-v1",
                        "aligned_count": bioc_alignment.aligned_count,
                        "unaligned_count": bioc_alignment.unaligned_count,
                        "records": [
                            record.to_dict() for record in bioc_alignment.records
                        ],
                    }
                )
                alignment_blob = self.store.put_blob(alignment_bytes)
                output_digests["bioc_locator_alignment"] = alignment_blob.sha256
                additional_output_bytes += len(alignment_bytes)

            empty_output = any(
                issue.code in {"NO_TEXT_ITEMS", "NO_NONEMPTY_TEXT_ITEMS"}
                for issue in report.issues
            )
            is_partial = (
                result.is_partial
                or not report.acceptable
                or bool(provenance_warnings)
                or (
                    self.config.memory_measurement_required
                    and (
                        result.memory_measurement is None
                        or not result.memory_measurement.baseline_comparable
                    )
                )
                or bool(jats_alignment and jats_alignment.unaligned_count)
                or bool(bioc_alignment and bioc_alignment.unaligned_count)
            )
            warnings = tuple(
                [str(error) for error in result.errors]
                + [issue.message for issue in report.issues]
                + list(provenance_warnings)
                + (
                    [
                        f"{jats_alignment.unaligned_count} JATS native locators are explicitly unaligned"
                    ]
                    if jats_alignment is not None and jats_alignment.unaligned_count
                    else []
                )
                + (
                    [
                        f"{bioc_alignment.unaligned_count} BioC native locators are explicitly unaligned"
                    ]
                    if bioc_alignment is not None and bioc_alignment.unaligned_count
                    else []
                )
                + (
                    [f"remote_task_id={result.remote_task_id}"]
                    if result.remote_task_id
                    else []
                )
            )
            finished = utc_now()
            run = ProcessingRun(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                stage_id="docling",
                component=_component_descriptor(
                    "docling",
                    (
                        attestation.component_version
                        if attestation is not None
                        else self.config.docling_version
                    ),
                ),
                component_invocation_id=(
                    attestation.invocation_id if attestation is not None else None
                ),
                runtime_identity_required=self.config.require_runtime_identity,
                component_versions=component_versions,
                model_versions=(
                    dict(attestation.model_versions) if attestation is not None else {}
                ),
                model_hashes=(
                    dict(attestation.model_hashes) if attestation is not None else {}
                ),
                container_image=(
                    attestation.container_reference if attestation is not None else None
                ),
                container_digest=(
                    attestation.container_digest if attestation is not None else None
                ),
                runtime_attestation=attestation,
                runtime_attestation_sha256=attestation_sha256,
                configuration=configuration,
                configuration_sha256=config_hash,
                started_at=started,
                finished_at=finished,
                status=(
                    ProcessingRunStatus.FAILED
                    if empty_output
                    else (
                        ProcessingRunStatus.PARTIAL
                        if is_partial
                        else ProcessingRunStatus.COMPLETE
                    )
                ),
                resource_usage=ResourceUsage(
                    wall_time_seconds=time.perf_counter() - started_clock,
                    peak_memory_bytes=(
                        result.memory_measurement.peak_memory_bytes
                        if result.memory_measurement is not None
                        else None
                    ),
                    input_bytes=len(content),
                    output_bytes=sum(
                        len(value) for value in (raw_bytes, document_bytes, spans_bytes)
                    )
                    + additional_output_bytes,
                    memory_measurement=result.memory_measurement,
                ),
                warnings=warnings,
                inputs=inputs,
                outputs=self.store.data_product_refs(
                    output_digests,
                    producer_run_id=run_id,
                    source_artifact_ids=self._source_artifact_ids(artifact, inputs),
                ),
                completed_stages=("conversion", "validation", "span_generation"),
            )
            diagnostics: list[ProcessingDiagnostic] = []
            memory_diagnostic = self._memory_measurement_diagnostic(
                artifact, run, result.memory_measurement, stage="docling"
            )
            if memory_diagnostic is not None:
                diagnostics.append(memory_diagnostic)
            if provenance_warnings:
                diagnostics.append(
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.ERROR,
                        stage="runtime_provenance",
                        code="DOCLING_RUNTIME_PROVENANCE_INCOMPLETE",
                        message="; ".join(provenance_warnings),
                        details={
                            "attestation_error": result.runtime_attestation_error,
                            "attested": attestation is not None,
                            "component_versions": component_versions,
                        },
                    )
                )
            for issue in report.issues:
                diagnostics.append(
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=(
                            DiagnosticSeverity.ERROR
                            if issue.severity is QualitySeverity.ERROR
                            else DiagnosticSeverity.WARNING
                        ),
                        stage="validation",
                        code=issue.code,
                        message=issue.message,
                        item_ref=issue.item_ref,
                        page_number=issue.page_number,
                    )
                )
            if jats_alignment is not None and jats_alignment.unaligned_count:
                diagnostics.append(
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.WARNING,
                        stage="jats_locator_alignment",
                        code="JATS_LOCATORS_UNALIGNED",
                        message=(
                            f"{jats_alignment.unaligned_count} of "
                            f"{len(jats_alignment.records)} JATS native locators "
                            "could not be aligned to Docling items"
                        ),
                        details={
                            "aligned_count": jats_alignment.aligned_count,
                            "unaligned_count": jats_alignment.unaligned_count,
                        },
                    )
                )
            if bioc_alignment is not None and bioc_alignment.unaligned_count:
                diagnostics.append(
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.WARNING,
                        stage="bioc_locator_alignment",
                        code="BIOC_LOCATORS_UNALIGNED",
                        message=(
                            f"{bioc_alignment.unaligned_count} of "
                            f"{len(bioc_alignment.records)} BioC native locators "
                            "could not be aligned to Docling items"
                        ),
                        details={
                            "aligned_count": bioc_alignment.aligned_count,
                            "unaligned_count": bioc_alignment.unaligned_count,
                        },
                    )
                )
            run = self._commit_processing_run(artifact, run, tuple(diagnostics))
            self.store.delete_execution_checkpoint(checkpoint_id)
            return _DoclingStage(run, document, report, len(spans))
        except ProcessingRunCommitIncompleteError:
            raise
        except Exception as exc:
            if _docling_checkpoint_is_terminal(exc):
                self.store.delete_execution_checkpoint(checkpoint_id)
            self._save_failed_run(
                artifact,
                component_id="docling",
                component_version=self.config.docling_version,
                configuration=configuration,
                started_at=started,
                started_clock=started_clock,
                error=exc,
                runtime_identity_required=self.config.require_runtime_identity,
                inputs=inputs,
            )
            return None

    async def _run_grobid(
        self,
        artifact: DocumentArtifact,
        content: bytes,
        *,
        filename: str,
    ) -> _GrobidStage | None:
        inputs = self._source_data_products(artifact)
        configuration = {
            "input_sha256": sha256_bytes(content),
            "expected_grobid_version": self.config.grobid_version,
            "container_image": self.config.grobid_container_image,
            "container_digest": self.config.grobid_container_digest,
            "model_versions": self.config.grobid_model_versions,
            "model_hashes": self.config.grobid_model_hashes,
            "coordinates": list(self.grobid.coordinates),
            "consolidate_header": self.grobid.consolidate_header,
            "consolidate_citations": self.grobid.consolidate_citations,
            "segment_sentences": self.grobid.segment_sentences,
            "minimum_text_characters": self.config.grobid_minimum_text_characters,
        }
        reusable = self._reusable_run(artifact, "grobid", configuration)
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            tei = self.store.read_blob(
                reusable.require_output("grobid_tei").blob_sha256
            )
            return _GrobidStage(
                reusable,
                tei,
                _tei_text_length(tei) >= self.config.grobid_minimum_text_characters,
            )

        started = utc_now()
        started_clock = time.perf_counter()
        try:
            result = await self.grobid.process_fulltext(content, filename=filename)
            attestation = result.runtime_attestation
            provenance_warnings = self._runtime_attestation_warnings(
                "grobid", attestation, result.runtime_attestation_error
            )
            component_versions = (
                dict(attestation.component_versions) if attestation is not None else {}
            )
            tei_blob = self.store.put_blob(result.tei_xml)
            output_digests = {"grobid_tei": tei_blob.sha256}
            attestation_sha256 = None
            attestation_output_bytes = 0
            if attestation is not None:
                attestation_bytes = _canonical_json_bytes(
                    attestation.model_dump(mode="json")
                )
                attestation_blob = self.store.put_blob(attestation_bytes)
                attestation_sha256 = attestation_blob.sha256
                attestation_output_bytes = len(attestation_bytes)
                output_digests["runtime_attestation"] = attestation_blob.sha256
            usable = (
                _tei_text_length(result.tei_xml)
                >= self.config.grobid_minimum_text_characters
            )
            warning_message = (
                "GROBID TEI contains too little text; OCR fallback required"
            )
            warnings = (() if usable else (warning_message,)) + provenance_warnings
            finished = utc_now()
            run_id = _run_id()
            run = ProcessingRun(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                stage_id="grobid",
                component=_component_descriptor(
                    "grobid",
                    (
                        attestation.component_version
                        if attestation is not None
                        else self.config.grobid_version
                    ),
                ),
                component_invocation_id=(
                    attestation.invocation_id if attestation is not None else None
                ),
                runtime_identity_required=self.config.require_runtime_identity,
                component_versions=component_versions,
                model_versions=(
                    dict(attestation.model_versions) if attestation is not None else {}
                ),
                model_hashes=(
                    dict(attestation.model_hashes) if attestation is not None else {}
                ),
                container_image=(
                    attestation.container_reference if attestation is not None else None
                ),
                container_digest=(
                    attestation.container_digest if attestation is not None else None
                ),
                runtime_attestation=attestation,
                runtime_attestation_sha256=attestation_sha256,
                configuration=configuration,
                configuration_sha256=configuration_sha256(configuration),
                started_at=started,
                finished_at=finished,
                status=(
                    ProcessingRunStatus.COMPLETE
                    if (
                        usable
                        and not provenance_warnings
                        and (
                            not self.config.memory_measurement_required
                            or (
                                result.memory_measurement is not None
                                and result.memory_measurement.baseline_comparable
                            )
                        )
                    )
                    else ProcessingRunStatus.PARTIAL
                ),
                resource_usage=ResourceUsage(
                    wall_time_seconds=time.perf_counter() - started_clock,
                    peak_memory_bytes=(
                        result.memory_measurement.peak_memory_bytes
                        if result.memory_measurement is not None
                        else None
                    ),
                    input_bytes=len(content),
                    output_bytes=len(result.tei_xml) + attestation_output_bytes,
                    memory_measurement=result.memory_measurement,
                ),
                warnings=warnings,
                inputs=inputs,
                outputs=self.store.data_product_refs(
                    output_digests,
                    producer_run_id=run_id,
                    source_artifact_ids=self._source_artifact_ids(artifact, inputs),
                ),
                completed_stages=("fulltext_tei", "usability_validation"),
            )
            diagnostics: list[ProcessingDiagnostic] = []
            memory_diagnostic = self._memory_measurement_diagnostic(
                artifact, run, result.memory_measurement, stage="grobid"
            )
            if memory_diagnostic is not None:
                diagnostics.append(memory_diagnostic)
            if provenance_warnings:
                diagnostics.append(
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.ERROR,
                        stage="runtime_provenance",
                        code="GROBID_RUNTIME_PROVENANCE_INCOMPLETE",
                        message="; ".join(provenance_warnings),
                        details={
                            "attestation_error": result.runtime_attestation_error,
                            "attested": attestation is not None,
                            "component_versions": component_versions,
                        },
                    )
                )
            if not usable:
                diagnostics.append(
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.WARNING,
                        stage="grobid",
                        code="GROBID_TEXT_INSUFFICIENT",
                        message=warning_message,
                    )
                )
            run = self._commit_processing_run(artifact, run, tuple(diagnostics))
            return _GrobidStage(run, result.tei_xml, usable)
        except ProcessingRunCommitIncompleteError:
            raise
        except Exception as exc:
            run = self._save_failed_run(
                artifact,
                component_id="grobid",
                component_version=self.config.grobid_version,
                configuration=configuration,
                started_at=started,
                started_clock=started_clock,
                error=exc,
                runtime_identity_required=self.config.require_runtime_identity,
                inputs=inputs,
            )
            return _GrobidStage(run, None, False)

    async def _run_ocr(
        self,
        artifact: DocumentArtifact,
        content: bytes,
        *,
        fallback_reason: str,
    ) -> _OCRStage | None:
        inputs = self._source_data_products(artifact)
        configuration = {
            "input_sha256": sha256_bytes(content),
            "fallback_reason": fallback_reason,
            "expected_ocrmypdf_version": self.config.ocrmypdf_version,
            "mode": self.config.ocr_mode,
            "container_image": (
                self.config.ocr_container_image
                if self.config.ocr_mode == "container_cli"
                else None
            ),
            "container_digest": (
                self.config.ocr_container_digest
                if self.config.ocr_mode == "container_cli"
                else None
            ),
            "languages": list(
                getattr(self.ocrmypdf, "languages", self.config.ocr_languages)
            ),
            "rotate_pages": self.ocrmypdf.rotate_pages,
            "deskew": self.ocrmypdf.deskew,
            "jobs": self.ocrmypdf.jobs,
            "optimize": self.ocrmypdf.optimize,
            "skip_text": True,
            "output_type": "pdf",
        }
        reusable = self._reusable_run(artifact, "ocrmypdf", configuration)
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            derivative = self._ensure_ocr_derivative(artifact, reusable)
            return _OCRStage(reusable, derivative)

        run_id = _run_id()
        started = utc_now()
        started_clock = time.perf_counter()
        try:
            result = await self.ocrmypdf.convert(content)
            attestation = result.runtime_attestation
            provenance_warnings = self._runtime_attestation_warnings(
                "ocrmypdf", attestation, result.runtime_attestation_error
            )
            component_versions = (
                dict(attestation.component_versions) if attestation is not None else {}
            )
            pdf_blob = self.store.put_blob(result.pdf_bytes)
            sidecar_blob = self.store.put_blob(result.sidecar_text.encode("utf-8"))
            log_bytes = _canonical_json_bytes(
                {"stdout": result.stdout, "stderr": result.stderr, "exit_code": 0}
            )
            log_blob = self.store.put_blob(log_bytes)
            output_digests = {
                "searchable_pdf": pdf_blob.sha256,
                "ocr_sidecar": sidecar_blob.sha256,
                "ocr_log": log_blob.sha256,
            }
            attestation_sha256 = None
            attestation_output_bytes = 0
            if attestation is not None:
                attestation_bytes = _canonical_json_bytes(
                    attestation.model_dump(mode="json")
                )
                attestation_blob = self.store.put_blob(attestation_bytes)
                attestation_sha256 = attestation_blob.sha256
                attestation_output_bytes = len(attestation_bytes)
                output_digests["runtime_attestation"] = attestation_blob.sha256
            output_warnings = (
                ()
                if result.sidecar_text.strip()
                else ("OCRmyPDF produced an empty OCR sidecar",)
            )
            warnings = output_warnings + provenance_warnings
            run = ProcessingRun(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                stage_id="ocrmypdf",
                component=_component_descriptor(
                    "ocrmypdf",
                    (
                        attestation.component_version
                        if attestation is not None
                        else self.config.ocrmypdf_version
                    ),
                ),
                component_invocation_id=(
                    attestation.invocation_id if attestation is not None else None
                ),
                runtime_identity_required=self.config.require_runtime_identity,
                component_versions=component_versions,
                container_image=(
                    attestation.container_reference if attestation is not None else None
                ),
                container_digest=(
                    attestation.container_digest if attestation is not None else None
                ),
                runtime_attestation=attestation,
                runtime_attestation_sha256=attestation_sha256,
                configuration=configuration,
                configuration_sha256=configuration_sha256(configuration),
                started_at=started,
                finished_at=utc_now(),
                status=(
                    ProcessingRunStatus.COMPLETE
                    if (
                        not warnings
                        and (
                            not self.config.memory_measurement_required
                            or (
                                result.memory_measurement is not None
                                and result.memory_measurement.baseline_comparable
                            )
                        )
                    )
                    else ProcessingRunStatus.PARTIAL
                ),
                resource_usage=ResourceUsage(
                    wall_time_seconds=time.perf_counter() - started_clock,
                    peak_memory_bytes=(
                        result.memory_measurement.peak_memory_bytes
                        if result.memory_measurement is not None
                        else None
                    ),
                    input_bytes=len(content),
                    output_bytes=len(result.pdf_bytes)
                    + len(result.sidecar_text.encode("utf-8"))
                    + len(log_bytes)
                    + attestation_output_bytes,
                    memory_measurement=result.memory_measurement,
                ),
                warnings=warnings,
                inputs=inputs,
                outputs=self.store.data_product_refs(
                    output_digests,
                    producer_run_id=run_id,
                    source_artifact_ids=self._source_artifact_ids(artifact, inputs),
                ),
                completed_stages=(
                    "ocr_conversion",
                    "sidecar",
                    "reconstructable_derivative",
                ),
            )
            diagnostics: tuple[ProcessingDiagnostic, ...] = ()
            memory_diagnostic = self._memory_measurement_diagnostic(
                artifact, run, result.memory_measurement, stage="ocrmypdf"
            )
            if memory_diagnostic is not None:
                diagnostics = (memory_diagnostic,)
            if provenance_warnings:
                diagnostics += (
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.ERROR,
                        stage="runtime_provenance",
                        code="OCR_RUNTIME_PROVENANCE_INCOMPLETE",
                        message="; ".join(provenance_warnings),
                        details={
                            "attestation_error": result.runtime_attestation_error,
                            "attested": attestation is not None,
                            "component_versions": component_versions,
                        },
                    ),
                )
            run = self._commit_processing_run(artifact, run, diagnostics)
            derivative = self._ensure_ocr_derivative(artifact, run)
            return _OCRStage(run, derivative)
        except ProcessingRunCommitIncompleteError:
            raise
        except Exception as exc:
            run = self._save_failed_run(
                artifact,
                component_id="ocrmypdf",
                component_version=self.config.ocrmypdf_version,
                configuration=configuration,
                started_at=started,
                started_clock=started_clock,
                error=exc,
                run_id=run_id,
                runtime_identity_required=self.config.require_runtime_identity,
                inputs=inputs,
            )
            return _OCRStage(run, None)

    def _run_alignment(
        self,
        artifact: DocumentArtifact,
        docling_stage: _DoclingStage,
        grobid_run: ProcessingRun,
        tei_xml: bytes,
    ) -> tuple[ProcessingRun, ScholarlyAlignmentOverlay | None]:
        configuration = {
            "algorithm": "token-sequence-v2",
            "minimum_score": self.config.alignment_minimum_score,
            "docling_document_sha256": docling_stage.run.require_output(
                "docling_document"
            ).blob_sha256,
            "grobid_tei_sha256": sha256_bytes(tei_xml),
        }
        reusable = self._reusable_run(artifact, "docling-grobid-aligner", configuration)
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            payload = json.loads(
                self.store.read_blob(
                    reusable.require_output("alignment_overlay").blob_sha256
                )
            )
            if not isinstance(payload, dict):
                raise ValueError(
                    "persisted scholarly alignment overlay is not an object"
                )
            return reusable, ScholarlyAlignmentOverlay.from_dict(payload)

        started = utc_now()
        started_clock = time.perf_counter()
        try:
            overlay = self.aligner.align(docling_stage.document, tei_xml)
            overlay_bytes = _canonical_json_bytes(overlay.to_dict())
            overlay_blob = self.store.put_blob(overlay_bytes)
            warning_message = f"{overlay.unaligned_count} scholarly annotations are explicitly unaligned"
            warnings = (warning_message,) if overlay.unaligned_count else ()
            run_id = _run_id()
            inputs = (
                docling_stage.run.require_output("docling_document"),
                grobid_run.require_output("grobid_tei"),
            )
            run = ProcessingRun(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                stage_id="docling-grobid-aligner",
                component=_component_descriptor("docling-grobid-aligner", "2"),
                configuration=configuration,
                configuration_sha256=configuration_sha256(configuration),
                started_at=started,
                finished_at=utc_now(),
                status=ProcessingRunStatus.COMPLETE,
                resource_usage=ResourceUsage(
                    wall_time_seconds=time.perf_counter() - started_clock,
                    input_bytes=len(tei_xml),
                    output_bytes=len(overlay_bytes),
                ),
                warnings=warnings,
                inputs=inputs,
                outputs=self.store.data_product_refs(
                    {"alignment_overlay": overlay_blob.sha256},
                    producer_run_id=run_id,
                    source_artifact_ids=self._source_artifact_ids(artifact, inputs),
                ),
                completed_stages=("tei_extraction", "alignment", "unaligned_marking"),
            )
            diagnostics: tuple[ProcessingDiagnostic, ...] = ()
            if overlay.unaligned_count:
                diagnostics = (
                    self._build_diagnostic(
                        artifact,
                        run.run_id,
                        severity=DiagnosticSeverity.WARNING,
                        stage="alignment",
                        code="SCHOLARLY_ANNOTATIONS_UNALIGNED",
                        message=warning_message,
                        details={
                            "aligned_count": overlay.aligned_count,
                            "unaligned_count": overlay.unaligned_count,
                        },
                    ),
                )
            run = self._commit_processing_run(artifact, run, diagnostics)
            return run, overlay
        except ProcessingRunCommitIncompleteError:
            raise
        except Exception as exc:
            run = self._save_failed_run(
                artifact,
                component_id="docling-grobid-aligner",
                component_version="2",
                configuration=configuration,
                started_at=started,
                started_clock=started_clock,
                error=exc,
                inputs=(
                    docling_stage.run.require_output("docling_document"),
                    grobid_run.require_output("grobid_tei"),
                ),
            )
            return run, None

    def _run_content_integrity(
        self,
        artifact: DocumentArtifact,
        docling_stage: _DoclingStage,
        *,
        scholarly_overlay: ScholarlyAlignmentOverlay | None,
        scholarly_alignment_product: DataProductRef | None,
    ) -> ProcessingRun:
        """Persist explicit table, figure, and citation relationship outcomes."""

        configuration = {
            "algorithm": "explicit-content-integrity-v1",
            "docling_document_sha256": docling_stage.run.require_output(
                "docling_document"
            ).blob_sha256,
            "scholarly_alignment_sha256": (
                scholarly_alignment_product.blob_sha256
                if scholarly_alignment_product is not None
                else None
            ),
        }
        reusable = self._reusable_run(
            artifact, "docling-content-integrity", configuration
        )
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            self.store.read_blob(
                reusable.require_output("content_integrity_overlay").blob_sha256
            )
            return reusable

        started = utc_now()
        started_clock = time.perf_counter()
        try:
            if scholarly_overlay is not None and scholarly_alignment_product is None:
                raise ValueError(
                    "a scholarly overlay requires its persisted alignment product"
                )
            report = validate_content_integrity(
                docling_stage.document,
                scholarly_overlay=scholarly_overlay,
            )
            overlay_bytes = _canonical_json_bytes(report.to_dict())
            overlay_blob = self.store.put_blob(overlay_bytes)
            warnings = tuple(dict.fromkeys(issue.message for issue in report.issues))
            run_id = _run_id()
            inputs = (docling_stage.run.require_output("docling_document"),) + (
                (scholarly_alignment_product,)
                if scholarly_alignment_product is not None
                else ()
            )
            run = ProcessingRun(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                stage_id="docling-content-integrity",
                component=_component_descriptor("docling-content-integrity", "1"),
                configuration=configuration,
                configuration_sha256=configuration_sha256(configuration),
                started_at=started,
                finished_at=utc_now(),
                status=(
                    ProcessingRunStatus.PARTIAL
                    if report.issues
                    else ProcessingRunStatus.COMPLETE
                ),
                resource_usage=ResourceUsage(
                    wall_time_seconds=time.perf_counter() - started_clock,
                    input_bytes=len(_canonical_json_bytes(docling_stage.document)),
                    output_bytes=len(overlay_bytes),
                ),
                warnings=warnings,
                inputs=inputs,
                outputs=self.store.data_product_refs(
                    {"content_integrity_overlay": overlay_blob.sha256},
                    producer_run_id=run_id,
                    source_artifact_ids=self._source_artifact_ids(artifact, inputs),
                ),
                completed_stages=(
                    "enumerate_relationships",
                    "resolve_relationships",
                    "preserve_unaligned",
                ),
            )
            diagnostics = tuple(
                self._build_diagnostic(
                    artifact,
                    run.run_id,
                    severity=(
                        DiagnosticSeverity.ERROR
                        if issue.severity is QualitySeverity.ERROR
                        else DiagnosticSeverity.WARNING
                    ),
                    stage="content_integrity",
                    code=issue.code,
                    message=issue.message,
                    item_ref=issue.item_ref,
                    page_number=issue.page_number,
                )
                for issue in report.issues
            )
            return self._commit_processing_run(artifact, run, diagnostics)
        except ProcessingRunCommitIncompleteError:
            raise
        except Exception as exc:
            return self._save_failed_run(
                artifact,
                component_id="docling-content-integrity",
                component_version="1",
                configuration=configuration,
                started_at=started,
                started_clock=started_clock,
                error=exc,
                inputs=(docling_stage.run.require_output("docling_document"),)
                + (
                    (scholarly_alignment_product,)
                    if scholarly_alignment_product is not None
                    else ()
                ),
            )

    def _reusable_run(
        self,
        artifact: DocumentArtifact,
        component_id: str,
        configuration: dict[str, Any],
    ) -> ProcessingRun | None:
        config_hash = configuration_sha256(configuration)
        runs = self.store.list_processing_runs(
            artifact_id=artifact.artifact_id,
            component_id=component_id,
            configuration_sha256=config_hash,
        )
        return self._select_reusable_run(
            runs,
            statuses=frozenset(
                {ProcessingRunStatus.COMPLETE, ProcessingRunStatus.PARTIAL}
            ),
        )

    def _current_output_policy_sha256(self) -> str:
        return configuration_sha256(self._output_policy_snapshot())

    def _select_reusable_run(
        self,
        runs: tuple[ProcessingRun, ...],
        *,
        statuses: frozenset[ProcessingRunStatus],
        required_outputs: tuple[str, ...] = (),
    ) -> ProcessingRun | None:
        """Select only a terminal run produced under the exact current policy."""

        pipeline_context = _PIPELINE_CONTEXT.get()
        resume_named_forced_attempt = (
            pipeline_context is not None
            and pipeline_context.force_reprocess
            and pipeline_context.pipeline_attempt_id is not None
        )
        if (
            pipeline_context is not None
            and pipeline_context.force_reprocess
            and not resume_named_forced_attempt
        ):
            return None
        named_pipeline_run_id = (
            pipeline_context.pipeline_run_id
            if resume_named_forced_attempt and pipeline_context is not None
            else None
        )
        named_repetition_group_id = (
            pipeline_context.repetition_group_id
            if resume_named_forced_attempt and pipeline_context is not None
            else None
        )
        output_policy_sha256 = self._current_output_policy_sha256()
        return next(
            (
                run
                for run in reversed(runs)
                if run.status in statuses
                and run.output("diagnostics_manifest") is not None
                and run.output_policy_sha256 == output_policy_sha256
                and (
                    not resume_named_forced_attempt
                    or (
                        run.pipeline_run_id == named_pipeline_run_id
                        and run.repetition_group_id == named_repetition_group_id
                    )
                )
                and all(run.output(name) is not None for name in required_outputs)
            ),
            None,
        )

    def _commit_processing_run(
        self,
        artifact: DocumentArtifact,
        run: ProcessingRun,
        diagnostics: tuple[ProcessingDiagnostic, ...] = (),
    ) -> ProcessingRun:
        """Publish a run with a durable manifest, then idempotently index it."""

        if run.output("diagnostics_manifest") is not None:
            raise ValueError("processing run already contains a diagnostics manifest")
        output_policy_snapshot = self._output_policy_snapshot()
        output_policy_sha256 = configuration_sha256(output_policy_snapshot)
        if (
            run.output_policy_snapshot
            and run.output_policy_snapshot != output_policy_snapshot
        ):
            raise ValueError(
                "processing run output policy conflicts with processor policy"
            )
        if (
            run.output_policy_sha256 is not None
            and run.output_policy_sha256 != output_policy_sha256
        ):
            raise ValueError(
                "processing run output policy hash conflicts with processor policy"
            )
        manifest = ProcessingRunDiagnosticManifest(
            artifact_id=artifact.artifact_id,
            processing_run_id=run.run_id,
            diagnostics=diagnostics,
        )
        manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
        manifest_blob = self.store.put_blob(manifest_bytes)
        output_bytes = run.resource_usage.output_bytes
        run_payload = run.model_dump(mode="python")
        committed_status = run.status
        if committed_status is ProcessingRunStatus.COMPLETE and any(
            diagnostic.code == "MEMORY_MEASUREMENT_UNAVAILABLE"
            for diagnostic in diagnostics
        ):
            committed_status = ProcessingRunStatus.PARTIAL
        pipeline_context = _PIPELINE_CONTEXT.get()
        run_payload.update(
            {
                "status": committed_status,
                "pipeline_run_id": (
                    pipeline_context.pipeline_run_id
                    if pipeline_context is not None
                    else run.pipeline_run_id
                ),
                "repetition_group_id": (
                    pipeline_context.repetition_group_id
                    if pipeline_context is not None
                    else run.repetition_group_id
                ),
                "output_policy_snapshot": output_policy_snapshot,
                "output_policy_sha256": output_policy_sha256,
                "resource_usage": run.resource_usage.model_copy(
                    update={"output_bytes": (output_bytes or 0) + len(manifest_bytes)}
                ),
                "outputs": (
                    *run.outputs,
                    self.store.data_product_ref(
                        name="diagnostics_manifest",
                        blob_sha256=manifest_blob.sha256,
                        producer_run_id=run.run_id,
                        source_artifact_ids=self._source_artifact_ids(
                            artifact, run.inputs
                        ),
                    ),
                ),
            }
        )
        committed_run = ProcessingRun.model_validate(run_payload)
        self.store.save_processing_run(committed_run)
        self._reconcile_run_diagnostics(artifact, committed_run)
        return committed_run

    def _output_policy_snapshot(self) -> dict[str, Any]:
        """Return the complete, canonical static policy for this processor.

        Keep this payload free of artifact, input, and branch information. Its
        hash therefore stays identical for born-digital and scanned PDFs even
        though the latter legitimately executes OCR and extra scholarly stages.
        """

        return {
            "schema": _OUTPUT_POLICY_SCHEMA_VERSION,
            "document_processing_config": self.config.model_dump(mode="json"),
            "local_pipeline": {
                "specification": self.pipeline_spec.model_dump(
                    mode="json",
                    by_alias=True,
                ),
                "registry": self.component_registry.contract_snapshot(),
            },
            "effective_parser_options": {
                "docling": {
                    "conversion_options": self.config.docling_options,
                },
                "grobid": {
                    "coordinates": list(self.grobid.coordinates),
                    "consolidate_header": self.grobid.consolidate_header,
                    "consolidate_citations": self.grobid.consolidate_citations,
                    "include_raw_citations": True,
                    "segment_sentences": self.grobid.segment_sentences,
                },
                "ocrmypdf": {
                    "languages": list(
                        getattr(
                            self.ocrmypdf,
                            "languages",
                            self.config.ocr_languages,
                        )
                    ),
                    "rotate_pages": self.ocrmypdf.rotate_pages,
                    "deskew": self.ocrmypdf.deskew,
                    "jobs": self.ocrmypdf.jobs,
                    "optimize": self.ocrmypdf.optimize,
                    "skip_text": True,
                    "output_type": "pdf",
                },
            },
            "execution_limits": {
                "docling": {
                    "use_async_api": getattr(self.docling, "use_async_api", None),
                    "connect_timeout_seconds": getattr(
                        self.docling, "connect_timeout_seconds", None
                    ),
                    "request_timeout_seconds": getattr(
                        self.docling, "request_timeout_seconds", None
                    ),
                    "task_timeout_seconds": getattr(
                        self.docling, "task_timeout_seconds", None
                    ),
                    "poll_interval_seconds": getattr(
                        self.docling, "poll_interval_seconds", None
                    ),
                    "max_response_bytes": getattr(
                        self.docling,
                        "max_response_bytes",
                        self.config.docling_max_response_bytes,
                    ),
                },
                "grobid": {
                    "connect_timeout_seconds": getattr(
                        self.grobid, "connect_timeout_seconds", None
                    ),
                    "timeout_seconds": getattr(self.grobid, "timeout_seconds", None),
                    "max_response_bytes": getattr(
                        self.grobid,
                        "max_response_bytes",
                        self.config.grobid_max_response_bytes,
                    ),
                },
                "ocrmypdf": {
                    "timeout_seconds": getattr(self.ocrmypdf, "timeout_seconds", None),
                    "probe_timeout_seconds": getattr(
                        self.ocrmypdf, "probe_timeout_seconds", None
                    ),
                    "memory_limit": getattr(self.ocrmypdf, "memory_limit", None),
                    "cpu_limit": getattr(self.ocrmypdf, "cpu_limit", None),
                    "pids_limit": getattr(self.ocrmypdf, "pids_limit", None),
                    "read_only": getattr(self.ocrmypdf, "read_only", None),
                    "tmpfs": getattr(self.ocrmypdf, "tmpfs", None),
                },
            },
            "runtime_trust_policy": self._runtime_trust_policy(),
            "routing": {
                "algorithm_version": _OUTPUT_POLICY_ROUTING_VERSION,
                "reject_extension_only_detection": (
                    self.config.reject_extension_only_detection
                ),
            },
            "algorithms": _OUTPUT_POLICY_ALGORITHM_VERSIONS,
            "contract_schemas": _OUTPUT_POLICY_CONTRACT_SCHEMAS,
        }

    def _reconcile_run_diagnostics(
        self, artifact: DocumentArtifact, run: ProcessingRun
    ) -> tuple[ProcessingDiagnostic, ...]:
        manifest_sha256 = run.output_sha256("diagnostics_manifest")
        if manifest_sha256 is None:
            raise ValueError(f"processing run {run.run_id} has no diagnostics manifest")
        manifest = ProcessingRunDiagnosticManifest.model_validate_json(
            self.store.read_blob(manifest_sha256)
        )
        if (
            manifest.artifact_id != artifact.artifact_id
            or manifest.processing_run_id != run.run_id
        ):
            raise ValueError("diagnostics manifest does not match its processing run")
        try:
            for diagnostic in manifest.diagnostics:
                self.store.save_diagnostic(diagnostic)
        except Exception as exc:
            raise ProcessingRunCommitIncompleteError(run.run_id) from exc
        return manifest.diagnostics

    def _memory_measurement_diagnostic(
        self,
        artifact: DocumentArtifact,
        run: ProcessingRun,
        measurement: MemoryMeasurement | None,
        *,
        stage: str,
    ) -> ProcessingDiagnostic | None:
        """Make missing/failed accounting explicit when policy requires it."""

        if measurement is None and not self.config.memory_measurement_required:
            return None
        if measurement is not None and measurement.baseline_comparable:
            return None
        measured_but_noncomparable = (
            measurement is not None
            and measurement.status is MemoryMeasurementStatus.MEASURED
        )
        failure_reason = _memory_measurement_failure_reason(measurement)
        return self._build_diagnostic(
            artifact,
            run.run_id,
            severity=(
                DiagnosticSeverity.ERROR
                if self.config.memory_measurement_required
                else DiagnosticSeverity.WARNING
            ),
            stage="resource_measurement",
            code=(
                "MEMORY_MEASUREMENT_NONCOMPARABLE"
                if measured_but_noncomparable
                else "MEMORY_MEASUREMENT_UNAVAILABLE"
            ),
            message=(
                "Parser-stage peak-memory measurement is not baseline-comparable"
                if measured_but_noncomparable
                else "Parser-stage peak-memory measurement is unavailable or failed"
            ),
            details={
                "parser_stage": stage,
                "status": measurement.status.value if measurement else "missing",
                "failure_code": measurement.failure_code if measurement else None,
                "failure_reason": failure_reason,
                "baseline_comparable": False,
            },
        )

    def _save_failed_run(
        self,
        artifact: DocumentArtifact,
        *,
        component_id: str,
        component_version: str,
        configuration: dict[str, Any],
        started_at: datetime,
        started_clock: float,
        error: Exception,
        container_image: str | None = None,
        container_digest: OciDigest | None = None,
        component_versions: dict[str, str] | None = None,
        model_versions: dict[str, str] | None = None,
        model_hashes: dict[str, str] | None = None,
        runtime_identity_required: bool = False,
        run_id: str | None = None,
        inputs: tuple[DataProductRef, ...] = (),
    ) -> ProcessingRun:
        memory_measurement = getattr(error, "memory_measurement", None)
        resolved_run_id = run_id or _run_id()
        run = ProcessingRun(
            run_id=resolved_run_id,
            artifact_id=artifact.artifact_id,
            stage_id=component_id,
            component=_component_descriptor(component_id, component_version),
            runtime_identity_required=runtime_identity_required,
            component_versions=component_versions or {},
            model_versions=model_versions or {},
            model_hashes=model_hashes or {},
            container_image=container_image,
            container_digest=container_digest,
            configuration=configuration,
            configuration_sha256=configuration_sha256(configuration),
            started_at=started_at,
            finished_at=utc_now(),
            status=ProcessingRunStatus.FAILED,
            resource_usage=ResourceUsage(
                wall_time_seconds=time.perf_counter() - started_clock,
                peak_memory_bytes=(
                    memory_measurement.peak_memory_bytes
                    if memory_measurement is not None
                    else None
                ),
                input_bytes=artifact.raw_location.byte_size,
                memory_measurement=memory_measurement,
            ),
            warnings=(str(error) or error.__class__.__name__,),
            inputs=inputs,
        )
        code = (
            error.code
            if isinstance(error, ParserServiceError)
            else f"{component_id}_failed"
        )
        diagnostic = self._build_diagnostic(
            artifact,
            run.run_id,
            severity=DiagnosticSeverity.FATAL,
            stage=component_id,
            code=code,
            message=str(error) or error.__class__.__name__,
            details={
                "exception_type": error.__class__.__name__,
                "retryable": getattr(error, "retryable", False),
                "status_code": getattr(error, "status_code", None),
            },
        )
        memory_diagnostic = self._memory_measurement_diagnostic(
            artifact, run, memory_measurement, stage=component_id
        )
        return self._commit_processing_run(
            artifact,
            run,
            (diagnostic,)
            if memory_diagnostic is None
            else (diagnostic, memory_diagnostic),
        )

    def _save_diagnostic(
        self,
        artifact: DocumentArtifact,
        run: ProcessingRun,
        *,
        severity: DiagnosticSeverity,
        stage: str,
        code: str,
        message: str,
        item_ref: str | None = None,
        page_number: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> ProcessingDiagnostic:
        diagnostic = self._build_diagnostic(
            artifact,
            run.run_id,
            severity=severity,
            stage=stage,
            code=code,
            message=message,
            item_ref=item_ref,
            page_number=page_number,
            details=details,
        )
        self.store.save_diagnostic(diagnostic)
        return diagnostic

    def _build_diagnostic(
        self,
        artifact: DocumentArtifact,
        processing_run_id: str,
        *,
        severity: DiagnosticSeverity,
        stage: str,
        code: str,
        message: str,
        item_ref: str | None = None,
        page_number: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> ProcessingDiagnostic:
        normalized_code = _diagnostic_code(code)
        diagnostic_id = sha256_bytes(
            "\x1f".join(
                (processing_run_id, normalized_code, item_ref or "", message)
            ).encode("utf-8")
        )
        return ProcessingDiagnostic(
            diagnostic_id=diagnostic_id,
            artifact_id=artifact.artifact_id,
            processing_run_id=processing_run_id,
            severity=severity,
            stage=stage,
            code=normalized_code,
            message=message,
            page_number=page_number,
            item_ref=item_ref,
            remediation_status=RemediationStatus.OPEN,
            details=details or {},
        )

    def _record_terminal_router_run(
        self, artifact: DocumentArtifact, reason: str
    ) -> ProcessingRun:
        configuration = {"media_type": artifact.media_type, "router_version": "1"}
        runs = self.store.list_processing_runs(
            artifact_id=artifact.artifact_id,
            component_id="document-router",
            configuration_sha256=configuration_sha256(configuration),
        )
        reusable = self._select_reusable_run(
            runs,
            statuses=frozenset({ProcessingRunStatus.QUARANTINED}),
        )
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            return reusable
        now = utc_now()
        run_id = _run_id()
        run = ProcessingRun(
            run_id=run_id,
            artifact_id=artifact.artifact_id,
            stage_id="document-router",
            component=_component_descriptor("document-router", "1"),
            configuration=configuration,
            configuration_sha256=configuration_sha256(configuration),
            started_at=now,
            finished_at=now,
            status=ProcessingRunStatus.QUARANTINED,
            warnings=(reason,),
            completed_stages=("format_detection", "quarantine"),
        )
        diagnostic = self._build_diagnostic(
            artifact,
            run.run_id,
            severity=DiagnosticSeverity.FATAL,
            stage="routing",
            code="UNSUPPORTED_INPUT_FORMAT",
            message=reason,
        )
        return self._commit_processing_run(artifact, run, (diagnostic,))

    def _record_fallback_exhaustion_run(
        self,
        artifact: DocumentArtifact,
        *,
        docling_document_sha256: str,
        reason_codes: tuple[str, ...],
        upstream_runs: tuple[ProcessingRun, ...],
    ) -> ProcessingRun:
        """Persist an explicit terminal quarantine after all PDF fallbacks fail."""

        configuration = {
            "policy_version": "1",
            "source_sha256": artifact.source_sha256,
            "docling_document_sha256": docling_document_sha256,
            "reason_codes": list(reason_codes),
            "upstream_runs": [
                {
                    "component_id": run.component_id,
                    "configuration_sha256": run.configuration_sha256,
                    "status": run.status.value,
                    "outputs": [
                        product.model_dump(mode="json") for product in run.outputs
                    ],
                }
                for run in upstream_runs
            ],
        }
        config_hash = configuration_sha256(configuration)
        reusable = self._select_reusable_run(
            self.store.list_processing_runs(
                artifact_id=artifact.artifact_id,
                component_id="document-fallback-policy",
                configuration_sha256=config_hash,
            ),
            statuses=frozenset({ProcessingRunStatus.QUARANTINED}),
        )
        if reusable is not None:
            self._reconcile_run_diagnostics(artifact, reusable)
            return reusable

        reason_summary = ", ".join(reason_codes)
        now = utc_now()
        run_id = _run_id()
        run = ProcessingRun(
            run_id=run_id,
            artifact_id=artifact.artifact_id,
            stage_id="document-fallback-policy",
            component=_component_descriptor("document-fallback-policy", "1"),
            configuration=configuration,
            configuration_sha256=config_hash,
            started_at=now,
            finished_at=now,
            status=ProcessingRunStatus.QUARANTINED,
            warnings=(f"PDF parser fallbacks exhausted: {reason_summary}",),
            inputs=tuple(
                product
                for upstream_run in upstream_runs
                for product in upstream_run.outputs
            ),
            completed_stages=("fallback_evaluation", "quarantine"),
        )
        diagnostic = self._build_diagnostic(
            artifact,
            run.run_id,
            severity=DiagnosticSeverity.FATAL,
            stage="fallback_policy",
            code="PARSER_FALLBACK_EXHAUSTED",
            message=(
                "No acceptable PDF scholarly-parser path remained after explicit "
                f"fallback processing: {reason_summary}"
            ),
            details={"reason_codes": list(reason_codes)},
        )
        return self._commit_processing_run(artifact, run, (diagnostic,))

    def _find_derivative(
        self, parent_artifact_id: str, source_sha256: str
    ) -> DocumentArtifact | None:
        for artifact in self.store.list_artifacts():
            if (
                artifact.parent_artifact_id == parent_artifact_id
                and artifact.source_sha256 == source_sha256
                and artifact.relationship is ArtifactRelationship.DERIVATIVE
            ):
                return artifact
        return None

    def _ensure_ocr_derivative(
        self,
        parent: DocumentArtifact,
        ocr_run: ProcessingRun,
    ) -> DocumentArtifact:
        """Reconcile a derivative only after its creator run is durable."""

        source_sha256 = ocr_run.require_output("searchable_pdf").blob_sha256
        existing = self._find_derivative(parent.artifact_id, source_sha256)
        if existing is not None:
            if existing.raw_location.created_by_run_id != ocr_run.run_id:
                pipeline_context = _PIPELINE_CONTEXT.get()
                if pipeline_context is None or not pipeline_context.force_reprocess:
                    raise ArtifactMetadataConflictError(
                        "OCR derivative exists with different immutable creator lineage"
                    )
            return existing
        try:
            return self.ingest_bytes(
                self.store.read_blob(source_sha256),
                acquisition_uri=(
                    f"derived://ocrmypdf/{parent.artifact_id}/{source_sha256}"
                ),
                media_type="application/pdf",
                identifiers={"filename": "searchable.pdf"},
                relationship=ArtifactRelationship.DERIVATIVE,
                parent_artifact_id=parent.artifact_id,
                created_by_run_id=ocr_run.run_id,
            )
        except Exception as exc:
            raise ProcessingRunCommitIncompleteError(ocr_run.run_id) from exc

    def _result_after_failure(
        self,
        artifact: DocumentArtifact,
        route: Any,
        previous_run_ids: set[str],
        status: ProcessingRunStatus,
    ) -> DocumentProcessingResult:
        runs = tuple(
            run
            for run in self.store.list_processing_runs(artifact_id=artifact.artifact_id)
            if run.run_id not in previous_run_ids
        )
        return DocumentProcessingResult(
            artifact=artifact,
            status=status,
            route=tuple(stage.value for stage in route.required_stages)
            + tuple(stage.value for stage in route.conditional_stages),
            processing_runs=runs,
            diagnostics=self.store.list_diagnostics(artifact_id=artifact.artifact_id),
        )


def _memory_measurement_failure_reason(
    measurement: MemoryMeasurement | None,
) -> str:
    if measurement is None:
        return "missing"
    if measurement.status is not MemoryMeasurementStatus.MEASURED:
        return measurement.failure_code or measurement.status.value
    if not measurement.peak_memory_bytes:
        return "peak_memory_not_positive"
    if measurement.memory_events.get("oom_kill", 0) > 0:
        return "oom_kill_observed"
    if measurement.method != "cgroup-v2-memory.peak":
        return "unsupported_measurement_method"
    if not measurement.exclusive:
        return "measurement_boundary_not_exclusive"
    if measurement.shared_overhead_excluded is not True:
        return "shared_overhead_not_excluded"
    if measurement.started_at is None or measurement.finished_at is None:
        return "measurement_interval_missing"
    return "measurement_scope_not_comparable"


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _native_locator_payload(
    locators: tuple[NativeTextLocator, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "text": item.text,
            "source_kind": item.source_kind,
            "document_index": item.document_index,
            "document_id": item.document_id,
            "passage_index": item.passage_index,
            "offset": item.offset,
            "length": item.length,
            "xml_id": item.xml_id,
            "xpath": item.xpath,
            "infons": item.infons,
        }
        for item in locators
    ]


def _flatten_component_versions(value: Any, prefix: str = "") -> dict[str, str]:
    if isinstance(value, dict):
        flattened: dict[str, str] = {}
        for key in sorted(value, key=str):
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_component_versions(value[key], child_prefix))
        return flattened
    if isinstance(value, (str, int, float, bool)) and prefix:
        return {prefix: str(value)}
    if isinstance(value, str):
        return {"runtime": value}
    return {}


def _artifact_id(
    source_sha256: str,
    *,
    acquisition_uri: str,
    relationship: ArtifactRelationship,
    parent_artifact_id: str | None,
) -> str:
    identity = "\x1f".join(
        (
            source_sha256,
            acquisition_uri,
            relationship.value,
            parent_artifact_id or "",
        )
    )
    return f"artifact-{sha256_bytes(identity.encode('utf-8'))}"


def _run_id() -> str:
    return f"run-{uuid.uuid4()}"


def _optional_workflow_identifier(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _forced_pipeline_run_id(
    artifact_id: str,
    *,
    output_policy_sha256: str,
    repetition_group_id: str | None,
    pipeline_attempt_id: str,
) -> str:
    """Return the stable identity of one explicitly named forced attempt."""

    identity = configuration_sha256(
        {
            "schema": "deepcritical-forced-pipeline-attempt-v1",
            "artifact_id": artifact_id,
            "output_policy_sha256": output_policy_sha256,
            "repetition_group_id": repetition_group_id,
            "pipeline_attempt_id": pipeline_attempt_id,
        }
    )
    return f"workflow-{identity}"


def _execution_checkpoint_id(
    artifact_id: str,
    component_id: str,
    config_hash: str,
    *,
    output_policy_sha256: str,
    attempt_id: str | None = None,
) -> str:
    value = "\x1f".join(
        (
            artifact_id,
            component_id,
            config_hash,
            output_policy_sha256,
            attempt_id or "shared-recovery",
        )
    )
    return f"external-task-{sha256_bytes(value.encode('utf-8'))}"


def _checkpoint_matches_invocation(
    checkpoint: ExecutionCheckpoint,
    *,
    artifact_id: str,
    component_id: str,
    configuration_sha256: str,
    output_policy_sha256: str,
    pipeline_context: _PipelineContext | None,
) -> bool:
    """Reject a checkpoint unless every immutable invocation scope agrees."""

    if (
        checkpoint.artifact_id != artifact_id
        or checkpoint.component_id != component_id
        or checkpoint.configuration_sha256 != configuration_sha256
        or checkpoint.output_policy_sha256 != output_policy_sha256
    ):
        return False
    if pipeline_context is None or not pipeline_context.force_reprocess:
        return (
            checkpoint.repetition_group_id is None
            and checkpoint.pipeline_attempt_id is None
        )
    return (
        checkpoint.pipeline_run_id == pipeline_context.pipeline_run_id
        and checkpoint.repetition_group_id == pipeline_context.repetition_group_id
        and checkpoint.pipeline_attempt_id == pipeline_context.pipeline_attempt_id
    )


def _docling_checkpoint_is_terminal(error: Exception) -> bool:
    """Return whether retrying a persisted remote task can never make progress."""

    if not isinstance(error, ParserServiceError):
        return False
    if error.status_code == 404:
        return True
    return error.code in {
        "docling_response_too_large",
        "docling_task_failed",
        "docling_invalid_result",
        "docling_missing_document",
        "docling_invalid_json_content",
        "docling_missing_json_content",
    }


def _diagnostic_code(value: str) -> str:
    normalized = "".join(
        character if character.isalnum() else "_" for character in value.upper()
    ).strip("_")
    return normalized or "PARSER_FAILURE"


def _tei_text_length(tei_xml: bytes) -> int:
    # GROBID TEI markup is excluded; this is only an OCR fallback signal.
    from defusedxml import ElementTree

    try:
        root = ElementTree.fromstring(tei_xml)
    except ElementTree.ParseError:
        return 0
    return len(" ".join("".join(root.itertext()).split()))


def _filename_from_uri(uri: str) -> str:
    parsed = urlparse(uri)
    name = Path(unquote(parsed.path)).name
    return name or "document"


__all__ = [
    "ArtifactMetadataConflictError",
    "DocumentProcessingConfig",
    "DocumentProcessingResult",
    "DocumentProcessor",
    "ProcessingRunCommitIncompleteError",
]
