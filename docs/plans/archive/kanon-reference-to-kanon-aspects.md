---
slug: kanon-reference-to-kanon-aspects
status: done
shipped-in: PR #114
owner: makutaku
created: 2026-05-03
related-adr: 0054
related-pr: 112
---

# Plan — `kanon_reference` → `kanon_aspects` Python module rename + source-tree move

## Context

Sibling to PR #112 (which moved `kernel/` → `packages/kanon-core/src/kanon_core/`). ADR-0054 §3 commits to:
- Python module rename: `kanon_reference` → `kanon_aspects`
- Source-tree move: `src/kanon_reference/` → `packages/kanon-aspects/src/kanon_aspects/`
- Per-package pyproject: `packages/kanon-aspects/pyproject.toml`
- Continue shipping kanon-kit as the only PyPI distribution per ADR-0053

This PR completes the second half of ADR-0054 §7's move-toward-final-layout work.

## Acceptance criteria

- AC1: `packages/kanon-aspects/src/kanon_aspects/__init__.py` exists; `src/kanon_reference/` does not.
- AC2: All Python imports updated: `from kanon_reference` → `from kanon_aspects`; `import kanon_reference` → `import kanon_aspects`.
- AC3: `packages/kanon-aspects/pyproject.toml` exists; `name = "kanon-aspects"`; uses prefix-REMOVE form (`only-include = ["src"]; sources = ["src"]`); `cd packages/kanon-aspects && python -m build` produces `kanon_aspects-X.Y.Z-py3-none-any.whl`.
- AC4: `cd packages/kanon-aspects && pip install -e .` succeeds (PEP 660 editable).
- AC5: Root `pyproject.toml` continues to publish `kanon-kit`. Updates: `[tool.hatch.build.targets.wheel] packages = ["packages/kanon-core/src/kanon_core", "packages/kanon-aspects/src/kanon_aspects"]`; `[tool.hatch.build.targets.sdist] include = [...]`; `[project.entry-points."kanon.aspects"]` dotted paths update from `kanon_reference.aspects.kanon_<slug>.loader:MANIFEST` → `kanon_aspects.aspects.kanon_<slug>.loader:MANIFEST`.
- AC6: Validator allow-list at `packages/kanon-core/src/kanon_core/_manifest.py:238` stays `("kanon-aspects", "kanon-kit")` — distribution names, not module names.
- AC7: Substrate-independence test (`scripts/check_substrate_independence.py`) still passes — kanon_core MUST NOT import kanon_aspects directly.
- AC8: Aspect manifests' `validators:` dotted paths stay `kanon_core._validators.X` (kernel side, unchanged from PR #112).
- AC9: All 7 standalone gates green; pytest 967 passing.
- AC10: `make wheel-check` produces `status: ok`.
- AC11: `kanon verify .` ok; fidelity recaptured.
- AC12: CI workflows (`checks.yml`, `verify.yml`) audited for any hardcoded `kanon_reference` or `src/kanon_reference` paths — fix proactively to avoid the PR #112 → #113 lap.
- AC13: Per the PR #112/#113 lesson: WAIT for ALL CI jobs (not just e2e) before relying on auto-merge.

## Scope

### In
- Source-tree move: `src/kanon_reference/` → `packages/kanon-aspects/src/kanon_aspects/`.
- All Python imports of `kanon_reference` updated to `kanon_aspects`.
- `packages/kanon-aspects/pyproject.toml` authored.
- Root `pyproject.toml` retargeted: wheel packages, sdist include, entry-points.
- `scripts/check_substrate_independence.py` — update its `kanon_reference` references.
- `scripts/check_kit_consistency.py` — already updated for kernel; check if it needs aspect-side updates.
- Test fixtures referencing `kanon_reference` or `src/kanon_reference/`.
- CI workflows: audit + fix proactively.
- CHANGELOG entry under `[Unreleased]`.
- Doc cite sweep across `docs/contributing.md`, `docs/kanon-implementation.md` (NON-immutable docs).

### Out
- ADR body updates to mention the new path (immutable per ADR-0032; allow-edit only for broken links found by `check_links.py`).
- Workspace coordinator conversion of root pyproject (separate final PR).
- PyPI publish of kanon-aspects (deferred per ADR-0053).

## Steps

1. `git mv src/kanon_reference/` → `packages/kanon-aspects/src/kanon_aspects/`.
2. Bulk sed Python imports: `from kanon_reference` → `from kanon_aspects`; `import kanon_reference` → `import kanon_aspects`.
3. Update root `pyproject.toml` entry-points dotted paths.
4. Update root `pyproject.toml` wheel.packages + sdist.include.
5. Author `packages/kanon-aspects/pyproject.toml`.
6. Update `scripts/check_substrate_independence.py` to reflect new module name.
7. Update test fixtures.
8. Audit + update `.github/workflows/checks.yml` and `.github/workflows/verify.yml` for any `kanon_reference` references (proactive — lesson from PR #112/#113).
9. Audit + update `docs/contributing.md` + `docs/kanon-implementation.md` (sed `src/kanon_reference/` → `packages/kanon-aspects/src/kanon_aspects/`).
10. Audit + fix any broken `../src/kanon_reference/` link refs in immutable ADRs/plans (Allow-ADR-edit trailer if needed).
11. Run `uv sync --reinstall --all-extras`.
12. `python -c "import kanon_aspects; print(kanon_aspects.__path__)"` — should work.
13. `make typecheck`, `make lint`, `pytest -q` — should pass.
14. `kanon verify .`, `kanon fidelity update .`.
15. `make wheel-check` — should produce `status: ok`.
16. CHANGELOG entry.
17. Commit, push, PR. **Wait for ALL jobs (not just e2e) before merging** per PR #113 lesson.

## Risks

- **Entry-points dotted paths**: the entry-point group `kanon.aspects` (per ADR-0040 protocol contract) stays — it's the GROUP that's protocol; the dotted-path VALUES inside change from `kanon_reference.aspects.X.loader:MANIFEST` → `kanon_aspects.aspects.X.loader:MANIFEST`. The substrate's discovery code (`packages/kanon-core/src/kanon_core/_manifest.py:272`) reads via `entry_points(group="kanon.aspects")` — unchanged.
- **Substrate-independence invariant**: `check_substrate_independence.py` enforces that `kanon_core` MUST NOT import `kanon_aspects` (and historically `kanon_reference`). Update that script's grep target.
- **Validator dotted paths**: aspect manifest YAML files have `validators: ["kanon_core._validators.X"]` — these are kernel-side, unchanged. But there might be aspect-loader dotted-paths in the entry-points block that need update.
- **CI workflow audit**: lesson from PR #113 — don't trust local-only checks.
