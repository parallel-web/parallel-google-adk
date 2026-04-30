#!/usr/bin/env bash
set -euo pipefail

# Release helper for parallel-google-adk.
# Usage:
#   ./scripts/release.sh rc       # next RC (0.1.0 -> 0.2.0rc1 OR 0.1.0rc1 -> 0.1.0rc2)
#   ./scripts/release.sh stable   # promote current RC to stable (0.1.0rc2 -> 0.1.0)
#   ./scripts/release.sh 0.2.0    # set an explicit version
#
# What it does:
#   1. Updates the version field in pyproject.toml
#   2. Creates a release branch (release/X.Y.Z)
#   3. Commits with "chore: bump version to X.Y.Z"
#   4. Pushes the branch and opens a PR
#
# After the PR merges, .github/workflows/auto-release.yml creates the tag +
# GitHub release automatically, which triggers publish.yml -> PyPI.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

die() { echo "error: $*" >&2; exit 1; }

get_current_version() {
    grep '^version = ' "$PROJECT_ROOT/pyproject.toml" | sed 's/version = "\(.*\)"/\1/'
}

calculate_next_version() {
    local current="$1"
    local bump_type="$2"
    case "$bump_type" in
        rc)
            if [[ "$current" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)rc([0-9]+)$ ]]; then
                local maj="${BASH_REMATCH[1]}" min="${BASH_REMATCH[2]}" pat="${BASH_REMATCH[3]}" rc="${BASH_REMATCH[4]}"
                echo "${maj}.${min}.${pat}rc$((rc + 1))"
            elif [[ "$current" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
                local maj="${BASH_REMATCH[1]}" min="${BASH_REMATCH[2]}" pat="${BASH_REMATCH[3]}"
                echo "${maj}.$((min + 1)).${pat}rc1"
            else
                die "cannot parse version: $current"
            fi
            ;;
        stable)
            if [[ "$current" =~ ^([0-9]+\.[0-9]+\.[0-9]+)rc[0-9]+$ ]]; then
                echo "${BASH_REMATCH[1]}"
            else
                die "current version ($current) is not an RC -- nothing to promote"
            fi
            ;;
        *)
            if [[ "$bump_type" =~ ^[0-9]+\.[0-9]+\.[0-9]+(rc[0-9]+)?$ ]]; then
                echo "$bump_type"
            else
                die "invalid version format: $bump_type (expected X.Y.Z or X.Y.Zrc#)"
            fi
            ;;
    esac
}

update_pyproject() {
    local new_version="$1"
    sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" "$PROJECT_ROOT/pyproject.toml"
    rm "$PROJECT_ROOT/pyproject.toml.bak"
}

main() {
    [[ $# -eq 1 ]] || die "usage: $0 (rc | stable | X.Y.Z[rc#])"
    local bump="$1"

    cd "$PROJECT_ROOT"

    # Refuse to run on a dirty tree -- version PRs should be clean.
    if [[ -n "$(git status --porcelain)" ]]; then
        die "working tree is not clean. Commit or stash changes first."
    fi

    # Must run from main so the release branch forks from a clean upstream tip.
    local current_branch
    current_branch="$(git rev-parse --abbrev-ref HEAD)"
    if [[ "$current_branch" != "main" ]]; then
        die "must be on 'main' (currently on '$current_branch'). Run: git checkout main && git pull"
    fi

    # Make sure we're up to date with origin/main so the release branch is
    # forking from the latest tip — otherwise the version bump can land on a
    # stale base.
    git fetch origin main --quiet
    if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
        die "local main is not in sync with origin/main. Run: git pull --ff-only"
    fi

    local current new branch tag
    current="$(get_current_version)"
    new="$(calculate_next_version "$current" "$bump")"
    branch="release/$new"
    tag="v$new"

    # Refuse if the tag already exists locally OR on the remote — auto-release
    # would otherwise double-tag and fail mid-flight.
    if git rev-parse "$tag" >/dev/null 2>&1; then
        die "tag $tag already exists locally"
    fi
    if git ls-remote --tags origin "$tag" | grep -q "refs/tags/$tag$"; then
        die "tag $tag already exists on origin"
    fi

    echo "current: $current"
    echo "new:     $new"
    echo "branch:  $branch"
    echo "tag:     $tag (will be created by auto-release.yml after merge)"
    read -rp "proceed? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || die "aborted"

    git checkout -b "$branch"
    update_pyproject "$new"
    git add pyproject.toml
    git commit -m "chore: bump version to $new"
    git push -u origin "$branch"

    if command -v gh >/dev/null 2>&1; then
        gh pr create \
            --title "chore: bump version to $new" \
            --body "Release $new. Merging this PR will trigger auto-release.yml -> publish.yml -> PyPI."
    else
        echo "(gh CLI not found; open the PR manually: https://github.com/parallel-web/parallel-google-adk/compare/main...$branch)"
    fi
}

main "$@"
