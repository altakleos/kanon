---
status: done
date: 2026-04-29
---
# Plan: Delivery Guidance in Base Layer

## Problem

Agents following kanon protocols have no guidance on what to do after implementation is complete. Changes are left uncommitted, unpushed, with no PR. This applies to all kanon consumers regardless of which aspects are enabled.

## Approach

Add delivery guidance to the base AGENTS.md template (always present, zero config) and cross-reference it from existing protocols.

## Changes

### 1. `src/kanon/kit/agents-md-base.md` — add delivery bullet to Contribution Conventions

Add a "Delivering work" bullet after the existing three bullets:

```markdown
- **Delivering work** — a task is not done until changes are committed and pushed. After completing work:
  1. Run the `completion-checklist` protocol first, if active.
  2. Stage changed files explicitly (`git add <files>`), not `git add .`.
  3. Commit with a conventional-commit message. Reference the plan slug if one exists.
  4. Push to the remote branch. For worktree branches, push `wt/<slug>`.
  5. Open a PR/MR/CR with a summary of changes, what was tested, and a link to the plan.
  6. State what was committed and where the PR is. Never leave uncommitted changes.
```

### 2. `src/kanon/kit/aspects/kanon-sdd/protocols/completion-checklist.md` — amend exit criteria

Change the exit criteria from:

> "All acceptance criteria met. No test regressions. Docs updated. No unrelated changes. Artifact statuses current."

To:

> "All acceptance criteria met. No test regressions. Docs updated. No unrelated changes. Artifact statuses current. Changes committed and pushed per Contribution Conventions."

### 3. `src/kanon/kit/aspects/kanon-worktrees/protocols/worktree-lifecycle.md` — amend teardown

Add a step before "Remove the worktree" in the Teardown section:

> - Push the worktree branch and open a PR/MR/CR before tearing down. A worktree should not be removed until its changes are on a remote branch with a review request (or merged).

## Out of scope

- New aspect creation (deferred until delivery guidance outgrows prose)
- Hard gate addition (delivery is a "you're done, now ship" moment, not a pre-modification gate)
- CLI tooling (`kanon deliver` command)

## Acceptance criteria

- [x] Contribution Conventions in agents-md-base.md includes delivery guidance
- [x] completion-checklist exit criteria references committing/pushing
- [x] worktree-lifecycle teardown includes push/PR step before removal
- [x] `kanon verify` passes on the kanon repo itself after changes
- [x] Existing tests pass
