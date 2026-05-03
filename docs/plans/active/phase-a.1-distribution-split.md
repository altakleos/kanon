---
status: approved
slug: phase-a.1-distribution-split
date: 2026-05-01
design: docs/design/distribution-boundary.md
---

# Plan: Phase A.1 — Distribution split (three pyproject.toml files)

## Context

Per [ADR-0045](../../decisions/0045-de-opinionation-transition.md) §Decision step 1: "Distribution split (substrate / reference / meta-alias pyproject.toml files)". Per [ADR-0043](../../decisions/0043-distribution-boundary-and-cadence.md): `kanon-core` (kernel) ships separately from `kanon-aspects` (aspects); `kanon-kit` is a meta-package alias preserving the convenience-install path. The canonical shapes for all three `pyproject.toml` files are specified in [`docs/design/distribution-boundary.md`](../../design/distribution-boundary.md).

**Coupling note (intentional design choice for A.1):** the canonical substrate wheel built from `packaging/substrate/pyproject.toml` will not be runtime-functional until A.2 wires entry-point-based aspect discovery (per ADR-0040). The substrate's `_kit_root()` machinery currently looks for aspects co-located with the kernel package; A.1 lands the *packaging shape*, A.2 lands the *runtime discovery*. The `kanon-aspects` wheel has no `LOADER` infrastructure until A.2 either. **A.1 ships pyproject files as schema-of-record, not as the active build path.** The top-level `pyproject.toml` continues to build `kanon-kit` v0.3.x.

This ordering matches ADR-0045's stipulation that each Phase A step gates on substrate-self-conformance staying green: if A.1 ripped aspect content into a `kanon_reference` source tree before A.2 wired the runtime discovery, the kernel would break between commits.

## Goal

Land a single PR that:

1. Authors three `pyproject.toml` files at `packaging/substrate/pyproject.toml`, `packaging/reference/pyproject.toml`, `packaging/kit/pyproject.toml`, each conforming to the canonical shapes in the ADR-0043 design.
2. Authors a CI gate `scripts/check_packaging_split.py` that validates each file's name, version, and core metadata against the canonical shapes.
3. Preserves the active build path: top-level `pyproject.toml` remains the canonical build input for v0.3.x; the `packaging/` files are skeletons activated incrementally by A.2 onward.
4. Adds a CHANGELOG entry under `[Unreleased] § Added`.

## Scope

### In scope

#### A. `packaging/substrate/pyproject.toml`

New file. Follows the substrate shape from `docs/design/distribution-boundary.md`:

```toml
[project]
name = "kanon-core"
version = "1.0.0a1"
description = "Protocol substrate for prose-as-code engineering discipline in LLM-agent-driven repos."
readme = "../../README.md"
requires-python = ">=3.10"
license = { file = "../../LICENSE" }
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Operating System :: POSIX",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
]

[project.scripts]
kanon = "kanon.cli:main"

[project.urls]
Homepage = "https://github.com/altakleos/kanon"
Documentation = "https://github.com/altakleos/kanon/blob/main/docs/foundations/vision.md"

[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["../../src/kanon"]
exclude = [
    "../../src/kanon/kit/aspects/**",  # kit-shape aspects retired by Phase A.3; ship none
]
```

Header comment marks this as a Phase A.1 skeleton, not yet build-active, with a pointer to A.2/A.3 for activation.

#### B. `packaging/reference/pyproject.toml`

New file. Follows the reference shape from the design. Since `kanon_reference` Python package + LOADER stubs land in A.2, the entry-points block is a placeholder (commented `# Activated by Phase A.2 — see docs/design/kernel-reference-interface.md` with the seven entry-point lines commented out for traceability):

```toml
[project]
name = "kanon-aspects"
version = "1.0.0a1"
description = "Reference discipline aspects for the kanon protocol substrate."
readme = "../../README.md"
requires-python = ">=3.10"
license = { file = "../../LICENSE" }
dependencies = [
    "kanon-core==1.0.0a1",
]

# Activated by Phase A.2 — see docs/design/kernel-reference-interface.md.
# [project.entry-points."kanon.aspects"]
# kanon-deps = "kanon_reference.aspects.kanon_deps:LOADER"
# kanon-fidelity = "kanon_reference.aspects.kanon_fidelity:LOADER"
# kanon-release = "kanon_reference.aspects.kanon_release:LOADER"
# kanon-sdd = "kanon_reference.aspects.kanon_sdd:LOADER"
# kanon-security = "kanon_reference.aspects.kanon_security:LOADER"
# kanon-testing = "kanon_reference.aspects.kanon_testing:LOADER"
# kanon-worktrees = "kanon_reference.aspects.kanon_worktrees:LOADER"

[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
# Source tree authored by Phase A.2.
packages = []
```

#### C. `packaging/kit/pyproject.toml`

New file. The meta-alias:

```toml
[project]
name = "kanon-kit"
version = "1.0.0a1"
description = "Convenience meta-package: installs kanon-core plus kanon-aspects."
readme = "../../README.md"
requires-python = ">=3.10"
license = { file = "../../LICENSE" }
dependencies = [
    "kanon-core==1.0.0a1",
    "kanon-aspects==1.0.0a1",
]

[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
# Meta-package — no source content. Bare-minimum sentinel module for hatch to produce a wheel.
packages = ["src/_kanon_kit_meta"]
```

A two-line `packaging/kit/src/_kanon_kit_meta/__init__.py` (`""" kanon-kit meta-package — installs kanon-core + kanon-aspects. """`) gives hatch something to package.

#### D. CI gate `scripts/check_packaging_split.py`

New file. Validates each of the three `packaging/*/pyproject.toml` files:

- file exists
- parses as TOML
- top-level `[project].name` matches expected (`kanon-core` / `kanon-aspects` / `kanon-kit`)
- top-level `[project].version` is `1.0.0a1`
- top-level `[project].requires-python` is `>=3.10`
- substrate has a `[project.scripts] kanon = "kanon.cli:main"` entry; reference and kit do not
- reference depends on `kanon-core==1.0.0a1`; kit depends on both
- substrate's `[tool.hatch.build.targets.wheel].exclude` includes `"../../src/kanon/kit/aspects/**"`

Mirrors the gate-shape of `scripts/check_kit_consistency.py` and `scripts/check_foundations.py`. Returns `{"errors": [...], "status": "ok"|"error"}` JSON.

#### E. CI gate test

New file `tests/scripts/test_check_packaging_split.py`. Mirrors the test-shape of `tests/scripts/test_check_kit_consistency.py`. Covers: (1) green path (current state passes); (2) each invariant fails when violated (parse-able tampering: missing field, wrong name, wrong version, missing exclude).

#### F. Top-level pyproject.toml — UNCHANGED

The active build path remains as-is. Phase A.1 is purely additive at the packaging layer.

#### G. CHANGELOG entry

One paragraph under `## [Unreleased]` § Added.

#### H. Optional: README pointer

A one-line addition in the README under "Installation" or near the existing kanon-kit reference, noting that v1.0 will ship as `kanon-core` + `kanon-aspects` with a `kanon-kit` meta alias. Soft pointer; design lives in `docs/design/distribution-boundary.md`.

### Out of scope

- **Aspect content move.** Aspects stay at `src/kanon/kit/aspects/` until Phase A.3 deletes the kit-shape; A.2 may relocate them under `kanon_reference/`.
- **`kanon_reference` Python package authoring.** A.2 territory.
- **LOADER stubs.** A.2 territory (entry-points are commented placeholders here).
- **Substrate runtime discovery rewrite (`_load_aspect_registry()` reading `importlib.metadata.entry_points`).** A.2 territory.
- **`_kit_root()` retirement.** A.2 territory.
- **Top-level `pyproject.toml` swing.** A later phase swings the top-level build to the substrate pyproject; for now the top-level is the canonical v0.3.x kit-kit build.
- **Making any of the three packaging wheels actually buildable end-to-end.** They are schema-of-record; A.2 onward makes them functional.
- **No new ADR / spec / design / principle changes.**

## Approach

1. Create `packaging/substrate/pyproject.toml`, `packaging/reference/pyproject.toml`, `packaging/kit/pyproject.toml` per the shapes above.
2. Create the two-line sentinel module at `packaging/kit/src/_kanon_kit_meta/__init__.py`.
3. Author `scripts/check_packaging_split.py` with the validations above.
4. Author `tests/scripts/test_check_packaging_split.py` with green-path + each-invariant-fails tests.
5. Run gates: `kanon verify .`, `python scripts/check_links.py`, `python scripts/check_foundations.py`, `python scripts/check_kit_consistency.py`, `python scripts/check_invariant_ids.py`, `python scripts/check_packaging_split.py`, `pytest tests/scripts/test_check_packaging_split.py`.
6. Run full pytest to confirm no regression: `uv run --frozen pytest -q --no-cov`.
7. Author CHANGELOG entry.
8. Optional README pointer.
9. Commit + push + open PR.

## Acceptance criteria

### Substrate pyproject

- [ ] AC-S1: `packaging/substrate/pyproject.toml` exists; parses as TOML.
- [ ] AC-S2: `[project].name = "kanon-core"`; `version = "1.0.0a1"`; `requires-python = ">=3.10"`; `dependencies` include `click>=8.1` + `pyyaml>=6.0`.
- [ ] AC-S3: `[project.scripts] kanon = "kanon.cli:main"` present.
- [ ] AC-S4: `[tool.hatch.build.targets.wheel].exclude` contains `"../../src/kanon/kit/aspects/**"`.

### Reference pyproject

- [ ] AC-R1: `packaging/reference/pyproject.toml` exists; parses as TOML.
- [ ] AC-R2: `[project].name = "kanon-aspects"`; `version = "1.0.0a1"`; depends on `kanon-core==1.0.0a1`.
- [ ] AC-R3: `[project.entry-points."kanon.aspects"]` exists as a *commented-out* stub for traceability (one comment line per the seven aspects); not active.

### Kit meta pyproject

- [ ] AC-K1: `packaging/kit/pyproject.toml` exists; parses as TOML.
- [ ] AC-K2: `[project].name = "kanon-kit"`; `version = "1.0.0a1"`; depends on both `kanon-core==1.0.0a1` and `kanon-aspects==1.0.0a1`.
- [ ] AC-K3: Sentinel module `packaging/kit/src/_kanon_kit_meta/__init__.py` exists with a one-line docstring.

### CI gate

- [ ] AC-CI1: `scripts/check_packaging_split.py` exists; runnable; returns `{"status":"ok"}` JSON on green path.
- [ ] AC-CI2: `tests/scripts/test_check_packaging_split.py` covers green path + each invariant failure (≥6 tests).
- [ ] AC-CI3: Test file follows the existing CI-test conftest shape (uses `load_ci_script` fixture).

### Cross-cutting

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Added` gains a paragraph naming Phase A.1.
- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3: `python scripts/check_links.py` passes.
- [ ] AC-X4: `python scripts/check_foundations.py` passes.
- [ ] AC-X5: `python scripts/check_kit_consistency.py` passes.
- [ ] AC-X6: `python scripts/check_invariant_ids.py` passes.
- [ ] AC-X7: `python scripts/check_packaging_split.py` passes (the new gate validates itself green).
- [ ] AC-X8: `uv run --frozen pytest -q --no-cov` passes (no regression).
- [ ] AC-X9: Top-level `pyproject.toml` is byte-identical to current `main` after this PR.
- [ ] AC-X10: No `src/kanon/` content changed; no aspect content moved; no `_kit_root()` change; no source code change in any kanon module.

## Risks / concerns

- **Risk: someone tries `cd packaging/substrate && uv build` and is confused when the wheel doesn't run.** Mitigation: header comment on each pyproject file ("Phase A.1 skeleton — substrate wheel not runtime-functional until A.2 wires entry-point discovery"); README pointer.
- **Risk: `scripts/check_kit_consistency.py` flags the new `packaging/` directory as unexpected kit content.** Mitigation: inspect the gate's scope; if it walks the repo for any TOML at non-canonical paths, narrow it (or add `packaging/` to its allowlist). Verify locally; if it fires, this plan amends to address.
- **Risk: hatch's TOML validator may reject `packages = []` in the reference pyproject.** Mitigation: if hatch errors on empty `packages`, use a placeholder `packages = ["packaging/reference/_placeholder"]` with a one-byte sentinel file; the new gate accepts either form.
- **Risk: `kanon verify .` might walk `packaging/` and choke on an unexpected `pyproject.toml`.** Verify locally; the verify command should ignore paths outside its scope.
- **Risk: pytest's coverage gate (`--cov-fail-under=90`) may dip from the new files.** Mitigation: ensure the new CI gate has tests covering all branches; verify coverage stays ≥90 with `uv run --frozen pytest --cov`.

## Documentation impact

- **New files:** `packaging/substrate/pyproject.toml`, `packaging/reference/pyproject.toml`, `packaging/kit/pyproject.toml`, `packaging/kit/src/_kanon_kit_meta/__init__.py`, `scripts/check_packaging_split.py`, `tests/scripts/test_check_packaging_split.py`, `docs/plans/phase-a.1-distribution-split.md`.
- **Touched files:** `CHANGELOG.md`. Optionally `README.md` (one-line pointer; soft scope).
- **No changes to:** top-level `pyproject.toml`, any `src/kanon/` content, any `docs/specs/`, any `docs/design/`, any `docs/decisions/`, any `docs/foundations/`, any aspect manifests, any protocol prose.
