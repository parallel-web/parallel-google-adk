# Assets — TODO

For the `adk-docs` PR, drop the Parallel logo here as `parallel.png`:

- **Format**: PNG with transparent background.
- **Aspect ratio**: square (1:1).
- **Recommended size**: 512×512 (matches the resolution other partners ship — Stripe, Pinecone, Tavily).
- **Path expected by adk-docs**: `docs/integrations/assets/parallel.png` (referenced from the `catalog_icon` frontmatter field in `parallel.md`).

A demo screenshot also belongs here (`research_agent.png`). Generate one by running:

```
PARALLEL_API_KEY=... .venv/bin/python ../../scripts/capture_screenshot.py
```

That writes `docs/screenshot.txt` — open it in a polished terminal (iTerm2 with a clean theme, or [ray.so](https://ray.so) / [carbon.now.sh](https://carbon.now.sh) for a styled image), then crop and save as `research_agent.png` here.
