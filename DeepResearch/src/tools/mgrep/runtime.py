"""Shared runtime helpers for repo-local mgrep semantic search."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path
from typing import Any, cast

from omegaconf import OmegaConf

from DeepResearch.src.datatypes.mgrep import MgrepConfig

from .service import MgrepService

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MGREP_CONFIG_PATH = _PROJECT_ROOT / "configs" / "mgrep" / "default.yaml"

_SERVICE_CACHE: dict[tuple[str, str], MgrepService] = {}
_SERVICE_CACHE_LOCK = threading.Lock()


def run_async(coro: Any) -> Any:
    """Run a coroutine from sync code, even if a loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - exercised in async callers
            error["value"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


def load_mgrep_config(config_path: str | Path | None = None) -> MgrepConfig:
    """Load mgrep config from YAML, defaulting to the repo config."""
    resolved_path = (
        DEFAULT_MGREP_CONFIG_PATH
        if config_path is None
        else Path(config_path).expanduser().resolve()
    )
    if config_path is None and not resolved_path.exists():
        return MgrepConfig()
    raw_config = OmegaConf.load(resolved_path)
    config_data = OmegaConf.to_container(raw_config, resolve=True)
    if config_data is None:
        config_data = {}
    if not isinstance(config_data, dict):
        msg = f"Expected mapping config at {resolved_path}, got {type(config_data)}"
        raise TypeError(msg)
    return MgrepConfig.model_validate(cast("dict[str, Any]", config_data))


def resolve_mgrep_config(
    *,
    config: MgrepConfig | None = None,
    config_path: str | Path | None = None,
) -> MgrepConfig:
    """Resolve either an injected config object or a YAML-backed config."""
    if config is not None and config_path is not None:
        msg = "Provide either config or config_path, not both"
        raise ValueError(msg)
    if config is not None:
        return config.model_copy(deep=True)
    return load_mgrep_config(config_path)


def get_mgrep_service(
    repo_root: str | Path = ".",
    *,
    config: MgrepConfig | None = None,
    config_path: str | Path | None = None,
) -> MgrepService:
    """Reuse one mgrep service per repo root and resolved config."""
    resolved_repo_root = str(Path(repo_root).resolve())
    resolved_config = resolve_mgrep_config(config=config, config_path=config_path)
    cache_key = (
        resolved_repo_root,
        json.dumps(resolved_config.model_dump(mode="json"), sort_keys=True),
    )
    with _SERVICE_CACHE_LOCK:
        service = _SERVICE_CACHE.get(cache_key)
        if service is None:
            service = MgrepService(
                repo_root=resolved_repo_root,
                config=resolved_config.model_copy(deep=True),
            )
            _SERVICE_CACHE[cache_key] = service
        return service


def clear_mgrep_service_cache() -> None:
    """Clear cached services for tests or process-level resets."""
    with _SERVICE_CACHE_LOCK:
        _SERVICE_CACHE.clear()
