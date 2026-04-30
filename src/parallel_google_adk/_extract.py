"""Parallel Extract API as an ADK FunctionTool."""

from __future__ import annotations

from typing import Annotated, Any

from google.adk.tools import FunctionTool

from ._client import get_client


def extract(
    urls: Annotated[
        list[str],
        "URLs to extract content from. 1–20 per call. Fully-qualified http(s) URLs only.",
    ],
    objective: Annotated[
        str | None,
        "Optional focus: what to keep relevant. Improves signal-to-noise on long pages.",
    ] = None,
    full_content: Annotated[
        bool,
        "If True, returns full cleaned page content. If False (default), returns excerpts only.",
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
    # full_content goes inside advanced_settings, not at the top level —
    # the SDK rejects it as an unexpected kwarg otherwise.
    if full_content:
        kwargs["advanced_settings"] = {"full_content": True}
    response = client.extract(**kwargs)
    return response.model_dump()


extract = FunctionTool(extract)
