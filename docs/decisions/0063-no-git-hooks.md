---
status: accepted
date: 2026-05-04
---
# ADR-0063: No Git Hooks for Gate Enforcement

## Context

Hard gates enforce that LLM agents follow process (worktree isolation, plan-before-build, etc.). The enforcement model is prose-based: agents read AGENTS.md, emit audit-trail sentences, and violations are detected post-hoc via transcript review.

Git hooks (pre-commit, pre-push) were considered as a runtime enforcement mechanism that could block commits on main or reject edits outside worktrees.

## Decision

kanon does NOT use git hooks for gate enforcement.

## Alternatives Considered

1. **Pre-commit hook rejecting commits on main** — Would prevent the observed failure (6 direct-to-main commits). Rejected for the reasons below.
2. **Pre-push hook requiring worktree branch** — Same enforcement, different timing. Same problems.
3. **Husky/lint-staged integration** — Adds a dependency and doesn't solve the fundamental issues.

## Rationale (Why Not Hooks)

1. **Hooks are fragile.** They require `--no-verify` to bypass, which agents and humans routinely use. A bypass mechanism that's one flag away isn't enforcement.
2. **Hooks are local state.** They aren't committed (`.git/hooks/` is not tracked). Every clone, every worktree, every CI runner needs separate hook installation. This is operational debt.
3. **Hooks break workflows.** Legitimate operations (rebasing, cherry-picking, emergency fixes) require hook bypass. A hook that must be bypassed regularly trains users to bypass it always.
4. **Hooks can't distinguish intent.** A pre-commit hook can't know whether a commit on main is a merge commit (legitimate) or a direct commit (violation). Heuristics here produce false positives.
5. **The substrate's trust model is repo write-access.** If you can commit, you're trusted. Hooks add a second trust layer that contradicts this model.
6. **`kanon gates check` provides the same signal without the problems.** The CLI command gives a definitive pass/fail that agents and CI can act on, without the fragility of hooks.

## Consequences

- Gate enforcement remains prose-based (AGENTS.md) + mechanical verification (`kanon gates check`) + post-hoc detection (audit-trail sentences, fidelity fixtures).
- Direct-to-main commits are possible. They are caught by CI (`check_process_gates.py`) and transcript review, not prevented at commit time.
- This is an intentional trade-off: we accept occasional violations in exchange for a system that never blocks legitimate work.

## References

- [ADR-0062](0062-declarative-hard-gates.md): Declarative hard gates
- [Spec: gates-check](../specs/gates-check.md): Mechanical gate evaluation CLI
