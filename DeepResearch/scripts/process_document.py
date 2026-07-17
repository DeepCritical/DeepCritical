"""Command-line entry point for the scientific document-processing pipeline."""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import os
import re
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlparse

from omegaconf import DictConfig, OmegaConf

from DeepResearch.src.document_processing import (
    ContainerOCRmyPDFRunner,
    ContentAddressedStore,
    DoclingServeClient,
    DocumentProcessingConfig,
    DocumentProcessor,
    GrobidClient,
    HttpRemoteMemoryMeasurementReporter,
    HttpRemoteRuntimeAttestationReporter,
    LinuxCgroupV2InvocationMeter,
    OCRmyPDFRunner,
    SourcePreflightError,
)

_INSECURE_LOCAL_SECRETS = frozenset(
    {"deepcritical-local-only", "replace-with-a-random-local-secret"}
)
_SAFE_SERVICE_SECRET = re.compile(r"^[A-Za-z0-9._~+/=-]{16,256}$")


def _required_service_api_key(service: Any, *, service_name: str) -> str:
    env_name = str(service.get("api_key_env", "")).strip()
    if not env_name:
        raise ValueError(f"services.{service_name}.api_key_env must be configured")
    value = os.getenv(env_name, "").strip()
    if (
        not _SAFE_SERVICE_SECRET.fullmatch(value)
        or value in _INSECURE_LOCAL_SECRETS
        or value.lower().startswith("replace-with-")
    ):
        raise ValueError(
            f"{env_name} must contain a non-default, URL-safe secret of 16-256 characters"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse one scientific document with Docling and GROBID."
    )
    parser.add_argument("source", type=Path, nargs="?", help="Local source artifact")
    parser.add_argument(
        "--artifact-id",
        help="Resume an artifact already stored in the content-addressed store",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/document_processing/default.yaml"),
    )
    parser.add_argument("--store", type=Path, help="Override the CAS root")
    parser.add_argument("--docling-url", help="Override Docling Serve base URL")
    parser.add_argument("--grobid-url", help="Override GROBID base URL")
    parser.add_argument(
        "--ocr-command",
        "--ocr-executable",
        dest="ocr_command",
        help="Override 'docker' for container mode or 'ocrmypdf' for local mode",
    )
    parser.add_argument(
        "--check-services",
        action="store_true",
        help=(
            "Check parser and configured reporter readiness before processing; "
            "this is automatic when runtime identity or memory evidence is required"
        ),
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Run every parser stage again instead of reusing terminal outputs",
    )
    parser.add_argument(
        "--benchmark-repetition-group",
        help=(
            "Group independent forced benchmark attempts for deterministic pairing; "
            "requires --force-reprocess and --workflow-attempt-id"
        ),
    )
    parser.add_argument(
        "--workflow-attempt-id",
        help=(
            "Stable identity for one forced attempt. Reuse it after interruption to "
            "resume the persisted Docling task; use a new value for an independent "
            "attempt. Requires --force-reprocess."
        ),
    )
    return parser


async def run(args: argparse.Namespace) -> int:
    if (args.source is None) == (args.artifact_id is None):
        raise ValueError("provide exactly one of source or --artifact-id")
    if args.workflow_attempt_id and not args.force_reprocess:
        raise ValueError("--workflow-attempt-id requires --force-reprocess")
    if args.benchmark_repetition_group and not args.workflow_attempt_id:
        raise ValueError(
            "--benchmark-repetition-group requires --workflow-attempt-id so one "
            "interrupted attempt can resume without colliding with independent runs"
        )
    raw_config = OmegaConf.load(args.config)
    if not isinstance(raw_config, DictConfig):
        raise ValueError("document-processing config must be a mapping")

    services = raw_config.services
    ocr_config = services.ocr
    store_root = args.store or Path(str(raw_config.storage.root))
    docling_url = args.docling_url or str(services.docling.base_url)
    grobid_url = args.grobid_url or str(services.grobid.base_url)
    allow_external_endpoints = bool(
        raw_config.security.get("allow_external_parser_endpoints", False)
    )
    _validate_parser_endpoint(
        docling_url,
        service_name="Docling",
        allow_external=allow_external_endpoints,
    )
    if bool(services.grobid.enabled):
        _validate_parser_endpoint(
            grobid_url,
            service_name="GROBID",
            allow_external=allow_external_endpoints,
        )
    docling_api_key = _required_service_api_key(
        services.docling, service_name="docling"
    )
    grobid_api_key = _required_service_api_key(services.grobid, service_name="grobid")
    config = _processing_config(raw_config)
    docling_memory_reporter = _memory_reporter(
        services.docling,
        service_name="docling.memory_reporter",
        allow_external=allow_external_endpoints,
        required=config.memory_measurement_required,
    )
    grobid_memory_reporter = _memory_reporter(
        services.grobid,
        service_name="grobid.memory_reporter",
        allow_external=allow_external_endpoints,
        required=config.memory_measurement_required and config.grobid_enabled,
    )
    docling_runtime_reporter = _runtime_attestation_reporter(
        services.docling,
        service_name="docling.runtime_attestation_reporter",
        allow_external=allow_external_endpoints,
        required=config.require_runtime_identity,
    )
    grobid_runtime_reporter = _runtime_attestation_reporter(
        services.grobid,
        service_name="grobid.runtime_attestation_reporter",
        allow_external=allow_external_endpoints,
        required=config.require_runtime_identity and config.grobid_enabled,
    )
    ocr_memory_meter = _ocr_memory_meter(
        ocr_config,
        required=config.memory_measurement_required and config.ocr_enabled,
    )
    docling = DoclingServeClient(
        docling_url,
        api_key=docling_api_key,
        connect_timeout_seconds=float(services.docling.connect_timeout_seconds),
        request_timeout_seconds=float(services.docling.request_timeout_seconds),
        task_timeout_seconds=float(services.docling.job_timeout_seconds),
        poll_interval_seconds=float(services.docling.poll_interval_seconds),
        max_response_bytes=config.docling_max_response_bytes,
        use_async_api=bool(services.docling.get("async", True)),
        memory_reporter=docling_memory_reporter,
        runtime_reporter=docling_runtime_reporter,
    )
    grobid = GrobidClient(
        grobid_url,
        connect_timeout_seconds=float(services.grobid.connect_timeout_seconds),
        timeout_seconds=float(services.grobid.request_timeout_seconds),
        max_response_bytes=config.grobid_max_response_bytes,
        consolidate_header=int(bool(services.grobid.consolidate_header)),
        consolidate_citations=int(bool(services.grobid.consolidate_citations)),
        api_key=grobid_api_key,
        memory_reporter=grobid_memory_reporter,
        runtime_reporter=grobid_runtime_reporter,
    )
    if config.ocr_mode == "container_cli":
        ocrmypdf = ContainerOCRmyPDFRunner(
            config.ocr_container_image,
            runtime_executable=args.ocr_command or "docker",
            timeout_seconds=float(ocr_config.timeout_seconds),
            languages=config.ocr_languages,
            jobs=int(ocr_config.jobs),
            rotate_pages=bool(ocr_config.rotate_pages),
            deskew=bool(ocr_config.deskew),
            optimize=int(ocr_config.optimize),
            memory_meter=ocr_memory_meter,
            expected_digest=config.ocr_container_digest,
            require_digest_addressed=config.require_runtime_identity,
        )
    else:
        ocrmypdf = OCRmyPDFRunner(
            args.ocr_command or "ocrmypdf",
            timeout_seconds=float(ocr_config.timeout_seconds),
            languages=config.ocr_languages,
            jobs=int(ocr_config.jobs),
            rotate_pages=bool(ocr_config.rotate_pages),
            deskew=bool(ocr_config.deskew),
            optimize=int(ocr_config.optimize),
            memory_meter=ocr_memory_meter,
        )
    processor = DocumentProcessor(
        ContentAddressedStore(store_root),
        docling=docling,
        grobid=grobid,
        ocrmypdf=ocrmypdf,
        config=config,
    )

    if _service_precheck_required(args, config):
        await _check_parser_services(
            docling,
            grobid,
            grobid_enabled=config.grobid_enabled,
            memory_reporters=(docling_memory_reporter, grobid_memory_reporter),
            runtime_reporters=(docling_runtime_reporter, grobid_runtime_reporter),
        )

    try:
        result = (
            await processor.process_path(
                args.source,
                force_reprocess=args.force_reprocess,
                repetition_group_id=args.benchmark_repetition_group,
                workflow_attempt_id=args.workflow_attempt_id,
            )
            if args.source is not None
            else await processor.process_artifact(
                args.artifact_id,
                force_reprocess=args.force_reprocess,
                repetition_group_id=args.benchmark_repetition_group,
                workflow_attempt_id=args.workflow_attempt_id,
            )
        )
    except SourcePreflightError as exc:
        print(json.dumps(_intake_quarantine_payload(exc), indent=2, sort_keys=True))
        return 1
    print(json.dumps(_result_payload(result), indent=2, sort_keys=True))
    return 0 if result.status.value in {"complete", "partial"} else 1


def _service_precheck_required(
    args: argparse.Namespace,
    config: DocumentProcessingConfig,
) -> bool:
    """Return whether readiness is mandatory before any parser work starts."""

    return bool(
        args.check_services
        or config.require_runtime_identity
        or config.memory_measurement_required
    )


def _intake_quarantine_payload(error: SourcePreflightError) -> dict[str, Any]:
    record = error.quarantine_record
    return {
        "artifact_id": None,
        "intake_quarantine_id": record.intake_id if record is not None else None,
        "status": "quarantined",
        "source_path": record.source_path if record is not None else None,
        "preflight_result_sha256": (
            record.preflight_result_sha256 if record is not None else None
        ),
        "diagnostics": [
            {
                "code": diagnostic.code.value,
                "severity": diagnostic.severity.value,
                "message": diagnostic.message,
                "details": diagnostic.details,
            }
            for diagnostic in error.result.diagnostics
        ],
    }


async def _check_parser_services(
    docling: Any,
    grobid: Any,
    *,
    grobid_enabled: bool,
    memory_reporters: tuple[Any | None, Any | None] = (None, None),
    runtime_reporters: tuple[Any | None, Any | None] = (None, None),
) -> dict[str, object]:
    health: dict[str, object] = {"docling": await docling.health()}
    if not health["docling"]:
        raise RuntimeError("Docling is not healthy")
    if grobid_enabled:
        health["grobid"] = await grobid.health()
        if not health["grobid"]:
            raise RuntimeError("GROBID is not healthy")
    for reporter_kind, reporters in (
        ("memory", memory_reporters),
        ("runtime attestation", runtime_reporters),
    ):
        for parser_name, reporter in zip(("docling", "grobid"), reporters, strict=True):
            if reporter is None or (parser_name == "grobid" and not grobid_enabled):
                continue
            healthy = await reporter.health()
            health[f"{parser_name}_{reporter_kind.replace(' ', '_')}_reporter"] = (
                healthy
            )
            if not healthy:
                raise RuntimeError(
                    f"{parser_name} {reporter_kind} reporter is not healthy"
                )
    return health


def _result_payload(result: Any) -> dict[str, Any]:
    return {
        "artifact_id": result.artifact.artifact_id,
        "status": result.status.value,
        "route": list(result.route),
        "canonical_document_sha256": result.canonical_document_sha256,
        "grobid_tei_sha256": result.grobid_tei_sha256,
        "alignment_sha256": result.alignment_sha256,
        "content_integrity_sha256": result.content_integrity_sha256,
        "content_span_count": result.content_span_count,
        "derivative_artifact_ids": list(result.derivative_artifact_ids),
        "parser_runs": [
            {
                "run_id": run.run_id,
                "parser": run.parser_name,
                "version": run.parser_version,
                "status": run.status.value,
                "output_hashes": run.output_hashes,
            }
            for run in result.parser_runs
        ],
        "diagnostics": [
            {
                "code": diagnostic.code,
                "severity": diagnostic.severity.value,
                "stage": diagnostic.stage,
                "message": diagnostic.message,
            }
            for diagnostic in result.diagnostics
        ],
    }


def _processing_config(raw_config: DictConfig) -> DocumentProcessingConfig:
    _validate_static_policy(raw_config)
    services = raw_config.services
    quality = raw_config.quality
    routing = raw_config.routing
    security = raw_config.security
    ocr_config = services.ocr
    ocr_mode_value = str(ocr_config.mode)
    if ocr_mode_value not in {"container_cli", "local_cli"}:
        raise ValueError(
            "services.ocr.mode must be either 'container_cli' or 'local_cli'"
        )
    ocr_mode = cast("Literal['container_cli', 'local_cli']", ocr_mode_value)
    config = DocumentProcessingConfig(
        docling_version=str(services.docling.parser_version),
        docling_serve_version=str(services.docling.serve_version),
        docling_container_image=str(services.docling.container_image),
        docling_container_digest=_optional_text(services.docling.container_digest),
        docling_model_versions=_string_mapping(services.docling.model_versions),
        docling_model_hashes=_string_mapping(services.docling.model_hashes),
        docling_max_response_bytes=_positive_byte_limit(
            services.docling.max_response_bytes,
            path="services.docling.max_response_bytes",
        ),
        grobid_version=str(services.grobid.parser_version),
        grobid_enabled=bool(services.grobid.enabled),
        grobid_container_image=str(services.grobid.container_image),
        grobid_container_digest=_optional_text(services.grobid.container_digest),
        grobid_model_versions=_string_mapping(services.grobid.model_versions),
        grobid_model_hashes=_string_mapping(services.grobid.model_hashes),
        grobid_max_response_bytes=_positive_byte_limit(
            services.grobid.max_response_bytes,
            path="services.grobid.max_response_bytes",
        ),
        ocrmypdf_version=str(ocr_config.parser_version),
        ocr_enabled=bool(ocr_config.enabled),
        ocr_mode=ocr_mode,
        ocr_container_image=str(ocr_config.container_image),
        ocr_container_digest=_optional_text(ocr_config.container_digest),
        ocr_languages=tuple(str(value) for value in ocr_config.languages),
        detect_image_only_pdfs=bool(routing.pdf.detect_image_only),
        minimum_text_characters_per_page=int(routing.pdf.min_text_characters_per_page),
        image_only_page_ratio=float(routing.pdf.image_only_page_ratio),
        minimum_pdf_locator_coverage=float(quality.minimum_pdf_locator_coverage),
        managed_parsers_enabled=bool(raw_config.managed_providers.enabled),
        require_runtime_identity=bool(quality.require_runtime_identity),
        memory_measurement_required=bool(
            quality.get("memory_measurement_required", False)
        ),
        preflight_enabled=bool(routing.preflight_enabled),
        max_source_bytes=int(routing.max_source_bytes),
        max_pdf_pages=int(routing.max_pdf_pages),
        allow_encrypted_pdfs=bool(security.allow_encrypted_pdfs),
        require_pdf_page_count=bool(security.require_pdf_page_count),
        quarantine_on_pdf_structure_uncertainty=bool(
            security.quarantine_on_pdf_structure_uncertainty
        ),
        quarantine_on_fallback_exhaustion=bool(
            routing.fallback.quarantine_on_exhaustion
        ),
        allow_source_symlinks=bool(security.allow_source_symlinks),
        reject_extension_only_detection=bool(routing.reject_extension_only_detection),
    )
    if config.require_runtime_identity:
        missing: list[str] = []
        if config.docling_container_digest is None:
            missing.append("services.docling.container_digest")
        if not config.docling_model_hashes:
            missing.append("services.docling.model_hashes")
        if config.grobid_enabled:
            if config.grobid_container_digest is None:
                missing.append("services.grobid.container_digest")
            if not config.grobid_model_hashes:
                missing.append("services.grobid.model_hashes")
        if config.ocr_enabled:
            if config.ocr_mode != "container_cli":
                missing.append("services.ocr.mode=container_cli")
            if config.ocr_container_digest is None:
                missing.append("services.ocr.container_digest")
        if missing:
            raise ValueError(
                "quality.require_runtime_identity requires configured identity "
                f"expectations: {', '.join(missing)}"
            )
    return config


def _validate_static_policy(raw_config: DictConfig) -> None:
    """Reject configuration values the P0 implementation cannot honor."""

    required_true = {
        "enabled": raw_config.enabled,
        "services.docling.enabled": raw_config.services.docling.enabled,
        "services.grobid.enabled": raw_config.services.grobid.enabled,
        "services.ocr.enabled": raw_config.services.ocr.enabled,
        "storage.content_addressed": raw_config.storage.content_addressed,
        "storage.immutable_originals": raw_config.storage.immutable_originals,
        "storage.atomic_writes": raw_config.storage.atomic_writes,
        "storage.preserve_native_jats": raw_config.storage.preserve_native_jats,
        "storage.preserve_native_bioc": raw_config.storage.preserve_native_bioc,
        "storage.preserve_docling_document": (
            raw_config.storage.preserve_docling_document
        ),
        "storage.preserve_grobid_tei": raw_config.storage.preserve_grobid_tei,
        "storage.preserve_ocr_derivatives": (
            raw_config.storage.preserve_ocr_derivatives
        ),
        "storage.preserve_parser_logs": raw_config.storage.preserve_parser_logs,
        "storage.supplements_are_separate_artifacts": (
            raw_config.storage.supplements_are_separate_artifacts
        ),
        "routing.preflight_enabled": raw_config.routing.preflight_enabled,
        "routing.sniff_media_type": raw_config.routing.sniff_media_type,
        "routing.prefer_native_jats": raw_config.routing.prefer_native_jats,
        "routing.reject_extension_only_detection": (
            raw_config.routing.reject_extension_only_detection
        ),
        "routing.pdf.docling_ocr_original": (
            raw_config.routing.pdf.docling_ocr_original
        ),
        "routing.pdf.create_searchable_derivative": (
            raw_config.routing.pdf.create_searchable_derivative
        ),
        "routing.fallback.each_fallback_creates_parser_run": (
            raw_config.routing.fallback.each_fallback_creates_parser_run
        ),
        "routing.fallback.quarantine_on_exhaustion": (
            raw_config.routing.fallback.quarantine_on_exhaustion
        ),
        "quality.empty_success_is_failure": (
            raw_config.quality.empty_success_is_failure
        ),
        "quality.require_pdf_page_and_bounding_box": (
            raw_config.quality.require_pdf_page_and_bounding_box
        ),
        "quality.require_content_hashes": raw_config.quality.require_content_hashes,
        "quality.require_source_locators": raw_config.quality.require_source_locators,
        "quality.require_resolved_item_references": (
            raw_config.quality.require_resolved_item_references
        ),
        "quality.unaligned_citations_are_diagnostics": (
            raw_config.quality.unaligned_citations_are_diagnostics
        ),
        "quality.unaligned_tables_are_diagnostics": (
            raw_config.quality.unaligned_tables_are_diagnostics
        ),
        "quality.unaligned_figures_are_diagnostics": (
            raw_config.quality.unaligned_figures_are_diagnostics
        ),
        "services.docling.async": raw_config.services.docling.get("async", False),
        "services.grobid.include_raw_citations": (
            raw_config.services.grobid.include_raw_citations
        ),
        "services.grobid.include_pdf_coordinates": (
            raw_config.services.grobid.include_pdf_coordinates
        ),
        "services.ocr.skip_text_pages": raw_config.services.ocr.skip_text_pages,
        "security.require_mime_sniffing": raw_config.security.require_mime_sniffing,
    }
    for path, value in required_true.items():
        if not bool(value):
            raise ValueError(f"{path} must be true for the P0 processing contract")
    if bool(raw_config.routing.fallback.silent):
        raise ValueError("routing.fallback.silent must remain false")
    required_false = {
        "security.allow_remote_source_urls": raw_config.security.allow_remote_source_urls,
        "security.allow_docling_remote_services": (
            raw_config.security.allow_docling_remote_services
        ),
        "security.allow_external_plugins": raw_config.security.allow_external_plugins,
        "security.retain_document_text_in_service_logs": (
            raw_config.security.retain_document_text_in_service_logs
        ),
    }
    for path, value in required_false.items():
        if bool(value):
            raise ValueError(f"{path} must be false for the P0 processing contract")

    if float(raw_config.quality.minimum_pdf_locator_coverage) < 0.95:
        raise ValueError("quality.minimum_pdf_locator_coverage must be at least 0.95")

    required_values = {
        "storage.hash_algorithm": (raw_config.storage.hash_algorithm, "sha256"),
        "routing.pdf.grobid_scanned_input": (
            raw_config.routing.pdf.grobid_scanned_input,
            "ocrmypdf_derivative",
        ),
        "services.docling.submit_path": (
            raw_config.services.docling.submit_path,
            "/v1/convert/file/async",
        ),
        "services.docling.version_path": (
            raw_config.services.docling.version_path,
            "/version",
        ),
        "services.grobid.process_path": (
            raw_config.services.grobid.process_path,
            "/api/processFulltextDocument",
        ),
        "services.grobid.version_path": (
            raw_config.services.grobid.version_path,
            "/api/version",
        ),
        "services.ocr.engine": (raw_config.services.ocr.engine, "tesseract"),
        "services.ocr.output_type": (raw_config.services.ocr.output_type, "pdf"),
    }
    for path, (value, expected) in required_values.items():
        if str(value) != expected:
            raise ValueError(f"{path} must be {expected!r} for this P0 implementation")

    expected_routes = {
        "jats_xml": "docling_jats",
        "bioc_xml": "bioc_adapter",
        "bioc_json": "bioc_adapter",
        "pdf": "docling_pdf_with_grobid",
        "html": "docling",
        "docx": "docling",
        "xlsx": "docling",
        "pptx": "docling",
        "image": "docling_ocr",
    }
    configured_routes = OmegaConf.to_container(raw_config.routing.routes, resolve=True)
    if configured_routes != expected_routes:
        raise ValueError("routing.routes must match the implemented P0 routing graph")

    if bool(raw_config.routing.pdf.run_grobid) != bool(
        raw_config.services.grobid.enabled
    ):
        raise ValueError("routing.pdf.run_grobid must match services.grobid.enabled")
    allowed_statuses = tuple(
        str(value) for value in raw_config.quality.allowed_terminal_statuses
    )
    if allowed_statuses != ("complete", "partial", "quarantined", "failed"):
        raise ValueError(
            "quality.allowed_terminal_statuses must list complete, partial, quarantined, and failed"
        )
    if bool(raw_config.managed_providers.allow_implicit_fallback):
        raise ValueError("managed parser fallback cannot be implicit")
    if bool(raw_config.managed_providers.enabled):
        raise ValueError(
            "managed parser adapters are disabled until upload policy is approved"
        )


def _validate_parser_endpoint(
    value: str,
    *,
    service_name: str,
    allow_external: bool,
) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise ValueError(f"{service_name} endpoint must be an HTTP(S) URL")
    hostname = parsed.hostname.casefold()
    if hostname == "localhost":
        return
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and address.is_loopback:
        return
    if not allow_external:
        raise ValueError(
            f"{service_name} endpoint is not loopback; approve external parser uploads first"
        )
    if parsed.scheme != "https":
        raise ValueError(f"{service_name} external endpoint must use HTTPS")


def _memory_reporter(
    service: Any,
    *,
    service_name: str,
    allow_external: bool,
    required: bool,
) -> HttpRemoteMemoryMeasurementReporter | None:
    reporter = service.get("memory_reporter")
    enabled = reporter is not None and bool(reporter.get("enabled", False))
    if required and not enabled:
        raise ValueError(
            f"services.{service_name}.enabled must be true when "
            "quality.memory_measurement_required is true"
        )
    if not enabled:
        return None
    base_url = str(reporter.get("base_url", "")).strip()
    if not base_url:
        raise ValueError(f"services.{service_name}.base_url must be configured")
    _validate_parser_endpoint(
        base_url,
        service_name=f"{service_name} service",
        allow_external=allow_external,
    )
    return HttpRemoteMemoryMeasurementReporter(
        base_url,
        api_key=_required_service_api_key(reporter, service_name=service_name),
        connect_timeout_seconds=float(reporter.get("connect_timeout_seconds", 5)),
        request_timeout_seconds=float(reporter.get("request_timeout_seconds", 30)),
        resolution_timeout_seconds=float(
            reporter.get("resolution_timeout_seconds", 30)
        ),
        poll_interval_seconds=float(reporter.get("poll_interval_seconds", 0.25)),
    )


def _runtime_attestation_reporter(
    service: Any,
    *,
    service_name: str,
    allow_external: bool,
    required: bool,
) -> HttpRemoteRuntimeAttestationReporter | None:
    reporter = service.get("runtime_attestation_reporter")
    enabled = reporter is not None and bool(reporter.get("enabled", False))
    if required and not enabled:
        raise ValueError(
            f"services.{service_name}.enabled must be true when "
            "quality.require_runtime_identity is true"
        )
    if not enabled:
        return None
    base_url = str(reporter.get("base_url", "")).strip()
    expected_reporter_id = str(reporter.get("expected_reporter_id", "")).strip()
    if not base_url:
        raise ValueError(f"services.{service_name}.base_url must be configured")
    if not expected_reporter_id:
        raise ValueError(
            f"services.{service_name}.expected_reporter_id must be configured"
        )
    _validate_parser_endpoint(
        base_url,
        service_name=f"{service_name} service",
        allow_external=allow_external,
    )
    return HttpRemoteRuntimeAttestationReporter(
        base_url,
        expected_reporter_id=expected_reporter_id,
        api_key=_required_service_api_key(reporter, service_name=service_name),
        connect_timeout_seconds=float(reporter.get("connect_timeout_seconds", 5)),
        request_timeout_seconds=float(reporter.get("request_timeout_seconds", 30)),
        resolution_timeout_seconds=float(
            reporter.get("resolution_timeout_seconds", 30)
        ),
        poll_interval_seconds=float(reporter.get("poll_interval_seconds", 0.25)),
    )


def _ocr_memory_meter(
    ocr_service: Any,
    *,
    required: bool,
) -> LinuxCgroupV2InvocationMeter | None:
    meter = ocr_service.get("memory_meter")
    enabled = meter is not None and bool(meter.get("enabled", False))
    if required and not enabled:
        raise ValueError(
            "services.ocr.memory_meter.enabled must be true when "
            "quality.memory_measurement_required is true"
        )
    if not enabled:
        return None
    parent = str(meter.get("cgroup_v2_parent", "")).strip()
    environment_sha256 = str(meter.get("environment_sha256", "")).strip()
    if not parent:
        raise ValueError(
            "services.ocr.memory_meter.cgroup_v2_parent must be configured"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", environment_sha256):
        raise ValueError(
            "services.ocr.memory_meter.environment_sha256 must be a lowercase "
            "SHA-256 digest"
        )
    return LinuxCgroupV2InvocationMeter(
        parent,
        environment_sha256=environment_sha256,
    )


def _optional_text(value: Any) -> str | None:
    return None if value is None else str(value)


def _positive_byte_limit(value: Any, *, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{path} must be a positive integer byte count")
    return value


def _string_mapping(value: Any) -> dict[str, str]:
    resolved = OmegaConf.to_container(value, resolve=True)
    if not isinstance(resolved, dict):
        raise ValueError("runtime version/hash configuration must be a mapping")
    return {str(key): str(item) for key, item in resolved.items()}


def main() -> int:
    return asyncio.run(run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
