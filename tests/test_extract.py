"""Unit tests for extract.py — verify SDK call shape including full_content nesting."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from parallel_google_adk import extract as extract_tool


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, Any]:
        return self._payload


def _patch_client(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_extract(**kwargs: Any) -> _FakeResponse:
        captured.update(kwargs)
        return _FakeResponse({"results": [{"url": u} for u in kwargs["urls"]]})

    fake_client = SimpleNamespace(extract=fake_extract)
    # String target resolves via sys.modules — bypasses the package's
    # re-exported `extract` FunctionTool that would otherwise shadow the
    # submodule under attribute access.
    monkeypatch.setattr("parallel_google_adk._extract.get_client", lambda: fake_client)
    return captured


def test_extract_default_call_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _patch_client(monkeypatch)
    extract_tool.func(urls=["https://a", "https://b"])

    assert captured["urls"] == ["https://a", "https://b"]
    assert "objective" not in captured
    # full_content defaults to False -> advanced_settings must NOT be added.
    assert "advanced_settings" not in captured


def test_extract_passes_objective(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _patch_client(monkeypatch)
    extract_tool.func(urls=["https://a"], objective="What products do they sell?")
    assert captured["objective"] == "What products do they sell?"


def test_extract_full_content_nests_under_advanced_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: full_content must be inside advanced_settings.

    The SDK rejects ``client.extract(full_content=True)`` as an unexpected
    kwarg — the value lives in the advanced_settings envelope instead.
    """
    captured = _patch_client(monkeypatch)
    extract_tool.func(urls=["https://a"], full_content=True)
    assert "full_content" not in captured  # NOT a top-level kwarg
    assert captured["advanced_settings"] == {"full_content": True}
