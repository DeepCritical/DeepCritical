"""Registered local stages for the reference document-processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .alignment import ScholarlyAlignmentOverlay
from .models import (
    ComponentDescriptor,
    DataProductRef,
    DocumentArtifact,
    ProcessingRun,
    ProcessingRunStatus,
    sha256_bytes,
)
from .orchestration import (
    AllCondition,
    CompiledPipeline,
    ComponentInstanceSpec,
    ComponentRegistration,
    ComponentRegistry,
    EmptyComponentConfig,
    FunctionStagePlugin,
    LocalStageExecutor,
    OutputPresentCondition,
    PipelineCompiler,
    PipelineContract,
    PipelineInputRef,
    PipelineOrchestrator,
    PipelineSpec,
    PortContract,
    StageContext,
    StageExecutionStatus,
    StageExecutor,
    StageOutputRef,
    StageResult,
    StageSpec,
)
from .preflight import PreflightDecision
from .routing import InputFormat, ProcessingStage, RouteDecision
from .validation import probably_image_only

if TYPE_CHECKING:
    from .adapters import NativeTextLocator
    from .pipeline import (
        DocumentProcessingResult,
        DocumentProcessor,
        _DoclingStage,
        _GrobidStage,
        _OCRStage,
    )


_ARTIFACT_ID_SCHEMA = PipelineContract(
    schema_uri="urn:deepcritical:document-processing:artifact-id",
    schema_version="deepcritical-artifact-id-v1",
)
_RESULT_SCHEMA = (
    "urn:deepcritical:document-processing:document-processing-result",
    "deepcritical-document-processing-result-v1",
)
_ARTIFACT_FLOW_SCHEMA = (
    "urn:deepcritical:document-processing:local-artifact-flow",
    "deepcritical-local-artifact-flow-v1",
)
_ROUTED_FLOW_SCHEMA = (
    "urn:deepcritical:document-processing:local-routed-flow",
    "deepcritical-local-routed-flow-v1",
)
_PREPARED_FLOW_SCHEMA = (
    "urn:deepcritical:document-processing:local-prepared-flow",
    "deepcritical-local-prepared-flow-v1",
)
_DOCLING_FLOW_SCHEMA = (
    "urn:deepcritical:document-processing:local-docling-flow",
    "deepcritical-local-docling-flow-v1",
)
_PRIMARY_GROBID_SCHEMA = (
    "urn:deepcritical:document-processing:local-primary-grobid-outcome",
    "deepcritical-local-primary-grobid-outcome-v1",
)
_OCR_OUTCOME_SCHEMA = (
    "urn:deepcritical:document-processing:local-ocr-outcome",
    "deepcritical-local-ocr-outcome-v1",
)
_FALLBACK_GROBID_SCHEMA = (
    "urn:deepcritical:document-processing:local-fallback-grobid-outcome",
    "deepcritical-local-fallback-grobid-outcome-v1",
)
_SCHOLARLY_FLOW_SCHEMA = (
    "urn:deepcritical:document-processing:local-scholarly-flow",
    "deepcritical-local-scholarly-flow-v1",
)
_ALIGNMENT_OUTCOME_SCHEMA = (
    "urn:deepcritical:document-processing:local-alignment-outcome",
    "deepcritical-local-alignment-outcome-v1",
)
_INTEGRITY_OUTCOME_SCHEMA = (
    "urn:deepcritical:document-processing:local-integrity-outcome",
    "deepcritical-local-integrity-outcome-v1",
)
_FINALIZABLE_FLOW_SCHEMA = (
    "urn:deepcritical:document-processing:local-finalizable-flow",
    "deepcritical-local-finalizable-flow-v1",
)


@dataclass(frozen=True, slots=True)
class _ArtifactFlow:
    artifact: DocumentArtifact
    preflight_run: ProcessingRun | None


@dataclass(frozen=True, slots=True)
class _RoutedFlow:
    artifact: DocumentArtifact
    preflight_run: ProcessingRun | None
    content: bytes
    filename: str
    route: RouteDecision
    run_ids_before: frozenset[str]


@dataclass(frozen=True, slots=True)
class _PreparedFlow:
    routed: _RoutedFlow
    parse_content: bytes
    parse_filename: str
    parse_media_type: str
    native_locators: tuple[NativeTextLocator, ...]
    docling_inputs: tuple[DataProductRef, ...]
    preprocessing_runs: tuple[ProcessingRun, ...]
    native_locator_incomplete: bool


@dataclass(frozen=True, slots=True)
class _DoclingFlow:
    prepared: _PreparedFlow
    docling_stage: _DoclingStage
    pdf_probably_image_only: bool


@dataclass(frozen=True, slots=True)
class _PrimaryGrobidOutcome:
    parsed: _DoclingFlow
    stage: _GrobidStage | None
    fallback_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _OCROutcome:
    primary: _PrimaryGrobidOutcome
    stage: _OCRStage | None
    derivative_preflight_run: ProcessingRun | None
    derivative_artifacts: tuple[DocumentArtifact, ...]
    derivative_quarantined: bool


@dataclass(frozen=True, slots=True)
class _FallbackGrobidOutcome:
    ocr: _OCROutcome
    stage: _GrobidStage | None


@dataclass(frozen=True, slots=True)
class _ScholarlyFlow:
    parsed: _DoclingFlow
    primary: _PrimaryGrobidOutcome | None
    ocr: _OCROutcome | None
    fallback: _FallbackGrobidOutcome | None
    selected_tei: bytes | None
    selected_grobid_run: ProcessingRun | None
    stage_runs: tuple[ProcessingRun, ...]
    derivative_artifacts: tuple[DocumentArtifact, ...]
    ocr_fallback_unusable: bool
    ocr_derivative_quarantined: bool


@dataclass(frozen=True, slots=True)
class _AlignmentOutcome:
    scholarly: _ScholarlyFlow
    run: ProcessingRun
    overlay: ScholarlyAlignmentOverlay | None
    alignment_sha256: str | None


@dataclass(frozen=True, slots=True)
class _IntegrityOutcome:
    scholarly: _ScholarlyFlow
    alignment: _AlignmentOutcome | None
    run: ProcessingRun
    content_integrity_sha256: str | None
    stage_runs: tuple[ProcessingRun, ...]


@dataclass(frozen=True, slots=True)
class _FinalizableFlow:
    integrity: _IntegrityOutcome
    fallback_exhaustion_run: ProcessingRun | None
    stage_runs: tuple[ProcessingRun, ...]


def _port(
    schema: tuple[str, str],
    value_type: type[Any],
    *,
    required: bool = True,
) -> PortContract:
    return PortContract(
        schema_uri=schema[0],
        schema_version=schema[1],
        value_types=value_type,
        required=required,
    )


def _descriptor(
    component_id: str,
    component_version: str,
    capability: str,
) -> ComponentDescriptor:
    return ComponentDescriptor(
        component_id=component_id,
        component_version=component_version,
        capability=capability,
    )


def _registration(
    *,
    descriptor: ComponentDescriptor,
    inputs: dict[str, PortContract],
    outputs: dict[str, PortContract],
    handler: Any,
) -> ComponentRegistration:
    return ComponentRegistration(
        descriptor=descriptor,
        configuration_model=EmptyComponentConfig,
        input_ports=inputs,
        output_ports=outputs,
        plugin=FunctionStagePlugin(handler),
    )


class _DocumentStagePlugins:
    def __init__(self, processor: DocumentProcessor) -> None:
        self.processor = processor

    async def preflight(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        from .pipeline import DocumentProcessingResult

        artifact_id = context.require_input("artifact_id", str)
        artifact = self.processor.store.get_artifact(artifact_id)
        preflight_run: ProcessingRun | None = None
        if self.processor.config.preflight_enabled:
            preflight_run, preflight = self.processor._load_or_run_preflight(artifact)
            if preflight.decision is PreflightDecision.QUARANTINE:
                return StageResult(
                    status=StageExecutionStatus.QUARANTINED,
                    outputs={
                        "result": DocumentProcessingResult(
                            artifact=artifact,
                            status=ProcessingRunStatus.QUARANTINED,
                            route=("preflight", "quarantine"),
                            processing_runs=(preflight_run,),
                            diagnostics=self.processor.store.list_diagnostics(
                                artifact_id=artifact.artifact_id
                            ),
                        )
                    },
                )
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={
                "ready": _ArtifactFlow(
                    artifact=artifact,
                    preflight_run=preflight_run,
                )
            },
        )

    async def route(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        from .pipeline import DocumentProcessingResult, _filename_from_uri

        flow = context.require_input("ready", _ArtifactFlow)
        artifact = flow.artifact
        content = self.processor.store.read_blob(artifact.source_sha256)
        filename = artifact.identifiers.get("filename") or _filename_from_uri(
            artifact.acquisition_uri
        )
        route = self.processor.router.route(
            content,
            filename=filename,
            media_type=artifact.media_type,
            ocr_enabled=self.processor.config.ocr_enabled,
            grobid_enabled=self.processor.config.grobid_enabled,
        )
        run_ids_before = frozenset(
            run.run_id
            for run in self.processor.store.list_processing_runs(
                artifact_id=artifact.artifact_id
            )
        )
        if route.required_stages == (ProcessingStage.QUARANTINE,):
            run = self.processor._record_terminal_router_run(artifact, route.reason)
            return StageResult(
                status=StageExecutionStatus.QUARANTINED,
                outputs={
                    "result": DocumentProcessingResult(
                        artifact=artifact,
                        status=ProcessingRunStatus.QUARANTINED,
                        route=tuple(stage.value for stage in route.required_stages),
                        processing_runs=(run,),
                        diagnostics=self.processor.store.list_diagnostics(
                            artifact_id=artifact.artifact_id
                        ),
                    )
                },
            )
        routed = _RoutedFlow(
            artifact=artifact,
            preflight_run=flow.preflight_run,
            content=content,
            filename=filename,
            route=route,
            run_ids_before=run_ids_before,
        )
        outputs: dict[str, object] = {"processable": routed}
        if (
            route.input_format is InputFormat.PDF
            and self.processor.config.grobid_enabled
        ):
            outputs["pdf_scholarly"] = routed
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs=outputs,
        )

    async def prepare(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        flow = context.require_input("routed", _RoutedFlow)
        artifact = flow.artifact
        route = flow.route
        parse_content = flow.content
        parse_filename = flow.filename
        parse_media_type = artifact.media_type
        native_locators: tuple[NativeTextLocator, ...] = ()
        docling_inputs = self.processor._source_data_products(artifact)
        preprocessing_runs: list[ProcessingRun] = (
            [flow.preflight_run] if flow.preflight_run is not None else []
        )
        native_locator_incomplete = False

        if route.input_format in {InputFormat.BIOC_JSON, InputFormat.BIOC_XML}:
            adapted, adapter_run = self.processor._run_bioc_adapter(
                artifact,
                flow.content,
                route.input_format,
            )
            preprocessing_runs.append(adapter_run)
            if adapted is None:
                return StageResult(
                    status=StageExecutionStatus.FAILED,
                    outputs={
                        "result": self.processor._result_after_failure(
                            artifact,
                            route,
                            set(flow.run_ids_before),
                            ProcessingRunStatus.FAILED,
                        )
                    },
                )
            parse_content = adapted.content
            parse_filename = adapted.filename
            parse_media_type = adapted.media_type
            native_locators = adapted.locator_overlay
            docling_inputs = (
                adapter_run.require_output("html_projection"),
                adapter_run.require_output("native_locator_overlay"),
            )
            native_locator_incomplete = (
                adapter_run.status is not ProcessingRunStatus.COMPLETE
            )
        elif route.input_format is InputFormat.JATS:
            native_locators, adapter_run = self.processor._run_jats_locator_adapter(
                artifact, flow.content
            )
            preprocessing_runs.append(adapter_run)
            native_locator_product = adapter_run.output("native_locator_overlay")
            if native_locator_product is not None:
                docling_inputs += (native_locator_product,)
            native_locator_incomplete = (
                adapter_run.status is not ProcessingRunStatus.COMPLETE
            )

        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={
                "prepared": _PreparedFlow(
                    routed=flow,
                    parse_content=parse_content,
                    parse_filename=parse_filename,
                    parse_media_type=parse_media_type,
                    native_locators=native_locators,
                    docling_inputs=docling_inputs,
                    preprocessing_runs=tuple(preprocessing_runs),
                    native_locator_incomplete=native_locator_incomplete,
                )
            },
        )

    async def docling(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        flow = context.require_input("prepared", _PreparedFlow)
        routed = flow.routed
        docling_stage = await self.processor._run_docling(
            routed.artifact,
            flow.parse_content,
            filename=flow.parse_filename,
            media_type=flow.parse_media_type,
            input_format=routed.route.input_format,
            native_locators=flow.native_locators,
            inputs=flow.docling_inputs,
        )
        if docling_stage is None:
            return StageResult(
                status=StageExecutionStatus.FAILED,
                outputs={
                    "result": self.processor._result_after_failure(
                        routed.artifact,
                        routed.route,
                        set(routed.run_ids_before),
                        ProcessingRunStatus.FAILED,
                    )
                },
            )
        image_only = (
            routed.route.input_format is InputFormat.PDF
            and self.processor.config.detect_image_only_pdfs
            and probably_image_only(
                docling_stage.document,
                minimum_characters_per_page=(
                    self.processor.config.minimum_text_characters_per_page
                ),
                image_only_page_ratio=self.processor.config.image_only_page_ratio,
            )
        )
        parsed = _DoclingFlow(
            prepared=flow,
            docling_stage=docling_stage,
            pdf_probably_image_only=image_only,
        )
        outputs: dict[str, object] = {"parsed": parsed}
        if image_only:
            outputs["pdf_image_only"] = parsed
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs=outputs,
        )

    async def primary_grobid(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        parsed = context.require_input("parsed", _DoclingFlow)
        routed = context.require_input("pdf", _RoutedFlow)
        grobid_stage = await self.processor._run_grobid(
            routed.artifact,
            routed.content,
            filename=routed.filename,
        )
        fallback_reasons: list[str] = []
        if parsed.pdf_probably_image_only:
            fallback_reasons.append("image_only_pages")
        if grobid_stage is None or not grobid_stage.usable:
            fallback_reasons.append("grobid_text_insufficient")
        outcome = _PrimaryGrobidOutcome(
            parsed=parsed,
            stage=grobid_stage,
            fallback_reasons=tuple(fallback_reasons),
        )
        outputs: dict[str, object] = {"outcome": outcome}
        if self.processor.config.ocr_enabled and (
            parsed.pdf_probably_image_only
            or grobid_stage is None
            or not grobid_stage.usable
        ):
            outputs["needs_ocr"] = outcome
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs=outputs,
        )

    async def ocr(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        primary = context.require_input("primary", _PrimaryGrobidOutcome)
        parsed = primary.parsed
        routed = parsed.prepared.routed
        ocr_stage = await self.processor._run_ocr(
            routed.artifact,
            routed.content,
            fallback_reason="+".join(primary.fallback_reasons),
        )
        derivative_artifacts: list[DocumentArtifact] = []
        derivative_preflight_run: ProcessingRun | None = None
        derivative_quarantined = False
        if ocr_stage is not None and ocr_stage.derivative is not None:
            derivative_artifacts.append(ocr_stage.derivative)
            if self.processor.config.preflight_enabled:
                derivative_preflight_run, derivative_preflight = (
                    self.processor._load_or_run_preflight(ocr_stage.derivative)
                )
                derivative_quarantined = not derivative_preflight.may_proceed
        outcome = _OCROutcome(
            primary=primary,
            stage=ocr_stage,
            derivative_preflight_run=derivative_preflight_run,
            derivative_artifacts=tuple(derivative_artifacts),
            derivative_quarantined=derivative_quarantined,
        )
        outputs: dict[str, object] = {"outcome": outcome}
        if (
            ocr_stage is not None
            and ocr_stage.derivative is not None
            and not derivative_quarantined
        ):
            outputs["searchable"] = outcome
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs=outputs,
        )

    async def fallback_grobid(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        ocr = context.require_input("ocr", _OCROutcome)
        if ocr.stage is None or ocr.stage.derivative is None:
            raise RuntimeError("searchable OCR output has no derivative artifact")
        derivative = ocr.stage.derivative
        searchable_pdf = self.processor.store.read_blob(derivative.source_sha256)
        stage = await self.processor._run_grobid(
            derivative,
            searchable_pdf,
            filename=f"ocr-{ocr.primary.parsed.prepared.routed.filename}",
        )
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={
                "outcome": _FallbackGrobidOutcome(
                    ocr=ocr,
                    stage=stage,
                )
            },
        )

    async def select_scholarly(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        parsed = context.require_input("parsed", _DoclingFlow)
        primary = _optional_input(context, "primary", _PrimaryGrobidOutcome)
        ocr = _optional_input(context, "ocr", _OCROutcome)
        fallback = _optional_input(
            context,
            "fallback",
            _FallbackGrobidOutcome,
        )
        selected_tei: bytes | None = None
        selected_grobid_run: ProcessingRun | None = None
        primary_stage = primary.stage if primary is not None else None
        if (
            primary_stage is not None
            and primary_stage.usable
            and not parsed.pdf_probably_image_only
        ):
            selected_tei = primary_stage.tei_xml
            selected_grobid_run = primary_stage.run
        if (
            fallback is not None
            and fallback.stage is not None
            and fallback.stage.usable
        ):
            selected_tei = fallback.stage.tei_xml
            selected_grobid_run = fallback.stage.run
        ocr_fallback_unusable = ocr is not None and selected_tei is None
        if selected_tei is None and primary_stage is not None and primary_stage.usable:
            selected_tei = primary_stage.tei_xml
            selected_grobid_run = primary_stage.run

        stage_runs = [
            *parsed.prepared.preprocessing_runs,
            parsed.docling_stage.run,
        ]
        if primary_stage is not None:
            stage_runs.append(primary_stage.run)
        if ocr is not None and ocr.stage is not None:
            stage_runs.append(ocr.stage.run)
        if ocr is not None and ocr.derivative_preflight_run is not None:
            stage_runs.append(ocr.derivative_preflight_run)
        if fallback is not None and fallback.stage is not None:
            stage_runs.append(fallback.stage.run)
        scholarly = _ScholarlyFlow(
            parsed=parsed,
            primary=primary,
            ocr=ocr,
            fallback=fallback,
            selected_tei=selected_tei,
            selected_grobid_run=selected_grobid_run,
            stage_runs=tuple(stage_runs),
            derivative_artifacts=(ocr.derivative_artifacts if ocr is not None else ()),
            ocr_fallback_unusable=ocr_fallback_unusable,
            ocr_derivative_quarantined=(
                ocr.derivative_quarantined if ocr is not None else False
            ),
        )
        outputs: dict[str, object] = {"flow": scholarly}
        if selected_tei is not None:
            outputs["selected"] = scholarly
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs=outputs,
        )

    async def align(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        scholarly = context.require_input("scholarly", _ScholarlyFlow)
        if scholarly.selected_tei is None or scholarly.selected_grobid_run is None:
            raise RuntimeError("selected scholarly TEI has no producing run")
        run, overlay = self.processor._run_alignment(
            scholarly.parsed.prepared.routed.artifact,
            scholarly.parsed.docling_stage,
            scholarly.selected_grobid_run,
            scholarly.selected_tei,
        )
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={
                "outcome": _AlignmentOutcome(
                    scholarly=scholarly,
                    run=run,
                    overlay=overlay,
                    alignment_sha256=(
                        run.output_sha256("alignment_overlay")
                        if overlay is not None
                        else None
                    ),
                )
            },
        )

    async def integrity(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        scholarly = context.require_input("scholarly", _ScholarlyFlow)
        alignment = _optional_input(context, "alignment", _AlignmentOutcome)
        alignment_product = (
            alignment.run.output("alignment_overlay")
            if alignment is not None and alignment.overlay is not None
            else None
        )
        run = self.processor._run_content_integrity(
            scholarly.parsed.prepared.routed.artifact,
            scholarly.parsed.docling_stage,
            scholarly_overlay=(alignment.overlay if alignment is not None else None),
            scholarly_alignment_product=alignment_product,
        )
        stage_runs = list(scholarly.stage_runs)
        if alignment is not None:
            stage_runs.append(alignment.run)
        stage_runs.append(run)
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={
                "outcome": _IntegrityOutcome(
                    scholarly=scholarly,
                    alignment=alignment,
                    run=run,
                    content_integrity_sha256=run.output_sha256(
                        "content_integrity_overlay"
                    ),
                    stage_runs=tuple(stage_runs),
                )
            },
        )

    async def fallback_policy(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        integrity = context.require_input("integrity", _IntegrityOutcome)
        scholarly = integrity.scholarly
        routed = scholarly.parsed.prepared.routed
        fallback_exhausted = routed.route.input_format is InputFormat.PDF and (
            scholarly.selected_tei is None
            or scholarly.ocr_fallback_unusable
            or scholarly.ocr_derivative_quarantined
        )
        fallback_run: ProcessingRun | None = None
        stage_runs = list(integrity.stage_runs)
        if (
            self.processor.config.quarantine_on_fallback_exhaustion
            and fallback_exhausted
        ):
            reason_codes: list[str] = []
            if scholarly.selected_tei is None:
                reason_codes.append("no_usable_scholarly_tei")
            if scholarly.ocr_fallback_unusable:
                reason_codes.append("ocr_grobid_fallback_unusable")
            if scholarly.ocr_derivative_quarantined:
                reason_codes.append("ocr_derivative_quarantined")
            fallback_run = self.processor._record_fallback_exhaustion_run(
                routed.artifact,
                docling_document_sha256=(
                    scholarly.parsed.docling_stage.run.require_output(
                        "docling_document"
                    ).blob_sha256
                ),
                reason_codes=tuple(reason_codes),
                upstream_runs=tuple(stage_runs),
            )
            stage_runs.append(fallback_run)
        return StageResult(
            status=StageExecutionStatus.COMPLETE,
            outputs={
                "flow": _FinalizableFlow(
                    integrity=integrity,
                    fallback_exhaustion_run=fallback_run,
                    stage_runs=tuple(stage_runs),
                )
            },
        )

    async def finalize(
        self,
        context: StageContext,
        _: BaseModel,
    ) -> StageResult:
        from .pipeline import DocumentProcessingResult

        finalizable = context.require_input("flow", _FinalizableFlow)
        integrity = finalizable.integrity
        scholarly = integrity.scholarly
        parsed = scholarly.parsed
        prepared = parsed.prepared
        routed = prepared.routed
        alignment = integrity.alignment
        if finalizable.fallback_exhaustion_run is not None:
            overall_status = ProcessingRunStatus.QUARANTINED
        else:
            overall_status = parsed.docling_stage.run.status
            if prepared.native_locator_incomplete:
                overall_status = ProcessingRunStatus.PARTIAL
            if (
                routed.route.input_format is InputFormat.PDF
                and scholarly.selected_tei is None
            ):
                overall_status = ProcessingRunStatus.PARTIAL
            if (
                scholarly.selected_grobid_run is not None
                and scholarly.selected_grobid_run.status
                is not ProcessingRunStatus.COMPLETE
            ):
                overall_status = ProcessingRunStatus.PARTIAL
            if (
                scholarly.ocr is not None
                and scholarly.ocr.stage is not None
                and scholarly.ocr.stage.run.status is not ProcessingRunStatus.COMPLETE
            ):
                overall_status = ProcessingRunStatus.PARTIAL
            if scholarly.ocr_fallback_unusable:
                overall_status = ProcessingRunStatus.PARTIAL
            if scholarly.ocr_derivative_quarantined:
                overall_status = ProcessingRunStatus.PARTIAL
            if (
                alignment is not None
                and alignment.run.status is ProcessingRunStatus.FAILED
            ):
                overall_status = ProcessingRunStatus.PARTIAL
            if integrity.run.status is not ProcessingRunStatus.COMPLETE:
                overall_status = ProcessingRunStatus.PARTIAL
            if overall_status not in {
                ProcessingRunStatus.COMPLETE,
                ProcessingRunStatus.PARTIAL,
            }:
                overall_status = ProcessingRunStatus.FAILED

        derivative_ids = {
            derivative.artifact_id for derivative in scholarly.derivative_artifacts
        }
        diagnostics = tuple(
            diagnostic
            for diagnostic in self.processor.store.list_diagnostics()
            if diagnostic.artifact_id == routed.artifact.artifact_id
            or diagnostic.artifact_id in derivative_ids
        )
        result = DocumentProcessingResult(
            artifact=routed.artifact,
            status=overall_status,
            route=tuple(stage.value for stage in routed.route.required_stages)
            + tuple(stage.value for stage in routed.route.conditional_stages),
            processing_runs=finalizable.stage_runs,
            diagnostics=diagnostics,
            docling_document_sha256=parsed.docling_stage.run.output_sha256(
                "docling_document"
            ),
            grobid_tei_sha256=(
                sha256_bytes(scholarly.selected_tei)
                if scholarly.selected_tei is not None
                else None
            ),
            alignment_sha256=(
                alignment.alignment_sha256 if alignment is not None else None
            ),
            content_integrity_sha256=integrity.content_integrity_sha256,
            content_span_count=parsed.docling_stage.content_span_count,
            derivative_artifact_ids=tuple(
                derivative.artifact_id for derivative in scholarly.derivative_artifacts
            ),
        )
        return StageResult(
            status=(
                StageExecutionStatus.QUARANTINED
                if overall_status is ProcessingRunStatus.QUARANTINED
                else StageExecutionStatus.COMPLETE
            ),
            outputs={"result": result},
        )


def _optional_input(
    context: StageContext,
    name: str,
    value_type: type[Any],
) -> Any | None:
    value = context.inputs.get(name)
    if value is None:
        return None
    if not isinstance(value, value_type):
        raise TypeError(
            f"stage {context.stage_id!r} input {name!r} is not {value_type.__name__}"
        )
    return value


def build_document_component_registry(
    processor: DocumentProcessor,
) -> ComponentRegistry:
    """Register the fixed local implementations used by the reference DAG."""

    from .pipeline import DocumentProcessingResult

    plugins = _DocumentStagePlugins(processor)
    result = _port(_RESULT_SCHEMA, DocumentProcessingResult, required=False)
    artifact_flow = _port(_ARTIFACT_FLOW_SCHEMA, _ArtifactFlow, required=False)
    routed_flow = _port(_ROUTED_FLOW_SCHEMA, _RoutedFlow, required=False)
    prepared_flow = _port(_PREPARED_FLOW_SCHEMA, _PreparedFlow, required=False)
    docling_flow = _port(_DOCLING_FLOW_SCHEMA, _DoclingFlow, required=False)
    primary = _port(
        _PRIMARY_GROBID_SCHEMA,
        _PrimaryGrobidOutcome,
        required=False,
    )
    ocr = _port(_OCR_OUTCOME_SCHEMA, _OCROutcome, required=False)
    fallback = _port(
        _FALLBACK_GROBID_SCHEMA,
        _FallbackGrobidOutcome,
        required=False,
    )
    scholarly = _port(_SCHOLARLY_FLOW_SCHEMA, _ScholarlyFlow, required=False)
    alignment = _port(
        _ALIGNMENT_OUTCOME_SCHEMA,
        _AlignmentOutcome,
        required=False,
    )
    integrity = _port(
        _INTEGRITY_OUTCOME_SCHEMA,
        _IntegrityOutcome,
        required=False,
    )
    finalizable = _port(
        _FINALIZABLE_FLOW_SCHEMA,
        _FinalizableFlow,
        required=False,
    )
    registry = ComponentRegistry()
    registrations = (
        _registration(
            descriptor=_descriptor(
                "document-preflight",
                "1",
                "document.preflight",
            ),
            inputs={
                "artifact_id": PortContract(
                    schema_uri=_ARTIFACT_ID_SCHEMA.schema_uri,
                    schema_version=_ARTIFACT_ID_SCHEMA.schema_version,
                    value_types=str,
                )
            },
            outputs={"ready": artifact_flow, "result": result},
            handler=plugins.preflight,
        ),
        _registration(
            descriptor=_descriptor("document-router", "1", "document.route"),
            inputs={
                "ready": _port(
                    _ARTIFACT_FLOW_SCHEMA,
                    _ArtifactFlow,
                )
            },
            outputs={
                "processable": routed_flow,
                "pdf_scholarly": routed_flow,
                "result": result,
            },
            handler=plugins.route,
        ),
        _registration(
            descriptor=_descriptor(
                "document-native-adapter",
                "1",
                "document.adapt",
            ),
            inputs={"routed": _port(_ROUTED_FLOW_SCHEMA, _RoutedFlow)},
            outputs={"prepared": prepared_flow, "result": result},
            handler=plugins.prepare,
        ),
        _registration(
            descriptor=_descriptor(
                "docling",
                processor.config.docling_version,
                "document.parse",
            ),
            inputs={"prepared": _port(_PREPARED_FLOW_SCHEMA, _PreparedFlow)},
            outputs={
                "parsed": docling_flow,
                "pdf_image_only": docling_flow,
                "result": result,
            },
            handler=plugins.docling,
        ),
        _registration(
            descriptor=_descriptor(
                "grobid-primary",
                processor.config.grobid_version,
                "document.parse.scholarly",
            ),
            inputs={
                "parsed": _port(_DOCLING_FLOW_SCHEMA, _DoclingFlow),
                "pdf": _port(_ROUTED_FLOW_SCHEMA, _RoutedFlow),
            },
            outputs={"outcome": primary, "needs_ocr": primary},
            handler=plugins.primary_grobid,
        ),
        _registration(
            descriptor=_descriptor(
                "ocrmypdf-fallback",
                processor.config.ocrmypdf_version,
                "document.ocr",
            ),
            inputs={
                "primary": _port(
                    _PRIMARY_GROBID_SCHEMA,
                    _PrimaryGrobidOutcome,
                )
            },
            outputs={"outcome": ocr, "searchable": ocr},
            handler=plugins.ocr,
        ),
        _registration(
            descriptor=_descriptor(
                "grobid-fallback",
                processor.config.grobid_version,
                "document.parse.scholarly",
            ),
            inputs={"ocr": _port(_OCR_OUTCOME_SCHEMA, _OCROutcome)},
            outputs={"outcome": fallback},
            handler=plugins.fallback_grobid,
        ),
        _registration(
            descriptor=_descriptor(
                "scholarly-output-selector",
                "1",
                "document.select",
            ),
            inputs={
                "parsed": _port(_DOCLING_FLOW_SCHEMA, _DoclingFlow),
                "primary": primary,
                "ocr": ocr,
                "fallback": fallback,
            },
            outputs={"flow": scholarly, "selected": scholarly},
            handler=plugins.select_scholarly,
        ),
        _registration(
            descriptor=_descriptor(
                "docling-grobid-aligner",
                "token-sequence-v2",
                "document.align",
            ),
            inputs={"scholarly": _port(_SCHOLARLY_FLOW_SCHEMA, _ScholarlyFlow)},
            outputs={"outcome": alignment},
            handler=plugins.align,
        ),
        _registration(
            descriptor=_descriptor(
                "docling-content-integrity",
                "explicit-content-integrity-v1",
                "document.validate",
            ),
            inputs={
                "scholarly": _port(_SCHOLARLY_FLOW_SCHEMA, _ScholarlyFlow),
                "alignment": alignment,
            },
            outputs={"outcome": integrity},
            handler=plugins.integrity,
        ),
        _registration(
            descriptor=_descriptor(
                "document-fallback-policy",
                "1",
                "document.route",
            ),
            inputs={
                "integrity": _port(
                    _INTEGRITY_OUTCOME_SCHEMA,
                    _IntegrityOutcome,
                )
            },
            outputs={"flow": finalizable},
            handler=plugins.fallback_policy,
        ),
        _registration(
            descriptor=_descriptor(
                "document-result",
                "1",
                "document.result",
            ),
            inputs={
                "flow": _port(
                    _FINALIZABLE_FLOW_SCHEMA,
                    _FinalizableFlow,
                )
            },
            outputs={"result": result},
            handler=plugins.finalize,
        ),
    )
    for registration in registrations:
        registry.register(registration)
    return registry


def default_document_pipeline_spec() -> PipelineSpec:
    """Return the checked-in reference graph for current document behavior."""

    component_ids = (
        "document-preflight",
        "document-router",
        "document-native-adapter",
        "docling",
        "grobid-primary",
        "ocrmypdf-fallback",
        "grobid-fallback",
        "scholarly-output-selector",
        "docling-grobid-aligner",
        "docling-content-integrity",
        "document-fallback-policy",
        "document-result",
    )
    return PipelineSpec(
        pipeline_id="deepcritical-document-processing",
        pipeline_version="1",
        inputs={"artifact_id": _ARTIFACT_ID_SCHEMA},
        components=tuple(
            ComponentInstanceSpec(
                instance_id=component_id,
                component_id=component_id,
            )
            for component_id in component_ids
        ),
        stages=(
            StageSpec(
                stage_id="preflight",
                component="document-preflight",
                inputs={
                    "artifact_id": PipelineInputRef(input_name="artifact_id"),
                },
                outputs=("ready", "result"),
            ),
            StageSpec(
                stage_id="route",
                component="document-router",
                depends_on=("preflight",),
                inputs={
                    "ready": StageOutputRef(
                        stage_id="preflight",
                        output_name="ready",
                    )
                },
                outputs=("processable", "pdf_scholarly", "result"),
                condition=OutputPresentCondition(
                    stage_id="preflight",
                    output_name="ready",
                ),
            ),
            StageSpec(
                stage_id="prepare",
                component="document-native-adapter",
                depends_on=("route",),
                inputs={
                    "routed": StageOutputRef(
                        stage_id="route",
                        output_name="processable",
                    )
                },
                outputs=("prepared", "result"),
                condition=OutputPresentCondition(
                    stage_id="route",
                    output_name="processable",
                ),
            ),
            StageSpec(
                stage_id="docling",
                component="docling",
                depends_on=("prepare",),
                inputs={
                    "prepared": StageOutputRef(
                        stage_id="prepare",
                        output_name="prepared",
                    )
                },
                outputs=("parsed", "pdf_image_only", "result"),
                condition=OutputPresentCondition(
                    stage_id="prepare",
                    output_name="prepared",
                ),
            ),
            StageSpec(
                stage_id="primary-grobid",
                component="grobid-primary",
                depends_on=("route", "docling"),
                inputs={
                    "parsed": StageOutputRef(
                        stage_id="docling",
                        output_name="parsed",
                    ),
                    "pdf": StageOutputRef(
                        stage_id="route",
                        output_name="pdf_scholarly",
                    ),
                },
                outputs=("outcome", "needs_ocr"),
                condition=AllCondition(
                    conditions=(
                        OutputPresentCondition(
                            stage_id="route",
                            output_name="pdf_scholarly",
                        ),
                        OutputPresentCondition(
                            stage_id="docling",
                            output_name="parsed",
                        ),
                    )
                ),
            ),
            StageSpec(
                stage_id="ocr",
                component="ocrmypdf-fallback",
                depends_on=("primary-grobid",),
                inputs={
                    "primary": StageOutputRef(
                        stage_id="primary-grobid",
                        output_name="needs_ocr",
                    )
                },
                outputs=("outcome", "searchable"),
                condition=OutputPresentCondition(
                    stage_id="primary-grobid",
                    output_name="needs_ocr",
                ),
            ),
            StageSpec(
                stage_id="fallback-grobid",
                component="grobid-fallback",
                depends_on=("ocr",),
                inputs={
                    "ocr": StageOutputRef(
                        stage_id="ocr",
                        output_name="searchable",
                    )
                },
                outputs=("outcome",),
                condition=OutputPresentCondition(
                    stage_id="ocr",
                    output_name="searchable",
                ),
            ),
            StageSpec(
                stage_id="select-scholarly",
                component="scholarly-output-selector",
                depends_on=("docling", "primary-grobid", "ocr", "fallback-grobid"),
                inputs={
                    "parsed": StageOutputRef(
                        stage_id="docling",
                        output_name="parsed",
                    ),
                    "primary": StageOutputRef(
                        stage_id="primary-grobid",
                        output_name="outcome",
                    ),
                    "ocr": StageOutputRef(
                        stage_id="ocr",
                        output_name="outcome",
                    ),
                    "fallback": StageOutputRef(
                        stage_id="fallback-grobid",
                        output_name="outcome",
                    ),
                },
                outputs=("flow", "selected"),
                condition=OutputPresentCondition(
                    stage_id="docling",
                    output_name="parsed",
                ),
            ),
            StageSpec(
                stage_id="alignment",
                component="docling-grobid-aligner",
                depends_on=("select-scholarly",),
                inputs={
                    "scholarly": StageOutputRef(
                        stage_id="select-scholarly",
                        output_name="selected",
                    )
                },
                outputs=("outcome",),
                condition=OutputPresentCondition(
                    stage_id="select-scholarly",
                    output_name="selected",
                ),
            ),
            StageSpec(
                stage_id="integrity",
                component="docling-content-integrity",
                depends_on=("select-scholarly", "alignment"),
                inputs={
                    "scholarly": StageOutputRef(
                        stage_id="select-scholarly",
                        output_name="flow",
                    ),
                    "alignment": StageOutputRef(
                        stage_id="alignment",
                        output_name="outcome",
                    ),
                },
                outputs=("outcome",),
                condition=OutputPresentCondition(
                    stage_id="select-scholarly",
                    output_name="flow",
                ),
            ),
            StageSpec(
                stage_id="fallback-policy",
                component="document-fallback-policy",
                depends_on=("integrity",),
                inputs={
                    "integrity": StageOutputRef(
                        stage_id="integrity",
                        output_name="outcome",
                    )
                },
                outputs=("flow",),
                condition=OutputPresentCondition(
                    stage_id="integrity",
                    output_name="outcome",
                ),
            ),
            StageSpec(
                stage_id="finalize",
                component="document-result",
                depends_on=("fallback-policy",),
                inputs={
                    "flow": StageOutputRef(
                        stage_id="fallback-policy",
                        output_name="flow",
                    )
                },
                outputs=("result",),
                condition=OutputPresentCondition(
                    stage_id="fallback-policy",
                    output_name="flow",
                ),
            ),
        ),
    )


def build_document_pipeline(
    processor: DocumentProcessor,
    *,
    pipeline_spec: PipelineSpec | None = None,
    executor: StageExecutor | None = None,
) -> tuple[
    ComponentRegistry,
    CompiledPipeline,
    PipelineOrchestrator,
]:
    registry = build_document_component_registry(processor)
    compiled = PipelineCompiler(registry).compile(
        pipeline_spec or default_document_pipeline_spec()
    )
    return (
        registry,
        compiled,
        PipelineOrchestrator(executor or LocalStageExecutor()),
    )


__all__ = [
    "build_document_component_registry",
    "build_document_pipeline",
    "default_document_pipeline_spec",
]
