## Worktree Branch Hygiene

Use a dedicated git worktree for any change that touches multiple files or requires multiple steps. Trivial single-file edits (typos, one-liner fixes) stay in the main checkout.

**When to create a worktree:**

- The change is multi-file or multi-step.
- `git worktree list` shows other worktrees — parallel work is likely in progress.
- You are unsure — prefer isolation; an unnecessary worktree is harmless.

**Worktree location and naming:**

- Path: `.worktrees/<slug>/` where `<slug>` derives from the plan or task name.
- Branch: `wt/<slug>` — always use this prefix for worktree branches.

**Integration cadence:**

- Rebase from `main` before starting significant new work in the worktree.
- Resolve conflicts immediately — do not let them accumulate.

**Teardown rules:**

- Never force-remove a worktree with uncommitted changes.
- Commit or stash all work before running `git worktree remove`.
- Delete the `wt/<slug>` branch only after it has been merged.
