---
status: deferred
date: 2026-04-22
realizes:
  - P-specs-are-source
target-release: v0.3
---
# Spec: Expand-and-contract lifecycle — named pattern for breaking spec changes

## Intent

Provide a named, documented pattern for changing a spec invariant in a way that breaks downstream consumers (other specs referencing it, tests verifying it, implementation depending on it). Borrowed from Pact's consumer-driven-contract testing lifecycle.

## Problem

The kit has no named lifecycle for breaking spec changes. When an invariant must change incompatibly, the naive path is (a) edit the invariant, (b) fix everything that broke, (c) merge. This tempts authors to write backward-incompatible changes without migration runbooks, producing "spec revision broke three consumers" incidents.

## Sketched invariants

1. **Three-phase lifecycle.** Expand (add the new invariant alongside the old), migrate (update every downstream consumer to satisfy the new invariant), contract (remove the old invariant). Each phase is a separate commit set.
2. **Expand phase.** The new invariant is added to the spec with `status: expanding` (a new per-invariant status, distinct from spec-level status). The old invariant remains marked `deprecating: true` with a deadline.
3. **Migrate phase.** Downstream consumers update to satisfy the new invariant. The kit provides a query: `kanon consumers-of <spec>` lists dependents.
4. **Contract phase.** After the deadline, the old invariant is removed. `kanon verify` fails on any consumer still depending on the removed invariant.
5. **Validator support.** `ci/check_foundations.py` learns to respect `expanding`/`deprecating` invariants.

## Out of Scope in v0.1 and v0.2

All of it. This is the latest-target spec in v0.1's roadmap because it requires a mature graph-tooling foundation (`spec-graph-tooling.md`, also deferred) to be practical.

## Why deferred

Depends on spec-graph-tooling (for `consumers-of`) and on the invariant-IDs convention (`invariant-ids.md`, also deferred). Both need to land first. Realistic target: v0.3.

## References

- Methodology researcher report — Pact as the prior art.
