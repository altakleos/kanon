---
status: draft
design: "Follows ADR-0014 (worktree isolation)"
touches:
  - .kanon/protocols/kanon-worktrees/worktree-lifecycle.md
  - src/kanon/kit/aspects/kanon-worktrees/protocols/worktree-lifecycle.md
---

# Plan: Add merge-caution guidance to worktree-lifecycle

## Motivation

The SOP analysis identified a gap: no guidance for what to do when
merging a worktree while other worktrees exist on disk. The existing
Section 5 ("Parallel worktree coordination") covers file ownership
partitioning, append-only files, and merge ordering — but says nothing
about checking for other worktrees before integrating.

The panel concluded that a full conflict-resolution protocol is
over-engineered (the human is the coordination layer, and there's no
reliable way to detect whether a worktree is "active"). The right fix
is one additional bullet in Section 5: when you're about to merge and
other worktrees exist, check for file overlap and be cautious.

## Change

Add a 4th bullet to Section 5 of the worktree-lifecycle protocol:

> **Check for overlap before integrating.** Before merging your
> worktree branch into main, run `git worktree list`. If other
> worktrees exist, compare changed files
> (`git diff --name-only main...wt/<other>` for each). If files
> overlap, merge the smaller changeset first and rebase the remaining
> worktree(s) before continuing their work. If a rebase conflict
> cannot be resolved mechanically, stop and present it to the user.

## Files changed

| File | Change |
|------|--------|
| `.kanon/protocols/kanon-worktrees/worktree-lifecycle.md` | Add 4th bullet to Section 5 |
| `src/kanon/kit/aspects/kanon-worktrees/protocols/worktree-lifecycle.md` | Byte-identical copy of above |

## Files NOT changed (with rationale)

- **AGENTS.md branch-hygiene section** — summary section; the protocol
  is the source of truth. Adding merge-caution to the summary would
  bloat it for a rare scenario.
- **completion-checklist Step 7** — checks worktree usage, not merge
  coordination. No change needed.
- **Fidelity fixture** — tests audit-sentence and force-remove rules,
  not Section 5 content. No change needed.

## Acceptance criteria

1. Section 5 of worktree-lifecycle.md contains 4 bullets (existing 3 +
   new merge-caution bullet).
2. Both copies (`.kanon/protocols/` and `src/kanon/kit/aspects/`) are
   byte-identical.
3. `python ci/check_kit_consistency.py` passes.
4. `kanon verify .` passes.
5. No other files are modified.
