---
status: done
date: 2026-04-27
design: "No design doc — mechanical script hardening + prose additions to existing files"
---
# Plan: Phase 1 — Upstream sensei worktree hardening + process prose

## Goal

Bring three quick-win improvements from sensei into kanon's kit bundle:

1. Harden `worktree-setup.sh` (dirty-check, idempotent, multi-slug)
2. Add design-doc skip audit convention to `spec-before-design` section
3. Add parallel worktree coordination guidance to `worktree-lifecycle` protocol

## Acceptance Criteria

- [ ] `worktree-setup.sh` aborts if the working directory has uncommitted staged or unstaged changes
- [ ] `worktree-setup.sh` skips (exit 0) if the worktree already exists instead of erroring
- [ ] `worktree-setup.sh` reuses an existing branch instead of failing on `-b` conflict
- [ ] `worktree-setup.sh` accepts 1 or more slug arguments
- [ ] `spec-before-design.md` includes the `design: "Follows ADR-NNNN"` frontmatter convention for design-doc skips
- [ ] `worktree-lifecycle.md` includes a "Parallel worktree coordination" subsection covering disjoint write sets, shared accumulation files, and merge ordering
- [ ] All existing tests pass (`pytest`)
- [ ] `kanon verify .` passes

## Files Modified

| File | Change |
|------|--------|
| `src/kanon/kit/aspects/kanon-worktrees/files/scripts/worktree-setup.sh` | Dirty-check, idempotent, multi-slug |
| `src/kanon/kit/aspects/kanon-sdd/sections/spec-before-design.md` | Design-doc skip frontmatter convention |
| `src/kanon/kit/aspects/kanon-worktrees/protocols/worktree-lifecycle.md` | Parallel coordination subsection |

## Out of Scope

- Teardown script changes (merge workflow is intentionally not in kanon)
- Multi-slug for teardown/status scripts
- CI validator promotions (Phase 2)
- New aspect depths or manifest changes
