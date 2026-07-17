"""Filesystem-backed, content-addressed persistence for processing records."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, TypeVar

from pydantic import BaseModel, ValidationError

from .models import (
    ArtifactLocation,
    ArtifactLocationRole,
    DocumentArtifact,
    ExternalTaskCheckpoint,
    IntakeQuarantineRecord,
    ParseDiagnostic,
    ParserRun,
    ParserRunDiagnosticManifest,
    ParserRunStatus,
)

_SHA256_PATTERN = frozenset("0123456789abcdef")
_RECORD_MODEL = TypeVar("_RECORD_MODEL", bound=BaseModel)


class StorageError(RuntimeError):
    """Base exception for document-processing persistence failures."""


class BlobNotFoundError(StorageError):
    """Raised when a requested content hash is not stored."""


class BlobTooLargeError(StorageError):
    """Raised when a streaming blob crosses an explicit byte limit."""

    def __init__(self, *, max_bytes: int, observed_bytes: int) -> None:
        super().__init__(
            f"blob exceeded {max_bytes} bytes while streaming "
            f"(observed at least {observed_bytes})"
        )
        self.max_bytes = max_bytes
        self.observed_bytes = observed_bytes


class HashMismatchError(StorageError):
    """Raised when stored bytes do not match their claimed digest."""


class RecordNotFoundError(StorageError):
    """Raised when a requested immutable record does not exist."""


class RecordConflictError(StorageError):
    """Raised when an ID is reused for different immutable record content."""


class CorruptRecordError(StorageError):
    """Raised when a stored record cannot be decoded or validated."""


@dataclass(frozen=True, slots=True)
class StoredBlob:
    """Result of an idempotent blob write."""

    sha256: str
    byte_size: int
    uri: str
    path: Path

    def as_location(
        self,
        *,
        media_type: str,
        role: ArtifactLocationRole,
        created_by_run_id: str | None = None,
    ) -> ArtifactLocation:
        """Create a provenance location for this verified blob."""

        return ArtifactLocation(
            uri=self.uri,
            sha256=self.sha256,
            byte_size=self.byte_size,
            media_type=media_type,
            role=role,
            created_by_run_id=created_by_run_id,
        )


class ContentAddressedStore:
    """Immutable local storage for source bytes and processing state.

    Blobs are addressed by SHA-256 and records by a hash of their stable ID.
    Complete temporary files are linked into place, making publication atomic
    without allowing an existing value to be overwritten.  Repeating the same
    write is idempotent; repeating an ID with different content is an error.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self._blob_root = self.root / "blobs" / "sha256"
        self._record_root = self.root / "records"
        self._temporary_root = self.root / ".tmp"
        for directory in (
            self._blob_root,
            self._record_root / "artifacts",
            self._record_root / "parser_runs",
            self._record_root / "diagnostics",
            self._record_root / "external_tasks",
            self._record_root / "intake_quarantines",
            self._temporary_root,
        ):
            _ensure_directory_durable(directory)

    def put_blob(
        self,
        data: bytes | bytearray | memoryview | BinaryIO,
        *,
        expected_sha256: str | None = None,
        max_bytes: int | None = None,
    ) -> StoredBlob:
        """Persist bytes once and return their verified content identity."""

        if expected_sha256 is not None:
            _validate_sha256(expected_sha256)
        if max_bytes is not None and max_bytes < 0:
            raise ValueError("max_bytes cannot be negative")

        temporary_path = self._temporary_path("blob")
        digest = hashlib.sha256()
        byte_size = 0
        try:
            with temporary_path.open("xb") as destination:
                if isinstance(data, (bytes, bytearray, memoryview)):
                    chunks = (bytes(data),)
                elif hasattr(data, "read"):
                    chunks = iter(lambda: data.read(1024 * 1024), b"")
                else:
                    raise TypeError("data must be bytes-like or a binary stream")

                for chunk in chunks:
                    if not isinstance(chunk, bytes):
                        raise TypeError("binary streams must return bytes")
                    next_size = byte_size + len(chunk)
                    if max_bytes is not None and next_size > max_bytes:
                        raise BlobTooLargeError(
                            max_bytes=max_bytes,
                            observed_bytes=next_size,
                        )
                    destination.write(chunk)
                    digest.update(chunk)
                    byte_size = next_size
                destination.flush()
                os.fsync(destination.fileno())

            actual_sha256 = digest.hexdigest()
            if expected_sha256 is not None and actual_sha256 != expected_sha256:
                raise HashMismatchError(
                    f"expected blob {expected_sha256}, got {actual_sha256}"
                )

            destination_path = self.blob_path(actual_sha256)
            _ensure_directory_durable(destination_path.parent)
            try:
                self._publish_no_replace(temporary_path, destination_path)
            except FileExistsError:
                # Another writer (or an earlier identical write) published the
                # same content address first. Verification below distinguishes
                # valid idempotency from corruption.
                pass
            self.verify_blob(actual_sha256)
            return StoredBlob(
                sha256=actual_sha256,
                byte_size=byte_size,
                uri=self.blob_uri(actual_sha256),
                path=destination_path,
            )
        finally:
            temporary_path.unlink(missing_ok=True)

    def put_blob_file(
        self,
        source: str | Path,
        *,
        expected_sha256: str | None = None,
        max_bytes: int | None = None,
    ) -> StoredBlob:
        """Stream a file into the store without modifying the source."""

        source_path = Path(source)
        with source_path.open("rb") as source_stream:
            return self.put_blob(
                source_stream,
                expected_sha256=expected_sha256,
                max_bytes=max_bytes,
            )

    def blob_uri(self, sha256: str) -> str:
        """Return the canonical URI for a digest in this store."""

        _validate_sha256(sha256)
        return f"cas://sha256/{sha256}"

    def blob_path(self, sha256: str) -> Path:
        """Return the deterministic local path for a digest."""

        _validate_sha256(sha256)
        return self._blob_root / sha256[:2] / sha256[2:]

    def read_blob(self, sha256: str) -> bytes:
        """Read bytes after verifying their content hash."""

        path = self.verify_blob(sha256)
        return path.read_bytes()

    def verify_blob(self, sha256: str) -> Path:
        """Verify that a blob exists and matches its content address."""

        path = self.blob_path(sha256)
        if not path.is_file():
            raise BlobNotFoundError(f"blob not found: {sha256}")

        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual != sha256:
            raise HashMismatchError(f"stored blob {sha256} hashes to {actual}")
        return path

    def save_artifact(self, artifact: DocumentArtifact) -> Path:
        """Persist an artifact after validating blobs and parent lineage."""

        self._verify_location(artifact.raw_location)
        for location in artifact.derived_locations:
            self._verify_location(location)
        if artifact.parent_artifact_id is not None:
            self.get_artifact(artifact.parent_artifact_id)
        raw_creator_owner = artifact.parent_artifact_id
        if artifact.raw_location.created_by_run_id is not None:
            if raw_creator_owner is None:
                raise RecordConflictError(
                    "a source artifact raw location cannot claim a creator parser run"
                )
            self._validate_location_creator(
                artifact.raw_location,
                expected_artifact_id=raw_creator_owner,
            )
        for location in artifact.derived_locations:
            if location.created_by_run_id is not None:
                self._validate_location_creator(
                    location,
                    expected_artifact_id=artifact.artifact_id,
                )
        return self._save_record("artifacts", artifact.artifact_id, artifact)

    def _validate_location_creator(
        self,
        location: ArtifactLocation,
        *,
        expected_artifact_id: str,
    ) -> None:
        creator_run_id = location.created_by_run_id
        if creator_run_id is None:
            return
        creator = self.get_parser_run(creator_run_id)
        if creator.artifact_id != expected_artifact_id:
            raise RecordConflictError(
                f"creator run {creator_run_id} belongs to a different artifact"
            )
        if location.sha256 not in creator.output_hashes.values():
            raise RecordConflictError(
                f"creator run {creator_run_id} does not declare the location hash"
            )

    def get_artifact(self, artifact_id: str) -> DocumentArtifact:
        """Load and validate an immutable artifact record."""

        return self._get_record(
            "artifacts", artifact_id, DocumentArtifact, id_field="artifact_id"
        )

    def list_artifacts(self) -> tuple[DocumentArtifact, ...]:
        """Return all artifacts in stable ID order."""

        return tuple(
            sorted(
                self._read_record_directory("artifacts", DocumentArtifact),
                key=lambda record: record.artifact_id,
            )
        )

    def save_intake_quarantine(self, record: IntakeQuarantineRecord) -> Path:
        """Persist a rejected path intake without storing unsafe source bytes."""

        self.verify_blob(record.preflight_result_sha256)
        return self._save_record("intake_quarantines", record.intake_id, record)

    def get_intake_quarantine(self, intake_id: str) -> IntakeQuarantineRecord:
        return self._get_record(
            "intake_quarantines",
            intake_id,
            IntakeQuarantineRecord,
            id_field="intake_id",
        )

    def list_intake_quarantines(self) -> tuple[IntakeQuarantineRecord, ...]:
        return tuple(
            sorted(
                self._read_record_directory(
                    "intake_quarantines",
                    IntakeQuarantineRecord,
                ),
                key=lambda record: (record.created_at, record.intake_id),
            )
        )

    def save_parser_run(self, parser_run: ParserRun) -> Path:
        """Persist a parser run after validating all referenced content."""

        self.get_artifact(parser_run.artifact_id)
        for output_name, output_sha256 in parser_run.output_hashes.items():
            self.verify_blob(output_sha256)
            output_uri = parser_run.output_locations.get(output_name)
            if output_uri is not None:
                expected_uri = self.blob_uri(output_sha256)
                if output_uri != expected_uri:
                    raise HashMismatchError(
                        f"output {output_name!r} location does not match its hash"
                    )
        return self._save_record("parser_runs", parser_run.run_id, parser_run)

    def get_parser_run(self, run_id: str) -> ParserRun:
        """Load and validate one parser-run record."""

        return self._get_record("parser_runs", run_id, ParserRun, id_field="run_id")

    def list_parser_runs(
        self,
        *,
        artifact_id: str | None = None,
        parser_name: str | None = None,
        status: ParserRunStatus | None = None,
        configuration_sha256: str | None = None,
        output_policy_sha256: str | None = None,
    ) -> tuple[ParserRun, ...]:
        """Query persisted run state for deterministic resume decisions."""

        if configuration_sha256 is not None:
            _validate_sha256(configuration_sha256)
        if output_policy_sha256 is not None:
            _validate_sha256(output_policy_sha256)
        records = self._read_record_directory("parser_runs", ParserRun)
        selected = (
            record
            for record in records
            if (artifact_id is None or record.artifact_id == artifact_id)
            and (parser_name is None or record.parser_name == parser_name)
            and (status is None or record.status is status)
            and (
                configuration_sha256 is None
                or record.configuration_sha256 == configuration_sha256
            )
            and (
                output_policy_sha256 is None
                or record.output_policy_sha256 == output_policy_sha256
            )
        )
        return tuple(
            sorted(selected, key=lambda record: (record.started_at, record.run_id))
        )

    def latest_parser_run(
        self,
        artifact_id: str,
        parser_name: str,
        *,
        configuration_sha256: str | None = None,
        output_policy_sha256: str | None = None,
    ) -> ParserRun | None:
        """Return the most recent matching persisted attempt, if any."""

        runs = self.list_parser_runs(
            artifact_id=artifact_id,
            parser_name=parser_name,
            configuration_sha256=configuration_sha256,
            output_policy_sha256=output_policy_sha256,
        )
        return runs[-1] if runs else None

    def has_complete_run(
        self,
        artifact_id: str,
        parser_name: str,
        *,
        configuration_sha256: str | None = None,
        output_policy_sha256: str | None = None,
    ) -> bool:
        """Whether a complete run also has its required diagnostics indexed."""

        return any(
            self.parser_run_diagnostics_reconciled(run)
            for run in self.list_parser_runs(
                artifact_id=artifact_id,
                parser_name=parser_name,
                status=ParserRunStatus.COMPLETE,
                configuration_sha256=configuration_sha256,
                output_policy_sha256=output_policy_sha256,
            )
        )

    def parser_run_diagnostics_reconciled(self, parser_run: ParserRun) -> bool:
        """Whether every diagnostic in a run's durable manifest is indexed."""

        manifest_sha256 = parser_run.output_hashes.get("diagnostics_manifest")
        if manifest_sha256 is None:
            # Records created before the manifest protocol remain queryable, while
            # the processing pipeline deliberately does not reuse them.
            return True
        manifest = ParserRunDiagnosticManifest.model_validate_json(
            self.read_blob(manifest_sha256)
        )
        if (
            manifest.artifact_id != parser_run.artifact_id
            or manifest.parser_run_id != parser_run.run_id
        ):
            raise RecordConflictError("diagnostics manifest does not match parser run")
        for expected in manifest.diagnostics:
            try:
                actual = self.get_diagnostic(expected.diagnostic_id)
            except RecordNotFoundError:
                return False
            if actual != expected:
                raise RecordConflictError(
                    "indexed diagnostic does not match diagnostics manifest"
                )
        return True

    def list_resume_candidates(
        self,
        parser_name: str,
        *,
        configuration_sha256: str | None = None,
        output_policy_sha256: str | None = None,
    ) -> tuple[DocumentArtifact, ...]:
        """Return artifacts with no run or a latest partial/failed attempt.

        Explicitly quarantined artifacts are not automatically retried.  A
        caller must create a deliberate remediation run after resolving the
        quarantine condition.
        """

        if output_policy_sha256 is not None:
            _validate_sha256(output_policy_sha256)
        candidates: list[DocumentArtifact] = []
        for artifact in self.list_artifacts():
            latest = self.latest_parser_run(
                artifact.artifact_id,
                parser_name,
                configuration_sha256=configuration_sha256,
                output_policy_sha256=output_policy_sha256,
            )
            if (
                latest is None
                or latest.status
                in {
                    ParserRunStatus.PARTIAL,
                    ParserRunStatus.FAILED,
                }
                or (
                    latest.status is ParserRunStatus.COMPLETE
                    and not self.parser_run_diagnostics_reconciled(latest)
                )
            ):
                candidates.append(artifact)
        return tuple(candidates)

    def save_diagnostic(self, diagnostic: ParseDiagnostic) -> Path:
        """Persist a diagnostic with validated artifact/run references."""

        self.get_artifact(diagnostic.artifact_id)
        if diagnostic.parser_run_id is not None:
            parser_run = self.get_parser_run(diagnostic.parser_run_id)
            if parser_run.artifact_id != diagnostic.artifact_id:
                raise RecordConflictError(
                    "diagnostic artifact does not match its parser run"
                )
        return self._save_record("diagnostics", diagnostic.diagnostic_id, diagnostic)

    def save_external_task_checkpoint(self, checkpoint: ExternalTaskCheckpoint) -> Path:
        """Persist a remote task ID before polling so restarts can resume it."""

        self.get_artifact(checkpoint.artifact_id)
        return self._save_record("external_tasks", checkpoint.checkpoint_id, checkpoint)

    def get_external_task_checkpoint(
        self, checkpoint_id: str
    ) -> ExternalTaskCheckpoint:
        return self._get_record(
            "external_tasks",
            checkpoint_id,
            ExternalTaskCheckpoint,
            id_field="checkpoint_id",
        )

    def delete_external_task_checkpoint(self, checkpoint_id: str) -> None:
        """Clear staging state only after a terminal parser run is durable."""

        path = self._record_path("external_tasks", checkpoint_id)
        try:
            path.unlink()
        except FileNotFoundError:
            return
        _fsync_directory(path.parent)

    def get_diagnostic(self, diagnostic_id: str) -> ParseDiagnostic:
        """Load and validate one diagnostic record."""

        return self._get_record(
            "diagnostics",
            diagnostic_id,
            ParseDiagnostic,
            id_field="diagnostic_id",
        )

    def list_diagnostics(
        self,
        *,
        artifact_id: str | None = None,
        parser_run_id: str | None = None,
    ) -> tuple[ParseDiagnostic, ...]:
        """Return diagnostics filtered by evidence lineage."""

        records = self._read_record_directory("diagnostics", ParseDiagnostic)
        selected = (
            record
            for record in records
            if (artifact_id is None or record.artifact_id == artifact_id)
            and (parser_run_id is None or record.parser_run_id == parser_run_id)
        )
        return tuple(
            sorted(
                selected, key=lambda record: (record.created_at, record.diagnostic_id)
            )
        )

    def _verify_location(self, location: ArtifactLocation) -> None:
        expected_uri = self.blob_uri(location.sha256)
        if location.uri != expected_uri:
            raise HashMismatchError(
                f"location URI {location.uri!r} does not match {location.sha256}"
            )
        path = self.verify_blob(location.sha256)
        if path.stat().st_size != location.byte_size:
            raise HashMismatchError(
                f"location size for {location.sha256} does not match stored blob"
            )

    def _save_record(
        self, category: str, record_id: str, record: _RECORD_MODEL
    ) -> Path:
        path = self._record_path(category, record_id)
        # Pydantic's frozen models are only shallowly immutable: nested dicts can
        # still be changed, and model_copy(update=...) does not re-run validation.
        # Reconstruct the record from plain Python data immediately before
        # serialization so invalid mutations can never become durable state.
        validated_record = type(record).model_validate(record.model_dump(mode="python"))
        serialized = _canonical_record_bytes(validated_record)

        if path.exists():
            if path.read_bytes() == serialized:
                return path
            raise RecordConflictError(
                f"immutable {category} ID already has different content: {record_id}"
            )

        temporary_path = self._temporary_path(category)
        try:
            with temporary_path.open("xb") as destination:
                destination.write(serialized)
                destination.flush()
                os.fsync(destination.fileno())
            try:
                self._publish_no_replace(temporary_path, path)
            except FileExistsError:
                if path.read_bytes() != serialized:
                    raise RecordConflictError(
                        f"concurrent conflicting {category} write: {record_id}"
                    ) from None
            return path
        finally:
            temporary_path.unlink(missing_ok=True)

    def _get_record(
        self,
        category: str,
        record_id: str,
        model: type[_RECORD_MODEL],
        *,
        id_field: str,
    ) -> _RECORD_MODEL:
        path = self._record_path(category, record_id)
        if not path.is_file():
            raise RecordNotFoundError(f"{category} record not found: {record_id}")
        record = self._decode_record(path, model)
        if getattr(record, id_field) != record_id:
            raise CorruptRecordError(
                f"{category} record key does not match its stored ID: {record_id}"
            )
        return record

    def _read_record_directory(
        self, category: str, model: type[_RECORD_MODEL]
    ) -> tuple[_RECORD_MODEL, ...]:
        directory = self._record_root / category
        return tuple(
            self._decode_record(path, model) for path in directory.glob("*.json")
        )

    def _decode_record(self, path: Path, model: type[_RECORD_MODEL]) -> _RECORD_MODEL:
        try:
            return model.model_validate_json(path.read_bytes())
        except (OSError, ValidationError, ValueError) as exc:
            raise CorruptRecordError(f"invalid record at {path}") from exc

    def _record_path(self, category: str, record_id: str) -> Path:
        if not record_id.strip():
            raise ValueError("record ID must not be empty")
        key = hashlib.sha256(record_id.encode("utf-8")).hexdigest()
        return self._record_root / category / f"{key}.json"

    def _temporary_path(self, prefix: str) -> Path:
        descriptor, name = tempfile.mkstemp(
            dir=self._temporary_root,
            prefix=f"{prefix}-",
            suffix=".tmp",
        )
        os.close(descriptor)
        path = Path(name)
        path.unlink()
        return path

    @staticmethod
    def _publish_no_replace(source: Path, destination: Path) -> None:
        """Atomically publish a complete file without replacing a peer."""

        try:
            os.link(source, destination)
        except FileExistsError:
            # A concurrent publisher may not have synced the shared directory
            # entry yet. Sync it here before accepting the existing record.
            _fsync_directory(destination.parent)
            raise
        _fsync_directory(destination.parent)


def _ensure_directory_durable(directory: Path) -> None:
    """Create missing directories and durably publish each new directory entry."""

    missing: list[Path] = []
    candidate = directory
    while not candidate.exists():
        missing.append(candidate)
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent

    for candidate in reversed(missing):
        try:
            candidate.mkdir()
        except FileExistsError:
            if not candidate.is_dir():
                raise
        # Sync both the new directory's contents and the parent entry that
        # names it. This also closes the race where a peer created it first.
        _fsync_directory(candidate)
        _fsync_directory(candidate.parent)


def _fsync_directory(directory: Path) -> None:
    """Flush directory entries on POSIX; Windows has no portable equivalent."""

    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonical_record_bytes(record: BaseModel) -> bytes:
    data = record.model_dump(mode="json")
    return (
        json.dumps(
            data,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in _SHA256_PATTERN for character in value):
        raise ValueError("SHA-256 hashes must be 64 lowercase hexadecimal characters")


__all__ = [
    "BlobNotFoundError",
    "BlobTooLargeError",
    "ContentAddressedStore",
    "CorruptRecordError",
    "HashMismatchError",
    "RecordConflictError",
    "RecordNotFoundError",
    "StorageError",
    "StoredBlob",
]
