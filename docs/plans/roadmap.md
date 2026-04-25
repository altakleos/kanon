---
status: accepted
date: 2026-04-22
---
# Roadmap — Deferred Capabilities

Capabilities committed to but not yet shipped. Each is tracked as a `status: deferred` spec in [`../specs/`](../specs/) so a fresh session can discover it without reference to any external plan.

## Deferred to v0.2

| Spec | Capability | Status |
|---|---|---|
| [`specs/fidelity-lock.md`](../specs/fidelity-lock.md) | `.kanon/fidelity.lock` — spec/artifact/fixture SHAs; CI refuses merge on mismatch. | **Shipped** (v0.2.0a4) |
| [`specs/spec-graph-tooling.md`](../specs/spec-graph-tooling.md) | Atomic rename across the `serves:`/`realizes:`/`fixtures:` graph; orphan detection; spec-diff rendering. | Deferred |
| [`specs/ambiguity-budget.md`](../specs/ambiguity-budget.md) | `kanon ambiguity-budget`: two-agents-one-spec falsifier. | Deferred |
| [`specs/multi-agent-coordination.md`](../specs/multi-agent-coordination.md) | Reservations ledger, plan SHA pins, decision handshake, sub-agent AGENTS.md inheritance. | Deferred |
| [`specs/invariant-ids.md`](../specs/invariant-ids.md) | Stable per-invariant anchors + `verified_by:` references. | **Shipped** (v0.2.0a4) |

## Deferred to v0.3+

| Spec | Capability |
|---|---|
| [`specs/expand-and-contract-lifecycle.md`](../specs/expand-and-contract-lifecycle.md) | Named lifecycle for breaking spec changes (expand → migrate → contract). |

## How deferred specs graduate

`status: deferred` → `status: draft` (work begins) → `status: accepted` (capability ships). Each graduation is its own plan in `docs/plans/`. Deferred specs do not land in `status: accepted` directly — the `draft` stage ensures the design is revisited under current context, not under whatever assumptions held when the spec was first authored.
