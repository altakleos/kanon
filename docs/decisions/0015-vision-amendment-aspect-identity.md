---
status: accepted
date: 2026-04-23
---
# ADR-0015: Vision amendment — aspect-oriented identity

## Context

The vision document (`docs/foundations/vision.md`) defines kanon through three properties: Portable, Tiered, Self-hosting. With the aspect model (ADR-0012) shipping in v0.2, "Tiered" is no longer the kit's organizing principle — tiers are now a depth dial on the `sdd` aspect. The vision's Current Promises and Success Criteria sections are also v0.1-only and don't reflect the aspect model or the `worktrees` aspect.

Per the foundations' immutability-with-trail convention, vision amendments are documented via ADR and tracked in an amendment trail.

## Decision

Amend three sections of `docs/foundations/vision.md`:

1. **§What kanon Is** — replace "Tiered" (property #2) with "Aspect-oriented." Update the self-hosting property to reference both `sdd:3` and `worktrees:2`.
2. **§Current Promises** — add aspect-based opt-in, worktree isolation, and non-destructive aspect lifecycle. Retain cross-harness, verification, and model-version promises.
3. **§Success Criteria** — split into v0.1 (achieved) and v0.2 (in progress). Add aspect-model and worktrees criteria.

Leave §Why It Exists, §Design Stance, and §Non-Goals untouched — they remain accurate.

## Alternatives Considered

**Leave the vision as-is.** Rejected. The vision is step 0 in the AGENTS.md boot chain. Every agent session starts with a stale frame that describes kanon as a "tiered SDD kit" when it is now a multi-aspect discipline kit. The framing error compounds across sessions.

**Full rewrite.** Rejected. The philosophy sections (Why It Exists, Design Stance, Non-Goals) are still accurate. A full rewrite risks losing the founding document's archaeological value.

## Consequences

- The vision doc's identity sections now match the accepted aspects spec (ADR-0012) and worktrees spec.
- The amendment trail at the bottom of vision.md tracks both ADR-0013 and this ADR.
- Future vision amendments follow the same pattern: ADR + amendment trail entry.

## References

- [Vision](../foundations/vision.md)
- [ADR-0012: Aspect model](0012-aspect-model.md)
- [ADR-0013: Vision amendment — reference automation](0013-vision-amendment-reference-automation.md)
- [ADR-0014: Worktrees aspect](0014-worktrees-aspect.md)
