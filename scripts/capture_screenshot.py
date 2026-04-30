"""Capture a clean terminal screenshot for the adk-docs integration page.

Runs the example agent and writes the formatted output to docs/screenshot.txt
(human-readable plain text). Take a screenshot of that file rendered in your
terminal of choice (or use Carbon / ray.so for a polished image).

Usage:
    PARALLEL_API_KEY=... .venv/bin/python scripts/capture_screenshot.py
    open -a Terminal docs/screenshot.txt   # then take a screenshot manually
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from io import StringIO
from pathlib import Path

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

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "screenshot.txt"


async def main() -> int:
    if "PARALLEL_API_KEY" not in os.environ:
        print("Set PARALLEL_API_KEY before running.", file=sys.stderr)
        return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    buf = StringIO()

    agent = LlmAgent(
        model="gemini-flash-latest",
        name="research_agent",
        instruction=(
            "You are a research assistant. Use web_search to find sources and "
            "always cite them with the url."
        ),
        tools=[web_search, web_fetch, extract, deep_research, enrich],
    )
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="parallel-demo", user_id="demo"
    )
    runner = Runner(
        agent=agent,
        app_name="parallel-demo",
        session_service=session_service,
        plugins=[ParallelTracingPlugin()],
    )

    prompt = "What does Parallel's Search API do? Cite parallel.ai in one sentence."

    buf.write("$ python research_agent.py\n")
    buf.write(f"\n>>> {prompt}\n\n")

    user_message = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(
        user_id="demo", session_id=session.id, new_message=user_message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    buf.write(part.text + "\n")

    final_session = await session_service.get_session(
        app_name="parallel-demo", user_id="demo", session_id=session.id
    )
    calls = final_session.state.get("_parallel_calls", []) if final_session else []
    buf.write(f"\n--- Parallel call trace ({len(calls)} calls) ---\n")
    for call in calls:
        buf.write(f"  {json.dumps(call)}\n")

    OUTPUT_PATH.write_text(buf.getvalue())
    print(f"Wrote {OUTPUT_PATH}")
    print("\n--- preview ---\n")
    print(buf.getvalue())
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
