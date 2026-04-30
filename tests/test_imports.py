"""Smoke test: package imports cleanly and exposes the expected surface."""

from __future__ import annotations


def test_public_imports() -> None:
    from parallel_google_adk import (
        ParallelTracingPlugin,
        deep_research,
        enrich,
        extract,
        web_fetch,
        web_search,
    )

    # Tools should be FunctionTool instances with the right name attribute.
    from google.adk.tools import FunctionTool

    for tool, expected_name in [
        (web_search, "_web_search"),
        (web_fetch, "_web_fetch"),
        (extract, "_extract"),
        (deep_research, "_deep_research"),
        (enrich, "_enrich"),
    ]:
        assert isinstance(tool, FunctionTool)
        assert tool.name == expected_name

    plugin = ParallelTracingPlugin()
    assert plugin.name == "parallel-tracing"


def test_version() -> None:
    import parallel_google_adk

    assert parallel_google_adk.__version__ == "0.1.0"
