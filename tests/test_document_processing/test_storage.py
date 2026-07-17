"""Tests for immutable content-addressed document-processing storage."""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import ValidationError

from DeepResearch.src.document_processing import storage as storage_module
from DeepResearch.src.document_processing.models import (
    ArtifactLocationRole,
    ArtifactRelationship,
    DiagnosticSeverity,
    DocumentArtifact,
    ExternalTaskCheckpoint,
    ParseDiagnostic,
    ParserRun,
    ParserRunStatus,
    configuration_sha256,
)
from DeepResearch.src.document_processing.storage import (
    BlobNotFoundError,
    BlobTooLargeError,
    ContentAddressedStore,
    HashMismatchError,
    RecordConflictError,
    RecordNotFoundError,
)


@pytest.fixture
def store(tmp_path: Path) -> ContentAddressedStore:
    return ContentAddressedStore(tmp_path / "document-store")


def save_artifact(
    store: ContentAddressedStore,
    artifact_id: str = "artifact-1",
    *,
    relationship: ArtifactRelationship = ArtifactRelationship.SOURCE,
    parent_artifact_id: str | None = None,
) -> DocumentArtifact:
    blob = store.put_blob(b"source document bytes")
    artifact = DocumentArtifact(
        artifact_id=artifact_id,
        source_sha256=blob.sha256,
        acquisition_uri=f"https://example.test/{artifact_id}.pdf",
        identifiers={"pmc": f"PMC-{artifact_id}"},
        media_type="application/pdf",
        relationship=relationship,
        parent_artifact_id=parent_artifact_id,
        raw_location=blob.as_location(
            media_type="application/pdf", role=ArtifactLocationRole.RAW
        ),
    )
    store.save_artifact(artifact)
    return artifact


def make_run(
    artifact_id: str,
    run_id: str,
    status: ParserRunStatus,
    *,
    minute: int = 0,
    output_hashes: dict[str, str] | None = None,
    output_locations: dict[str, str] | None = None,
    output_policy_snapshot: dict[str, object] | None = None,
) -> ParserRun:
    config = {"do_ocr": True}
    started_at = datetime(2026, 7, 17, 12, minute, tzinfo=UTC)
    return ParserRun(
        run_id=run_id,
        artifact_id=artifact_id,
        parser_name="docling",
        parser_version="2.113.0",
        configuration=config,
        configuration_sha256=configuration_sha256(config),
        output_policy_snapshot=output_policy_snapshot or {},
        output_policy_sha256=(
            configuration_sha256(output_policy_snapshot)
            if output_policy_snapshot
            else None
        ),
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=2),
        status=status,
        output_hashes=output_hashes or {},
        output_locations=output_locations or {},
    )


def test_blob_write_is_content_addressed_verified_and_idempotent(
    store: ContentAddressedStore,
) -> None:
    first = store.put_blob(b"same bytes")
    second = store.put_blob(b"same bytes", expected_sha256=first.sha256)

    assert first == second
    assert first.uri == f"cas://sha256/{first.sha256}"
    assert first.path == store.blob_path(first.sha256)
    assert store.read_blob(first.sha256) == b"same bytes"
    assert len(list((store.root / "blobs" / "sha256").rglob("*"))) == 2


def test_blob_and_record_publication_fsync_destination_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fsynced_directories: list[Path] = []
    monkeypatch.setattr(
        storage_module,
        "_fsync_directory",
        lambda directory: fsynced_directories.append(Path(directory)),
    )
    durable_store = ContentAddressedStore(tmp_path / "durable-store")
    fsynced_directories.clear()

    blob = durable_store.put_blob(b"durably published")

    assert fsynced_directories.count(blob.path.parent) >= 2
    assert blob.path.parent.parent in fsynced_directories

    artifact = DocumentArtifact(
        artifact_id="durable-artifact",
        source_sha256=blob.sha256,
        acquisition_uri="https://example.test/durable.pdf",
        media_type="application/pdf",
        raw_location=blob.as_location(
            media_type="application/pdf",
            role=ArtifactLocationRole.RAW,
        ),
    )
    fsynced_directories.clear()
    record_path = durable_store.save_artifact(artifact)

    assert fsynced_directories == [record_path.parent]


def test_directory_fsync_supports_the_host_platform(tmp_path: Path) -> None:
    storage_module._fsync_directory(tmp_path)


def test_blob_expected_hash_and_tamper_are_detected(
    store: ContentAddressedStore,
) -> None:
    with pytest.raises(HashMismatchError, match="expected blob"):
        store.put_blob(b"actual", expected_sha256="0" * 64)

    blob = store.put_blob(b"untampered")
    blob.path.write_bytes(b"tampered")
    with pytest.raises(HashMismatchError, match="hashes to"):
        store.read_blob(blob.sha256)


def test_streaming_blob_limit_never_publishes_oversized_content(
    store: ContentAddressedStore,
) -> None:
    with pytest.raises(BlobTooLargeError) as error:
        store.put_blob(BytesIO(b"012345"), max_bytes=5)

    assert error.value.max_bytes == 5
    assert error.value.observed_bytes == 6
    assert not any(path.is_file() for path in (store.root / "blobs").rglob("*"))
    assert not any((store.root / ".tmp").iterdir())

    exact = store.put_blob(BytesIO(b"012345"), max_bytes=6)
    assert exact.byte_size == 6


def test_missing_blob_is_explicit(store: ContentAddressedStore) -> None:
    with pytest.raises(BlobNotFoundError, match="blob not found"):
        store.read_blob("f" * 64)


def test_artifact_records_are_idempotent_and_conflicts_never_overwrite(
    store: ContentAddressedStore,
) -> None:
    artifact = save_artifact(store)
    first_path = store.save_artifact(artifact)
    second_path = store.save_artifact(artifact)

    assert first_path == second_path
    assert store.get_artifact(artifact.artifact_id) == artifact

    conflicting = artifact.model_copy(
        update={"acquisition_uri": "https://different.test/source.pdf"}
    )
    with pytest.raises(RecordConflictError, match="different content"):
        store.save_artifact(conflicting)
    assert store.get_artifact(artifact.artifact_id) == artifact


def test_save_revalidates_model_copy_before_persisting(
    store: ContentAddressedStore,
) -> None:
    blob = store.put_blob(b"source document bytes")
    artifact = DocumentArtifact(
        artifact_id="artifact-invalid-copy",
        source_sha256=blob.sha256,
        acquisition_uri="https://example.test/invalid-copy.pdf",
        media_type="application/pdf",
        raw_location=blob.as_location(
            media_type="application/pdf", role=ArtifactLocationRole.RAW
        ),
    )
    invalid = artifact.model_copy(update={"source_sha256": "0" * 64})

    with pytest.raises(
        ValidationError, match=r"source_sha256 must match raw_location\.sha256"
    ):
        store.save_artifact(invalid)
    with pytest.raises(RecordNotFoundError, match="artifact-invalid-copy"):
        store.get_artifact(artifact.artifact_id)


def test_artifact_save_verifies_location_hash_size_and_parent(
    store: ContentAddressedStore,
) -> None:
    blob = store.put_blob(b"child")
    child = DocumentArtifact(
        artifact_id="supplement-1",
        source_sha256=blob.sha256,
        acquisition_uri="https://example.test/supplement-1.pdf",
        media_type="application/pdf",
        relationship=ArtifactRelationship.SUPPLEMENT,
        parent_artifact_id="missing-parent",
        raw_location=blob.as_location(
            media_type="application/pdf", role=ArtifactLocationRole.RAW
        ),
    )
    with pytest.raises(RecordNotFoundError, match="missing-parent"):
        store.save_artifact(child)

    save_artifact(store, "parent")
    wrong_size = child.model_copy(
        update={
            "parent_artifact_id": "parent",
            "raw_location": child.raw_location.model_copy(update={"byte_size": 999}),
        }
    )
    with pytest.raises(HashMismatchError, match="size"):
        store.save_artifact(wrong_size)


def test_derived_artifact_creator_lineage_requires_matching_durable_run(
    store: ContentAddressedStore,
) -> None:
    parent = save_artifact(store, "parent-lineage")
    derivative_blob = store.put_blob(b"searchable derivative")

    def derivative_for(run_id: str) -> DocumentArtifact:
        return DocumentArtifact(
            artifact_id=f"derivative-{run_id}",
            source_sha256=derivative_blob.sha256,
            acquisition_uri=f"derived://ocr/{run_id}",
            media_type="application/pdf",
            relationship=ArtifactRelationship.DERIVATIVE,
            parent_artifact_id=parent.artifact_id,
            raw_location=derivative_blob.as_location(
                media_type="application/pdf",
                role=ArtifactLocationRole.RAW,
                created_by_run_id=run_id,
            ),
        )

    with pytest.raises(RecordNotFoundError, match="run-missing-creator"):
        store.save_artifact(derivative_for("run-missing-creator"))

    unrelated_output = store.put_blob(b"different output")
    wrong_output_run = make_run(
        parent.artifact_id,
        "run-wrong-output",
        ParserRunStatus.COMPLETE,
        output_hashes={"searchable_pdf": unrelated_output.sha256},
    )
    store.save_parser_run(wrong_output_run)
    with pytest.raises(RecordConflictError, match="does not declare"):
        store.save_artifact(derivative_for(wrong_output_run.run_id))

    other_parent = save_artifact(store, "other-parent-lineage")
    wrong_parent_run = make_run(
        other_parent.artifact_id,
        "run-wrong-parent",
        ParserRunStatus.COMPLETE,
        output_hashes={"searchable_pdf": derivative_blob.sha256},
    )
    store.save_parser_run(wrong_parent_run)
    with pytest.raises(RecordConflictError, match="different artifact"):
        store.save_artifact(derivative_for(wrong_parent_run.run_id))

    correct_run = make_run(
        parent.artifact_id,
        "run-correct-output",
        ParserRunStatus.COMPLETE,
        output_hashes={"searchable_pdf": derivative_blob.sha256},
    )
    store.save_parser_run(correct_run)
    derivative = derivative_for(correct_run.run_id)

    store.save_artifact(derivative)

    assert store.get_artifact(derivative.artifact_id) == derivative


def test_parser_run_requires_artifact_and_verified_outputs(
    store: ContentAddressedStore,
) -> None:
    with pytest.raises(RecordNotFoundError, match="artifact-1"):
        store.save_parser_run(
            make_run("artifact-1", "run-before-artifact", ParserRunStatus.FAILED)
        )

    artifact = save_artifact(store)
    output = store.put_blob(b'{"docling": "document"}')
    run = make_run(
        artifact.artifact_id,
        "run-complete",
        ParserRunStatus.COMPLETE,
        output_hashes={"docling_document": output.sha256},
        output_locations={"docling_document": output.uri},
    )
    store.save_parser_run(run)

    assert store.get_parser_run(run.run_id) == run
    assert store.has_complete_run(artifact.artifact_id, "docling")

    missing_output = make_run(
        artifact.artifact_id,
        "run-missing-output",
        ParserRunStatus.PARTIAL,
        output_hashes={"tei": "e" * 64},
    )
    with pytest.raises(BlobNotFoundError, match="blob not found"):
        store.save_parser_run(missing_output)


def test_save_revalidates_mutated_nested_configuration(
    store: ContentAddressedStore,
) -> None:
    artifact = save_artifact(store)
    run = make_run(
        artifact.artifact_id,
        "run-mutated-configuration",
        ParserRunStatus.PARTIAL,
    )
    run.configuration["do_ocr"] = False

    with pytest.raises(
        ValidationError, match="configuration_sha256 does not match configuration"
    ):
        store.save_parser_run(run)
    with pytest.raises(RecordNotFoundError, match="run-mutated-configuration"):
        store.get_parser_run(run.run_id)


def test_run_queries_make_interrupted_work_resumable(
    store: ContentAddressedStore,
) -> None:
    artifact_ids = ("never-run", "partial", "failed", "complete", "quarantined")
    for artifact_id in artifact_ids:
        save_artifact(store, artifact_id)

    statuses = {
        "partial": ParserRunStatus.PARTIAL,
        "failed": ParserRunStatus.FAILED,
        "complete": ParserRunStatus.COMPLETE,
        "quarantined": ParserRunStatus.QUARANTINED,
    }
    for minute, (artifact_id, status) in enumerate(statuses.items()):
        store.save_parser_run(
            make_run(artifact_id, f"run-{artifact_id}", status, minute=minute)
        )

    candidates = store.list_resume_candidates("docling")
    assert {artifact.artifact_id for artifact in candidates} == {
        "never-run",
        "partial",
        "failed",
    }
    assert store.latest_parser_run("partial", "docling") is not None
    assert len(store.list_parser_runs(status=ParserRunStatus.FAILED)) == 1


def test_run_queries_can_isolate_output_policies(
    store: ContentAddressedStore,
) -> None:
    artifact = save_artifact(store, "policy-filter")
    policy_a: dict[str, object] = {"pipeline": "a"}
    policy_b: dict[str, object] = {"pipeline": "b"}
    policy_c: dict[str, object] = {"pipeline": "c"}
    policy_a_hash = configuration_sha256(policy_a)
    policy_b_hash = configuration_sha256(policy_b)
    policy_c_hash = configuration_sha256(policy_c)
    complete_a = make_run(
        artifact.artifact_id,
        "run-policy-a",
        ParserRunStatus.COMPLETE,
        output_policy_snapshot=policy_a,
    )
    failed_b = make_run(
        artifact.artifact_id,
        "run-policy-b",
        ParserRunStatus.FAILED,
        minute=1,
        output_policy_snapshot=policy_b,
    )
    legacy_partial = make_run(
        artifact.artifact_id,
        "run-without-policy",
        ParserRunStatus.PARTIAL,
        minute=2,
    )
    for run in (complete_a, failed_b, legacy_partial):
        store.save_parser_run(run)

    assert store.list_parser_runs(
        artifact_id=artifact.artifact_id,
        output_policy_sha256=policy_a_hash,
    ) == (complete_a,)
    assert (
        store.latest_parser_run(
            artifact.artifact_id,
            "docling",
            output_policy_sha256=policy_a_hash,
        )
        == complete_a
    )
    assert store.has_complete_run(
        artifact.artifact_id,
        "docling",
        output_policy_sha256=policy_a_hash,
    )
    assert not store.has_complete_run(
        artifact.artifact_id,
        "docling",
        output_policy_sha256=policy_b_hash,
    )
    assert (
        store.list_resume_candidates(
            "docling",
            output_policy_sha256=policy_a_hash,
        )
        == ()
    )
    assert store.list_resume_candidates(
        "docling",
        output_policy_sha256=policy_b_hash,
    ) == (artifact,)
    assert store.list_resume_candidates(
        "docling",
        output_policy_sha256=policy_c_hash,
    ) == (artifact,)
    assert store.latest_parser_run(artifact.artifact_id, "docling") == legacy_partial


def test_run_query_output_policy_filters_validate_hashes(
    store: ContentAddressedStore,
) -> None:
    invalid_hash = "not-a-sha256"

    with pytest.raises(ValueError, match="SHA-256 hashes"):
        store.list_parser_runs(output_policy_sha256=invalid_hash)
    with pytest.raises(ValueError, match="SHA-256 hashes"):
        store.latest_parser_run(
            "artifact",
            "docling",
            output_policy_sha256=invalid_hash,
        )
    with pytest.raises(ValueError, match="SHA-256 hashes"):
        store.has_complete_run(
            "artifact",
            "docling",
            output_policy_sha256=invalid_hash,
        )
    with pytest.raises(ValueError, match="SHA-256 hashes"):
        store.list_resume_candidates(
            "docling",
            output_policy_sha256=invalid_hash,
        )


def test_checkpoint_deletion_fsyncs_only_after_actual_deletion(
    store: ContentAddressedStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = save_artifact(store, "checkpoint-durability")
    checkpoint = ExternalTaskCheckpoint(
        checkpoint_id="durable-checkpoint",
        artifact_id=artifact.artifact_id,
        parser_name="docling",
        configuration_sha256=configuration_sha256({"do_ocr": True}),
        output_policy_sha256=configuration_sha256({"pipeline": "durable"}),
        remote_task_id="remote-task-1",
    )
    store.save_external_task_checkpoint(checkpoint)
    fsynced_directories: list[Path] = []
    monkeypatch.setattr(
        storage_module,
        "_fsync_directory",
        lambda directory: fsynced_directories.append(Path(directory)),
    )

    store.delete_external_task_checkpoint(checkpoint.checkpoint_id)

    assert fsynced_directories == [store.root / "records" / "external_tasks"]
    with pytest.raises(RecordNotFoundError, match="durable-checkpoint"):
        store.get_external_task_checkpoint(checkpoint.checkpoint_id)

    store.delete_external_task_checkpoint(checkpoint.checkpoint_id)
    assert fsynced_directories == [store.root / "records" / "external_tasks"]


def test_newer_failed_run_remains_resumable_after_an_older_complete_run(
    store: ContentAddressedStore,
) -> None:
    artifact = save_artifact(store)
    store.save_parser_run(
        make_run(artifact.artifact_id, "run-old-complete", ParserRunStatus.COMPLETE)
    )
    store.save_parser_run(
        make_run(
            artifact.artifact_id,
            "run-new-failed",
            ParserRunStatus.FAILED,
            minute=1,
        )
    )

    assert store.list_resume_candidates("docling") == (artifact,)
    assert store.has_complete_run(artifact.artifact_id, "docling")


def test_diagnostics_validate_run_lineage_and_are_queryable(
    store: ContentAddressedStore,
) -> None:
    first_artifact = save_artifact(store, "artifact-1")
    second_artifact = save_artifact(store, "artifact-2")
    run = make_run(first_artifact.artifact_id, "run-partial", ParserRunStatus.PARTIAL)
    store.save_parser_run(run)

    wrong_artifact = ParseDiagnostic(
        diagnostic_id="diagnostic-wrong",
        artifact_id=second_artifact.artifact_id,
        parser_run_id=run.run_id,
        severity=DiagnosticSeverity.ERROR,
        stage="alignment",
        code="ALIGNMENT.UNRESOLVED_CITATION",
        message="Citation did not resolve.",
    )
    with pytest.raises(RecordConflictError, match="does not match"):
        store.save_diagnostic(wrong_artifact)

    diagnostic = wrong_artifact.model_copy(
        update={
            "diagnostic_id": "diagnostic-1",
            "artifact_id": first_artifact.artifact_id,
        }
    )
    store.save_diagnostic(diagnostic)

    assert store.get_diagnostic(diagnostic.diagnostic_id) == diagnostic
    assert store.list_diagnostics(parser_run_id=run.run_id) == (diagnostic,)
