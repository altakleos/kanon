---
status: bootstrap
date: 2026-04-22
---
# Roadmap — Deferred Capabilities

Capabilities the design has committed to but whose implementation is scheduled for a later release. Each is tracked as a `status: deferred` spec in [`../specs/`](../specs/) so a fresh session can discover it without reference to any external plan.

Authored in Phase B of v0.1. Commit 1 ships this index with placeholder entries; Phase B writes the actual `status: deferred` specs and updates the table below.

## Deferred to v0.2+

| Spec | Capability | Source of design |
|---|---|---|
| `specs/fidelity-lock.md` | `.agent-sdd/fidelity.lock` with spec/artifact/fixture SHAs; CI refuses merge on mismatch | planning synthesis under specs-as-source frame |
| `specs/spec-graph-tooling.md` | Atomic rename across the `serves:`/`realizes:`/`fixtures:` graph; orphan detection; spec-diff rendering | specs-as-source architect |
| `specs/ambiguity-budget.md` | `agent-sdd ambiguity-budget`: two-agents-one-spec falsifier | fair adversary attack → user-adopted |
| `specs/multi-agent-coordination.md` | `docs/.coordination/reservations.yaml`; plan frontmatter `spec-sha:`/`write-set:`; `[?]` task state | multi-agent architect |
| `specs/expand-and-contract-lifecycle.md` | Named lifecycle for non-additive spec changes (add, migrate, remove) | methodology research (Pact) |
| `specs/invariant-ids.md` | Stable per-invariant anchors + `verified_by:` references (optional in v0.1, required later) | reader-first designer |
