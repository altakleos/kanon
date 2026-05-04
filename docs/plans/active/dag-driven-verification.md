---
status: done
date: 2026-05-04
adr: ../decisions/0061-dag-driven-verification.md
---
# Plan: DAG-driven verification (ADR-0061)

## Goal

Make _graph.py the core of kanon verify. Validators become node/edge handlers dispatched via topological walk.

## Phases

### Phase 1: Finding dataclass + handler types
- [x] Create `_findings.py` with `Finding` dataclass
- [x] Define `NodeHandler` and `EdgeHandler` Protocol classes
- [x] Define dispatch table types

### Phase 2: Synthetic edges + change detection
- [x] Add synthetic `derived-from` edges (vision→principles) to build_graph()
- [x] Create `_change_detection.py`: hash store, detect changed nodes

### Phase 3: DAG verification engine
- [x] Create `_dag_verify.py` with: build graph → detect changes → topo walk → dispatch handlers → collect findings
- [x] Implement downstream walk using GraphData.inbound_all
- [x] Implement impact chain construction during walk

### Phase 4: Migrate validators to handlers
- [x] Create `_handlers.py` with thin adapter layer over existing validators
- [x] 4 node handlers: plan_completion, index_consistency, link_check, adr_immutability
- [x] 3 edge handlers: vision_coherence, reference_live, design_exists
- [x] register_all_handlers() wires dispatch tables

### Phase 5: Wire into CLI + structured output
- [x] DAG engine runs alongside legacy pipeline (additive, try/except guarded)
- [x] INV-9 preserved: project validators still run first
- [x] Fidelity assertions still run last
- [x] Findings merged with deduplication
- [x] Backward-compatible exit codes preserved

### Phase 6: Tests
- [x] 12 tests for Finding, change detection, DAG engine, handlers, format_findings
- [x] 1003 total tests passing
- [x] Legacy _verify.py functions preserved (removal deferred to Phase 3 of Product Strategist's roadmap)

## Acceptance criteria

- [x] kanon verify builds the graph and walks it
- [x] Findings are structured with impact chains
- [x] All existing verification behavior preserved
- [x] INV-9 ordering invariant preserved
- [x] 1003 tests pass
