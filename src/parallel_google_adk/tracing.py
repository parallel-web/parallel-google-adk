"""Optional ADK Plugin that traces Parallel tool calls.

Captures, per session: tool name, latency, citation count, and (when present
in the tool result) cost. Stored on the invocation context state so downstream
observability/Plugin layers can read it.

Keep narrow — no policy, no quota, no side-effecting export. If you want
those, layer your own Plugin on top or pipe ctx.state["_parallel_calls"] to
your existing observability stack.
"""

from __future__ import annotations

import time
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin

PARALLEL_TOOL_NAMES = {
    "_web_search",
    "_web_fetch",
    "_extract",
    "_deep_research",
    "_enrich",
    # Be permissive about the public names too in case ADK uses them.
    "web_search",
    "web_fetch",
    "extract",
    "deep_research",
    "enrich",
}


class ParallelTracingPlugin(BasePlugin):
    """Traces calls to Parallel FunctionTools.

    Reads/writes ``ctx.state["_parallel_calls"]`` — a list of dicts with
    keys: tool, latency_s, citation_count, cost_usd (optional), error (optional).
    """

    def __init__(
        self,
        name: str = "parallel-tracing",
        state_key: str = "_parallel_calls",
    ) -> None:
        super().__init__(name=name)
        self._state_key = state_key
        self._starts: dict[int, float] = {}

    async def before_tool_callback(
        self, *, tool: Any, tool_args: dict[str, Any], **_: Any
    ) -> None:
        if getattr(tool, "name", None) not in PARALLEL_TOOL_NAMES:
            return
        self._starts[id(tool_args)] = time.monotonic()

    async def after_tool_callback(
        self,
        *,
        tool: Any,
        tool_args: dict[str, Any],
        result: Any,
        tool_context: Any = None,
        **_: Any,
    ) -> None:
        if getattr(tool, "name", None) not in PARALLEL_TOOL_NAMES:
            return
        started_at = self._starts.pop(id(tool_args), None)
        latency_s = time.monotonic() - started_at if started_at is not None else None

        entry: dict[str, Any] = {
            "tool": tool.name,
            "latency_s": latency_s,
            "citation_count": _count_citations(result),
        }
        cost = _extract_cost(result)
        if cost is not None:
            entry["cost_usd"] = cost

        state = (
            getattr(tool_context, "state", None) if tool_context is not None else None
        )
        if state is None:
            return
        bucket = state.get(self._state_key) or []
        bucket.append(entry)
        state[self._state_key] = bucket


def _count_citations(result: Any) -> int:
    """Best-effort citation count across the API response shapes we wrap.

    - Search API: each ``results[]`` entry carries a ``url`` — count those.
    - Extract API: same — ``results[]`` with ``url``.
    - Task API (deep_research / enrich): citations live under ``output.basis``
      (list of basis blocks) or each entry's ``citations`` field.
    """
    if not isinstance(result, dict):
        return 0
    # Direct top-level ``citations`` (rare, but handle it).
    if isinstance(result.get("citations"), list):
        return len(result["citations"])
    # Search / Extract: count URL-bearing results.
    results_list = result.get("results")
    if isinstance(results_list, list):
        url_count = sum(1 for r in results_list if isinstance(r, dict) and r.get("url"))
        if url_count:
            return url_count
        return sum(
            len(r.get("citations", [])) if isinstance(r, dict) else 0
            for r in results_list
        )
    # Task API: ``output.basis`` is a list of basis entries with citations.
    output = result.get("output")
    if isinstance(output, dict):
        basis = output.get("basis")
        if isinstance(basis, list):
            total = 0
            for entry in basis:
                if isinstance(entry, dict) and isinstance(entry.get("citations"), list):
                    total += len(entry["citations"])
            if total:
                return total
    # Legacy / older envelopes with top-level basis.
    basis = result.get("basis")
    if isinstance(basis, dict) and isinstance(basis.get("citations"), list):
        return len(basis["citations"])
    return 0


def _extract_cost(result: Any) -> float | None:
    if not isinstance(result, dict):
        return None
    cost = result.get("cost_usd")
    if isinstance(cost, (int, float)):
        return float(cost)
    usage = result.get("usage")
    if isinstance(usage, dict) and isinstance(usage.get("cost_usd"), (int, float)):
        return float(usage["cost_usd"])
    return None
