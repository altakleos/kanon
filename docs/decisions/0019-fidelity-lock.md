---
status: accepted
date: 2026-04-24
---
# ADR-0019: Fidelity Lock — spec-SHA drift detection

## Context

Specs change over time but there is no mechanism to detect when a spec has drifted from its last verification checkpoint. Drift between specs and tests accumulates silently.

## Decision

1. A lock file at `.kanon/fidelity.lock` (YAML) records SHA-256 of each accepted/draft spec.
2. `kanon fidelity update` generates/refreshes the lock.
3. `kanon verify` at SDD depth ≥ 2 warns on stale SHAs if the lock exists.
4. Phase 1: spec-SHA only. Phase 2 (after verified-by): fixture and artifact SHAs.
5. Core feature, not an aspect. Opt-in via lock file presence.

## Alternatives Considered

**Full artifact tracking in Phase 1.** Rejected — requires verified-by mapping which is deferred to v0.3.
**Per-spec lock files.** Rejected — one file is simpler to manage and diff.

## Consequences

- New CLI command: `kanon fidelity update`.
- `kanon verify` gains fidelity checks at depth ≥ 2.
- `.kanon/fidelity.lock` committed to version control.

## References

- [Spec: Fidelity Lock](../specs/fidelity-lock.md)
- [Spec: Verified-By](../specs/verified-by.md) — enables Phase 2
