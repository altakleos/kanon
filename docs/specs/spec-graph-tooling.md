---
status: deferred
date: 2026-04-22
realizes:
  - P-specs-are-source
  - P-cross-link-dont-duplicate
target-release: v0.2
---
# Spec: Spec-graph tooling — rename, orphan detection, spec-diff

## Intent

Treat the cross-link graph (`serves:`, `realizes:`, `stressed_by:`, `fixtures:`, `verified_by:` slugs) as a typed graph and provide tools that operate on it atomically: rename a slug across every file that references it, detect orphans (principles no spec `realizes:`; specs no plan `serves:`), and render spec-diffs at the invariant level (not the prose-paragraph level).

## Problem

Sensei has experienced manual rename pain. A principle rename today means `grep -r <old-slug>` + hand-editing 10+ files, with no atomicity guarantee and no validator to catch misses. Orphan principles accumulate silently because nothing flags them. Spec diffs today are markdown diffs — showing prose changes — when what the reviewer cares about is invariant changes.

## Sketched invariants

1. `agent-sdd graph rename <old-slug> <new-slug>` does one atomic filesystem transaction: every file that cites the slug (in frontmatter or prose) is updated, the change is atomic, and `ci/check_foundations.py` passes after.
2. `agent-sdd graph orphans` emits a report: principles without any inbound `realizes:`/`serves:` references, specs without any inbound plan `serves:`, etc. Configurable thresholds (warn after N releases, fail after M).
3. `agent-sdd graph diff <old-sha> <new-sha>` shows invariant-level changes — bullet-by-bullet additions/removals in each spec's Invariants section — not prose-level changes.
4. Integration with the fidelity-lock (above) so a spec-graph change can update the lock mechanically.

## Out of Scope in v0.1

All of it. Spec-graph tooling makes the kit qualitatively more powerful for platform-scale adopters; v0.1 ships the prose conventions (cross-linking, frontmatter) without the mechanical manipulation tools.

## Why deferred

Real engineering effort; touches frontmatter parsing across 6+ artifact types; requires design doc work. Appropriate for a v0.2 plan of its own after v0.1 proves the method's core claims.

## References

- Design synthesis (specs-as-source architect).
