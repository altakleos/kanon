---
status: done
date: 2026-04-30
slug: high-coverage-gaps
---
# Plan: Test Coverage Gaps (Items 4 + 6)

## Goal

Add error-path tests to the highest-value untested modules and close the
`_detect.py` coverage gap.

## Changes

### Item 6: _detect.py coverage (85% → ~100%)

**File:** `tests/test_detect.py` (append to existing)

Add 3 tests:
1. **Node+TS detection** — `tmp_path` with `package.json` + `tsconfig.json` → `typecheck_cmd == "npx tsc --noEmit"`
2. **`_toml_has_section` OSError** — unreadable file → returns False
3. **ESLint config detection** — `tmp_path` with `.eslintrc.json` → detected

### Item 4: Error-path tests for highest-value modules

Scope to the 3 most impactful files (not all 16 — diminishing returns):

**a) `tests/test_fidelity.py`** — append error-path tests:
- Malformed YAML frontmatter → returns errors
- Missing required fields (protocol, actor) → returns errors
- Unreadable fixture file → returns errors

**b) `tests/test_graph.py`** — append error-path tests:
- Malformed frontmatter in a doc → handled gracefully
- Missing docs/ directory → no crash

**c) `tests/test_validators.py`** — append error-path tests:
- Validator receives nonexistent target → no crash
- Validator receives target with no docs/ → no crash

## Acceptance criteria

- [x] `_detect.py` coverage ≥ 95%
- [x] Error-path tests added to test_detect, test_fidelity, test_graph, test_validators
- [x] All existing tests pass
- [x] Overall coverage ≥ 94%
