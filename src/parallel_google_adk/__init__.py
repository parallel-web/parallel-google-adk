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
        plugins=[ParallelTracingPlugin()],
    )

For Search alone, the Search MCP at https://search.parallel.ai/mcp is the simpler
default — see the integration page for the MCPToolset wiring. This package is the
typed-FunctionTool path for users who want fine-grained schemas, hidden polling,
and tracing.
"""

from .extract import extract
from .search import web_fetch, web_search
from .task import deep_research, enrich
from .tracing import ParallelTracingPlugin

__version__ = "0.1.0"

__all__ = [
    "ParallelTracingPlugin",
    "__version__",
    "deep_research",
    "enrich",
    "extract",
    "web_fetch",
    "web_search",
]
