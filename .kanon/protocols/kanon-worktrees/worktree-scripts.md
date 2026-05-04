---
status: accepted
date: 2026-05-04
depth-min: 2
invoke-when: Creating, inspecting, or tearing down worktrees at depth 2, where shell helper scripts are available
---
# Protocol: Worktree Scripts

## Purpose

At depth 2, three shell scripts are scaffolded under `scripts/`. Use them instead of raw `git worktree` commands for consistent worktree management.

## Steps

### 1. Creating a worktree

Use `scripts/worktree-setup.sh <slug>` instead of `git worktree add`. The script creates `.worktrees/<slug>` on branch `wt/<slug>` with the correct conventions from the `branch-hygiene` protocol.

Multiple slugs can be passed to create several worktrees at once.

### 2. Checking worktree status

Use `scripts/worktree-status.sh` to list all active worktrees with branch name, last commit date, and dirty/clean status.

### 3. Tearing down a worktree

Use `scripts/worktree-teardown.sh <slug>` instead of `git worktree remove`. The script refuses to remove a worktree with uncommitted changes, preventing accidental work loss.

## Exit criteria

- Worktree operations use the helper scripts, not raw git commands.
