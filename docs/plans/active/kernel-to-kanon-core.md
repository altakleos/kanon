---
slug: kernel-to-kanon-core
status: approved
owner: makutaku
created: 2026-05-03
related-adr: 0054
---

# Plan — `kernel` → `kanon_core` Python module rename + source-tree move

## Context

ADR-0054 (accepted) committed to:
1. Python module rename: `kernel` → `kanon_core`
2. Source-tree move: `kernel/` → `packages/kanon-core/src/kanon_core/`
3. Per-package pyproject: `packages/kanon-core/pyproject.toml`
4. Keep `kanon-kit` as the only PyPI ship target until ADR-0053's forcing function fires

This plan executes (1)+(2)+(3). The kanon-aspects rename + move is a sibling plan (`kanon-reference-to-kanon-aspects`) executed in a subsequent PR. The full workspace-coordinator conversion (root pyproject becomes `[tool.uv.workspace]` only, kanon-kit becomes a meta-package) is deferred to a final PR after both renames land.

The risk class is the **same as ADR-0050 Option A** (PRs #96, #97, #98, #99, #100, #102, #104, #107 over 12 hours). Mitigations: the new `make wheel-check` (PR #106 + #107) catches sdist/wheel regressions before tag-push; the wheel-validator was added precisely to catch the regression class produced by ADR-0050's lap.

## Acceptance criteria

- AC1: `packages/kanon-core/src/kanon_core/__init__.py` exists; `kernel/` does not.
- AC2: All Python imports updated: `from kernel` → `from kanon_core`; `import kernel` → `import kanon_core`. Both 1-arity (`from kernel import X`) and dotted (`from kernel._validators import Y`) forms covered.
- AC3: `packages/kanon-core/pyproject.toml` exists; `name = "kanon-core"`; uses Hatchling's prefix-REMOVE form (`only-include = ["src"]; sources = ["src"]`); `cd packages/kanon-core && python -m build` produces a `kanon_core-X.Y.Z-py3-none-any.whl` containing `kanon_core/...`.
- AC4: `cd packages/kanon-core && pip install -e .` succeeds (PEP 660 editable install — the form `editables` accepts).
- AC5: Root `pyproject.toml` continues to publish `kanon-kit` as the monolith. Updates: `[tool.hatch.version] path = "packages/kanon-core/src/kanon_core/__init__.py"`; `[tool.hatch.build.targets.wheel] packages = ["packages/kanon-core/src/kanon_core", "src/kanon_reference"]`; `[project.scripts] kanon = "kanon_core.cli:main"`; mypy/ruff/coverage configs retarget `kanon_core` (NOT `packages/kanon-core/src/kanon_core` — that reads as path; mypy wants module name).
- AC6: `kernel/_manifest.py` validator allow-list at line 238 stays `("kanon-aspects", "kanon-kit")` — distribution names, not module names. The error messages around it that mention "kanon-core" stay as-is.
- AC7: Aspects' loader files at `src/kanon_reference/aspects/kanon_<slug>/loader.py` update their `from kernel.X import Y` imports to `from kanon_core.X import Y`. Aspect manifest dotted paths (validators) update.
- AC8: `Makefile` typecheck + lint targets retarget `kanon_core/` (or appropriate path). `make check` succeeds.
- AC9: `scripts/check_*.py` files referencing `kernel/` paths update to the new location. `scripts/check_wheel_build.py` and `scripts/check_package_contents.py` updated to expect `kanon_core/` in the wheel (instead of `kernel/`).
- AC10: `tests/test_aspect_registry.py` + any other test that mentions kernel module name updates.
- AC11: `.kanon/config.yaml` preflight stages: `import kernel; kernel.__version__` → `import kanon_core; kanon_core.__version__`.
- AC12: All 7 standalone gates green.
- AC13: `pytest -q` passes.
- AC14: `make wheel-check` produces `status: ok` against the wheel.
- AC15: `kanon verify .` status=ok; fidelity recaptured.
- AC16: CHANGELOG `[Unreleased]` entry under `### Changed`.

## Scope

### In
- Source-tree move: `kernel/` → `packages/kanon-core/src/kanon_core/`.
- All Python imports of `kernel` updated to `kanon_core`.
- `packages/kanon-core/pyproject.toml` authored (build-correct standalone — could publish if desired).
- Root `pyproject.toml` retargeted to use the new paths; STAYS the kanon-kit publisher.
- `Makefile`, `scripts/check_*.py`, `tests/test_aspect_registry.py`, `.kanon/config.yaml`, aspect loader imports, validator dotted paths, fidelity.lock.
- CHANGELOG `[Unreleased]` entry.
- Doc cite sweep across foundational/spec/design docs (NOT ADRs — those are immutable; "kernel" stays in their bodies).

### Out
- `kanon_reference` → `kanon_aspects` rename (sibling plan).
- Workspace coordinator conversion of root pyproject (final PR after both renames).
- Actual three-distribution PyPI publish (deferred per ADR-0053).
- ADR body updates (immutable; per ADR-0054 historical surfaces NOT retroactively rewritten).
- Archived plan body updates.
- Git history rewrites.

## Steps

1. `git mv kernel/ packages/kanon-core/src/kanon_core/` (create intermediate dirs first via touch+rm or mkdir).
2. Sed across all `.py` files: `from kernel\.` → `from kanon_core.`; `from kernel ` → `from kanon_core `; `import kernel\b` → `import kanon_core` (carefully — preserve `import kernel.X as kernel` patterns if any). Use word-boundary regex.
3. Sed `kernel/_validators` → `kanon_core/_validators` and similar dotted forms in YAML/manifests.
4. Author `packages/kanon-core/pyproject.toml`.
5. Update root `pyproject.toml`: hatch.version path, wheel packages, scripts entry, mypy packages, coverage source, ruff src.
6. Update `Makefile` typecheck + lint targets.
7. Update `scripts/check_package_contents.py` `_CORE_REQUIRED_FILES` from `kanon/...` → `kanon_core/...` (this script was already updated in PR #99 to expect `kernel/...`; now needs another update). Also `kernel/kit/` → `kanon_core/kit/`.
8. Update `scripts/check_wheel_build.py` `_KERNEL_INIT` constant.
9. Update `.kanon/config.yaml` preflight stage's import statement.
10. Update aspect manifests + loader files: `kanon_reference.X` validator paths might reference kernel internals.
11. Update test fixtures.
12. Run `uv sync --reinstall --all-extras` to refresh editable install.
13. `python -c "import kanon_core; print(kanon_core.__version__)"` — should work.
14. `make typecheck` + `make lint` — should pass.
15. `pytest -q` — should pass (any failures: trace + fix).
16. `kanon verify .` — should be ok or have fidelity warnings.
17. `kanon fidelity update .` if needed.
18. `make wheel-check` — should produce `status: ok` against the wheel.
19. CHANGELOG `[Unreleased]` entry.
20. Commit, push, PR, auto-merge.

## Risks

- **Hatchling wheel-build path rewriting**: when root pyproject says `packages = ["packages/kanon-core/src/kanon_core"]`, the wheel layout is `kanon_core/...` (basename of last path component). Verify experimentally before committing. If Hatch insists on path-prefix preservation, may need `[tool.hatch.build.targets.wheel.sources] "packages/kanon-core/src/kanon_core" = "kanon_core"` — which is the prefix-RENAME form that breaks editable installs. Mitigation: test early; if necessary, the dev loop installs from `packages/kanon-core/` directly via `pip install -e packages/kanon-core` and root pyproject only handles the publish wheel build.
- **Aspect bundle import-path discovery**: aspect loaders import from kernel internals (`from kernel._foo import bar`). After rename: `from kanon_core._foo import bar`. The entry-point group `kanon.aspects` and the loader manifest paths stay (they're string identifiers; only the module names inside change).
- **Fidelity drift**: many fidelity-watched files will change. Recapture once at the end.
- **Validator allow-list interpretation**: `kernel/_manifest.py:238`'s `("kanon-aspects", "kanon-kit")` are DISTRIBUTION names (PyPI artifacts). The Python module rename doesn't affect them. Tests should still pass; if any test was checking `kernel.X` module name as a string, it needs updating.
