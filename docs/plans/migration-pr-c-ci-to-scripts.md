---
status: approved
slug: migration-pr-c-ci-to-scripts
date: 2026-05-02
---

# Plan: Migration PR C — `ci/` → `scripts/` (per ADR-0049 §Implementation Roadmap step C)

## Goal

Rename the top-level `ci/` directory to `scripts/` and make it a proper Python package (`scripts/__init__.py`). Honors ADR-0049 §1(5): "ci/ → scripts/ as a proper Python package." Eliminates the `importlib.util.spec_from_file_location` test-infra fragility surfaced by PRs #80–82.

## Scope

In scope:
- `git mv ci scripts`; hoist `scripts/ci/*` up to `scripts/` (the existing top-level `scripts/` already had worktree shell scripts; merge).
- Add `scripts/__init__.py` to make it a Python package.
- `git mv tests/ci tests/scripts` and update `tests/scripts/conftest.py` to point at the new path.
- Update `.github/workflows/{checks,verify,release}.yml` to invoke `scripts/check_*.py` (was `ci/check_*.py`).
- Update `src/kanon/_validators/test_import_check.py` regex + path scanning to look for `scripts/` references in `tests/scripts/`.
- Sweep substrate-internal doc/code refs (`docs/contributing.md`, `docs/kanon-implementation.md`, `src/kanon/_graph.py` comments, etc.).
- Update `src/kanon_reference/aspects/kanon_sdd/protocols/adr-immutability.md` (substrate self-reference) + mirror to `.kanon/protocols/kanon-sdd/adr-immutability.md` (kit-consistency byte-equality preserved until PR F loosens).
- Update test files inside `tests/scripts/` whose docstrings + path constants still cited `ci/`.
- Recapture fidelity lock.

Out of scope:
- Consumer-facing prose where `ci/` is shown as an EXAMPLE of where a consumer might put their CI scripts (e.g., the kanon-release protocol's `python ci/release-preflight.py` recommendation; the kanon-sdd scaffolded README that mentions `ci/check_foundations.py`). These remain because consumers choose their own CI script location; the substrate's own choice doesn't bind them.

## Acceptance criteria

- AC1: `ci/` directory no longer exists; `scripts/` contains the 15 check scripts + `release-preflight.py` + `__init__.py` + the prior worktree shell scripts.
- AC2: `tests/ci/` no longer exists; `tests/scripts/` mirrors it.
- AC3: All 7 standalone gates pass when invoked as `python scripts/check_X.py`.
- AC4: Full pytest passes (no new failures from path moves).
- AC5: GitHub Actions workflows invoke gates via `scripts/check_X.py`.
- AC6: `kanon verify .` exits 0; substrate-internal `_validators/test_import_check.py` scans `tests/scripts/` for canonical `_REPO_ROOT / "scripts" / ...` patterns.

## Steps

1. `git mv ci scripts` then hoist `scripts/ci/*` → `scripts/` (existing top-level `scripts/` had shell scripts).
2. `touch scripts/__init__.py`.
3. `git mv tests/ci tests/scripts`; update `tests/scripts/conftest.py` REPO_ROOT path.
4. Sed-update workflow files.
5. Sed-update doc files (substrate-internal only).
6. Update `src/kanon/_validators/test_import_check.py` regex + paths.
7. Update test files for new path constants + docstrings.
8. Mirror substrate-self-reference change in `adr-immutability.md` to `.kanon/protocols/...`.
9. Run gates + pytest; fix any remaining hardcoded refs.
10. Recapture fidelity.
11. CHANGELOG entry.
12. Commit + push + PR.

## Verification

- `test ! -d ci/ && test -d scripts/ && test -f scripts/__init__.py && echo OK`
- `test ! -d tests/ci/ && test -d tests/scripts/ && echo OK`
- `pytest --no-cov -q` → 964 passed
- 7 gates → ok
