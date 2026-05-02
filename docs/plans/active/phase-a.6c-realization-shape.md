---
status: approved
slug: phase-a.6c-realization-shape
date: 2026-05-02
design: docs/design/dialect-grammar.md
---

# Plan: Phase A.6c — `_realization_shape.py` (shape parser + resolution validator)

## Why split A.6 into four sub-plans

Recap from A.6b's plan: A.6 is split into A.6a (resolutions engine, shipped #68), A.6b (dialect grammar, shipped #69), A.6c (this plan), A.6d (composition algebra). Each is a focused module per the design at [`docs/design/dialect-grammar.md`](../../design/dialect-grammar.md).

## Context

[ADR-0041](../../decisions/0041-realization-shape-dialect-grammar.md) §Decision 1 ratified the `realization-shape:` per-contract frontmatter: a contract declares which verbs, evidence-kinds, and stages a valid resolution may cite. The substrate validates resolutions against the contract's declared shape at replay time.

Per design [`docs/design/dialect-grammar.md`](../../design/dialect-grammar.md) §"Realization-shape: concrete schema":

```yaml
realization-shape:
  verbs: [lint, test, typecheck, format]
  evidence-kinds: [config-file, ci-workflow, build-script]
  stages: [commit, push, release]
  additional-properties: false
```

And the v1 dialect's verb enumeration:

```yaml
verbs:
  - lint, test, typecheck, format, scan, audit, sign, publish, report
```

A.6c authors the parser + validator. **Wiring into `_resolutions.py` replay path is deferred** to a later sub-plan (Phase A.6e or A.7), coupled with adding `realization-shape:` to actual contracts (which currently don't exist).

## Scope

### In scope

#### A. `src/kanon/_realization_shape.py` (new module, ~140 LOC)

Public surface:

```python
V1_DIALECT_VERBS: frozenset[str] = frozenset({
    "lint", "test", "typecheck", "format",
    "scan", "audit", "sign", "publish", "report",
})

@dataclass
class RealizationShape:
    verbs: frozenset[str]
    evidence_kinds: frozenset[str]
    stages: frozenset[str]
    additional_properties: bool = False

@dataclass
class ShapeValidationError:
    code: str  # one of: 'invalid-verb', 'invalid-evidence-kind',
               #         'invalid-stage', 'unknown-key'
    contract: str | None = None
    detail: str | None = None

def parse_realization_shape(
    raw: Any,
    *,
    dialect: str,
    source: str | None = None,
) -> RealizationShape:
    """Parse a contract's `realization-shape:` frontmatter block.

    Raises click.ClickException for missing/malformed shape; rejects
    verbs not in the dialect's verb enumeration.
    """

def validate_resolution_against_shape(
    realized_by: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    shape: RealizationShape,
    *,
    contract: str | None = None,
) -> list[ShapeValidationError]:
    """Check a resolution's `realized-by:` + `evidence:` against shape.

    Returns a list of structured errors (empty list = clean).
    """
```

Behaviour:
- `parse_realization_shape` validates the YAML block has the four required keys (verbs, evidence-kinds, stages); validates `verbs` is a list of v1 dialect verbs; validates `additional-properties` is bool (default False); returns a `RealizationShape` dataclass.
- `validate_resolution_against_shape` walks `realized-by` entries, checking each invocation's verb is in `shape.verbs`; walks `evidence` entries, checking each kind is in `shape.evidence_kinds` (when entry has a `kind:` field — optional in v1 spec); checks no stages outside `shape.stages` are referenced.

Per ADR-0041 §INV-dialect-grammar-shape-validates-resolutions: shape mismatches surface as ReplayError-shaped findings; A.6c returns `ShapeValidationError` (a parallel structure to ReplayError so A.6e wiring is mechanical).

#### B. `tests/test_realization_shape.py` (~180 LOC, ~16 cases)

- Parser: valid shape → RealizationShape; missing required key → raises; non-list verbs → raises; unknown verb (not in V1_DIALECT_VERBS) → raises; non-bool additional-properties → raises (with default fallback semantics)
- V1 dialect verb enumeration: presence of canonical 9 verbs
- Validator: clean resolution → empty errors; verb not in shape.verbs → 'invalid-verb' error; evidence kind not in shape.evidence_kinds → 'invalid-evidence-kind' error; multiple findings accumulate (no early exit)
- Edge cases: empty realized-by; empty evidence; missing kind: in evidence (allowed in v1)

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- **Wiring into `_resolutions.py` replay path** — deferred. Coupled with adding `realization-shape:` frontmatter to actual contracts (none exist today).
- **`_composition.py`** — A.6d.
- **CLI verbs** (`kanon contracts validate`) — A.7.
- **`additional-properties: true` semantics for forward-compat** — A.6c v1 implementation refuses unknown keys when `additional_properties=False`; the True branch is a passthrough, exercised lightly in tests.
- **Migration of existing aspect manifests to declare `realization-shape:`** — bundled with the wiring sub-plan.
- **Spec / design / ADR / principle changes** — none.

## Approach

1. Author `src/kanon/_realization_shape.py` per the design (V1 verbs constant + dataclasses + parser + validator).
2. Author `tests/test_realization_shape.py` with the ~16 cases above.
3. Run all 6 standalone gates + full pytest. Fix any regressions (none expected — additive module).
4. CHANGELOG entry.
5. Commit + push + auto-merge per "when done, merge".

## Acceptance criteria

### Module

- [ ] AC-M1: `src/kanon/_realization_shape.py` exists with `V1_DIALECT_VERBS`, `RealizationShape`, `ShapeValidationError`, `parse_realization_shape`, `validate_resolution_against_shape` symbols.
- [ ] AC-M2: `V1_DIALECT_VERBS` is a frozenset containing exactly the 9 canonical verbs (`lint`, `test`, `typecheck`, `format`, `scan`, `audit`, `sign`, `publish`, `report`).
- [ ] AC-M3: `parse_realization_shape({"verbs": ["lint"], "evidence-kinds": ["config-file"], "stages": []}, dialect="2026-05-01")` returns a `RealizationShape` instance.
- [ ] AC-M4: Parser raises `click.ClickException` for missing required keys, non-list verbs, unknown verbs.
- [ ] AC-M5: Validator returns `[]` for a clean resolution; structured `ShapeValidationError` list otherwise.

### Tests

- [ ] AC-T1: `tests/test_realization_shape.py` exercises ≥15 cases.
- [ ] AC-T2: Full pytest passes.

### CHANGELOG

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Added` gains a paragraph naming Phase A.6c.

### Cross-cutting

- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3..X7: standard gates pass (`check_links`, `check_foundations`, `check_kit_consistency`, `check_invariant_ids`, `check_packaging_split`, `check_verified_by`).
- [ ] AC-X8: No `src/kanon_reference/` change.
- [ ] AC-X9: No `_resolutions.py` integration.
- [ ] AC-X10: No CLI verb additions.

## Risks / concerns

- **Risk: speculative engineering — no contract today carries `realization-shape:`.** Mitigation: validator is exercised via direct tests with synthetic shapes. Wiring lands in a later sub-plan when contracts are migrated.
- **Risk: V1_DIALECT_VERBS hardcoded; future dialects add verbs.** Per ADR-0041 — dialect supersession is ADR-driven, not configuration. A future v2 dialect ships with its own verb set; the parser will accept a `dialect=` kwarg to choose.
- **Risk: evidence-kind enumeration is open today.** Per design §"Field semantics", the `evidence-kinds:` list is publisher-declared; A.6c doesn't enforce a substrate-side enumeration. The validator only checks that resolution `kind:` values are in the contract's declared list.

## Documentation impact

- **New files:** `src/kanon/_realization_shape.py`, `tests/test_realization_shape.py`, `docs/plans/phase-a.6c-realization-shape.md`.
- **Touched files:** `CHANGELOG.md`.
- **No changes to:** `src/kanon/_manifest.py`, `src/kanon/_resolutions.py`, `src/kanon/_dialects.py`, `src/kanon/cli.py`, `src/kanon_reference/`, aspect manifests, specs, designs, ADRs, foundations, principles, top-level `pyproject.toml`.
