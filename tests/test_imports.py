"""Smoke test: package imports cleanly and exposes the expected surface."""

from __future__ import annotations

from importlib.metadata import version as pkg_version

import pytest


def test_public_imports() -> None:
    from parallel_google_adk import (
        ParallelTracingPlugin,
        deep_research,
        enrich,
        extract,
        web_fetch,
        web_search,
    )

    # Tools should be FunctionTool instances with public, LLM-friendly names.
    from google.adk.tools import FunctionTool

    for tool, expected_name in [
        (web_search, "web_search"),
        (web_fetch, "web_fetch"),
        (extract, "extract"),
        (deep_research, "deep_research"),
        (enrich, "enrich"),
    ]:
        assert isinstance(tool, FunctionTool)
        assert tool.name == expected_name

    plugin = ParallelTracingPlugin()
    assert plugin.name == "parallel-tracing"


@pytest.mark.parametrize(
    "tool_name",
    ["web_search", "web_fetch", "extract", "deep_research", "enrich"],
)
def test_tool_name_in_tracing_set(tool_name: str) -> None:
    """Every public tool must be recognized by the tracing plugin."""
    from parallel_google_adk.tracing import PARALLEL_TOOL_NAMES

    assert tool_name in PARALLEL_TOOL_NAMES


def test_version_matches_metadata() -> None:
    """__version__ should reflect the installed package metadata."""
    import parallel_google_adk

    # When installed editable, importlib.metadata returns pyproject's version.
    expected = pkg_version("parallel-google-adk")
    assert parallel_google_adk.__version__ == expected
