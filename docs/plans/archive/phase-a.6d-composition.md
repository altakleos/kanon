---
status: done
shipped-in: PR #71
slug: phase-a.6d-composition
date: 2026-05-02
design: docs/design/dialect-grammar.md
---

# Plan: Phase A.6d — `_composition.py` (topo-sort + cycle detection + replaces resolution)

## Context

Per [ADR-0041](../../decisions/0041-realization-shape-dialect-grammar.md) §Decision 3 and design [`docs/design/dialect-grammar.md`](../../design/dialect-grammar.md) §"Composition resolution algorithm". When multiple contracts target the same `surface:`, the kernel orders them via topological sort over `before:` / `after:` edges. `replaces:` substitutes one contract for another. Cycles fail loudly with explicit cycle-path reporting.

A.6d authors the algebra. **Wiring into substrate runtime** (composition at replay time) deferred — coupled with the absence of real contracts.

## Scope

### In scope

#### A. `src/kanon/_composition.py` (new module, ~190 LOC)

Public surface:

```python
@dataclass(frozen=True)
class ContractRef:
    contract_id: str
    surface: str
    before: tuple[str, ...] = ()
    after: tuple[str, ...] = ()
    replaces: tuple[str, ...] = ()

@dataclass
class CompositionError:
    code: str  # 'composition-cycle' | 'ambiguous-composition' (warning code)
    surface: str
    detail: str

def compose(contracts: list[ContractRef], surface: str) -> tuple[list[ContractRef], list[CompositionError]]:
    """Compose contracts targeting *surface* into topological order.

    Returns (ordered, findings). `findings` includes both fatal errors
    (`composition-cycle`) and warnings (`ambiguous-composition`).

    Steps per design:
      1. Filter to contracts targeting `surface`.
      2. Resolve `replaces:` substitution: replaced contracts are dropped;
         replacing contracts retain their slot.
      3. Build a directed graph from `before:` / `after:` edges.
      4. Topological sort (Kahn's algorithm with stable tie-break by
         contract_id for INV-dialect-grammar-replaces-substitution
         deterministic ordering when no edges constrain).
      5. On cycle, return CompositionError with cycle-path detail.
      6. When two contracts have no relationship, emit
         ambiguous-composition warning.
    """
```

#### B. `tests/test_composition.py` (~210 LOC, ~14 cases)

- Empty contracts → empty ordering, no findings
- Single contract → single-element ordering
- `before:` orders A before B
- `after:` (B after A) produces same ordering
- Multiple independent contracts → ambiguous-composition warning + alphabetical fallback
- Cycle (A before B, B before A) → composition-cycle error with both ids in detail
- Self-loop (A before A) → composition-cycle
- replaces: drops the replaced contract from output
- replaces: chain (A replaces B, B replaces C) handled
- replaces: cycle (A replaces B, B replaces A) → composition-cycle (treated as edge cycle)
- Surface filter: contracts with different surface are excluded
- Stable ordering: same input always produces same output

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- Wiring into substrate runtime (deferred — no contracts to compose)
- CLI verbs (A.7)
- `_manifest.py` integration

## Acceptance criteria

- [x] AC-M1: `src/kanon/_composition.py` exists with `ContractRef`, `CompositionError`, `compose` symbols
- [x] AC-M2: `compose([], surface="x")` returns `([], [])`
- [x] AC-M3: `compose` honours `before:` / `after:` edges
- [x] AC-M4: `compose` detects cycles; returns `composition-cycle` error
- [x] AC-M5: `compose` resolves `replaces:` substitution
- [x] AC-T1: ≥12 tests passing
- [x] AC-X1..X8: standard gates green; CHANGELOG updated; no other modules changed
