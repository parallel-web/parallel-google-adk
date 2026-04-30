# Release process

`parallel-google-adk` uses **PyPI Trusted Publishing** (OIDC) — no API tokens stored anywhere. Releases are commit-message-driven: merge a `chore: bump version to X.Y.Z` commit to `main`, and the rest happens automatically.

## One-time PyPI setup (do this before the first release)

1. Go to https://pypi.org/manage/account/publishing/ → "Add a new pending publisher".
2. Fill in:
   - **PyPI project name**: `parallel-google-adk`
   - **Owner**: `parallel-web`
   - **Repository name**: `parallel-google-adk`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`
3. On GitHub: Settings → Environments → "New environment" → name it `pypi`. Optionally add a deployment branch rule (only `main`).

After the first successful publish, the project becomes a regular publisher (no longer "pending").

## Cutting a release

### Option A — use the helper script (recommended)

```bash
./scripts/release.sh rc       # next RC (0.1.0 -> 0.2.0rc1, or 0.1.0rc1 -> 0.1.0rc2)
./scripts/release.sh stable   # promote current RC to stable (0.1.0rc2 -> 0.1.0)
./scripts/release.sh 0.2.0    # explicit version
```

The script updates `pyproject.toml`, creates `release/X.Y.Z`, commits with the trigger message, pushes, and opens a PR.

### Option B — manual

1. Edit `pyproject.toml` — bump `version = "X.Y.Z"`.
2. Commit with the exact prefix: `chore: bump version to X.Y.Z`.
3. Open a PR against `main`.

## What happens after the PR merges

1. **`auto-release.yml`** detects the version-bump commit message on `main`, creates tag `vX.Y.Z`, and publishes a GitHub Release (marked prerelease automatically for `rcN` versions).
2. **`publish.yml`** triggers on the GitHub Release event, builds sdist + wheel, and publishes to PyPI via OIDC.

Both workflows are idempotent: if the tag already exists, `auto-release.yml` fails fast.

## Pre-flight checklist before merging the release PR

- [ ] CI green on the PR (`ci.yml`)
- [ ] `CHANGELOG.md` updated (if you keep one)
- [ ] Version in `pyproject.toml` matches the commit message
- [ ] No accidental `+dirty` or local edits sneaking in
