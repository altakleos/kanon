---
status: done
shipped-in: PR #69
slug: phase-a.6b-dialect-module
date: 2026-05-02
design: docs/design/dialect-grammar.md
---

# Plan: Phase A.6b — `_dialects.py` module (supported-dialect registry + pin validation)

## Why split A.6 into four sub-plans

Re-examining the design at [`docs/design/dialect-grammar.md`](../../design/dialect-grammar.md), the implementation footprint names FOUR new modules: `_dialects.py` (~60 LOC), `_realization_shape.py` (~120 LOC), `_composition.py` (~150 LOC), plus extensions to `_manifest.py`, `_resolutions.py`, and `cli.py`. Combined with A.6a's `_resolutions.py`, the total Phase A.6 work is ~+800 LOC source + ~+250 LOC tests across ~15 files. Splitting at module boundaries:

- **A.6a (shipped, PR #68):** `_resolutions.py` — engine, replay, canonicalization
- **A.6b (this plan):** `_dialects.py` — supported-dialect registry + pin validation
- **A.6c (next plan):** `_realization_shape.py` — shape parser + resolution validator
- **A.6d (next plan):** `_composition.py` — topo-sort + cycle detection + replaces resolution

This plan covers A.6b only. It is the smallest of the four — a single focused module.

## Context

Phase 0 ratified [ADR-0041](../../decisions/0041-realization-shape-dialect-grammar.md): the substrate's contract grammar — what *shape* aspect manifests and contracts must conform to. Three coupled commitments: realization-shape, dialect grammar, composition algebra. A.6b implements **just the dialect-grammar enforcement**: a supported-dialect registry the substrate ships and a `validate_dialect_pin()` function that the substrate's load path will invoke (in a later sub-plan) when reading aspect manifests.

Per design [`docs/design/dialect-grammar.md`](../../design/dialect-grammar.md) §"Substrate-side dialect registry":

```python
SUPPORTED_DIALECTS = ["2026-05-01"]
DEPRECATION_WARNING_BEFORE = []  # nothing deprecated yet

def validate_dialect_pin(manifest_dialect: str) -> None:
    if manifest_dialect not in SUPPORTED_DIALECTS:
        raise UnknownDialectError(...)
    if manifest_dialect in DEPRECATION_WARNING_BEFORE:
        warnings.warn(...)
```

A.6b authors that module + tests. **Wiring into `_manifest.py` load-time validation is deferred to a later sub-plan** — coupled with adding `kanon-dialect:` to actual aspect manifests, which is a separate concern.

## Scope

### In scope

#### A. `src/kanon/_dialects.py` (new module, ~80 LOC)

Public surface:

```python
SUPPORTED_DIALECTS: tuple[str, ...] = ("2026-05-01",)
DEPRECATION_WARNING_BEFORE: tuple[str, ...] = ()  # no dialect deprecated yet

def validate_dialect_pin(
    manifest_dialect: str | None,
    *,
    source: str | None = None,
) -> None:
    """Validate a manifest's `kanon-dialect:` pin against supported dialects.

    Raises click.ClickException for missing or unknown pins.
    Emits a stderr deprecation warning when the pin matches a soon-to-be-retired
    dialect (per INV-dialect-grammar-version-format).

    `source` is an optional human-readable label (e.g., aspect slug) for
    error messages.
    """
```

Per the design, the dialect-pin format follows INV-dialect-grammar-pin-required + INV-dialect-grammar-version-format from [`docs/specs/dialect-grammar.md`](../../specs/dialect-grammar.md). The format is `YYYY-MM-DD`; A.6b validates that the value is in `SUPPORTED_DIALECTS` (an exact-match check; ADR-0041 ratifies date-stamped pinning, not range-matching).

#### B. `tests/test_dialects.py` (~120 LOC, ~10 cases)

- INV-dialect-grammar-pin-required: missing pin raises ClickException
- INV-dialect-grammar-version-format: pin must match a supported dialect string
- Supported dialect passes silently
- Unknown dialect raises with a helpful error naming `SUPPORTED_DIALECTS`
- Deprecation warning fires when `manifest_dialect in DEPRECATION_WARNING_BEFORE` (use monkeypatch to inject a deprecated dialect)
- `source` label appears in error messages
- Empty / None pin raises with the missing-pin error code
- Future-format pin (e.g., `2099-01-01`) raises (not in SUPPORTED_DIALECTS)
- Past-format pin (e.g., `2025-01-01`) raises (not in SUPPORTED_DIALECTS)
- Malformed pin (e.g., `not-a-date`) raises (not in SUPPORTED_DIALECTS — substrate doesn't try to parse format; missing-from-allowlist suffices)

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- **Wiring `validate_dialect_pin()` into `_manifest.py` load path.** Deferred until a later sub-plan; coupled with adding `kanon-dialect:` to actual aspect manifests (which currently don't carry it).
- **`_realization_shape.py`** — A.6c.
- **`_composition.py`** — A.6d.
- **`kanon contracts validate` CLI verb** — A.7.
- **Migration of existing kit-side manifests to add `kanon-dialect:`** — bundled with the load-time wiring sub-plan.
- **Spec / design / ADR / principle changes** — none.

## Approach

1. Author `src/kanon/_dialects.py` per the design (registry constants + `validate_dialect_pin` function).
2. Author `tests/test_dialects.py` with the ~10 cases above.
3. Run all 6 standalone gates + full pytest. Fix any regressions (none expected — additive module).
4. CHANGELOG entry under `[Unreleased] § Added`.
5. Commit + push + auto-merge per "when done, merge".

## Acceptance criteria

### Module

- [x] AC-M1: `src/kanon/_dialects.py` exists with `SUPPORTED_DIALECTS`, `DEPRECATION_WARNING_BEFORE`, `validate_dialect_pin` symbols.
- [x] AC-M2: `SUPPORTED_DIALECTS` contains `"2026-05-01"` (the ratified v1 dialect per ADR-0041).
- [x] AC-M3: `DEPRECATION_WARNING_BEFORE` is empty (no current deprecations).
- [x] AC-M4: `validate_dialect_pin("2026-05-01")` succeeds (no exception, no warning).
- [x] AC-M5: `validate_dialect_pin("unknown")` raises `click.ClickException` with text including the supported list.
- [x] AC-M6: `validate_dialect_pin(None)` raises `click.ClickException` ("missing pin").
- [x] AC-M7: When `DEPRECATION_WARNING_BEFORE` contains the pin (test via monkeypatch), a stderr warning fires.

### Tests

- [x] AC-T1: `tests/test_dialects.py` exercises ≥10 cases covering the 6 invariants.
- [x] AC-T2: Full pytest passes.

### CHANGELOG

- [x] AC-X1: `CHANGELOG.md` `[Unreleased] § Added` gains a paragraph naming Phase A.6b.

### Cross-cutting

- [x] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [x] AC-X3..X7: standard gates pass (`check_links`, `check_foundations`, `check_kit_consistency`, `check_invariant_ids`, `check_packaging_split`, `check_verified_by`).
- [x] AC-X8: No `src/kanon_reference/` change.
- [x] AC-X9: No CLI verb additions.
- [x] AC-X10: No `_manifest.py` integration (deferred).

## Risks / concerns

- **Risk: speculative engineering — no manifest currently pins `kanon-dialect:`.** Mitigation: A.6b ships the validator; wiring lands in a later sub-plan when manifests are migrated. The validator is exercised via direct tests.
- **Risk: deprecation logic is currently dead code (DEPRECATION_WARNING_BEFORE is empty).** Mitigation: tested via monkeypatch; activated when the substrate ships its first dialect supersession (per ADR-0041 cadence).
- **Risk: the registry is hardcoded; future dialects require source edits.** This is intentional per ADR-0041 — dialect supersession is an ADR-driven event, not configuration.

## Documentation impact

- **New files:** `src/kanon/_dialects.py`, `tests/test_dialects.py`, `docs/plans/phase-a.6b-dialect-module.md`.
- **Touched files:** `CHANGELOG.md`.
- **No changes to:** `src/kanon/_manifest.py`, `src/kanon/_resolutions.py`, `src/kanon/cli.py`, `src/kanon_reference/`, aspect manifests, specs, designs, ADRs, foundations, principles, top-level `pyproject.toml`.
