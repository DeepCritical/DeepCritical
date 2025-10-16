from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup  # optional; if missing, users can install when needed

from .base import ExecutionResult, ToolRunner, ToolSpec, registry


class PatentScrapeTool(ToolRunner):
    def __init__(self):
        super().__init__(
            ToolSpec(
                name="patent_scrape",
                description="Scrape basic patent info from a public page",
                inputs={"url": "TEXT"},
                outputs={"title": "TEXT", "abstract": "TEXT"},
            )
        )

    def run(self, params: dict[str, Any]) -> ExecutionResult:
        ok, err = self.validate(params)
        if not ok:
            return ExecutionResult(success=False, error=err or "invalid params")
        url = params["url"]
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = (soup.find("title").get_text() if soup.find("title") else "").strip()
        abstract_el = soup.find("meta", {"name": "description"})
        abstract = (
            abstract_el["content"].strip()
            if abstract_el and abstract_el.get("content")
            else ""
        )
        return ExecutionResult(
            success=True, data={"title": title, "abstract": abstract}
        )


def _register() -> None:
    registry.register("patent_scrape", lambda: PatentScrapeTool())


_register()
