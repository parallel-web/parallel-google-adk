"""Parallel Extract API as an ADK FunctionTool."""

from __future__ import annotations

from typing import Annotated, Any

from google.adk.tools import FunctionTool

from ._client import get_client


def _extract(
    urls: Annotated[
        list[str],
        "URLs to extract clean content from. 1–20 per call. Fully-qualified "
        "http(s) URLs only.",
    ],
    objective: Annotated[
        str | None,
        "Optional focus: what to keep relevant in the extraction. Improves "
        "signal-to-noise on long pages. Omit for full extraction.",
    ] = None,
    full_content: Annotated[
        bool,
        "If True, returns the full cleaned page content. If False (default), "
        "returns LLM-optimized excerpts only.",
    ] = False,
) -> dict[str, Any]:
    """Extract clean content from web pages and PDFs in batch.

    Handles JavaScript-rendered sites and multi-page PDFs. Use this when you
    already know the URLs (e.g. after web_search) and need richer extraction
    than a single web_fetch call.
    """
    client = get_client()
    kwargs: dict[str, Any] = {"urls": list(urls)}
    if objective is not None:
        kwargs["objective"] = objective
    if full_content:
        kwargs["full_content"] = True
    response = client.extract(**kwargs)
    return response.model_dump()


extract = FunctionTool(_extract)
