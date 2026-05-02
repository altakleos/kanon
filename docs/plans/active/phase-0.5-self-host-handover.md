---
status: approved
slug: phase-0.5-self-host-handover
date: 2026-05-01
design: "No new design surface — ADR-0045 ratified the canonical Phase 0.5 sequence; this plan executes it. Recipe schema lives in `docs/design/distribution-boundary.md` (per ADR-0043)."
---

# Plan: Phase 0.5 — Self-host hand-over

## Context

Per [ADR-0045](../../decisions/0045-de-opinionation-transition.md), Phase 0.5 ships **before any Phase A deletion** and rewrites the kanon repo's `.kanon/config.yaml` to opt-in form via the publisher recipe (per ADR-0043). After Phase 0.5 lands, the kanon repo opts in to reference aspects exactly as any external consumer would; the kit-shape `defaults:` / `_detect.py` / kit-global `files:` machinery is still present in code but no longer load-bearing for the kanon repo's self-host.

Today's `.kanon/config.yaml` (v3 schema):
- Already declares all seven aspects explicitly (so `defaults:` is already a no-op for self-host)
- Has `kit_version: 0.3.1a1`, `aspects: {...}`, `preflight-stages: {...}`
- Does NOT have `schema-version`, `kanon-dialect`, `provenance`, or recipe references

Phase 0.5's job is to **forward-compatibly augment** the config with v4 fields while keeping v3 fields intact for backward compatibility with the current kit's parser. The current kit's `_read_config()` uses `yaml.safe_load()` and accesses fields via `.get()`, so unknown top-level keys are silently ignored — additive v4 fields are safe.

## Goal

Land a single self-contained PR that:

1. **Authors the kanon repo's recipe file** at `.kanon/recipes/reference-default.yaml`. Schema per [`docs/design/distribution-boundary.md`](../../design/distribution-boundary.md). Lists the seven reference aspects at the same depths the current config declares.
2. **Augments `.kanon/config.yaml`** with v4 fields (`schema-version`, `kanon-dialect`, `provenance`) while preserving existing v3 fields (`kit_version`, `aspects:`, `preflight-stages:`). The current kit reads only v3 fields and ignores v4; `kanon verify .` stays green.
3. **No source / aspect-manifest / protocol-prose / CI / new-spec / new-design / new-ADR changes.** Phase 0.5 is config + recipe data only.

## Scope

### In scope

#### A. Recipe file — `.kanon/recipes/reference-default.yaml`

New file. Schema per [`docs/design/distribution-boundary.md`](../../design/distribution-boundary.md) Recipe YAML schema section. Concrete content lists the seven reference aspects at the depths the kanon repo currently has:

```yaml
schema-version: 1
recipe-id: reference-default
publisher: kanon-reference
recipe-version: "1.0"
target-dialect: "2026-05-01"
description: "Default reference recipe..."
aspects:
  - id: kanon-sdd
    depth: 3
  - id: kanon-testing
    depth: 3
    config:
      test_cmd: .venv/bin/python -m pytest --no-cov -q
      lint_cmd: .venv/bin/ruff check src/ tests/ ci/
      typecheck_cmd: .venv/bin/mypy src/kanon
      format_cmd: ''
  - id: kanon-worktrees
    depth: 2
  - id: kanon-release
    depth: 2
  - id: kanon-security
    depth: 2
  - id: kanon-deps
    depth: 2
  - id: kanon-fidelity
    depth: 1
```

This recipe is checked into the kanon repo's `.kanon/recipes/`. Phase A.1 (distribution split) will move the canonical version into the `kanon-reference` package's `recipes/` directory; the file in `.kanon/recipes/` remains as the consumer-side opt-in artifact.

#### B. `.kanon/config.yaml` augmentation

Add v4 fields at the top of the file while preserving all v3 fields:

```yaml
# v4 fields (added by Phase 0.5 — currently ignored by v3 kit; activated by Phase A.1)
schema-version: 4
kanon-dialect: "2026-05-01"
provenance:
  - recipe: reference-default
    publisher: kanon-reference
    recipe-version: "1.0"
    applied_at: "2026-05-01T00:00:00+00:00"

# v3 fields (read by today's kit; preserved verbatim until Phase A.3 deletes the v3 reader)
kit_version: 0.3.1a1
aspects:
  ... (unchanged) ...
preflight-stages:
  ... (unchanged) ...
```

The augmentation is purely additive; v3 fields are not modified. Today's `kanon verify .` reads only v3 fields and stays green.

#### C. Plan documentation

The plan file documents the hand-over event for traceability.

#### D. CHANGELOG entry

One paragraph under `## [Unreleased]` § Changed (this is user-visible substrate behaviour change for the kanon repo, even if symbolic).

### Out of scope

- **Phase A deletions.** This plan ships Phase 0.5 *only*; Phase A.1 onward follows in subsequent plans.
- **Kit-side parser changes.** The current `_read_config()` is unchanged; Phase A.3 deletes the v3 reader. Phase 0.5 only writes the new file shape.
- **`kanon-reference` package authoring.** Phase A.1 territory. The recipe file in `.kanon/recipes/` is a stand-in for what `kanon-reference`'s `recipes/` directory will eventually ship.
- **Migration script.** Phase A.9 territory.
- **No new ADR, spec, design, or principle.**

## Approach

1. **Author `.kanon/recipes/reference-default.yaml`** with the schema from ADR-0043's design.
2. **Augment `.kanon/config.yaml`** by prepending v4 fields and a clear comment marking the boundary between v4-additions and v3-preserved fields.
3. **Run gates locally**: `kanon verify .`, `python scripts/check_links.py`, `python scripts/check_foundations.py`, `python scripts/check_kit_consistency.py`, etc.
4. **Author CHANGELOG entry** under `[Unreleased] § Changed`.
5. **Regenerate fidelity lock** if any spec SHAs bump (unlikely; we're touching consumer-side artifacts only).

## Acceptance criteria

### Recipe file

- [ ] AC-R1: `.kanon/recipes/reference-default.yaml` exists with the schema per ADR-0043's design.
- [ ] AC-R2: Recipe lists the seven reference aspects at the same depths the current `.kanon/config.yaml` declares (kanon-sdd:3, kanon-testing:3, kanon-worktrees:2, kanon-release:2, kanon-security:2, kanon-deps:2, kanon-fidelity:1).
- [ ] AC-R3: Recipe's `target-dialect` is `2026-05-01`.

### Config augmentation

- [ ] AC-C1: `.kanon/config.yaml` has new top-level fields `schema-version: 4`, `kanon-dialect: "2026-05-01"`, `provenance:`.
- [ ] AC-C2: `.kanon/config.yaml`'s existing v3 fields (`kit_version`, `aspects:`, `preflight-stages:`) are preserved verbatim — no field removed, no value changed.

### CHANGELOG

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Changed` gains a paragraph naming Phase 0.5.

### Cross-cutting

- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings (the current kit ignores v4 fields).
- [ ] AC-X3: `python scripts/check_links.py` passes.
- [ ] AC-X4: `python scripts/check_foundations.py` passes, zero warnings.
- [ ] AC-X5: `python scripts/check_kit_consistency.py` passes (no new kit-side files added; this gate is unaffected).
- [ ] AC-X6: `python scripts/check_invariant_ids.py` passes.
- [ ] AC-X7: No source / aspect-manifest / protocol-prose / CI / new-spec / new-design / new-ADR / new-principle changes.

## Risks / concerns

- **Risk: today's kit's parser may reject unknown top-level fields.** Mitigation: I inspected `_scaffold.py:_read_config()` semantics earlier — `yaml.safe_load()` returns a dict; field access is `.get()`-based; unknown keys are silently ignored. Verify by running `kanon verify .` after the augmentation; if it fails, revert and ship Phase 0.5 deferred to Phase A.1.
- **Risk: `check_kit_consistency.py` may flag the new `.kanon/recipes/` directory.** Mitigation: the gate inspects kit-side files only; consumer-side artifacts under `.kanon/` aren't in scope. Verify locally; if the gate fires, the plan amends to address.
- **Risk: the recipe file's schema differs from what Phase A.1 ultimately ships.** Mitigation: schema follows the ADR-0043 design exactly. If Phase A.1 finds the schema needs amendment, the recipe file is a single edit, not a refactor.
- **Risk: someone reads `kit_version: 0.3.1a1` next to `schema-version: 4` and gets confused.** Mitigation: a comment in the config marks the boundary explicitly: "# v4 fields (added by Phase 0.5)..." / "# v3 fields (preserved until Phase A.3 deletes the v3 reader)..."

## Documentation impact

- **New files:** `.kanon/recipes/reference-default.yaml`, `docs/plans/phase-0.5-self-host-handover.md`.
- **Touched files:** `.kanon/config.yaml` (additive only; v3 fields preserved), `CHANGELOG.md`.
- **No source / aspect-manifest / protocol-prose / CI / new-spec / new-design / new-ADR / new-principle changes.**
