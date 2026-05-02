---
status: approved
slug: phase-a.2.1-loader-package
date: 2026-05-01
design: docs/design/kernel-reference-interface.md
---

# Plan: Phase A.2.1 — `kanon_reference` package + LOADER stubs (additive)

## Why split A.2 in two

[ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) ratifies the kernel/reference runtime interface; the design at [`docs/design/kernel-reference-interface.md`](../design/kernel-reference-interface.md) sizes Phase A.2 at ~+450 LOC source / -80 LOC source / +150 LOC tests across ~12 files. That's too large for one review-friendly PR. Splitting at the natural seam between *additive* and *substractive* work:

- **A.2.1 (this plan):** Author the `kanon_reference` Python package, the seven LOADER (`MANIFEST`) stubs, and uncomment the entry-points block in `packaging/reference/pyproject.toml`. Pure addition. The substrate's runtime is unchanged. `_kit_root()` still loads from `src/kanon/kit/aspects/`. Self-host trivially stays green.
- **A.2.2 (next plan):** Substrate `_load_aspect_registry()` rewrite, `_kit_root()` retirement (11 call sites in `_manifest.py` + `_scaffold.py`), namespace-ownership validator, and `scripts/check_substrate_independence.py` gate. Substractive + risky.

This plan covers A.2.1 only.

## Context

Phase A.1 (PR #61) shipped the three skeleton `pyproject.toml` files. `packaging/reference/pyproject.toml` ships the entry-points block as commented-out stubs:

```toml
# Activated by Phase A.2 — see docs/design/kernel-reference-interface.md.
# [project.entry-points."kanon.aspects"]
# kanon-deps = "kanon_reference.aspects.kanon_deps:LOADER"
# ...
```

But `kanon_reference` doesn't exist as a Python package yet. Phase A.2.1 authors it.

Per the design ([`docs/design/kernel-reference-interface.md`](../design/kernel-reference-interface.md) §"Resolver shape"):

> The entry-point value resolves to either:
> 1. A module attribute named `MANIFEST` containing the parsed manifest dict (most common).
> 2. A callable returning the manifest dict when invoked with no arguments.
>
> Phase A's entry-point loader tries (1) first, then (2). The kernel does not import the publisher's full package — only the module the entry-point names. The manifest dict has the same shape as today's `src/kanon/kit/aspects/<aspect>/manifest.yaml`.
>
> ### Why `MANIFEST`-as-attribute is the recommended shape
> Static attribute (vs. callable) makes the manifest discoverable to type-checkers, lints, and offline analysis tools. Publishers writing in pure-data style produce a YAML→Python conversion at package-build time; the runtime cost at substrate-startup is one module import per publisher.

A.2.1 ships **option 1 (MANIFEST-as-attribute)**: each of the seven aspect modules (`kanon_reference/aspects/kanon_X.py`) carries a `MANIFEST: dict[str, Any] = {...}` literal whose body is the parsed equivalent of `src/kanon/kit/aspects/<X>/manifest.yaml`.

**Note on entry-point token:** A.1's commented stubs used `:LOADER` as the attribute name; the design specifies `:MANIFEST`. A.2.1 corrects to `:MANIFEST` when uncommenting.

## Scope

### In scope

#### A. `src/kanon_reference/` Python package

New top-level package alongside `src/kanon/`:

```
src/kanon_reference/
├── __init__.py          # one-line module docstring
└── aspects/
    ├── __init__.py      # one-line docstring
    ├── kanon_deps.py    # MANIFEST = {...}
    ├── kanon_fidelity.py
    ├── kanon_release.py
    ├── kanon_sdd.py
    ├── kanon_security.py
    ├── kanon_testing.py
    └── kanon_worktrees.py
```

Each aspect module contains a single top-level constant:

```python
# src/kanon_reference/aspects/kanon_sdd.py
"""kanon-sdd MANIFEST stub — Phase A.2.1 LOADER for the substrate's entry-point discovery.

The MANIFEST dict mirrors src/kanon/kit/aspects/kanon-sdd/manifest.yaml byte-for-byte
in semantic content (modulo YAML→Python conversion). The duplication is short-lived:
Phase A.3 deletes the YAML when kit-shape aspect content is retired and the
LOADER stubs become the canonical shape.
"""

from typing import Any

MANIFEST: dict[str, Any] = {
    "files": [...],
    "depth-0": {"files": [...], "protocols": [...], "sections": [...]},
    "depth-1": {...},
    ...
}
```

The conversion is mechanical: `yaml.safe_load(open("src/kanon/kit/aspects/<X>/manifest.yaml").read())` → Python literal.

#### B. Update `packaging/reference/pyproject.toml`

Two changes:

1. **Uncomment the entry-points block** and rename `:LOADER` → `:MANIFEST` per the design.
2. **Replace placeholder package** with the real `kanon_reference` package:
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["../../src/kanon_reference"]
   ```

#### C. Delete placeholder

Remove `packaging/reference/src/_kanon_reference_placeholder/__init__.py` and the parent directory tree (no longer needed).

#### D. Update `scripts/check_packaging_split.py`

Phase A.1's gate didn't validate the entry-points block (it was commented out). A.2.1's gate now validates it IS present and references the seven canonical aspect IDs pointing at `kanon_reference.aspects.kanon_X:MANIFEST`. Adds one new check function `_check_reference_entry_points`.

#### E. Update `tests/scripts/test_check_packaging_split.py`

Mirror the gate change: green-path test still passes; new synthetic-failure tests cover (a) missing entry-points block, (b) wrong entry-point target.

#### F. New test: `tests/test_kanon_reference_manifests.py`

For each of the seven aspects, assert the LOADER `MANIFEST` dict is structurally equivalent to the corresponding `src/kanon/kit/aspects/<X>/manifest.yaml` parsed via `yaml.safe_load`. This is the contract that prevents A.2.1's LOADER stubs from drifting away from the YAML source-of-truth before A.3 retires the YAML.

### Out of scope

- **Substrate runtime change.** No `_load_aspect_registry()`, no `_kit_root()` retirement — A.2.2.
- **Aspect content move.** YAML manifests stay at `src/kanon/kit/aspects/<X>/manifest.yaml`; the LOADER stubs duplicate-but-don't-replace. A.3 deletes the YAMLs.
- **Namespace-ownership validator.** A.2.2.
- **`scripts/check_substrate_independence.py`.** A.2.2.
- **Top-level `pyproject.toml` swing.** Later in Phase A.
- **No new ADR / spec / design / principle changes.**

## Approach

1. Read each `src/kanon/kit/aspects/<X>/manifest.yaml` and convert to a Python literal `MANIFEST` dict.
2. Author the seven `kanon_reference/aspects/kanon_X.py` modules with the MANIFEST constants.
3. Author `kanon_reference/__init__.py` and `kanon_reference/aspects/__init__.py` (one-line docstrings each).
4. Update `packaging/reference/pyproject.toml`: uncomment entry-points; rename `:LOADER` → `:MANIFEST`; swap placeholder package for real `kanon_reference`.
5. Delete `packaging/reference/src/_kanon_reference_placeholder/`.
6. Update `scripts/check_packaging_split.py` to validate the now-active entry-points block.
7. Update `tests/scripts/test_check_packaging_split.py` accordingly.
8. Author `tests/test_kanon_reference_manifests.py` with the YAML-vs-MANIFEST equivalence test (parametrized over the seven aspects).
9. Run all gates + full pytest.
10. CHANGELOG entry under `[Unreleased] § Added`.
11. Commit + push + PR.

## Acceptance criteria

### Package + LOADERs

- [ ] AC-P1: `src/kanon_reference/__init__.py` exists with a one-line docstring.
- [ ] AC-P2: `src/kanon_reference/aspects/__init__.py` exists with a one-line docstring.
- [ ] AC-P3: Seven modules `src/kanon_reference/aspects/kanon_{deps,fidelity,release,sdd,security,testing,worktrees}.py` exist, each with a top-level `MANIFEST: dict[str, Any]`.
- [ ] AC-P4: For each of the seven aspects, the LOADER MANIFEST is semantically equivalent to `yaml.safe_load(src/kanon/kit/aspects/<X>/manifest.yaml)`.

### Pyproject update

- [ ] AC-Y1: `packaging/reference/pyproject.toml` has an active (uncommented) `[project.entry-points."kanon.aspects"]` block.
- [ ] AC-Y2: Each of the seven entries points at `kanon_reference.aspects.kanon_<id>:MANIFEST`.
- [ ] AC-Y3: `[tool.hatch.build.targets.wheel].packages` references `../../src/kanon_reference`.
- [ ] AC-Y4: The placeholder file `packaging/reference/src/_kanon_reference_placeholder/__init__.py` and its parent dirs are deleted.

### CI gate

- [ ] AC-CI1: `scripts/check_packaging_split.py` gains a `_check_reference_entry_points` function that validates the seven entry-points are present and target `kanon_reference.aspects.kanon_<id>:MANIFEST`.
- [ ] AC-CI2: `tests/scripts/test_check_packaging_split.py` covers green path + missing-entry-points failure + wrong-entry-point-target failure.
- [ ] AC-CI3: New test `tests/test_kanon_reference_manifests.py` parametrized over the seven aspects asserts MANIFEST ≡ YAML (semantic equivalence).

### Cross-cutting

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Added` gains a paragraph naming Phase A.2.1.
- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3: `python scripts/check_links.py` passes.
- [ ] AC-X4: `python scripts/check_foundations.py` passes.
- [ ] AC-X5: `python scripts/check_kit_consistency.py` passes.
- [ ] AC-X6: `python scripts/check_invariant_ids.py` passes.
- [ ] AC-X7: `python scripts/check_packaging_split.py` passes.
- [ ] AC-X8: `pytest tests/test_kanon_reference_manifests.py --no-cov` → 7 passed.
- [ ] AC-X9: Full pytest: ≥841 passed (was 834 + 7 new manifest-equivalence + new gate-failure tests), 0 failed.
- [ ] AC-X10: No `src/kanon/` content changed (kernel and YAML manifests untouched). No aspect content moved. No `_kit_root()` change.
- [ ] AC-X11: Top-level `pyproject.toml` byte-identical to current `main`.

## Risks / concerns

- **Risk: drift between LOADER MANIFEST and YAML manifest over A.2.1's lifetime.** Mitigation: AC-X8 / `tests/test_kanon_reference_manifests.py` runs on every commit; any drift hard-fails CI. Phase A.3 deletes the YAML, eliminating the drift surface entirely.
- **Risk: hatch build still fails because `kanon_reference` package now has real content but no setup is wired.** A.2.1 doesn't try to actually `uv build` the wheel — that's a later step. The pyproject is schema-of-record per Phase A.1's framing.
- **Risk: `check_kit_consistency.py` flags the new `src/kanon_reference/` directory.** Inspect the gate's scope; if it walks `src/` for kit-related layouts, narrow it. Verify locally; if it fires, plan amends to address.
- **Risk: `:MANIFEST` vs. `:LOADER` rename is missed somewhere else.** Mitigation: grep for `:LOADER` after the change; only Phase A.1's commented-out stubs should reference it (and we're uncommenting them).
- **Risk: Python literal conversion of 312 lines of YAML produces large diff.** Mitigation: ~600 LOC across seven small modules is tolerable; the equivalence test is the safety net.

## Documentation impact

- **New files:** `src/kanon_reference/__init__.py`, `src/kanon_reference/aspects/__init__.py`, seven `src/kanon_reference/aspects/kanon_*.py`, `tests/test_kanon_reference_manifests.py`, `docs/plans/phase-a.2.1-loader-package.md`.
- **Touched files:** `packaging/reference/pyproject.toml`, `scripts/check_packaging_split.py`, `tests/scripts/test_check_packaging_split.py`, `CHANGELOG.md`.
- **Deleted files:** `packaging/reference/src/_kanon_reference_placeholder/__init__.py` (and parent dirs).
- **No changes to:** `src/kanon/` (kernel + YAML manifests untouched), specs, designs, ADRs, foundations, protocol prose, top-level pyproject.
