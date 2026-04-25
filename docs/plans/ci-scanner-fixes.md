---
feature: ci-scanner-fixes
serves: docs/specs/deps.md, docs/specs/testing.md
design: "Follows ADR-0011 (kit consistency byte-equality) — pattern instantiation; bug fixes only."
status: done
date: 2026-04-25
---
# Plan: CI scanner false-positive fixes (`check_deps.py`, `check_test_quality.py`)

## Context

Audit risks R5 and R9. Both scripts are kit-shipped (consumers receive them via the `deps` and `testing` aspects at depth 2+) and exist in two copies under ADR-0011 byte-equality:

| Script | Repo path | Kit path |
|---|---|---|
| `check_deps.py` | `ci/check_deps.py` | `src/kanon/kit/aspects/deps/files/ci/check_deps.py` |
| `check_test_quality.py` | `ci/check_test_quality.py` | `src/kanon/kit/aspects/testing/files/ci/check_test_quality.py` |

Both bugs are false positives — they emit findings on benign input — and undermine the validators' credibility.

### R5 — `check_deps.py:_check_pyproject_toml` flags `requires-python`

Today's behavior: `in_deps` flips to `True` on encountering the literal line `[project]`, and stays true until the next line beginning with `]`. Result: `requires-python = ">=3.10"` (a PEP 621 Python-language constraint, not a package dependency) matches `_PYPROJECT_UNPINNED` and is reported as an unpinned dependency. The repo's own `pyproject.toml:11` triggers this on every run.

Fix: tighten `in_deps` to mean "inside the `dependencies = [...]` array" (and `optional-dependencies` arrays), not "inside the `[project]` table". The `[project]` header should not flip the state at all.

### R9 — `check_test_quality.py:_find_test_files` walks `.venv/`

Today's behavior: `root.rglob(pattern)` descends into `.venv/`, picking up Python's site-packages. The repo's run reports 11 warnings on `.venv/lib/python3.11/site-packages/mypy*` test files. `check_deps.py` already has a `_SKIP_DIRS` set; `check_test_quality.py` does not.

Fix: introduce the same skip-set in `check_test_quality.py` and apply it during file collection.

## Tasks

- [x] T1: In `check_deps.py:_check_pyproject_toml`, replaced the loose `[project]` state machine with one that flips `in_deps = True` only on lines matching `<name> = [` (covering `dependencies` and `[project.optional-dependencies]` group bodies). Mirrored in both copies (`ci/check_deps.py` and `src/kanon/kit/aspects/deps/files/ci/check_deps.py`); byte-equality preserved.

- [x] T2: In `check_test_quality.py`, added `_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}` and filtered `_find_test_files` by `any(part in _SKIP_DIRS for part in p.relative_to(root).parts)`. Mirrored in both copies.

- [x] T3: Added `test_pyproject_requires_python_alone_is_not_a_dependency` and `test_pyproject_requires_python_skipped_alongside_dependencies` to `tests/ci/test_check_deps.py`.

- [x] T4: Added `test_pyproject_dependency_array_still_scanned` and `test_pyproject_optional_dependencies_block_scanned`. Used exotic `">=1.0"` entries because the existing `_PYPROJECT_UNPINNED` regex requires the operator to immediately follow the opening quote — the realistic `"name>=1.0"` form does not match the regex (a separate pre-existing limitation, out of scope for this plan).

- [x] T5: Added `test_skip_dirs_excludes_venv_and_friends` to `tests/ci/test_check_test_quality.py` — verifies `_find_test_files` skips `.venv/` and `node_modules/` while still picking up `tests/test_real.py`.

- [x] T6: `python ci/check_kit_consistency.py` returns exit 0; `diff` between repo and kit copies is empty for both files.

- [x] T7: `CHANGELOG.md` `## [Unreleased] / ### Fixed` carries two entries covering both fixes.

## Acceptance Criteria

- [x] AC1: `python ci/check_deps.py` against the repo emits zero findings (was 1: false positive on `requires-python = ">=3.10"`).
- [x] AC2: `python ci/check_test_quality.py` against the repo emits zero `.venv/`-related warnings (was 11).
- [x] AC3: `python ci/check_kit_consistency.py` returns exit 0; both kit/repo copies are byte-identical.
- [x] AC4: `pytest` passes — new regression tests (T3–T5) pass alongside the 305 prior tests.
- [x] AC5: `ruff check` clean on changed files. (Three pre-existing SIM117 errors in `tests/ci/test_release_preflight.py` are unrelated.)

## Documentation Impact

- `CHANGELOG.md`: one consolidated `### Fixed` entry under `## [Unreleased]` (T7) — both bugs were user-observable warnings emitted into consumer projects.
- No spec amendment: `docs/specs/deps.md` and `docs/specs/testing.md` already promise the *intent* of these scanners; the changes correct buggy implementations of that intent.
- No README change.
