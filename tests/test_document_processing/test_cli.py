from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from omegaconf import DictConfig, OmegaConf

from DeepResearch.scripts.process_document import (
    _check_parser_services,
    _memory_reporter,
    _ocr_memory_meter,
    _pipeline_spec,
    _processing_config,
    _required_service_api_key,
    _result_payload,
    _runtime_attestation_reporter,
    _service_precheck_required,
    _validate_parser_endpoint,
    build_parser,
    run,
)
from DeepResearch.src.document_processing.clients import (
    HttpRemoteMemoryMeasurementReporter,
    HttpRemoteRuntimeAttestationReporter,
    ServiceHealth,
)
from DeepResearch.src.document_processing.models import (
    ComponentDescriptor,
    ProcessingRun,
    ProcessingRunStatus,
    configuration_sha256,
)
from DeepResearch.src.document_processing.pipeline import DocumentProcessingConfig
from DeepResearch.src.document_processing.storage import ContentAddressedStore


def _default_config() -> DictConfig:
    path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "document_processing"
        / "default.yaml"
    )
    config = OmegaConf.load(path)
    assert isinstance(config, DictConfig)
    config.quality.require_runtime_identity = False
    return config


def test_default_config_maps_to_runtime_contract() -> None:
    raw = _default_config()
    config = _processing_config(raw)
    pipeline = _pipeline_spec(raw)

    assert config.ocr_mode == "container_cli"
    assert config.ocr_languages == ("eng",)
    assert config.minimum_pdf_locator_coverage == 0.95
    assert config.managed_parsers_enabled is False
    assert config.preflight_enabled is True
    assert config.max_source_bytes == 104_857_600
    assert config.max_pdf_pages == 1_000
    assert config.docling_max_response_bytes == 268_435_456
    assert config.grobid_max_response_bytes == 134_217_728
    assert config.allow_encrypted_pdfs is False
    assert config.grobid_enabled is True
    assert config.detect_image_only_pdfs is True
    assert config.minimum_text_characters_per_page == 20
    assert config.image_only_page_ratio == 0.8
    assert config.reject_extension_only_detection is True
    assert config.quarantine_on_fallback_exhaustion is True
    assert config.require_runtime_identity is False
    assert pipeline.pipeline_id == "deepcritical-document-processing"
    assert tuple(stage.stage_id for stage in pipeline.stages) == (
        "preflight",
        "route",
        "prepare",
        "docling",
        "primary-grobid",
        "ocr",
        "fallback-grobid",
        "select-scholarly",
        "alignment",
        "integrity",
        "canonicalize",
        "fallback-policy",
        "finalize",
    )


def test_config_schema_version_is_required_and_recognized() -> None:
    raw = _default_config()
    del raw["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        _processing_config(raw)

    raw = _default_config()
    raw.schema_version = "deepcritical-document-processing-config-v1"
    with pytest.raises(ValueError, match="schema_version"):
        _processing_config(raw)


@pytest.mark.parametrize(
    ("service_name", "invalid_limit"),
    [
        ("docling", 0),
        ("docling", True),
        ("docling", 1.5),
        ("grobid", -1),
        ("grobid", False),
        ("grobid", "1024"),
    ],
)
def test_response_byte_limits_require_positive_integers(
    service_name: str,
    invalid_limit: object,
) -> None:
    raw = _default_config()
    raw.services[service_name].max_response_bytes = invalid_limit

    with pytest.raises(
        ValueError, match=rf"services\.{service_name}\.max_response_bytes"
    ):
        _processing_config(raw)


def test_default_resource_accounting_is_explicitly_optional() -> None:
    raw = _default_config()

    assert (
        _memory_reporter(
            raw.services.docling,
            service_name="docling.memory_reporter",
            allow_external=False,
            required=False,
        )
        is None
    )
    assert _ocr_memory_meter(raw.services.ocr, required=False) is None


def test_enforced_memory_accounting_rejects_missing_adapters() -> None:
    raw = _default_config()

    with pytest.raises(ValueError, match=r"docling\.memory_reporter\.enabled"):
        _memory_reporter(
            raw.services.docling,
            service_name="docling.memory_reporter",
            allow_external=False,
            required=True,
        )
    with pytest.raises(ValueError, match=r"ocr\.memory_meter\.enabled"):
        _ocr_memory_meter(raw.services.ocr, required=True)


def test_enabled_memory_reporter_is_authenticated_and_wired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _default_config()
    raw.services.docling.memory_reporter.enabled = True
    monkeypatch.setenv("RESOURCE_REPORTER_API_KEY", "reporter-fixture-key-123")

    reporter = _memory_reporter(
        raw.services.docling,
        service_name="docling.memory_reporter",
        allow_external=False,
        required=True,
    )

    assert isinstance(reporter, HttpRemoteMemoryMeasurementReporter)
    assert reporter.api_key == "reporter-fixture-key-123"


def test_enabled_runtime_reporter_is_authenticated_and_wired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _default_config()
    raw.services.docling.runtime_attestation_reporter.enabled = True
    monkeypatch.setenv("RUNTIME_ATTESTATION_API_KEY", "runtime-reporter-fixture-key")

    reporter = _runtime_attestation_reporter(
        raw.services.docling,
        service_name="docling.runtime_attestation_reporter",
        allow_external=False,
        required=True,
    )

    assert isinstance(reporter, HttpRemoteRuntimeAttestationReporter)
    assert reporter.expected_reporter_id == "deepcritical-local-supervisor"


def test_invalid_ocr_mode_fails_before_processing() -> None:
    raw = _default_config()
    raw.services.ocr.mode = "implicit_remote_fallback"

    with pytest.raises(ValueError, match=r"services\.ocr\.mode"):
        _processing_config(raw)


def test_parser_service_secrets_are_required_and_reject_known_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = {"api_key_env": "TEST_PARSER_API_KEY"}
    monkeypatch.delenv("TEST_PARSER_API_KEY", raising=False)
    with pytest.raises(ValueError, match=r"non-default.*secret"):
        _required_service_api_key(service, service_name="fixture")
    monkeypatch.setenv("TEST_PARSER_API_KEY", "deepcritical-local-only")
    with pytest.raises(ValueError, match=r"non-default.*secret"):
        _required_service_api_key(service, service_name="fixture")
    monkeypatch.setenv(
        "TEST_PARSER_API_KEY", "replace-with-a-different-random-local-secret"
    )
    with pytest.raises(ValueError, match=r"non-default.*secret"):
        _required_service_api_key(service, service_name="fixture")
    monkeypatch.setenv("TEST_PARSER_API_KEY", "a-secure-fixture-key-123")
    assert (
        _required_service_api_key(service, service_name="fixture")
        == "a-secure-fixture-key-123"
    )


def test_invalid_model_hash_and_unhonored_policy_fail_at_startup() -> None:
    bad_hash = _default_config()
    bad_hash.services.docling.model_versions = {"layout": "1"}
    bad_hash.services.docling.model_hashes = {"layout": "not-a-sha256"}

    with pytest.raises(ValueError, match="String should match pattern"):
        _processing_config(bad_hash)

    silent_fallback = _default_config()
    silent_fallback.routing.fallback.silent = True
    with pytest.raises(ValueError, match=r"fallback\.silent"):
        _processing_config(silent_fallback)

    non_atomic = _default_config()
    non_atomic.storage.atomic_writes = False
    with pytest.raises(ValueError, match=r"storage\.atomic_writes"):
        _processing_config(non_atomic)

    false_route = _default_config()
    false_route.routing.routes.pdf = "custom_pdf_parser"
    with pytest.raises(ValueError, match=r"routing\.routes"):
        _processing_config(false_route)

    no_grobid = _default_config()
    no_grobid.services.grobid.enabled = False
    no_grobid.routing.pdf.run_grobid = False
    with pytest.raises(ValueError, match=r"services\.grobid\.enabled"):
        _processing_config(no_grobid)

    weak_provenance = _default_config()
    assert _processing_config(weak_provenance).require_runtime_identity is False

    extension_only = _default_config()
    extension_only.routing.reject_extension_only_detection = False
    with pytest.raises(ValueError, match=r"reject_extension_only_detection"):
        _processing_config(extension_only)

    weakened_geometry = _default_config()
    weakened_geometry.quality.minimum_pdf_locator_coverage = 0.5
    with pytest.raises(ValueError, match=r"minimum_pdf_locator_coverage"):
        _processing_config(weakened_geometry)


def test_external_parser_endpoints_require_explicit_approval() -> None:
    _validate_parser_endpoint(
        "http://127.0.0.1:5001",
        service_name="Docling",
        allow_external=False,
    )
    with pytest.raises(ValueError, match="not loopback"):
        _validate_parser_endpoint(
            "https://parser.example.test",
            service_name="Docling",
            allow_external=False,
        )
    _validate_parser_endpoint(
        "https://parser.example.test",
        service_name="Docling",
        allow_external=True,
    )
    with pytest.raises(ValueError, match="must use HTTPS"):
        _validate_parser_endpoint(
            "http://parser.example.test",
            service_name="Docling",
            allow_external=True,
        )


def test_required_runtime_identity_rejects_placeholder_deployment_values() -> None:
    raw = _default_config()
    raw.quality.require_runtime_identity = True

    with pytest.raises(ValueError, match="configured identity expectations"):
        _processing_config(raw)


def test_cli_accepts_resume_without_local_source() -> None:
    args = build_parser().parse_args(["--artifact-id", "artifact-123"])

    assert args.source is None
    assert args.artifact_id == "artifact-123"


def test_service_precheck_is_automatic_for_required_provenance() -> None:
    args = build_parser().parse_args(["--artifact-id", "artifact-123"])

    assert _service_precheck_required(
        args,
        DocumentProcessingConfig(require_runtime_identity=True),
    )
    assert _service_precheck_required(
        args,
        DocumentProcessingConfig(
            require_runtime_identity=False,
            memory_measurement_required=True,
        ),
    )
    optional_config = DocumentProcessingConfig(require_runtime_identity=False)
    assert not _service_precheck_required(args, optional_config)

    explicit_args = build_parser().parse_args(
        ["--artifact-id", "artifact-123", "--check-services"]
    )
    assert _service_precheck_required(explicit_args, optional_config)


def test_check_services_help_explains_mandatory_automatic_precheck() -> None:
    help_text = " ".join(build_parser().format_help().split())

    assert "automatic when runtime identity or memory evidence is required" in help_text


def test_cli_exposes_explicit_benchmark_repeat_controls() -> None:
    args = build_parser().parse_args(
        [
            "--artifact-id",
            "artifact-123",
            "--force-reprocess",
            "--benchmark-repetition-group",
            "pmc-p0-v1",
            "--pipeline-attempt-id",
            "attempt-001",
        ]
    )

    assert args.force_reprocess is True
    assert args.benchmark_repetition_group == "pmc-p0-v1"
    assert args.pipeline_attempt_id == "attempt-001"


def test_result_payload_uses_component_generic_run_contract() -> None:
    configuration = {"fixture": True}
    now = datetime(2026, 7, 27, tzinfo=UTC)
    processing_run = ProcessingRun(
        run_id="run-1",
        artifact_id="artifact-1",
        stage_id="docling",
        component=ComponentDescriptor(
            component_id="docling",
            component_version="2.113.0",
            capability="document.parse",
        ),
        configuration=configuration,
        configuration_sha256=configuration_sha256(configuration),
        started_at=now,
        finished_at=now,
        status=ProcessingRunStatus.COMPLETE,
    )
    result = SimpleNamespace(
        artifact=SimpleNamespace(artifact_id="artifact-1"),
        status=ProcessingRunStatus.COMPLETE,
        route=("docling",),
        docling_document_sha256=None,
        grobid_tei_sha256=None,
        alignment_sha256=None,
        content_integrity_sha256=None,
        content_span_count=0,
        derivative_artifact_ids=(),
        processing_runs=(processing_run,),
        diagnostics=(),
    )

    payload = _result_payload(result)

    serialized_run = payload["processing_runs"][0]
    assert serialized_run["component_id"] == "docling"
    assert serialized_run["component_version"] == "2.113.0"
    assert "parser" not in serialized_run
    assert "output_hashes" not in serialized_run


class _HealthClient:
    def __init__(self, healthy: object) -> None:
        self.healthy = healthy
        self.calls = 0

    async def health(self) -> object:
        self.calls += 1
        return self.healthy


@pytest.mark.asyncio
async def test_service_precheck_rejects_unhealthy_docling_before_grobid() -> None:
    docling = _HealthClient(ServiceHealth(False, {"ready": False}, {}))
    grobid = _HealthClient(True)

    with pytest.raises(RuntimeError, match="Docling is not healthy"):
        await _check_parser_services(docling, grobid, grobid_enabled=True)

    assert docling.calls == 1
    assert grobid.calls == 0


@pytest.mark.asyncio
async def test_service_precheck_checks_configured_reporters() -> None:
    docling = _HealthClient(ServiceHealth(True, {"ready": True}, {}))
    grobid = _HealthClient(True)
    docling_memory = _HealthClient(True)
    docling_runtime = _HealthClient(True)

    health = await _check_parser_services(
        docling,
        grobid,
        grobid_enabled=True,
        memory_reporters=(docling_memory, None),
        runtime_reporters=(docling_runtime, None),
    )

    assert health["docling_memory_reporter"] is True
    assert health["docling_runtime_attestation_reporter"] is True
    assert docling_memory.calls == 1
    assert docling_runtime.calls == 1


@pytest.mark.asyncio
async def test_cli_serializes_pre_ingestion_path_quarantine(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DOCLING_API_KEY", "docling-test-secret-123")
    monkeypatch.setenv("GROBID_API_KEY", "grobid-test-secret-1234")
    raw = _default_config()
    raw.routing.max_source_bytes = 8
    config_path = tmp_path / "document-processing.yaml"
    OmegaConf.save(config=raw, f=config_path)
    source = tmp_path / "oversized.pdf"
    source.write_bytes(b"123456789")
    store_path = tmp_path / "store"
    args = build_parser().parse_args(
        [
            str(source),
            "--config",
            str(config_path),
            "--store",
            str(store_path),
        ]
    )

    exit_code = await run(args)
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "quarantined"
    assert payload["artifact_id"] is None
    assert payload["intake_quarantine_id"].startswith("intake-")
    assert payload["diagnostics"][0]["code"] == "SOURCE_TOO_LARGE"
    assert len(ContentAddressedStore(store_path).list_intake_quarantines()) == 1
