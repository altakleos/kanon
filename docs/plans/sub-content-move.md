---
status: approved
slug: sub-content-move
date: 2026-05-02
design: docs/design/kernel-reference-interface.md
---

# Plan: Sub-plan — aspect content move (`src/kanon/kit/aspects/` → `src/kanon_reference/data/`)

## Context

Per [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md), [ADR-0044](../decisions/0044-substrate-self-conformance.md), [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md). The substrate-independence invariant requires `kanon-substrate` to ship NO aspect data; aspects must travel with `kanon_reference`. Today, the seven kanon-* aspects' protocols / files / sections / agents-md still live at `src/kanon/kit/aspects/<X>/`. This plan moves them under `src/kanon_reference/data/<X>/`.

The LOADER MANIFEST modules (`src/kanon_reference/aspects/kanon_<X>.py`) stay where they are — they hold the dict literals that mirror the YAML manifests. The DATA (protocols/.md, files/..., etc.) moves.

## Scope

### In scope

#### A. Move 42 files

For each of the 7 reference aspects, move `src/kanon/kit/aspects/<slug>/{protocols,files,sections,agents-md}/...` → `src/kanon_reference/data/<slug>/{protocols,files,sections,agents-md}/...`. The `manifest.yaml` files in the kit-side aspects directory stay (they are the source-of-truth for the LOADER MANIFEST mirroring contract per A.2.1's equivalence test); they are NOT moved here. They retire when A.6c-style validators allow the LOADER MANIFEST to be canonical. (TODO: a future sub-plan deletes them.)

Actually, simpler: move `manifest.yaml` too. The equivalence test in `tests/test_kanon_reference_manifests.py` reads from `src/kanon/kit/aspects/<slug>/manifest.yaml` — update it to read from the new location.

Final layout per aspect: `src/kanon_reference/data/<slug>/manifest.yaml`, `src/kanon_reference/data/<slug>/protocols/*.md`, etc.

#### B. Update substrate `_load_aspects_from_entry_points()`

Currently synthesizes `_source = _kit_root() / "aspects" / slug` for kanon-* aspects. After the move, point at `src/kanon_reference/data/<slug>/`:

```python
if name.startswith("kanon-"):
    # Locate the data dir alongside the kanon_reference package.
    import kanon_reference
    data_root = Path(kanon_reference.__file__).parent / "data" / name
    entry["_source"] = str(data_root)
```

#### C. Update `tests/test_kanon_reference_manifests.py` paths

Read manifest YAMLs from new location.

#### D. Recapture fidelity lock

#### E. CHANGELOG entry under `[Unreleased] § Changed`.

### Out of scope

- 9 remaining `_kit_root()` retirements in `_scaffold.py` — separate sub-plan
- `scripts/check_substrate_independence.py` gate — separate sub-plan
- Deleting `_kit_root()` entirely — happens with retirements sub-plan

## Acceptance criteria

- [ ] AC-M1: All 42 files moved from `src/kanon/kit/aspects/<X>/...` to `src/kanon_reference/data/<X>/...`
- [ ] AC-M2: `src/kanon/kit/aspects/` is empty (or contains only `manifest.yaml` for kit-globals if any)
- [ ] AC-M3: Substrate's `_load_aspects_from_entry_points()` synthesizes `_source` pointing at new data location
- [ ] AC-M4: `tests/test_kanon_reference_manifests.py` reads from new location
- [ ] AC-M5: Fidelity lock recaptured
- [ ] AC-M6: `kanon verify .` ok; full pytest passes
- [ ] AC-X1..X8: standard gates green
