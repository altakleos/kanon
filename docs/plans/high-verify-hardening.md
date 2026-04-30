---
status: done
date: 2026-04-30
slug: high-verify-hardening
---
# Plan: _verify.py Silent Exception Hardening + Test Coverage (Items 5 + 7)

## Goal

Add logging to silent exception blocks in `_verify.py` and add tests for the
untested custom validator error branches.

## Changes

### Item 7: Add logging to silent `except Exception:` blocks

**File:** `src/kanon/_verify.py`

**Line 273** — `run_kit_validators`: `except Exception: continue`
- Add `warnings.append(f"verify: {aspect_name}: validator lookup failed: {exc}")` so
  the failure surfaces in the verify report instead of being silently swallowed.
- Change `except Exception:` to `except Exception as exc:`.

**Line 336** — `check_fidelity_assertions`: `except Exception: continue`
- Same pattern: capture `exc`, append a warning.

### Item 5: Test custom validator error branches

**File:** `tests/test_verify_validators.py` (new file)

Test the three error branches in `run_project_validators` (lines 220, 237, 244):

1. **ImportError** — project-aspect manifest references a nonexistent module
   → verify reports error mentioning the module name
2. **Missing `check()` callable** — module exists but has no `check` function
   → verify reports error
3. **Runtime exception in `check()`** — module's `check()` raises
   → verify reports error with exception message

Also test the newly-surfaced warnings from item 7:

4. **Kit validator lookup failure** — corrupt aspect triggers warning (line 273)
5. **Fidelity provides lookup failure** — corrupt aspect triggers warning (line 336)

## Acceptance criteria

- [ ] Both silent `except Exception:` blocks now capture `exc` and append warnings
- [ ] 5 new tests covering all validator error branches
- [ ] All existing tests pass
- [ ] mypy clean
