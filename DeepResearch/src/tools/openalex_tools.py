from __future__ import annotations

from typing import Any

import requests

from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class OpenAlexFetchTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="openalex_fetch",
                description="Fetch OpenAlex work or author",
                inputs={"entity": "TEXT", "identifier": "TEXT"},
                outputs={"result": "JSON"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err or "invalid params")
        entity = params["entity"]
        identifier = params["identifier"]
        base = "https://api.openalex.org"
        url = f"{base}/{entity}/{identifier}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return ExecutionResult(success=True, data={"result": resp.json()})


def _register() -> None:
    registry.register("openalex_fetch", lambda: OpenAlexFetchTool())


_register()
