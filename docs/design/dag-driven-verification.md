---
status: draft
date: 2026-05-04
implements: ADR-0061
---
# Design: DAG-Driven Verification

## Context

`_graph.py` models the full artifact DAG: 7 namespaces, 7 edge kinds, typed
dataclasses, `build_graph()` loader, precomputed inbound indices. `_verify.py`
runs validators in a flat linear sequence, each independently re-parsing
frontmatter to discover edges the graph already models. This design describes
how to unify them: the graph becomes the verification substrate.

## Architecture

### Current state (before)

```
kanon verify
  → _verify.py: linear sequence of check_* functions
  → _validators/*.py: each independently parses frontmatter
  → errors: list[str], warnings: list[str] (flat, unstructured)
  → _graph.py: unused by verify (only powers `kanon graph`)
```

### Target state (after)

```
kanon verify
  → build_graph() → GraphData (nodes, edges, indices)
  → detect_changes() → set of changed node slugs (hash store)
  → topo_walk(changed_nodes) → ordered visit sequence
  → for each visited node: dispatch node_handler(node, findings)
  → for each traversed edge: dispatch edge_handler(edge, src, dst, findings)
  → findings: list[Finding] (structured, with impact chains)
  → format_report(findings) → grouped by chain, severity-sorted
```

### Core types

```python
@dataclass(frozen=True)
class Finding:
    severity: Literal["error", "warning"]
    kind: str                    # e.g. "stale-reference", "missing-design", "body-changed"
    source_slug: str             # node that caused the finding
    source_namespace: str
    affected_slug: str | None    # downstream node affected (if relationship-based)
    affected_namespace: str | None
    chain: tuple[str, ...]       # walk path from root cause to this finding
    message: str
```

```python
# Handler signatures
NodeHandler = Callable[[Node, Path, list[Finding]], None]
EdgeHandler = Callable[[Edge, Node, Node, Path, list[Finding]], None]

# Dispatch tables
NODE_HANDLERS: dict[str, list[NodeHandler]] = {
    "plan": [check_plan_completion],
    "spec": [check_link_integrity],
    "principle": [check_link_integrity],
    "persona": [check_link_integrity],
    # ... all namespaces
}

EDGE_HANDLERS: dict[str, list[EdgeHandler]] = {
    "realizes": [check_reference_live],      # target not superseded
    "stressed_by": [check_reference_live],
    "derived-from": [check_vision_coherence], # synthetic edge, hash-based
    # ... all edge kinds
}
```

### Change detection

Hash store at `.kanon/verify-hashes.json`: maps `(namespace, slug) → sha256`.
On each run: build graph, compute current hashes, compare against stored
hashes, walk downstream from changed nodes, then update the store. Full verify
(no hash store or `--full` flag): all nodes are seeds.

### Topological walk

From each changed node, walk downstream via `GraphData.inbound_all` (or
`inbound_live` for live-only checks). Visit order is topological — a node is
visited only after all its upstream dependencies have been checked. This
ensures that a finding on a principle is emitted before the finding on the spec
that realizes it.

### Impact chains

Each `Finding` carries a `chain: tuple[str, ...]` — the walk path from
root-cause to affected node. The report groups findings by chain root:

```
IMPACT CHAIN: vision.md changed
  → P-publisher-symmetry: may need review (derived-from vision)
    → spec cli.md: realizes P-publisher-symmetry (stale reference)
      → design cli.md: implements spec with stale grounding
```

### Synthetic edges

`build_graph()` adds a synthetic `derived-from` edge from each principle to
the vision node — the one edge not discoverable from frontmatter, inferred
from the depth model.

### Migration from bespoke validators

Existing validators become thin wrappers. `plan_completion.check()` →
`check_plan_completion(node, target, findings)` (node handler).
`foundations_coherence.check()` → `check_vision_coherence(edge, src, dst,
target, findings)` (edge handler). `spec_design_parity.check()` →
`check_design_exists(edge, src, dst, target, findings)` (edge handler).

During migration, both old and new paths coexist. The old
`check(target, errors, warnings)` interface is preserved as a compatibility
shim.

### Ordering invariants

- **INV-9 (hostile-validator defense):** project validators run in a separate
  pre-pass before the graph walk. They do not participate in the DAG — they
  are sandboxed.
- **Fidelity assertions:** run in a post-pass after the graph walk.
  Capability-gated.
- **The graph walk itself** is the kit-validator pass, replacing the current
  linear sequence.

## Interfaces

### Verify output format

Structured JSON (for programmatic consumption):

```json
{
  "chains": [{
    "root": {"namespace": "vision", "slug": "vision"},
    "findings": [
      {"severity": "warning", "kind": "stale-derived", "affected": "principle/P-old"},
      {"severity": "warning", "kind": "stale-reference", "affected": "spec/cli"}
    ]
  }],
  "standalone": [
    {"severity": "error", "kind": "plan-incomplete", "source": "plan/my-plan"}
  ]
}
```

Human-readable (default): impact chains with indentation, standalone findings
listed separately.

### Handler registration

Kit handlers are registered in the dispatch tables (Python dicts in the engine
module). Aspect-contributed validators keep the `check(target, errors,
warnings)` interface and run as node handlers on a catch-all namespace.

## Decisions

1. **Graph-first verification** — `build_graph()` is the first step of
   `kanon verify`, not an optional side feature.
2. **Structured findings over flat strings** — `Finding` dataclass replaces
   `list[str]` for errors and warnings.
3. **Hash-based change detection** — incremental verify by default, `--full`
   for complete.
4. **Synthetic `derived-from` edge** for vision→principles — the one inferred
   relationship.
5. **Backward-compatible migration** — old `check()` interface preserved as
   shim during transition.

## References

- [ADR-0061](../decisions/0061-dag-driven-verification.md) — rationale
- [ADR-0058](../decisions/0058-foundations-coherence.md) — coherence validator
- [ADR-0060](../decisions/0060-foundations-review-and-impact.md) — impact validator
- `docs/specs/spec-graph-tooling.md` (deferred)
