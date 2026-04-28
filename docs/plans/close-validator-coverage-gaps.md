---
status: done
design: "Follows ADR-0031"
spec: "docs/specs/verification-contract.md"
---

# Plan: Close Validator Coverage Gaps

## Goal

Bring `_spec_design_parity.py` (82% → 90%+) and `_plan_completion.py` (89% → 90%+)
above the 90% coverage floor by adding targeted tests for uncovered defensive branches.

## Scope

**In scope:** new tests in `tests/test_spec_design_parity.py` and `tests/test_validators.py`.
**Out of scope:** source changes, other modules.

## Tasks

### T1: spec_design_parity.py (4 tests)

1. Spec named `_template.md` → skipped (line 30)
2. Unreadable spec file (OSError) → skipped (lines 33–34)
3. Spec without `---` prefix / no closing `---` → skipped (lines 36, 39)
4. Invalid YAML / non-dict frontmatter → skipped (lines 42–43, 45)

### T2: plan_completion.py (2 tests)

1. Plan with `---` start but no closing `---` → returns "" (line 37)
2. Plan with valid frontmatter but no `status:` key → returns "" (line 42, partial 40→38)

## Acceptance Criteria

1. Both modules report ≥90% branch coverage.
2. All existing tests pass. Full suite passes with overall ≥90%.
3. `ruff check` clean.
