from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from DeepResearch.scripts.generate_document_processing_observations import (
    main as generate_observations_main,
)
from DeepResearch.scripts.run_document_processing_benchmark import (
    main as benchmark_main,
)
from DeepResearch.src.document_processing import benchmark as benchmark_module
from DeepResearch.src.document_processing.benchmark import (
    BenchmarkError,
    generate_candidate_observations,
    load_manifest,
    load_observations,
    run_benchmark,
)
from DeepResearch.src.document_processing.clients import (
    DoclingServeClient,
    GrobidClient,
    OCRmyPDFRunner,
)
from DeepResearch.src.document_processing.models import (
    ArtifactLocationRole,
    ArtifactRelationship,
    ContentSpan,
    DocumentArtifact,
    JatsLocator,
    ParserRun,
    ParserRunStatus,
    PdfBoundingBox,
    PdfLocator,
    ResourceUsage,
    RuntimeAttestation,
    RuntimeAttestationSource,
    configuration_sha256,
    sha256_bytes,
)
from DeepResearch.src.document_processing.pipeline import (
    DocumentProcessingConfig,
    DocumentProcessor,
)
from DeepResearch.src.document_processing.storage import ContentAddressedStore

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def _write_artifact(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_baseline_memory_requires_isolated_cgroup_provenance() -> None:
    scalar_only = {
        "provenance": {
            "resource_accounting": {
                "memory_scope": "heavy_parser_invocations",
                "memory_baseline_comparable": False,
                "memory_required_run_ids": ["docling-run"],
                "memory_measurements": [],
                "memory_environment_by_boundary": {},
            }
        }
    }
    with pytest.raises(BenchmarkError, match="isolated cgroup-v2"):
        benchmark_module._baseline_memory_environment(scalar_only, "PMC1")

    measured = {
        "provenance": {
            "resource_accounting": {
                "memory_scope": "heavy_parser_invocations",
                "memory_baseline_comparable": True,
                "memory_required_run_ids": ["docling-run"],
                "memory_measurements": [
                    {
                        "parser_run_id": "docling-run",
                        "parser_name": "docling",
                        "measurement": {
                            "status": "measured",
                            "method": "cgroup-v2-memory.peak",
                            "scope": "invocation_cgroup",
                            "exclusive": True,
                            "shared_overhead_excluded": True,
                            "peak_memory_bytes": 4096,
                            "environment_sha256": "b" * 64,
                            "measurement_id": "docling-run",
                            "boundary": "docling-rq-job",
                            "started_at": "2026-07-17T12:00:00Z",
                            "finished_at": "2026-07-17T12:00:01Z",
                            "memory_events": {"oom_kill": 0},
                        },
                    }
                ],
                "memory_environment_by_boundary": {"docling-rq-job": ["b" * 64]},
            }
        }
    }
    assert benchmark_module._baseline_memory_environment(measured, "PMC1") == {
        "docling-rq-job": "b" * 64
    }
    measured["provenance"]["resource_accounting"]["memory_measurements"][0][
        "measurement"
    ]["memory_events"]["oom_kill"] = 1
    with pytest.raises(BenchmarkError, match="not baseline-comparable"):
        benchmark_module._baseline_memory_environment(measured, "PMC1")


def test_baseline_memory_environment_unions_conditional_ocr_boundaries() -> None:
    combined: dict[str, str] = {}
    benchmark_module._merge_baseline_memory_environment(
        combined,
        {"docling": "a" * 64, "grobid": "b" * 64},
        context="born-digital document",
    )
    benchmark_module._merge_baseline_memory_environment(
        combined,
        {
            "docling": "a" * 64,
            "grobid": "b" * 64,
            "ocrmypdf": "c" * 64,
        },
        context="scanned document",
    )

    assert combined == {
        "docling": "a" * 64,
        "grobid": "b" * 64,
        "ocrmypdf": "c" * 64,
    }
    with pytest.raises(BenchmarkError, match=r"conflicting.*same boundary"):
        benchmark_module._merge_baseline_memory_environment(
            combined,
            {"docling": "d" * 64},
            context="drifted document",
        )


def _build_manifest(
    tmp_path: Path,
    document_ids: tuple[str, ...] = ("PMC1",),
    *,
    thresholds: dict[str, float] | None = None,
    reference_path: Path | None = None,
) -> Path:
    documents = []
    for document_id in document_ids:
        jats_path = tmp_path / "corpus" / document_id / "article.nxml"
        pdf_path = tmp_path / "corpus" / document_id / "article.pdf"
        jats_hash = _write_artifact(
            jats_path, f"<article id='{document_id}'/>".encode()
        )
        pdf_hash = _write_artifact(pdf_path, f"%PDF fixture {document_id}".encode())
        documents.append(
            {
                "id": document_id,
                "pmcid": document_id,
                "categories": [
                    "multi-column",
                    "scanned",
                    "table-heavy",
                    "figure-heavy",
                    "malformed",
                ],
                "reuse": {
                    "license": "CC0-1.0",
                    "license_url": "https://example.test/license",
                    "reuse_allowed": True,
                    "verified": True,
                },
                "artifacts": {
                    "jats": {
                        "path": str(jats_path.relative_to(tmp_path)).replace("\\", "/"),
                        "sha256": jats_hash,
                        "media_type": "application/jats+xml",
                    },
                    "pdf": {
                        "path": str(pdf_path.relative_to(tmp_path)).replace("\\", "/"),
                        "sha256": pdf_hash,
                        "media_type": "application/pdf",
                    },
                },
            }
        )
    manifest: dict[str, object] = {
        "schema_version": "1.0",
        "name": "unit-fixture",
        "artifact_root": ".",
        "allowed_outcomes": ["complete", "partial", "quarantined"],
        "thresholds": thresholds or {},
        "performance_limits": {},
        "documents": documents,
    }
    if reference_path is not None:
        manifest["observation_sets"] = {
            "reference": {
                "path": str(reference_path.relative_to(tmp_path)).replace("\\", "/"),
                "sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                "media_type": "application/x-ndjson",
            }
        }
    return _write_json(tmp_path / "manifest.json", manifest)


def _persist_artifact(
    tmp_path: Path,
    manifest_path: Path,
    *,
    source_artifact: str = "pdf",
) -> tuple[ContentAddressedStore, DocumentArtifact]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    descriptor = manifest["documents"][0]["artifacts"][source_artifact]
    source_path = tmp_path / descriptor["path"]
    store = ContentAddressedStore(tmp_path / "cas")
    source_blob = store.put_blob_file(source_path, expected_sha256=descriptor["sha256"])
    artifact = DocumentArtifact(
        artifact_id=f"artifact-PMC1-{source_artifact}",
        source_sha256=source_blob.sha256,
        acquisition_uri=f"https://example.test/PMC1.{source_artifact}",
        identifiers={"pmcid": "PMC1"},
        media_type=descriptor["media_type"],
        raw_location=source_blob.as_location(
            media_type=descriptor["media_type"],
            role=ArtifactLocationRole.RAW,
        ),
    )
    store.save_artifact(artifact)
    return store, artifact


def _persist_docling_run(
    store: ContentAddressedStore,
    artifact: DocumentArtifact,
    *,
    run_id: str,
    started_at: datetime,
    document: dict[str, Any],
    peak_memory_bytes: int | None = 4096,
    source_artifact: str = "pdf",
    status: ParserRunStatus = ParserRunStatus.COMPLETE,
    locator_offset: float = 0.0,
    extra_span_page: int | None = None,
    workflow_run_id: str | None = None,
    repetition_group_id: str | None = None,
    output_policy_snapshot: dict[str, Any] | None = None,
) -> ParserRun:
    document_blob = store.put_blob(
        json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    spans = []
    for index, item in enumerate(document["texts"]):
        assert isinstance(item, dict)
        text = item["text"]
        assert isinstance(text, str)
        source_locator = (
            PdfLocator(
                page_number=1,
                bounding_box=PdfBoundingBox(
                    left=10.0 + locator_offset,
                    top=10.0 + index * 10 + locator_offset,
                    right=100.0 + locator_offset,
                    bottom=18.0 + index * 10 + locator_offset,
                ),
            )
            if source_artifact == "pdf"
            else JatsLocator(
                xml_id=f"text-{index}",
                xpath=f"/article/body/p[{index + 1}]",
            )
        )
        spans.append(
            ContentSpan(
                span_id=f"{run_id}-span-{index}",
                artifact_id=artifact.artifact_id,
                parser_run_id=run_id,
                docling_item_ref=f"#/texts/{index}",
                item_char_start=0,
                item_char_end=len(text),
                content_sha256=sha256_bytes(text.encode("utf-8")),
                source_locator=source_locator,
            ).model_dump(mode="json")
        )
    if extra_span_page is not None:
        first_text = document["texts"][0]["text"]
        assert isinstance(first_text, str)
        spans.append(
            ContentSpan(
                span_id=f"{run_id}-extra-span",
                artifact_id=artifact.artifact_id,
                parser_run_id=run_id,
                docling_item_ref="#/texts/0",
                item_char_start=1,
                item_char_end=5,
                content_sha256=sha256_bytes(first_text[1:5].encode("utf-8")),
                source_locator=PdfLocator(
                    page_number=extra_span_page,
                    bounding_box=PdfBoundingBox(
                        left=20.0,
                        top=20.0,
                        right=40.0,
                        bottom=30.0,
                    ),
                ),
            ).model_dump(mode="json")
        )
    spans_blob = store.put_blob(
        json.dumps(spans, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    configuration = {"input_format": source_artifact, "pipeline": "fixture"}
    resolved_workflow_run_id = workflow_run_id or f"workflow-{run_id}"
    run = ParserRun(
        run_id=run_id,
        artifact_id=artifact.artifact_id,
        workflow_run_id=resolved_workflow_run_id,
        repetition_group_id=repetition_group_id,
        parser_name="docling",
        parser_version="2.113.0",
        configuration=configuration,
        configuration_sha256=configuration_sha256(configuration),
        output_policy_snapshot=output_policy_snapshot or {},
        output_policy_sha256=(
            configuration_sha256(output_policy_snapshot)
            if output_policy_snapshot is not None
            else None
        ),
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=2),
        status=status,
        resource_usage=ResourceUsage(
            wall_time_seconds=2.0,
            peak_memory_bytes=peak_memory_bytes,
        ),
        output_hashes={
            "docling_document": document_blob.sha256,
            "content_spans": spans_blob.sha256,
        },
        output_locations={
            "docling_document": document_blob.uri,
            "content_spans": spans_blob.uri,
        },
        completed_stages=("conversion", "validation", "span_generation"),
    )
    store.save_parser_run(run)
    return run


def _output_policy(
    store: ContentAddressedStore,
    **config_overrides: object,
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "docling_container_digest": "sha256:" + ("a" * 64),
        "grobid_container_digest": "sha256:" + ("b" * 64),
        "ocr_container_digest": "sha256:" + ("c" * 64),
    }
    values.update(config_overrides)
    config = DocumentProcessingConfig.model_validate(values)
    return DocumentProcessor(store, config=config)._output_policy_snapshot()


def _persist_ocr_run(
    store: ContentAddressedStore,
    artifact: DocumentArtifact,
    *,
    run_id: str,
    workflow_run_id: str,
    policy: dict[str, Any],
) -> ParserRun:
    config = policy["document_processing_config"]
    assert isinstance(config, dict)
    started_at = datetime(2025, 1, 1, tzinfo=UTC)
    finished_at = started_at + timedelta(seconds=1)
    invocation_id = f"fixture-{run_id}"
    digest = str(config["ocr_container_digest"])
    image = str(config["ocr_container_image"]).split("@", maxsplit=1)[0]
    attestation = RuntimeAttestation(
        parser_name="ocrmypdf",
        parser_version=str(config["ocrmypdf_version"]),
        invocation_id=invocation_id,
        source=RuntimeAttestationSource.DIGEST_ADDRESSED_OCI_INVOCATION,
        reporter_id="deepcritical-container-ocr-runner-v1",
        observed_at=started_at + timedelta(milliseconds=500),
        workload_id=f"fixture-container-{run_id}",
        container_reference=f"{image}@{digest}",
        container_digest=digest,
        component_versions={
            "ocrmypdf": str(config["ocrmypdf_version"]),
            "tesseract": "5.0.0",
        },
    )
    attestation_payload = attestation.model_dump(mode="json")
    attestation_blob = store.put_blob(
        json.dumps(
            attestation_payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    run = ParserRun(
        run_id=run_id,
        artifact_id=artifact.artifact_id,
        workflow_run_id=workflow_run_id,
        parser_name="ocrmypdf",
        parser_version=str(config["ocrmypdf_version"]),
        parser_invocation_id=invocation_id,
        runtime_identity_required=True,
        component_versions=dict(attestation.component_versions),
        container_image=attestation.container_reference,
        container_digest=attestation.container_digest,
        runtime_attestation=attestation,
        runtime_attestation_sha256=attestation_blob.sha256,
        configuration={"expected_ocrmypdf_version": config["ocrmypdf_version"]},
        configuration_sha256=configuration_sha256(
            {"expected_ocrmypdf_version": config["ocrmypdf_version"]}
        ),
        output_policy_snapshot=policy,
        output_policy_sha256=configuration_sha256(policy),
        started_at=started_at,
        finished_at=finished_at,
        status=ParserRunStatus.COMPLETE,
        resource_usage=ResourceUsage(wall_time_seconds=1.0, peak_memory_bytes=2048),
        output_hashes={"runtime_attestation": attestation_blob.sha256},
        output_locations={"runtime_attestation": attestation_blob.uri},
        completed_stages=("ocr_conversion",),
    )
    store.save_parser_run(run)
    return run


def test_persisted_policy_is_shared_when_conditional_ocr_stages_differ(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    policy = _output_policy(store)
    document = _docling_candidate_document()
    born_digital = _persist_docling_run(
        store,
        artifact,
        run_id="born-digital",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=document,
        workflow_run_id="born-workflow",
        output_policy_snapshot=policy,
    )
    scanned = _persist_docling_run(
        store,
        artifact,
        run_id="scanned",
        started_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        document=document,
        workflow_run_id="scanned-workflow",
        output_policy_snapshot=policy,
    )
    _persist_ocr_run(
        store,
        artifact,
        run_id="scanned-ocr",
        workflow_run_id="scanned-workflow",
        policy=policy,
    )

    assert (
        benchmark_module._workflow_pipeline_recipe(
            store, artifact.artifact_id, born_digital.workflow_run_id, None
        )
        == policy
    )
    assert (
        benchmark_module._workflow_pipeline_recipe(
            store, artifact.artifact_id, scanned.workflow_run_id, None
        )
        == policy
    )
    assert (
        benchmark_module._corpus_pipeline_recipe(store, [born_digital, scanned])
        == policy
    )


def test_baseline_policy_rejects_ocr_and_threshold_or_algorithm_drift(
    tmp_path: Path,
) -> None:
    store = ContentAddressedStore(tmp_path / "cas")
    policy = _output_policy(store)
    ocr_disabled = _output_policy(store, ocr_enabled=False)
    changed_threshold = _output_policy(store, alignment_minimum_score=0.8)
    changed_algorithm = json.loads(json.dumps(policy))
    changed_algorithm["algorithms"]["grobid_docling_alignment"] = "token-sequence-v2"

    for changed in (ocr_disabled, changed_threshold, changed_algorithm):
        collection = {
            "schema": "deepcritical-document-output-policy-collection-v1",
            "workflow_policies": [policy, changed],
        }
        workflows = {"first": policy, "second": changed}
        with pytest.raises(BenchmarkError, match="output-policy"):
            benchmark_module._require_baseline_output_policy(collection, workflows)


def test_output_policy_hash_captures_effective_parser_option_drift(
    tmp_path: Path,
) -> None:
    store = ContentAddressedStore(tmp_path / "cas")
    config = DocumentProcessingConfig(ocr_mode="local_cli")
    baseline = DocumentProcessor(
        store,
        grobid=GrobidClient(consolidate_citations=0),
        ocrmypdf=OCRmyPDFRunner(jobs=1, deskew=True),
        config=config,
    )._output_policy_snapshot()
    changed_grobid = DocumentProcessor(
        store,
        grobid=GrobidClient(consolidate_citations=1),
        ocrmypdf=OCRmyPDFRunner(jobs=1, deskew=True),
        config=config,
    )._output_policy_snapshot()
    changed_ocr = DocumentProcessor(
        store,
        grobid=GrobidClient(consolidate_citations=0),
        ocrmypdf=OCRmyPDFRunner(jobs=2, deskew=False),
        config=config,
    )._output_policy_snapshot()
    changed_docling_timing = DocumentProcessor(
        store,
        docling=DoclingServeClient(
            connect_timeout_seconds=11,
            poll_interval_seconds=0.5,
        ),
        grobid=GrobidClient(consolidate_citations=0),
        ocrmypdf=OCRmyPDFRunner(jobs=1, deskew=True),
        config=config,
    )._output_policy_snapshot()
    changed_grobid_timing = DocumentProcessor(
        store,
        grobid=GrobidClient(
            connect_timeout_seconds=11,
            consolidate_citations=0,
        ),
        ocrmypdf=OCRmyPDFRunner(jobs=1, deskew=True),
        config=config,
    )._output_policy_snapshot()

    assert configuration_sha256(baseline) != configuration_sha256(changed_grobid)
    assert configuration_sha256(baseline) != configuration_sha256(changed_ocr)
    assert configuration_sha256(baseline) != configuration_sha256(
        changed_docling_timing
    )
    assert configuration_sha256(baseline) != configuration_sha256(changed_grobid_timing)


def test_baseline_runtime_provenance_rejects_missing_or_mismatched_identity(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    policy = _output_policy(store)
    run = _persist_docling_run(
        store,
        artifact,
        run_id="runtime-mismatch",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
        workflow_run_id="runtime-workflow",
        output_policy_snapshot=policy,
    )

    provenance = benchmark_module._workflow_runtime_provenance(
        store,
        artifact.artifact_id,
        run.workflow_run_id,
        None,
        policy,
    )
    assert provenance["verified"] is False
    assert any(
        "runtime identity was not required" in issue for issue in provenance["issues"]
    )
    assert any(
        "task-bound runtime attestation is missing" in issue
        for issue in provenance["issues"]
    )


def test_candidate_runtime_validation_recomputes_attestation_trust(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    policy = _output_policy(store)
    run = _persist_ocr_run(
        store,
        artifact,
        run_id="candidate-runtime-ocr",
        workflow_run_id="candidate-runtime-workflow",
        policy=policy,
    )
    provenance = benchmark_module._workflow_runtime_provenance(
        store,
        artifact.artifact_id,
        run.workflow_run_id,
        None,
        policy,
    )

    assert provenance["verified"] is True
    assert (
        benchmark_module._candidate_runtime_identity_issues(provenance, policy, "PMC1")
        == []
    )

    spoofed = deepcopy(provenance)
    spoofed["verified"] = True
    stage = spoofed["stages"][0]
    attestation = stage["runtime_attestation"]
    attestation["component_versions"] = {
        "unrelated": "OCRmyPDF 17.4.1",
        "tesseract": "5.0.0-compatible",
    }
    stage["component_versions"] = dict(attestation["component_versions"])
    attestation_hash = configuration_sha256(attestation)
    stage["runtime_attestation_sha256"] = attestation_hash
    stage["runtime_attestation_output_sha256"] = attestation_hash

    issues = benchmark_module._candidate_runtime_identity_issues(
        spoofed, policy, "PMC1"
    )
    assert any("component 'ocrmypdf' differs from policy" in issue for issue in issues)

    wrong_reporter = deepcopy(provenance)
    wrong_reporter["verified"] = True
    reporter_stage = wrong_reporter["stages"][0]
    reporter_attestation = reporter_stage["runtime_attestation"]
    reporter_attestation["reporter_id"] = "untrusted-supervisor"
    reporter_hash = configuration_sha256(reporter_attestation)
    reporter_stage["runtime_attestation_sha256"] = reporter_hash
    reporter_stage["runtime_attestation_output_sha256"] = reporter_hash

    reporter_issues = benchmark_module._candidate_runtime_identity_issues(
        wrong_reporter, policy, "PMC1"
    )
    assert any(
        "attested reporter does not match policy" in issue for issue in reporter_issues
    )


def test_candidate_runtime_validation_never_trusts_verified_flag(
    tmp_path: Path,
) -> None:
    policy = _output_policy(ContentAddressedStore(tmp_path / "cas"))
    candidate_assertion = {
        "schema": "deepcritical-benchmark-runtime-provenance-v2",
        "verified": True,
        "issues": [],
        "stages": [{}],
    }

    issues = benchmark_module._candidate_runtime_identity_issues(
        candidate_assertion,
        policy,
        "PMC1",
    )

    assert issues
    assert any("parser_run_id is missing" in issue for issue in issues)
    assert any("parser_name is unsupported" in issue for issue in issues)


def _projected_content_spans_hash(
    store: ContentAddressedStore,
    run: ParserRun,
) -> str:
    spans = json.loads(store.read_blob(run.output_hashes["content_spans"]))
    normalized_spans = [
        {
            "docling_item_ref": span["docling_item_ref"],
            "item_char_start": span["item_char_start"],
            "item_char_end": span["item_char_end"],
            "content_sha256": span["content_sha256"],
            "source_locator": span["source_locator"],
        }
        for span in sorted(spans, key=lambda value: value["docling_item_ref"])
    ]
    return configuration_sha256(
        {
            "schema": "deepcritical-benchmark-projected-spans-v1",
            "spans": normalized_spans,
        }
    )


def _persist_scholarly_overlay(
    store: ContentAddressedStore,
    artifact: DocumentArtifact,
    docling_run: ParserRun,
    *,
    run_id: str = "alignment-run",
    reference_text: str = "Persisted scholarly bibliography entry",
    started_at: datetime | None = None,
    minimum_score: float | None = None,
    grobid_peak_memory_bytes: int | None = 8192,
    alignment_peak_memory_bytes: int | None = 2048,
    grobid_artifact: DocumentArtifact | None = None,
) -> ParserRun:
    overlay = {
        "algorithm_version": "token-sequence-v2",
        "aligned_count": 1,
        "unaligned_count": 0,
        "records": [
            {
                "annotation": {
                    "annotation_id": "annotation-1",
                    "kind": "biblStruct",
                    "text": reference_text,
                    "xml_id": "bibl-1",
                },
                "status": "aligned",
                "docling_item_ref": "#/texts/4",
                "score": 1.0,
            }
        ],
    }
    overlay_blob = store.put_blob(
        json.dumps(overlay, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    resolved_started_at = started_at or datetime(2025, 1, 1, 0, 2, tzinfo=UTC)
    resolved_grobid_artifact = grobid_artifact or artifact
    tei_blob = store.put_blob(b"<TEI><text>fixture</text></TEI>")
    grobid_configuration = {
        "input_sha256": resolved_grobid_artifact.source_sha256,
        "expected_grobid_version": "0.9.0",
        "coordinates": ["persName", "biblStruct"],
    }
    grobid_started_at = resolved_started_at - timedelta(seconds=30)
    grobid_run = ParserRun(
        run_id=f"grobid-{run_id}",
        artifact_id=resolved_grobid_artifact.artifact_id,
        workflow_run_id=docling_run.workflow_run_id,
        repetition_group_id=docling_run.repetition_group_id,
        parser_name="grobid",
        parser_version="0.9.0",
        configuration=grobid_configuration,
        configuration_sha256=configuration_sha256(grobid_configuration),
        started_at=grobid_started_at,
        finished_at=grobid_started_at + timedelta(seconds=3),
        status=ParserRunStatus.COMPLETE,
        resource_usage=ResourceUsage(
            wall_time_seconds=3.0,
            peak_memory_bytes=grobid_peak_memory_bytes,
        ),
        output_hashes={"grobid_tei": tei_blob.sha256},
        output_locations={"grobid_tei": tei_blob.uri},
        completed_stages=("fulltext_tei", "usability_validation"),
    )
    store.save_parser_run(grobid_run)

    configuration: dict[str, Any] = {
        "algorithm": "token-sequence-v2",
        "docling_document_sha256": docling_run.output_hashes["docling_document"],
        "grobid_tei_sha256": tei_blob.sha256,
    }
    if minimum_score is not None:
        configuration["minimum_score"] = minimum_score
    run = ParserRun(
        run_id=run_id,
        artifact_id=artifact.artifact_id,
        workflow_run_id=docling_run.workflow_run_id,
        repetition_group_id=docling_run.repetition_group_id,
        parser_name="docling-grobid-aligner",
        parser_version="2",
        configuration=configuration,
        configuration_sha256=configuration_sha256(configuration),
        started_at=resolved_started_at,
        finished_at=resolved_started_at + timedelta(seconds=1),
        status=ParserRunStatus.COMPLETE,
        resource_usage=ResourceUsage(
            wall_time_seconds=1.0,
            peak_memory_bytes=alignment_peak_memory_bytes,
        ),
        output_hashes={"alignment_overlay": overlay_blob.sha256},
        output_locations={"alignment_overlay": overlay_blob.uri},
        completed_stages=("tei_extraction", "alignment", "unaligned_marking"),
    )
    store.save_parser_run(run)
    return run


def _docling_candidate_document() -> dict[str, Any]:
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "paper",
        "body": {
            "self_ref": "#/body",
            "children": [{"$ref": "#/groups/0"}],
        },
        "furniture": {"self_ref": "#/furniture", "children": []},
        "groups": [
            {
                "self_ref": "#/groups/0",
                "children": [
                    {"$ref": "#/texts/0"},
                    {"$ref": "#/texts/1"},
                    {"$ref": "#/tables/0"},
                    {"$ref": "#/pictures/0"},
                ],
            }
        ],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "title",
                "level": 0,
                "text": "A deterministic paper",
            },
            {
                "self_ref": "#/texts/1",
                "label": "paragraph",
                "text": "The persisted result is the candidate evidence.",
            },
            {
                "self_ref": "#/texts/2",
                "label": "caption",
                "text": "Cohort table",
            },
            {
                "self_ref": "#/texts/3",
                "label": "caption",
                "text": "Study flow",
            },
            {
                "self_ref": "#/texts/4",
                "label": "reference",
                "text": "Docling-labelled bibliography entry",
            },
        ],
        "tables": [
            {
                "self_ref": "#/tables/0",
                "captions": [{"$ref": "#/texts/2"}],
                "data": {
                    "grid": [
                        [{"text": "Group"}, {"text": "Count"}],
                        [{"text": "A"}, {"text": "12"}],
                    ]
                },
            }
        ],
        "pictures": [
            {
                "self_ref": "#/pictures/0",
                "captions": [{"$ref": "#/texts/3"}],
            }
        ],
        "key_value_items": [],
        "pages": {"1": {"page_no": 1}},
    }


def _reference(document_id: str) -> dict[str, object]:
    return {
        "document_id": document_id,
        "outcome": "complete",
        "text": "Alpha beta gamma",
        "reading_order": ["Title", "Abstract", "Methods"],
        "headings": [{"text": "Methods", "level": 1}],
        "tables": [{"caption": "Cohort", "content_hash": HASH_C}],
        "figures": [{"source_id": "fig-1", "caption_id": "cap-1", "caption": "Flow"}],
        "references": [{"doi": "10.1000/example", "text": "Citation"}],
        "textual_items": [],
    }


def _candidate(
    document_id: str,
    *,
    text: str = "Alpha beta gamma",
    locator: object | None = None,
    output_hashes: list[str] | None = None,
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "parser": {
            "name": "fixture-parser",
            "version": "1.0.0",
            "configuration_hash": HASH_A,
        },
        "source_artifact": "pdf",
        "outcome": "complete",
        "text": text,
        "reading_order": ["Title", "Abstract", "Methods"],
        "headings": [{"text": "Methods", "level": 1}],
        "tables": [{"caption": "Cohort", "content_hash": HASH_C}],
        "figures": [{"source_id": "fig-1", "caption_id": "cap-1", "caption": "Flow"}],
        "references": [{"doi": "10.1000/example", "text": "Citation"}],
        "textual_items": [
            {
                "id": "#/texts/0",
                "text": text,
                "locator": locator or {"page": 1, "bbox": [0.0, 0.0, 10.0, 10.0]},
            }
        ],
        "content_hash": HASH_B,
        "output_hashes": output_hashes or [HASH_B, HASH_B],
        "elapsed_seconds": 2.0,
        "peak_memory_bytes": 1024,
    }


def test_baseline_benchmark_recomputes_runtime_identity_instead_of_verified_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference_path = _write_json(tmp_path / "reference.json", [_reference("PMC1")])
    manifest_path = _build_manifest(
        tmp_path,
        reference_path=reference_path,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        benchmark_module,
        "load_manifest",
        lambda *args, **kwargs: manifest,
    )
    policy = _output_policy(ContentAddressedStore(tmp_path / "policy-cas"))
    policy_hash = configuration_sha256(policy)
    candidate = _candidate("PMC1")
    candidate["parser"] = {
        "name": "fixture-parser",
        "version": "1.0.0",
        "configuration_hash": policy_hash,
    }
    candidate["provenance"] = {
        "pipeline_recipe": policy,
        "pipeline_recipe_sha256": policy_hash,
        "runtime_identity": {
            "schema": "deepcritical-benchmark-runtime-provenance-v2",
            "verified": True,
            "issues": [],
            "stages": [{}],
        },
    }
    candidate_path = _write_json(tmp_path / "candidate.json", [candidate])

    report = run_benchmark(
        manifest_path,
        candidate_path,
        reference_path,
        enforce_baseline=True,
    )

    document_violations = report["documents"][0]["violations"]
    assert any(
        "parser_run_id is missing" in violation for violation in document_violations
    )


def test_small_manifest_is_valid_until_baseline_is_explicit(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)

    loaded = load_manifest(manifest_path)

    assert loaded["name"] == "unit-fixture"
    with pytest.raises(BenchmarkError, match="between 50 and 75"):
        load_manifest(manifest_path, enforce_baseline=True)


def test_manifest_fails_clearly_when_artifact_hash_changes(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    (tmp_path / "corpus" / "PMC1" / "article.pdf").write_bytes(b"changed")

    with pytest.raises(BenchmarkError, match=r"artifacts\.pdf SHA-256 mismatch"):
        load_manifest(manifest_path)


def test_observations_accept_json_wrappers_and_jsonl(tmp_path: Path) -> None:
    wrapped_path = _write_json(
        tmp_path / "wrapped.json", {"observations": [_reference("PMC1")]}
    )
    jsonl_path = tmp_path / "candidate.jsonl"
    jsonl_path.write_text(
        "\n".join(
            json.dumps(_candidate(document_id)) for document_id in ("PMC1", "PMC2")
        ),
        encoding="utf-8",
    )

    assert set(load_observations(wrapped_path)) == {"PMC1"}
    assert set(load_observations(jsonl_path)) == {"PMC1", "PMC2"}


def test_identical_observations_produce_stable_passing_report(tmp_path: Path) -> None:
    thresholds = {
        "text_fidelity": 1.0,
        "reading_order": 1.0,
        "headings": 1.0,
        "tables": 1.0,
        "figure_caption_association": 1.0,
        "references": 1.0,
        "locator_coverage": 1.0,
        "determinism": 1.0,
    }
    reference_path = _write_json(tmp_path / "reference.json", [_reference("PMC1")])
    manifest_path = _build_manifest(
        tmp_path, thresholds=thresholds, reference_path=reference_path
    )
    candidate_path = _write_json(tmp_path / "candidate.json", [_candidate("PMC1")])

    first = run_benchmark(manifest_path, candidate_path)
    second = run_benchmark(manifest_path, candidate_path)

    assert first == second
    assert first["passed"] is True
    assert first["summary"]["scores"]["text_fidelity"]["aggregate"] == 1.0
    assert first["summary"]["scores"]["locator_coverage"]["aggregate"] == 1.0
    assert first["summary"]["outcomes"]["complete"] == 1
    assert first["summary"]["performance"]["documents_per_second"] == 0.5


def test_quality_gates_report_mismatch_without_hiding_report(tmp_path: Path) -> None:
    manifest_path = _build_manifest(
        tmp_path,
        thresholds={
            "text_fidelity": 0.7,
            "locator_coverage": 0.95,
            "determinism": 1.0,
        },
    )
    reference_path = _write_json(tmp_path / "reference.json", [_reference("PMC1")])
    candidate_path = _write_json(
        tmp_path / "candidate.json",
        [
            _candidate(
                "PMC1",
                text="Alpha",
                locator={"page": 1, "bbox": [10.0, 0.0, 0.0, 10.0]},
                output_hashes=[HASH_B, HASH_C],
            )
        ],
    )

    report = run_benchmark(manifest_path, candidate_path, reference_path)

    assert report["passed"] is False
    assert report["documents"][0]["scores"]["text_fidelity"] == 0.5
    assert report["documents"][0]["scores"]["locator_coverage"] == 0.0
    assert report["documents"][0]["scores"]["determinism"] == 0.0
    assert len(report["violations"]) == 3


def test_missing_observation_is_a_hard_error(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path, ("PMC1", "PMC2"))
    reference_path = _write_json(
        tmp_path / "reference.json", [_reference("PMC1"), _reference("PMC2")]
    )
    candidate_path = _write_json(tmp_path / "candidate.json", [_candidate("PMC1")])

    with pytest.raises(BenchmarkError, match=r"missing \['PMC2'\]"):
        run_benchmark(manifest_path, candidate_path, reference_path)


def test_locator_shape_must_match_the_selected_source_artifact(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    reference_path = _write_json(tmp_path / "reference.json", [_reference("PMC1")])
    pdf_candidate = _candidate("PMC1", locator={"xml_id": "sec-1"})
    candidate_path = _write_json(tmp_path / "candidate.json", [pdf_candidate])

    pdf_report = run_benchmark(manifest_path, candidate_path, reference_path)

    assert pdf_report["documents"][0]["scores"]["locator_coverage"] == 0.0

    jats_candidate = _candidate("PMC1", locator={"xml_id": "sec-1"})
    jats_candidate["source_artifact"] = "jats"
    _write_json(candidate_path, [jats_candidate])

    jats_report = run_benchmark(manifest_path, candidate_path, reference_path)

    assert jats_report["documents"][0]["scores"]["locator_coverage"] == 1.0


def test_figure_caption_scoring_ignores_parser_native_ids(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    reference = _reference("PMC1")
    candidate = _candidate("PMC1")
    assert isinstance(reference["figures"], list)
    assert isinstance(candidate["figures"], list)
    reference["figures"] = [
        {
            "source_id": "jats-figure-7",
            "caption_id": "jats-caption-7",
            "caption": "Flow",
        }
    ]
    candidate["figures"] = [
        {
            "source_id": "#/pictures/42",
            "caption_id": "#/texts/99",
            "caption": "Flow",
        }
    ]
    reference_path = _write_json(tmp_path / "reference.json", [reference])
    candidate_path = _write_json(tmp_path / "candidate.json", [candidate])

    report = run_benchmark(manifest_path, candidate_path, reference_path)

    assert report["documents"][0]["scores"]["figure_caption_association"] == 1.0


def test_reading_order_score_ignores_block_segmentation_but_detects_reordering() -> (
    None
):
    tokens = [f"token{index}" for index in range(96)]
    reference = [" ".join(tokens[:11]), " ".join(tokens[11:49]), " ".join(tokens[49:])]
    equivalent = [" ".join(tokens[:3]), " ".join(tokens[3:61]), " ".join(tokens[61:])]
    reordered = [" ".join(tokens[48:]), " ".join(tokens[:48])]
    one_token_deleted = [" ".join(tokens[1:])]

    assert benchmark_module._reading_order_score(equivalent, reference) == 1.0
    assert benchmark_module._reading_order_score(reordered, reference) < 1.0
    assert benchmark_module._reading_order_score(one_token_deleted, reference) > 0.98


def test_absent_optional_structures_are_not_applicable_or_macro_rewards(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    reference = _reference("PMC1")
    candidate = _candidate("PMC1")
    reference["tables"] = []
    reference["figures"] = []
    candidate["tables"] = []
    candidate["figures"] = []
    reference_path = _write_json(tmp_path / "reference.json", [reference])
    candidate_path = _write_json(tmp_path / "candidate.json", [candidate])

    report = run_benchmark(manifest_path, candidate_path, reference_path)
    document = report["documents"][0]

    assert document["scores"]["tables"] is None
    assert document["scores"]["figure_caption_association"] is None
    assert document["not_applicable_metrics"] == [
        "figure_caption_association",
        "tables",
    ]
    assert report["summary"]["scores"]["tables"] == {
        "aggregate": None,
        "mean": None,
        "minimum": None,
        "measured_documents": 0,
        "not_applicable_documents": 1,
    }

    reference["tables"] = [{"caption": "Expected table", "text": "A | B"}]
    _write_json(reference_path, [reference])
    report_with_missing_table = run_benchmark(
        manifest_path, candidate_path, reference_path
    )
    assert report_with_missing_table["documents"][0]["scores"]["tables"] == 0.0


def test_observation_generation_selects_static_output_policy_hash(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    first_policy = _output_policy(store)
    second_policy = _output_policy(store, alignment_minimum_score=0.87)
    first_run = _persist_docling_run(
        store,
        artifact,
        run_id="first-policy-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
        output_policy_snapshot=first_policy,
    )
    _persist_docling_run(
        store,
        artifact,
        run_id="second-policy-run",
        started_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
        output_policy_snapshot=second_policy,
    )
    first_policy_hash = configuration_sha256(first_policy)

    payload = generate_candidate_observations(
        manifest_path,
        store.root,
        output_policy_hash=first_policy_hash,
    )

    assert payload["selection"]["output_policy_hash"] == first_policy_hash
    assert payload["selection"]["configuration_hash"] is None
    assert payload["observations"][0]["provenance"]["parser_run_id"] == first_run.run_id
    with pytest.raises(BenchmarkError, match="mutually exclusive"):
        generate_candidate_observations(
            manifest_path,
            store.root,
            configuration_hash=first_run.configuration_sha256,
            output_policy_hash=first_policy_hash,
        )
    with pytest.raises(BenchmarkError, match="has no 'docling' parser run"):
        generate_candidate_observations(
            manifest_path,
            store.root,
            output_policy_hash="f" * 64,
        )


def test_enforced_generation_rejects_unmeasured_parser_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _build_manifest(tmp_path)
    manifest = load_manifest(manifest_path, verify_artifacts=False)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    policy = _output_policy(store)
    _persist_docling_run(
        store,
        artifact,
        run_id="unmeasured-baseline-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
        output_policy_snapshot=policy,
    )
    monkeypatch.setattr(
        benchmark_module, "load_manifest", lambda *args, **kwargs: manifest
    )
    monkeypatch.setattr(
        benchmark_module,
        "_require_baseline_output_policy",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        benchmark_module,
        "_workflow_runtime_provenance",
        lambda *args, **kwargs: {
            "schema": "deepcritical-benchmark-runtime-provenance-v1",
            "verified": True,
            "stages": [{"parser_name": "docling"}],
            "issues": [],
        },
    )

    with pytest.raises(BenchmarkError, match="isolated cgroup-v2"):
        generate_candidate_observations(
            manifest_path,
            store.root,
            enforce_baseline=True,
        )


def test_generates_deterministic_observations_from_persisted_cas(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    document = _docling_candidate_document()
    first_started = datetime(2025, 1, 1, tzinfo=UTC)
    _persist_docling_run(
        store,
        artifact,
        run_id="docling-run-1",
        started_at=first_started,
        document=document,
        workflow_run_id="workflow-repeat-1",
        repetition_group_id="repeat-group",
    )
    latest_run = _persist_docling_run(
        store,
        artifact,
        run_id="docling-run-2",
        started_at=first_started + timedelta(minutes=1),
        document=document,
        workflow_run_id="workflow-repeat-2",
        repetition_group_id="repeat-group",
    )

    first = generate_candidate_observations(manifest_path, store.root)
    second = generate_candidate_observations(manifest_path, store.root)

    assert first == second
    assert first["schema_version"] == "1.0"
    observation = first["observations"][0]
    assert observation["outcome"] == "complete"
    assert observation["parser"] == {
        "name": "docling",
        "version": "2.113.0",
        "configuration_hash": first["selection"]["pipeline_recipe_sha256"],
    }
    assert (
        observation["provenance"]["pipeline_recipe_sha256"]
        == (first["selection"]["pipeline_recipe_sha256"])
    )
    assert observation["reading_order"] == [
        "A deterministic paper",
        "The persisted result is the candidate evidence.",
        "Cohort table",
        "Study flow",
        "Docling-labelled bibliography entry",
    ]
    assert observation["headings"] == [{"text": "A deterministic paper", "level": 0}]
    assert observation["tables"] == [
        {
            "source_id": "#/tables/0",
            "caption": "Cohort table",
            "text": "Group | Count\nA | 12",
        }
    ]
    assert observation["figures"] == [
        {
            "source_id": "#/pictures/0",
            "caption_id": "#/texts/3",
            "caption": "Study flow",
        }
    ]
    assert observation["references"] == [
        {
            "source_id": "#/texts/4",
            "text": "Docling-labelled bibliography entry",
        }
    ]
    assert observation["textual_items"][0]["locator"] == {
        "page": 1,
        "bbox": [10.0, 10.0, 100.0, 18.0],
    }
    expected_content_hash = configuration_sha256(
        {
            "schema": "deepcritical-benchmark-projected-content-v1",
            "docling_document_sha256": latest_run.output_hashes["docling_document"],
            "projected_content_spans_sha256": _projected_content_spans_hash(
                store,
                latest_run,
            ),
        }
    )
    assert observation["content_hash"] == expected_content_hash
    assert observation["output_hashes"] == [
        expected_content_hash,
        expected_content_hash,
    ]
    assert observation["provenance"]["peak_memory_bytes_recorded"] is True


def test_repeat_hashes_include_all_locator_spans_not_only_representative(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    document = _docling_candidate_document()
    _persist_docling_run(
        store,
        artifact,
        run_id="docling-run-1",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=document,
        workflow_run_id="workflow-repeat-1",
        repetition_group_id="repeat-group",
        extra_span_page=2,
    )
    _persist_docling_run(
        store,
        artifact,
        run_id="docling-run-2",
        started_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        document=document,
        extra_span_page=3,
        workflow_run_id="workflow-repeat-2",
        repetition_group_id="repeat-group",
    )

    payload = generate_candidate_observations(manifest_path, store.root)
    observation = payload["observations"][0]

    assert observation["textual_items"][0]["locator"]["page"] == 1
    assert len(observation["output_hashes"]) == 2
    assert len(set(observation["output_hashes"])) == 2
    assert observation["provenance"]["determinism"] == {
        "status": "measured",
        "workflow_run_ids": ["workflow-repeat-2", "workflow-repeat-1"],
        "repetition_group_id": "repeat-group",
    }


def test_repeat_hashes_reject_a_corrupt_persisted_component(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    document = _docling_candidate_document()
    first_run = _persist_docling_run(
        store,
        artifact,
        run_id="docling-run-1",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=document,
        workflow_run_id="workflow-repeat-1",
        repetition_group_id="repeat-group",
    )
    _persist_docling_run(
        store,
        artifact,
        run_id="docling-run-2",
        started_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        document=document,
        workflow_run_id="workflow-repeat-2",
        repetition_group_id="repeat-group",
    )
    store.blob_path(first_run.output_hashes["content_spans"]).write_bytes(b"corrupt")

    with pytest.raises(BenchmarkError, match=r"stored blob .* hashes to"):
        generate_candidate_observations(manifest_path, store.root)


def test_generation_uses_persisted_grobid_bibliography_without_inference(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    docling_run = _persist_docling_run(
        store,
        artifact,
        run_id="docling-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
    )
    _persist_scholarly_overlay(store, artifact, docling_run)

    payload = generate_candidate_observations(manifest_path, store.root)
    observation = payload["observations"][0]

    assert observation["references"] == [
        {
            "source_id": "bibl-1",
            "text": "Persisted scholarly bibliography entry",
        }
    ]
    assert "doi" not in observation["references"][0]
    assert "pmid" not in observation["references"][0]
    assert observation["provenance"]["reference_source"] == ("grobid_alignment_overlay")
    assert observation["provenance"]["scholarly_overlay"]["parser_run_id"] == (
        "alignment-run"
    )


def test_generation_pins_composite_alignment_identity_and_repeat_hashes(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    docling_run = _persist_docling_run(
        store,
        artifact,
        run_id="docling-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
    )
    different_configuration = _persist_scholarly_overlay(
        store,
        artifact,
        docling_run,
        run_id="alignment-different-configuration",
        reference_text="Different configuration",
        started_at=datetime(2025, 1, 1, 0, 2, tzinfo=UTC),
        minimum_score=0.5,
    )
    _persist_scholarly_overlay(
        store,
        artifact,
        docling_run,
        run_id="alignment-repeat-1",
        reference_text="First output from matching configuration",
        started_at=datetime(2025, 1, 1, 0, 3, tzinfo=UTC),
        minimum_score=0.72,
    )
    selected_alignment = _persist_scholarly_overlay(
        store,
        artifact,
        docling_run,
        run_id="alignment-repeat-2",
        reference_text="Selected output from matching configuration",
        started_at=datetime(2025, 1, 1, 0, 4, tzinfo=UTC),
        minimum_score=0.72,
        alignment_peak_memory_bytes=32768,
    )
    selected_grobid = store.get_parser_run("grobid-alignment-repeat-2")

    payload = generate_candidate_observations(manifest_path, store.root)
    observation = payload["observations"][0]

    _legacy_identity_components = {
        "schema": "deepcritical-benchmark-parser-composition-v1",
        "primary": {
            "parser_name": docling_run.parser_name,
            "parser_version": docling_run.parser_version,
            "configuration_sha256": docling_run.configuration_sha256,
        },
        "derivations": [],
        "grobid": {
            "parser_name": selected_grobid.parser_name,
            "parser_version": selected_grobid.parser_version,
            "configuration_sha256": configuration_sha256(
                {
                    "expected_grobid_version": "0.9.0",
                    "coordinates": ["persName", "biblStruct"],
                }
            ),
        },
        "scholarly_alignment": {
            "parser_name": selected_alignment.parser_name,
            "parser_version": selected_alignment.parser_version,
            "configuration_sha256": configuration_sha256(
                {
                    "algorithm": "token-sequence-v1",
                    "minimum_score": 0.72,
                }
            ),
        },
    }
    expected_content_hash = configuration_sha256(
        {
            "schema": "deepcritical-benchmark-projected-content-v1",
            "docling_document_sha256": docling_run.output_hashes["docling_document"],
            "projected_content_spans_sha256": _projected_content_spans_hash(
                store,
                docling_run,
            ),
            "scholarly_alignment_sha256": selected_alignment.output_hashes[
                "alignment_overlay"
            ],
        }
    )
    excluded_configuration_hash = configuration_sha256(
        {
            "schema": "deepcritical-benchmark-projected-content-v1",
            "docling_document_sha256": docling_run.output_hashes["docling_document"],
            "projected_content_spans_sha256": _projected_content_spans_hash(
                store,
                docling_run,
            ),
            "scholarly_alignment_sha256": different_configuration.output_hashes[
                "alignment_overlay"
            ],
        }
    )

    assert observation["references"] == [
        {
            "source_id": "bibl-1",
            "text": "Selected output from matching configuration",
        }
    ]
    assert observation["parser"] == {
        "name": "docling",
        "version": "2.113.0",
        "configuration_hash": payload["selection"]["pipeline_recipe_sha256"],
    }
    assert observation["content_hash"] == expected_content_hash
    assert observation["output_hashes"] == [expected_content_hash]
    assert excluded_configuration_hash not in observation["output_hashes"]
    scholarly_provenance = observation["provenance"]["scholarly_overlay"]
    assert scholarly_provenance["parser_run_id"] == selected_alignment.run_id
    assert scholarly_provenance["workflow_run_id"] == docling_run.workflow_run_id
    assert scholarly_provenance["grobid_parser_run"]["parser_run_id"] == (
        selected_grobid.run_id
    )
    assert observation["provenance"]["candidate_parser_composition"]["schema"] == (
        "deepcritical-benchmark-executed-composition-v2"
    )
    assert observation["elapsed_seconds"] > 6.0
    assert observation["peak_memory_bytes"] == 8192
    accounting = observation["provenance"]["resource_accounting"]
    assert accounting["elapsed_seconds_method"] == "sum_stage_wall_time"
    assert (
        accounting["peak_memory_bytes_method"] == "max_heavy_parser_stage_peak_memory"
    )
    assert accounting["parser_run_ids"][0] == docling_run.run_id
    assert accounting["parser_run_ids"][-1] == selected_alignment.run_id
    assert selected_alignment.run_id not in accounting["memory_required_run_ids"]
    assert accounting["memory_excluded_runs"] == [
        {
            "parser_run_id": selected_alignment.run_id,
            "parser_name": "docling-grobid-aligner",
            "reason": "not_an_isolated_heavy_parser_invocation",
        }
    ]
    assert observation["provenance"]["determinism"]["status"] == "unmeasured"


def test_composite_resource_accounting_does_not_zero_fill_unknown_memory(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    docling_run = _persist_docling_run(
        store,
        artifact,
        run_id="docling-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
    )
    _persist_scholarly_overlay(
        store,
        artifact,
        docling_run,
        grobid_peak_memory_bytes=None,
    )

    payload = generate_candidate_observations(manifest_path, store.root)
    observation = payload["observations"][0]

    assert observation["elapsed_seconds"] == 6.0
    assert "peak_memory_bytes" not in observation
    assert observation["provenance"]["peak_memory_bytes_recorded"] is False
    assert (
        observation["provenance"]["resource_accounting"]["peak_memory_bytes_method"]
        == "unmeasured_when_any_heavy_parser_stage_missing"
    )


def test_composite_resolves_ocr_derivative_grobid_lineage(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    docling_run = _persist_docling_run(
        store,
        artifact,
        run_id="docling-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
    )
    original_grobid_configuration = {
        "input_sha256": artifact.source_sha256,
        "expected_grobid_version": "0.9.0",
        "coordinates": ["persName", "biblStruct"],
    }
    original_grobid_run = ParserRun(
        run_id="grobid-original-failed",
        artifact_id=artifact.artifact_id,
        workflow_run_id=docling_run.workflow_run_id,
        repetition_group_id=docling_run.repetition_group_id,
        parser_name="grobid",
        parser_version="0.9.0",
        configuration=original_grobid_configuration,
        configuration_sha256=configuration_sha256(original_grobid_configuration),
        started_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        finished_at=datetime(2025, 1, 1, 0, 1, 2, tzinfo=UTC),
        status=ParserRunStatus.FAILED,
        resource_usage=ResourceUsage(wall_time_seconds=2.0, peak_memory_bytes=12288),
        warnings=("GROBID input has insufficient text",),
        completed_stages=("fulltext_tei",),
    )
    store.save_parser_run(original_grobid_run)
    ocr_pdf = store.put_blob(b"%PDF searchable OCR derivative")
    ocr_configuration = {
        "input_sha256": artifact.source_sha256,
        "expected_ocrmypdf_version": "17.4.1",
        "languages": ["eng"],
    }
    ocr_started_at = datetime(2025, 1, 1, 0, 2, tzinfo=UTC)
    ocr_run = ParserRun(
        run_id="ocr-run",
        artifact_id=artifact.artifact_id,
        workflow_run_id=docling_run.workflow_run_id,
        repetition_group_id=docling_run.repetition_group_id,
        parser_name="ocrmypdf",
        parser_version="17.4.1",
        configuration=ocr_configuration,
        configuration_sha256=configuration_sha256(ocr_configuration),
        started_at=ocr_started_at,
        finished_at=ocr_started_at + timedelta(seconds=4),
        status=ParserRunStatus.COMPLETE,
        resource_usage=ResourceUsage(
            wall_time_seconds=4.0,
            peak_memory_bytes=16384,
        ),
        output_hashes={"ocr_pdf": ocr_pdf.sha256},
        output_locations={"ocr_pdf": ocr_pdf.uri},
        completed_stages=("ocr", "searchable_pdf_validation"),
    )
    store.save_parser_run(ocr_run)
    derivative = DocumentArtifact(
        artifact_id="artifact-PMC1-ocr-derivative",
        source_sha256=ocr_pdf.sha256,
        acquisition_uri="https://example.test/PMC1.pdf#ocr",
        identifiers={"pmcid": "PMC1"},
        media_type="application/pdf",
        relationship=ArtifactRelationship.DERIVATIVE,
        parent_artifact_id=artifact.artifact_id,
        raw_location=ocr_pdf.as_location(
            media_type="application/pdf",
            role=ArtifactLocationRole.RAW,
            created_by_run_id=ocr_run.run_id,
        ),
    )
    store.save_artifact(derivative)
    alignment_run = _persist_scholarly_overlay(
        store,
        artifact,
        docling_run,
        run_id="alignment-ocr",
        started_at=datetime(2025, 1, 1, 0, 3, tzinfo=UTC),
        grobid_artifact=derivative,
    )
    grobid_run = store.get_parser_run("grobid-alignment-ocr")

    payload = generate_candidate_observations(manifest_path, store.root)
    observation = payload["observations"][0]

    assert observation["parser"] == {
        "name": "docling",
        "version": "2.113.0",
        "configuration_hash": payload["selection"]["pipeline_recipe_sha256"],
    }
    assert observation["elapsed_seconds"] == 12.0
    assert observation["peak_memory_bytes"] == 16384
    scholarly = observation["provenance"]["scholarly_overlay"]
    assert scholarly["grobid_parser_run"]["artifact_id"] == derivative.artifact_id
    assert scholarly["derivation_parser_runs"] == [
        {
            "parser_run_id": ocr_run.run_id,
            "workflow_run_id": ocr_run.workflow_run_id,
            "repetition_group_id": ocr_run.repetition_group_id,
            "parser_name": ocr_run.parser_name,
            "parser_version": ocr_run.parser_version,
            "configuration_sha256": ocr_run.configuration_sha256,
        }
    ]
    assert observation["provenance"]["resource_accounting"]["parser_run_ids"] == [
        docling_run.run_id,
        original_grobid_run.run_id,
        ocr_run.run_id,
        grobid_run.run_id,
        alignment_run.run_id,
    ]


def test_generation_preserves_partial_items_with_unresolved_captions(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    document = _docling_candidate_document()
    document["tables"][0]["captions"] = [{"$ref": "#/texts/999"}]
    document["pictures"][0]["captions"] = [
        {"$ref": "#/tables/0"},
        {"unexpected": "caption"},
    ]
    _persist_docling_run(
        store,
        artifact,
        run_id="partial-docling-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=document,
        workflow_run_id="workflow-repeat-2",
        repetition_group_id="repeat-group",
        status=ParserRunStatus.PARTIAL,
    )

    payload = generate_candidate_observations(manifest_path, store.root)
    observation = payload["observations"][0]

    assert observation["outcome"] == "partial"
    assert observation["tables"][0] == {
        "source_id": "#/tables/0",
        "caption": "",
        "caption_status": "unaligned",
        "caption_diagnostics": [{"source_id": "#/texts/999", "reason": "missing_item"}],
        "unresolved_caption_refs": ["#/texts/999"],
        "text": "Group | Count\nA | 12",
    }
    assert observation["figures"][0] == {
        "source_id": "#/pictures/0",
        "caption_id": "#/tables/0",
        "caption": "",
        "caption_status": "unaligned",
        "caption_diagnostics": [
            {
                "path": "captions[1]",
                "reason": "malformed_reference",
                "value_type": "object",
            },
            {"source_id": "#/tables/0", "reason": "non_text_item"},
        ],
        "unresolved_caption_refs": ["#/tables/0"],
    }


def test_generation_preserves_native_jats_locators(tmp_path: Path) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(
        tmp_path,
        manifest_path,
        source_artifact="jats",
    )
    _persist_docling_run(
        store,
        artifact,
        run_id="jats-docling-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
        source_artifact="jats",
    )

    payload = generate_candidate_observations(
        manifest_path,
        store.root,
        source_artifact="jats",
    )
    observation = payload["observations"][0]

    assert observation["source_artifact"] == "jats"
    assert observation["textual_items"][0]["locator"] == {
        "xml_id": "text-0",
        "xpath": "/article/body/p[1]",
    }


def test_generation_preserves_explicit_quarantine_without_empty_success(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    started_at = datetime(2025, 1, 1, tzinfo=UTC)
    configuration = {"policy": "bounded-input-v1"}
    run = ParserRun(
        run_id="preflight-quarantine",
        artifact_id=artifact.artifact_id,
        parser_name="document-preflight",
        parser_version="1",
        configuration=configuration,
        configuration_sha256=configuration_sha256(configuration),
        started_at=started_at,
        finished_at=started_at,
        status=ParserRunStatus.QUARANTINED,
        warnings=("encrypted source",),
        completed_stages=("bounded_input_inspection", "policy_decision"),
    )
    store.save_parser_run(run)

    payload = generate_candidate_observations(manifest_path, store.root)
    observation = payload["observations"][0]

    assert observation["outcome"] == "quarantined"
    assert observation["parser"]["name"] == "document-preflight"
    assert observation["text"] == ""
    assert "content_hash" not in observation
    assert observation["provenance"]["warnings"] == ["encrypted source"]


def test_observation_generation_cli_writes_loadable_candidate_set(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    store, artifact = _persist_artifact(tmp_path, manifest_path)
    _persist_docling_run(
        store,
        artifact,
        run_id="docling-run",
        started_at=datetime(2025, 1, 1, tzinfo=UTC),
        document=_docling_candidate_document(),
        peak_memory_bytes=None,
    )
    output_path = tmp_path / "candidate-observations.json"

    exit_code = generate_observations_main(
        [
            str(manifest_path),
            "--cas",
            str(store.root),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    observations = load_observations(output_path)
    assert set(observations) == {"PMC1"}
    assert "peak_memory_bytes" not in observations["PMC1"]
    assert observations["PMC1"]["provenance"]["peak_memory_bytes_recorded"] is False


def test_cli_writes_machine_readable_report_and_returns_gate_status(
    tmp_path: Path,
) -> None:
    manifest_path = _build_manifest(tmp_path)
    reference_path = _write_json(tmp_path / "reference.json", [_reference("PMC1")])
    candidate_path = _write_json(tmp_path / "candidate.json", [_candidate("PMC1")])
    report_path = tmp_path / "report.json"

    exit_code = benchmark_main(
        [
            str(manifest_path),
            "--candidate",
            str(candidate_path),
            "--reference",
            str(reference_path),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert json.loads(report_path.read_text(encoding="utf-8"))["passed"] is True
