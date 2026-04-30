"""Unit tests for ParallelTracingPlugin."""

from __future__ import annotations

from typing import Any

import pytest

from parallel_google_adk.tracing import (
    ParallelTracingPlugin,
    _count_citations,
    _extract_cost,
)


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeContext:
    def __init__(self) -> None:
        self.state: dict[str, Any] = {}


@pytest.mark.asyncio
async def test_plugin_records_parallel_call() -> None:
    plugin = ParallelTracingPlugin()
    tool = _FakeTool("_web_search")
    ctx = _FakeContext()
    args: dict[str, Any] = {"objective": "x", "queries": ["x"]}
    await plugin.before_tool_callback(tool=tool, tool_args=args)
    await plugin.after_tool_callback(
        tool=tool,
        tool_args=args,
        result={"results": [{"citations": ["a", "b"]}, {"citations": ["c"]}]},
        tool_context=ctx,
    )
    calls = ctx.state["_parallel_calls"]
    assert len(calls) == 1
    entry = calls[0]
    assert entry["tool"] == "_web_search"
    assert entry["citation_count"] == 3
    assert entry["latency_s"] is not None and entry["latency_s"] >= 0


@pytest.mark.asyncio
async def test_plugin_skips_non_parallel_tool() -> None:
    plugin = ParallelTracingPlugin()
    tool = _FakeTool("some_other_tool")
    ctx = _FakeContext()
    args: dict[str, Any] = {}
    await plugin.before_tool_callback(tool=tool, tool_args=args)
    await plugin.after_tool_callback(
        tool=tool, tool_args=args, result={}, tool_context=ctx
    )
    assert ctx.state.get("_parallel_calls") is None


def test_count_citations_handles_shapes() -> None:
    # Top-level citations list.
    assert _count_citations({"citations": [1, 2, 3]}) == 3
    # Search/Extract: URL-bearing results.
    assert (
        _count_citations({"results": [{"url": "https://a"}, {"url": "https://b"}]}) == 2
    )
    # Older shape: per-result citations lists.
    assert (
        _count_citations({"results": [{"citations": [1]}, {"citations": [2, 3]}]}) == 3
    )
    # Task API: output.basis list with per-entry citations.
    assert (
        _count_citations(
            {
                "output": {
                    "basis": [
                        {"citations": ["x", "y"]},
                        {"citations": ["z"]},
                    ]
                }
            }
        )
        == 3
    )
    # Legacy basis dict shape.
    assert _count_citations({"basis": {"citations": [1, 2]}}) == 2
    assert _count_citations({}) == 0
    assert _count_citations(None) == 0


def test_extract_cost_handles_shapes() -> None:
    assert _extract_cost({"cost_usd": 0.42}) == 0.42
    assert _extract_cost({"usage": {"cost_usd": 1.5}}) == 1.5
    assert _extract_cost({}) is None
    assert _extract_cost(None) is None
