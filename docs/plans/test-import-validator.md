---
status: done
design: "Follows ADR-0028"
date: 2026-04-27
---
# Plan: Test-Import Validator

## Goal

Add a kit validator that detects test files under `tests/ci/` referencing
CI scripts that don't exist on disk.  This catches the exact class of bug
that broke sensei's CI after its kanon migration (Phase G deleted a CI
script but left its companion test file behind).

## Scope

- New validator module: `src/kanon/_validators/test_import_check.py`
- Registered under `kanon-testing` depth-2 (CI scripts are a depth-2
  artifact for testing/security/deps aspects).
- Scans `tests/ci/test_*.py` for the canonical path-construction pattern
  (`_REPO_ROOT / "ci" / "<name>.py"`) and verifies the referenced script
  exists.
- Emits **errors** for missing scripts — an orphaned test that aborts
  collection is never intentional.

## Out of scope

- Dynamic imports, pytest plugins, or conftest fixtures.
- Test files outside `tests/ci/` (those don't follow the CI-script
  companion pattern).
- Validating that the CI script is syntactically correct.

## Tasks

- [x] Write `src/kanon/_validators/test_import_check.py`
- [x] Register in `src/kanon/kit/aspects/kanon-testing/manifest.yaml`
  under `depth-2: validators:`
- [x] Add tests: orphan detected, clean repo passes, missing tests/ci/
  dir skipped, self-hosting test
- [x] Verify: `pytest` green, `ruff check` clean

## Acceptance Criteria

1. `kanon verify .` on a project with a test file referencing a missing
   CI script reports an error with the test file path and missing script.
2. `kanon verify .` on the kanon repo itself passes.
3. The validator skips projects without a `tests/ci/` directory.
4. Only the canonical pattern is matched — no false positives on
   unrelated Path constructions.
