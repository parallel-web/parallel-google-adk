"""Parallel Task API as ADK FunctionTools.

Two tools:
  - deep_research: long-running multi-hop research with cited results
  - enrich: structured-output extraction against a JSON Schema

``deep_research`` uses ``client.task_run.execute(...)`` which handles create +
poll internally and accepts no output schema (returns a markdown report).

``enrich`` needs to pass a JSON Schema dict, which ``execute()`` rejects (it
only accepts Pydantic classes / strings); so it routes via
``client.beta.task_run.create(task_spec={"output_schema": {"type": "json", "json_schema": ...}})``
followed by ``client.task_run.result(run_id, api_timeout=...)`` for polling.

Default processor is ``pro-fast`` for deep research (good speed/quality
tradeoff); override for the slower ``pro`` (2–10 min) or ``ultra`` (5–25 min).
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from google.adk.tools import FunctionTool

from ._client import get_client

DEFAULT_DEEP_RESEARCH_PROCESSOR = "pro-fast"
DEFAULT_ENRICH_PROCESSOR = "core"
DEFAULT_TIMEOUT_S = 1200.0  # 20 minutes


def _format_result(result: Any) -> dict[str, Any]:
    """Convert SDK TaskRunResult / ParsedTaskRunResult to a plain dict."""
    payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    parsed = getattr(result, "parsed", None)
    if parsed is not None:
        payload["parsed"] = (
            parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        )
    return payload


def deep_research(
    objective: Annotated[
        str,
        "Natural-language description of what to research. Be specific.",
    ],
    processor: Annotated[
        str,
        "'pro-fast' (default, ~1–3 min), 'pro' (2–10 min), or 'ultra' (5–25 min).",
    ] = DEFAULT_DEEP_RESEARCH_PROCESSOR,
    timeout_seconds: Annotated[
        float,
        "Maximum time to wait. Defaults to 20 minutes.",
    ] = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Run a multi-hop deep research task with cited results.

    Returns a comprehensive report with per-claim citations. Use for thorough
    investigations — not quick fact lookups (use web_search for those).
    """
    client = get_client()
    result = client.task_run.execute(
        input=objective,
        processor=processor,
        timeout=timeout_seconds,
    )
    return _format_result(result)


def enrich(
    objective: Annotated[
        str,
        "What to extract about each input. e.g. 'Find the company's CEO and HQ city.'",
    ],
    inputs_json: Annotated[
        str,
        'JSON-encoded list of entity dicts. Example: \'[{"name":"Acme","url":"acme.com"}]\'.',
    ],
    output_schema_json: Annotated[
        str,
        'JSON-encoded JSON Schema for the per-input output. Example: \'{"type":"object","properties":{"ceo":{"type":"string"}}}\'.',
    ],
    processor: Annotated[
        str,
        "'core' (default), 'pro' for harder questions, or 'lite' for cheap/fast runs.",
    ] = DEFAULT_ENRICH_PROCESSOR,
    timeout_seconds: Annotated[float, "Max wait time."] = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Enrich a list of entities with structured, cited fields.

    Use this when you want typed output (a schema-conforming dict) rather than
    a markdown report. Both inputs_json and output_schema_json are JSON strings.
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
    payload = {"objective": objective, "inputs": inputs}
    # task_run.execute() rejects raw JSON Schema dicts (it accepts only Pydantic
    # classes or strings), so we use the create() + result() path. The schema
    # must be wrapped in the discriminated-union envelope:
    # {"type": "json", "json_schema": <our schema>}.
    run = client.beta.task_run.create(
        input=payload,
        processor=processor,
        task_spec={"output_schema": {"type": "json", "json_schema": schema}},
    )
    # Poll for the result. api_timeout controls the SDK long-poll window.
    result = client.task_run.result(run.run_id, api_timeout=int(timeout_seconds))
    return _format_result(result)


deep_research = FunctionTool(deep_research)
enrich = FunctionTool(enrich)
