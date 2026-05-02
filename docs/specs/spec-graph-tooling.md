---
status: superseded
date: 2026-04-22
realizes:
  - P-specs-are-source
  - P-cross-link-dont-duplicate
target-release: v0.2
superseded-by:
  - docs/specs/spec-graph-rename.md
  - docs/specs/spec-graph-orphans.md
  - docs/specs/spec-graph-diff.md
superseded-date: 2026-04-25
---
# Spec: Spec-graph tooling — rename, orphan detection, spec-diff (SUPERSEDED)

> **Superseded 2026-04-25.** This umbrella spec bundled three independent capabilities (rename, orphan detection, invariant-level diff) into one. A multi-lens panel review found that the bundle hid material differences in implementation cost, failure modes, and consumer demand: rename is high-stakes and consequential; orphans is read-only and small; diff is the long pole. The umbrella has been split into three independent specs:
>
> - [`spec-graph-rename.md`](spec-graph-rename.md) — `status: draft`, target v0.3. Atomic slug rename with `--type` discriminator and ops-manifest extension to ADR-0024.
> - [`spec-graph-orphans.md`](spec-graph-orphans.md) — `status: draft`, target v0.3. Read-only report with `orphan-exempt:` opt-out; deferred specs excluded from the live graph.
> - [`spec-graph-diff.md`](spec-graph-diff.md) — `status: deferred`, target v0.3+. Anchor-keyed diff (depends on `invariant-ids.md`); ancestor-required ordering. Refined to draft-grade rigor for promotion later.
>
> The original text below is preserved for archaeology. Do not promote this spec; the three replacements own the contract.

## Intent

Treat the cross-link graph (`serves:`, `realizes:`, `stressed_by:`, `fixtures:`, `verified_by:` slugs) as a typed graph and provide tools that operate on it atomically: rename a slug across every file that references it, detect orphans (principles no spec `realizes:`; specs no plan `serves:`), and render spec-diffs at the invariant level (not the prose-paragraph level).

## Problem

Sensei has experienced manual rename pain. A principle rename today means `grep -r <old-slug>` + hand-editing 10+ files, with no atomicity guarantee and no validator to catch misses. Orphan principles accumulate silently because nothing flags them. Spec diffs today are markdown diffs — showing prose changes — when what the reviewer cares about is invariant changes.

## Sketched invariants

1. `kanon graph rename <old-slug> <new-slug>` does one atomic filesystem transaction: every file that cites the slug (in frontmatter or prose) is updated, the change is atomic, and `scripts/check_foundations.py` passes after.
2. `kanon graph orphans` emits a report: principles without any inbound `realizes:`/`serves:` references, specs without any inbound plan `serves:`, etc. Configurable thresholds (warn after N releases, fail after M).
3. `kanon graph diff <old-sha> <new-sha>` shows invariant-level changes — bullet-by-bullet additions/removals in each spec's Invariants section — not prose-level changes.
4. Integration with the fidelity-lock (above) so a spec-graph change can update the lock mechanically.

## Out of Scope in v0.1

All of it. Spec-graph tooling makes the kit qualitatively more powerful for platform-scale adopters; v0.1 ships the prose conventions (cross-linking, frontmatter) without the mechanical manipulation tools.

## Why deferred

Real engineering effort; touches frontmatter parsing across 6+ artifact types; requires design doc work. Appropriate for a v0.2 plan of its own after v0.1 proves the method's core claims.

## References

- Design synthesis (specs-as-source architect).
