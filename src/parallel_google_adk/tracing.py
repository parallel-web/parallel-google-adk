"""Optional ADK Plugin that traces Parallel tool calls.

Captures, per session: tool name, latency, citation count, and (when present
in the tool result) cost. Stored on the session state so downstream
observability layers can read it.

Keep narrow — no policy, no quota, no side-effecting export. If you want
those, layer your own Plugin on top or pipe ``state["_parallel_calls"]`` to
your existing observability stack.

Usage:
    runner = Runner(agent=agent, app_name="my-app", plugins=[ParallelTracingPlugin()])

After a run::
    final_session = await session_service.get_session(...)
    calls = final_session.state.get("_parallel_calls", [])
    # [{"tool": "web_search", "latency_s": 1.16, "citation_count": 5}, ...]
"""

from __future__ import annotations

import time
from typing import Any

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Public tool names registered by parallel_google_adk. Tracing applies to these
# only — other tools the agent calls are passed through untouched.
PARALLEL_TOOL_NAMES = frozenset(
    {"web_search", "web_fetch", "extract", "deep_research", "enrich"}
)


class ParallelTracingPlugin(BasePlugin):
    """Traces calls to Parallel FunctionTools.

    Records latency, citation count, and (when reported) cost in
    ``tool_context.state["_parallel_calls"]`` — a list of dicts with keys:
    ``tool``, ``latency_s``, ``citation_count``, ``cost_usd`` (optional),
    ``error`` (optional).

    Per-call timing is keyed on ``ToolContext.function_call_id`` so concurrent
    sessions sharing one Plugin instance don't collide.
    """

    def __init__(
        self,
        name: str = "parallel-tracing",
        state_key: str = "_parallel_calls",
    ) -> None:
        super().__init__(name=name)
        self._state_key = state_key
        self._starts: dict[str, float] = {}

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> None:
        if tool.name not in PARALLEL_TOOL_NAMES:
            return
        key = self._call_key(tool_context, tool)
        self._starts[key] = time.monotonic()

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> None:
        if tool.name not in PARALLEL_TOOL_NAMES:
            return
        latency_s = self._consume_latency(tool_context, tool)

        entry: dict[str, Any] = {
            "tool": tool.name,
            "latency_s": latency_s,
            "citation_count": _count_citations(result),
        }
        cost = _extract_cost(result)
        if cost is not None:
            entry["cost_usd"] = cost
        self._append_entry(tool_context, entry)

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> None:
        if tool.name not in PARALLEL_TOOL_NAMES:
            return
        latency_s = self._consume_latency(tool_context, tool)
        self._append_entry(
            tool_context,
            {
                "tool": tool.name,
                "latency_s": latency_s,
                "error": repr(error),
            },
        )

    # ----- internal helpers -----

    @staticmethod
    def _call_key(tool_context: ToolContext, tool: BaseTool) -> str:
        # function_call_id is unique per LLM-emitted tool call. Falls back to
        # a less-unique key if ADK ever omits it.
        call_id = getattr(tool_context, "function_call_id", None)
        return f"{call_id}:{tool.name}" if call_id else f"_:{tool.name}"

    def _consume_latency(
        self, tool_context: ToolContext, tool: BaseTool
    ) -> float | None:
        key = self._call_key(tool_context, tool)
        started_at = self._starts.pop(key, None)
        return time.monotonic() - started_at if started_at is not None else None

    def _append_entry(self, tool_context: ToolContext, entry: dict[str, Any]) -> None:
        state = getattr(tool_context, "state", None)
        if state is None:
            return
        bucket = state.get(self._state_key) or []
        bucket.append(entry)
        state[self._state_key] = bucket


def _count_citations(result: Any) -> int:
    """Best-effort citation count across the API response shapes we wrap.

    - Search / Extract API: each ``results[]`` entry carries a ``url`` — count those.
    - web_fetch (single-URL): one envelope dict with ``url`` at top — count as 1.
    - Task API (deep_research / enrich): citations live under ``output.basis``.
    """
    if not isinstance(result, dict):
        return 0
    if isinstance(result.get("citations"), list):
        return len(result["citations"])
    results_list = result.get("results")
    if isinstance(results_list, list):
        url_count = sum(1 for r in results_list if isinstance(r, dict) and r.get("url"))
        if url_count:
            return url_count
        return sum(
            len(r.get("citations", [])) if isinstance(r, dict) else 0
            for r in results_list
        )
    if isinstance(result.get("url"), str):
        return 1
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
