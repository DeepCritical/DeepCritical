from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from DeepResearch.src.document_processing.clients import (
    ContainerOCRmyPDFRunner,
    DoclingConversionResult,
    DoclingServeClient,
    GrobidClient,
    HttpRemoteMemoryMeasurementReporter,
    HttpRemoteRuntimeAttestationReporter,
    ManagedParserAdapter,
    ManagedParserResult,
    OCRmyPDFRunner,
    ParserServiceError,
    RemoteMemoryMeasurementReporter,
    RemoteRuntimeAttestationReporter,
)
from DeepResearch.src.document_processing.models import (
    MemoryMeasurement,
    MemoryMeasurementScope,
    MemoryMeasurementStatus,
    RuntimeAttestation,
    RuntimeAttestationSource,
)
from DeepResearch.src.document_processing.resources import MemoryMeasurementRequest


class _ManagedAdapterFixture:
    provider_name = "disabled-test-provider"
    parser_version = "1"

    async def parse(
        self,
        content: bytes,
        *,
        filename: str,
        media_type: str,
    ) -> ManagedParserResult:
        return ManagedParserResult(
            provider_name=self.provider_name,
            parser_version=self.parser_version,
            raw_output=content,
            media_type=media_type,
            metadata={"filename": filename},
        )


class _RemoteMemoryReporter:
    async def resolve(
        self, *, parser_name: str, remote_task_id: str | None
    ) -> dict[str, object]:
        assert parser_name == "docling"
        assert remote_task_id == "task-123"
        return {
            "status": "measured",
            "method": "cgroup-v2-memory.peak",
            "scope": "invocation_cgroup",
            "boundary": "docling-rq-job",
            "peak_memory_bytes": 2048,
            "environment_sha256": "a" * 64,
            "measurement_id": "task-123",
            "exclusive": True,
            "memory_events": {"oom_kill": 0},
        }


class _GrobidMemoryReporter:
    def __init__(self) -> None:
        self.remote_task_id: str | None = None

    async def resolve(
        self, *, parser_name: str, remote_task_id: str | None
    ) -> dict[str, object]:
        assert parser_name == "grobid"
        assert remote_task_id is not None
        self.remote_task_id = remote_task_id
        return {
            "status": "measured",
            "method": "cgroup-v2-memory.peak",
            "scope": "invocation_cgroup",
            "boundary": "grobid-request",
            "peak_memory_bytes": 4096,
            "environment_sha256": "b" * 64,
            "measurement_id": remote_task_id,
            "started_at": "2026-07-17T12:00:00Z",
            "finished_at": "2026-07-17T12:00:01Z",
            "exclusive": True,
            "shared_overhead_excluded": True,
            "memory_events": {"oom_kill": 0},
        }


class _GrobidRuntimeReporter:
    def __init__(self) -> None:
        self.remote_task_id: str | None = None

    async def resolve(
        self, *, parser_name: str, remote_task_id: str | None
    ) -> RuntimeAttestation:
        assert parser_name == "grobid"
        assert remote_task_id is not None
        self.remote_task_id = remote_task_id
        digest = "sha256:" + ("9" * 64)
        return RuntimeAttestation(
            parser_name="grobid",
            parser_version="0.9.0",
            invocation_id=remote_task_id,
            source=RuntimeAttestationSource.AUTHENTICATED_DEPLOYMENT_REPORTER,
            reporter_id="fixture-supervisor",
            observed_at=datetime.now(UTC),
            workload_id="grobid-worker-1",
            container_reference=f"registry.test/grobid@{digest}",
            container_digest=digest,
            component_versions={"grobid": "0.9.0"},
            model_versions={"full": "0.9.0"},
            model_hashes={"full": "8" * 64},
        )


class _MismatchedMemoryReporter:
    async def resolve(
        self, *, parser_name: str, remote_task_id: str | None
    ) -> dict[str, object]:
        assert parser_name in {"docling", "grobid"}
        assert remote_task_id is not None
        return {
            "status": "measured",
            "method": "cgroup-v2-memory.peak",
            "scope": "invocation_cgroup",
            "boundary": f"{parser_name}-invocation",
            "peak_memory_bytes": 1024,
            "environment_sha256": "c" * 64,
            "measurement_id": "different-invocation",
            "exclusive": True,
            "memory_events": {"oom_kill": 0},
        }


class _MeasuredLease:
    def __init__(self, request: MemoryMeasurementRequest) -> None:
        self.request = request
        self.finished = False
        self.attached_pids: list[int] = []
        self.wrapped_commands: list[tuple[str, ...]] = []

    @property
    def container_cgroup_parent(self) -> str:
        return "/deepcritical/ocr-fixture"

    def attach_pid(self, pid: int) -> None:
        self.attached_pids.append(pid)

    def wrap_subprocess_command(self, command: Sequence[str]) -> tuple[str, ...]:
        wrapped = ("cgroup-bootstrap", *command)
        self.wrapped_commands.append(wrapped)
        return wrapped

    def finish(self) -> MemoryMeasurement:
        self.finished = True
        return MemoryMeasurement(
            status=MemoryMeasurementStatus.MEASURED,
            method="cgroup-v2-memory.peak",
            scope=MemoryMeasurementScope.INVOCATION_CGROUP,
            boundary=self.request.boundary,
            peak_memory_bytes=8192,
            environment_sha256="d" * 64,
            measurement_id=self.request.measurement_id,
            started_at=datetime(2026, 7, 17, 12, tzinfo=UTC),
            finished_at=datetime(2026, 7, 17, 12, 0, 1, tzinfo=UTC),
            exclusive=True,
            shared_overhead_excluded=True,
            memory_events={"oom_kill": 0},
        )


class _MeasuredMeter:
    def __init__(self) -> None:
        self.lease: _MeasuredLease | None = None

    def begin(self, request: MemoryMeasurementRequest) -> _MeasuredLease:
        self.lease = _MeasuredLease(request)
        return self.lease


def test_managed_parser_protocol_exists_without_enabling_a_provider() -> None:
    adapter = _ManagedAdapterFixture()

    assert isinstance(adapter, ManagedParserAdapter)


@pytest.mark.asyncio
async def test_http_memory_reporter_authenticates_and_polls_exact_task() -> None:
    requests: list[tuple[str, str, str | None]] = []

    async def measurement(request: web.Request) -> web.Response:
        parser_name = request.match_info["parser_name"]
        task_id = request.match_info["task_id"]
        requests.append((parser_name, task_id, request.headers.get("X-API-Key")))
        if len(requests) == 1:
            return web.Response(status=202)
        return web.json_response(
            {
                "status": "measured",
                "method": "cgroup-v2-memory.peak",
                "scope": "invocation_cgroup",
                "boundary": "docling-rq-job",
                "peak_memory_bytes": 2048,
                "environment_sha256": "a" * 64,
                "measurement_id": task_id,
                "started_at": "2026-07-17T12:00:00Z",
                "finished_at": "2026-07-17T12:00:01Z",
                "exclusive": True,
                "shared_overhead_excluded": True,
                "memory_events": {"oom_kill": 0},
            }
        )

    app = web.Application()
    app.router.add_get(
        "/v1/measurements/{parser_name}/{task_id}",
        measurement,
    )
    server = TestServer(app)
    await server.start_server()
    try:
        reporter = HttpRemoteMemoryMeasurementReporter(
            str(server.make_url("/")).rstrip("/"),
            api_key="resource-reporter-fixture-key",
            poll_interval_seconds=0.001,
        )
        payload = await reporter.resolve(
            parser_name="docling",
            remote_task_id="task-123",
        )
    finally:
        await server.close()

    assert payload["measurement_id"] == "task-123"
    assert requests == [
        ("docling", "task-123", "resource-reporter-fixture-key"),
        ("docling", "task-123", "resource-reporter-fixture-key"),
    ]


@pytest.mark.asyncio
async def test_http_runtime_reporter_authenticates_and_binds_exact_task() -> None:
    requests: list[tuple[str, str, str | None]] = []
    digest = "sha256:" + ("d" * 64)

    async def attestation(request: web.Request) -> web.Response:
        parser_name = request.match_info["parser_name"]
        task_id = request.match_info["task_id"]
        requests.append((parser_name, task_id, request.headers.get("X-API-Key")))
        if len(requests) == 1:
            return web.Response(status=202)
        return web.json_response(
            {
                "schema_version": "deepcritical-runtime-attestation-v1",
                "parser_name": parser_name,
                "parser_version": "2.113.0",
                "invocation_id": task_id,
                "source": "authenticated_deployment_reporter",
                "reporter_id": "fixture-supervisor",
                "observed_at": "2026-07-18T00:00:00Z",
                "workload_id": "docling-worker-1",
                "container_reference": f"registry.test/docling@{digest}",
                "container_digest": digest,
                "component_versions": {
                    "docling": "2.113.0",
                    "docling_serve": "1.21.0",
                },
                "model_versions": {"layout": "1"},
                "model_hashes": {"layout": "e" * 64},
            }
        )

    app = web.Application()
    app.router.add_get(
        "/v1/attestations/{parser_name}/{task_id}",
        attestation,
    )
    server = TestServer(app)
    await server.start_server()
    try:
        reporter = HttpRemoteRuntimeAttestationReporter(
            str(server.make_url("/")).rstrip("/"),
            expected_reporter_id="fixture-supervisor",
            api_key="runtime-reporter-fixture-key",
            poll_interval_seconds=0.001,
        )
        assert isinstance(reporter, RemoteRuntimeAttestationReporter)
        payload = await reporter.resolve(
            parser_name="docling", remote_task_id="task-123"
        )
    finally:
        await server.close()

    assert payload.invocation_id == "task-123"
    assert payload.container_digest == digest
    assert requests == [
        ("docling", "task-123", "runtime-reporter-fixture-key"),
        ("docling", "task-123", "runtime-reporter-fixture-key"),
    ]


def test_authenticated_clients_reject_external_cleartext_endpoints() -> None:
    with pytest.raises(ValueError, match="external endpoint must use HTTPS"):
        HttpRemoteRuntimeAttestationReporter(
            "http://reporter.example.test",
            expected_reporter_id="fixture",
            api_key="runtime-reporter-fixture-key",
        )
    with pytest.raises(ValueError, match="external endpoint must use HTTPS"):
        DoclingServeClient(
            "http://parser.example.test", api_key="docling-fixture-key-123"
        )


def _docling_document() -> dict[str, Any]:
    return {
        "schema_name": "DoclingDocument",
        "version": "1.0.0",
        "name": "paper",
        "body": {"self_ref": "#/body", "children": []},
        "furniture": {"self_ref": "#/furniture", "children": []},
        "groups": [],
        "texts": [],
        "tables": [],
        "pictures": [],
        "key_value_items": [],
        "pages": {},
    }


def test_parser_clients_require_non_default_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DOCLING_API_KEY", raising=False)
    monkeypatch.delenv("GROBID_API_KEY", raising=False)

    with pytest.raises(ValueError, match=r"Docling.*non-default"):
        DoclingServeClient()
    with pytest.raises(ValueError, match=r"GROBID.*non-default"):
        GrobidClient()
    with pytest.raises(ValueError, match=r"Docling.*non-default"):
        DoclingServeClient(api_key="short")
    with pytest.raises(ValueError, match=r"GROBID.*non-default"):
        GrobidClient(api_key="replace-with-a-different-random-local-secret")


@pytest.mark.parametrize("invalid_limit", [0, -1, True, 1.5])
def test_parser_clients_require_positive_integer_response_limits(
    invalid_limit: object,
) -> None:
    with pytest.raises(ValueError, match="max_response_bytes"):
        DoclingServeClient(max_response_bytes=invalid_limit)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="max_response_bytes"):
        GrobidClient(max_response_bytes=invalid_limit)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_docling_client_version_and_async_conversion_contract() -> None:
    submitted = asyncio.Event()

    async def version(request: web.Request) -> web.Response:
        assert request.headers["X-API-Key"] == "docling-test-key-123"
        return web.json_response({"docling": "2.113.0", "serve": "1.21.0"})

    async def submit(request: web.Request) -> web.Response:
        assert request.headers["X-API-Key"] == "docling-test-key-123"
        await request.read()
        submitted.set()
        return web.json_response({"task_id": "task-123"})

    async def poll(request: web.Request) -> web.Response:
        assert request.match_info["task_id"] == "task-123"
        return web.json_response({"task_status": "success"})

    async def result(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "status": "success",
                "document": {"json_content": _docling_document()},
                "errors": [],
            }
        )

    app = web.Application()
    app.router.add_get("/version", version)
    app.router.add_post("/v1/convert/file/async", submit)
    app.router.add_get("/v1/status/poll/{task_id}", poll)
    app.router.add_get("/v1/result/{task_id}", result)
    server = TestServer(app)
    await server.start_server()
    try:
        client = DoclingServeClient(
            str(server.make_url("/")).rstrip("/"),
            api_key="docling-test-key-123",
            poll_interval_seconds=0.001,
        )
        versions = await client.version()
        conversion = await client.convert(
            b"synthetic",
            filename="paper.html",
            media_type="text/html",
        )
    finally:
        await server.close()

    assert submitted.is_set()
    assert versions == {"docling": "2.113.0", "serve": "1.21.0"}
    assert conversion.document["schema_name"] == "DoclingDocument"
    assert conversion.remote_task_id == "task-123"


@pytest.mark.asyncio
async def test_docling_rejects_oversized_declared_poll_response() -> None:
    response_limit = 64

    async def submit(request: web.Request) -> web.Response:
        await request.read()
        return web.json_response({"task_id": "task-oversized-poll"})

    async def poll(request: web.Request) -> web.Response:
        assert request.match_info["task_id"] == "task-oversized-poll"
        return web.Response(
            body=b"x" * (response_limit + 1),
            content_type="application/json",
        )

    app = web.Application()
    app.router.add_post("/v1/convert/file/async", submit)
    app.router.add_get("/v1/status/poll/{task_id}", poll)
    server = TestServer(app)
    await server.start_server()
    try:
        client = DoclingServeClient(
            str(server.make_url("/")).rstrip("/"),
            max_response_bytes=response_limit,
            poll_interval_seconds=0.001,
        )
        with pytest.raises(ParserServiceError) as error:
            await client.convert(
                b"synthetic",
                filename="paper.html",
                media_type="text/html",
            )
    finally:
        await server.close()

    assert error.value.code == "docling_response_too_large"
    assert "declares 65 bytes" in str(error.value)


@pytest.mark.asyncio
async def test_docling_rejects_oversized_chunked_result_response() -> None:
    response_limit = 96

    async def submit(request: web.Request) -> web.Response:
        await request.read()
        return web.json_response({"task_id": "task-oversized-result"})

    async def poll(request: web.Request) -> web.Response:
        assert request.match_info["task_id"] == "task-oversized-result"
        return web.json_response({"task_status": "success"})

    async def result(request: web.Request) -> web.StreamResponse:
        assert request.match_info["task_id"] == "task-oversized-result"
        response = web.StreamResponse(headers={"Content-Type": "application/json"})
        response.enable_chunked_encoding()
        await response.prepare(request)
        await response.write(
            b'{"status":"success","padding":"' + (b"x" * response_limit) + b'"}'
        )
        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_post("/v1/convert/file/async", submit)
    app.router.add_get("/v1/status/poll/{task_id}", poll)
    app.router.add_get("/v1/result/{task_id}", result)
    server = TestServer(app)
    await server.start_server()
    try:
        client = DoclingServeClient(
            str(server.make_url("/")).rstrip("/"),
            max_response_bytes=response_limit,
            poll_interval_seconds=0.001,
        )
        with pytest.raises(ParserServiceError) as error:
            await client.convert(
                b"synthetic",
                filename="paper.html",
                media_type="text/html",
            )
    finally:
        await server.close()

    assert error.value.code == "docling_response_too_large"
    assert "while streaming" in str(error.value)


@pytest.mark.asyncio
async def test_docling_client_preserves_trusted_remote_memory_measurement() -> None:
    async def submit(request: web.Request) -> web.Response:
        await request.read()
        return web.json_response({"task_id": "task-123"})

    async def poll(request: web.Request) -> web.Response:
        return web.json_response({"task_status": "success"})

    async def result(request: web.Request) -> web.Response:
        return web.json_response(
            {"status": "success", "document": {"json_content": _docling_document()}}
        )

    app = web.Application()
    app.router.add_post("/v1/convert/file/async", submit)
    app.router.add_get("/v1/status/poll/{task_id}", poll)
    app.router.add_get("/v1/result/{task_id}", result)
    server = TestServer(app)
    await server.start_server()
    try:
        client = DoclingServeClient(
            str(server.make_url("/")).rstrip("/"),
            memory_reporter=_RemoteMemoryReporter(),
            poll_interval_seconds=0.001,
        )
        conversion = await client.convert(
            b"synthetic", filename="paper.html", media_type="text/html"
        )
    finally:
        await server.close()

    assert conversion.memory_measurement is not None
    assert conversion.memory_measurement.status is MemoryMeasurementStatus.MEASURED
    assert conversion.memory_measurement.peak_memory_bytes == 2048
    assert isinstance(_RemoteMemoryReporter(), RemoteMemoryMeasurementReporter)


@pytest.mark.asyncio
async def test_docling_rejects_memory_measurement_for_another_task() -> None:
    client = DoclingServeClient(memory_reporter=_MismatchedMemoryReporter())
    result = DoclingConversionResult(
        document=_docling_document(),
        raw_response={},
        status="success",
        remote_task_id="task-123",
    )

    measured = await client._with_measurement(result)

    assert measured.memory_measurement is not None
    assert measured.memory_measurement.status is MemoryMeasurementStatus.FAILED
    assert (
        measured.memory_measurement.failure_code == "docling_memory_measurement_unbound"
    )


@pytest.mark.asyncio
async def test_docling_async_task_timeout_is_explicit_and_retryable() -> None:
    async def submit(request: web.Request) -> web.Response:
        await request.read()
        return web.json_response({"task_id": "task-never-finishes"})

    async def poll(request: web.Request) -> web.Response:
        assert request.match_info["task_id"] == "task-never-finishes"
        return web.json_response({"task_status": "started"})

    app = web.Application()
    app.router.add_post("/v1/convert/file/async", submit)
    app.router.add_get("/v1/status/poll/{task_id}", poll)
    server = TestServer(app)
    await server.start_server()
    try:
        client = DoclingServeClient(
            str(server.make_url("/")).rstrip("/"),
            task_timeout_seconds=0.01,
            poll_interval_seconds=0.001,
        )
        with pytest.raises(ParserServiceError) as error:
            await client.convert(
                b"synthetic",
                filename="paper.html",
                media_type="text/html",
            )
    finally:
        await server.close()

    assert error.value.code == "docling_task_timeout"
    assert error.value.retryable is True


@pytest.mark.asyncio
async def test_grobid_client_observes_version_and_preserves_tei() -> None:
    measurement_headers: list[str] = []
    reporter = _GrobidMemoryReporter()
    runtime_reporter = _GrobidRuntimeReporter()

    async def version(request: web.Request) -> web.Response:
        assert request.headers["X-API-Key"] == "grobid-test-key-1234"
        return web.Response(text="0.9.0")

    async def process(request: web.Request) -> web.Response:
        assert request.headers["X-API-Key"] == "grobid-test-key-1234"
        measurement_headers.append(request.headers["X-DeepCritical-Invocation-ID"])
        await request.read()
        return web.Response(
            body=b'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text/></TEI>',
            content_type="application/xml",
        )

    app = web.Application()
    app.router.add_get("/api/version", version)
    app.router.add_post("/api/processFulltextDocument", process)
    server = TestServer(app)
    await server.start_server()
    try:
        client = GrobidClient(
            str(server.make_url("/")).rstrip("/"),
            api_key="grobid-test-key-1234",
            memory_reporter=reporter,
            runtime_reporter=runtime_reporter,
        )
        observed = await client.version()
        parsed = await client.process_fulltext(b"%PDF-1.7", filename="paper.pdf")
    finally:
        await server.close()

    assert observed == "0.9.0"
    assert parsed.tei_xml.startswith(b"<TEI")
    assert parsed.memory_measurement is not None
    assert measurement_headers == [reporter.remote_task_id]
    assert measurement_headers == [runtime_reporter.remote_task_id]
    assert parsed.memory_measurement.measurement_id == reporter.remote_task_id
    assert parsed.runtime_attestation is not None
    assert parsed.runtime_attestation.invocation_id == runtime_reporter.remote_task_id


@pytest.mark.asyncio
@pytest.mark.parametrize("chunked", [False, True], ids=["declared", "chunked"])
async def test_grobid_rejects_oversized_tei_response(chunked: bool) -> None:
    response_limit = 64
    tei = (
        b'<TEI xmlns="http://www.tei-c.org/ns/1.0"><text>'
        + (b"x" * response_limit)
        + b"</text></TEI>"
    )

    async def process(request: web.Request) -> web.StreamResponse:
        await request.read()
        if not chunked:
            return web.Response(body=tei, content_type="application/xml")
        response = web.StreamResponse(headers={"Content-Type": "application/xml"})
        response.enable_chunked_encoding()
        await response.prepare(request)
        await response.write(tei)
        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_post("/api/processFulltextDocument", process)
    server = TestServer(app)
    await server.start_server()
    try:
        client = GrobidClient(
            str(server.make_url("/")).rstrip("/"),
            max_response_bytes=response_limit,
        )
        with pytest.raises(ParserServiceError) as error:
            await client.process_fulltext(b"%PDF-1.7", filename="paper.pdf")
    finally:
        await server.close()

    assert error.value.code == "grobid_response_too_large"
    expected_message = "while streaming" if chunked else "declares"
    assert expected_message in str(error.value)


@pytest.mark.asyncio
async def test_grobid_rejects_memory_measurement_for_another_request() -> None:
    client = GrobidClient(memory_reporter=_MismatchedMemoryReporter())

    measurement = await client._resolve_memory_measurement("request-123")

    assert measurement is not None
    assert measurement.status is MemoryMeasurementStatus.FAILED
    assert measurement.failure_code == "grobid_memory_measurement_unbound"


def test_docling_invalid_result_is_never_a_success() -> None:
    with pytest.raises(ParserServiceError, match="status"):
        DoclingServeClient._normalize_result({"status": "failure"})


@pytest.mark.asyncio
async def test_container_ocr_version_probes_are_network_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"17.4.1\n", b""

    async def fake_subprocess(*command: str, **kwargs: Any) -> FakeProcess:
        commands.append(command)
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner("jbarlow83/ocrmypdf:v17.4.1")

    assert await runner.version() == "17.4.1"
    assert await runner.tesseract_version() == "17.4.1"
    assert all("--network" in command and "none" in command for command in commands)
    assert all("--read-only" in command for command in commands)
    assert all("--pids-limit" in command and "256" in command for command in commands)
    assert all(
        "--tmpfs" in command and "/tmp:size=2g,mode=1777" in command
        for command in commands
    )
    assert any(
        "--entrypoint" in command and "tesseract" in command for command in commands
    )


@pytest.mark.asyncio
async def test_ocr_version_probe_timeout_kills_and_reaps_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = asyncio.Event()

    class HangingProcess:
        returncode = 0
        killed = False

        async def communicate(self) -> tuple[bytes, bytes]:
            if not self.killed:
                await release.wait()
            return b"", b""

        def kill(self) -> None:
            self.killed = True
            release.set()

    process = HangingProcess()

    async def fake_subprocess(*command: str, **kwargs: Any) -> HangingProcess:
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner(
        "jbarlow83/ocrmypdf:v17.4.1", probe_timeout_seconds=0.001
    )

    with pytest.raises(ParserServiceError) as error:
        await runner.version()

    assert error.value.code == "ocrmypdf_container_version_timeout"
    assert error.value.retryable is True
    assert process.killed is True


@pytest.mark.asyncio
async def test_container_ocr_conversion_uses_hardened_runtime_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"ok", b""

        def kill(self) -> None:
            raise AssertionError("successful fixture must not be killed")

    async def fake_subprocess(*command: str, **kwargs: Any) -> FakeProcess:
        commands.append(command)
        output_mount = next(
            value
            for value in command
            if value.startswith("type=bind,source=") and "target=/output" in value
        )
        output_source = output_mount.split(",target=/output", maxsplit=1)[
            0
        ].removeprefix("type=bind,source=")
        output_dir = Path(output_source)
        (output_dir / "searchable.pdf").write_bytes(b"%PDF-searchable")
        (output_dir / "searchable.txt").write_text("recognized", encoding="utf-8")
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner("jbarlow83/ocrmypdf:v17.4.1")

    result = await runner.convert(b"%PDF-original")

    command = commands[0]
    assert result.pdf_bytes == b"%PDF-searchable"
    assert "--read-only" in command
    assert command[command.index("--pids-limit") + 1] == "256"
    assert command[command.index("--tmpfs") + 1] == "/tmp:size=2g,mode=1777"
    assert command[command.index("--network") + 1] == "none"


@pytest.mark.asyncio
async def test_container_ocr_digest_invocation_produces_bound_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []
    digest = "sha256:" + ("f" * 64)

    class FakeProcess:
        returncode = 0

        def __init__(self, stdout: bytes) -> None:
            self.stdout = stdout

        async def communicate(self) -> tuple[bytes, bytes]:
            return self.stdout, b""

        def kill(self) -> None:
            raise AssertionError("successful fixture must not be killed")

    async def fake_subprocess(*command: str, **kwargs: Any) -> FakeProcess:
        commands.append(command)
        output_mounts = [
            value
            for value in command
            if value.startswith("type=bind,source=") and "target=/output" in value
        ]
        if not output_mounts:
            return FakeProcess(
                b"tesseract 5.4.0\n" if "tesseract" in command else b"17.4.1\n"
            )
        output_source = (
            output_mounts[0]
            .split(",target=/output", maxsplit=1)[0]
            .removeprefix("type=bind,source=")
        )
        (Path(output_source) / "searchable.pdf").write_bytes(b"%PDF-searchable")
        return FakeProcess(b"ok")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner(
        "jbarlow83/ocrmypdf:v17.4.1",
        expected_digest=digest,
        require_digest_addressed=True,
    )

    result = await runner.convert(b"%PDF-original")

    assert result.runtime_attestation is not None
    assert isinstance(result.runtime_attestation, RuntimeAttestation)
    assert result.runtime_attestation.parser_version == "17.4.1"
    assert result.runtime_attestation.container_digest == digest
    assert result.runtime_attestation.source is (
        RuntimeAttestationSource.DIGEST_ADDRESSED_OCI_INVOCATION
    )
    assert all("--pull" in command and "never" in command for command in commands)
    conversion = commands[-1]
    assert runner.image in conversion
    assert "--name" in conversion
    assert "--label" in conversion


def test_container_ocr_required_digest_rejects_missing_or_conflicting_identity() -> (
    None
):
    digest = "sha256:" + ("1" * 64)
    with pytest.raises(ValueError, match="requires a digest-addressed image"):
        ContainerOCRmyPDFRunner(
            "jbarlow83/ocrmypdf:v17.4.1",
            require_digest_addressed=True,
        )
    with pytest.raises(ValueError, match="differs from the configured"):
        ContainerOCRmyPDFRunner(
            f"jbarlow83/ocrmypdf:v17.4.1@{digest}",
            expected_digest="sha256:" + ("2" * 64),
            require_digest_addressed=True,
        )


@pytest.mark.asyncio
async def test_container_ocr_uses_invocation_cgroup_parent_and_preserves_measurement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"ok", b""

        def kill(self) -> None:
            raise AssertionError("successful fixture must not be killed")

    async def fake_subprocess(*command: str, **kwargs: Any) -> FakeProcess:
        commands.append(command)
        output_mount = next(
            value
            for value in command
            if value.startswith("type=bind,source=") and "target=/output" in value
        )
        output_source = output_mount.split(",target=/output", maxsplit=1)[
            0
        ].removeprefix("type=bind,source=")
        (Path(output_source) / "searchable.pdf").write_bytes(b"%PDF-searchable")
        return FakeProcess()

    meter = _MeasuredMeter()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = ContainerOCRmyPDFRunner(
        "jbarlow83/ocrmypdf:v17.4.1",
        memory_meter=meter,
    )

    result = await runner.convert(b"%PDF-original")

    command = commands[0]
    assert command[command.index("--cgroup-parent") + 1] == (
        "/deepcritical/ocr-fixture"
    )
    assert meter.lease is not None
    assert meter.lease.finished is True
    assert meter.lease.attached_pids == []
    assert result.memory_measurement is not None
    assert result.memory_measurement.baseline_comparable is True
    assert (
        result.memory_measurement.measurement_id == meter.lease.request.measurement_id
    )


@pytest.mark.asyncio
async def test_local_ocr_attaches_spawned_process_to_invocation_cgroup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        pid = 4321
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"ok", b""

        def kill(self) -> None:
            raise AssertionError("successful fixture must not be killed")

    async def fake_subprocess(*command: str, **kwargs: Any) -> FakeProcess:
        Path(command[-1]).write_bytes(b"%PDF-searchable")
        return FakeProcess()

    meter = _MeasuredMeter()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    runner = OCRmyPDFRunner(memory_meter=meter)

    result = await runner.convert(b"%PDF-original")

    assert meter.lease is not None
    assert meter.lease.attached_pids == []
    assert meter.lease.wrapped_commands[0][0] == "cgroup-bootstrap"
    assert result.memory_measurement is not None
    assert result.memory_measurement.boundary == "ocrmypdf-local-process"


@pytest.mark.parametrize(
    "image",
    ["jbarlow83/ocrmypdf", "jbarlow83/ocrmypdf:latest"],
)
def test_container_ocr_rejects_unpinned_image_tags(image: str) -> None:
    with pytest.raises(ValueError, match="explicit non-latest"):
        ContainerOCRmyPDFRunner(image)
