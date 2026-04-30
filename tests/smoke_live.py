"""Live smoke test against api.parallel.ai.

Run manually:
    PARALLEL_API_KEY=... .venv/bin/python tests/smoke_live.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback


def _line(label: str) -> None:
    print(f"\n--- {label} ---")


def _summary(name: str, result: dict) -> None:
    if (
        isinstance(result, dict)
        and "results" in result
        and isinstance(result["results"], list)
    ):
        print(f"{name}: ok ({len(result['results'])} results)")
    elif isinstance(result, dict) and "url" in result:
        print(f"{name}: ok (url={result['url']!r})")
    elif isinstance(result, dict):
        keys = list(result.keys())[:5]
        print(f"{name}: ok (keys={keys})")
    else:
        print(f"{name}: ok ({type(result).__name__})")


def main() -> int:
    if "PARALLEL_API_KEY" not in os.environ:
        print("PARALLEL_API_KEY not set; skipping live test.", file=sys.stderr)
        return 1

    failures: list[str] = []

    from parallel_google_adk.search import _web_fetch, _web_search
    from parallel_google_adk.extract import _extract
    from parallel_google_adk.task import _deep_research

    _line("web_search")
    try:
        result = _web_search(
            objective="What is the Parallel AI web research API?",
            queries=["parallel.ai search API", "parallel AI web research"],
            max_results=3,
        )
        _summary("web_search", result)
        # Print one excerpt for sanity.
        results_list = result.get("results") or []
        if results_list:
            first = results_list[0]
            print(f"  first.url: {first.get('url')}")
            excerpts = first.get("excerpts") or []
            if excerpts:
                preview = excerpts[0][:120].replace("\n", " ")
                print(f"  first.excerpt[0:120]: {preview}...")
    except Exception as e:
        failures.append(f"web_search: {e}")
        traceback.print_exc()

    _line("web_fetch")
    try:
        result = _web_fetch(url="https://parallel.ai/")
        _summary("web_fetch", result)
        print(f"  url: {result.get('url')}")
        print(f"  title: {result.get('title')}")
    except Exception as e:
        failures.append(f"web_fetch: {e}")
        traceback.print_exc()

    _line("extract (multi-URL)")
    try:
        result = _extract(
            urls=["https://parallel.ai/", "https://docs.parallel.ai/"],
            objective="What products does Parallel offer?",
        )
        _summary("extract", result)
        for r in (result.get("results") or [])[:2]:
            print(f"  - {r.get('url')} (excerpts={len((r.get('excerpts') or []))})")
    except Exception as e:
        failures.append(f"extract: {e}")
        traceback.print_exc()

    # Deep research is slow + costs $$. Only run if explicitly opted in.
    if os.environ.get("RUN_DEEP_RESEARCH") == "1":
        _line("deep_research (pro-fast)")
        try:
            result = _deep_research(
                objective="In one paragraph: what does Parallel AI's Search API do? Cite parallel.ai.",
                processor="pro-fast",
                timeout_seconds=300,
            )
            _summary("deep_research", result)
            output = result.get("output") or result.get("parsed")
            if output:
                preview = (
                    json.dumps(output)[:300]
                    if not isinstance(output, str)
                    else output[:300]
                )
                print(f"  output[0:300]: {preview}...")
        except Exception as e:
            failures.append(f"deep_research: {e}")
            traceback.print_exc()
    else:
        print("\n(skipping deep_research; set RUN_DEEP_RESEARCH=1 to enable)")

    print("\n=========================")
    if failures:
        print(f"FAILED: {len(failures)} tool(s)")
        for f in failures:
            print(f"  - {f}")
        return 2
    print("All smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
