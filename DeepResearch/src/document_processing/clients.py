"""Clients for the reusable document-processing services.

The clients intentionally preserve provider-native responses.  Normalization and
quality decisions happen in the orchestration layer so a failed or partial parser
cannot silently overwrite evidence from another parser.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import signal
import tempfile
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast, runtime_checkable
from urllib.parse import quote, urlparse
from uuid import uuid4

import aiohttp

from .models import (
    MemoryMeasurement,
    MemoryMeasurementStatus,
    RuntimeAttestation,
    RuntimeAttestationSource,
    utc_now,
)
from .resources import (
    InvocationMemoryMeter,
    MemoryMeasurementLease,
    MemoryMeasurementRequest,
    parse_trusted_memory_measurement,
)

_INVOCATION_ID_HEADER = "X-DeepCritical-Invocation-ID"
_INSECURE_SERVICE_API_KEYS = frozenset(
    {"deepcritical-local-only", "replace-with-a-random-local-secret"}
)
_SAFE_SERVICE_API_KEY = re.compile(r"^[A-Za-z0-9._~+/=-]{16,256}$")
_OCI_DIGEST_REFERENCE = re.compile(r"@(?P<digest>sha256:[0-9a-f]{64})$")
DEFAULT_DOCLING_MAX_RESPONSE_BYTES = 256 * 1024 * 1024
DEFAULT_GROBID_MAX_RESPONSE_BYTES = 128 * 1024 * 1024
_DEFAULT_CONTROL_RESPONSE_LIMIT_BYTES = 1024 * 1024
_HTTP_RESPONSE_CHUNK_BYTES = 64 * 1024
_RESPONSE_BODY_PREVIEW_BYTES = 8192
_DEFAULT_SUBPROCESS_OUTPUT_LIMIT_BYTES = 1024 * 1024
_DEFAULT_SUBPROCESS_CLEANUP_TIMEOUT_SECONDS = 30.0
_OUTPUT_TRUNCATION_MARKER = b"\n[DeepCritical subprocess output truncated]\n"
_SIGKILL = getattr(signal, "SIGKILL", 9)


def _required_service_api_key(
    value: str | None, *, environment_name: str, service_name: str
) -> str:
    """Resolve and validate authentication before any parser request can exist."""

    resolved = value if value is not None else os.getenv(environment_name)
    secret = resolved.strip() if resolved is not None else ""
    if (
        not _SAFE_SERVICE_API_KEY.fullmatch(secret)
        or secret in _INSECURE_SERVICE_API_KEYS
        or secret.lower().startswith("replace-with-")
    ):
        raise ValueError(
            f"{service_name} api_key (or {environment_name}) must contain a "
            "non-default, URL-safe secret of 16-256 characters"
        )
    return secret


def _validate_authenticated_endpoint(value: str, *, service_name: str) -> str:
    """Reject external cleartext endpoints before attaching authentication."""

    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError(f"{service_name} endpoint must be an HTTP(S) URL")
    hostname = parsed.hostname.casefold()
    loopback = hostname == "localhost"
    if not loopback:
        try:
            loopback = ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            loopback = False
    if not loopback and parsed.scheme != "https":
        raise ValueError(f"{service_name} external endpoint must use HTTPS")
    return normalized


class ParserServiceError(RuntimeError):
    """A parser service failed in a way callers can record as a diagnostic."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int | None = None,
        retryable: bool = False,
        response_body: str | None = None,
        memory_measurement: MemoryMeasurement | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.response_body = response_body
        self.memory_measurement = memory_measurement


@dataclass(frozen=True, slots=True)
class ServiceHealth:
    """Typed service readiness result with optional version evidence."""

    ready: bool
    readiness: Mapping[str, Any]
    versions: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DoclingConversionResult:
    """Lossless result returned by Docling Serve."""

    document: dict[str, Any]
    raw_response: dict[str, Any]
    status: str
    processing_time_seconds: float | None = None
    timings: Mapping[str, Any] = field(default_factory=dict)
    errors: tuple[Mapping[str, Any] | str, ...] = ()
    remote_task_id: str | None = None
    memory_measurement: MemoryMeasurement | None = None
    runtime_attestation: RuntimeAttestation | None = None
    runtime_attestation_error: str | None = None

    @property
    def is_partial(self) -> bool:
        return self.status == "partial_success"


@dataclass(frozen=True, slots=True)
class GrobidResult:
    """Unmodified GROBID TEI plus request-level metadata."""

    tei_xml: bytes
    coordinates: tuple[str, ...]
    status_code: int
    remote_request_id: str | None = None
    memory_measurement: MemoryMeasurement | None = None
    runtime_attestation: RuntimeAttestation | None = None
    runtime_attestation_error: str | None = None


@dataclass(frozen=True, slots=True)
class OCRResult:
    """Searchable derivative produced by OCRmyPDF."""

    pdf_bytes: bytes
    sidecar_text: str
    stdout: str
    stderr: str
    exit_code: int
    memory_measurement: MemoryMeasurement | None = None
    runtime_attestation: RuntimeAttestation | None = None
    runtime_attestation_error: str | None = None


@runtime_checkable
class RemoteMemoryMeasurementReporter(Protocol):
    """Trusted deployment adapter that binds metrics to one remote parser task."""

    async def resolve(
        self, *, component_id: str, remote_task_id: str | None
    ) -> MemoryMeasurement | Mapping[str, object] | None:
        """Return a verified metric supplied by the parser deployment."""


@runtime_checkable
class RemoteRuntimeAttestationReporter(Protocol):
    """Trusted deployment adapter for task-bound parser runtime identity."""

    async def resolve(
        self, *, component_id: str, remote_task_id: str | None
    ) -> RuntimeAttestation | Mapping[str, object] | None:
        """Return independently observed identity for one parser invocation."""


class HttpRemoteMemoryMeasurementReporter:
    """Resolve persisted, task-bound measurements from a trusted supervisor.

    The supervisor contract is an authenticated
    ``GET /v1/measurements/{component_id}/{task_or_request_id}`` endpoint. A
    successful response body is one strict ``MemoryMeasurement`` object. The
    reporter never derives a value from service RSS or shared container stats.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        api_key_environment: str = "RESOURCE_REPORTER_API_KEY",
        connect_timeout_seconds: float = 5.0,
        request_timeout_seconds: float = 30.0,
        resolution_timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        if (
            connect_timeout_seconds <= 0
            or request_timeout_seconds <= 0
            or resolution_timeout_seconds <= 0
            or poll_interval_seconds <= 0
        ):
            raise ValueError("resource reporter timeouts must be positive")
        self.base_url = _validate_authenticated_endpoint(
            base_url, service_name="resource reporter"
        )
        self.api_key = _required_service_api_key(
            api_key,
            environment_name=api_key_environment,
            service_name="resource reporter",
        )
        self.connect_timeout_seconds = connect_timeout_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.resolution_timeout_seconds = resolution_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    async def resolve(
        self, *, component_id: str, remote_task_id: str | None
    ) -> Mapping[str, object]:
        if component_id not in {"docling", "grobid"}:
            raise ValueError("resource reporter component_id is not supported")
        if remote_task_id is None or not remote_task_id.strip():
            raise ValueError("resource reporter requires a task or request identity")
        task_id = remote_task_id.strip()
        path = (
            f"{self.base_url}/v1/measurements/{quote(component_id, safe='')}/"
            f"{quote(task_id, safe='')}"
        )
        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        deadline = asyncio.get_running_loop().time() + self.resolution_timeout_seconds
        headers = {"X-API-Key": self.api_key}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise ParserServiceError(
                        "Resource measurement was not available before the deadline",
                        code="memory_reporter_timeout",
                        retryable=True,
                    )
                request_timeout = aiohttp.ClientTimeout(
                    total=min(self.request_timeout_seconds, remaining),
                    connect=min(self.connect_timeout_seconds, remaining),
                )
                async with session.get(
                    path,
                    allow_redirects=False,
                    timeout=request_timeout,
                ) as response:
                    if response.status == 200:
                        return cast(
                            "Mapping[str, object]", await _read_json_response(response)
                        )
                    if response.status not in {202, 404}:
                        body = await _read_response_preview(response)
                        raise ParserServiceError(
                            f"Resource reporter returned HTTP {response.status}",
                            code="memory_reporter_failed",
                            status_code=response.status,
                            retryable=response.status in {408, 429, 502, 503, 504},
                            response_body=body,
                        )
                if asyncio.get_running_loop().time() >= deadline:
                    raise ParserServiceError(
                        "Resource measurement was not available before the deadline",
                        code="memory_reporter_timeout",
                        retryable=True,
                    )
                await asyncio.sleep(
                    min(
                        self.poll_interval_seconds,
                        max(0.0, deadline - asyncio.get_running_loop().time()),
                    )
                )

    async def health(self) -> bool:
        """Verify reporter authentication/readiness without fabricating a metric."""

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={"X-API-Key": self.api_key},
        ) as session:
            async with session.get(
                f"{self.base_url}/health", allow_redirects=False
            ) as response:
                return response.status == 200


class HttpRemoteRuntimeAttestationReporter:
    """Resolve task-bound runtime identity from an authenticated supervisor.

    The supervisor must derive image and model identity from the workload that
    handled the supplied invocation.  Expected hashes are intentionally never
    sent to this endpoint, preventing a configuration echo from masquerading as
    an observation.
    """

    def __init__(
        self,
        base_url: str,
        *,
        expected_reporter_id: str,
        api_key: str | None = None,
        api_key_environment: str = "RUNTIME_ATTESTATION_API_KEY",
        connect_timeout_seconds: float = 5.0,
        request_timeout_seconds: float = 30.0,
        resolution_timeout_seconds: float = 30.0,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        if (
            connect_timeout_seconds <= 0
            or request_timeout_seconds <= 0
            or resolution_timeout_seconds <= 0
            or poll_interval_seconds <= 0
        ):
            raise ValueError("runtime attestation reporter timeouts must be positive")
        normalized_reporter_id = expected_reporter_id.strip()
        if not normalized_reporter_id:
            raise ValueError("runtime attestation expected_reporter_id is required")
        self.base_url = _validate_authenticated_endpoint(
            base_url, service_name="runtime attestation reporter"
        )
        self.expected_reporter_id = normalized_reporter_id
        self.api_key = _required_service_api_key(
            api_key,
            environment_name=api_key_environment,
            service_name="runtime attestation reporter",
        )
        self.connect_timeout_seconds = connect_timeout_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.resolution_timeout_seconds = resolution_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    async def resolve(
        self, *, component_id: str, remote_task_id: str | None
    ) -> RuntimeAttestation:
        if component_id not in {"docling", "grobid"}:
            raise ValueError("runtime attestation component_id is not supported")
        if remote_task_id is None or not remote_task_id.strip():
            raise ValueError("runtime attestation requires an invocation identity")
        task_id = remote_task_id.strip()
        path = (
            f"{self.base_url}/v1/attestations/{quote(component_id, safe='')}/"
            f"{quote(task_id, safe='')}"
        )
        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        deadline = asyncio.get_running_loop().time() + self.resolution_timeout_seconds
        headers = {"X-API-Key": self.api_key}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise ParserServiceError(
                        "Runtime attestation was not available before the deadline",
                        code="runtime_attestation_reporter_timeout",
                        retryable=True,
                    )
                request_timeout = aiohttp.ClientTimeout(
                    total=min(self.request_timeout_seconds, remaining),
                    connect=min(self.connect_timeout_seconds, remaining),
                )
                async with session.get(
                    path,
                    allow_redirects=False,
                    timeout=request_timeout,
                ) as response:
                    if response.status == 200:
                        payload = await _read_json_response(response)
                        attestation = RuntimeAttestation.model_validate(payload)
                        if (
                            attestation.component_id != component_id
                            or attestation.invocation_id != task_id
                        ):
                            raise ParserServiceError(
                                "Runtime attestation does not match the invocation",
                                code="runtime_attestation_unbound",
                            )
                        if attestation.reporter_id != self.expected_reporter_id:
                            raise ParserServiceError(
                                "Runtime attestation came from an untrusted reporter",
                                code="runtime_attestation_reporter_mismatch",
                            )
                        return attestation
                    if response.status not in {202, 404}:
                        body = await _read_response_preview(response)
                        raise ParserServiceError(
                            f"Runtime attestation reporter returned HTTP {response.status}",
                            code="runtime_attestation_reporter_failed",
                            status_code=response.status,
                            retryable=response.status in {408, 429, 502, 503, 504},
                            response_body=body,
                        )
                if asyncio.get_running_loop().time() >= deadline:
                    raise ParserServiceError(
                        "Runtime attestation was not available before the deadline",
                        code="runtime_attestation_reporter_timeout",
                        retryable=True,
                    )
                await asyncio.sleep(
                    min(
                        self.poll_interval_seconds,
                        max(0.0, deadline - asyncio.get_running_loop().time()),
                    )
                )

    async def health(self) -> bool:
        """Verify reporter authentication/readiness without claiming evidence."""

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={"X-API-Key": self.api_key},
        ) as session:
            async with session.get(
                f"{self.base_url}/health", allow_redirects=False
            ) as response:
                return response.status == 200


@dataclass(frozen=True, slots=True)
class ManagedParserResult:
    """Provider-native output returned only by an explicitly enabled adapter."""

    provider_name: str
    component_version: str
    raw_output: bytes
    media_type: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@runtime_checkable
class ManagedParserAdapter(Protocol):
    """Opt-in boundary for a managed parser; no implementation is enabled in P0."""

    provider_name: str
    component_version: str

    async def parse(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
    ) -> ManagedParserResult:
        """Upload one approved artifact and return unmodified provider output."""


TaskSubmittedHook = Callable[[str], Awaitable[None] | None]


def _stringify_form_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _docling_readiness_is_explicit(readiness: Mapping[str, Any]) -> bool:
    """Interpret only a documented, explicit Docling readiness value."""

    if "ready" in readiness:
        return readiness["ready"] is True
    return readiness.get("status") == "ok"


def _normalize_grobid_version(body: bytes) -> str:
    """Normalize GROBID's current JSON response and legacy plain-text response."""

    raw_version = body.decode("utf-8", errors="replace").strip()
    if not raw_version:
        raise ParserServiceError(
            "GROBID version endpoint returned an empty value",
            code="grobid_version_empty",
        )
    if not raw_version.startswith(("{", "[")):
        return raw_version
    try:
        payload = json.loads(raw_version)
    except json.JSONDecodeError as exc:
        raise ParserServiceError(
            "GROBID version endpoint returned malformed JSON",
            code="grobid_version_invalid",
        ) from exc
    version = payload.get("version") if isinstance(payload, Mapping) else None
    if not isinstance(version, str) or not version.strip():
        raise ParserServiceError(
            "GROBID version endpoint returned no valid version",
            code="grobid_version_invalid",
        )
    return version.strip()


class DoclingServeClient:
    """Thin asynchronous client for Docling Serve's durable conversion API."""

    _SUCCESS_STATUSES = frozenset({"success", "partial_success"})
    _TASK_SUCCESS = frozenset({"success"})
    _TASK_FAILURE = frozenset({"failure"})

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5001",
        *,
        api_key: str | None = None,
        connect_timeout_seconds: float = 10.0,
        request_timeout_seconds: float = 120.0,
        task_timeout_seconds: float = 3600.0,
        poll_interval_seconds: float = 1.0,
        max_response_bytes: int = DEFAULT_DOCLING_MAX_RESPONSE_BYTES,
        use_async_api: bool = True,
        memory_reporter: RemoteMemoryMeasurementReporter | None = None,
        runtime_reporter: RemoteRuntimeAttestationReporter | None = None,
    ) -> None:
        if connect_timeout_seconds <= 0 or request_timeout_seconds <= 0:
            raise ValueError("Docling timeouts must be positive")
        if (
            not isinstance(max_response_bytes, int)
            or isinstance(max_response_bytes, bool)
            or max_response_bytes <= 0
        ):
            raise ValueError("Docling max_response_bytes must be a positive integer")
        self.base_url = _validate_authenticated_endpoint(
            base_url, service_name="Docling"
        )
        self.api_key = _required_service_api_key(
            api_key,
            environment_name="DOCLING_API_KEY",
            service_name="Docling",
        )
        self.connect_timeout_seconds = connect_timeout_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.task_timeout_seconds = task_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_response_bytes = max_response_bytes
        self.use_async_api = use_async_api
        self.memory_reporter = memory_reporter
        self.runtime_reporter = runtime_reporter

    @property
    def headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    async def health(self) -> ServiceHealth:
        """Return explicit readiness and version evidence.

        HTTP success alone is insufficient. Unknown, missing, malformed, and
        explicitly false readiness payloads all fail closed.
        """

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, headers=self.headers
        ) as session:
            async with session.get(
                f"{self.base_url}/ready", allow_redirects=False
            ) as response:
                await self._raise_for_response(response, code="docling_not_ready")
                readiness = await _read_json_response(
                    response,
                    max_bytes=self.max_response_bytes,
                    too_large_code="docling_response_too_large",
                )

            async with session.get(
                f"{self.base_url}/version", allow_redirects=False
            ) as response:
                versions: dict[str, Any] = {}
                if response.status == 200:
                    versions = await _read_json_response(
                        response,
                        max_bytes=self.max_response_bytes,
                        too_large_code="docling_response_too_large",
                    )
                elif response.status != 403:
                    await self._raise_for_response(
                        response, code="docling_version_failed"
                    )
        return ServiceHealth(
            ready=_docling_readiness_is_explicit(readiness),
            readiness=readiness,
            versions=versions,
        )

    async def version(self) -> dict[str, Any]:
        """Return the observed Docling Serve component-version payload."""

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, headers=self.headers
        ) as session:
            async with session.get(
                f"{self.base_url}/version", allow_redirects=False
            ) as response:
                await self._raise_for_response(response, code="docling_version_failed")
                return await _read_json_response(
                    response,
                    max_bytes=self.max_response_bytes,
                    too_large_code="docling_response_too_large",
                )

    async def convert(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
        options: Mapping[str, Any] | None = None,
        resume_task_id: str | None = None,
        on_task_submitted: TaskSubmittedHook | None = None,
    ) -> DoclingConversionResult:
        """Convert one artifact and return the serialized ``DoclingDocument``.

        When the async API is enabled, ``resume_task_id`` resumes polling an
        already-persisted remote task instead of submitting the artifact again.
        ``on_task_submitted`` lets callers persist the task id before polling.
        """

        normalized_options = {
            "to_formats": ("json",),
            "image_export_mode": "embedded",
            "do_ocr": True,
            "table_mode": "accurate",
            **dict(options or {}),
        }
        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, headers=self.headers
        ) as session:
            if not self.use_async_api:
                raw = await self._submit_sync(
                    session,
                    content,
                    filename=filename,
                    media_type=media_type,
                    options=normalized_options,
                )
                return await self._with_evidence(self._normalize_result(raw))

            task_id = resume_task_id
            if task_id is None:
                task_id = await self._submit_async(
                    session,
                    content,
                    filename=filename,
                    media_type=media_type,
                    options=normalized_options,
                )
                if on_task_submitted is not None:
                    hook_result = on_task_submitted(task_id)
                    if isinstance(hook_result, Awaitable):
                        await hook_result

            await self._wait_for_task(session, task_id)
            raw = await self._fetch_result(session, task_id)
            return await self._with_evidence(
                self._normalize_result(raw, remote_task_id=task_id)
            )

    async def _with_evidence(
        self, result: DoclingConversionResult
    ) -> DoclingConversionResult:
        measured = await self._with_measurement(result)
        attestation, error = await _resolve_runtime_attestation(
            self.runtime_reporter,
            component_id="docling",
            invocation_id=measured.remote_task_id,
        )
        return DoclingConversionResult(
            document=measured.document,
            raw_response=measured.raw_response,
            status=measured.status,
            processing_time_seconds=measured.processing_time_seconds,
            timings=measured.timings,
            errors=measured.errors,
            remote_task_id=measured.remote_task_id,
            memory_measurement=measured.memory_measurement,
            runtime_attestation=attestation,
            runtime_attestation_error=error,
        )

    async def _with_measurement(
        self, result: DoclingConversionResult
    ) -> DoclingConversionResult:
        if self.memory_reporter is None:
            return result
        if result.remote_task_id is None:
            raise ParserServiceError(
                "Docling resource measurement has no task identity",
                code="docling_memory_measurement_unbound",
            )
        try:
            measurement = parse_trusted_memory_measurement(
                await self.memory_reporter.resolve(
                    component_id="docling", remote_task_id=result.remote_task_id
                )
            )
        except Exception:
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.FAILED,
                measurement_id=result.remote_task_id,
                failure_code="docling_memory_measurement_failed",
            )
        if (
            measurement is not None
            and measurement.measurement_id != result.remote_task_id
        ):
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.FAILED,
                measurement_id=result.remote_task_id,
                failure_code="docling_memory_measurement_unbound",
            )
        if measurement is None:
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.UNAVAILABLE,
                measurement_id=result.remote_task_id,
                failure_code="docling_memory_measurement_unavailable",
            )
        return DoclingConversionResult(
            document=result.document,
            raw_response=result.raw_response,
            status=result.status,
            processing_time_seconds=result.processing_time_seconds,
            timings=result.timings,
            errors=result.errors,
            remote_task_id=result.remote_task_id,
            memory_measurement=measurement,
            runtime_attestation=result.runtime_attestation,
            runtime_attestation_error=result.runtime_attestation_error,
        )

    def _make_form(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
        options: Mapping[str, Any],
    ) -> aiohttp.FormData:
        form = aiohttp.FormData()
        form.add_field("files", content, filename=filename, content_type=media_type)
        for name, value in options.items():
            if value is None:
                continue
            if isinstance(value, Sequence) and not isinstance(
                value, (str, bytes, bytearray)
            ):
                for item in value:
                    form.add_field(name, _stringify_form_value(item))
            else:
                form.add_field(name, _stringify_form_value(value))
        form.add_field("target_type", "inbody")
        return form

    async def _submit_sync(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        *,
        filename: str,
        media_type: str,
        options: Mapping[str, Any],
    ) -> dict[str, Any]:
        form = self._make_form(
            content, filename=filename, media_type=media_type, options=options
        )
        async with session.post(
            f"{self.base_url}/v1/convert/file",
            data=form,
            allow_redirects=False,
        ) as response:
            await self._raise_for_response(response, code="docling_conversion_failed")
            return await _read_json_response(
                response,
                max_bytes=self.max_response_bytes,
                too_large_code="docling_response_too_large",
            )

    async def _submit_async(
        self,
        session: aiohttp.ClientSession,
        content: bytes,
        *,
        filename: str,
        media_type: str,
        options: Mapping[str, Any],
    ) -> str:
        form = self._make_form(
            content, filename=filename, media_type=media_type, options=options
        )
        async with session.post(
            f"{self.base_url}/v1/convert/file/async",
            data=form,
            allow_redirects=False,
        ) as response:
            await self._raise_for_response(response, code="docling_submit_failed")
            payload = await _read_json_response(
                response,
                max_bytes=self.max_response_bytes,
                too_large_code="docling_response_too_large",
            )
        task_id = payload.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ParserServiceError(
                "Docling Serve did not return a task id",
                code="docling_missing_task_id",
                response_body=json.dumps(payload, sort_keys=True),
            )
        return task_id

    async def _wait_for_task(
        self, session: aiohttp.ClientSession, task_id: str
    ) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.task_timeout_seconds
        while True:
            if loop.time() >= deadline:
                raise ParserServiceError(
                    f"Docling task {task_id} exceeded its timeout",
                    code="docling_task_timeout",
                    retryable=True,
                )
            async with session.get(
                f"{self.base_url}/v1/status/poll/{task_id}",
                allow_redirects=False,
            ) as response:
                await self._raise_for_response(response, code="docling_poll_failed")
                payload = await _read_json_response(
                    response,
                    max_bytes=self.max_response_bytes,
                    too_large_code="docling_response_too_large",
                )
            status = str(payload.get("task_status", "")).lower()
            if status in self._TASK_SUCCESS:
                return
            if status in self._TASK_FAILURE:
                raise ParserServiceError(
                    f"Docling task {task_id} failed: {payload.get('error_message') or 'unknown error'}",
                    code="docling_task_failed",
                    response_body=json.dumps(payload, sort_keys=True),
                )
            await asyncio.sleep(self.poll_interval_seconds)

    async def _fetch_result(
        self, session: aiohttp.ClientSession, task_id: str
    ) -> dict[str, Any]:
        async with session.get(
            f"{self.base_url}/v1/result/{task_id}", allow_redirects=False
        ) as response:
            await self._raise_for_response(response, code="docling_result_failed")
            return await _read_json_response(
                response,
                max_bytes=self.max_response_bytes,
                too_large_code="docling_response_too_large",
            )

    @classmethod
    def _normalize_result(
        cls, raw: dict[str, Any], *, remote_task_id: str | None = None
    ) -> DoclingConversionResult:
        status = str(raw.get("status", "failure"))
        if status not in cls._SUCCESS_STATUSES:
            raise ParserServiceError(
                f"Docling conversion returned status {status!r}",
                code="docling_invalid_result",
                response_body=json.dumps(raw, sort_keys=True),
            )
        wrapper = raw.get("document")
        if not isinstance(wrapper, Mapping):
            raise ParserServiceError(
                "Docling response has no document object",
                code="docling_missing_document",
                response_body=json.dumps(raw, sort_keys=True),
            )
        document = wrapper.get("json_content")
        if isinstance(document, str):
            try:
                document = json.loads(document)
            except json.JSONDecodeError as exc:
                raise ParserServiceError(
                    "Docling json_content is not valid JSON",
                    code="docling_invalid_json_content",
                ) from exc
        if not isinstance(document, dict):
            raise ParserServiceError(
                "Docling response did not include serialized DoclingDocument JSON",
                code="docling_missing_json_content",
                response_body=json.dumps(raw, sort_keys=True),
            )
        errors = raw.get("errors") or []
        timings_value = raw.get("timings")
        timings = (
            cast("dict[str, Any]", timings_value)
            if isinstance(timings_value, dict)
            else {}
        )
        return DoclingConversionResult(
            document=document,
            raw_response=raw,
            status=status,
            processing_time_seconds=_optional_float(raw.get("processing_time")),
            timings=timings,
            errors=tuple(errors) if isinstance(errors, list) else (str(errors),),
            remote_task_id=remote_task_id,
        )

    @staticmethod
    async def _raise_for_response(
        response: aiohttp.ClientResponse, *, code: str
    ) -> None:
        if 200 <= response.status < 300:
            return
        body = await _read_response_preview(response)
        raise ParserServiceError(
            f"Parser service returned HTTP {response.status}",
            code=code,
            status_code=response.status,
            retryable=response.status in {408, 429, 502, 503, 504},
            response_body=body,
        )


class GrobidClient:
    """Client for GROBID's scholarly full-text TEI service."""

    DEFAULT_COORDINATES = (
        "persName",
        "head",
        "p",
        "s",
        "ref",
        "biblStruct",
        "figure",
        "formula",
    )

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8070",
        *,
        connect_timeout_seconds: float = 10.0,
        timeout_seconds: float = 180.0,
        max_response_bytes: int = DEFAULT_GROBID_MAX_RESPONSE_BYTES,
        coordinates: Sequence[str] = DEFAULT_COORDINATES,
        consolidate_header: int = 0,
        consolidate_citations: int = 0,
        segment_sentences: bool = True,
        api_key: str | None = None,
        memory_reporter: RemoteMemoryMeasurementReporter | None = None,
        runtime_reporter: RemoteRuntimeAttestationReporter | None = None,
    ) -> None:
        if connect_timeout_seconds <= 0 or timeout_seconds <= 0:
            raise ValueError("GROBID timeouts must be positive")
        if (
            not isinstance(max_response_bytes, int)
            or isinstance(max_response_bytes, bool)
            or max_response_bytes <= 0
        ):
            raise ValueError("GROBID max_response_bytes must be a positive integer")
        self.base_url = _validate_authenticated_endpoint(
            base_url, service_name="GROBID"
        )
        self.connect_timeout_seconds = connect_timeout_seconds
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.coordinates = tuple(coordinates)
        self.consolidate_header = consolidate_header
        self.consolidate_citations = consolidate_citations
        self.segment_sentences = segment_sentences
        self.api_key = _required_service_api_key(
            api_key,
            environment_name="GROBID_API_KEY",
            service_name="GROBID",
        )
        self.memory_reporter = memory_reporter
        self.runtime_reporter = runtime_reporter

    @property
    def headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    async def health(self) -> bool:
        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, headers=self.headers
        ) as session:
            async with session.get(
                f"{self.base_url}/api/isalive", allow_redirects=False
            ) as response:
                if response.status != 200:
                    return False
                body = await _read_response_bytes(
                    response,
                    max_bytes=self.max_response_bytes,
                    too_large_code="grobid_response_too_large",
                )
                return body.decode("utf-8", errors="replace").strip().lower() in {
                    "true",
                    "ok",
                    "1",
                }

    async def version(self) -> str:
        """Return the observed version reported by the running GROBID service."""

        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, headers=self.headers
        ) as session:
            async with session.get(
                f"{self.base_url}/api/version", allow_redirects=False
            ) as response:
                if response.status != 200:
                    body = await _read_response_preview(response)
                    raise ParserServiceError(
                        f"GROBID version endpoint returned HTTP {response.status}",
                        code="grobid_version_failed",
                        status_code=response.status,
                        response_body=body,
                    )
                body = await _read_response_bytes(
                    response,
                    max_bytes=self.max_response_bytes,
                    too_large_code="grobid_response_too_large",
                )
        return _normalize_grobid_version(body)

    async def process_fulltext(
        self, content: bytes, *, filename: str = "document.pdf"
    ) -> GrobidResult:
        measurement_request_id = (
            str(uuid4())
            if self.memory_reporter is not None or self.runtime_reporter is not None
            else None
        )
        form = aiohttp.FormData()
        form.add_field(
            "input", content, filename=filename, content_type="application/pdf"
        )
        form.add_field("consolidateHeader", str(self.consolidate_header))
        form.add_field("consolidateCitations", str(self.consolidate_citations))
        form.add_field("includeRawCitations", "1")
        form.add_field("segmentSentences", "1" if self.segment_sentences else "0")
        for coordinate in self.coordinates:
            form.add_field("teiCoordinates", coordinate)

        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        request_headers = self.headers
        if measurement_request_id is not None:
            request_headers[_INVOCATION_ID_HEADER] = measurement_request_id
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.base_url}/api/processFulltextDocument",
                data=form,
                headers=request_headers,
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    body = await _read_response_preview(response)
                    raise ParserServiceError(
                        f"GROBID returned HTTP {response.status}",
                        code="grobid_conversion_failed",
                        status_code=response.status,
                        retryable=response.status in {408, 429, 503, 504},
                        response_body=body,
                    )
                tei = await _read_response_bytes(
                    response,
                    max_bytes=self.max_response_bytes,
                    too_large_code="grobid_response_too_large",
                )
        if b"<TEI" not in tei and b":TEI" not in tei:
            raise ParserServiceError(
                "GROBID response is not TEI XML",
                code="grobid_invalid_tei",
                response_body=tei[:_RESPONSE_BODY_PREVIEW_BYTES].decode(
                    "utf-8", errors="replace"
                ),
            )
        measurement = await self._resolve_memory_measurement(measurement_request_id)
        attestation, attestation_error = await _resolve_runtime_attestation(
            self.runtime_reporter,
            component_id="grobid",
            invocation_id=measurement_request_id,
        )
        return GrobidResult(
            tei_xml=tei,
            coordinates=self.coordinates,
            status_code=200,
            remote_request_id=measurement_request_id,
            memory_measurement=measurement,
            runtime_attestation=attestation,
            runtime_attestation_error=attestation_error,
        )

    async def _resolve_memory_measurement(
        self, measurement_request_id: str | None
    ) -> MemoryMeasurement | None:
        if self.memory_reporter is None:
            return None
        if measurement_request_id is None:
            raise ParserServiceError(
                "GROBID resource measurement has no request identity",
                code="grobid_memory_measurement_unbound",
            )
        try:
            measurement = parse_trusted_memory_measurement(
                await self.memory_reporter.resolve(
                    component_id="grobid", remote_task_id=measurement_request_id
                )
            )
        except Exception:
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.FAILED,
                measurement_id=measurement_request_id,
                failure_code="grobid_memory_measurement_failed",
            )
        if (
            measurement is not None
            and measurement.measurement_id != measurement_request_id
        ):
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.FAILED,
                measurement_id=measurement_request_id,
                failure_code="grobid_memory_measurement_unbound",
            )
        if measurement is None:
            measurement = MemoryMeasurement(
                status=MemoryMeasurementStatus.UNAVAILABLE,
                measurement_id=measurement_request_id,
                failure_code="grobid_memory_measurement_unavailable",
            )
        return measurement


class OCRmyPDFRunner:
    """Run OCRmyPDF without a shell and return, but never replace, a derivative."""

    def __init__(
        self,
        executable: str = "ocrmypdf",
        *,
        timeout_seconds: float = 1800.0,
        probe_timeout_seconds: float = 30.0,
        languages: Sequence[str] = ("eng",),
        jobs: int = 1,
        rotate_pages: bool = True,
        deskew: bool = True,
        optimize: int = 1,
        tesseract_executable: str = "tesseract",
        memory_meter: InvocationMemoryMeter | None = None,
        memory_boundary: str = "ocrmypdf-local-process",
        subprocess_output_limit_bytes: int = _DEFAULT_SUBPROCESS_OUTPUT_LIMIT_BYTES,
        subprocess_cleanup_timeout_seconds: float = (
            _DEFAULT_SUBPROCESS_CLEANUP_TIMEOUT_SECONDS
        ),
    ) -> None:
        if not 0 <= optimize <= 3:
            raise ValueError("OCRmyPDF optimize must be between 0 and 3")
        if timeout_seconds <= 0 or probe_timeout_seconds <= 0:
            raise ValueError("OCRmyPDF timeouts must be positive")
        if subprocess_output_limit_bytes <= 0:
            raise ValueError("OCRmyPDF subprocess output limit must be positive")
        if subprocess_cleanup_timeout_seconds <= 0:
            raise ValueError("OCRmyPDF subprocess cleanup timeout must be positive")
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.probe_timeout_seconds = probe_timeout_seconds
        self.languages = tuple(languages)
        self.jobs = jobs
        self.rotate_pages = rotate_pages
        self.deskew = deskew
        self.optimize = optimize
        self.tesseract_executable = tesseract_executable
        self.memory_meter = memory_meter
        self.memory_boundary = memory_boundary
        self.subprocess_output_limit_bytes = subprocess_output_limit_bytes
        self.subprocess_cleanup_timeout_seconds = subprocess_cleanup_timeout_seconds

    def _begin_memory_measurement(self) -> MemoryMeasurementLease | None:
        if self.memory_meter is None:
            return None
        try:
            return self.memory_meter.begin(
                MemoryMeasurementRequest(
                    measurement_id=str(uuid4()),
                    component_id="ocrmypdf",
                    boundary=self.memory_boundary,
                )
            )
        except Exception as exc:
            raise ParserServiceError(
                "Unable to create the OCRmyPDF memory measurement boundary",
                code="ocrmypdf_memory_measurement_failed",
            ) from exc

    async def version(self) -> str:
        process, stdout, stderr = await _run_capped_subprocess(
            (self.executable, "--version"),
            timeout_seconds=self.probe_timeout_seconds,
            output_limit_bytes=self.subprocess_output_limit_bytes,
            cleanup_timeout_seconds=self.subprocess_cleanup_timeout_seconds,
            timeout_message="Unable to read OCRmyPDF version before the probe timeout",
            timeout_code="ocrmypdf_version_timeout",
        )
        if process.returncode != 0:
            raise ParserServiceError(
                "Unable to read OCRmyPDF version",
                code="ocrmypdf_version_failed",
                response_body=stderr.decode("utf-8", errors="replace")[:8192],
            )
        return stdout.decode("utf-8", errors="replace").strip()

    async def tesseract_version(self) -> str:
        process, stdout, stderr = await _run_capped_subprocess(
            (self.tesseract_executable, "--version"),
            timeout_seconds=self.probe_timeout_seconds,
            output_limit_bytes=self.subprocess_output_limit_bytes,
            cleanup_timeout_seconds=self.subprocess_cleanup_timeout_seconds,
            timeout_message="Unable to read Tesseract version before the probe timeout",
            timeout_code="tesseract_version_timeout",
        )
        if process.returncode != 0:
            raise ParserServiceError(
                "Unable to read Tesseract version",
                code="tesseract_version_failed",
                response_body=stderr.decode("utf-8", errors="replace")[:8192],
            )
        first_line = stdout.decode("utf-8", errors="replace").splitlines()
        return first_line[0].strip() if first_line else ""

    async def convert(self, content: bytes) -> OCRResult:
        with tempfile.TemporaryDirectory(prefix="deepcritical-ocr-") as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "original.pdf"
            output_path = tmp_path / "searchable.pdf"
            sidecar_path = tmp_path / "searchable.txt"
            input_path.write_bytes(content)

            command = [
                self.executable,
                "--output-type",
                "pdf",
                "--optimize",
                str(self.optimize),
                "--skip-text",
                "--sidecar",
                os.fspath(sidecar_path),
                "--jobs",
                str(self.jobs),
                "--language",
                "+".join(self.languages),
            ]
            if self.rotate_pages:
                command.append("--rotate-pages")
            if self.deskew:
                command.append("--deskew")
            command.extend([os.fspath(input_path), os.fspath(output_path)])

            lease = self._begin_memory_measurement()
            try:
                subprocess_command = (
                    lease.wrap_subprocess_command(command)
                    if lease is not None
                    else tuple(command)
                )
                process, stdout_bytes, stderr_bytes = await _run_capped_subprocess(
                    subprocess_command,
                    timeout_seconds=self.timeout_seconds,
                    output_limit_bytes=self.subprocess_output_limit_bytes,
                    cleanup_timeout_seconds=self.subprocess_cleanup_timeout_seconds,
                    timeout_message="OCRmyPDF exceeded its timeout",
                    timeout_code="ocrmypdf_timeout",
                    abort_hook=(
                        (lambda: _abort_memory_lease(lease))
                        if lease is not None
                        else None
                    ),
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                if process.returncode != 0 or not output_path.is_file():
                    raise ParserServiceError(
                        f"OCRmyPDF exited with code {process.returncode}",
                        code="ocrmypdf_failed",
                        status_code=process.returncode,
                        response_body=stderr[:8192],
                    )
                sidecar_text = (
                    sidecar_path.read_text(encoding="utf-8", errors="replace")
                    if sidecar_path.is_file()
                    else ""
                )
                measurement = (
                    _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    if lease is not None
                    else None
                )
                lease = None
                return OCRResult(
                    pdf_bytes=output_path.read_bytes(),
                    sidecar_text=sidecar_text,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=process.returncode,
                    memory_measurement=measurement,
                )
            except ParserServiceError as exc:
                if lease is not None:
                    exc.memory_measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                raise
            except asyncio.CancelledError as exc:
                if lease is not None:
                    measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                    exc.add_note(
                        "OCRmyPDF cancellation memory measurement: "
                        f"{measurement.status.value}"
                    )
                raise
            except OSError as exc:
                error = ParserServiceError(
                    "Unable to launch OCRmyPDF",
                    code="ocrmypdf_launch_failed",
                )
                if lease is not None:
                    error.memory_measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                raise error from exc
            finally:
                if lease is not None:
                    # Only unexpected non-parser exceptions reach this path.
                    # Finish exactly once and make a cleanup failure observable.
                    measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                    if measurement.status is MemoryMeasurementStatus.FAILED:
                        raise ParserServiceError(
                            "Unable to finish the OCRmyPDF memory measurement",
                            code="ocrmypdf_memory_measurement_failed",
                            memory_measurement=measurement,
                        )


class ContainerOCRmyPDFRunner(OCRmyPDFRunner):
    """Run the pinned OCRmyPDF image with no network and explicit bind mounts."""

    def __init__(
        self,
        image: str = "jbarlow83/ocrmypdf:v17.4.1",
        *,
        runtime_executable: str = "docker",
        timeout_seconds: float = 1800.0,
        probe_timeout_seconds: float = 30.0,
        languages: Sequence[str] = ("eng",),
        jobs: int = 1,
        rotate_pages: bool = True,
        deskew: bool = True,
        optimize: int = 1,
        memory_limit: str = "4g",
        cpu_limit: float = 2.0,
        pids_limit: int = 256,
        tmpfs: str = "/tmp:size=2g,mode=1777",
        memory_meter: InvocationMemoryMeter | None = None,
        expected_digest: str | None = None,
        require_digest_addressed: bool = False,
        subprocess_output_limit_bytes: int = _DEFAULT_SUBPROCESS_OUTPUT_LIMIT_BYTES,
        subprocess_cleanup_timeout_seconds: float = (
            _DEFAULT_SUBPROCESS_CLEANUP_TIMEOUT_SECONDS
        ),
    ) -> None:
        super().__init__(
            executable="ocrmypdf",
            timeout_seconds=timeout_seconds,
            probe_timeout_seconds=probe_timeout_seconds,
            languages=languages,
            jobs=jobs,
            rotate_pages=rotate_pages,
            deskew=deskew,
            optimize=optimize,
            memory_meter=memory_meter,
            memory_boundary="ocrmypdf-container",
            subprocess_output_limit_bytes=subprocess_output_limit_bytes,
            subprocess_cleanup_timeout_seconds=(subprocess_cleanup_timeout_seconds),
        )
        digest_match = _OCI_DIGEST_REFERENCE.search(image)
        embedded_digest = digest_match.group("digest") if digest_match else None
        if expected_digest is not None and not re.fullmatch(
            r"sha256:[0-9a-f]{64}", expected_digest
        ):
            raise ValueError("OCRmyPDF expected digest must be an OCI SHA-256 digest")
        if (
            embedded_digest is not None
            and expected_digest is not None
            and embedded_digest != expected_digest
        ):
            raise ValueError(
                "OCRmyPDF image digest differs from the configured expected digest"
            )
        if embedded_digest is None and expected_digest is not None:
            image = f"{image}@{expected_digest}"
            embedded_digest = expected_digest
        image_without_digest = image.split("@", maxsplit=1)[0]
        image_name = image_without_digest.rsplit("/", 1)[-1]
        has_tag = ":" in image_name
        if (not has_tag and embedded_digest is None) or image_without_digest.endswith(
            ":latest"
        ):
            raise ValueError(
                "OCRmyPDF container image must use an explicit non-latest tag"
            )
        if require_digest_addressed and embedded_digest is None:
            raise ValueError(
                "OCRmyPDF runtime identity requires a digest-addressed image"
            )
        if pids_limit <= 0:
            raise ValueError("OCRmyPDF container PID limit must be positive")
        if not tmpfs.startswith("/tmp:"):
            raise ValueError("OCRmyPDF container tmpfs must mount /tmp")
        self.image = image
        self.container_digest = embedded_digest
        self.require_digest_addressed = require_digest_addressed
        self.runtime_executable = runtime_executable
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.pids_limit = pids_limit
        self.tmpfs = tmpfs
        self.read_only = True

    def _security_arguments(self) -> list[str]:
        arguments = [
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(self.pids_limit),
            "--tmpfs",
            self.tmpfs,
        ]
        if os.name == "posix":
            arguments.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
        if self.container_digest is not None:
            arguments.extend(["--pull", "never"])
        return arguments

    async def _force_remove_container(self, workload_id: str) -> None:
        """Kill and remove one exact invocation container by its unique name."""

        process, stdout, stderr = await _run_capped_subprocess(
            (self.runtime_executable, "rm", "--force", workload_id),
            timeout_seconds=self.subprocess_cleanup_timeout_seconds,
            output_limit_bytes=self.subprocess_output_limit_bytes,
            cleanup_timeout_seconds=self.subprocess_cleanup_timeout_seconds,
            timeout_message=(
                f"Timed out while force-removing OCR container {workload_id}"
            ),
            timeout_code="ocrmypdf_container_cleanup_timeout",
        )
        if process.returncode == 0:
            return
        detail = b"\n".join((stdout, stderr)).decode("utf-8", errors="replace")
        if "no such container" in detail.casefold():
            return
        raise RuntimeError(
            f"docker rm --force failed for {workload_id} with code "
            f"{process.returncode}: {detail[:8192]}"
        )

    async def _run_container_probe(
        self,
        *container_arguments: str,
        probe_name: str,
        timeout_message: str,
        timeout_code: str,
    ) -> tuple[Any, bytes, bytes]:
        workload_id = f"deepcritical-ocr-{probe_name}-{uuid4().hex}"
        return await _run_capped_subprocess(
            (
                self.runtime_executable,
                "run",
                "--rm",
                *self._security_arguments(),
                "--name",
                workload_id,
                "--label",
                f"org.deepcritical.probe={probe_name}",
                *container_arguments,
            ),
            timeout_seconds=self.probe_timeout_seconds,
            output_limit_bytes=self.subprocess_output_limit_bytes,
            cleanup_timeout_seconds=self.subprocess_cleanup_timeout_seconds,
            timeout_message=timeout_message,
            timeout_code=timeout_code,
            abort_hook=lambda: self._force_remove_container(workload_id),
        )

    async def version(self) -> str:
        process, stdout, stderr = await self._run_container_probe(
            self.image,
            "--version",
            probe_name="version",
            timeout_message=(
                "Unable to read containerized OCRmyPDF version before the probe timeout"
            ),
            timeout_code="ocrmypdf_container_version_timeout",
        )
        if process.returncode != 0:
            raise ParserServiceError(
                "Unable to read containerized OCRmyPDF version",
                code="ocrmypdf_container_version_failed",
                response_body=stderr.decode("utf-8", errors="replace")[:8192],
            )
        return stdout.decode("utf-8", errors="replace").strip()

    async def tesseract_version(self) -> str:
        process, stdout, stderr = await self._run_container_probe(
            "--entrypoint",
            "tesseract",
            self.image,
            "--version",
            probe_name="tesseract-version",
            timeout_message=(
                "Unable to read containerized Tesseract version before the probe "
                "timeout"
            ),
            timeout_code="tesseract_container_version_timeout",
        )
        if process.returncode != 0:
            raise ParserServiceError(
                "Unable to read containerized Tesseract version",
                code="tesseract_container_version_failed",
                response_body=stderr.decode("utf-8", errors="replace")[:8192],
            )
        first_line = stdout.decode("utf-8", errors="replace").splitlines()
        return first_line[0].strip() if first_line else ""

    async def convert(self, content: bytes) -> OCRResult:
        component_versions: dict[str, str] = {}
        attestation_error: str | None = None
        if self.container_digest is None:
            attestation_error = "ocr_runtime_image_is_not_digest_addressed"
        else:
            try:
                component_versions = {
                    "ocrmypdf": await self.version(),
                    "tesseract": await self.tesseract_version(),
                }
            except Exception as exc:
                attestation_error = f"ocr_runtime_version_probe_failed: {exc}"
        with tempfile.TemporaryDirectory(prefix="deepcritical-ocr-container-") as tmp:
            workspace = Path(tmp).resolve()
            input_dir = workspace / "input"
            output_dir = workspace / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / "original.pdf").write_bytes(content)
            invocation_id = str(uuid4())
            workload_id = f"deepcritical-ocr-{invocation_id}"

            lease = self._begin_memory_measurement()
            cgroup_arguments: list[str] = []
            if lease is not None and lease.container_cgroup_parent is not None:
                cgroup_arguments = [
                    "--cgroup-parent",
                    lease.container_cgroup_parent,
                ]
            command = [
                self.runtime_executable,
                "run",
                "--rm",
                *self._security_arguments(),
                "--name",
                workload_id,
                "--label",
                f"org.deepcritical.invocation-id={invocation_id}",
                *cgroup_arguments,
                "--memory",
                self.memory_limit,
                "--cpus",
                str(self.cpu_limit),
                "--mount",
                f"type=bind,source={input_dir},target=/input,readonly",
                "--mount",
                f"type=bind,source={output_dir},target=/output",
                self.image,
                "--output-type",
                "pdf",
                "--optimize",
                str(self.optimize),
                "--skip-text",
                "--sidecar",
                "/output/searchable.txt",
                "--jobs",
                str(self.jobs),
                "--language",
                "+".join(self.languages),
            ]
            if self.rotate_pages:
                command.append("--rotate-pages")
            if self.deskew:
                command.append("--deskew")
            command.extend(["/input/original.pdf", "/output/searchable.pdf"])

            try:
                process, stdout_bytes, stderr_bytes = await _run_capped_subprocess(
                    command,
                    timeout_seconds=self.timeout_seconds,
                    output_limit_bytes=self.subprocess_output_limit_bytes,
                    cleanup_timeout_seconds=self.subprocess_cleanup_timeout_seconds,
                    timeout_message="Containerized OCRmyPDF exceeded its timeout",
                    timeout_code="ocrmypdf_container_timeout",
                    abort_hook=lambda: _abort_container_invocation(
                        self, workload_id, lease
                    ),
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                output_path = output_dir / "searchable.pdf"
                sidecar_path = output_dir / "searchable.txt"
                if process.returncode != 0 or not output_path.is_file():
                    raise ParserServiceError(
                        f"Containerized OCRmyPDF exited with code {process.returncode}",
                        code="ocrmypdf_container_failed",
                        status_code=process.returncode,
                        response_body=stderr[:8192],
                    )
                measurement = (
                    _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    if lease is not None
                    else None
                )
                lease = None
                runtime_attestation = None
                if self.container_digest is not None and not attestation_error:
                    runtime_attestation = RuntimeAttestation(
                        component_id="ocrmypdf",
                        component_version=component_versions["ocrmypdf"],
                        invocation_id=invocation_id,
                        source=(
                            RuntimeAttestationSource.DIGEST_ADDRESSED_OCI_INVOCATION
                        ),
                        reporter_id="deepcritical-container-ocr-runner-v1",
                        observed_at=utc_now(),
                        workload_id=workload_id,
                        container_reference=self.image,
                        container_digest=self.container_digest,
                        component_versions=component_versions,
                    )
                return OCRResult(
                    pdf_bytes=output_path.read_bytes(),
                    sidecar_text=(
                        sidecar_path.read_text(encoding="utf-8", errors="replace")
                        if sidecar_path.is_file()
                        else ""
                    ),
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=process.returncode,
                    memory_measurement=measurement,
                    runtime_attestation=runtime_attestation,
                    runtime_attestation_error=attestation_error,
                )
            except ParserServiceError as exc:
                if lease is not None:
                    exc.memory_measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                raise
            except asyncio.CancelledError as exc:
                if lease is not None:
                    measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                    exc.add_note(
                        "Containerized OCRmyPDF cancellation memory measurement: "
                        f"{measurement.status.value}"
                    )
                raise
            except OSError as exc:
                error = ParserServiceError(
                    "Unable to launch the OCRmyPDF container",
                    code="ocrmypdf_container_launch_failed",
                )
                if lease is not None:
                    error.memory_measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                raise error from exc
            finally:
                if lease is not None:
                    measurement = _finish_memory_measurement_once(
                        lease, boundary=self.memory_boundary
                    )
                    lease = None
                    if measurement.status is MemoryMeasurementStatus.FAILED:
                        raise ParserServiceError(
                            "Unable to finish the OCRmyPDF container memory measurement",
                            code="ocrmypdf_memory_measurement_failed",
                            memory_measurement=measurement,
                        )


async def _resolve_runtime_attestation(
    reporter: RemoteRuntimeAttestationReporter | None,
    *,
    component_id: str,
    invocation_id: str | None,
) -> tuple[RuntimeAttestation | None, str | None]:
    """Resolve strict evidence without discarding an otherwise valid parse."""

    if reporter is None:
        return None, "runtime_attestation_reporter_not_configured"
    if invocation_id is None or not invocation_id.strip():
        return None, "runtime_attestation_invocation_id_missing"
    try:
        payload = await reporter.resolve(
            component_id=component_id,
            remote_task_id=invocation_id,
        )
        if payload is None:
            return None, "runtime_attestation_unavailable"
        attestation = (
            payload
            if isinstance(payload, RuntimeAttestation)
            else RuntimeAttestation.model_validate(payload)
        )
        if (
            attestation.component_id != component_id
            or attestation.invocation_id != invocation_id
        ):
            return None, "runtime_attestation_unbound"
        return attestation, None
    except Exception as exc:
        code = (
            exc.code
            if isinstance(exc, ParserServiceError)
            else "runtime_attestation_invalid"
        )
        detail = str(exc).strip()
        return None, f"{code}: {detail}" if detail else code


async def _run_capped_subprocess(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    output_limit_bytes: int,
    cleanup_timeout_seconds: float,
    timeout_message: str,
    timeout_code: str,
    abort_hook: Callable[[], Awaitable[None] | None] | None = None,
) -> tuple[Any, bytes, bytes]:
    """Run a process with bounded capture and cancellation-safe cleanup.

    Real asyncio subprocess streams are drained continuously, retaining at
    most ``output_limit_bytes`` per stream. The ``communicate`` fallback exists
    only for lightweight injected test doubles which do not expose StreamReader
    objects; its returned bytes are capped immediately.
    """

    if not command:
        raise ValueError("subprocess command must not be empty")
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=os.name == "posix",
    )
    completion = asyncio.create_task(
        _collect_capped_process_output(process, output_limit_bytes)
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            asyncio.shield(completion), timeout=timeout_seconds
        )
        return process, stdout, stderr
    except TimeoutError as exc:
        cleanup_errors = await _shielded_subprocess_cleanup(
            process,
            completion,
            abort_hook=abort_hook,
            cleanup_timeout_seconds=cleanup_timeout_seconds,
        )
        detail = _cleanup_error_detail(cleanup_errors)
        raise ParserServiceError(
            timeout_message,
            code=timeout_code,
            retryable=True,
            response_body=detail,
        ) from exc
    except asyncio.CancelledError as exc:
        cleanup_errors = await _shielded_subprocess_cleanup(
            process,
            completion,
            abort_hook=abort_hook,
            cleanup_timeout_seconds=cleanup_timeout_seconds,
        )
        if cleanup_errors:
            exc.add_note(_cleanup_error_detail(cleanup_errors) or "cleanup failed")
        raise


async def _collect_capped_process_output(
    process: Any, output_limit_bytes: int
) -> tuple[bytes, bytes]:
    stdout_stream = getattr(process, "stdout", None)
    stderr_stream = getattr(process, "stderr", None)
    wait_method = getattr(process, "wait", None)
    if (
        callable(getattr(stdout_stream, "read", None))
        and callable(getattr(stderr_stream, "read", None))
        and callable(wait_method)
    ):
        stdout_task = asyncio.create_task(
            _drain_capped_stream(stdout_stream, output_limit_bytes)
        )
        stderr_task = asyncio.create_task(
            _drain_capped_stream(stderr_stream, output_limit_bytes)
        )
        await wait_method()
        stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
        return stdout, stderr

    # Compatibility path for injected tests. asyncio's real Process always
    # takes the bounded StreamReader path above.
    stdout, stderr = await process.communicate()
    return (
        _cap_subprocess_output(bytes(stdout), output_limit_bytes),
        _cap_subprocess_output(bytes(stderr), output_limit_bytes),
    )


async def _drain_capped_stream(stream: Any, limit: int) -> bytes:
    captured = bytearray()
    truncated = False
    while True:
        chunk = await stream.read(min(65536, limit + 1))
        if not chunk:
            break
        remaining = max(0, limit - len(captured))
        if remaining:
            captured.extend(chunk[:remaining])
        if len(chunk) > remaining:
            truncated = True
    return _cap_subprocess_output(bytes(captured), limit, truncated=truncated)


def _cap_subprocess_output(
    output: bytes, limit: int, *, truncated: bool = False
) -> bytes:
    if len(output) <= limit and not truncated:
        return output
    if limit <= len(_OUTPUT_TRUNCATION_MARKER):
        return _OUTPUT_TRUNCATION_MARKER[:limit]
    prefix_size = limit - len(_OUTPUT_TRUNCATION_MARKER)
    return output[:prefix_size] + _OUTPUT_TRUNCATION_MARKER


async def _shielded_subprocess_cleanup(
    process: Any,
    completion: asyncio.Task[tuple[bytes, bytes]],
    *,
    abort_hook: Callable[[], Awaitable[None] | None] | None,
    cleanup_timeout_seconds: float,
) -> tuple[str, ...]:
    cleanup = asyncio.create_task(
        _cleanup_subprocess(
            process,
            completion,
            abort_hook=abort_hook,
            cleanup_timeout_seconds=cleanup_timeout_seconds,
        )
    )
    cancellation: asyncio.CancelledError | None = None
    while True:
        try:
            errors = await asyncio.shield(cleanup)
            break
        except asyncio.CancelledError as exc:
            if cleanup.cancelled():
                # ``shield`` never cancels the inner task. If the cleanup task
                # cancelled itself, retrying it would spin forever.
                raise
            # Cancellation must not be able to cancel the cleanup task itself.
            # Keep waiting under a fresh shield after every cancellation so a
            # timeout/cancellation race or repeated shutdown requests cannot
            # leave parser descendants running. Re-raise cancellation only
            # after the bounded cleanup has completed.
            if cancellation is None:
                cancellation = exc

    if cancellation is not None:
        if errors:
            cancellation.add_note(
                _cleanup_error_detail(errors) or "subprocess cleanup failed"
            )
        raise cancellation
    return errors


async def _cleanup_subprocess(
    process: Any,
    completion: asyncio.Task[tuple[bytes, bytes]],
    *,
    abort_hook: Callable[[], Awaitable[None] | None] | None,
    cleanup_timeout_seconds: float,
) -> tuple[str, ...]:
    errors: list[str] = []
    _kill_process_group(process, errors)

    if abort_hook is not None:
        try:
            abort_result = abort_hook()
            if isinstance(abort_result, Awaitable):
                await asyncio.wait_for(abort_result, timeout=cleanup_timeout_seconds)
        except Exception as exc:
            errors.append(f"abort hook failed: {exc}")

    try:
        await asyncio.wait_for(
            asyncio.shield(completion), timeout=cleanup_timeout_seconds
        )
    except TimeoutError:
        errors.append("subprocess did not exit before the cleanup timeout")
        completion.cancel()
        try:
            await completion
        except (asyncio.CancelledError, Exception):
            pass
    except Exception as exc:
        errors.append(f"subprocess reap failed: {exc}")
    return tuple(errors)


def _kill_process_group(process: Any, errors: list[str]) -> None:
    """Kill a POSIX process group, with a direct-process fallback."""

    pid = getattr(process, "pid", None)
    group_killed = False
    if os.name == "posix" and isinstance(pid, int) and pid > 0:
        try:
            os.killpg(pid, _SIGKILL)
            group_killed = True
        except ProcessLookupError:
            group_killed = True
        except Exception as exc:
            errors.append(f"process-group kill failed: {exc}")
    if group_killed:
        return
    try:
        process.kill()
    except ProcessLookupError:
        return
    except Exception as exc:
        errors.append(f"process kill failed: {exc}")


def _cleanup_error_detail(errors: Sequence[str]) -> str | None:
    if not errors:
        return None
    return "subprocess cleanup failures: " + "; ".join(errors)


async def _abort_memory_lease(lease: MemoryMeasurementLease | None) -> None:
    if lease is None:
        return
    abort = getattr(lease, "abort", None)
    if abort is not None:
        # The cgroup-v2 fallback may poll for descendant exit for up to two
        # seconds. Keep that kernel/filesystem cleanup off the event loop.
        await asyncio.to_thread(abort)


async def _abort_container_invocation(
    runner: ContainerOCRmyPDFRunner,
    workload_id: str,
    lease: MemoryMeasurementLease | None,
) -> None:
    errors: list[str] = []
    try:
        await runner._force_remove_container(workload_id)
    except Exception as exc:
        errors.append(f"container force-remove failed: {exc}")
    if lease is not None:
        try:
            await _abort_memory_lease(lease)
        except Exception as exc:
            errors.append(f"invocation cgroup abort failed: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))


def _finish_memory_measurement_once(
    lease: MemoryMeasurementLease, *, boundary: str
) -> MemoryMeasurement:
    """Finish once and return evidence even when parser execution failed."""

    try:
        return lease.finish()
    except Exception as exc:
        request = getattr(lease, "request", None)
        measurement_id = getattr(request, "measurement_id", None)
        return MemoryMeasurement(
            status=MemoryMeasurementStatus.FAILED,
            boundary=boundary,
            measurement_id=measurement_id,
            failure_code=f"memory_measurement_finish_failed:{exc.__class__.__name__}",
        )


async def _read_response_bytes(
    response: aiohttp.ClientResponse,
    *,
    max_bytes: int,
    too_large_code: str,
) -> bytes:
    """Read one response under a hard decoded-body byte ceiling.

    ``Content-Length`` provides an early rejection when present. The streamed
    count is still authoritative because responses may be chunked, omit the
    header, or be transparently decompressed by the HTTP client.
    """

    declared_bytes = response.content_length
    if declared_bytes is not None and declared_bytes > max_bytes:
        raise ParserServiceError(
            (
                f"Parser response declares {declared_bytes} bytes, exceeding "
                f"the configured {max_bytes}-byte limit"
            ),
            code=too_large_code,
            status_code=response.status,
        )

    body = bytearray()
    async for chunk in response.content.iter_chunked(_HTTP_RESPONSE_CHUNK_BYTES):
        received_bytes = len(body) + len(chunk)
        if received_bytes > max_bytes:
            raise ParserServiceError(
                (
                    f"Parser response exceeded the configured {max_bytes}-byte "
                    f"limit while streaming (received at least {received_bytes} bytes)"
                ),
                code=too_large_code,
                status_code=response.status,
            )
        body.extend(chunk)
    return bytes(body)


async def _read_response_preview(
    response: aiohttp.ClientResponse,
    *,
    max_bytes: int = _RESPONSE_BODY_PREVIEW_BYTES,
) -> str:
    """Return a bounded error-body preview without materializing the response."""

    declared_bytes = response.content_length
    if declared_bytes is not None and declared_bytes > max_bytes:
        return f"[response body omitted: declared {declared_bytes} bytes]"

    body = bytearray()
    truncated = False
    async for chunk in response.content.iter_chunked(_HTTP_RESPONSE_CHUNK_BYTES):
        remaining = max_bytes - len(body)
        if len(chunk) > remaining:
            body.extend(chunk[:remaining])
            truncated = True
            break
        body.extend(chunk)
        if len(body) == max_bytes:
            truncated = True
            break
    preview = bytes(body).decode("utf-8", errors="replace")
    return f"{preview}\n[response body truncated]" if truncated else preview


async def _read_json_response(
    response: aiohttp.ClientResponse,
    *,
    max_bytes: int = _DEFAULT_CONTROL_RESPONSE_LIMIT_BYTES,
    too_large_code: str = "parser_response_too_large",
) -> dict[str, Any]:
    body = await _read_response_bytes(
        response,
        max_bytes=max_bytes,
        too_large_code=too_large_code,
    )
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParserServiceError(
            "Parser service returned invalid JSON",
            code="parser_invalid_json_response",
            response_body=body[:_RESPONSE_BODY_PREVIEW_BYTES].decode(
                "utf-8", errors="replace"
            ),
        ) from exc
    if not isinstance(payload, dict):
        raise ParserServiceError(
            "Parser service returned a non-object JSON response",
            code="parser_invalid_json_shape",
        )
    return payload


def _optional_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ContainerOCRmyPDFRunner",
    "DoclingConversionResult",
    "DoclingServeClient",
    "GrobidClient",
    "GrobidResult",
    "HttpRemoteMemoryMeasurementReporter",
    "HttpRemoteRuntimeAttestationReporter",
    "ManagedParserAdapter",
    "ManagedParserResult",
    "OCRResult",
    "OCRmyPDFRunner",
    "ParserServiceError",
    "RemoteMemoryMeasurementReporter",
    "RemoteRuntimeAttestationReporter",
    "ServiceHealth",
]
