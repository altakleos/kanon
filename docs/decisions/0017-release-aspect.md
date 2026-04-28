---
status: accepted
date: 2026-04-24
---
# ADR-0017: Release aspect — disciplined release publishing

## Context

kanon's own release process is manual knowledge encoded in CI workflows. As the kit ships more aspects and targets more consumers, release discipline should be packageable like any other development discipline.

## Decision

Ship `release` as a standalone aspect with:

1. **Depth range 0–2.** Depth 0 = opt-out. Depth 1 = prose guidance (protocol + AGENTS.md section). Depth 2 = prose + automation (CI template + preflight script).
2. **No cross-aspect dependency.** `requires: []`. Release discipline is independently useful without SDD ceremony.
3. **Scaffolding shape.** Protocol at `.kanon/protocols/kanon-release/release-checklist.md`. AGENTS.md section `release/publishing-discipline`. CI files at `ci/release-preflight.py` and `.github/workflows/release.yml` (depth-2 only, copy-in templates, no byte-equality enforcement).
4. **Stability: experimental.** Until self-hosted and validated.

## Alternatives Considered

**Require sdd >= 1.** Rejected. Release discipline is independently useful. Forcing plan-before-build for release automation creates an adoption barrier.

**Binary depth (0–1).** Rejected. The knowledge layer (protocol) and automation layer (CI templates) are independently useful. A GitLab CI user wants the checklist without GitHub Actions templates.

## Consequences

- New aspect directory `src/kanon/kit/aspects/release/` added to the kit bundle.
- Top-level `manifest.yaml` gains a `release` entry.
- Third shipping aspect after `sdd` and `worktrees`.

## References

- [Spec: Release](../specs/release.md)
- [ADR-0013: Vision amendment — reference automation](0013-vision-amendment-reference-automation.md)
- [Spec: Aspects](../specs/aspects.md)
