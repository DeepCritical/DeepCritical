from __future__ import annotations

from ..datatypes.pydantic_ai_tools import CodeExecBuiltinRunner, UrlContextBuiltinRunner
from ..utils.pydantic_ai_utils import (
    build_agent as _build_agent,
)
from ..utils.pydantic_ai_utils import (
    build_builtin_tools as _build_builtin_tools,
)
from ..utils.pydantic_ai_utils import (
    build_toolsets as _build_toolsets,
)

# Import the tool runners and utilities from utils
from ..utils.pydantic_ai_utils import (
    get_pydantic_ai_config as _get_cfg,
)
from ..utils.pydantic_ai_utils import (
    run_agent_sync as _run_sync,
)

# Registry overrides and additions
from .base import registry

registry.register("pyd_code_exec", lambda: CodeExecBuiltinRunner())
registry.register("pyd_url_context", lambda: UrlContextBuiltinRunner())

# Export the functions for external use
__all__ = [
    "_build_agent",
    "_build_builtin_tools",
    "_build_toolsets",
    "_get_cfg",
    "_run_sync",
]
