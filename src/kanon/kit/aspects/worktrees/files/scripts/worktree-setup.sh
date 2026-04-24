#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/worktree-setup.sh <slug>
# Creates a git worktree at .worktrees/<slug> on branch wt/<slug>.

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <slug>" >&2
  exit 1
fi

slug="$1"
wt_dir=".worktrees/${slug}"
branch="wt/${slug}"

if [[ -d "$wt_dir" ]]; then
  echo "Error: worktree already exists at ${wt_dir}" >&2
  exit 1
fi

# Warn if .worktrees/ is not in .gitignore
if [[ -f .gitignore ]] && ! grep -qx '.worktrees/' .gitignore 2>/dev/null; then
  echo "Warning: .worktrees/ is not in .gitignore — consider adding it." >&2
fi

git worktree add "$wt_dir" -b "$branch"
echo "Worktree created: ${wt_dir} (branch: ${branch})"
