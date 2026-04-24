---
status: accepted
date: 2026-04-24
---
# ADR-0021: Testing aspect — test discipline for LLM-agent-driven repos

## Context

LLM agents default to implementation-first and optimize for "tests pass" rather than "tests protect." Without explicit discipline, agents silently delete failing tests, weaken assertions, and skip edge cases. Research shows tests-as-stopping-conditions significantly improve LLM code generation quality (9-29% improvement per Mathews & Nagappan 2024, 94.3% pass rate with human-written tests per TDFlow 2025).

## Decision

1. **Depth range 0–3.** Depth 0 = opt-out. Depth 1 = test discipline (tests accompany code, no silent deletion, prefer test-first). Depth 2 = AC-first + TDD (translate plan acceptance criteria into failing tests before implementation; red-green-refactor for spec invariants). Depth 3 = automated enforcement (CI validator for test anti-patterns).
2. **No cross-aspect dependency.** `requires: []`, `suggests: ["sdd >= 1"]`. Testing works standalone; gets better with SDD.
3. **Language-agnostic at all depths.** Protocols describe principles, not framework commands.
4. **Coverage floor in config.** `aspects.testing.config.coverage_floor` (default 80).
5. **Two protocols.** `test-discipline.md` (depth 1) and `ac-first-tdd.md` (depth 2).
6. **Stability: experimental.**

## Alternatives Considered

**Strict TDD mandate.** Rejected — over-prescribes for config/prose/UI work. "Prefer test-first" captures the design benefit without blocking legitimate workflows.
**Depth 0–2 (merge TDD into depth 1).** Rejected — test-alongside and AC-first+TDD are genuinely different layers of discipline with different adoption costs.
**Language-specific scaffolding at depth 3.** Rejected — kanon is portable across languages.

## Consequences

- New aspect directory `src/kanon/kit/aspects/testing/`.
- Fourth shipping aspect after sdd, worktrees, release.
- First aspect to use the `config:` block (`coverage_floor`).
- First aspect to use `suggests:` field.

## References

- [Spec: Testing](../specs/testing.md)
- [ADR-0013: Vision amendment — reference automation](0013-vision-amendment-reference-automation.md)
- [Spec: Verified-By](../specs/verified-by.md)
