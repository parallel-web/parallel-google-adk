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
    def __init__(self, function_call_id: str = "fc-1") -> None:
        self.function_call_id = function_call_id
        self.state: dict[str, Any] = {}


@pytest.mark.asyncio
async def test_plugin_records_parallel_call() -> None:
    plugin = ParallelTracingPlugin()
    tool = _FakeTool("web_search")
    ctx = _FakeContext()
    args: dict[str, Any] = {"objective": "x", "queries": ["x"]}
    await plugin.before_tool_callback(tool=tool, tool_args=args, tool_context=ctx)
    await plugin.after_tool_callback(
        tool=tool,
        tool_args=args,
        tool_context=ctx,
        result={"results": [{"url": "https://a"}, {"url": "https://b"}]},
    )
    calls = ctx.state["_parallel_calls"]
    assert len(calls) == 1
    entry = calls[0]
    assert entry["tool"] == "web_search"
    assert entry["citation_count"] == 2
    assert entry["latency_s"] is not None and entry["latency_s"] >= 0


@pytest.mark.asyncio
async def test_plugin_records_error() -> None:
    plugin = ParallelTracingPlugin()
    tool = _FakeTool("deep_research")
    ctx = _FakeContext(function_call_id="fc-err")
    args: dict[str, Any] = {"objective": "x"}
    await plugin.before_tool_callback(tool=tool, tool_args=args, tool_context=ctx)
    await plugin.on_tool_error_callback(
        tool=tool,
        tool_args=args,
        tool_context=ctx,
        error=RuntimeError("boom"),
    )
    calls = ctx.state["_parallel_calls"]
    assert len(calls) == 1
    entry = calls[0]
    assert entry["tool"] == "deep_research"
    assert "boom" in entry["error"]
    assert entry["latency_s"] is not None


@pytest.mark.asyncio
async def test_plugin_skips_non_parallel_tool() -> None:
    plugin = ParallelTracingPlugin()
    tool = _FakeTool("some_other_tool")
    ctx = _FakeContext()
    args: dict[str, Any] = {}
    await plugin.before_tool_callback(tool=tool, tool_args=args, tool_context=ctx)
    await plugin.after_tool_callback(
        tool=tool, tool_args=args, tool_context=ctx, result={}
    )
    assert ctx.state.get("_parallel_calls") is None


@pytest.mark.asyncio
async def test_concurrent_calls_use_distinct_keys() -> None:
    """Two overlapping tool calls (different function_call_ids) must not race."""
    plugin = ParallelTracingPlugin()
    tool = _FakeTool("web_search")
    ctx_a = _FakeContext(function_call_id="fc-a")
    ctx_b = _FakeContext(function_call_id="fc-b")
    args_a: dict[str, Any] = {}
    args_b: dict[str, Any] = {}

    await plugin.before_tool_callback(tool=tool, tool_args=args_a, tool_context=ctx_a)
    await plugin.before_tool_callback(tool=tool, tool_args=args_b, tool_context=ctx_b)
    await plugin.after_tool_callback(
        tool=tool, tool_args=args_b, tool_context=ctx_b, result={"results": []}
    )
    await plugin.after_tool_callback(
        tool=tool, tool_args=args_a, tool_context=ctx_a, result={"results": []}
    )
    assert len(ctx_a.state["_parallel_calls"]) == 1
    assert len(ctx_b.state["_parallel_calls"]) == 1
    assert ctx_a.state["_parallel_calls"][0]["latency_s"] is not None
    assert ctx_b.state["_parallel_calls"][0]["latency_s"] is not None


def test_count_citations_handles_shapes() -> None:
    assert _count_citations({"citations": [1, 2, 3]}) == 3
    assert (
        _count_citations({"results": [{"url": "https://a"}, {"url": "https://b"}]}) == 2
    )
    assert _count_citations({"url": "https://a", "title": "x", "excerpts": ["y"]}) == 1
    assert (
        _count_citations({"results": [{"citations": [1]}, {"citations": [2, 3]}]}) == 3
    )
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
    assert _count_citations({"basis": {"citations": [1, 2]}}) == 2
    assert _count_citations({}) == 0
    assert _count_citations(None) == 0


def test_extract_cost_handles_shapes() -> None:
    assert _extract_cost({"cost_usd": 0.42}) == 0.42
    assert _extract_cost({"usage": {"cost_usd": 1.5}}) == 1.5
    assert _extract_cost({}) is None
    assert _extract_cost(None) is None
