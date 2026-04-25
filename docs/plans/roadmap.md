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
| [`specs/spec-graph-tooling.md`](../specs/spec-graph-tooling.md) | (Umbrella — atomic rename, orphan detection, spec-diff.) | **Superseded** 2026-04-25; split into three specs (see v0.3 row below) |
| [`specs/ambiguity-budget.md`](../specs/ambiguity-budget.md) | `kanon ambiguity-budget`: two-agents-one-spec falsifier. | Deferred |
| [`specs/multi-agent-coordination.md`](../specs/multi-agent-coordination.md) | Reservations ledger, plan SHA pins, decision handshake, sub-agent AGENTS.md inheritance. | Deferred |
| [`specs/invariant-ids.md`](../specs/invariant-ids.md) | Stable per-invariant anchors + `verified_by:` references. | **Shipped** (v0.2.0a4) |

## Drafted for v0.3 (work in flight)

| Spec | Capability | Status |
|---|---|---|
| [`specs/spec-graph-rename.md`](../specs/spec-graph-rename.md) | `kanon graph rename` — atomic slug rename with `--type` discriminator and ops-manifest extension to ADR-0024; frontmatter-only scope. | Draft |
| [`specs/spec-graph-orphans.md`](../specs/spec-graph-orphans.md) | `kanon graph orphans` — read-only orphan report with `orphan-exempt:` opt-out; provides the `_graph.py` primitive for future `consumers-of`. | Draft |

## Deferred to v0.3+

| Spec | Capability |
|---|---|
| [`specs/spec-graph-diff.md`](../specs/spec-graph-diff.md) | `kanon graph diff` — invariant-level diff between two snapshots, keyed by `INV-*` anchors, ancestor-required ordering. Long pole; depends on the `_graph.py` primitive landing first. |
| [`specs/expand-and-contract-lifecycle.md`](../specs/expand-and-contract-lifecycle.md) | Named lifecycle for breaking spec changes (expand → migrate → contract). Unblocked by `spec-graph-orphans.md`'s graph-load primitive (which provides the `consumers-of` data structure). |

## How deferred specs graduate

`status: deferred` → `status: draft` (work begins) → `status: accepted` (capability ships). Each graduation is its own plan in `docs/plans/`. Deferred specs do not land in `status: accepted` directly — the `draft` stage ensures the design is revisited under current context, not under whatever assumptions held when the spec was first authored.
