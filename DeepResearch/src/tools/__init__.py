"""Tool registry initialization with safe imports."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

from .base import registry

logger = logging.getLogger(__name__)


def _safe_import(module_name: str):
    """Import a module, logging and continuing when optional deps are missing."""

    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.warning("Skipping tool module %s: %s", module_name, exc)
        return None


_safe_imports = [
    "DeepResearch.src.tools.analytics_tools",
    "DeepResearch.src.tools.bioinformatics_tools",
    "DeepResearch.src.tools.deepsearch_tools",
    "DeepResearch.src.tools.deepsearch_workflow_tool",
    "DeepResearch.src.tools.docker_sandbox",
    "DeepResearch.src.tools.integrated_search_tools",
    "DeepResearch.src.tools.mock_tools",
    "DeepResearch.src.tools.pyd_ai_tools",
    "DeepResearch.src.tools.websearch_tools",
    "DeepResearch.src.tools.workflow_tools",
]

_loaded_modules = [_safe_import(mod) for mod in _safe_imports]

if TYPE_CHECKING:
    from .bioinformatics_tools import GOAnnotationTool, PubMedRetrievalTool
    from .deepsearch_tools import DeepSearchTool
    from .integrated_search_tools import RAGSearchTool
    from .websearch_tools import ChunkedSearchTool, WebSearchTool

__all__ = ["registry", "_loaded_modules", "_safe_imports"]
