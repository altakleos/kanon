---
slug: uv-workspace-kit-meta
status: approved
owner: makutaku
created: 2026-05-04
related-adr: 0054
related-pr: 112 114
---

# Plan — uv workspace coordinator + `packages/kit-meta/` (per ADR-0054 §7)

## Context

Final step of ADR-0054 §7's move-toward-final-layout work. PRs #112 + #114 landed the per-package source moves + per-package pyprojects for `kanon-core` and `kanon-aspects`. This PR:

1. Adds `[tool.uv.workspace] members = ["packages/*"]` + `[tool.uv.sources]` to root `pyproject.toml` so `uv sync` installs all members editable.
2. Authors `packages/kit-meta/pyproject.toml` — the future-canonical kanon-kit meta-package publisher (declares `kanon-core` + `kanon-aspects` as PyPI dependencies). **Build-correct standalone but NOT published** — the active PyPI ship target stays the root pyproject's monolith wheel until ADR-0053's forcing function fires.

After this PR lands, the layout is fully aligned with ADR-0054 §1 except for the actual three-distribution PyPI publish (deferred per ADR-0053).

## Acceptance criteria

- AC1: Root `pyproject.toml` carries `[tool.uv.workspace] members = ["packages/kanon-core", "packages/kanon-aspects", "packages/kit-meta"]` and `[tool.uv.sources]` mapping each member as `{ workspace = true }`.
- AC2: Root `pyproject.toml` continues to carry `[project] name = "kanon-kit"` with the existing `dependencies = ["click", "pyyaml"]` and `[tool.hatch.build.targets.wheel] packages = [...]` collecting both source trees → still publishes the monolith wheel as today.
- AC3: `packages/kit-meta/pyproject.toml` exists. `name = "kanon-kit"` (DUPLICATE of root by design — the future-canonical publisher, swap-in when ADR-0053 forcing function fires). `dependencies = ["kanon-core==X.Y.Z", "kanon-aspects==X.Y.Z"]`. Hatchling build target ships zero source (meta-package). Lock-stepped version per ADR-0054 §6.
- AC4: `cd packages/kit-meta && python -m build --wheel` produces `kanon_kit-0.5.0a2-py3-none-any.whl` containing only meta + dist-info (no source).
- AC5: `uv sync` from repo root installs all 3 workspace members editable into one shared `.venv`.
- AC6: `pip install -e packages/kanon-core packages/kanon-aspects packages/kit-meta` works in fresh venv.
- AC7: `kanon verify .` ok; pytest 967 passing; `make wheel-check` status=ok against the kanon-kit monolith wheel built from root.
- AC8: CI workflows audited for any path that would break with the new layout — fix proactively.
- AC9: CHANGELOG `[Unreleased]` entry under `### Changed`.
- AC10: Wait for ALL CI jobs (not just e2e) before merging — per the lessons from PRs #112/#113/#114/#115/#116.

## Scope

### In
- Root `pyproject.toml` — add `[tool.uv.workspace]` + `[tool.uv.sources]` blocks.
- `packages/kit-meta/pyproject.toml` — new file, build-correct standalone.
- `packages/kit-meta/src/kanon_kit/__init__.py` — empty package marker (or omit if Hatchling supports zero-source meta packages).
- CHANGELOG entry.
- Doc cite sweep if any docs reference the missing `kit-meta` directory.

### Out
- Actual three-distribution PyPI publish (deferred per ADR-0053).
- Removing `[project]` from root pyproject (would break the active monolith publish).
- Source-tree refactors beyond what's already in main.

## Steps

1. Author `packages/kit-meta/pyproject.toml`.
2. Decide: does Hatchling allow zero-source wheels? If yes, omit `kanon_kit/__init__.py`. If no, author a tiny one.
3. Test `cd packages/kit-meta && python -m build --wheel` produces a clean meta-package wheel.
4. Add `[tool.uv.workspace] members = ["packages/kanon-core", "packages/kanon-aspects", "packages/kit-meta"]` + `[tool.uv.sources]` to root pyproject.
5. Run `uv sync` to verify workspace resolves.
6. Run `make wheel-check` to confirm root pyproject still publishes monolith correctly.
7. Run `pytest -q --no-cov` — should be 967 passing.
8. Run `kanon verify .`; fidelity update if needed.
9. CHANGELOG entry.
10. Audit CI workflows.
11. Commit, push, PR. **Do NOT use `--auto`** — wait for all CI jobs, then manually merge.

## Risks

- **Dual-publishing collision**: both root `pyproject.toml` and `packages/kit-meta/pyproject.toml` declare `name = "kanon-kit"`. As long as only ONE of them is the publish-active path (root), this is fine — they don't conflict at install time. The risk is contributor confusion. Mitigation: kit-meta/pyproject.toml carries a comment header explicitly stating it's NOT yet active; root carries a corresponding note.
- **Hatchling zero-source wheel**: I'm not 100% sure Hatchling can build a wheel with zero source files. Likely yes via `[tool.hatch.build.targets.wheel] only-include = []` or similar. Test experimentally; if necessary, add `kanon_kit/__init__.py` as a tiny stub.
- **uv workspace + active root [project]**: uv may complain about the mixed mode. Test `uv sync` explicitly.
- **Auto-merge race**: Per PRs #115/#116 lesson, do NOT use `--auto` here; wait for all jobs and merge manually.
