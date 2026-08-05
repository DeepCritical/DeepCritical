from __future__ import annotations

import inspect
import json
import time
from io import BytesIO
from typing import Any

import pytest
from bioc import BioCCollection, BioCDocument, BioCPassage, biocjson
from pypdf import PdfWriter

from DeepResearch.src.document_processing import pipeline as pipeline_module
from DeepResearch.src.document_processing import preflight as preflight_module
from DeepResearch.src.document_processing.clients import (
    DoclingConversionResult,
    GrobidResult,
    OCRResult,
    ParserServiceError,
)
from DeepResearch.src.document_processing.document_pipeline import (
    default_document_pipeline_spec,
)
from DeepResearch.src.document_processing.models import (
    ArtifactRelationship,
    DocumentArtifact,
    MemoryMeasurement,
    MemoryMeasurementScope,
    MemoryMeasurementStatus,
    ProcessingRunStatus,
    RuntimeAttestation,
    RuntimeAttestationSource,
    sha256_bytes,
    utc_now,
)
from DeepResearch.src.document_processing.orchestration import (
    CompiledStage,
    LocalStageExecutor,
    StageContext,
    StageResult,
)
from DeepResearch.src.document_processing.pipeline import (
    ArtifactMetadataConflictError,
    DocumentProcessingConfig,
    DocumentProcessor,
    ProcessingRunCommitIncompleteError,
    SourcePreflightError,
)
from DeepResearch.src.document_processing.storage import ContentAddressedStore


def _docling_document() -> dict[str, Any]:
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "paper",
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": "#/texts/0"}, {"$ref": "#/texts/1"}],
        },
        "furniture": {"self_ref": "#/furniture", "children": []},
        "groups": [],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "section_header",
                "text": "Methods",
                "prov": [
                    {
                        "page_no": 1,
                        "bbox": {
                            "l": 10,
                            "t": 20,
                            "r": 90,
                            "b": 10,
                            "coord_origin": "BOTTOMLEFT",
                        },
                    }
                ],
            },
            {
                "self_ref": "#/texts/1",
                "label": "paragraph",
                "text": "Amyloid beta was measured in a reusable synthetic cohort.",
                "prov": [
                    {
                        "page_no": 1,
                        "bbox": {
                            "l": 10,
                            "t": 40,
                            "r": 90,
                            "b": 30,
                            "coord_origin": "BOTTOMLEFT",
                        },
                    }
                ],
            },
        ],
        "tables": [],
        "pictures": [],
        "key_value_items": [],
        "pages": {"1": {"page_no": 1}},
    }


def _usable_tei() -> bytes:
    return b"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div>
    <head coords="1,10,10,80,10">Methods</head>
    <p coords="1,10,30,80,10">Amyloid beta was measured in a reusable synthetic cohort.</p>
    <p>This deliberately long scholarly result makes the sidecar usability check pass.</p>
    </div></body></text></TEI>"""


def _encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _plain_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class FakeDocling:
    def __init__(self) -> None:
        self.calls = 0

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        self.calls += 1
        document = _docling_document()
        raw = {
            "document": {"json_content": document},
            "status": "success",
            "processing_time": 0.01,
            "timings": {},
            "errors": [],
        }
        return DoclingConversionResult(
            document=document,
            raw_response=raw,
            status="success",
            processing_time_seconds=0.01,
            remote_task_id="task-1",
        )


class OptionCapturingDocling(FakeDocling):
    def __init__(self) -> None:
        super().__init__()
        self.options: dict[str, Any] | None = None

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        self.options = dict(kwargs["options"])
        return await super().convert(*args, **kwargs)


class ImageOnlySignalDocling(FakeDocling):
    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        result = await super().convert(*args, **kwargs)
        for item in result.document["texts"]:
            item["text"] = "x"
        return result


class MeasuredDocling(FakeDocling):
    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        result = await super().convert(*args, **kwargs)
        return DoclingConversionResult(
            document=result.document,
            raw_response=result.raw_response,
            status=result.status,
            remote_task_id=result.remote_task_id,
            memory_measurement=MemoryMeasurement(
                status=MemoryMeasurementStatus.MEASURED,
                method="cgroup-v2-memory.peak",
                scope=MemoryMeasurementScope.INVOCATION_CGROUP,
                boundary="docling-rq-job",
                peak_memory_bytes=8192,
                environment_sha256="a" * 64,
                measurement_id="docling-task-1",
                started_at=utc_now(),
                finished_at=utc_now(),
                exclusive=True,
                shared_overhead_excluded=True,
                memory_events={"oom_kill": 0},
            ),
        )


class ZeroPeakDocling(FakeDocling):
    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        result = await super().convert(*args, **kwargs)
        now = utc_now()
        return DoclingConversionResult(
            document=result.document,
            raw_response=result.raw_response,
            status=result.status,
            remote_task_id=result.remote_task_id,
            memory_measurement=MemoryMeasurement(
                status=MemoryMeasurementStatus.MEASURED,
                method="cgroup-v2-memory.peak",
                scope=MemoryMeasurementScope.INVOCATION_CGROUP,
                boundary="docling-rq-job",
                peak_memory_bytes=0,
                environment_sha256="a" * 64,
                measurement_id="docling-task-zero",
                started_at=now,
                finished_at=now,
                exclusive=True,
                shared_overhead_excluded=True,
                memory_events={"oom_kill": 0},
            ),
        )


class BrokenIntegrityDocling(FakeDocling):
    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        result = await super().convert(*args, **kwargs)
        result.document["tables"] = [
            {
                "self_ref": "#/tables/0",
                "label": "table",
                "captions": [],
            }
        ]
        return result


class BrokenHierarchyDocling(FakeDocling):
    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        result = await super().convert(*args, **kwargs)
        result.document["body"]["children"].append({"$ref": "#/texts/404"})
        return result


class EmptyDocling(FakeDocling):
    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        result = await super().convert(*args, **kwargs)
        result.document["texts"] = []
        result.document["body"]["children"] = []
        return result


class FailingDocling(FakeDocling):
    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        self.calls += 1
        raise ParserServiceError(
            "encrypted or corrupt PDF",
            code="docling_encrypted_pdf",
            status_code=422,
        )


class ResumableDocling(FakeDocling):
    def __init__(self) -> None:
        super().__init__()
        self.resume_task_ids: list[str | None] = []

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        self.calls += 1
        resume_task_id = kwargs.get("resume_task_id")
        self.resume_task_ids.append(resume_task_id)
        if self.calls == 1:
            hook = kwargs["on_task_submitted"]
            hook_result = hook("remote-task-persisted")
            if inspect.isawaitable(hook_result):
                await hook_result
            raise ParserServiceError(
                "worker interrupted after submission",
                code="docling_poll_failed",
                retryable=True,
            )
        assert resume_task_id == "remote-task-persisted"
        document = _docling_document()
        raw = {
            "document": {"json_content": document},
            "status": "success",
            "processing_time": 0.01,
            "timings": {},
            "errors": [],
        }
        return DoclingConversionResult(
            document=document,
            raw_response=raw,
            status="success",
            remote_task_id=resume_task_id,
        )


class ForceIsolatedCheckpointDocling(FakeDocling):
    def __init__(self) -> None:
        super().__init__()
        self.resume_task_ids: list[str | None] = []

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        self.calls += 1
        resume_task_id = kwargs.get("resume_task_id")
        self.resume_task_ids.append(resume_task_id)
        if self.calls == 1:
            hook_result = kwargs["on_task_submitted"]("older-normal-task")
            if inspect.isawaitable(hook_result):
                await hook_result
            raise ParserServiceError(
                "normal workflow was interrupted after submission",
                code="docling_poll_failed",
                retryable=True,
            )
        assert resume_task_id is None
        document = _docling_document()
        return DoclingConversionResult(
            document=document,
            raw_response={
                "document": {"json_content": document},
                "status": "success",
                "processing_time": 0.01,
                "timings": {},
                "errors": [],
            },
            status="success",
            remote_task_id="independent-forced-task",
        )


class TerminalCheckpointDocling(FakeDocling):
    def __init__(self) -> None:
        super().__init__()
        self.resume_task_ids: list[str | None] = []

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        self.calls += 1
        resume_task_id = kwargs.get("resume_task_id")
        self.resume_task_ids.append(resume_task_id)
        if self.calls == 1:
            hook_result = kwargs["on_task_submitted"]("terminal-task")
            if inspect.isawaitable(hook_result):
                await hook_result
            raise ParserServiceError(
                "polling was interrupted",
                code="docling_poll_failed",
                retryable=True,
            )
        if self.calls == 2:
            assert resume_task_id == "terminal-task"
            raise ParserServiceError(
                "the remote task reached failure",
                code="docling_task_failed",
            )
        assert resume_task_id is None
        return await super().convert(*args, **kwargs)


class ImmediateTerminalCheckpointDocling(FakeDocling):
    def __init__(self) -> None:
        super().__init__()
        self.resume_task_ids: list[str | None] = []

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        resume_task_id = kwargs.get("resume_task_id")
        self.resume_task_ids.append(resume_task_id)
        if len(self.resume_task_ids) == 1:
            hook_result = kwargs["on_task_submitted"]("immediate-terminal-task")
            if inspect.isawaitable(hook_result):
                await hook_result
            raise ParserServiceError(
                "the newly submitted task failed",
                code="docling_task_failed",
            )
        assert resume_task_id is None
        return await super().convert(*args, **kwargs)


class OversizedResponseCheckpointDocling(FakeDocling):
    def __init__(self) -> None:
        super().__init__()
        self.resume_task_ids: list[str | None] = []

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        resume_task_id = kwargs.get("resume_task_id")
        self.resume_task_ids.append(resume_task_id)
        if len(self.resume_task_ids) == 1:
            hook_result = kwargs["on_task_submitted"]("oversized-result-task")
            if inspect.isawaitable(hook_result):
                await hook_result
            raise ParserServiceError(
                "Docling response exceeded its configured byte limit",
                code="docling_response_too_large",
                status_code=200,
            )
        assert resume_task_id is None
        return await super().convert(*args, **kwargs)


class VersionedDocling(FakeDocling):
    def __init__(self, version: str = "2.113.0") -> None:
        super().__init__()
        self.observed_version = version
        self.observed_reporter_id = "fixture-supervisor"
        self.runtime_reporter = _ExpectedRuntimeReporter("fixture-supervisor")

    async def version(self) -> dict[str, str]:
        return {
            "docling": self.observed_version,
            "docling_serve": "1.21.0",
        }

    async def convert(self, *args: Any, **kwargs: Any) -> DoclingConversionResult:
        result = await super().convert(*args, **kwargs)
        digest = "sha256:" + ("a" * 64)
        return DoclingConversionResult(
            document=result.document,
            raw_response=result.raw_response,
            status=result.status,
            processing_time_seconds=result.processing_time_seconds,
            remote_task_id=result.remote_task_id,
            runtime_attestation=RuntimeAttestation(
                component_id="docling",
                component_version=self.observed_version,
                invocation_id="task-1",
                source=(RuntimeAttestationSource.AUTHENTICATED_DEPLOYMENT_REPORTER),
                reporter_id=self.observed_reporter_id,
                observed_at=utc_now(),
                workload_id="docling-worker-1",
                container_reference=(
                    "quay.io/docling-project/docling-serve-cpu:v1.21.0@" + digest
                ),
                container_digest=digest,
                component_versions={
                    "docling": self.observed_version,
                    "docling_serve": "1.21.0",
                },
                model_versions={"layout": "1"},
                model_hashes={"layout": "b" * 64},
            ),
        )


class _ExpectedRuntimeReporter:
    def __init__(self, expected_reporter_id: str) -> None:
        self.expected_reporter_id = expected_reporter_id


class FakeGrobid:
    coordinates = (
        "persName",
        "head",
        "p",
        "s",
        "ref",
        "biblStruct",
        "figure",
        "formula",
    )
    consolidate_header = 0
    consolidate_citations = 0
    segment_sentences = True

    def __init__(self, *, scan_first: bool = False) -> None:
        self.calls = 0
        self.scan_first = scan_first

    async def process_fulltext(self, content: bytes, *, filename: str) -> GrobidResult:
        self.calls += 1
        tei = (
            b'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text/></TEI>'
            if self.scan_first and b"OCR DERIVATIVE" not in content
            else _usable_tei()
        )
        return GrobidResult(tei_xml=tei, coordinates=self.coordinates, status_code=200)


class FakeOCR:
    rotate_pages = True
    deskew = True
    jobs = 2
    optimize = 1

    def __init__(self) -> None:
        self.calls = 0

    async def convert(self, content: bytes) -> OCRResult:
        self.calls += 1
        return OCRResult(
            pdf_bytes=b"%PDF-1.7\nOCR DERIVATIVE",
            sidecar_text="Recovered OCR text",
            stdout="ok",
            stderr="",
            exit_code=0,
        )


class CorruptOCR(FakeOCR):
    async def convert(self, content: bytes) -> OCRResult:
        self.calls += 1
        return OCRResult(
            pdf_bytes=b"%PDF-1.7\ncorrupt OCR output\n%%EOF\n",
            sidecar_text="OCR text",
            stdout="",
            stderr="",
            exit_code=0,
        )


class FailingAligner:
    def align(self, *args: Any, **kwargs: Any) -> None:
        raise ValueError("synthetic alignment failure")


def _config() -> DocumentProcessingConfig:
    return DocumentProcessingConfig(
        ocr_mode="local_cli",
        grobid_minimum_text_characters=80,
        minimum_pdf_locator_coverage=0.95,
        preflight_enabled=False,
        require_runtime_identity=False,
    )


class _RecordingExecutor:
    def __init__(self) -> None:
        self.stage_ids: list[str] = []
        self.local = LocalStageExecutor()

    async def execute(
        self,
        stage: CompiledStage,
        context: StageContext,
    ) -> StageResult:
        self.stage_ids.append(stage.spec.stage_id)
        return await self.local.execute(stage, context)


class _RaiseAfterStageExecutor:
    def __init__(self, stage_id: str) -> None:
        self.stage_id = stage_id
        self.local = LocalStageExecutor()

    async def execute(
        self,
        stage: CompiledStage,
        context: StageContext,
    ) -> StageResult:
        result = await self.local.execute(stage, context)
        if stage.spec.stage_id == self.stage_id:
            raise RuntimeError(f"unexpected failure after {self.stage_id}")
        return result


@pytest.mark.asyncio
async def test_reference_flow_executes_through_the_compiled_local_dag(tmp_path) -> None:
    executor = _RecordingExecutor()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
        stage_executor=executor,
    )
    artifact = processor.ingest_bytes(
        b"<html><body>compiled local pipeline</body></html>",
        acquisition_uri="https://example.test/compiled.html",
        media_type="text/html",
        identifiers={"filename": "compiled.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.COMPLETE
    assert executor.stage_ids == [
        "preflight",
        "route",
        "prepare",
        "docling",
        "select-scholarly",
        "integrity",
        "canonicalize",
        "fallback-policy",
        "finalize",
    ]
    assert processor.component_registry.component_ids == (
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
        "canonical-document-view",
        "document-fallback-policy",
        "document-result",
    )
    canonical_run = next(
        run
        for run in result.processing_runs
        if run.component_id == "canonical-document-view"
    )
    canonical_product = canonical_run.require_output("canonical_document_view")
    canonical_view = processor.store.read_canonical_document(canonical_product)
    assert result.canonical_document_sha256 == canonical_product.blob_sha256
    assert canonical_view.artifact_id == artifact.artifact_id
    assert canonical_view.blocks
    assert {product.name for product in canonical_view.source_products} >= {
        "docling_document",
        "content_spans",
        "content_integrity_overlay",
    }
    component_spec = next(
        component
        for component in processor.pipeline_spec.components
        if component.instance_id == "canonical-document-view"
    )
    assert component_spec.configuration == {
        "anchoring_policy": "source-spans-and-native-nodes-v1",
        "text_normalization": "unicode-nfc-collapse-whitespace-v1",
    }
    assert not hasattr(processor, "_process_artifact_once_legacy")


@pytest.mark.asyncio
async def test_canonical_stage_persists_invalid_integrity_payload_as_failure(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = _RecordingExecutor()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
        stage_executor=executor,
    )
    artifact = processor.ingest_bytes(
        b"<html><body>invalid integrity payload</body></html>",
        acquisition_uri="https://example.test/invalid-integrity.html",
        media_type="text/html",
        identifiers={"filename": "invalid-integrity.html"},
    )
    original_canonicalize = processor._run_canonicalization

    def corrupt_integrity_payload(*args: Any, **kwargs: Any):
        integrity_run = kwargs["integrity_run"]
        integrity_sha256 = integrity_run.require_output(
            "content_integrity_overlay"
        ).blob_sha256
        original_read = processor.store.read_blob

        def read_blob(sha256: str) -> bytes:
            if sha256 == integrity_sha256:
                return b"[]"
            return original_read(sha256)

        monkeypatch.setattr(processor.store, "read_blob", read_blob)
        try:
            return original_canonicalize(*args, **kwargs)
        finally:
            monkeypatch.setattr(processor.store, "read_blob", original_read)

    monkeypatch.setattr(
        processor,
        "_run_canonicalization",
        corrupt_integrity_payload,
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.FAILED
    assert result.canonical_document_sha256 is None
    canonical_runs = [
        run
        for run in result.processing_runs
        if run.component_id == "canonical-document-view"
    ]
    assert len(canonical_runs) == 1
    assert canonical_runs[0].status is ProcessingRunStatus.FAILED
    assert canonical_runs[0].output("canonical_document_view") is None
    assert executor.stage_ids[-1] == "canonicalize"
    assert "fallback-policy" not in executor.stage_ids
    assert "finalize" not in executor.stage_ids


@pytest.mark.asyncio
async def test_canonical_mapping_error_is_persisted_as_partial(
    tmp_path,
) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=BrokenHierarchyDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>broken native hierarchy</body></html>",
        acquisition_uri="https://example.test/broken-hierarchy.html",
        media_type="text/html",
        identifiers={"filename": "broken-hierarchy.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    canonical_run = next(
        run
        for run in result.processing_runs
        if run.component_id == "canonical-document-view"
    )
    view = processor.store.read_canonical_document(
        canonical_run.require_output("canonical_document_view")
    )
    assert result.status is ProcessingRunStatus.PARTIAL
    assert canonical_run.status is ProcessingRunStatus.PARTIAL
    assert "UNRESOLVED_NATIVE_REFERENCE" in canonical_run.warnings
    assert any(
        diagnostic.code == "UNRESOLVED_NATIVE_REFERENCE"
        for diagnostic in view.diagnostics
    )


@pytest.mark.asyncio
async def test_unexpected_stage_failure_persists_one_failed_run(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    docling = FakeDocling()
    processor = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>unexpected route failure</body></html>",
        acquisition_uri="https://example.test/unexpected.html",
        media_type="text/html",
        identifiers={"filename": "unexpected.html"},
    )

    def unexpected_route(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("unexpected route failure")

    monkeypatch.setattr(processor.router, "route", unexpected_route)

    with pytest.raises(RuntimeError, match="unexpected route failure"):
        await processor.process_artifact(artifact.artifact_id)

    runs = store.list_processing_runs(artifact_id=artifact.artifact_id)
    assert len(runs) == 1
    failed = runs[0]
    assert failed.status is ProcessingRunStatus.FAILED
    assert failed.stage_id == "route"
    assert (
        failed.component
        == processor.component_registry.require("document-router").descriptor
    )
    assert failed.configuration == {}
    assert failed.configuration_sha256 == sha256_bytes(b"{}")
    assert failed.pipeline_run_id is not None
    assert failed.output("diagnostics_manifest") is not None
    assert docling.calls == 0


@pytest.mark.asyncio
async def test_failure_observer_does_not_duplicate_a_terminal_component_run(
    tmp_path,
) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    processor = DocumentProcessor(
        store,
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
        stage_executor=_RaiseAfterStageExecutor("docling"),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>persist then fail</body></html>",
        acquisition_uri="https://example.test/persisted.html",
        media_type="text/html",
        identifiers={"filename": "persisted.html"},
    )

    with pytest.raises(RuntimeError, match="unexpected failure after docling"):
        await processor.process_artifact(artifact.artifact_id)

    runs = store.list_processing_runs(artifact_id=artifact.artifact_id)
    assert len(runs) == 1
    assert runs[0].component_id == "docling"
    assert runs[0].status is ProcessingRunStatus.COMPLETE


@pytest.mark.asyncio
async def test_unrelated_terminal_run_does_not_hide_stage_failure(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    processor = DocumentProcessor(
        store,
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>unrelated run then route failure</body></html>",
        acquisition_uri="https://example.test/unrelated-run.html",
        media_type="text/html",
        identifiers={"filename": "unrelated-run.html"},
    )

    def persist_unrelated_then_fail(*args: Any, **kwargs: Any) -> None:
        unrelated_error = RuntimeError("unrelated terminal failure")
        processor._save_failed_run(
            artifact,
            component_id="unrelated-component",
            component_version="1",
            stage_id="unrelated-stage",
            configuration={},
            started_at=utc_now(),
            started_clock=time.perf_counter(),
            error=unrelated_error,
        )
        raise RuntimeError("unexpected route failure")

    monkeypatch.setattr(processor.router, "route", persist_unrelated_then_fail)

    with pytest.raises(RuntimeError, match="unexpected route failure"):
        await processor.process_artifact(artifact.artifact_id)

    runs = store.list_processing_runs(artifact_id=artifact.artifact_id)
    assert len(runs) == 2
    by_stage = {run.stage_id: run for run in runs}
    assert by_stage["unrelated-stage"].component_id == "unrelated-component"
    assert by_stage["unrelated-stage"].status is ProcessingRunStatus.FAILED
    assert by_stage["route"].component_id == "document-router"
    assert by_stage["route"].status is ProcessingRunStatus.FAILED
    assert (
        by_stage["route"].pipeline_run_id == by_stage["unrelated-stage"].pipeline_run_id
    )


@pytest.mark.asyncio
async def test_pipeline_specification_is_part_of_reuse_identity(tmp_path) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    first_docling = FakeDocling()
    first = DocumentProcessor(
        store,
        docling=first_docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    content = b"<html><body>pipeline identity</body></html>"
    artifact = first.ingest_bytes(
        content,
        acquisition_uri="https://example.test/pipeline-identity.html",
        media_type="text/html",
        identifiers={"filename": "pipeline-identity.html"},
    )
    first_result = await first.process_artifact(artifact.artifact_id)

    changed_docling = FakeDocling()
    changed = DocumentProcessor(
        store,
        docling=changed_docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
        pipeline_spec=default_document_pipeline_spec().model_copy(
            update={"pipeline_version": "3"}
        ),
    )
    second_result = await changed.process_artifact(artifact.artifact_id)

    assert first_docling.calls == 1
    assert changed_docling.calls == 1
    assert (
        first_result.processing_runs[0].output_policy_sha256
        != second_result.processing_runs[0].output_policy_sha256
    )


@pytest.mark.asyncio
async def test_docling_effective_options_are_sent_and_persisted(tmp_path) -> None:
    docling = OptionCapturingDocling()
    config = DocumentProcessingConfig(
        docling_options={"to_formats": ["json"], "do_ocr": False},
        docling_max_response_bytes=12_345,
        grobid_max_response_bytes=67_890,
        ocr_mode="local_cli",
        preflight_enabled=False,
        require_runtime_identity=False,
    )
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=config,
    )
    artifact = processor.ingest_bytes(
        b"<html><body>effective Docling options</body></html>",
        acquisition_uri="https://example.test/effective-options.html",
        media_type="text/html",
        identifiers={"filename": "effective-options.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)
    run = next(run for run in result.processing_runs if run.component_id == "docling")
    expected = {
        "to_formats": ["json"],
        "image_export_mode": "embedded",
        "do_ocr": False,
        "table_mode": "accurate",
    }

    assert config.docling_options == expected
    assert docling.options == expected
    assert run.configuration["options"] == expected
    assert (
        run.output_policy_snapshot["document_processing_config"]["docling_options"]
        == expected
    )
    assert (
        run.output_policy_snapshot["effective_parser_options"]["docling"][
            "conversion_options"
        ]
        == expected
    )
    assert (
        run.output_policy_snapshot["document_processing_config"][
            "docling_max_response_bytes"
        ]
        == 12_345
    )
    assert (
        run.output_policy_snapshot["document_processing_config"][
            "grobid_max_response_bytes"
        ]
        == 67_890
    )
    assert (
        run.output_policy_snapshot["execution_limits"]["docling"]["max_response_bytes"]
        == 12_345
    )
    assert (
        run.output_policy_snapshot["execution_limits"]["grobid"]["max_response_bytes"]
        == 67_890
    )


@pytest.mark.asyncio
async def test_pipeline_persists_trusted_docling_memory_measurement(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=MeasuredDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body><p>Measured parser document</p></body></html>",
        acquisition_uri="https://example.test/measured.html",
        media_type="text/html",
    )

    result = await processor.process_artifact(artifact.artifact_id)
    run = next(run for run in result.processing_runs if run.component_id == "docling")

    assert run.resource_usage.peak_memory_bytes == 8192
    assert run.resource_usage.memory_measurement is not None
    assert run.resource_usage.memory_measurement.boundary == "docling-rq-job"


@pytest.mark.asyncio
async def test_pipeline_records_unavailable_memory_only_when_policy_requires_it(
    tmp_path,
) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(
            ocr_mode="local_cli",
            preflight_enabled=False,
            require_runtime_identity=False,
            memory_measurement_required=True,
        ),
    )
    artifact = processor.ingest_bytes(
        b"<html><body><p>Unmetered parser document</p></body></html>",
        acquisition_uri="https://example.test/unmetered.html",
        media_type="text/html",
    )

    result = await processor.process_artifact(artifact.artifact_id)
    docling_run = next(
        run for run in result.processing_runs if run.component_id == "docling"
    )

    assert any(
        diagnostic.code == "MEMORY_MEASUREMENT_UNAVAILABLE"
        for diagnostic in result.diagnostics
    )
    assert docling_run.status is ProcessingRunStatus.PARTIAL


@pytest.mark.asyncio
async def test_required_zero_peak_memory_is_noncomparable_and_partial(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=ZeroPeakDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(
            ocr_mode="local_cli",
            preflight_enabled=False,
            require_runtime_identity=False,
            memory_measurement_required=True,
        ),
    )
    artifact = processor.ingest_bytes(
        b"<html><body><p>Zero is not a measured peak.</p></body></html>",
        acquisition_uri="https://example.test/zero-memory.html",
        media_type="text/html",
    )

    result = await processor.process_artifact(artifact.artifact_id)
    run = next(
        item for item in result.processing_runs if item.component_id == "docling"
    )
    diagnostic = next(
        item
        for item in result.diagnostics
        if item.code == "MEMORY_MEASUREMENT_NONCOMPARABLE"
    )

    assert run.status is ProcessingRunStatus.PARTIAL
    assert diagnostic.details["failure_reason"] == "peak_memory_not_positive"


def test_reingest_rejects_conflicting_immutable_metadata(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    content = b"%PDF-1.7\nSAME BYTES"
    common = {
        "acquisition_uri": "https://example.test/paper.pdf",
        "media_type": "application/pdf",
    }
    processor.ingest_bytes(content, identifiers={"pmcid": "PMC1"}, **common)

    with pytest.raises(ArtifactMetadataConflictError, match="different immutable"):
        processor.ingest_bytes(content, identifiers={"pmcid": "PMC2"}, **common)


@pytest.mark.asyncio
async def test_pipeline_quarantines_encrypted_pdf_before_parser_submission(
    tmp_path,
) -> None:
    docling = FakeDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(ocr_mode="local_cli"),
    )
    artifact = processor.ingest_bytes(
        _encrypted_pdf(),
        acquisition_uri="https://example.test/encrypted-preflight.pdf",
        media_type="application/pdf",
        identifiers={"filename": "encrypted-preflight.pdf"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.QUARANTINED
    assert result.route == ("preflight", "quarantine")
    assert result.processing_runs[0].component_id == "document-preflight"
    assert any(diagnostic.code == "PDF_ENCRYPTED" for diagnostic in result.diagnostics)
    assert docling.calls == 0


def test_oversized_bytes_get_bounded_quarantine_without_storing_source(
    tmp_path,
) -> None:
    docling = FakeDocling()
    store = ContentAddressedStore(tmp_path / "store")
    processor = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(
            ocr_mode="local_cli",
            max_source_bytes=8,
        ),
    )
    content = b"123456789"

    with pytest.raises(SourcePreflightError) as error:
        processor.ingest_bytes(
            content,
            acquisition_uri="https://example.test/oversized.bin",
            media_type="application/octet-stream",
            identifiers={"filename": "oversized.bin"},
        )

    assert error.value.result.diagnostics[0].code == "SOURCE_TOO_LARGE"
    assert store.list_artifacts() == ()
    records = store.list_intake_quarantines()
    assert records == (error.value.quarantine_record,)
    assert records[0].source_path == (
        "bytes-sha256:15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225"
    )
    assert not store.blob_path(sha256_bytes(content)).exists()
    assert docling.calls == 0


def test_oversized_path_gets_bounded_quarantine_without_storing_source(
    tmp_path,
) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    processor = DocumentProcessor(
        store,
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(
            ocr_mode="local_cli",
            max_source_bytes=8,
        ),
    )
    source = tmp_path / "oversized.bin"
    source.write_bytes(b"123456789")

    with pytest.raises(SourcePreflightError) as error:
        processor.ingest_path(source)

    assert error.value.result.diagnostics[0].code == "SOURCE_TOO_LARGE"
    assert store.list_artifacts() == ()
    records = store.list_intake_quarantines()
    assert records == (error.value.quarantine_record,)
    assert records[0].observed_byte_size == 9
    assert records[0].reason_codes == ("SOURCE_TOO_LARGE",)
    assert store.read_blob(records[0].preflight_result_sha256)
    assert not store.blob_path(
        "15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225"
    ).exists()

    # Rewriting an existing file makes Windows lstat/fstat disagree about
    # st_ctime_ns even when no process changes the file between open and read.
    # Repeated intake must preserve the real size diagnostic rather than report
    # that API-level metadata difference as a source swap.
    for _ in range(20):
        source.write_bytes(b"123456789")
        with pytest.raises(SourcePreflightError) as repeated_error:
            processor.ingest_path(source)
        assert repeated_error.value.result.diagnostics[0].code == "SOURCE_TOO_LARGE"
        assert repeated_error.value.quarantine_record == records[0]

    assert store.list_intake_quarantines() == records


def test_ingest_path_rejects_a_descriptor_that_changes_during_snapshot(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    processor = DocumentProcessor(
        store,
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(ocr_mode="local_cli"),
    )
    source = tmp_path / "changing.html"
    content = b"<html><body>stable descriptor fixture</body></html>"
    source.write_bytes(content)
    real_signature = preflight_module._source_snapshot_signature
    calls = 0

    def drift_on_final_stat(value: Any) -> tuple[int, ...]:
        nonlocal calls
        calls += 1
        signature = real_signature(value)
        if calls == 4:
            return (*signature[:-1], signature[-1] + 1)
        return signature

    monkeypatch.setattr(
        preflight_module, "_source_snapshot_signature", drift_on_final_stat
    )

    with pytest.raises(SourcePreflightError) as error:
        processor.ingest_path(source)

    assert error.value.result.diagnostics[0].code == "SOURCE_SNAPSHOT_CHANGED"
    assert store.list_artifacts() == ()
    assert not store.blob_path(sha256_bytes(content)).exists()
    assert store.list_intake_quarantines() == (error.value.quarantine_record,)


@pytest.mark.asyncio
async def test_expected_runtime_config_not_transient_probe_controls_reuse(
    tmp_path,
) -> None:
    docling = VersionedDocling()
    config = DocumentProcessingConfig(
        preflight_enabled=False,
        ocr_mode="local_cli",
        docling_container_digest="sha256:" + ("a" * 64),
        docling_model_versions={"layout": "1"},
        docling_model_hashes={"layout": "b" * 64},
    )
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=config,
    )
    artifact = processor.ingest_bytes(
        b"<html><body>runtime identity</body></html>",
        acquisition_uri="https://example.test/runtime.html",
        media_type="text/html",
        identifiers={"filename": "runtime.html"},
    )

    first = await processor.process_artifact(artifact.artifact_id)
    second = await processor.process_artifact(artifact.artifact_id)
    docling.observed_version = "2.114.0"
    third = await processor.process_artifact(artifact.artifact_id)

    upgraded = DocumentProcessor(
        processor.store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=config.model_copy(update={"docling_version": "2.114.0"}),
    )
    fourth = await upgraded.process_artifact(artifact.artifact_id)

    assert first.status is ProcessingRunStatus.COMPLETE
    assert second.status is ProcessingRunStatus.COMPLETE
    assert third.status is ProcessingRunStatus.COMPLETE
    assert fourth.status is ProcessingRunStatus.COMPLETE
    assert docling.calls == 2
    first_docling_run = next(
        run for run in first.processing_runs if run.component_id == "docling"
    )
    third_docling_run = next(
        run for run in third.processing_runs if run.component_id == "docling"
    )
    fourth_docling_run = next(
        run for run in fourth.processing_runs if run.component_id == "docling"
    )
    assert first_docling_run.component_versions["docling"] == "2.113.0"
    assert first_docling_run.runtime_attestation is not None
    assert (
        first_docling_run.component_invocation_id
        == first_docling_run.runtime_attestation.invocation_id
    )
    processor.store.verify_blob(first_docling_run.runtime_attestation_sha256 or "")
    assert third_docling_run.run_id == first_docling_run.run_id
    assert fourth_docling_run.component_versions["docling"] == "2.114.0"


@pytest.mark.asyncio
async def test_runtime_reporter_trust_drift_prevents_cross_policy_reuse(
    tmp_path,
) -> None:
    docling = VersionedDocling()
    config = DocumentProcessingConfig(
        preflight_enabled=False,
        ocr_mode="local_cli",
        docling_container_digest="sha256:" + ("a" * 64),
        docling_model_versions={"layout": "1"},
        docling_model_hashes={"layout": "b" * 64},
    )
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=config,
    )
    artifact = processor.ingest_bytes(
        b"<html><body>runtime reporter trust drift</body></html>",
        acquisition_uri="https://example.test/runtime-reporter.html",
        media_type="text/html",
        identifiers={"filename": "runtime-reporter.html"},
    )

    first = await processor.process_artifact(artifact.artifact_id)
    docling.runtime_reporter.expected_reporter_id = "replacement-supervisor"
    docling.observed_reporter_id = "replacement-supervisor"
    second = await processor.process_artifact(artifact.artifact_id)

    first_run = next(
        run for run in first.processing_runs if run.component_id == "docling"
    )
    second_run = next(
        run for run in second.processing_runs if run.component_id == "docling"
    )
    assert first.status is ProcessingRunStatus.COMPLETE
    assert second.status is ProcessingRunStatus.COMPLETE
    assert docling.calls == 2
    assert first_run.run_id != second_run.run_id
    assert first_run.output_policy_sha256 != second_run.output_policy_sha256
    assert first_run.output_policy_snapshot["runtime_trust_policy"]["docling"] == {
        "reporter_configured": True,
        "expected_reporter_id": "fixture-supervisor",
        "expected_source": "authenticated_deployment_reporter",
        "attestation_contract_version": (
            "deepcritical-authenticated-runtime-attestation-reporter-v1"
        ),
        "attestation_schema_version": "deepcritical-runtime-attestation-v1",
    }


def test_runtime_attestation_requires_exact_canonical_component_names(
    tmp_path,
) -> None:
    docling = VersionedDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(
            ocr_mode="local_cli",
            docling_container_digest="sha256:" + ("a" * 64),
            docling_model_versions={"layout": "1"},
            docling_model_hashes={"layout": "b" * 64},
        ),
    )
    digest = "sha256:" + ("a" * 64)
    spoofed = RuntimeAttestation(
        component_id="docling",
        component_version="2.113.0",
        invocation_id="task-spoofed-components",
        source=RuntimeAttestationSource.AUTHENTICATED_DEPLOYMENT_REPORTER,
        reporter_id="fixture-supervisor",
        observed_at=utc_now(),
        workload_id="docling-worker-spoofed",
        container_reference=(
            "quay.io/docling-project/docling-serve-cpu:v1.21.0@" + digest
        ),
        container_digest=digest,
        component_versions={
            "unrelated": "docling 2.113.0",
            "docling_serve": "1.21.0-compatible",
        },
        model_versions={"layout": "1"},
        model_hashes={"layout": "b" * 64},
    )

    warnings = processor._runtime_attestation_warnings("docling", spoofed, None)

    assert any("component 'docling'" in warning for warning in warnings)
    assert any("component 'docling_serve'" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_configured_runtime_identity_is_not_treated_as_observed(tmp_path) -> None:
    config = DocumentProcessingConfig(
        preflight_enabled=False,
        ocr_mode="local_cli",
        docling_container_digest="sha256:" + ("a" * 64),
        docling_model_versions={"layout": "1"},
        docling_model_hashes={"layout": "b" * 64},
        require_runtime_identity=True,
    )
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=config,
    )
    artifact = processor.ingest_bytes(
        b"<html><body>configured identity is only an expectation</body></html>",
        acquisition_uri="https://example.test/unattested.html",
        media_type="text/html",
        identifiers={"filename": "unattested.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)
    run = next(
        item for item in result.processing_runs if item.component_id == "docling"
    )

    assert run.status is ProcessingRunStatus.PARTIAL
    assert run.runtime_attestation is None
    assert run.container_digest is None
    assert run.model_hashes == {}
    assert any(
        diagnostic.code == "DOCLING_RUNTIME_PROVENANCE_INCOMPLETE"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_effective_client_option_drift_prevents_cross_policy_reuse(
    tmp_path,
) -> None:
    store = ContentAddressedStore(tmp_path / "store")
    docling = FakeDocling()
    config = _config().model_copy(update={"preflight_enabled": True})
    first_ocr = FakeOCR()
    first = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=first_ocr,
        config=config,
    )
    artifact = first.ingest_bytes(
        b"<html><body>policy drift</body></html>",
        acquisition_uri="https://example.test/policy-drift.html",
        media_type="text/html",
        identifiers={"filename": "policy-drift.html"},
    )
    first_result = await first.process_artifact(artifact.artifact_id)
    changed_ocr = FakeOCR()
    changed_ocr.jobs = 3
    changed = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=changed_ocr,
        config=config,
    )

    second_result = await changed.process_artifact(artifact.artifact_id)
    first_run = next(
        run for run in first_result.processing_runs if run.component_id == "docling"
    )
    second_run = next(
        run for run in second_result.processing_runs if run.component_id == "docling"
    )

    assert docling.calls == 2
    assert first_run.run_id != second_run.run_id
    assert first_run.output_policy_sha256 != second_run.output_policy_sha256
    current_policy = second_run.output_policy_sha256
    assert current_policy is not None
    second_preflight = next(
        run
        for run in second_result.processing_runs
        if run.component_id == "document-preflight"
    )
    assert second_preflight.output_policy_sha256 == current_policy
    assert second_preflight.run_id not in {
        run.run_id for run in first_result.processing_runs
    }


@pytest.mark.asyncio
async def test_parser_container_images_are_part_of_reuse_identity(tmp_path) -> None:
    docling = FakeDocling()
    grobid = FakeGrobid()
    config = _config()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=grobid,
        ocrmypdf=FakeOCR(),
        config=config,
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nCONTAINER IDENTITY",
        acquisition_uri="https://example.test/container-identity.pdf",
        media_type="application/pdf",
        identifiers={"filename": "container-identity.pdf"},
    )

    first = await processor.process_artifact(artifact.artifact_id)
    changed = DocumentProcessor(
        processor.store,
        docling=docling,
        grobid=grobid,
        ocrmypdf=FakeOCR(),
        config=config.model_copy(
            update={
                "docling_container_image": "example/docling:changed",
                "grobid_container_image": "example/grobid:changed",
            }
        ),
    )
    second = await changed.process_artifact(artifact.artifact_id)

    assert first.status is ProcessingRunStatus.COMPLETE
    assert second.status is ProcessingRunStatus.COMPLETE
    assert docling.calls == 2
    assert grobid.calls == 2


@pytest.mark.asyncio
async def test_missing_runtime_provenance_is_explicitly_partial(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=DocumentProcessingConfig(
            preflight_enabled=False,
            ocr_mode="local_cli",
        ),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>missing identity</body></html>",
        acquisition_uri="https://example.test/missing-identity.html",
        media_type="text/html",
        identifiers={"filename": "missing-identity.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.PARTIAL
    assert any(
        diagnostic.code == "DOCLING_RUNTIME_PROVENANCE_INCOMPLETE"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_pipeline_persists_outputs_and_resumes_completed_stages(tmp_path) -> None:
    docling = FakeDocling()
    grobid = FakeGrobid()
    ocr = FakeOCR()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=grobid,
        ocrmypdf=ocr,
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nBORN DIGITAL",
        acquisition_uri="https://example.test/paper.pdf",
        media_type="application/pdf",
        identifiers={"filename": "paper.pdf"},
    )

    first = await processor.process_artifact(artifact.artifact_id)
    assert first.status is ProcessingRunStatus.COMPLETE
    assert first.docling_document_sha256
    assert first.grobid_tei_sha256
    assert first.alignment_sha256
    assert first.content_integrity_sha256
    assert first.canonical_document_sha256
    assert first.content_span_count == 2
    assert {run.component_id for run in first.processing_runs} >= {
        "docling",
        "grobid",
        "docling-grobid-aligner",
        "docling-content-integrity",
        "canonical-document-view",
    }
    policy_hashes = {run.output_policy_sha256 for run in first.processing_runs}
    assert len(policy_hashes) == 1
    assert None not in policy_hashes
    assert all(
        run.output_policy_snapshot["schema"] == "deepcritical-document-output-policy-v2"
        for run in first.processing_runs
    )
    assert all(
        run.output_policy_snapshot["local_pipeline"]["specification"]
        == processor.pipeline_spec.model_dump(mode="json", by_alias=True)
        for run in first.processing_runs
    )
    assert docling.calls == 1
    assert grobid.calls == 1
    assert ocr.calls == 0

    processor.aligner = FailingAligner()
    second = await processor.process_artifact(artifact.artifact_id)
    assert second.status is ProcessingRunStatus.COMPLETE
    assert second.docling_document_sha256 == first.docling_document_sha256
    assert second.alignment_sha256 == first.alignment_sha256
    assert second.content_integrity_sha256 == first.content_integrity_sha256
    assert second.canonical_document_sha256 == first.canonical_document_sha256
    assert {run.component_id for run in second.processing_runs} >= {
        "docling",
        "grobid",
        "docling-grobid-aligner",
        "docling-content-integrity",
        "canonical-document-view",
    }
    assert docling.calls == 1
    assert grobid.calls == 1
    assert ocr.calls == 0


@pytest.mark.asyncio
async def test_forced_benchmark_workflows_are_independent_and_pairable(
    tmp_path,
) -> None:
    docling = FakeDocling()
    grobid = FakeGrobid(scan_first=True)
    ocr = FakeOCR()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=grobid,
        ocrmypdf=ocr,
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nBENCHMARK REPEAT",
        acquisition_uri="https://example.test/benchmark-repeat.pdf",
        media_type="application/pdf",
        identifiers={"filename": "benchmark-repeat.pdf"},
    )

    first = await processor.process_artifact(
        artifact.artifact_id,
        force_reprocess=True,
        repetition_group_id="benchmark-pmc-v1",
        pipeline_attempt_id="attempt-1",
    )
    second = await processor.process_artifact(
        artifact.artifact_id,
        force_reprocess=True,
        repetition_group_id="benchmark-pmc-v1",
        pipeline_attempt_id="attempt-2",
    )

    assert first.status is ProcessingRunStatus.COMPLETE
    assert second.status is ProcessingRunStatus.COMPLETE
    first_workflows = {run.pipeline_run_id for run in first.processing_runs}
    second_workflows = {run.pipeline_run_id for run in second.processing_runs}
    assert len(first_workflows) == 1
    assert len(second_workflows) == 1
    assert first_workflows.isdisjoint(second_workflows)
    assert {
        run.repetition_group_id
        for run in first.processing_runs + second.processing_runs
    } == {"benchmark-pmc-v1"}
    assert docling.calls == 2
    assert grobid.calls == 4
    assert ocr.calls == 2
    assert first.derivative_artifact_ids == second.derivative_artifact_ids


@pytest.mark.asyncio
async def test_named_attempt_and_benchmark_group_require_forced_scope(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )

    with pytest.raises(ValueError, match="pipeline_attempt_id requires"):
        await processor.process_artifact(
            "not-loaded",
            pipeline_attempt_id="attempt-1",
        )
    with pytest.raises(ValueError, match="require pipeline_attempt_id"):
        await processor.process_artifact(
            "not-loaded",
            force_reprocess=True,
            repetition_group_id="benchmark-v1",
        )


@pytest.mark.asyncio
async def test_content_integrity_overlay_marks_unaligned_tables_and_result_partial(
    tmp_path,
) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=BrokenIntegrityDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>table integrity</body></html>",
        acquisition_uri="https://example.test/table.html",
        media_type="text/html",
        identifiers={"filename": "table.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.PARTIAL
    integrity_run = next(
        run
        for run in result.processing_runs
        if run.component_id == "docling-content-integrity"
    )
    overlay = json.loads(
        processor.store.read_blob(
            integrity_run.require_output("content_integrity_overlay").blob_sha256
        )
    )
    assert overlay["records"][0]["kind"] == "table"
    assert overlay["records"][0]["status"] == "unaligned"
    assert any(
        diagnostic.code == "UNALIGNED_TABLE" for diagnostic in result.diagnostics
    )
    docling_run = next(
        run for run in result.processing_runs if run.component_id == "docling"
    )
    assert integrity_run.inputs == (docling_run.require_output("docling_document"),)


@pytest.mark.asyncio
async def test_page_level_image_only_signal_triggers_ocr_even_when_grobid_is_usable(
    tmp_path,
) -> None:
    grobid = FakeGrobid()
    ocr = FakeOCR()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=ImageOnlySignalDocling(),
        grobid=grobid,
        ocrmypdf=ocr,
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nIMAGE ONLY SIGNAL",
        acquisition_uri="https://example.test/image-signal.pdf",
        media_type="application/pdf",
        identifiers={"filename": "image-signal.pdf"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.COMPLETE
    assert ocr.calls == 1
    assert grobid.calls == 2
    ocr_run = next(
        run for run in result.processing_runs if run.component_id == "ocrmypdf"
    )
    assert ocr_run.configuration["fallback_reason"] == "image_only_pages"


@pytest.mark.asyncio
async def test_scanned_pdf_creates_recorded_ocr_derivative_and_retries_grobid(
    tmp_path,
) -> None:
    docling = FakeDocling()
    grobid = FakeGrobid(scan_first=True)
    ocr = FakeOCR()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=grobid,
        ocrmypdf=ocr,
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nIMAGE ONLY",
        acquisition_uri="https://example.test/scan.pdf",
        media_type="application/pdf",
        identifiers={"filename": "scan.pdf"},
    )

    result = await processor.process_artifact(artifact.artifact_id)
    assert result.status is ProcessingRunStatus.COMPLETE
    assert len(result.derivative_artifact_ids) == 1
    assert ocr.calls == 1
    assert grobid.calls == 2
    ocr_run = next(
        run for run in result.processing_runs if run.component_id == "ocrmypdf"
    )
    fallback_grobid_run = next(
        run
        for run in result.processing_runs
        if run.component_id == "grobid"
        and run.artifact_id == result.derivative_artifact_ids[0]
    )
    assert fallback_grobid_run.inputs == (ocr_run.require_output("searchable_pdf"),)
    assert fallback_grobid_run.require_output("grobid_tei").source_artifact_ids == (
        result.derivative_artifact_ids[0],
        artifact.artifact_id,
    )
    alignment_run = next(
        run
        for run in result.processing_runs
        if run.component_id == "docling-grobid-aligner"
    )
    assert [product.name for product in alignment_run.inputs] == [
        "docling_document",
        "grobid_tei",
    ]
    assert alignment_run.require_output("alignment_overlay").source_artifact_ids == (
        artifact.artifact_id,
        result.derivative_artifact_ids[0],
    )
    integrity_run = next(
        run
        for run in result.processing_runs
        if run.component_id == "docling-content-integrity"
    )
    assert [product.name for product in integrity_run.inputs] == [
        "docling_document",
        "alignment_overlay",
    ]
    assert any(
        diagnostic.code == "GROBID_TEXT_INSUFFICIENT"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_ocr_derivative_lineage_recovers_after_run_commit_crash(
    tmp_path,
    monkeypatch,
) -> None:
    grobid = FakeGrobid(scan_first=True)
    ocr = FakeOCR()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=grobid,
        ocrmypdf=ocr,
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nIMAGE ONLY CRASH",
        acquisition_uri="https://example.test/scan-crash.pdf",
        media_type="application/pdf",
        identifiers={"filename": "scan-crash.pdf"},
    )
    original_ingest = processor.ingest_bytes
    crash_pending = True

    def crash_once(content: bytes, **kwargs: Any) -> DocumentArtifact:
        nonlocal crash_pending
        if (
            crash_pending
            and kwargs.get("relationship") is ArtifactRelationship.DERIVATIVE
        ):
            crash_pending = False
            raise OSError("synthetic crash after OCR run commit")
        return original_ingest(content, **kwargs)

    monkeypatch.setattr(processor, "ingest_bytes", crash_once)

    with pytest.raises(ProcessingRunCommitIncompleteError):
        await processor.process_artifact(artifact.artifact_id)

    ocr_run = next(
        run
        for run in processor.store.list_processing_runs(
            artifact_id=artifact.artifact_id
        )
        if run.component_id == "ocrmypdf"
    )
    assert ocr_run.status is ProcessingRunStatus.COMPLETE
    assert ocr.calls == 1
    assert not any(
        candidate.parent_artifact_id == artifact.artifact_id
        for candidate in processor.store.list_artifacts()
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.COMPLETE
    assert ocr.calls == 1
    derivative = processor.store.get_artifact(result.derivative_artifact_ids[0])
    assert derivative.raw_location.created_by_run_id == ocr_run.run_id


@pytest.mark.asyncio
async def test_quarantined_ocr_derivative_is_never_sent_to_grobid(tmp_path) -> None:
    grobid = FakeGrobid(scan_first=True)
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=grobid,
        ocrmypdf=CorruptOCR(),
        config=DocumentProcessingConfig(
            ocr_mode="local_cli",
            grobid_minimum_text_characters=80,
            require_runtime_identity=False,
        ),
    )
    artifact = processor.ingest_bytes(
        _plain_pdf(),
        acquisition_uri="https://example.test/corrupt-ocr-source.pdf",
        media_type="application/pdf",
        identifiers={"filename": "corrupt-ocr-source.pdf"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.QUARANTINED
    assert grobid.calls == 1
    assert len(result.derivative_artifact_ids) == 1
    assert any(
        run.component_id == "document-fallback-policy"
        and run.status is ProcessingRunStatus.QUARANTINED
        for run in result.processing_runs
    )
    assert any(
        diagnostic.code == "PDF_STRUCTURE_UNCERTAIN"
        for diagnostic in result.diagnostics
    )
    assert any(
        diagnostic.code == "PARSER_FALLBACK_EXHAUSTED"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_unsupported_input_is_explicitly_quarantined(tmp_path) -> None:
    docling = FakeDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config().model_copy(update={"preflight_enabled": True}),
    )
    artifact = processor.ingest_bytes(
        b"unsupported binary",
        acquisition_uri="https://example.test/blob.bin",
        media_type="application/octet-stream",
        identifiers={"filename": "blob.bin"},
    )
    result = await processor.process_artifact(artifact.artifact_id)
    assert result.status is ProcessingRunStatus.QUARANTINED
    assert result.processing_runs[0].status is ProcessingRunStatus.QUARANTINED
    assert result.diagnostics[0].code == "UNSUPPORTED_INPUT_FORMAT"
    assert docling.calls == 0

    changed_ocr = FakeOCR()
    changed_ocr.jobs = 3
    changed = DocumentProcessor(
        processor.store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=changed_ocr,
        config=_config().model_copy(update={"preflight_enabled": True}),
    )
    changed_result = await changed.process_artifact(artifact.artifact_id)

    assert changed_result.status is ProcessingRunStatus.QUARANTINED
    first_router = result.processing_runs[0]
    second_router = changed_result.processing_runs[0]
    assert first_router.run_id != second_router.run_id
    assert first_router.output_policy_sha256 != second_router.output_policy_sha256
    preflight_runs = processor.store.list_processing_runs(
        artifact_id=artifact.artifact_id,
        component_id="document-preflight",
    )
    assert len(preflight_runs) == 2
    assert len({run.output_policy_sha256 for run in preflight_runs}) == 2


@pytest.mark.asyncio
async def test_parser_failure_is_persisted_with_machine_readable_diagnostic(
    tmp_path,
) -> None:
    docling = FailingDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nencrypted",
        acquisition_uri="https://example.test/encrypted.pdf",
        media_type="application/pdf",
        identifiers={"filename": "encrypted.pdf"},
    )
    result = await processor.process_artifact(artifact.artifact_id)
    assert result.status is ProcessingRunStatus.FAILED
    assert result.processing_runs[0].status is ProcessingRunStatus.FAILED
    assert result.diagnostics[0].code == "DOCLING_ENCRYPTED_PDF"
    assert result.diagnostics[0].details["status_code"] == 422


@pytest.mark.asyncio
async def test_empty_docling_parse_is_failed_not_successful_or_partial(
    tmp_path,
) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=EmptyDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>source text</body></html>",
        acquisition_uri="https://example.test/empty-parse.html",
        media_type="text/html",
        identifiers={"filename": "empty-parse.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.FAILED
    assert (
        next(
            run for run in result.processing_runs if run.component_id == "docling"
        ).status
        is ProcessingRunStatus.FAILED
    )
    assert any(diagnostic.code == "NO_TEXT_ITEMS" for diagnostic in result.diagnostics)


@pytest.mark.asyncio
async def test_html_pipeline_persists_docling_item_content_spans(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>source text</body></html>",
        acquisition_uri="https://example.test/source.html",
        media_type="text/html",
        identifiers={"filename": "source.html"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.COMPLETE
    docling_run = next(
        run for run in result.processing_runs if run.component_id == "docling"
    )
    assert docling_run.status is ProcessingRunStatus.COMPLETE
    span_set = json.loads(
        processor.store.read_blob(
            docling_run.require_output("content_spans").blob_sha256
        )
    )
    spans = span_set["spans"]
    assert (
        span_set["representation_product_id"]
        == docling_run.require_output("docling_document").product_id
    )
    assert [span["source_locator"] for span in spans] == [
        {
            "kind": "docling_item",
            "input_format": "html",
            "item_ref": "#/texts/0",
        },
        {
            "kind": "docling_item",
            "input_format": "html",
            "item_ref": "#/texts/1",
        },
    ]


@pytest.mark.asyncio
async def test_docling_remote_task_checkpoint_resumes_after_interruption(
    tmp_path,
) -> None:
    docling = ResumableDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nREMOTE TASK",
        acquisition_uri="https://example.test/remote-task.pdf",
        media_type="application/pdf",
        identifiers={"filename": "remote-task.pdf"},
    )

    first = await processor.process_artifact(artifact.artifact_id)
    second = await processor.process_artifact(artifact.artifact_id)

    assert first.status is ProcessingRunStatus.FAILED
    assert second.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, "remote-task-persisted"]


@pytest.mark.asyncio
async def test_named_forced_attempt_resumes_across_restart_and_is_idempotent(
    tmp_path,
) -> None:
    docling = ResumableDocling()
    store = ContentAddressedStore(tmp_path / "store")
    first_processor = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = first_processor.ingest_bytes(
        b"<html><body>forced restart resume</body></html>",
        acquisition_uri="https://example.test/forced-restart.html",
        media_type="text/html",
        identifiers={"filename": "forced-restart.html"},
    )
    attempt = {
        "force_reprocess": True,
        "repetition_group_id": "restart-benchmark-v1",
        "pipeline_attempt_id": "attempt-001",
    }

    interrupted = await first_processor.process_artifact(
        artifact.artifact_id, **attempt
    )
    checkpoint_paths = tuple(
        (store.root / "records" / "execution_checkpoints").glob("*.json")
    )
    assert len(checkpoint_paths) == 1
    checkpoint_payload = json.loads(checkpoint_paths[0].read_text(encoding="utf-8"))
    assert checkpoint_payload["pipeline_attempt_id"] == "attempt-001"
    assert checkpoint_payload["repetition_group_id"] == "restart-benchmark-v1"
    restarted_processor = DocumentProcessor(
        ContentAddressedStore(store.root),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    resumed = await restarted_processor.process_artifact(
        artifact.artifact_id, **attempt
    )
    completed_retry_processor = DocumentProcessor(
        ContentAddressedStore(store.root),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    completed_retry = await completed_retry_processor.process_artifact(
        artifact.artifact_id, **attempt
    )

    interrupted_docling = next(
        run for run in interrupted.processing_runs if run.component_id == "docling"
    )
    resumed_docling = next(
        run for run in resumed.processing_runs if run.component_id == "docling"
    )
    completed_retry_docling = next(
        run for run in completed_retry.processing_runs if run.component_id == "docling"
    )
    assert interrupted.status is ProcessingRunStatus.FAILED
    assert resumed.status is ProcessingRunStatus.COMPLETE
    assert completed_retry.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, "remote-task-persisted"]
    assert docling.calls == 2
    assert interrupted_docling.pipeline_run_id == resumed_docling.pipeline_run_id
    assert checkpoint_payload["pipeline_run_id"] == resumed_docling.pipeline_run_id
    assert completed_retry_docling.run_id == resumed_docling.run_id
    assert completed_retry_docling.pipeline_run_id == resumed_docling.pipeline_run_id
    assert (
        tuple((store.root / "records" / "execution_checkpoints").glob("*.json")) == ()
    )


@pytest.mark.asyncio
async def test_different_forced_attempt_never_resumes_interrupted_checkpoint(
    tmp_path,
) -> None:
    docling = ForceIsolatedCheckpointDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>forced attempt isolation</body></html>",
        acquisition_uri="https://example.test/forced-attempt-isolation.html",
        media_type="text/html",
        identifiers={"filename": "forced-attempt-isolation.html"},
    )

    interrupted = await processor.process_artifact(
        artifact.artifact_id,
        force_reprocess=True,
        repetition_group_id="attempt-isolation-v1",
        pipeline_attempt_id="attempt-a",
    )
    independent = await processor.process_artifact(
        artifact.artifact_id,
        force_reprocess=True,
        repetition_group_id="attempt-isolation-v1",
        pipeline_attempt_id="attempt-b",
    )

    assert interrupted.status is ProcessingRunStatus.FAILED
    assert independent.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, None]
    assert {run.pipeline_run_id for run in interrupted.processing_runs}.isdisjoint(
        {run.pipeline_run_id for run in independent.processing_runs}
    )


@pytest.mark.asyncio
async def test_policy_drift_never_resumes_named_forced_attempt_checkpoint(
    tmp_path,
) -> None:
    docling = ForceIsolatedCheckpointDocling()
    store = ContentAddressedStore(tmp_path / "store")
    first_processor = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = first_processor.ingest_bytes(
        b"<html><body>forced policy isolation</body></html>",
        acquisition_uri="https://example.test/forced-policy-isolation.html",
        media_type="text/html",
        identifiers={"filename": "forced-policy-isolation.html"},
    )
    attempt = {
        "force_reprocess": True,
        "repetition_group_id": "policy-isolation-v1",
        "pipeline_attempt_id": "attempt-a",
    }

    interrupted = await first_processor.process_artifact(
        artifact.artifact_id, **attempt
    )
    changed_processor = DocumentProcessor(
        ContentAddressedStore(store.root),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config().model_copy(update={"alignment_minimum_score": 0.8}),
    )
    changed = await changed_processor.process_artifact(artifact.artifact_id, **attempt)

    assert interrupted.status is ProcessingRunStatus.FAILED
    assert changed.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, None]
    assert {run.output_policy_sha256 for run in interrupted.processing_runs}.isdisjoint(
        {run.output_policy_sha256 for run in changed.processing_runs}
    )


@pytest.mark.asyncio
async def test_forced_docling_workflow_never_resumes_an_older_checkpoint(
    tmp_path,
) -> None:
    docling = ForceIsolatedCheckpointDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>forced checkpoint isolation</body></html>",
        acquisition_uri="https://example.test/forced-checkpoint.html",
        media_type="text/html",
        identifiers={"filename": "forced-checkpoint.html"},
    )

    interrupted = await processor.process_artifact(artifact.artifact_id)
    forced = await processor.process_artifact(
        artifact.artifact_id,
        force_reprocess=True,
        repetition_group_id="checkpoint-isolation-v1",
        pipeline_attempt_id="forced-attempt-1",
    )

    assert interrupted.status is ProcessingRunStatus.FAILED
    assert forced.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, None]
    forced_docling = next(
        run for run in forced.processing_runs if run.component_id == "docling"
    )
    assert forced_docling.repetition_group_id == "checkpoint-isolation-v1"


@pytest.mark.asyncio
async def test_terminal_docling_task_is_not_resumed_forever(tmp_path) -> None:
    docling = TerminalCheckpointDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>terminal task</body></html>",
        acquisition_uri="https://example.test/terminal-task.html",
        media_type="text/html",
        identifiers={"filename": "terminal-task.html"},
    )

    first = await processor.process_artifact(artifact.artifact_id)
    second = await processor.process_artifact(artifact.artifact_id)
    third = await processor.process_artifact(artifact.artifact_id)

    assert first.status is ProcessingRunStatus.FAILED
    assert second.status is ProcessingRunStatus.FAILED
    assert third.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, "terminal-task", None]


@pytest.mark.asyncio
async def test_immediately_terminal_new_docling_task_clears_checkpoint(
    tmp_path,
) -> None:
    docling = ImmediateTerminalCheckpointDocling()
    store = ContentAddressedStore(tmp_path / "store")
    processor = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>immediate terminal task</body></html>",
        acquisition_uri="https://example.test/immediate-terminal.html",
        media_type="text/html",
        identifiers={"filename": "immediate-terminal.html"},
    )

    first = await processor.process_artifact(artifact.artifact_id)
    checkpoints = list(
        (store.root / "records" / "execution_checkpoints").glob("*.json")
    )
    second = await processor.process_artifact(artifact.artifact_id)

    assert first.status is ProcessingRunStatus.FAILED
    assert checkpoints == []
    assert second.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, None]


@pytest.mark.asyncio
async def test_oversized_docling_result_is_failed_and_clears_checkpoint(
    tmp_path,
) -> None:
    docling = OversizedResponseCheckpointDocling()
    store = ContentAddressedStore(tmp_path / "store")
    processor = DocumentProcessor(
        store,
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<html><body>oversized Docling result</body></html>",
        acquisition_uri="https://example.test/oversized-result.html",
        media_type="text/html",
        identifiers={"filename": "oversized-result.html"},
    )

    failed = await processor.process_artifact(artifact.artifact_id)
    checkpoints = list(
        (store.root / "records" / "execution_checkpoints").glob("*.json")
    )
    retried = await processor.process_artifact(artifact.artifact_id)

    failed_docling = next(
        run for run in failed.processing_runs if run.component_id == "docling"
    )
    assert failed.status is ProcessingRunStatus.FAILED
    assert failed_docling.status is ProcessingRunStatus.FAILED
    assert any(
        diagnostic.code == "DOCLING_RESPONSE_TOO_LARGE"
        and diagnostic.processing_run_id == failed_docling.run_id
        for diagnostic in failed.diagnostics
    )
    assert checkpoints == []
    assert retried.status is ProcessingRunStatus.COMPLETE
    assert docling.resume_task_ids == [None, None]


@pytest.mark.asyncio
async def test_jats_locator_failure_is_recorded_and_makes_result_partial(
    tmp_path,
) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<article><p>truncated",
        acquisition_uri="https://example.test/truncated.nxml",
        media_type="application/jats+xml",
        identifiers={"filename": "truncated.nxml"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.PARTIAL
    assert any(
        run.component_id == "jats-locator-adapter"
        and run.status is ProcessingRunStatus.FAILED
        for run in result.processing_runs
    )
    assert any(
        diagnostic.code == "JATS_LOCATOR_ADAPTER_FAILED"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_alignment_failure_is_explicit_and_makes_result_partial(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    processor.aligner = FailingAligner()  # type: ignore[assignment]
    artifact = processor.ingest_bytes(
        b"%PDF-1.7\nBORN DIGITAL",
        acquisition_uri="https://example.test/alignment-failure.pdf",
        media_type="application/pdf",
        identifiers={"filename": "alignment-failure.pdf"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.PARTIAL
    assert result.grobid_tei_sha256
    assert result.alignment_sha256 is None
    assert any(
        run.component_id == "docling-grobid-aligner"
        and run.status is ProcessingRunStatus.FAILED
        and [product.name for product in run.inputs]
        == ["docling_document", "grobid_tei"]
        for run in result.processing_runs
    )
    assert any(
        diagnostic.code == "DOCLING_GROBID_ALIGNER_FAILED"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_jats_unaligned_locators_are_persisted_and_diagnosed(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<article><body><p id='p1'>Text absent from Docling.</p></body></article>",
        acquisition_uri="https://example.test/unaligned.nxml",
        media_type="application/jats+xml",
        identifiers={"filename": "unaligned.nxml"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.PARTIAL
    docling_run = next(
        run for run in result.processing_runs if run.component_id == "docling"
    )
    assert docling_run.status is ProcessingRunStatus.PARTIAL
    assert docling_run.output("jats_locator_alignment") is not None
    adapter_run = next(
        run
        for run in result.processing_runs
        if run.component_id == "jats-locator-adapter"
    )
    assert docling_run.inputs == (adapter_run.require_output("native_locator_overlay"),)
    assert any(
        diagnostic.code == "JATS_LOCATORS_UNALIGNED"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_bioc_unaligned_locators_are_partial_and_diagnosed(tmp_path) -> None:
    collection = BioCCollection()
    document = BioCDocument()
    document.id = "PMC-BIOC-UNALIGNED"
    passage = BioCPassage()
    passage.offset = 0
    passage.text = "Text absent from the Docling conversion."
    document.add_passage(passage)
    collection.add_document(document)
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        biocjson.dumps(collection).encode("utf-8"),
        acquisition_uri="https://example.test/unaligned.bioc.json",
        media_type="application/bioc+json",
        identifiers={"filename": "unaligned.bioc.json"},
    )

    result = await processor.process_artifact(artifact.artifact_id)
    docling_run = next(
        run for run in result.processing_runs if run.component_id == "docling"
    )

    assert result.status is ProcessingRunStatus.PARTIAL
    assert docling_run.status is ProcessingRunStatus.PARTIAL
    assert any(
        diagnostic.code == "BIOC_LOCATORS_UNALIGNED"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_jats_without_native_text_locators_is_partial(tmp_path) -> None:
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=FakeDocling(),
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        b"<article><body><custom-tag>Unsupported text node.</custom-tag></body></article>",
        acquisition_uri="https://example.test/no-locators.nxml",
        media_type="application/jats+xml",
        identifiers={"filename": "no-locators.nxml"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.PARTIAL
    assert any(
        diagnostic.code == "JATS_NATIVE_LOCATORS_EMPTY"
        for diagnostic in result.diagnostics
    )


@pytest.mark.asyncio
async def test_bioc_pipeline_persists_native_content_spans(tmp_path) -> None:
    collection = BioCCollection()
    collection.source = "PMC"
    collection.date = "20260717"
    collection.key = "pipeline-test"
    first_document = BioCDocument()
    first_document.id = "PMC-BIOC-1"
    first_passage = BioCPassage()
    first_passage.offset = 5
    first_passage.text = "Methods"
    first_document.add_passage(first_passage)
    collection.add_document(first_document)
    second_document = BioCDocument()
    second_document.id = "PMC-BIOC-2"
    second_passage = BioCPassage()
    second_passage.offset = 42
    second_passage.text = "Amyloid beta was measured in a reusable synthetic cohort."
    second_document.add_passage(second_passage)
    collection.add_document(second_document)

    docling = FakeDocling()
    processor = DocumentProcessor(
        ContentAddressedStore(tmp_path / "store"),
        docling=docling,
        grobid=FakeGrobid(),
        ocrmypdf=FakeOCR(),
        config=_config(),
    )
    artifact = processor.ingest_bytes(
        biocjson.dumps(collection).encode("utf-8"),
        acquisition_uri="https://example.test/article.bioc.json",
        media_type="application/bioc+json",
        identifiers={"filename": "article.bioc.json"},
    )

    result = await processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.COMPLETE
    assert result.content_span_count == 2
    adapter_run = next(
        run for run in result.processing_runs if run.component_id == "bioc-adapter"
    )
    native_locators = json.loads(
        processor.store.read_blob(
            adapter_run.require_output("native_locator_overlay").blob_sha256
        )
    )
    assert [locator["document_index"] for locator in native_locators] == [0, 1]
    assert [locator["length"] for locator in native_locators] == [
        len(first_passage.text),
        len(second_passage.text),
    ]
    docling_run = next(
        run for run in result.processing_runs if run.component_id == "docling"
    )
    assert docling_run.output("bioc_locator_alignment") is not None
    assert docling_run.inputs == (
        adapter_run.require_output("html_projection"),
        adapter_run.require_output("native_locator_overlay"),
    )
    span_set = json.loads(
        processor.store.read_blob(
            docling_run.require_output("content_spans").blob_sha256
        )
    )
    spans = span_set["spans"]
    assert spans[0]["source_locator"] == {
        "kind": "bioc",
        "document_index": 0,
        "document_id": "PMC-BIOC-1",
        "passage_index": 0,
        "sentence_index": None,
        "offset": 5,
        "length": len(first_passage.text),
    }
    assert spans[1]["source_locator"]["document_index"] == 1
    assert spans[1]["source_locator"]["length"] == len(second_passage.text)

    resumed = await processor.process_artifact(artifact.artifact_id)

    assert resumed.status is ProcessingRunStatus.COMPLETE
    assert resumed.content_span_count == 2
    assert docling.calls == 1
