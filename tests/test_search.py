"""Unit tests for search.py — verify SDK call shape, not HTTP transport."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from parallel_google_adk import web_fetch, web_search


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, Any]:
        return self._payload


def _patch_client(
    monkeypatch: pytest.MonkeyPatch, *, response_payload: dict[str, Any]
) -> dict[str, Any]:
    """Replace get_client() with a fake; return a dict where the fake records the kwargs it was called with."""
    captured: dict[str, Any] = {}

    def fake_search(**kwargs: Any) -> _FakeResponse:
        captured["search"] = kwargs
        return _FakeResponse(response_payload)

    def fake_extract(**kwargs: Any) -> _FakeResponse:
        captured["extract"] = kwargs
        return _FakeResponse(response_payload)

    fake_client = SimpleNamespace(search=fake_search, extract=fake_extract)
    monkeypatch.setattr("parallel_google_adk._search.get_client", lambda: fake_client)
    return captured


def test_web_search_passes_advanced_settings_max_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch_client(
        monkeypatch, response_payload={"results": [{"url": "https://example.com"}]}
    )
    result = web_search.func(
        objective="grounded objective", queries=["q1", "q2"], max_results=7
    )

    sent = captured["search"]
    assert sent["objective"] == "grounded objective"
    assert sent["search_queries"] == ["q1", "q2"]
    # max_results MUST be inside advanced_settings — top-level is rejected by the SDK.
    assert sent["advanced_settings"] == {"max_results": 7}
    assert "max_chars_total" not in sent  # omitted when None
    assert result == {"results": [{"url": "https://example.com"}]}


def test_web_search_passes_max_chars_total_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch_client(monkeypatch, response_payload={"results": []})
    web_search.func(objective="x", queries=["q"], max_chars_total=10_000)
    assert captured["search"]["max_chars_total"] == 10_000


def test_web_fetch_returns_first_result(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _patch_client(
        monkeypatch,
        response_payload={
            "results": [
                {"url": "https://x", "title": "X", "excerpts": ["…"]},
            ],
            "warnings": [],
        },
    )
    result = web_fetch.func(url="https://x")

    assert captured["extract"] == {"urls": ["https://x"]}
    assert result["url"] == "https://x"
    assert result["title"] == "X"


def test_web_fetch_passes_objective(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _patch_client(
        monkeypatch, response_payload={"results": [{"url": "https://x"}]}
    )
    web_fetch.func(url="https://x", objective="be brief")
    assert captured["extract"]["objective"] == "be brief"


def test_web_fetch_empty_results_returns_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_client(
        monkeypatch, response_payload={"results": [], "warnings": ["unreachable"]}
    )
    result = web_fetch.func(url="https://nope")
    assert result == {
        "url": "https://nope",
        "results": [],
        "warnings": ["unreachable"],
    }
