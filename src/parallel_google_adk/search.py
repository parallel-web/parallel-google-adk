"""Parallel Search API as ADK FunctionTools.

Most agents should prefer the Search MCP (https://search.parallel.ai/mcp) over
these FunctionTools — it's the same surface with no SDK dependency. This module
exists for users who want everything Parallel-related to flow through the
parallel-web SDK with a single auth path.
"""

from __future__ import annotations

from typing import Annotated, Any

from google.adk.tools import FunctionTool

from ._client import get_client


def _web_search(
    objective: Annotated[
        str,
        "Natural-language description of what you want to find. Be specific — "
        "the model uses this to score and select the most relevant excerpts.",
    ],
    queries: Annotated[
        list[str],
        "1–5 keyword search queries (3–6 words each). Each query is run "
        "independently; results are merged and re-ranked.",
    ],
    max_results: Annotated[
        int,
        "Maximum number of excerpts to return. 1–10 recommended.",
    ] = 5,
    max_chars_total: Annotated[
        int | None,
        "Optional ceiling on total characters across all excerpts. Useful for "
        "controlling token budget on long-running agent loops.",
    ] = None,
) -> dict[str, Any]:
    """Search the web for current, citation-aware information.

    Returns LLM-optimized excerpts with source URLs. Use this when you need
    grounded facts the model wouldn't know, or when you don't already have
    URLs to fetch. Prefer web_fetch when you have specific URLs in hand.
    """
    client = get_client()
    kwargs: dict[str, Any] = {
        "objective": objective,
        "search_queries": list(queries),
        "advanced_settings": {"max_results": max_results},
    }
    if max_chars_total is not None:
        kwargs["max_chars_total"] = max_chars_total
    response = client.search(**kwargs)
    return response.model_dump()


def _web_fetch(
    url: Annotated[str, "The URL to fetch. Must be a fully-qualified http(s) URL."],
    objective: Annotated[
        str | None,
        "Optional focus for the extraction — what to keep relevant. If omitted, "
        "returns the full cleaned content.",
    ] = None,
) -> dict[str, Any]:
    """Fetch a single URL and return clean, LLM-ready content.

    Handles JavaScript-rendered pages and PDFs. Use this when you already know
    the URL (e.g. after a web_search call). For multi-URL or batch extraction
    with richer options, use the `extract` tool instead.
    """
    client = get_client()
    kwargs: dict[str, Any] = {"urls": [url]}
    if objective is not None:
        kwargs["objective"] = objective
    response = client.extract(**kwargs)
    envelope = response.model_dump()
    results = envelope.get("results") or []
    return (
        results[0]
        if results
        else {"url": url, "results": [], "warnings": envelope.get("warnings")}
    )


web_search = FunctionTool(_web_search)
web_fetch = FunctionTool(_web_fetch)
