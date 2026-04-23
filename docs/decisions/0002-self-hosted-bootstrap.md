---
status: accepted
date: 2026-04-22
---
# ADR-0002: Self-hosted bootstrap — commits 1–3 are pre-SDD

## Context

`kanon` is itself a tier-3 `kanon` project. Its own development must follow the method it ships. This creates a chicken-and-egg: the first commit cannot follow the method because the method files (AGENTS.md, development-process.md, decisions/, plans/) do not yet exist in the repo.

## Decision

The first three commits on `main` are explicitly **pre-SDD bootstrap** commits. The method engages from commit 4 onward.

- **Commit 1 (bootstrap).** Repo skeleton: `LICENSE`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, `AGENTS.md` (hand-authored, tier-3), `CLAUDE.md` shim, `docs/development-process.md` (ported from Sensei, project-agnostic), `docs/kanon-implementation.md` (bootstrap stub), `docs/foundations/vision.md` (bootstrap stub), index `README.md` files under `docs/foundations/`, `docs/decisions/`, `docs/plans/`. All boot-chain links resolve.
- **Commit 2 (bootstrap).** `docs/foundations/vision.md` fleshed out with Current Promises + Non-Goals + Design Stance. `docs/plans/v0.1-bootstrap.md` is authored.
- **Commit 3 (bootstrap).** This ADR and the other seven critical ADRs (0001, 0003–0008). `docs/decisions/README.md` index populated.
- **Commit 4 onward.** Every change follows the kit's own rules: plan-before-build, spec-before-design, etc. Spec-authoring, design-doc authoring, and implementation land in later commits per the Phase B–F schedule in `docs/plans/v0.1-bootstrap.md`.

## Alternatives Considered

1. **Write the method first in an external scratch area, then move into the repo as commit 1.** Essentially the same content distribution, but now the repo's commit history is opaque about *how* the method was introduced. Rejected — auditability of the bootstrap itself is valuable.
2. **Defer `AGENTS.md` and the method files to later commits; ship only `pyproject.toml` in commit 1.** Creates a window where the repo is not-yet-an-kanon-project but claims to be one. Rejected — the self-hosting property should hold from commit 1.
3. **Write a minimal AGENTS.md first (no process gates), then add gates incrementally.** Same issue as #2 — a consumer looking at an early kanon commit would not see the same AGENTS.md shape the kit itself ships. Rejected.
4. **Three-commit named bootstrap with an ADR legitimising it** (chosen). Honest, bounded, auditable. Future readers can distinguish bootstrap commits from rule violations.

## Consequences

- Commits 1–3 are NOT themselves subject to the plan-before-build or spec-before-design gates. They are bootstrap by declaration.
- The retroactive-plan-rot concern (see `docs/foundations/vision.md` Design Stance and session planning history) is bounded because the bootstrap phase is explicitly scoped to three commits.
- Future contributors reading the git log can point at this ADR if challenged "the method was violated in commits 1–3." Answer: yes, deliberately and documented.

## Config Impact

None.

## References

- Session plan at `~/.claude/plans/implement-1-thru-7-whimsical-backus.md` (reconstructable from the approved plan captured inside the ExitPlanMode return).
- `docs/plans/v0.1-bootstrap.md` — execution record.
