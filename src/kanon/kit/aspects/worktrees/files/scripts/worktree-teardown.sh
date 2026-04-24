#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/worktree-teardown.sh <slug>
# Safely removes the worktree at .worktrees/<slug>. Refuses if dirty.

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <slug>" >&2
  exit 1
fi

slug="$1"
wt_dir=".worktrees/${slug}"
branch="wt/${slug}"

if [[ ! -d "$wt_dir" ]]; then
  echo "Error: no worktree at ${wt_dir}" >&2
  exit 1
fi

# Refuse to remove if there are uncommitted changes
if ! git -C "$wt_dir" diff --quiet HEAD 2>/dev/null || \
   [[ -n "$(git -C "$wt_dir" status --porcelain 2>/dev/null)" ]]; then
  echo "Error: worktree at ${wt_dir} has uncommitted changes. Commit or stash first." >&2
  exit 1
fi

git worktree remove "$wt_dir"
echo "Worktree removed: ${wt_dir}"

# Delete branch if merged
if git branch -d "$branch" 2>/dev/null; then
  echo "Branch deleted: ${branch} (was merged)"
else
  echo "Branch retained: ${branch} (not yet merged or does not exist)"
fi
