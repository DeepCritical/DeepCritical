"""Typed data-product contract and lineage tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from DeepResearch.src.document_processing.models import (
    ArtifactLocationRole,
    ComponentDescriptor,
    DataProductRef,
    DocumentArtifact,
    ProcessingRun,
    ProcessingRunStatus,
    configuration_sha256,
)
from DeepResearch.src.document_processing.products import (
    PRODUCT_REGISTRY,
    build_data_product_ref,
    validate_product_contract,
)
from DeepResearch.src.document_processing.storage import (
    ContentAddressedStore,
    HashMismatchError,
    RecordConflictError,
)

EXPECTED_PRODUCTS = {
    "preflight_result",
    "native_locator_overlay",
    "html_projection",
    "docling_document",
    "docling_response",
    "content_spans",
    "jats_locator_alignment",
    "bioc_locator_alignment",
    "runtime_attestation",
    "grobid_tei",
    "searchable_pdf",
    "ocr_sidecar",
    "ocr_log",
    "alignment_overlay",
    "content_integrity_overlay",
    "canonical_document_view",
    "diagnostics_manifest",
}


def _store_with_artifact(
    tmp_path: Path,
) -> tuple[ContentAddressedStore, DocumentArtifact]:
    store = ContentAddressedStore(tmp_path / "store")
    source = store.put_blob(b"source")
    artifact = DocumentArtifact(
        artifact_id="artifact-1",
        source_sha256=source.sha256,
        acquisition_uri="https://example.test/source.pdf",
        media_type="application/pdf",
        raw_location=source.as_location(
            media_type="application/pdf",
            role=ArtifactLocationRole.RAW,
        ),
    )
    store.save_artifact(artifact)
    return store, artifact


def _run(
    artifact: DocumentArtifact,
    *,
    run_id: str,
    inputs: tuple[DataProductRef, ...] = (),
    outputs: tuple[DataProductRef, ...] = (),
) -> ProcessingRun:
    configuration = {"fixture": True}
    now = datetime(2026, 7, 27, tzinfo=UTC)
    return ProcessingRun(
        run_id=run_id,
        artifact_id=artifact.artifact_id,
        stage_id="fixture",
        component=ComponentDescriptor(
            component_id="fixture-component",
            component_version="1",
            capability="fixture",
        ),
        configuration=configuration,
        configuration_sha256=configuration_sha256(configuration),
        started_at=now,
        finished_at=now,
        status=ProcessingRunStatus.COMPLETE,
        inputs=inputs,
        outputs=outputs,
    )


def test_product_registry_is_complete_and_builds_exact_contract() -> None:
    assert set(PRODUCT_REGISTRY) == EXPECTED_PRODUCTS

    product = build_data_product_ref(
        name="docling_document",
        blob_sha256="a" * 64,
        uri=f"cas://sha256/{'a' * 64}",
        byte_size=7,
        producer_run_id="run-1",
        source_artifact_ids=("artifact-1",),
    )

    validate_product_contract(product)
    assert product.media_type == "application/json"
    assert product.payload_schema_version == "docling-document-v1"
    assert product.product_id.startswith("product-")


def test_product_registry_rejects_unknown_or_misdeclared_products() -> None:
    with pytest.raises(ValueError, match="unknown data product"):
        build_data_product_ref(
            name="undeclared",
            blob_sha256="a" * 64,
            uri=f"cas://sha256/{'a' * 64}",
            byte_size=0,
            producer_run_id="run-1",
            source_artifact_ids=("artifact-1",),
        )

    product = build_data_product_ref(
        name="docling_document",
        blob_sha256="a" * 64,
        uri=f"cas://sha256/{'a' * 64}",
        byte_size=0,
        producer_run_id="run-1",
        source_artifact_ids=("artifact-1",),
    )
    with pytest.raises(ValueError, match="registered contract"):
        validate_product_contract(
            product.model_copy(update={"media_type": "text/plain"})
        )
    with pytest.raises(ValueError, match="unknown data product"):
        validate_product_contract(product.model_copy(update={"name": "undeclared"}))
    with pytest.raises(ValueError, match="invalid product_id"):
        validate_product_contract(
            product.model_copy(update={"product_id": "product-wrong"})
        )


def test_store_accepts_declared_products_and_checks_input_lineage(
    tmp_path: Path,
) -> None:
    store, artifact = _store_with_artifact(tmp_path)
    output_blob = store.put_blob(b'{"document":true}')
    output = store.data_product_ref(
        name="docling_document",
        blob_sha256=output_blob.sha256,
        producer_run_id="producer",
        source_artifact_ids=(artifact.artifact_id,),
    )
    producer = _run(artifact, run_id="producer", outputs=(output,))
    store.save_processing_run(producer)

    consumer = _run(artifact, run_id="consumer", inputs=(output,))
    store.save_processing_run(consumer)
    assert store.get_processing_run(consumer.run_id) == consumer

    undeclared_blob = store.put_blob(b'{"other":true}')
    undeclared = store.data_product_ref(
        name="docling_response",
        blob_sha256=undeclared_blob.sha256,
        producer_run_id=producer.run_id,
        source_artifact_ids=(artifact.artifact_id,),
    )
    with pytest.raises(RecordConflictError, match="not declared"):
        store.save_processing_run(
            _run(artifact, run_id="invalid-consumer", inputs=(undeclared,))
        )


def test_store_rejects_product_schema_uri_and_size_mismatches(
    tmp_path: Path,
) -> None:
    store, artifact = _store_with_artifact(tmp_path)
    output_blob = store.put_blob(b'{"document":true}')
    output = store.data_product_ref(
        name="docling_document",
        blob_sha256=output_blob.sha256,
        producer_run_id="run-invalid",
        source_artifact_ids=(artifact.artifact_id,),
    )

    wrong_schema = output.model_copy(
        update={"payload_schema_version": "docling-document-v99"}
    )
    with pytest.raises(RecordConflictError, match="registered contract"):
        store.save_processing_run(
            _run(artifact, run_id="run-invalid", outputs=(wrong_schema,))
        )

    wrong_size = output.model_copy(update={"byte_size": output.byte_size + 1})
    with pytest.raises(HashMismatchError, match="size does not match"):
        store.save_processing_run(
            _run(artifact, run_id="run-invalid", outputs=(wrong_size,))
        )
