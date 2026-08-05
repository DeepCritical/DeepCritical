from __future__ import annotations

import tomllib
from pathlib import Path

import yaml


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _live_workflow_path() -> Path:
    return _repository_root() / ".github" / "workflows" / "document-processing-live.yml"


def _live_workflow() -> dict:
    return yaml.safe_load(_live_workflow_path().read_text(encoding="utf-8"))


def _step(jobs: dict, job_name: str, step_name: str) -> dict:
    selected = tuple(
        step for step in jobs[job_name]["steps"] if step.get("name") == step_name
    )
    assert len(selected) == 1
    return selected[0]


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


def test_live_workflow_runs_direct_and_compiled_contracts_in_isolated_jobs() -> None:
    workflow = _live_workflow()
    jobs = workflow["jobs"]

    assert set(jobs) == {"quality", "docling", "grobid", "ocr"}
    assert all(job["runs-on"] == "ubuntu-24.04" for job in jobs.values())
    assert "continue-on-error" not in _live_workflow_path().read_text(encoding="utf-8")

    selections = {
        "docling": (
            "test_live_docling_async_conversion_contract",
            "test_live_compiled_docling_pipeline",
        ),
        "grobid": (
            "test_live_grobid_tei_contract",
            "test_live_compiled_grobid_pipeline",
        ),
        "ocr": (
            "test_live_digest_addressed_ocr_derivative_contract",
            "test_live_compiled_ocr_pipeline",
        ),
    }
    for job_name, test_names in selections.items():
        run_step = next(
            step
            for step in jobs[job_name]["steps"]
            if step.get("name", "").startswith("Run the ")
        )
        command = run_step["run"]
        assert all(test_name in command for test_name in test_names)


def test_every_live_job_verifies_the_reported_checkout_revision() -> None:
    workflow = _live_workflow()
    assert (
        workflow["env"]["TESTED_REVISION"]
        == "${{ github.event.pull_request.head.sha || github.sha }}"
    )

    for job_name in ("quality", "docling", "grobid", "ocr"):
        checkout = _step(
            workflow["jobs"],
            job_name,
            "Check out the tested revision",
        )
        assert checkout["with"]["ref"] == "${{ env.TESTED_REVISION }}"
        verify = _step(
            workflow["jobs"],
            job_name,
            "Verify the checked-out revision",
        )
        assert 'actual_revision="$(git rev-parse HEAD)"' in verify["run"]
        assert 'test "$actual_revision" = "$TESTED_REVISION"' in verify["run"]


def test_hardening_pull_requests_run_every_isolated_live_job() -> None:
    workflow = yaml.load(
        _live_workflow_path().read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    pull_request = workflow["on"]["pull_request"]
    assert pull_request["branches"] == ["document-processing"]
    assert set(pull_request["paths"]) == {
        ".github/workflows/document-processing-live.yml",
        "DeepResearch/src/document_processing/**",
        "configs/document_processing/**",
        "docker/document-processing/**",
        "tests/test_document_processing/**",
        "pyproject.toml",
        "uv.lock",
    }

    for job_name in ("docling", "grobid", "ocr"):
        assert "github.event_name == 'pull_request'" in workflow["jobs"][job_name]["if"]


def test_quality_job_enforces_the_complete_repository_gate() -> None:
    jobs = _live_workflow()["jobs"]
    quality = jobs["quality"]
    assert quality["timeout-minutes"] == 30
    assert all(
        jobs[name]["needs"] == "quality" for name in ("docling", "grobid", "ocr")
    )

    document_suite = _step(
        jobs,
        "quality",
        "Run the complete document-processing suite",
    )["run"]
    assert "tests/test_document_processing" in document_suite

    repository_suite = _step(
        jobs,
        "quality",
        "Run the repository CI marker selection",
    )["run"]
    assert '-m "not optional and not containerized"' in repository_suite
    assert "--ignore" not in repository_suite
    assert "--deselect" not in repository_suite

    assert (
        "tests/test_bioinformatics_tools/"
        in _step(
            jobs,
            "quality",
            "Run the dedicated bioinformatics lane",
        )["run"]
    )
    assert (
        "DeepResearch/ tests/"
        in _step(
            jobs,
            "quality",
            "Run full Ruff lint",
        )["run"]
    )
    assert (
        "ruff format --check DeepResearch/ tests/"
        in _step(
            jobs,
            "quality",
            "Check full Ruff formatting",
        )["run"]
    )
    assert (
        "ty check DeepResearch"
        in _step(
            jobs,
            "quality",
            "Run full type checks",
        )["run"]
    )
    lock_and_whitespace = _step(
        jobs,
        "quality",
        "Check lockfile and whitespace",
    )["run"]
    assert "uv lock --check" in lock_and_whitespace
    assert "git diff --check" in lock_and_whitespace
    assert (
        "mkdocs build"
        in _step(
            jobs,
            "quality",
            "Build documentation",
        )["run"]
    )
