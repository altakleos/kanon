The `worktrees` aspect is active. All file-modifying changes should be isolated in git worktrees under `.worktrees/<slug>/`.

## Key Constraints

- Worktree creation is triggered by **any file modification**, not concurrency detection.
- Never force-remove a worktree with uncommitted changes.
- Branch naming convention: `wt/<slug>`.
