"""Stable provenance contracts for scientific document processing.

These records deliberately wrap, rather than replace, component-native document
models. In particular, parsed content remains in serialized
``DoclingDocument`` output while these contracts make source identity,
transformation lineage, and evidence locators stable across parser upgrades.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Sha256 = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$", strict=True),
]
OciDigest = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$", strict=True),
]
DoclingInputFormat = Literal["html", "docx", "pptx", "xlsx", "image"]


def utc_now() -> datetime:
    """Return a timezone-aware timestamp normalized to UTC."""

    return datetime.now(UTC)


def sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 digest for *value*."""

    return hashlib.sha256(value).hexdigest()


def configuration_sha256(configuration: dict[str, Any]) -> str:
    """Hash a JSON configuration using a deterministic canonical encoding.

    Configuration values must be JSON serializable.  Rejecting implicit string
    conversion is intentional: environment-specific object representations
    would make otherwise identical processing runs appear reproducible.
    """

    encoded = json.dumps(
        configuration,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256_bytes(encoded)


class FrozenModel(BaseModel):
    """Base for immutable, strict processing records."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class ArtifactRelationship(StrEnum):
    """How an artifact relates to another artifact."""

    SOURCE = "source"
    SUPPLEMENT = "supplement"
    DERIVATIVE = "derivative"


class ArtifactLocationRole(StrEnum):
    """Purpose of a stored artifact location."""

    RAW = "raw"
    SEARCHABLE_PDF = "searchable_pdf"
    PARSER_OUTPUT = "parser_output"
    SUPPLEMENT = "supplement"
    OTHER_DERIVATIVE = "other_derivative"


class ProcessingRunStatus(StrEnum):
    """Terminal processing outcomes; none imply silent success."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class DiagnosticSeverity(StrEnum):
    """Severity of a processing diagnostic."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class RemediationStatus(StrEnum):
    """Lifecycle state for an explicit processing problem."""

    OPEN = "open"
    RETRY_SCHEDULED = "retry_scheduled"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"


class MemoryMeasurementStatus(StrEnum):
    """Whether a component-stage memory measurement is trustworthy."""

    MEASURED = "measured"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class MemoryMeasurementScope(StrEnum):
    """Isolation boundary that owns a memory measurement."""

    INVOCATION_CGROUP = "invocation_cgroup"
    EXCLUSIVE_SERVICE_CGROUP = "exclusive_service_cgroup"


class RuntimeAttestationSource(StrEnum):
    """Trusted mechanism that bound runtime identity to one invocation."""

    AUTHENTICATED_DEPLOYMENT_REPORTER = "authenticated_deployment_reporter"
    DIGEST_ADDRESSED_OCI_INVOCATION = "digest_addressed_oci_invocation"


class ArtifactLocation(FrozenModel):
    """A hash-verified location for a raw or derived artifact."""

    uri: str = Field(description="Internal CAS URI or durable external URI")
    sha256: Sha256
    byte_size: int = Field(ge=0)
    media_type: str
    role: ArtifactLocationRole
    created_by_run_id: str | None = None

    @field_validator("uri", "media_type", "created_by_run_id")
    @classmethod
    def _strip_nonempty_optional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class LicenseMetadata(FrozenModel):
    """Acquisition-time reuse information, without inferring legal rights."""

    spdx_id: str | None = None
    license_uri: str | None = None
    statement: str | None = None
    reuse_allowed: bool | None = None
    checked_at: datetime | None = None

    @field_validator("spdx_id", "license_uri", "statement")
    @classmethod
    def _strip_license_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("license values must not be empty")
        return normalized

    @field_validator("checked_at")
    @classmethod
    def _normalize_checked_at(cls, value: datetime | None) -> datetime | None:
        return _as_utc(value, "checked_at") if value is not None else None

    @model_validator(mode="after")
    def _has_evidence(self) -> LicenseMetadata:
        if not any((self.spdx_id, self.license_uri, self.statement)):
            raise ValueError(
                "license metadata requires an identifier, URI, or statement"
            )
        return self


class DocumentArtifact(FrozenModel):
    """Immutable identity and lineage for one acquired or derived document."""

    schema_version: Literal["deepcritical-document-artifact-v1"] = (
        "deepcritical-document-artifact-v1"
    )
    artifact_id: str
    source_sha256: Sha256
    acquisition_uri: str
    identifiers: dict[str, str] = Field(default_factory=dict)
    license: LicenseMetadata | None = None
    media_type: str
    relationship: ArtifactRelationship = ArtifactRelationship.SOURCE
    parent_artifact_id: str | None = None
    raw_location: ArtifactLocation
    derived_locations: tuple[ArtifactLocation, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "artifact_id", "acquisition_uri", "media_type", "parent_artifact_id"
    )
    @classmethod
    def _strip_artifact_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("artifact values must not be empty")
        return normalized

    @field_validator("identifiers")
    @classmethod
    def _validate_identifiers(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, identifier in value.items():
            key = key.strip().lower()
            identifier = identifier.strip()
            if not key or not identifier:
                raise ValueError("identifier names and values must not be empty")
            if key in normalized:
                raise ValueError(f"duplicate normalized identifier: {key}")
            normalized[key] = identifier
        return normalized

    @field_validator("created_at")
    @classmethod
    def _normalize_created_at(cls, value: datetime) -> datetime:
        return _as_utc(value, "created_at")

    @model_validator(mode="after")
    def _validate_lineage_and_locations(self) -> DocumentArtifact:
        if self.relationship is ArtifactRelationship.SOURCE:
            if self.parent_artifact_id is not None:
                raise ValueError("source artifacts cannot have a parent")
        elif self.parent_artifact_id is None:
            raise ValueError("supplement and derivative artifacts require a parent")

        if self.parent_artifact_id == self.artifact_id:
            raise ValueError("an artifact cannot be its own parent")
        if self.raw_location.role is not ArtifactLocationRole.RAW:
            raise ValueError("raw_location must have role='raw'")
        if self.source_sha256 != self.raw_location.sha256:
            raise ValueError("source_sha256 must match raw_location.sha256")

        seen: set[tuple[str, ArtifactLocationRole]] = set()
        for location in self.derived_locations:
            if location.role is ArtifactLocationRole.RAW:
                raise ValueError("derived_locations cannot have role='raw'")
            identity = (location.sha256, location.role)
            if identity in seen:
                raise ValueError("duplicate derived artifact location")
            seen.add(identity)
        return self


class IntakeQuarantineRecord(FrozenModel):
    """Bounded evidence for a local path rejected before artifact ingestion."""

    schema_version: Literal["deepcritical-intake-quarantine-v1"] = (
        "deepcritical-intake-quarantine-v1"
    )
    intake_id: str
    source_path: str
    acquisition_uri: str
    media_type: str
    observed_byte_size: int | None = Field(default=None, ge=0)
    preflight_result_sha256: Sha256
    preflight_policy_sha256: Sha256
    reason_codes: tuple[str, ...] = Field(min_length=1)
    status: Literal["quarantined"] = "quarantined"
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "intake_id",
        "source_path",
        "acquisition_uri",
        "media_type",
    )
    @classmethod
    def _strip_intake_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("intake quarantine values must not be empty")
        return normalized

    @field_validator("reason_codes")
    @classmethod
    def _normalize_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(code.strip().upper() for code in value)
        if any(
            not code or not re.fullmatch(r"[A-Z][A-Z0-9_]*", code)
            for code in normalized
        ):
            raise ValueError("intake reason codes must be machine-readable")
        if len(set(normalized)) != len(normalized):
            raise ValueError("intake reason codes must be unique")
        return normalized

    @field_validator("created_at")
    @classmethod
    def _normalize_intake_time(cls, value: datetime) -> datetime:
        return _as_utc(value, "created_at")


class MemoryMeasurement(FrozenModel):
    """Provenance for a peak-memory value, separate from component output data.

    A numeric peak without this record is retained for older processing runs,
    but is intentionally not sufficient for a baseline comparison.
    """

    status: MemoryMeasurementStatus
    method: str | None = None
    scope: MemoryMeasurementScope | None = None
    boundary: str | None = None
    peak_memory_bytes: int | None = Field(default=None, ge=0)
    effective_memory_limit_bytes: int | None = Field(default=None, ge=0)
    environment_sha256: Sha256 | None = None
    measurement_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exclusive: bool = False
    shared_overhead_excluded: bool | None = None
    failure_code: str | None = None
    memory_events: dict[str, int] = Field(default_factory=dict)

    @field_validator("method", "boundary", "measurement_id", "failure_code")
    @classmethod
    def _normalize_measurement_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("memory measurement text must not be empty")
        return normalized

    @field_validator("started_at", "finished_at")
    @classmethod
    def _normalize_measurement_time(
        cls, value: datetime | None, info: Any
    ) -> datetime | None:
        return None if value is None else _as_utc(value, info.field_name)

    @field_validator("memory_events")
    @classmethod
    def _validate_memory_events(cls, value: dict[str, int]) -> dict[str, int]:
        if any(
            not key.strip() or isinstance(count, bool) or count < 0
            for key, count in value.items()
        ):
            raise ValueError(
                "memory event names must be non-empty non-negative integers"
            )
        return {key.strip(): count for key, count in value.items()}

    @model_validator(mode="after")
    def _validate_measurement(self) -> MemoryMeasurement:
        if (
            self.finished_at is not None
            and self.started_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("memory measurement finished_at cannot precede started_at")
        if self.status is MemoryMeasurementStatus.MEASURED:
            required = {
                "method": self.method,
                "scope": self.scope,
                "boundary": self.boundary,
                "peak_memory_bytes": self.peak_memory_bytes,
                "environment_sha256": self.environment_sha256,
                "measurement_id": self.measurement_id,
            }
            if any(value is None for value in required.values()):
                raise ValueError(
                    "measured memory requires method, scope, boundary, peak, environment, and id"
                )
            if self.failure_code is not None:
                raise ValueError("measured memory cannot have failure_code")
        elif self.peak_memory_bytes is not None:
            raise ValueError(
                "unavailable or failed memory measurement cannot have peak_memory_bytes"
            )
        return self

    @property
    def baseline_comparable(self) -> bool:
        """Whether this value can participate in an enforced P0 baseline."""

        return (
            self.status is MemoryMeasurementStatus.MEASURED
            and self.method == "cgroup-v2-memory.peak"
            and self.scope
            in {
                MemoryMeasurementScope.INVOCATION_CGROUP,
                MemoryMeasurementScope.EXCLUSIVE_SERVICE_CGROUP,
            }
            and self.peak_memory_bytes is not None
            and self.peak_memory_bytes > 0
            and self.exclusive
            and self.shared_overhead_excluded is True
            and self.started_at is not None
            and self.finished_at is not None
            and self.memory_events.get("oom_kill", 0) == 0
        )


class ResourceUsage(FrozenModel):
    """Optional measured resources for a component invocation."""

    wall_time_seconds: float | None = Field(default=None, ge=0)
    cpu_time_seconds: float | None = Field(default=None, ge=0)
    peak_memory_bytes: int | None = Field(default=None, ge=0)
    input_bytes: int | None = Field(default=None, ge=0)
    output_bytes: int | None = Field(default=None, ge=0)
    memory_measurement: MemoryMeasurement | None = None

    @model_validator(mode="after")
    def _validate_memory_measurement(self) -> ResourceUsage:
        if self.memory_measurement is not None:
            if self.peak_memory_bytes != self.memory_measurement.peak_memory_bytes:
                raise ValueError("peak_memory_bytes must match memory_measurement peak")
        return self


class ComponentDescriptor(FrozenModel):
    """Stable identity and capability of one processing component."""

    schema_version: Literal["deepcritical-component-descriptor-v1"] = (
        "deepcritical-component-descriptor-v1"
    )
    component_id: str
    component_version: str
    capability: str

    @field_validator("component_id", "component_version", "capability")
    @classmethod
    def _strip_component_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("component descriptor values must not be empty")
        return normalized


class DataProductRef(FrozenModel):
    """Typed, content-addressed reference to one immutable stage product."""

    schema_version: Literal["deepcritical-data-product-ref-v1"] = (
        "deepcritical-data-product-ref-v1"
    )
    name: str
    product_id: str
    blob_sha256: Sha256
    uri: str
    byte_size: int = Field(ge=0)
    media_type: str
    payload_schema_uri: str
    payload_schema_version: str
    producer_run_id: str
    source_artifact_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator(
        "name",
        "product_id",
        "uri",
        "media_type",
        "payload_schema_uri",
        "payload_schema_version",
        "producer_run_id",
    )
    @classmethod
    def _strip_product_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("data product values must not be empty")
        return normalized

    @field_validator("source_artifact_ids")
    @classmethod
    def _validate_source_artifacts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("source artifact IDs must not be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("source artifact IDs must be unique")
        return normalized


class RuntimeAttestation(FrozenModel):
    """Observed component identity bound to one concrete invocation.

    Expected identities belong in processing configuration.  This record is
    reserved for evidence independently observed by a trusted deployment
    reporter, or for a local OCI invocation whose exact digest-addressed image
    reference was executed by DeepCritical itself.
    """

    schema_version: Literal["deepcritical-runtime-attestation-v1"] = (
        "deepcritical-runtime-attestation-v1"
    )
    component_id: str
    component_version: str
    invocation_id: str
    source: RuntimeAttestationSource
    reporter_id: str
    observed_at: datetime
    workload_id: str
    container_reference: str
    container_digest: OciDigest
    container_image_id: OciDigest | None = None
    component_versions: dict[str, str]
    model_versions: dict[str, str] = Field(default_factory=dict)
    model_hashes: dict[str, Sha256] = Field(default_factory=dict)

    @field_validator(
        "invocation_id",
        "component_version",
        "reporter_id",
        "workload_id",
        "container_reference",
    )
    @classmethod
    def _strip_attestation_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("runtime attestation values must not be empty")
        return normalized

    @field_validator("observed_at")
    @classmethod
    def _normalize_observed_at(cls, value: datetime) -> datetime:
        return _as_utc(value, "observed_at")

    @field_validator("component_versions", "model_versions")
    @classmethod
    def _validate_attested_versions(cls, value: dict[str, str]) -> dict[str, str]:
        return _normalized_mapping(value)

    @field_validator("model_hashes")
    @classmethod
    def _validate_attested_hash_names(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not key.strip() for key in value):
            raise ValueError("runtime attestation model names must not be empty")
        return {key.strip(): digest for key, digest in value.items()}

    @model_validator(mode="after")
    def _validate_attested_identity(self) -> RuntimeAttestation:
        if not self.component_versions:
            raise ValueError("runtime attestation requires component versions")
        if self.model_versions.keys() != self.model_hashes.keys():
            raise ValueError(
                "runtime attestation model version and hash inventories must match"
            )
        digest_suffix = f"@{self.container_digest}"
        if digest_suffix not in self.container_reference:
            raise ValueError(
                "attested container reference must include its immutable digest"
            )
        return self


class ProcessingRun(FrozenModel):
    """Reproducible record of one component invocation on one artifact."""

    schema_version: Literal["deepcritical-processing-run-v1"] = (
        "deepcritical-processing-run-v1"
    )
    run_id: str
    artifact_id: str
    pipeline_run_id: str | None = None
    repetition_group_id: str | None = None
    stage_id: str
    component: ComponentDescriptor
    component_invocation_id: str | None = None
    runtime_identity_required: bool = False
    component_versions: dict[str, str] = Field(default_factory=dict)
    model_versions: dict[str, str] = Field(default_factory=dict)
    model_hashes: dict[str, Sha256] = Field(default_factory=dict)
    container_image: str | None = None
    container_digest: OciDigest | None = None
    runtime_attestation: RuntimeAttestation | None = None
    runtime_attestation_sha256: Sha256 | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    configuration_sha256: Sha256
    # This is deliberately distinct from ``configuration``.  The latter is the
    # configuration for one invocation and consequently includes input hashes and
    # conditional-branch details.  The output policy is the complete static
    # pipeline contract shared by every invocation in a workflow.
    output_policy_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_policy_sha256: Sha256 | None = None
    started_at: datetime
    finished_at: datetime
    status: ProcessingRunStatus
    resource_usage: ResourceUsage = Field(default_factory=ResourceUsage)
    warnings: tuple[str, ...] = ()
    inputs: tuple[DataProductRef, ...] = ()
    outputs: tuple[DataProductRef, ...] = ()
    completed_stages: tuple[str, ...] = ()

    @field_validator(
        "run_id",
        "artifact_id",
        "pipeline_run_id",
        "repetition_group_id",
        "stage_id",
        "component_invocation_id",
        "container_image",
    )
    @classmethod
    def _strip_run_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("processing run values must not be empty")
        return normalized

    @field_validator("started_at", "finished_at")
    @classmethod
    def _normalize_run_time(cls, value: datetime, info: Any) -> datetime:
        return _as_utc(value, info.field_name)

    @field_validator("component_versions", "model_versions")
    @classmethod
    def _validate_string_mappings(cls, value: dict[str, str]) -> dict[str, str]:
        return _normalized_mapping(value)

    @field_validator("model_hashes")
    @classmethod
    def _validate_hash_mapping_keys(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not key.strip() for key in value):
            raise ValueError("hash mapping names must not be empty")
        return {key.strip(): digest for key, digest in value.items()}

    @field_validator("warnings", "completed_stages")
    @classmethod
    def _validate_string_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("list values must not be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("list values must not contain duplicates")
        return normalized

    @model_validator(mode="after")
    def _validate_provenance(self) -> ProcessingRun:
        try:
            expected_config_hash = configuration_sha256(self.configuration)
        except (TypeError, ValueError) as exc:
            raise ValueError("configuration must be canonical JSON") from exc
        if self.configuration_sha256 != expected_config_hash:
            raise ValueError("configuration_sha256 does not match configuration")
        if self.output_policy_snapshot:
            try:
                expected_policy_hash = configuration_sha256(self.output_policy_snapshot)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "output_policy_snapshot must be canonical JSON"
                ) from exc
            if self.output_policy_sha256 is None:
                raise ValueError(
                    "output_policy_sha256 is required when output_policy_snapshot is set"
                )
            if self.output_policy_sha256 != expected_policy_hash:
                raise ValueError(
                    "output_policy_sha256 does not match output_policy_snapshot"
                )
        elif self.output_policy_sha256 is not None:
            raise ValueError(
                "output_policy_snapshot is required when output_policy_sha256 is set"
            )
        if self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        if self.container_digest is not None and self.container_image is None:
            raise ValueError("container_digest requires container_image")
        if self.runtime_attestation is None:
            if self.runtime_attestation_sha256 is not None:
                raise ValueError(
                    "runtime_attestation is required with its content hash"
                )
            if self.container_digest is not None or self.model_hashes:
                raise ValueError(
                    "observed container digests and model hashes require runtime "
                    "attestation"
                )
        else:
            attestation = self.runtime_attestation
            if attestation.component_id != self.component.component_id:
                raise ValueError(
                    "runtime attestation component does not match processing run"
                )
            if attestation.component_version != self.component.component_version:
                raise ValueError("component_version must come from runtime attestation")
            if self.component_invocation_id != attestation.invocation_id:
                raise ValueError(
                    "component_invocation_id must match runtime attestation"
                )
            if not self.started_at <= attestation.observed_at <= self.finished_at:
                raise ValueError(
                    "runtime attestation observation must fall within the processing run"
                )
            expected_attestation_hash = configuration_sha256(
                attestation.model_dump(mode="json")
            )
            if self.runtime_attestation_sha256 != expected_attestation_hash:
                raise ValueError(
                    "runtime_attestation_sha256 does not match runtime_attestation"
                )
            attestation_output = next(
                (
                    product
                    for product in self.outputs
                    if product.name == "runtime_attestation"
                ),
                None,
            )
            if (
                attestation_output is None
                or attestation_output.blob_sha256 != expected_attestation_hash
            ):
                raise ValueError(
                    "runtime attestation must be preserved as a processing-run output"
                )
            if self.container_digest != attestation.container_digest:
                raise ValueError("container_digest must come from runtime attestation")
            if self.container_image != attestation.container_reference:
                raise ValueError("container_image must come from runtime attestation")
            if self.component_versions != attestation.component_versions:
                raise ValueError(
                    "component_versions must come from runtime attestation"
                )
            if self.model_versions != attestation.model_versions:
                raise ValueError("model_versions must come from runtime attestation")
            if self.model_hashes != attestation.model_hashes:
                raise ValueError("model_hashes must come from runtime attestation")
        if self.repetition_group_id is not None and self.pipeline_run_id is None:
            raise ValueError("repetition_group_id requires pipeline_run_id")
        if (
            self.runtime_identity_required
            and self.status is ProcessingRunStatus.COMPLETE
        ):
            if self.runtime_attestation is None:
                raise ValueError(
                    "complete processing runs require task-bound runtime attestation"
                )
            if not self.component_versions:
                raise ValueError(
                    "complete processing runs require observed component versions"
                )
            if self.container_image is not None and self.container_digest is None:
                raise ValueError(
                    "complete container processing runs require an immutable digest"
                )
            if self.model_versions.keys() != self.model_hashes.keys():
                raise ValueError(
                    "model version and hash inventories must have identical keys"
                )
        input_ids = [product.product_id for product in self.inputs]
        if len(set(input_ids)) != len(input_ids):
            raise ValueError("processing-run input product IDs must be unique")
        output_names = [product.name for product in self.outputs]
        if len(set(output_names)) != len(output_names):
            raise ValueError("processing-run output names must be unique")
        output_ids = [product.product_id for product in self.outputs]
        if len(set(output_ids)) != len(output_ids):
            raise ValueError("processing-run output product IDs must be unique")
        for product in self.outputs:
            if product.producer_run_id != self.run_id:
                raise ValueError("output producer_run_id must match processing run")
            if self.artifact_id not in product.source_artifact_ids:
                raise ValueError(
                    "processing-run artifact must be included in output lineage"
                )
        return self

    @property
    def component_id(self) -> str:
        """Return the component identifier without duplicating persisted data."""

        return self.component.component_id

    @property
    def component_version(self) -> str:
        """Return the component version without duplicating persisted data."""

        return self.component.component_version

    def output(self, name: str) -> DataProductRef | None:
        """Return a named output, if the run produced it."""

        return next((product for product in self.outputs if product.name == name), None)

    def require_output(self, name: str) -> DataProductRef:
        """Return a named output or raise a precise contract error."""

        product = self.output(name)
        if product is None:
            raise KeyError(f"processing run {self.run_id!r} has no output {name!r}")
        return product

    def output_sha256(self, name: str) -> Sha256 | None:
        """Return the digest of a named output without materializing a map."""

        product = self.output(name)
        return product.blob_sha256 if product is not None else None


class PdfBoundingBox(FrozenModel):
    """PDF rectangle in source-page coordinates."""

    left: float = Field(ge=0)
    top: float = Field(ge=0)
    right: float = Field(gt=0)
    bottom: float = Field(gt=0)
    page_width: float | None = Field(default=None, gt=0)
    page_height: float | None = Field(default=None, gt=0)
    coordinate_origin: Literal["top_left", "bottom_left"] = "top_left"

    @model_validator(mode="after")
    def _validate_rectangle(self) -> PdfBoundingBox:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("bounding box must have positive width and height")
        if self.page_width is not None and self.right > self.page_width:
            raise ValueError("bounding box exceeds page width")
        if self.page_height is not None and self.bottom > self.page_height:
            raise ValueError("bounding box exceeds page height")
        return self


class PdfLocator(FrozenModel):
    """Page and geometry locator for a PDF-derived item."""

    kind: Literal["pdf"] = "pdf"
    page_number: int = Field(ge=1)
    bounding_box: PdfBoundingBox
    page_label: str | None = None

    @field_validator("page_label")
    @classmethod
    def _strip_page_label(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("page_label must not be empty")
        return normalized


class JatsLocator(FrozenModel):
    """Stable native locator for a JATS element."""

    kind: Literal["jats"] = "jats"
    xml_id: str | None = None
    xpath: str | None = None

    @field_validator("xml_id", "xpath")
    @classmethod
    def _strip_jats_locator(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("JATS locator values must not be empty")
        return normalized

    @model_validator(mode="after")
    def _requires_native_reference(self) -> JatsLocator:
        if self.xml_id is None and self.xpath is None:
            raise ValueError("JATS locator requires xml_id or xpath")
        return self


class BioCLocator(FrozenModel):
    """Native passage range in a BioC collection.

    ``document_index`` is retained even when BioC supplies a document ID because
    IDs are not guaranteed to be present or unique within a collection.
    ``sentence_index`` preserves sentence-only passage coordinates when present.
    """

    kind: Literal["bioc"] = "bioc"
    document_index: int = Field(ge=0)
    document_id: str | None = None
    passage_index: int = Field(ge=0)
    sentence_index: int | None = Field(default=None, ge=0)
    offset: int = Field(ge=0)
    length: int = Field(gt=0)

    @field_validator("document_id")
    @classmethod
    def _strip_document_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("document_id must not be empty")
        return normalized


class DoclingItemLocator(FrozenModel):
    """Parser-native locator for formats without a stable source coordinate contract.

    The immutable ``DoclingDocument`` remains a native processor product for
    these formats. This locator is deliberately explicit about being
    processor-native; it must not be presented as an HTML XPath, Office object
    ID, or image coordinate.
    """

    kind: Literal["docling_item"] = "docling_item"
    input_format: DoclingInputFormat
    item_ref: str

    @field_validator("item_ref")
    @classmethod
    def _strip_item_ref(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Docling item reference must not be empty")
        return normalized


SourceLocator = Annotated[
    PdfLocator | JatsLocator | BioCLocator | DoclingItemLocator,
    Field(discriminator="kind"),
]


class ExecutionCheckpoint(FrozenModel):
    """Durable identity of a submitted asynchronous component task."""

    schema_version: Literal["deepcritical-execution-checkpoint-v1"] = (
        "deepcritical-execution-checkpoint-v1"
    )
    checkpoint_id: str
    artifact_id: str
    component_id: str
    configuration_sha256: Sha256
    output_policy_sha256: Sha256
    pipeline_run_id: str | None = None
    repetition_group_id: str | None = None
    pipeline_attempt_id: str | None = None
    remote_task_id: str
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "checkpoint_id",
        "artifact_id",
        "component_id",
        "pipeline_run_id",
        "repetition_group_id",
        "pipeline_attempt_id",
        "remote_task_id",
    )
    @classmethod
    def _strip_checkpoint_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("external task checkpoint values must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_attempt_scope(self) -> ExecutionCheckpoint:
        if self.pipeline_attempt_id is not None and self.pipeline_run_id is None:
            raise ValueError("pipeline_attempt_id requires pipeline_run_id")
        return self

    @field_validator("created_at")
    @classmethod
    def _normalize_checkpoint_time(cls, value: datetime) -> datetime:
        return _as_utc(value, "created_at")


class RepresentationAnchor(FrozenModel):
    """A character range in one exact native or canonical representation."""

    product_id: str
    node_id: str
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)

    @field_validator("product_id", "node_id")
    @classmethod
    def _strip_anchor_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("representation anchor values must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_character_range(self) -> RepresentationAnchor:
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be greater than char_start")
        return self


class ContentSpan(FrozenModel):
    """A content-addressed evidence span anchored in representation/source space."""

    span_id: str
    artifact_id: str
    processing_run_id: str
    representation_anchor: RepresentationAnchor
    content_sha256: Sha256
    source_locator: SourceLocator

    @field_validator("span_id", "artifact_id", "processing_run_id")
    @classmethod
    def _strip_span_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content span values must not be empty")
        return normalized


class ContentSpanSet(FrozenModel):
    """Versioned persisted set of spans targeting one representation product."""

    schema_version: Literal["deepcritical-content-span-set-v1"] = (
        "deepcritical-content-span-set-v1"
    )
    artifact_id: str
    processing_run_id: str
    representation_product_id: str
    spans: tuple[ContentSpan, ...] = ()

    @field_validator(
        "artifact_id",
        "processing_run_id",
        "representation_product_id",
    )
    @classmethod
    def _strip_span_set_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content span set values must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_span_lineage(self) -> ContentSpanSet:
        span_ids: set[str] = set()
        for span in self.spans:
            if span.artifact_id != self.artifact_id:
                raise ValueError("content span artifact_id does not match set")
            if span.processing_run_id != self.processing_run_id:
                raise ValueError("content span processing_run_id does not match set")
            if span.representation_anchor.product_id != self.representation_product_id:
                raise ValueError("content span representation does not match set")
            if span.span_id in span_ids:
                raise ValueError("content span IDs must be unique")
            span_ids.add(span.span_id)
        return self


class ProcessingDiagnostic(FrozenModel):
    """Machine-actionable, source-anchored processing warning or failure."""

    schema_version: Literal["deepcritical-processing-diagnostic-v1"] = (
        "deepcritical-processing-diagnostic-v1"
    )
    diagnostic_id: str
    artifact_id: str
    processing_run_id: str | None = None
    severity: DiagnosticSeverity
    stage: str
    code: str
    message: str
    page_number: int | None = Field(default=None, ge=1)
    item_ref: str | None = None
    source_locator: SourceLocator | None = None
    remediation_status: RemediationStatus = RemediationStatus.OPEN
    remediation_note: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator(
        "diagnostic_id",
        "artifact_id",
        "processing_run_id",
        "stage",
        "message",
        "item_ref",
        "remediation_note",
    )
    @classmethod
    def _strip_diagnostic_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("diagnostic values must not be empty")
        return normalized

    @field_validator("code")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*(?:\.[A-Z0-9_]+)*", normalized):
            raise ValueError("diagnostic code must be machine-readable")
        return normalized

    @field_validator("created_at")
    @classmethod
    def _normalize_diagnostic_time(cls, value: datetime) -> datetime:
        return _as_utc(value, "created_at")

    @model_validator(mode="after")
    def _validate_remediation(self) -> ProcessingDiagnostic:
        if (
            self.remediation_status is RemediationStatus.RESOLVED
            and self.remediation_note is None
        ):
            raise ValueError("resolved diagnostics require a remediation_note")
        if isinstance(self.source_locator, PdfLocator):
            if self.page_number is not None and (
                self.page_number != self.source_locator.page_number
            ):
                raise ValueError("page_number must agree with the PDF locator")
        return self


class ProcessingRunDiagnosticManifest(FrozenModel):
    """Durable diagnostic set that must be indexed before a run is reusable."""

    schema_version: Literal["deepcritical-processing-diagnostic-manifest-v1"] = (
        "deepcritical-processing-diagnostic-manifest-v1"
    )
    artifact_id: str
    processing_run_id: str
    diagnostics: tuple[ProcessingDiagnostic, ...] = ()

    @field_validator("artifact_id", "processing_run_id")
    @classmethod
    def _strip_manifest_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("diagnostic manifest values must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_diagnostic_lineage(self) -> ProcessingRunDiagnosticManifest:
        diagnostic_ids: set[str] = set()
        for diagnostic in self.diagnostics:
            if diagnostic.artifact_id != self.artifact_id:
                raise ValueError("manifest diagnostic artifact_id does not match")
            if diagnostic.processing_run_id != self.processing_run_id:
                raise ValueError("manifest diagnostic processing_run_id does not match")
            if diagnostic.diagnostic_id in diagnostic_ids:
                raise ValueError("manifest diagnostic IDs must be unique")
            diagnostic_ids.add(diagnostic.diagnostic_id)
        return self


def _as_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _normalized_mapping(value: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, item in value.items():
        key = key.strip()
        item = item.strip()
        if not key or not item:
            raise ValueError("mapping names and values must not be empty")
        if key in normalized:
            raise ValueError(f"duplicate normalized mapping key: {key}")
        normalized[key] = item
    return normalized


__all__ = [
    "ArtifactLocation",
    "ArtifactLocationRole",
    "ArtifactRelationship",
    "BioCLocator",
    "ComponentDescriptor",
    "ContentSpan",
    "ContentSpanSet",
    "DataProductRef",
    "DiagnosticSeverity",
    "DoclingInputFormat",
    "DoclingItemLocator",
    "DocumentArtifact",
    "ExecutionCheckpoint",
    "IntakeQuarantineRecord",
    "JatsLocator",
    "LicenseMetadata",
    "MemoryMeasurement",
    "MemoryMeasurementScope",
    "MemoryMeasurementStatus",
    "OciDigest",
    "PdfBoundingBox",
    "PdfLocator",
    "ProcessingDiagnostic",
    "ProcessingRun",
    "ProcessingRunDiagnosticManifest",
    "ProcessingRunStatus",
    "RemediationStatus",
    "RepresentationAnchor",
    "ResourceUsage",
    "RuntimeAttestation",
    "RuntimeAttestationSource",
    "Sha256",
    "SourceLocator",
    "configuration_sha256",
    "sha256_bytes",
    "utc_now",
]
