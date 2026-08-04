"""Crash-recovery tests for atomic processing-run diagnostic commitments."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from DeepResearch.src.document_processing import (
    ContentAddressedStore,
    DoclingConversionResult,
    DoclingServeClient,
    DocumentProcessingConfig,
    DocumentProcessor,
    ProcessingDiagnostic,
    ProcessingRunCommitIncompleteError,
    ProcessingRunDiagnosticManifest,
    ProcessingRunStatus,
)


class FailOnceDiagnosticStore(ContentAddressedStore):
    """Simulate a process failure after its processing run is already durable."""

    def __init__(self, root: Path, *, fail_once: bool) -> None:
        super().__init__(root)
        self.fail_once = fail_once

    def save_diagnostic(self, diagnostic: ProcessingDiagnostic) -> Path:
        if self.fail_once and diagnostic.processing_run_id is not None:
            run = self.get_processing_run(diagnostic.processing_run_id)
            if run.component_id == "docling":
                self.fail_once = False
                raise OSError("injected diagnostic index failure")
        return super().save_diagnostic(diagnostic)


class CheckpointingDocling(DoclingServeClient):
    def __init__(self) -> None:
        self.calls = 0

    async def convert(self, *_args: Any, **kwargs: Any) -> DoclingConversionResult:
        self.calls += 1
        assert kwargs["resume_task_id"] is None
        hook_result = kwargs["on_task_submitted"]("docling-task-1")
        if inspect.isawaitable(hook_result):
            await hook_result
        document = {
            "schema_name": "DoclingDocument",
            "version": "1.0.0",
            "name": "commit-recovery",
            "body": {
                "self_ref": "#/body",
                "children": [
                    {"$ref": "#/texts/0"},
                    {"$ref": "#/texts/1"},
                ],
            },
            "furniture": {"self_ref": "#/furniture", "children": []},
            "texts": [
                {
                    "self_ref": "#/texts/0",
                    "parent": {"$ref": "#/body"},
                    "children": [],
                    "label": "paragraph",
                    "text": "A recoverable parser result.",
                    "prov": [],
                },
                {
                    "self_ref": "#/texts/1",
                    "parent": {"$ref": "#/body"},
                    "children": [],
                    "label": "paragraph",
                    "text": "",
                    "prov": [],
                },
            ],
            "groups": [],
            "tables": [],
            "pictures": [],
            "key_value_items": [],
            "form_items": [],
            "pages": {},
        }
        raw_response = {
            "document": {"json_content": document},
            "status": "success",
            "errors": [],
        }
        return DoclingConversionResult(
            document=document,
            raw_response=raw_response,
            status="success",
            remote_task_id="docling-task-1",
        )


@pytest.mark.asyncio
async def test_retry_reconciles_diagnostics_without_repeating_docling(
    tmp_path: Path,
) -> None:
    store_root = tmp_path / "store"
    first_store = FailOnceDiagnosticStore(store_root, fail_once=True)
    docling = CheckpointingDocling()
    config = DocumentProcessingConfig(
        preflight_enabled=False,
        require_runtime_identity=False,
        ocr_mode="local_cli",
    )
    first_processor = DocumentProcessor(first_store, docling=docling, config=config)
    artifact = first_processor.ingest_bytes(
        b"<html><body>commit recovery</body></html>",
        acquisition_uri="https://example.test/commit-recovery.html",
        media_type="text/html",
        identifiers={"filename": "commit-recovery.html"},
    )

    with pytest.raises(
        ProcessingRunCommitIncompleteError,
        match="diagnostic reconciliation is incomplete",
    ):
        await first_processor.process_artifact(artifact.artifact_id)

    persisted_runs = first_store.list_processing_runs(
        artifact_id=artifact.artifact_id, component_id="docling"
    )
    assert len(persisted_runs) == 1
    persisted_run = persisted_runs[0]
    assert persisted_run.status is ProcessingRunStatus.COMPLETE
    manifest = ProcessingRunDiagnosticManifest.model_validate_json(
        first_store.read_blob(
            persisted_run.require_output("diagnostics_manifest").blob_sha256
        )
    )
    assert [item.code for item in manifest.diagnostics] == ["EMPTY_TEXT_ITEM"]
    assert first_store.list_diagnostics(processing_run_id=persisted_run.run_id) == ()
    assert not first_store.has_complete_run(artifact.artifact_id, "docling")
    assert first_store.list_resume_candidates("docling") == (artifact,)
    assert (
        len(list((store_root / "records" / "execution_checkpoints").glob("*.json")))
        == 1
    )
    assert docling.calls == 1

    reopened_store = FailOnceDiagnosticStore(store_root, fail_once=False)
    reopened_processor = DocumentProcessor(
        reopened_store,
        docling=docling,
        config=config,
    )
    result = await reopened_processor.process_artifact(artifact.artifact_id)

    assert result.status is ProcessingRunStatus.COMPLETE
    assert docling.calls == 1
    assert (
        next(run for run in result.processing_runs if run.component_id == "docling")
        == persisted_run
    )
    assert any(
        run.component_id == "docling-content-integrity"
        for run in result.processing_runs
    )
    assert [
        item.code
        for item in reopened_store.list_diagnostics(
            processing_run_id=persisted_run.run_id
        )
    ] == ["EMPTY_TEXT_ITEM"]
    assert reopened_store.has_complete_run(artifact.artifact_id, "docling")
    assert reopened_store.list_resume_candidates("docling") == ()
    assert list((store_root / "records" / "execution_checkpoints").glob("*.json")) == []
