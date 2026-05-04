---
status: draft
date: 2026-05-04
---
# ADR-0061: DAG-driven verification — the graph as verification substrate

## Context

kanon's SDD artifact stack forms an implicit DAG: vision → principles →
personas → specs → designs → plans. Each layer references the one above via
frontmatter (`realizes:`, `stressed_by:`, `implements:`, `spec:`). The
relationships are directional and acyclic — a natural graph.

The graph model already exists in `_graph.py` (shipped v0.3): 7 namespaces
(principle, persona, spec, aspect, capability, vision, plan), 7 edge kinds
(`realizes`, `serves`, `stressed_by`, `stresses`, `requires`, `serves_plan`,
`inv_ref`), typed `Node`/`Edge`/`GraphData` dataclasses, `build_graph()`
loader, and precomputed inbound indices (`inbound_all`, `inbound_live`). It
powers `kanon graph orphans` and `kanon graph rename`.

Verification (`_verify.py`) is completely disconnected from the graph. It runs
validators in a flat linear sequence. Each relationship-based validator
(`foundations_coherence`, `foundations_impact`, `spec_design_parity`)
independently re-parses frontmatter to discover the same edges the graph
already models. As the artifact stack grows, each new relationship requires a
new bespoke validator that re-discovers edges the graph already knows. This
does not scale.

The ideal architecture: the graph IS the verification substrate. Validators
become handlers registered against node types (property checks) or edge types
(relationship checks). When `kanon verify` runs, it builds the graph, detects
changes, walks downstream from changed nodes, and dispatches the appropriate
handler at each node or edge.

## Decision

Make `_graph.py` the core of `kanon verify`. The verify pipeline becomes:

1. `build_graph()` → `GraphData` (nodes, edges, indices).
2. `detect_changes()` → set of changed node slugs via hash store comparison.
3. `topo_walk(changed_nodes)` → ordered visit sequence downstream from seeds.
4. At each visited node, dispatch registered node-handlers.
5. At each traversed edge, dispatch registered edge-handlers.
6. Emit findings as structured `Finding` objects carrying impact chains.

Validators are reclassified into two types:

- **Node handlers** check properties of individual artifacts. Examples:
  `plan_completion` (checkbox state), `adr_immutability` (body-change
  detection), `index_consistency` (duplicate entries), `link_check` (URL
  resolution). These fire when their node is visited.

- **Edge handlers** check relationships between artifacts. Examples:
  `foundations_coherence` (vision→principles hash drift),
  `foundations_impact` (`realizes:`/`stressed_by:` → superseded slugs),
  `spec_design_parity` (spec→design existence). These fire when their edge
  is traversed.

The dispatch table maps `(namespace → node-handler)` and `(edge_kind →
edge-handler)`. Adding a new artifact type or relationship means adding an
entry to the dispatch table, not writing a new validator module.

Findings are structured: each carries source node, affected node, edge path
(the chain from root cause to symptom), severity (`error`/`warning`), and
kind. Impact chains are free — they are the walk path.

The vision→principles edge has no frontmatter declaration. `build_graph()`
adds a synthetic `derived-from` edge from each principle node to the vision
node. This is the one edge not discoverable from frontmatter — it is inferred
from the depth model (principles exist because vision exists).

Ordering invariants are preserved: project validators run before kit validators
(INV-9). Fidelity assertions run last (capability-gated). The topological walk
respects these constraints by running as the kit-validator pass, sandwiched
between the project pre-pass and the fidelity post-pass.

## Alternatives Considered

1. **Keep bespoke validators, add structured warnings + correlation pass.**
   Rejected: incremental improvement that does not address the root cause.
   Validators still re-discover edges the graph already models. Defers the
   ideal architecture without reducing complexity.

2. **DAG as a layer on top of validators (phased approach).** Rejected as the
   end state: layering adds indirection without simplification. Acceptable as
   a migration path but not the target architecture.

3. **Keep bespoke validators indefinitely.** Rejected: each new relationship
   requires a new validator that re-parses frontmatter. Does not scale past
   ~10 edge types.

## Consequences

- **Positive.** Single source of truth for artifact relationships (the graph).
  Adding new artifact types or relationships is a dispatch-table entry, not a
  new module. Impact chains are free. Verification is dependency-ordered, not
  linear.

- **Positive.** Existing `_graph.py` infrastructure (`build_graph`, inbound
  indices, orphan detection) is reused, not duplicated.

- **Negative.** Significant refactor of `_verify.py` and all 8+ validators.
  Migration requires both old and new paths to coexist during transition.

- **Negative.** The synthetic vision→principles edge is an inference, not a
  declared relationship. It is the one place the graph model makes an
  assumption.

## References

- `docs/specs/spec-graph-tooling.md` (deferred)
- [ADR-0058](0058-foundations-coherence.md) — foundations coherence
- [ADR-0060](0060-foundations-review-and-impact.md) — foundations review and impact
- Design doc: `docs/design/dag-driven-verification.md`
