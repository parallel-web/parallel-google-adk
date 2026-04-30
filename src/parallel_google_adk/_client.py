"""Cached Parallel SDK client for the ADK FunctionTools.

Reads PARALLEL_API_KEY from the environment by default. All FunctionTools call
get_client() lazily so import-time has no side effects.
"""

from __future__ import annotations

import os
from functools import lru_cache

from parallel import Parallel


@lru_cache(maxsize=1)
def get_client() -> Parallel:
    """Return a process-wide Parallel client.

    The client is cached for the lifetime of the process. Tests should call
    ``get_client.cache_clear()`` between cases that need different env vars.
    """
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PARALLEL_API_KEY is not set. Get a key at https://platform.parallel.ai "
            "and export PARALLEL_API_KEY=<your-key>."
        )
    return Parallel(api_key=api_key)
