"""Tests for the cached Parallel client."""

from __future__ import annotations

import pytest

from parallel_google_adk import _client


def setup_function() -> None:
    _client.get_client.cache_clear()


def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="PARALLEL_API_KEY"):
        _client.get_client()


def test_client_built_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARALLEL_API_KEY", "test-key-not-real")
    client = _client.get_client()
    assert client is not None
    # Should hit the same instance on a second call thanks to lru_cache.
    assert _client.get_client() is client
