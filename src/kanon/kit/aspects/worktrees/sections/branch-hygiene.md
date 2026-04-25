## Worktree Branch Hygiene

Use a dedicated git worktree for any change that modifies files. Read-only operations (reviewing code, running builds, answering questions) stay in the main checkout.

**Before your first file-modifying tool call, state in one sentence:** "Working in worktree `.worktrees/<slug>/` on branch `wt/<slug>`." If you cannot truthfully emit this sentence, stop and create the worktree. This sentence is the audit trail — its absence in a transcript is how violations get caught.

**When to create a worktree:**

- You are about to modify any file — no exceptions.
- `git worktree list` shows other worktrees — parallel work is in progress.
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
