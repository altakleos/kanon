---
status: in-progress
date: 2026-05-04
adr: ../decisions/0061-dag-driven-verification.md
---
# Plan: DAG-driven verification (ADR-0061)

## Goal

Make _graph.py the core of kanon verify. Validators become node/edge handlers dispatched via topological walk.

## Phases

### Phase 1: Finding dataclass + handler types
- [ ] Create `_findings.py` with `Finding` dataclass (severity, kind, source_slug, source_namespace, affected_slug, affected_namespace, chain, message)
- [ ] Define `NodeHandler` and `EdgeHandler` type aliases
- [ ] Define dispatch table types

### Phase 2: Synthetic edges + change detection
- [ ] Add synthetic `derived-from` edges (vision→principles) to build_graph()
- [ ] Create hash store module: compute node hashes, store/load from `.kanon/verify-hashes.json`, detect changed nodes

### Phase 3: DAG verification engine
- [ ] Create `_dag_verify.py` with: build graph → detect changes → topo walk → dispatch handlers → collect findings
- [ ] Implement topological walk using GraphData.inbound_all
- [ ] Implement impact chain construction during walk

### Phase 4: Migrate validators to handlers
- [ ] plan_completion → node handler (plan namespace)
- [ ] index_consistency → node handler (all namespaces with READMEs)
- [ ] link_check → node handler (all namespaces)
- [ ] adr_immutability → node handler (spec namespace, ADR subset)
- [ ] foundations_coherence → edge handler (derived-from edge kind)
- [ ] foundations_impact → edge handler (realizes/stressed_by edge kinds)
- [ ] spec_design_parity → edge handler (implements edge kind)
- [ ] test_import_check → node handler (kept as-is, non-SDD)

### Phase 5: Wire into CLI + structured output
- [ ] Replace linear verify() pipeline with DAG engine call
- [ ] Preserve INV-9: project validators run in pre-pass
- [ ] Preserve fidelity assertions in post-pass
- [ ] Format findings as impact chains (human-readable default)
- [ ] Backward-compatible exit codes (1 on errors, 0 on clean)

### Phase 6: Tests + cleanup
- [ ] Update test_cli_verify.py for new output format
- [ ] Update test_verify_validators.py for handler signatures
- [ ] Add tests for Finding, topo walk, impact chains, change detection
- [ ] Remove old _verify.py functions replaced by DAG engine
- [ ] All tests pass

## Acceptance criteria

- kanon verify builds the graph and walks it
- Findings are structured with impact chains
- All existing verification behavior preserved
- INV-9 ordering invariant preserved
- All tests pass
