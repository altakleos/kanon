#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/worktree-setup.sh <slug> [slug ...]
# Creates git worktrees at .worktrees/<slug> on branch wt/<slug>.

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 <slug> [slug ...]" >&2
  exit 1
fi

# Abort if working directory has uncommitted changes
if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  echo "Error: working directory has uncommitted changes. Commit or stash first." >&2
  exit 1
fi

# Warn if .worktrees/ is not in .gitignore
if [[ -f .gitignore ]] && ! grep -qx '.worktrees/' .gitignore 2>/dev/null; then
  echo "Warning: .worktrees/ is not in .gitignore — consider adding it." >&2
fi

for slug in "$@"; do
  wt_dir=".worktrees/${slug}"
  branch="wt/${slug}"

  if [[ -d "$wt_dir" ]]; then
    echo "Worktree already exists at ${wt_dir}, reusing it."
    continue
  fi

  if git show-ref --verify --quiet "refs/heads/${branch}"; then
    echo "Warning: branch ${branch} already exists, attaching worktree to it." >&2
    git worktree add "$wt_dir" "$branch"
  else
    git worktree add "$wt_dir" -b "$branch"
  fi

  echo "Worktree created: ${wt_dir} (branch: ${branch})"
done

echo "NOTE: Run your dependency install command (uv sync, npm install, etc.) in the new worktree(s)."
