---
status: approved
slug: wire-dialect-pin
date: 2026-05-02
design: docs/design/dialect-grammar.md
---

# Plan: Wire `_dialects.validate_dialect_pin()` into manifest load + add `kanon-dialect:` to 7 reference manifests

## Context

Phase A.6b shipped the `_dialects.validate_dialect_pin()` function. The validator exists but isn't enforced at manifest-load time — and no aspect manifest pins `kanon-dialect:`. Per INV-dialect-grammar-pin-required, every aspect manifest MUST pin the dialect.

This plan:
1. Adds `kanon-dialect: 2026-05-01` to all 7 reference aspect manifests (both the YAML at `src/kanon_reference/data/<slug>/manifest.yaml` and the LOADER MANIFEST literal at `src/kanon_reference/aspects/kanon_<slug>.py`).
2. Wires `validate_dialect_pin()` into `_load_aspects_from_entry_points()` so aspects without a valid pin are rejected at load time.
3. Updates `tests/test_kanon_reference_manifests.py` equivalence test to include the new field.

## Scope

### In scope

#### A. Add `kanon-dialect: 2026-05-01` to 7 LOADER MANIFESTs + 7 YAMLs

For each of `kanon-deps`, `kanon-fidelity`, `kanon-release`, `kanon-sdd`, `kanon-security`, `kanon-testing`, `kanon-worktrees`:
- Add `"kanon-dialect": "2026-05-01"` to the MANIFEST dict literal in `src/kanon_reference/aspects/kanon_<slug>.py`.
- Add `kanon-dialect: "2026-05-01"` to the YAML at `src/kanon_reference/data/<slug>/manifest.yaml`.

#### B. Wire `validate_dialect_pin()` into `_load_aspects_from_entry_points()`

After the MANIFEST is loaded from an entry-point and validated for required fields, also validate the dialect pin:

```python
from kanon._dialects import validate_dialect_pin
validate_dialect_pin(entry.get("kanon-dialect"), source=ep.name)
```

Aspects without a valid pin raise `click.ClickException` at load time, blocking substrate startup if any aspect is malformed.

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- Wiring into `_load_top_manifest()` directly (delegated by the entry-point load path)
- `kanon-dialect:` pin in non-manifest contracts (separate concern)

## Acceptance criteria

- [ ] AC-M1: All 7 LOADER MANIFESTs declare `kanon-dialect: "2026-05-01"`
- [ ] AC-M2: All 7 YAML manifests declare `kanon-dialect: "2026-05-01"`
- [ ] AC-M3: `_load_aspects_from_entry_points()` invokes `validate_dialect_pin()` per entry
- [ ] AC-M4: Equivalence test passes (LOADER MANIFEST union with top-entry+sub still equals)
- [ ] AC-T1: Full pytest passes
- [ ] AC-X1..X8: standard gates green
