"""Repo-local mgrep-style semantic search support."""

from __future__ import annotations

from importlib import import_module

_CLASS_EXPORTS = {
    "MgrepIndexTool": ("tools", "MgrepIndexTool"),
    "MgrepSearchTool": ("tools", "MgrepSearchTool"),
    "MgrepServer": ("server", "MgrepServer"),
    "MgrepService": ("service", "MgrepService"),
    "MgrepStatsTool": ("tools", "MgrepStatsTool"),
    "MgrepSyncTool": ("tools", "MgrepSyncTool"),
    "semantic_repo_search": ("tools", "semantic_repo_search"),
    "semantic_repo_search_tool": ("tools", "semantic_repo_search_tool"),
}

_SUBMODULE_EXPORTS = {
    "chunking",
    "discovery",
    "runtime",
    "server",
    "service",
    "tools",
}


def __getattr__(name: str):
    if name in _SUBMODULE_EXPORTS:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module

    if name not in _CLASS_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _CLASS_EXPORTS[name]
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals()) + list(_CLASS_EXPORTS) + list(_SUBMODULE_EXPORTS))


__all__ = tuple(sorted(list(_CLASS_EXPORTS) + list(_SUBMODULE_EXPORTS)))
