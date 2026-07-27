"""Contract tests for document-processing provenance records."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from DeepResearch.src.document_processing.models import (
    ArtifactLocation,
    ArtifactLocationRole,
    ArtifactRelationship,
    BioCLocator,
    ComponentDescriptor,
    ContentSpan,
    ContentSpanSet,
    DataProductRef,
    DiagnosticSeverity,
    DocumentArtifact,
    ExecutionCheckpoint,
    IntakeQuarantineRecord,
    JatsLocator,
    LicenseMetadata,
    MemoryMeasurement,
    MemoryMeasurementScope,
    MemoryMeasurementStatus,
    PdfBoundingBox,
    PdfLocator,
    ProcessingDiagnostic,
    ProcessingRun,
    ProcessingRunDiagnosticManifest,
    ProcessingRunStatus,
    RemediationStatus,
    RepresentationAnchor,
    ResourceUsage,
    RuntimeAttestation,
    RuntimeAttestationSource,
    configuration_sha256,
    sha256_bytes,
)
from DeepResearch.src.document_processing.products import build_data_product_ref

SOURCE_BYTES = b"scientific source"
SOURCE_HASH = sha256_bytes(SOURCE_BYTES)


def test_all_persisted_contracts_have_descriptive_schema_versions() -> None:
    expected = {
        DocumentArtifact: "deepcritical-document-artifact-v1",
        ProcessingRun: "deepcritical-processing-run-v1",
        ProcessingDiagnostic: "deepcritical-processing-diagnostic-v1",
        ExecutionCheckpoint: "deepcritical-execution-checkpoint-v1",
        ContentSpanSet: "deepcritical-content-span-set-v1",
        ProcessingRunDiagnosticManifest: (
            "deepcritical-processing-diagnostic-manifest-v1"
        ),
        RuntimeAttestation: "deepcritical-runtime-attestation-v1",
        IntakeQuarantineRecord: "deepcritical-intake-quarantine-v1",
        ComponentDescriptor: "deepcritical-component-descriptor-v1",
        DataProductRef: "deepcritical-data-product-ref-v1",
    }

    assert {
        model: model.model_fields["schema_version"].default for model in expected
    } == expected


def raw_location() -> ArtifactLocation:
    return ArtifactLocation(
        uri=f"cas://sha256/{SOURCE_HASH}",
        sha256=SOURCE_HASH,
        byte_size=len(SOURCE_BYTES),
        media_type="application/pdf",
        role=ArtifactLocationRole.RAW,
    )


def source_artifact(**overrides: object) -> DocumentArtifact:
    values: dict[str, object] = {
        "artifact_id": "pmc-123-pdf",
        "source_sha256": SOURCE_HASH,
        "acquisition_uri": "https://example.test/articles/PMC123.pdf",
        "identifiers": {"PMC": "PMC123", "DOI": "10.1/example"},
        "license": LicenseMetadata(spdx_id="CC-BY-4.0", reuse_allowed=True),
        "media_type": "application/pdf",
        "raw_location": raw_location(),
    }
    values.update(overrides)
    return DocumentArtifact(**values)


def processing_run(**overrides: object) -> ProcessingRun:
    configuration = {"ocr": True, "table_mode": "accurate"}
    digest = f"sha256:{'2' * 64}"
    attestation = RuntimeAttestation(
        component_id="docling",
        component_version="2.113.0",
        invocation_id="docling-task-1",
        source=RuntimeAttestationSource.AUTHENTICATED_DEPLOYMENT_REPORTER,
        reporter_id="fixture-supervisor",
        observed_at=datetime(2026, 7, 17, 12, 0, 2, tzinfo=UTC),
        workload_id="docling-worker-1",
        container_reference=("quay.io/docling-project/docling-serve:2.113.0@" + digest),
        container_digest=digest,
        component_versions={"docling": "2.113.0"},
        model_versions={"layout": "heron-101"},
        model_hashes={"layout": "1" * 64},
    )
    attestation_hash = configuration_sha256(attestation.model_dump(mode="json"))
    attestation_output = build_data_product_ref(
        name="runtime_attestation",
        blob_sha256=attestation_hash,
        uri=f"cas://sha256/{attestation_hash}",
        byte_size=0,
        producer_run_id="run-docling-1",
        source_artifact_ids=("pmc-123-pdf",),
    )
    values: dict[str, object] = {
        "run_id": "run-docling-1",
        "artifact_id": "pmc-123-pdf",
        "stage_id": "docling",
        "component": ComponentDescriptor(
            component_id="docling",
            component_version="2.113.0",
            capability="document-conversion",
        ),
        "component_invocation_id": "docling-task-1",
        "component_versions": {"docling": "2.113.0"},
        "model_versions": {"layout": "heron-101"},
        "model_hashes": {"layout": "1" * 64},
        "container_image": attestation.container_reference,
        "container_digest": digest,
        "runtime_attestation": attestation,
        "runtime_attestation_sha256": attestation_hash,
        "configuration": configuration,
        "configuration_sha256": configuration_sha256(configuration),
        "started_at": datetime(2026, 7, 17, 12, tzinfo=UTC),
        "finished_at": datetime(2026, 7, 17, 12, 0, 4, tzinfo=UTC),
        "status": ProcessingRunStatus.COMPLETE,
        "outputs": (attestation_output,),
        "warnings": ("one formula was low confidence",),
        "completed_stages": ("convert", "validate"),
    }
    values.update(overrides)
    return ProcessingRun(**values)


def test_configuration_hash_is_canonical_and_rejects_non_json() -> None:
    assert configuration_sha256({"b": [2, 1], "a": True}) == configuration_sha256(
        {"a": True, "b": [2, 1]}
    )
    with pytest.raises((TypeError, ValueError)):
        configuration_sha256({"not-json": object()})


def test_document_artifact_normalizes_identifiers_and_is_frozen() -> None:
    artifact = source_artifact()

    assert artifact.identifiers == {"pmc": "PMC123", "doi": "10.1/example"}
    assert artifact.created_at.tzinfo is UTC
    with pytest.raises(ValidationError):
        artifact.artifact_id = "replacement"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"parent_artifact_id": "parent"}, "source artifacts cannot have a parent"),
        (
            {"relationship": ArtifactRelationship.SUPPLEMENT},
            "require a parent",
        ),
        (
            {"source_sha256": "f" * 64},
            "source_sha256 must match",
        ),
    ],
)
def test_document_artifact_rejects_invalid_lineage(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        source_artifact(**overrides)


def test_supplement_and_derivative_locations_preserve_lineage() -> None:
    derivative_hash = sha256_bytes(b"searchable derivative")
    supplement = source_artifact(
        artifact_id="pmc-123-supp-1",
        relationship=ArtifactRelationship.SUPPLEMENT,
        parent_artifact_id="pmc-123-pdf",
        derived_locations=(
            ArtifactLocation(
                uri=f"cas://sha256/{derivative_hash}",
                sha256=derivative_hash,
                byte_size=21,
                media_type="application/pdf",
                role=ArtifactLocationRole.SEARCHABLE_PDF,
                created_by_run_id="run-ocr-1",
            ),
        ),
    )

    assert supplement.relationship is ArtifactRelationship.SUPPLEMENT
    assert supplement.parent_artifact_id == "pmc-123-pdf"
    assert supplement.derived_locations[0].created_by_run_id == "run-ocr-1"


def test_timestamps_must_be_aware_and_are_normalized_to_utc() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        source_artifact(created_at=datetime.fromisoformat("2026-07-17T12:00:00"))

    offset = timezone(timedelta(hours=8))
    artifact = source_artifact(created_at=datetime(2026, 7, 17, 20, tzinfo=offset))
    assert artifact.created_at == datetime(2026, 7, 17, 12, tzinfo=UTC)
    assert artifact.created_at.tzinfo is UTC


def test_processing_run_captures_reproducibility_provenance() -> None:
    run = processing_run()

    assert run.status is ProcessingRunStatus.COMPLETE
    assert run.model_hashes["layout"] == "1" * 64
    assert run.container_digest == f"sha256:{'2' * 64}"
    assert run.completed_stages == ("convert", "validate")
    assert run.require_output("runtime_attestation").blob_sha256
    assert run.output("missing") is None
    with pytest.raises(KeyError, match="has no output"):
        run.require_output("missing")


def test_memory_measurement_requires_isolated_provenance_and_scalar_match() -> None:
    measurement = MemoryMeasurement(
        status=MemoryMeasurementStatus.MEASURED,
        method="cgroup-v2-memory.peak",
        scope=MemoryMeasurementScope.INVOCATION_CGROUP,
        boundary="ocr-container",
        peak_memory_bytes=4096,
        environment_sha256="3" * 64,
        measurement_id="ocr-run-1",
        started_at=datetime(2026, 7, 17, 12, tzinfo=UTC),
        finished_at=datetime(2026, 7, 17, 12, 0, 1, tzinfo=UTC),
        exclusive=True,
        shared_overhead_excluded=True,
        memory_events={"oom_kill": 0},
    )
    usage = ResourceUsage(peak_memory_bytes=4096, memory_measurement=measurement)

    assert usage.memory_measurement is measurement
    assert measurement.baseline_comparable is True
    assert (
        measurement.model_copy(
            update={"scope": MemoryMeasurementScope.EXCLUSIVE_SERVICE_CGROUP}
        ).baseline_comparable
        is True
    )
    assert (
        measurement.model_copy(
            update={"shared_overhead_excluded": False}
        ).baseline_comparable
        is False
    )
    assert (
        measurement.model_copy(update={"started_at": None}).baseline_comparable is False
    )
    assert (
        measurement.model_copy(update={"peak_memory_bytes": 0}).baseline_comparable
        is False
    )
    assert ResourceUsage(peak_memory_bytes=99).memory_measurement is None
    with pytest.raises(ValidationError, match="must match"):
        ResourceUsage(peak_memory_bytes=1, memory_measurement=measurement)
    with pytest.raises(ValidationError, match="cannot have peak"):
        MemoryMeasurement(
            status=MemoryMeasurementStatus.UNAVAILABLE,
            peak_memory_bytes=1,
        )


def test_processing_run_rejects_mismatched_config_hash_and_bad_times() -> None:
    with pytest.raises(ValidationError, match="does not match configuration"):
        processing_run(configuration_sha256="0" * 64)

    with pytest.raises(ValidationError, match="cannot precede"):
        processing_run(
            finished_at=datetime(2026, 7, 17, 11, tzinfo=UTC),
        )

    with pytest.raises(ValidationError, match="requires pipeline_run_id"):
        processing_run(repetition_group_id="benchmark-v1")


def test_processing_run_validates_the_full_output_policy_snapshot_hash() -> None:
    policy = {
        "schema": "deepcritical-document-output-policy-v1",
        "document_processing_config": {"ocr_enabled": True},
        "routing": {"algorithm_version": "deterministic-document-router-v1"},
        "algorithms": {"grobid_docling_alignment": "token-sequence-v1"},
        "contract_schemas": {"content_span": "1"},
    }
    run = processing_run(
        output_policy_snapshot=policy,
        output_policy_sha256=configuration_sha256(policy),
    )

    assert run.output_policy_sha256 == configuration_sha256(policy)
    with pytest.raises(ValidationError, match="does not match output_policy_snapshot"):
        processing_run(output_policy_snapshot=policy, output_policy_sha256="0" * 64)
    with pytest.raises(ValidationError, match="output_policy_sha256 is required"):
        processing_run(output_policy_snapshot=policy)


def test_processing_run_requires_unique_typed_outputs() -> None:
    output = processing_run().require_output("runtime_attestation")
    with pytest.raises(ValidationError, match="output names must be unique"):
        processing_run(outputs=(output, output))


def test_complete_runtime_identity_requires_task_bound_attestation() -> None:
    assert (
        processing_run(runtime_identity_required=True).runtime_attestation is not None
    )

    with pytest.raises(ValidationError, match="task-bound runtime attestation"):
        processing_run(
            runtime_identity_required=True,
            runtime_attestation=None,
            runtime_attestation_sha256=None,
            component_invocation_id=None,
            component_versions={},
            model_versions={},
            model_hashes={},
            container_image=None,
            container_digest=None,
            outputs=(),
        )

    with pytest.raises(ValidationError, match="component_invocation_id"):
        processing_run(component_invocation_id="another-task")

    with pytest.raises(ValidationError, match="must come from runtime attestation"):
        processing_run(
            component=ComponentDescriptor(
                component_id="docling",
                component_version="configured-but-unobserved",
                capability="document-conversion",
            )
        )


def test_content_span_accepts_pdf_jats_and_bioc_native_locators() -> None:
    pdf_span = ContentSpan(
        span_id="span-1",
        artifact_id="pmc-123-pdf",
        processing_run_id="run-docling-1",
        representation_anchor=RepresentationAnchor(
            product_id="product-docling-document",
            node_id="#/texts/12",
            char_start=4,
            char_end=19,
        ),
        content_sha256="3" * 64,
        source_locator=PdfLocator(
            page_number=2,
            bounding_box=PdfBoundingBox(
                left=10,
                top=20,
                right=110,
                bottom=50,
                page_width=612,
                page_height=792,
            ),
        ),
    )
    jats_span = pdf_span.model_copy(
        update={
            "span_id": "span-2",
            "source_locator": JatsLocator(
                xml_id="sec-results", xpath="/article/body/sec[2]/p[1]"
            ),
        }
    )
    bioc_span = ContentSpan.model_validate(
        {
            **pdf_span.model_dump(mode="json"),
            "span_id": "span-3",
            "source_locator": {
                "kind": "bioc",
                "document_index": 2,
                "document_id": "PMC123",
                "passage_index": 4,
                "offset": 120,
                "length": 15,
            },
        }
    )

    assert pdf_span.source_locator.kind == "pdf"
    assert jats_span.source_locator.kind == "jats"
    assert isinstance(bioc_span.source_locator, BioCLocator)
    assert bioc_span.source_locator.document_index == 2
    assert bioc_span.source_locator.document_id == "PMC123"


def test_locators_reject_missing_or_invalid_source_coordinates() -> None:
    with pytest.raises(ValidationError, match="requires xml_id or xpath"):
        JatsLocator()
    with pytest.raises(ValidationError, match="exceeds page width"):
        PdfBoundingBox(
            left=10,
            top=10,
            right=101,
            bottom=20,
            page_width=100,
        )
    with pytest.raises(ValidationError, match="greater than 0"):
        BioCLocator(
            document_index=0,
            document_id="PMC123",
            passage_index=0,
            offset=0,
            length=0,
        )


def test_diagnostic_has_machine_code_and_consistent_locator() -> None:
    locator = PdfLocator(
        page_number=3,
        bounding_box=PdfBoundingBox(left=1, top=2, right=3, bottom=4),
    )
    diagnostic = ProcessingDiagnostic(
        diagnostic_id="diagnostic-1",
        artifact_id="pmc-123-pdf",
        processing_run_id="run-docling-1",
        severity=DiagnosticSeverity.WARNING,
        stage="provenance-validation",
        code="pdf.missing_text_geometry",
        message="One item has no character box.",
        page_number=3,
        source_locator=locator,
    )

    assert diagnostic.code == "PDF.MISSING_TEXT_GEOMETRY"
    with pytest.raises(ValidationError, match="must agree"):
        ProcessingDiagnostic.model_validate(
            {**diagnostic.model_dump(), "page_number": 4}
        )


def test_resolved_diagnostic_requires_remediation_note() -> None:
    with pytest.raises(ValidationError, match="remediation_note"):
        ProcessingDiagnostic(
            diagnostic_id="diagnostic-2",
            artifact_id="pmc-123-pdf",
            severity=DiagnosticSeverity.ERROR,
            stage="ocr",
            code="OCR.TIMEOUT",
            message="OCR service timed out.",
            remediation_status=RemediationStatus.RESOLVED,
        )
