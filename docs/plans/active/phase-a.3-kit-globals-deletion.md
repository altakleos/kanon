---
status: approved
slug: phase-a.3-kit-globals-deletion
date: 2026-05-02
design: docs/design/distribution-boundary.md
---

# Plan: Phase A.3 — kit-globals deletion (`defaults:` + `files:` + `kit.md`)

## Context

Per [ADR-0045](../../decisions/0045-de-opinionation-transition.md) §Decision step 3: "Kit-global `files:` + `defaults:` deleted; `.kanon/kit.md` migrated/deleted". Per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) (de-opinionation): the substrate has no opinion about which aspects a consumer should enable nor what files it should ship at the kit-global level. Consumers opt in explicitly via `aspects:` in `.kanon/config.yaml` or via publisher recipes (per [ADR-0043](../../decisions/0043-distribution-boundary-and-cadence.md)).

Today's `src/kanon/kit/manifest.yaml` declares two kit-globals that violate de-opinionation:

```yaml
defaults:
  - kanon-sdd
  - kanon-testing
  - kanon-security
  - kanon-deps
  - kanon-worktrees

files:
  - .kanon/kit.md
```

`defaults:` auto-enables five aspects when a consumer doesn't list any. `files:` lists kit-global files (today: just `.kanon/kit.md`, an opinionated orientation doc).

A.3 deletes both fields and the `.kanon/kit.md` artifact entirely.

## Substrate consumers

**`defaults:` (3 sites):**
- `src/kanon/cli.py:249` — `for name in top.get("defaults", [])` (likely `kanon init` profile)
- `src/kanon/cli.py:675` — `defaults: list[str] = list(top.get("defaults", []))` (init/aspect helper)
- `src/kanon/_manifest.py:727` — `names: list[str] = top.get("defaults", [])` (helper exposing default list)

**`files:` (3 sites):**
- `src/kanon/cli.py:388-399` — scaffolds top-level files into consumer's repo
- `src/kanon/_scaffold.py:245-247` — same in `_build_bundle`
- `src/kanon/_manifest.py:743` — `paths.extend(top.get("files", []) or [])` (manifest-fields helper)

**`kit.md` (5+ sites):**
- `src/kanon/kit/kit.md` — the template (57 lines)
- `.kanon/kit.md` — the kanon repo's own scaffolded artifact (consumer-side)
- `src/kanon/_scaffold.py:411-416` — `_render_kit_md()` reads template
- `src/kanon/cli.py:866-869` — atomic-writes kit.md during init
- `src/kanon/_cli_aspect.py:94, 152` — re-renders kit.md on aspect changes
- `scripts/check_kit_consistency.py:148-160` — `_check_kit_md_exists()` gate

## Goal

Single PR that:

1. Deletes `defaults:` from `src/kanon/kit/manifest.yaml` + all 3 substrate consumers.
2. Deletes `files:` from `src/kanon/kit/manifest.yaml` + all 3 substrate consumers.
3. Deletes `kit.md`: template (`src/kanon/kit/kit.md`), consumer artifact (`.kanon/kit.md`), `_scaffold.py:_render_kit_md()`, atomic writes in `cli.py` + `_cli_aspect.py`, gate check in `scripts/check_kit_consistency.py`.
4. Updates substrate tests that depended on these.
5. Recaptures `.kanon/fidelity.lock` after kit YAML changes.
6. CHANGELOG entry under `[Unreleased] § Removed`.

## Scope

### In scope

#### A. `src/kanon/kit/manifest.yaml`

Delete the `defaults:` block (lines 26-30) and the `files:` block (lines 31-32). The `aspects:` block remains (dead since A.2.2 — substrate sources from entry-points; A.4 may delete it).

#### B. Substrate code — `defaults:` consumers

- `src/kanon/cli.py:249` — `for name in top.get("defaults", [])` removed (the surrounding loop becomes a no-op or is restructured).
- `src/kanon/cli.py:675` — `defaults: list[str] = list(top.get("defaults", []))` removed; followers updated.
- `src/kanon/_manifest.py:727` — function returning defaults removed; callers updated.

If any CLI surface used `defaults:` to drive `kanon init` behaviour (e.g., `--profile solo` enables defaults), that profile becomes a no-op or is deprecated. **Audit during implementation.**

#### C. Substrate code — `files:` consumers

- `src/kanon/cli.py:388-399` — kit-global file-scaffolding loop removed.
- `src/kanon/_scaffold.py:245-247` — same loop in `_build_bundle` removed.
- `src/kanon/_manifest.py:743` — `paths.extend(top.get("files", []) or [])` removed.

#### D. Substrate code — `kit.md`

- Delete `src/kanon/kit/kit.md` (template).
- Delete `src/kanon/_scaffold.py:_render_kit_md()` and the `_kit_root() / "kit.md"` read at `:411-416`.
- Delete kit.md atomic-writes in `src/kanon/cli.py:866-869` and `src/kanon/_cli_aspect.py:94, 152`.
- Delete `scripts/check_kit_consistency.py:_check_kit_md_exists()` and remove its call from `run_checks()`.
- Delete `tests/scripts/test_check_kit_consistency.py::test_missing_kit_md_detected` and `::test_kit_md_bad_heading_detected` (testing removed code).

#### E. Consumer-side artifact in kanon repo

Delete `.kanon/kit.md` from the kanon repo (it's a scaffolded artifact whose source/maintainer is being removed).

#### F. Tests

Audit and update:
- `tests/test_cli.py` (8 references to kit.md)
- `tests/test_cli_helpers.py` (5 references)
- `tests/test_kit_integrity.py` (4 references) — update or delete byte-equality / scaffolding tests
- `tests/test_cli_verify.py` (1 reference)
- Any test that asserts `defaults:` is honored by `kanon init` becomes obsolete.

#### G. Fidelity lock

Recapture `.kanon/fidelity.lock` (`kanon fidelity update .`) — kit YAML changes cascade through fixtures.

#### H. CHANGELOG

Paragraph under `[Unreleased] § Removed` naming Phase A.3 and the canonical sequence position.

### Out of scope

- **Aspect content move** (`src/kanon/kit/aspects/<X>/` → `src/kanon_reference/aspects/<X>/data/`) — defer until a dedicated sub-plan; nine `_kit_root()` call sites in `_scaffold.py` retire when content moves.
- **Substrate-independence CI gate** (`scripts/check_substrate_independence.py` per ADR-0044) — deferred again; greening it requires the test-overlay refactor that depends on content move.
- **`_detect.py` deletion** — A.4 territory.
- **Bare-name CLI sugar deprecation** — A.5.
- **Kit YAML's `aspects:` block deletion** — could ship now (dead since A.2.2) but bundling with content-move keeps surface area cohesive; defer.
- **Spec / design / ADR / principle changes** — none.

## Approach

1. **Delete `defaults:` block** from `src/kanon/kit/manifest.yaml`. Walk the 3 substrate consumers; for each, remove the read and adjust surrounding logic. Audit for any CLI surface (e.g., `kanon init --profile solo`) that depended on it; document in implementation comments.
2. **Delete `files:` block** from `src/kanon/kit/manifest.yaml`. Walk the 3 substrate consumers; remove the read; adjust scaffolding logic.
3. **Delete `kit.md`**: template, consumer-artifact, scaffolding code (in `_scaffold.py`, `cli.py`, `_cli_aspect.py`), CI gate check, and 2 obsolete gate tests.
4. **Audit tests** for kit.md / defaults / files references; update or delete as applicable.
5. **Recapture fidelity lock** with `kanon fidelity update .`.
6. **Run all gates** + full pytest. Fix regressions.
7. **CHANGELOG entry**.
8. Commit + push + auto-merge per "when done, merge".

## Acceptance criteria

### Kit YAML

- [ ] AC-Y1: `src/kanon/kit/manifest.yaml` no longer contains `defaults:` block.
- [ ] AC-Y2: `src/kanon/kit/manifest.yaml` no longer contains `files:` block.
- [ ] AC-Y3: `src/kanon/kit/manifest.yaml` `aspects:` block remains (dead but preserved).

### Substrate

- [ ] AC-S1: No source file references `top.get("defaults"`, `top["defaults"]`, or equivalent.
- [ ] AC-S2: No source file references `top.get("files"`, `top["files"]`, kit-global `files:`, or `_kit_root() / "files"`.
- [ ] AC-S3: No source file references `kit.md` for read/write/render.
- [ ] AC-S4: `src/kanon/kit/kit.md` template file no longer exists.
- [ ] AC-S5: `.kanon/kit.md` (kanon repo's consumer-side artifact) no longer exists.
- [ ] AC-S6: `_scaffold.py:_render_kit_md()` deleted.

### Gate

- [ ] AC-G1: `scripts/check_kit_consistency.py:_check_kit_md_exists()` deleted; not called from `run_checks()`.
- [ ] AC-G2: `tests/scripts/test_check_kit_consistency.py::test_missing_kit_md_detected` and `::test_kit_md_bad_heading_detected` deleted.

### Fidelity

- [ ] AC-F1: `.kanon/fidelity.lock` regenerated; `kanon verify .` returns `status: ok`, zero warnings.

### Tests

- [ ] AC-T1: All test files audited; kit.md / defaults: / files: references removed or updated.
- [ ] AC-T2: Full pytest suite passes (no regression beyond removed obsolete tests).

### CHANGELOG

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Removed` gains a paragraph naming Phase A.3.

### Cross-cutting

- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3: `python scripts/check_links.py` passes.
- [ ] AC-X4: `python scripts/check_foundations.py` passes.
- [ ] AC-X5: `python scripts/check_kit_consistency.py` passes (after `_check_kit_md_exists` deletion).
- [ ] AC-X6: `python scripts/check_invariant_ids.py` passes.
- [ ] AC-X7: `python scripts/check_packaging_split.py` passes.
- [ ] AC-X8: No `src/kanon_reference/` change (out of scope).
- [ ] AC-X9: No `src/kanon/kit/aspects/` content moved (out of scope; defer to content-move sub-plan).

## Risks / concerns

- **Risk: `kanon init --profile solo` (or similar) silently breaks.** The `defaults:` block fed those profiles. Mitigation: audit `cli.py:249` and surrounding logic during implementation; if a profile relied on defaults, document the new behaviour (probably "no aspects enabled — consumer must opt in") and adjust tests.
- **Risk: many test files reference `kit.md`.** Mitigation: audit each (8 in test_cli.py, 5 in test_cli_helpers.py, 4 in test_kit_integrity.py); for each reference, either remove the test (if it tests removed kit.md mechanics) or adapt it (if it just incidentally mentions kit.md).
- **Risk: byte-equality fixtures in fidelity.lock cite kit.md.** Mitigation: `kanon fidelity update .` regenerates; verify post-regen that no entry references the deleted file.
- **Risk: AGENTS.md scaffolding referenced kit.md.** Verify scaffolded AGENTS.md doesn't have a "see `.kanon/kit.md`" pointer that's now dead. Update template if it does.
- **Risk: `--profile solo` / `--profile team` / `--profile all` / `--profile max` semantics change.** Per [ADR-0037](../../decisions/0037-profile-rename-and-max.md) those profiles are user-visible. If `defaults:` deletion changes their behaviour, ADR-0037 is implicitly amended; document in CHANGELOG explicitly.

## Documentation impact

- **Touched files:** `src/kanon/kit/manifest.yaml` (delete 2 blocks); `src/kanon/cli.py` (3 sites); `src/kanon/_scaffold.py` (~3 sites + delete `_render_kit_md`); `src/kanon/_manifest.py` (2 sites); `src/kanon/_cli_aspect.py` (2 sites); `scripts/check_kit_consistency.py` (delete `_check_kit_md_exists`); `tests/scripts/test_check_kit_consistency.py` (delete 2 tests); `tests/test_cli.py`, `tests/test_cli_helpers.py`, `tests/test_kit_integrity.py`, `tests/test_cli_verify.py` (audit + update); `.kanon/fidelity.lock`; `CHANGELOG.md`.
- **Deleted files:** `src/kanon/kit/kit.md`; `.kanon/kit.md`.
- **New files:** `docs/plans/phase-a.3-kit-globals-deletion.md`.
- **No changes to:** specs, designs, ADRs, foundations, principles, protocol prose, `src/kanon_reference/`, aspect manifests, top-level `pyproject.toml`.
