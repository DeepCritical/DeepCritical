from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def authenticated_parser_client_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep unit clients authenticated without weakening production defaults."""

    monkeypatch.setenv("DOCLING_API_KEY", "docling-fixture-key-123")
    monkeypatch.setenv("GROBID_API_KEY", "grobid-fixture-key-1234")
