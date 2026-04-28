---
status: done
design: "Follows ADR-0031 (fidelity-aspect)"
spec: "docs/specs/fidelity.md"
---

# Plan: Close `_fidelity.py` Coverage Gaps (74% → 90%+)

## Goal

Bring `src/kanon/_fidelity.py` from 74% to ≥90% branch coverage by adding
targeted tests for the 51 uncovered statements and 8 partial branches.

## Scope

**In scope:** new tests in `tests/test_fidelity.py` only.
**Out of scope:** source changes, refactoring, other modules.

## Coverage Gap Analysis

| Priority | Area | Lines | Statements | Description |
|----------|------|-------|------------|-------------|
| P1 | `parse_fixture` — `pattern_density` validation | 196–239 | ~44 | Entire pd parsing block: non-list pd_raw, non-dict entries, single `pattern` key, `patterns` not a list, empty patterns, non-number min/max, min>max, non-string pattern, invalid regex, valid construction |
| P2 | `parse_fixture` — `word_share` error branches | 176, 181, 183, 187 | ~4 | Non-dict word_share, non-number min, non-number max, min>max |
| P3 | `_string_list` — non-list branch | 78 | ~1 | Value is not None and not a list |
| P4 | `parse_fixture` — early exits | 104–105, 109 | ~3 | OSError on file read, missing YAML frontmatter |
| P5 | `_extract_all_turns` — empty match | 285 | ~1 | No turn markers found → empty list |

## Acceptance Criteria

1. `pytest tests/test_fidelity.py --cov=kanon._fidelity --cov-branch` reports ≥90%.
2. All existing tests continue to pass (no regressions).
3. Full suite `pytest` passes with overall coverage ≥90%.
4. `ruff check` clean.
5. New tests follow existing patterns in `test_fidelity.py` (fixture-file-in-tmp_path style).

## Tasks

### T1: pattern_density validation tests (P1)

Add tests for `parse_fixture` with `pattern_density` frontmatter covering:
- `pattern_density` is not a list (e.g., a string)
- Entry is not a dict (e.g., a bare string in the list)
- Single `pattern` key (string) → valid
- `patterns` is not a list
- Empty patterns (no `pattern` or `patterns`)
- `min` is not a number
- `max` is not a number
- `min > max`
- Non-string entry in patterns list
- Invalid regex pattern
- Valid entry with all fields → successful `PatternDensityEntry` construction

### T2: word_share error branch tests (P2)

Add tests for `parse_fixture` with `word_share` frontmatter covering:
- `word_share` is not a dict (e.g., a string)
- `word_share.min` is not a number
- `word_share.max` is not a number
- `word_share.min > word_share.max`

### T3: _string_list non-list branch (P3)

Add test for `parse_fixture` where a list field (e.g., `forbidden_phrases`) is
given a non-list value (e.g., an integer).

### T4: parse_fixture early exits (P4)

- Test with an unreadable file (chmod 000 or mock OSError).
- Test with a file that has no YAML frontmatter.

### T5: _extract_all_turns empty match (P5)

Test `evaluate_fixture` (or `_extract_all_turns` directly) with dogfood text
containing no turn markers.

## Verification

Run after implementation:
```bash
.venv/bin/pytest tests/test_fidelity.py --cov=kanon._fidelity --cov-report=term-missing --cov-branch -q
.venv/bin/pytest --tb=short -q
.venv/bin/ruff check src/ tests/
```
