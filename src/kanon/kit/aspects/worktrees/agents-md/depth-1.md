# AGENTS.md — ${project_name}

The `worktrees` aspect is active. Multi-file or multi-step changes should be isolated in git worktrees under `.worktrees/<slug>/`.

## Boot chain

0. Read this file.
1. Read [`.kanon/protocols/worktrees/worktree-lifecycle.md`](.kanon/protocols/worktrees/worktree-lifecycle.md) — the full worktree lifecycle protocol.

## Key Constraints

- Worktree creation is triggered by **change scope**, not concurrency detection.
- Never force-remove a worktree with uncommitted changes.
- Branch naming convention: `wt/<slug>`.

<!-- kanon:begin:worktrees/branch-hygiene -->
<!-- kanon:end:worktrees/branch-hygiene -->

<!-- kanon:begin:protocols-index -->
<!-- kanon:end:protocols-index -->

## References

- [`.kanon/protocols/worktrees/worktree-lifecycle.md`](.kanon/protocols/worktrees/worktree-lifecycle.md) — lifecycle protocol
