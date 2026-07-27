from __future__ import annotations

from pathlib import Path

import yaml


def test_docling_results_support_checkpoint_crash_recovery() -> None:
    compose_path = (
        Path(__file__).resolve().parents[2]
        / "docker"
        / "document-processing"
        / "compose.yaml"
    )
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    assert isinstance(compose, dict)
    shared_environment = compose["x-docling-environment"]
    assert shared_environment["DOCLING_SERVE_SINGLE_USE_RESULTS"] == "false"
    assert shared_environment["DOCLING_SERVE_ENG_RQ_RESULTS_TTL"] == "14400"
    assert "DOCLING_SERVE_RESULT_REMOVAL_DELAY" not in shared_environment

    for service_name in ("docling-api", "docling-worker"):
        environment = compose["services"][service_name]["environment"]
        assert environment["DOCLING_SERVE_SINGLE_USE_RESULTS"] == "false"
        assert environment["DOCLING_SERVE_ENG_RQ_RESULTS_TTL"] == "14400"


def test_parser_services_require_secrets_and_grobid_is_only_proxied() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load(
        (root / "docker" / "document-processing" / "compose.yaml").read_text(
            encoding="utf-8"
        )
    )
    services = compose["services"]
    serialized = str(compose)

    assert ":?Set a non-default DOCLING_API_KEY" in serialized
    assert ":?Set a non-default GROBID_API_KEY" in serialized
    assert ":?Set a non-default REDIS_PASSWORD" in serialized
    assert "ports" not in services["grobid"]
    assert services["grobid-proxy"]["ports"] == ["127.0.0.1:${GROBID_PORT:-8070}:8070"]
    caddyfile = (
        root / "docker" / "document-processing" / "Caddyfile.grobid"
    ).read_text(encoding="utf-8")
    assert "header X-API-Key" in caddyfile
    assert "reverse_proxy grobid:8070" in caddyfile


def test_deployment_requires_immutable_images_and_image_baked_models() -> None:
    root = Path(__file__).resolve().parents[2]
    compose_path = root / "docker" / "document-processing" / "compose.yaml"
    compose_text = compose_path.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)

    assert "DOCLING_IMAGE_DIGEST:?" in compose_text
    assert "GROBID_BASE_DIGEST:?" in compose_text
    assert "GROBID_IMAGE_DIGEST:?" in compose_text
    assert "OCRMYPDF_IMAGE_DIGEST:?" in compose_text
    assert "REDIS_IMAGE_DIGEST:?" in compose_text
    assert "CADDY_IMAGE_DIGEST:?" in compose_text
    assert compose["x-docling-container"]["pull_policy"] == "never"
    assert compose["services"]["redis"]["pull_policy"] == "never"
    assert compose["services"]["grobid"]["pull_policy"] == "never"
    assert compose["services"]["grobid-proxy"]["pull_policy"] == "never"
    assert compose["services"]["ocrmypdf"]["pull_policy"] == "never"
    assert compose["x-docling-container"]["platform"] == (
        "${DOCUMENT_PROCESSING_PLATFORM:-linux/amd64}"
    )

    assert "volumes" not in compose["x-docling-container"]
    assert "docling-cache" not in compose.get("volumes", {})

    grobid = compose["services"]["grobid"]
    assert "build" not in grobid
    assert "@${GROBID_IMAGE_DIGEST:?" in grobid["image"]
    grobid_build = compose["services"]["grobid-build"]
    assert grobid_build["profiles"] == ["build"]
    assert grobid_build["build"]["args"]["GROBID_BASE_DIGEST"].startswith(
        "${GROBID_BASE_DIGEST:?"
    )

    dockerfile = (
        root / "docker" / "document-processing" / "Dockerfile.grobid"
    ).read_text(encoding="utf-8")
    assert "FROM grobid/grobid:0.9.0-full@${GROBID_BASE_DIGEST}" in dockerfile


def test_docling_worker_health_checks_worker_heartbeat() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load(
        (root / "docker" / "document-processing" / "compose.yaml").read_text(
            encoding="utf-8"
        )
    )
    healthcheck = " ".join(compose["services"]["docling-worker"]["healthcheck"]["test"])

    assert "Worker.all" in healthcheck
    assert "last_heartbeat" in healthcheck
    assert "socket.gethostname" in healthcheck
    assert "worker.hostname == hostname" in healthcheck


def test_docling_api_healthcheck_requires_explicit_readiness_true() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load(
        (root / "docker" / "document-processing" / "compose.yaml").read_text(
            encoding="utf-8"
        )
    )
    healthcheck = " ".join(compose["services"]["docling-api"]["healthcheck"]["test"])

    assert 'payload.get("ready") is True' in healthcheck
