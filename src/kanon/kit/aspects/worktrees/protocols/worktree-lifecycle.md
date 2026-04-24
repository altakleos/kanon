---
status: accepted
date: 2026-04-23
depth-min: 1
invoke-when: A multi-file or multi-step change is about to begin, or `git worktree list` shows active worktrees from other work streams
---
# Protocol: Worktree lifecycle

## Purpose

Guide agents through the full lifecycle of a git worktree — from deciding whether isolation is warranted, through setup, development, integration, and teardown. The primary trigger is change scope (multi-file or multi-step), not concurrency detection. As a secondary heuristic, `git worktree list` reveals whether parallel work is already in progress.

## Steps

### 1. Decision

Assess the change scope:

- **Multi-file or multi-step change** → create a worktree.
- **Single-file typo or one-liner fix** → work in the main checkout.
- **Uncertain** → prefer a worktree; an unnecessary worktree is harmless, a missed collision is not.

Run `git worktree list` as a secondary check. If other worktrees exist under `.worktrees/`, parallel work is likely — isolate.

### 2. Setup

```bash
git worktree add .worktrees/<slug> -b wt/<slug>
```

- `<slug>` derives from the plan or task name (e.g., `worktrees-aspect`, `fix-login-bug`).
- Verify `.worktrees/` is listed in `.gitignore`. If not, add it.
- If the worktree already exists, reuse it — do not create a duplicate.

### 3. Work

Develop normally inside `.worktrees/<slug>/`. Commit frequently to the `wt/<slug>` branch. Follow all other active process gates (plan-before-build, etc.) as usual.

### 4. Integration

- Run `git rebase main` periodically to stay current.
- Resolve conflicts immediately — do not let them accumulate across multiple rebases.
- Before any significant new work session, rebase first.

### 5. Teardown

- Commit or stash all changes. **Never force-remove a worktree with uncommitted changes.**
- Remove the worktree: `git worktree remove .worktrees/<slug>`.
- Delete the branch only if it has been merged: `git branch -d wt/<slug>`.
- If the branch has not been merged and work is abandoned, escalate to the human before deleting.

## Exit criteria

- The worktree has been removed cleanly (no uncommitted changes lost).
- The `wt/<slug>` branch has been merged or explicitly preserved for later.
- `git worktree list` no longer shows the removed worktree.

## Anti-patterns

- **Force-removing dirty worktrees.** `git worktree remove --force` with uncommitted changes destroys work. Never do this.
- **Long-lived worktrees without rebasing.** Divergence from `main` compounds merge conflicts. Rebase regularly.
- **Worktrees for trivial changes.** A single-file typo fix does not need isolation — the overhead is not justified.
- **Concurrency detection via lock files.** Lock files are fragile (stale after crashes, race conditions). Use change scope as the trigger instead.
