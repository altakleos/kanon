#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/worktree-status.sh
# Lists all worktrees under .worktrees/ with branch, last commit date, and status.

if [[ ! -d .worktrees ]]; then
  echo "No .worktrees/ directory found."
  exit 0
fi

# Clean up stale worktree metadata
git worktree prune

for wt in .worktrees/*/; do
  [[ -d "$wt" ]] || continue
  slug="$(basename "$wt")"
  branch="$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
  last_commit="$(git -C "$wt" log -1 --format='%ci' 2>/dev/null || echo "no commits")"
  if [[ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]]; then
    status="dirty"
  else
    status="clean"
  fi
  printf "%-20s  branch: %-25s  last-commit: %s  [%s]\n" "$slug" "$branch" "$last_commit" "$status"
done
