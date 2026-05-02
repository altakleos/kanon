---
status: approved
slug: migration-pr-a-bundle-collapse
date: 2026-05-02
---

# Plan: Migration PR A — Bundle collapse (per ADR-0049 §Implementation Roadmap)

## Goal

Collapse the per-aspect loader-stub + data-dir split (`src/kanon_reference/aspects/kanon_<slug>.py` + `src/kanon_reference/data/kanon-<slug>/`) into a single self-contained per-aspect bundle directory under `src/kanon_reference/aspects/kanon_<slug>/`. First step in the 6-PR migration sequence ratified by ADR-0049.

## Background

ADR-0049 §1(3) commits to per-aspect bundles. Today's split (loader Python module in one tree, data YAML+prose in another) was a Phase A.7 transitional artifact that the panel's archaeology (P7) identified as a maintenance friction point. PR A executes the collapse — the lowest-risk migration step per the panel's empirical cost-ranking.

## Naming convention reconciliation

ADR-0049 §1(3) wrote the example as `aspects/kanon-<slug>/{__init__.py, loader.py, ...}` with **hyphen** in the directory name. Python imports require **underscore** for module/package names. Resolution: bundle directory uses underscore (`aspects/kanon_<slug>/`) for Python compatibility; aspect SLUG remains `kanon-<slug>` everywhere it's user-visible (config, CLI, entry-points, prose). The two are connected by simple `_` ↔ `-` substitution. The ADR's normative claim ("each aspect is one self-contained directory containing loader + data") is honored; the example's hyphen was a typo that the implementation corrects.

## Scope

In scope:
- For each of 7 aspects (`kanon-deps`, `kanon-fidelity`, `kanon-release`, `kanon-sdd`, `kanon-security`, `kanon-testing`, `kanon-worktrees`):
  - Convert `src/kanon_reference/aspects/kanon_<slug>.py` (LOADER module) → `src/kanon_reference/aspects/kanon_<slug>/loader.py`.
  - Move `src/kanon_reference/data/kanon-<slug>/<contents>` → `src/kanon_reference/aspects/kanon_<slug>/<contents>` (manifest.yaml, protocols/, files/, sections/, agents-md/).
  - Add `src/kanon_reference/aspects/kanon_<slug>/__init__.py` to make the bundle a Python package (importlib.resources accessible).
- Delete the now-empty `src/kanon_reference/data/` tree.
- Update `pyproject.toml` entry-points: `kanon-<slug> = "kanon_reference.aspects.kanon_<slug>.loader:MANIFEST"`.
- Mirror entry-point change in `packaging/reference/pyproject.toml` (schema-of-record).
- Update `src/kanon/_manifest.py:_load_aspects_from_entry_points` `_source` synthesis: `Path(kanon_reference.__file__).parent / "aspects" / slug.replace("-", "_")`.
- Update `src/kanon/_manifest.py:_aspect_path` fallback similarly.
- Update `tests/test_kanon_reference_manifests.py` `_KIT_ASPECTS` constant to point at `aspects/kanon_<slug>/`.
- Update `scripts/check_kit_consistency.py` `_aspect_root()` if it has hardcoded `data/` path.
- Update `scripts/check_packaging_split.py` if its entry-point validation expects the old target.
- Update 7 manifest YAML header comments to cite new path (`src/kanon_reference/aspects/kanon_<slug>/files/` etc.).
- Update 7 LOADER docstring path refs.
- Recapture fidelity lock (.kanon/fidelity.lock).
- CHANGELOG entry.

Out of scope (deferred to subsequent migration PRs):
- Killing `packaging/` (PR B).
- Renaming `scripts/` → `scripts/` (PR C).
- `docs/plans/` partition (PR D).
- `src/kanon/` → `kernel/` (PR E).
- Loosening `check_kit_consistency.py` byte-mirror clause (PR F).

## Acceptance criteria

- AC1: All 7 aspects are bundles at `src/kanon_reference/aspects/kanon_<slug>/{loader.py, __init__.py, manifest.yaml, protocols/, ...}`.
- AC2: `src/kanon_reference/data/` no longer exists.
- AC3: `pyproject.toml` entry-points target `kanon_reference.aspects.kanon_<slug>.loader:MANIFEST`.
- AC4: `kanon verify .` exits 0; aspect data resolves via the new path.
- AC5: Full pytest passes (978+ tests; expect some test-data-path constants to need updating).
- AC6: 8 standalone gates pass.
- AC7: `tests/test_kanon_reference_manifests.py` equivalence tests still pass (LOADER's MANIFEST dict equals YAML's parsed content).
- AC8: Self-host conformance: `.kanon/protocols/<aspect>/...` files still match their counterparts in `aspects/kanon_<slug>/protocols/...` (or `check_kit_consistency.py` updated to read from new path).
- AC9: `python scripts/check_substrate_independence.py` still passes.

## Steps

1. Survey all hardcoded path references via grep + record.
2. For each aspect (7×): mkdir bundle dir, git mv loader, git mv data subtree contents, create __init__.py.
3. Delete empty `src/kanon_reference/data/`.
4. Update `pyproject.toml` + `packaging/reference/pyproject.toml` entry-points.
5. Update `_manifest.py` (2 sites: `_load_aspects_from_entry_points` line ~531, `_aspect_path` line ~723).
6. Update `tests/test_kanon_reference_manifests.py` `_KIT_ASPECTS`.
7. Update `scripts/check_kit_consistency.py` if needed.
8. Update `scripts/check_packaging_split.py` if needed.
9. Update 7 manifest YAML header comments + 7 LOADER docstring comments.
10. Re-run `uv pip install -e .` so entry-points are re-registered with new targets.
11. Run gates one at a time; fix issues.
12. Run full pytest; fix test breakage.
13. Recapture fidelity lock.
14. CHANGELOG entry.
15. Commit + push + PR + merge.

## Verification

- `kanon verify .` → ok
- 8 gates → ok
- `pytest --no-cov -q` → 978+ passed
- `kanon aspect list` → shows all 7 aspects with correct metadata
- Bundle structure: `find src/kanon_reference/aspects -type d -name "kanon_*" | wc -l` → 7
- No data dir: `test ! -d src/kanon_reference/data && echo OK`

## Risk + rollback

Risk: high — touches 50+ files including entry-point declarations + aspect-loader path synthesis. If anything goes wrong mid-migration, the substrate cannot find aspects and `kanon verify` breaks.

Rollback: `git revert <PR-A-merge-commit>` restores the prior layout. The PR is a single squash-merged commit, so revert is atomic.

Mitigation:
- Re-run `uv pip install -e .` after `pyproject.toml` changes to re-register entry-points with new targets.
- Verify each step incrementally — don't push until all gates green locally.
- The `_aspect_path` fail-loud fix from PR #82 will surface any path mismatch as an explicit ClickException, not a silent dead path.
