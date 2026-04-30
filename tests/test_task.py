"""Unit tests for the task module — JSON parse error paths and _format_result."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from parallel_google_adk import enrich
from parallel_google_adk._task import _format_result


def test_enrich_rejects_invalid_inputs_json() -> None:
    enrich_fn = enrich.func  # unwrap the FunctionTool
    with pytest.raises(ValueError, match="inputs_json"):
        enrich_fn(
            objective="x",
            inputs_json="not json {",
            output_schema_json='{"type":"object"}',
        )


def test_enrich_rejects_invalid_output_schema_json() -> None:
    enrich_fn = enrich.func
    with pytest.raises(ValueError, match="output_schema_json"):
        enrich_fn(
            objective="x",
            inputs_json="[]",
            output_schema_json="also not json",
        )


def test_format_result_with_model_dump() -> None:
    obj = SimpleNamespace(model_dump=lambda: {"output": {"x": 1}, "run": {"id": "r1"}})
    out = _format_result(obj)
    assert out == {"output": {"x": 1}, "run": {"id": "r1"}}


def test_format_result_lifts_parsed_pydantic_instance() -> None:
    parsed = SimpleNamespace(model_dump=lambda: {"website": "parallel.ai"})
    obj = SimpleNamespace(model_dump=lambda: {"output": {"basis": []}}, parsed=parsed)
    out = _format_result(obj)
    assert out["parsed"] == {"website": "parallel.ai"}
    assert out["output"]["basis"] == []


def test_format_result_dict_fallback() -> None:
    # An object without model_dump should fall through to dict(...) — we use a
    # mapping-compatible object so dict() succeeds.
    out = _format_result({"output": {"x": 1}})
    assert out == {"output": {"x": 1}}


def test_format_result_with_parsed_plain_dict() -> None:
    """If parsed isn't a Pydantic model, surface it verbatim."""
    obj = SimpleNamespace(
        model_dump=lambda: {"output": {}}, parsed={"already": "a dict"}
    )
    out: dict[str, Any] = _format_result(obj)
    assert out["parsed"] == {"already": "a dict"}
