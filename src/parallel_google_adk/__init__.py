"""Google ADK FunctionTools and Plugin for Parallel APIs.

Install:
    pip install parallel-google-adk

Usage:
    from parallel_google_adk import (
        web_search, web_fetch, extract,
        deep_research, enrich,
        ParallelTracingPlugin,
    )

    agent = LlmAgent(
        model="gemini-flash-latest",
        name="research_agent",
        tools=[web_search, web_fetch, extract, deep_research, enrich],
    )
    runner = Runner(agent=agent, app_name="my-app", plugins=[ParallelTracingPlugin()])

For Search alone, the Search MCP at https://search.parallel.ai/mcp is a simpler
default — see the integration docs for the MCPToolset wiring. This package is
the typed-FunctionTool path for users who want fine-grained schemas, hidden
polling, structured enrichment, and tracing.
"""

from importlib.metadata import PackageNotFoundError, version

from ._extract import extract
from ._search import web_fetch, web_search
from ._task import deep_research, enrich
from .tracing import ParallelTracingPlugin

try:
    __version__ = version("parallel-google-adk")
except PackageNotFoundError:
    # Editable install / source checkout without metadata.
    __version__ = "0.0.0+unknown"

__all__ = [
    "ParallelTracingPlugin",
    "__version__",
    "deep_research",
    "enrich",
    "extract",
    "web_fetch",
    "web_search",
]
