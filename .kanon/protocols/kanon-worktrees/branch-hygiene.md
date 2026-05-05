---
status: accepted
date: 2026-04-28
depth-min: 1
invoke-when: A file-modifying operation is about to begin
gate: hard
label: Worktree Isolation
summary: all file modifications happen in `.worktrees/<slug>/` on branch `wt/<slug>`.
audit: 'Working in worktree `.worktrees/<slug>/` on branch `wt/<slug>`.'
priority: 10
question: 'Am I in a worktree (`.worktrees/<slug>/`)? If not, check if one already exists (`ls .worktrees/`) before creating a new one.'
skip-when: never (always applies to file modifications)
check: '[[ "$PWD" == */.worktrees/* ]]'
---
# Protocol: Branch Hygiene

## Purpose

Ensure every file modification happens in an isolated git worktree, preventing interference between parallel work streams.

## Steps

### 1. Decide

If you are about to modify any file — create a worktree. No exceptions.

If you are only reading files, running builds, or answering questions — no worktree needed.

### 2. Create the worktree

```bash
git worktree add .worktrees/<slug> -b wt/<slug>
```

- `<slug>` derives from the plan or task name.
- Branch: `wt/<slug>` — always use this prefix.
- Verify `.worktrees/` is in `.gitignore`.

### 3. State the audit sentence

**Before your first file-modifying tool call, state in one sentence:** "Working in worktree `.worktrees/<slug>/` on branch `wt/<slug>`." If you cannot truthfully emit this sentence, stop and create the worktree.

### 4. Integration cadence

- Rebase from `main` before starting significant new work.
- Resolve conflicts immediately.

### 5. Teardown

- Never force-remove a worktree with uncommitted changes.
- Commit or stash all work before running `git worktree remove`.
- Delete the `wt/<slug>` branch only after it has been merged.

## Exit criteria

- All file modifications happened inside `.worktrees/<slug>/`.
- The audit sentence was stated before the first file-modifying tool call.
