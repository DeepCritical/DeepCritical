from __future__ import annotations

import tomllib
from pathlib import Path

import yaml


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_live_requirements_match_the_repository_lock() -> None:
    root = _repository_root()
    requirement_lines = (
        (root / "docker" / "document-processing" / "requirements-live.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    requirements = dict(line.split("==", maxsplit=1) for line in requirement_lines)
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked_versions = {
        package["name"]: package["version"] for package in lock["package"]
    }

    assert requirements
    assert requirements == {name: locked_versions[name] for name in requirements}


def test_redis_keeps_all_capabilities_dropped_without_a_setuid_transition() -> None:
    compose = yaml.safe_load(
        (
            _repository_root() / "docker" / "document-processing" / "compose.yaml"
        ).read_text(encoding="utf-8")
    )
    redis = compose["services"]["redis"]

    assert redis["user"] == "redis"
    assert redis["cap_drop"] == ["ALL"]
    assert "cap_add" not in redis


def test_grobid_actions_override_uses_only_the_locally_built_image() -> None:
    override = yaml.safe_load(
        (
            _repository_root()
            / "docker"
            / "document-processing"
            / "compose.github-actions.yaml"
        ).read_text(encoding="utf-8")
    )
    grobid = override["services"]["grobid"]

    assert grobid["image"] == (
        "${GROBID_IMAGE_REPOSITORY:-deepcritical/grobid}:0.9.0-full-p0-c2"
    )
    assert grobid["pull_policy"] == "never"


def test_grobid_proxy_grants_only_caddys_embedded_file_capability() -> None:
    compose = yaml.safe_load(
        (
            _repository_root() / "docker" / "document-processing" / "compose.yaml"
        ).read_text(encoding="utf-8")
    )
    proxy = compose["services"]["grobid-proxy"]

    assert proxy["cap_drop"] == ["ALL"]
    assert proxy["cap_add"] == ["NET_BIND_SERVICE"]
    assert proxy["security_opt"] == ["no-new-privileges:true"]


def test_grobid_build_requests_a_normalized_epoch() -> None:
    compose = yaml.safe_load(
        (
            _repository_root() / "docker" / "document-processing" / "compose.yaml"
        ).read_text(encoding="utf-8")
    )
    build_args = compose["services"]["grobid-build"]["build"]["args"]

    assert build_args["SOURCE_DATE_EPOCH"] == "${SOURCE_DATE_EPOCH:-0}"


def test_live_policy_versions_match_the_pinned_stack() -> None:
    config = yaml.safe_load(
        (
            _repository_root() / "configs" / "document_processing" / "default.yaml"
        ).read_text(encoding="utf-8")
    )
    services = config["services"]

    assert services["docling"]["container_image"] == (
        "quay.io/docling-project/docling-serve-cpu:v1.21.0"
    )
    assert services["docling"]["component_version"] == "2.96.1"
    assert services["docling"]["serve_version"] == "1.21.0"
    assert services["grobid"]["container_image"] == (
        "deepcritical/grobid:0.9.0-full-p0-c2"
    )
    assert services["grobid"]["component_version"] == "0.9.0"
    assert services["ocr"]["container_image"] == "jbarlow83/ocrmypdf:v17.4.1"
    assert services["ocr"]["component_version"] == "17.4.1"
