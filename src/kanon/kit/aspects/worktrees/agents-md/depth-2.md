The `worktrees` aspect is active with automation helpers. All file-modifying changes should be isolated in git worktrees under `.worktrees/<slug>/`.

## Key Constraints

- Worktree creation is triggered by **any file modification**, not concurrency detection.
- Never force-remove a worktree with uncommitted changes.
- Branch naming convention: `wt/<slug>`.
- Use the helper scripts in `scripts/` for consistent lifecycle management:
  - `scripts/worktree-setup.sh <slug>` — create a worktree
  - `scripts/worktree-teardown.sh <slug>` — safely remove a worktree
  - `scripts/worktree-status.sh` — list all active worktrees
