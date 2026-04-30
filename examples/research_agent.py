"""Runnable example: a research agent on Google ADK using Parallel.

Set PARALLEL_API_KEY (and GEMINI_API_KEY or appropriate Google creds) and run:
    pip install -e ".[dev]"
    python examples/research_agent.py
"""

from __future__ import annotations

import asyncio
import os

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

APP_NAME = "parallel-google-adk-demo"
USER_ID = "demo-user"


def build_agent() -> LlmAgent:
    return LlmAgent(
        model="gemini-flash-latest",
        name="research_agent",
        instruction=(
            "You are a research assistant. "
            "For quick fact lookups, call web_search. "
            "For specific URLs, call web_fetch or extract. "
            "For comprehensive cited reports, call deep_research. "
            "Always cite your sources."
        ),
        tools=[web_search, web_fetch, extract, deep_research, enrich],
    )


async def main() -> None:
    if "PARALLEL_API_KEY" not in os.environ:
        raise SystemExit("Set PARALLEL_API_KEY before running this example.")

    agent = build_agent()
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
        plugins=[ParallelTracingPlugin()],
    )

    prompt = (
        "Use web_search to find the homepage of Parallel (parallel.ai) and "
        "summarize what their Search API does in one sentence with a citation."
    )
    print(f"\n>>> {prompt}\n")

    user_message = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session.id, new_message=user_message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)

    final_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session.id
    )
    calls = final_session.state.get("_parallel_calls", []) if final_session else []
    print(f"\n--- Parallel call trace ({len(calls)} calls) ---")
    for call in calls:
        print(f"  {call}")


if __name__ == "__main__":
    asyncio.run(main())
