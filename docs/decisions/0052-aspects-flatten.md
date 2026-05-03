---
status: draft
date: 2026-05-03
---
# ADR-0052: aspects-flatten path selection

## Context

ADR-0049 §1(7) committed the kanon repo to a monorepo layout where the seven reference aspects live at a top-level semantic-named directory: `aspects/` (panel vote 6–1 for semantic naming over workspace-conventional `packages/<dist>/`). The corresponding source-tree move is `src/kanon_reference/` → `aspects/`. ADR-0049's §Implementation Roadmap PR E was the kernel-flatten move (`src/kanon/` → `kernel/`), and the planned final PR was the aspects-flatten move (`src/kanon_reference/` → `aspects/`).

The kernel-flatten attempt failed at the Hatch-build layer: the `[tool.hatch.build.targets.wheel.sources]` source-remap that would translate the on-disk path `kernel/` to the importable Python package `kanon` works fine for non-editable installs but the `editables` library (which Hatch uses to wire PEP 660 editable installs) only supports prefix STRIP, not prefix RENAME. ADR-0050 documented the constraint and authored three forward-options. We selected Option A (Python module rename `kanon` → `kernel`), shipped it in v0.5.0a2 (PR #96 + #97 + #99 + #100), and the renaming-the-Python-module approach is now the precedent-supported path for analogous source-tree refactors.

The aspects-flatten faces the **same** Hatch editable-install constraint. The architectural question is mechanically identical: a `[tool.hatch.build.targets.wheel.sources]` remap from on-disk `aspects/` to importable Python package `kanon_reference` would build correct non-editable wheels but break `pip install -e '.[dev]'` and `uv sync`'s editable mode. The Phase A three-package PyPI split (`kanon-core` + `kanon-aspects` + `kanon-kit` per ADR-0043 + ADR-0051) requires SOME decision on this question before the per-package pyproject co-location can land.

This ADR is to ADR-0049 §1(7) what ADR-0050 was to ADR-0049 §1(2): a normative supplement that records the constraint and selects a forward-option. Status: draft pending user ratification.

## Decision

**Defer the source-tree directory rename. Adopt no top-level `aspects/` directory; the reference aspects continue to live at `src/kanon_reference/`.**

This selects Option C from §Options below (skip the rename). The two alternative options (A: hatch source-remap; B: Python module rename per ADR-0050 precedent) are explicitly rejected for the reasons in §Alternatives.

The Phase A three-package PyPI split (ADR-0043 + ADR-0051) proceeds with the existing layout: each per-package `pyproject.toml` is co-located with its source by convention — `kernel/pyproject.toml` for the substrate kernel; `src/kanon_reference/pyproject.toml` for the reference aspects (or, per ADR-0049 PR-B's intent, `aspects/pyproject.toml` at top-level even though the source remains under `src/`). The asymmetry between `kernel/` (top-level, post-ADR-0050 Option A) and `src/kanon_reference/` (under `src/`, deferred indefinitely) is acknowledged: the kanon repo's `erd -L 2` output reads as inconsistent. We accept this in exchange for not paying the Python-module rename cost a second time.

### Why C over A and B

ADR-0050 Option A's lesson was that the Python-module rename cost is **not** the primary cost. The primary cost was the *coordination cost* of all the downstream hotfixes (preflight script, Makefile, validator script, sdist-include filter, distribution-name string in error messages — PRs #97, #98, #99, #100, #102, #104, #107) that surfaced only after the rename hit CI. Each was small in isolation; together they took 12 hours of autopilot rhythm to chase down.

Doing the same to `src/kanon_reference/` would replay that pattern. The package is much smaller (one `__init__.py` + 7 aspect subdirectories with `loader.py` + `manifest.yaml` + `protocols/` + `files/` per slug), but the integration surface is the same class: aspect-discovery entry-points (per ADR-0040, group `kanon.aspects`), validator allow-list (`kernel/_manifest.py:238`), wheel-content validator (`scripts/check_package_contents.py`), sdist include filter (`pyproject.toml [tool.hatch.build.targets.sdist].include`), test fixtures, ~30 doc cross-refs.

The benefit is purely visual: `aspects/` reads cleaner than `src/kanon_reference/` in `ls`. The kanon-core / kanon-aspects distribution boundary is structurally visible regardless because each package has its own `pyproject.toml`. ADR-0049 §1(7) Decision D2 voted for the visual win 6–1 — but D2 was decided before the kernel-flatten attempt revealed that the Hatch constraint multiplies the cost.

## Alternatives Considered

### Option A — Hatch source-remap (`[tool.hatch.build.targets.wheel.sources]` `aspects = "kanon_reference"`)

Rejected. **Confirmed broken.** The `editables` library that Hatch uses for PEP 660 editable installs supports only prefix-strip remaps (e.g., remove the `src/` prefix), not prefix-rename remaps (e.g., translate `aspects` ↔ `kanon_reference`). `pip install -e '.[dev]'` and `uv sync`'s editable mode would both fail with the same error class that produced ADR-0050. We have no reason to expect a different outcome on the second attempt.

### Option B — Python module rename `kanon_reference` → `aspects` (per ADR-0050 Option A precedent)

Rejected. **Doable but expensive.** This is the path that worked for the kernel-flatten. For aspects, it would entail:

1. New Python package: `aspects/__init__.py` (currently `src/kanon_reference/__init__.py`).
2. Source-tree move: `src/kanon_reference/aspects/kanon_<slug>/` → `aspects/<slug>/` (or `aspects/kanon_<slug>/` to preserve the entry-point group's slug grammar).
3. Aspect entry-points in each loader manifest's dotted path: `kanon_reference.aspects.kanon_<slug>.loader` → `aspects.<slug>.loader` (or kept as `kanon_reference.aspects.kanon_<slug>.loader` purely as a string identifier — the `kanon.aspects` entry-point GROUP is what the substrate discovers, not the dotted path inside).
4. Validator allow-list update: `kernel/_manifest.py:238` changes from `("kanon-aspects", "kanon-kit")` to whichever Python-distribution name the new layout produces. Likely the same — `kanon-aspects` distribution name is unchanged; the source-tree directory is what moves.
5. Doc cite sweep: ~30 ADR + design + plan refs from `src/kanon_reference/` → `aspects/`. Half are in immutable ADRs requiring `Allow-ADR-edit:` trailers.

Cost estimate: **~6–8 hours of autopilot rhythm** (same class as ADR-0050 Option A's lap), distributed across 4–6 PRs because each subsystem (build config, validator, sdist filter, docs) needs its own focused fix-and-CI loop.

The benefit (cleaner `ls`) is real but small. The cost is concrete and recently lived.

### Option C — Skip the rename (selected)

The selected path. `src/kanon_reference/` stays. The kanon repo's `erd -L 2` shows `kernel/` at depth-1 alongside `src/kanon_reference/` at depth-2 — visible asymmetry, acknowledged. The three-package PyPI split (ADR-0043 + ADR-0051) proceeds without a directory move; per-package pyprojects co-locate at:

- `kernel/pyproject.toml` — `kanon-core` distribution (substrate kernel).
- `src/kanon_reference/pyproject.toml` — `kanon-aspects` distribution (reference aspect bundles).
- `kit-meta/pyproject.toml` — `kanon-kit` meta-package (depends on `kanon-core` + `kanon-aspects`).

Top-level `pyproject.toml` becomes the uv workspace coordinator (no `[project]`, just `[tool.uv.workspace]` listing the three members).

The directory asymmetry is documented here as an explicit accepted-debt item. A future ADR may revisit the rename if (a) Hatch / editables grows prefix-rename support upstream, or (b) a downstream pain-point makes the asymmetry concretely costly.

### Option D — Adopt `packages/{core,aspects,kit}/` workspace-conventional layout (P6's Round-3 dissent in the ADR-0049 panel)

Rejected for the same reasons ADR-0049 §Alternatives §2 rejected it: the convention is real (Hatch + uv use it), but the structural cost in this repo is high (workspace-rename = mega-event-class restructuring touching 100+ files), the kernel-flatten Option A precedent isn't applicable (the workspace-rename moves source-tree; it doesn't rename Python modules), and the convention's payoff is low (the `[tool.uv.workspace]` table at the repo root indexes the workspace members regardless of directory naming).

## Consequences

### Layout

- `kernel/` stays at top-level (per ADR-0050 Option A) with its own `pyproject.toml` (Phase A).
- `src/kanon_reference/` stays at depth-2 (this ADR's deferral) with its own `pyproject.toml` (Phase A).
- `kit-meta/` is a new top-level directory (Phase A) holding the meta-package's `pyproject.toml` and nothing else (no source code; the meta-package ships zero `[tool.hatch.build.targets.wheel].packages`).
- Repo-root `pyproject.toml` is the uv workspace coordinator. It carries `[tool.uv.workspace] members = ["kernel", "src/kanon_reference", "kit-meta"]` (or a glob equivalent). The current `[project]` table moves to `kit-meta/pyproject.toml` (which preserves the existing `kanon-kit` distribution name).

### Documentation

- ADR-0049 §1(7) is **superseded in part** by this ADR (the source-tree move is deferred; the per-package pyproject co-location is preserved as ADR-0049 §Implementation Roadmap PR B's intent). Allow-ADR-edit trailer required on the commit that updates ADR-0049's §1(7) prose to point at this ADR.
- `docs/design/distribution-boundary.md` and any active plan that names `aspects/` as the source-tree path should be updated to clarify "directory rename deferred per ADR-0052; per-package pyproject co-locates at `src/kanon_reference/pyproject.toml`."
- This ADR may be ratified before Phase A's other steps (β, γ, δ, ε) execute, or in the same cycle as Phase A.

### Open question deferred

The asymmetric layout (`kernel/` at depth-1, `src/kanon_reference/` at depth-2) is unresolved. Future ADRs may revisit if:

1. Hatch / editables gains prefix-rename support → Option A becomes viable again.
2. A specific pain-point makes the asymmetry concretely costly (e.g., a contributor-onboarding metric showing newcomers get confused by the layout).
3. A panel-style review judges the visual cost has accumulated past the 6–8-hour rename cost.

Until then: deferred indefinitely, intentionally.

## Migration

- **Zero**. This ADR rejects the rename; nothing moves on disk.
- The Phase A three-package split proceeds in subsequent PRs (β, γ, δ, ε) per the strategic plan that authorized this ADR.
- No PyPI distribution names change. `kanon-core` + `kanon-aspects` + `kanon-kit` per ADR-0051 — all unaffected by the source-tree layout decision.

## References

- [ADR-0049](0049-monorepo-layout.md) — monorepo layout; this ADR supersedes its §1(7) (aspects-flatten) only. Allow-ADR-edit trailer required to update §1(7) prose.
- [ADR-0050](0050-kernel-flatten-deferral.md) — the kernel-flatten deferral that established the precedent + lived experience driving this ADR's option-rejection rationale.
- [ADR-0051](0051-distribution-naming.md) — distribution naming (`kanon-core` / `kanon-aspects` / `kanon-kit`); preserved verbatim.
- [ADR-0043](0043-distribution-boundary-and-cadence.md) — three-distribution split; this ADR confirms the split proceeds without a directory move.
- v0.5.0a2 release cycle: PRs #96, #97, #98, #99, #100, #102, #104, #107 — the lived autopilot cost of the kernel-flatten lap that this ADR's rejection-of-Option-B references.
