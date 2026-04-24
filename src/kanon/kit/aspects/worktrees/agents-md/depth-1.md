The `worktrees` aspect is active. Multi-file or multi-step changes should be isolated in git worktrees under `.worktrees/<slug>/`.

## Key Constraints

- Worktree creation is triggered by **change scope**, not concurrency detection.
- Never force-remove a worktree with uncommitted changes.
- Branch naming convention: `wt/<slug>`.

<!-- kanon:begin:worktrees/branch-hygiene -->
<!-- kanon:end:worktrees/branch-hygiene -->
