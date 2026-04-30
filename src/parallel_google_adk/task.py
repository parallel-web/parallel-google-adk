"""Parallel Task API as ADK FunctionTools.

Two tools:
  - deep_research: long-running multi-hop research with cited results
  - enrich: structured-output extraction against a JSON Schema or Pydantic model

Both use the SDK's ``client.task_run.execute(...)`` which handles create + poll
internally, so the FunctionTool returns a finished result in one call. Default
processor is ``pro-fast`` for deep research (good speed/quality tradeoff);
override for the slower-but-more-thorough ``pro`` (2–10 min) or ``ultra``
(5–25 min) processors.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from google.adk.tools import FunctionTool
from pydantic import BaseModel

from ._client import get_client

DEFAULT_DEEP_RESEARCH_PROCESSOR = "pro-fast"
DEFAULT_ENRICH_PROCESSOR = "core"
DEFAULT_TIMEOUT_S = 1200.0  # 20 minutes


def _format_result(result: Any) -> dict[str, Any]:
    """Convert SDK TaskRunResult / ParsedTaskRunResult to a plain dict.

    Surfaces run id, output, basis (citations + reasoning), and lifts the
    parsed pydantic instance to a top-level ``parsed`` field if present.
    """
    payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    parsed = getattr(result, "parsed", None)
    if parsed is not None:
        payload["parsed"] = (
            parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        )
    return payload


def _deep_research(
    objective: Annotated[
        str,
        "Natural-language description of what to research. Be specific about "
        "the question, the depth wanted, and any constraints (recency, sources, "
        "geography).",
    ],
    processor: Annotated[
        str,
        "Task processor. 'pro-fast' (default, ~1–3 min) for fast research; "
        "'pro' (2–10 min) for thorough; 'ultra' (5–25 min) for the most "
        "comprehensive investigative reports.",
    ] = DEFAULT_DEEP_RESEARCH_PROCESSOR,
    timeout_seconds: Annotated[
        float,
        "Maximum time to wait for the task to complete. Defaults to 20 minutes.",
    ] = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Run a multi-hop deep research task with cited results.

    Returns a comprehensive report with per-claim citations. Use this when the
    user wants a thorough investigation — not just a quick fact lookup. For
    fact lookups use web_search; for structured extraction use enrich.
    """
    client = get_client()
    result = client.task_run.execute(
        input=objective,
        processor=processor,
        timeout=timeout_seconds,
    )
    return _format_result(result)


def _enrich(
    objective: Annotated[
        str,
        "What to extract about each input. e.g. 'Find the company's CEO, "
        "headquarters city, and last funding round.'",
    ],
    inputs_json: Annotated[
        str,
        "JSON-encoded list of entities to enrich. Each entry is an object with "
        'keys like name/url/domain. Example: \'[{"name":"Acme","url":"acme.com"}]\'.',
    ],
    output_schema_json: Annotated[
        str,
        "JSON-encoded JSON Schema describing the desired per-input output shape. "
        'Example: \'{"type":"object","properties":{"ceo":{"type":"string"}},"required":["ceo"]}\'.',
    ],
    processor: Annotated[
        str,
        "Task processor. 'core' (default) is the standard enrichment processor; "
        "'pro' for harder questions; 'lite' for cheaper/faster runs.",
    ] = DEFAULT_ENRICH_PROCESSOR,
    timeout_seconds: Annotated[float, "Max wait time."] = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Enrich a list of entities with structured, cited fields.

    Use this when you want typed output (a schema-conforming dict) rather than
    a markdown report. Common use: pulling firmographic fields about companies,
    biographic fields about people, or product specs.

    Both inputs_json and output_schema_json are passed as JSON strings — the
    tool decodes them before calling the Task API.
    """
    try:
        inputs = json.loads(inputs_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"inputs_json must be valid JSON: {exc}") from exc
    try:
        schema = json.loads(output_schema_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"output_schema_json must be valid JSON: {exc}") from exc

    client = get_client()
    payload = {
        "objective": objective,
        "inputs": inputs,
    }
    result = client.task_run.execute(
        input=payload,
        processor=processor,
        output=schema,
        timeout=timeout_seconds,
    )
    return _format_result(result)


def enrich_with_model(
    objective: str,
    inputs: list[dict[str, Any]],
    output_model: type[BaseModel],
    processor: str = DEFAULT_ENRICH_PROCESSOR,
    timeout_seconds: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Pythonic enrich helper that accepts a Pydantic model class.

    Not exposed as a FunctionTool (LLMs can't pass class references), but useful
    for direct programmatic calls from agent harness code.
    """
    client = get_client()
    payload = {"objective": objective, "inputs": inputs}
    result = client.task_run.execute(
        input=payload,
        processor=processor,
        output=output_model,
        timeout=timeout_seconds,
    )
    return _format_result(result)


deep_research = FunctionTool(_deep_research)
enrich = FunctionTool(_enrich)
