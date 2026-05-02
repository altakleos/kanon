---
status: approved
slug: wire-realization-shape
date: 2026-05-02
design: docs/design/dialect-grammar.md
---

# Plan: Wire realization-shape validation into `_resolutions.replay()`

## Context

Phase A.6c shipped the realization-shape parser + validator (`_realization_shape.py`); A.6a shipped the resolutions replay engine (`_resolutions.py`). The engines exist but are not connected — `replay()` executes pin checks but never validates the resolution against the contract's declared shape (per INV-dialect-grammar-shape-validates-resolutions).

This plan wires them: between the pin-check phase and the execution phase, `replay()` now reads the contract file's frontmatter, looks for a `realization-shape:` block, parses it via `parse_realization_shape()`, and validates the resolution's `realized-by` + `evidence` via `validate_resolution_against_shape()`. Findings surface as `ReplayError` entries with the appropriate codes (`invalid-verb`, `invalid-evidence-kind`, `invalid-stage`, `unknown-key`).

**Skip-when-absent semantics:** today's reference contracts don't declare `realization-shape:` blocks. When the block is absent from a contract's frontmatter, `replay()` silently skips shape validation for that contract (no error). Contracts that DO declare the block (synthetic test fixtures; future `acme-` publishers) get validated.

## Scope

### In scope

#### A. `src/kanon/_resolutions.py` — wire shape validation

Add a new helper `_validate_shape_against_contract(contract_id, contract_path, entry, errors)` invoked between `_check_pins()` and `_execute_realizations()`:

```python
def _validate_shape_against_contract(
    contract_id: str,
    contract_path: Path,
    entry: dict[str, Any],
    errors: list[ReplayError],
) -> None:
    """Read contract frontmatter; if realization-shape declared, validate."""
    text = contract_path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    if "realization-shape" not in frontmatter:
        return  # skip-when-absent
    dialect = frontmatter.get("kanon-dialect", "2026-05-01")  # default v1
    try:
        shape = parse_realization_shape(
            frontmatter["realization-shape"], dialect=dialect, source=contract_id
        )
    except click.ClickException as exc:
        errors.append(
            ReplayError(
                code="invalid-realization-shape",
                contract=contract_id,
                reason=exc.message,
            )
        )
        return
    findings = validate_resolution_against_shape(
        realized_by=entry.get("realized-by") or [],
        evidence=entry.get("evidence") or [],
        shape=shape,
        contract=contract_id,
    )
    for f in findings:
        errors.append(
            ReplayError(code=f.code, contract=f.contract, reason=f.detail)
        )
```

Plus a tiny `_parse_frontmatter` helper that extracts the YAML block between `---` fences (or returns `{}` if absent — substrate's `_manifest._parse_frontmatter` exists; reuse).

Hook the helper into `_replay_inner` after `_check_pins()` succeeds.

#### B. `tests/test_resolutions.py` — add ~5 new test cases

- Contract WITHOUT `realization-shape:` → skip-when-absent (no findings)
- Contract WITH `realization-shape:` and clean resolution → no findings
- Contract WITH `realization-shape:` and invalid verb in resolution → `invalid-verb` finding
- Contract WITH `realization-shape:` and invalid evidence-kind → `invalid-evidence-kind` finding
- Contract WITH malformed `realization-shape:` → `invalid-realization-shape` finding

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- Adding `realization-shape:` to actual reference aspect contracts (no contracts have frontmatter today; that's a separate sub-plan)
- Dialect-pin enforcement at contract load time (item #2 of this autopilot batch)

## Acceptance criteria

- [ ] AC-M1: `_resolutions.py` exposes `_validate_shape_against_contract` and calls it from `_replay_inner` after pin-check
- [ ] AC-M2: Skip-when-absent: contracts without `realization-shape:` produce no shape findings
- [ ] AC-M3: Shape violations surface as `ReplayError` with the appropriate code
- [ ] AC-T1: ≥5 new tests passing
- [ ] AC-X1..X8: standard gates green; full pytest no regression
