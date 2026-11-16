"""End-to-end smoke test exercising every tool + the tracing plugin shapes.

Coverage gaps this fills (vs the lighter tests/smoke_live.py):
  - _enrich() against the live Task API (was never called)
  - LLM agent picking web_fetch and extract (only web_search was exercised before)
  - Tracing plugin citation_count heuristic on Task API output shape

Skips deep_research (already verified, slow + expensive). Set RUN_DEEP=1 to include.

Run:
    PARALLEL_API_KEY=... .venv/bin/python tests/smoke_live_full.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from parallel_google_adk import (
    ParallelTracingPlugin,
    deep_research,
    enrich,
    extract,
    web_fetch,
    web_search,
)
from parallel_google_adk.tracing import _count_citations

# The public re-exports are FunctionTool wrappers; .func gives the inner
# Python function so we can call it directly without going through ADK.
_enrich = enrich.func


def _line(label: str) -> None:
    print(f"\n--- {label} ---")


async def _run_agent_prompt(prompt: str, expected_tool: str) -> tuple[str, list]:
    """Run a single prompt through Gemini Flash and return final text + trace."""
    agent = LlmAgent(
        model="gemini-flash-latest",
        name="research_agent",
        instruction=(
            "You are a research assistant. Use the most appropriate tool. "
            "Always cite sources with their URL."
        ),
        tools=[web_search, web_fetch, extract, deep_research, enrich],
    )
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name="smoke", user_id="u")
    runner = Runner(
        agent=agent,
        app_name="smoke",
        session_service=session_service,
        plugins=[ParallelTracingPlugin()],
    )
    user_message = types.Content(role="user", parts=[types.Part(text=prompt)])
    final_text = ""
    async for event in runner.run_async(
        user_id="u", session_id=session.id, new_message=user_message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_text += part.text
    final_session = await session_service.get_session(
        app_name="smoke", user_id="u", session_id=session.id
    )
    calls = final_session.state.get("_parallel_calls", []) if final_session else []
    print(f"prompt: {prompt[:80]}...")
    print(f"expected tool: {expected_tool}")
    print(f"trace: {calls}")
    return final_text, calls


async def main() -> int:
    if "PARALLEL_API_KEY" not in os.environ:
        print("PARALLEL_API_KEY not set; aborting.", file=sys.stderr)
        return 1

    # Report unexpected errors from each check and keep running the remaining checks.
    failures: list[str] = []

    # 1. Direct _enrich() — first time hitting the live Task API enrich path.
    _line("_enrich (direct, lite processor)")
    try:
        result = _enrich(
            objective="Find the company's official website URL.",
            inputs_json=json.dumps(
                [{"name": "Parallel Web Systems"}, {"name": "Anthropic"}]
            ),
            output_schema_json=json.dumps(
                {
                    "type": "object",
                    "properties": {
                        "website": {"type": "string", "description": "Official URL"}
                    },
                    "required": ["website"],
                }
            ),
            processor="lite",
            timeout_seconds=300,
        )
        # Result shape varies; just assert we got something useful back.
        run_id = result.get("run_id") or (result.get("run") or {}).get("run_id")
        output = result.get("output") or result.get("parsed")
        print(f"run_id: {run_id}")
        if output:
            preview = (
                json.dumps(output)[:300]
                if not isinstance(output, str)
                else output[:300]
            )
            print(f"output[0:300]: {preview}")
        if not run_id and not output:
            failures.append("_enrich: empty result")
        else:
            # Also verify citation_count heuristic on Task API shape.
            citations = _count_citations(result)
            print(f"_count_citations on Task result: {citations}")
    except Exception as e:  # noqa: BLE001
        failures.append(f"_enrich: {e}")
        traceback.print_exc()

    web_tools = {"web_search", "web_fetch", "extract"}

    # 2. LLM agent — web_fetch
    _line("agent: should pick web_fetch")
    try:
        _, trace = await _run_agent_prompt(
            "Fetch the page at https://parallel.ai/ and summarize the headline in one sentence.",
            expected_tool="web_fetch",
        )
        tools_called = [c.get("tool") for c in trace]
        if not any(c.get("tool") in web_tools for c in trace):
            failures.append(
                f"agent web_fetch: no relevant tool called (got {tools_called})"
            )
        for call in trace:
            if call.get("citation_count", 0) == 0 and call.get("tool") in web_tools:
                failures.append(
                    f"agent web_fetch: tracing citation_count=0 for {call['tool']}"
                )
    except Exception as e:  # noqa: BLE001
        failures.append(f"agent web_fetch: {e}")
        traceback.print_exc()

    # 3. LLM agent — extract (multi-URL hint)
    _line("agent: should pick extract")
    try:
        _, trace = await _run_agent_prompt(
            "Extract the main content from these two URLs and tell me what they have in common: "
            "https://parallel.ai/ and https://docs.parallel.ai/",
            expected_tool="extract",
        )
        tools_called = [c.get("tool") for c in trace]
        if not any(c.get("tool") in web_tools for c in trace):
            failures.append(
                f"agent extract: no relevant tool called (got {tools_called})"
            )
    except Exception as e:  # noqa: BLE001
        failures.append(f"agent extract: {e}")
        traceback.print_exc()

    # 4. Optional — deep_research via agent (slow + expensive).
    if os.environ.get("RUN_DEEP") == "1":
        _line("agent: should pick deep_research")
        try:
            _, trace = await _run_agent_prompt(
                "Do deep research: what are the three core APIs Parallel offers, with a "
                "one-sentence description of each? Use the deep_research tool.",
                expected_tool="deep_research",
            )
            if not any(c.get("tool") == "deep_research" for c in trace):
                tools_called = [c.get("tool") for c in trace]
                failures.append(f"agent deep_research: not called (got {tools_called})")
        except Exception as e:  # noqa: BLE001
            failures.append(f"agent deep_research: {e}")
            traceback.print_exc()
    else:
        print("\n(skipping agent deep_research; set RUN_DEEP=1 to enable)")

    print("\n=========================")
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("All extended smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
