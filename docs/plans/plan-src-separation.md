---
status: done
design: "Extends existing check_process_gates.py"
---

# Plan: Enforce plan/src commit separation

## Problem

An agent can create a plan file with `status: accepted` and modify `src/`
files in the same commit. The co-presence gate passes because it only checks
that a plan exists in the diff — not that it was committed separately.
This defeats the "plan before build" intent.

## Solution

In PR mode (`--base-ref`), walk individual commits and warn if any single
commit touches both `docs/plans/*.md` and `src/` files. In push mode
(single commit), the same check applies to HEAD.

This is a **warning**, not a hard error — allowing retroactive fixes via
a follow-up commit that adds the plan. The co-presence check remains the
hard gate; separation is an additional signal.

Exempted by `Trivial-change:` trailer (same as the plan co-presence check).

## Changes

### 1. Add `_check_plan_src_separation()` to `check_process_gates.py`

Walk commits in the range. For each commit, get its changed files. If a
commit touches both `docs/plans/*.md` and `src/` — and has no
`Trivial-change:` trailer — emit a warning.

### 2. Add tests

- Same-commit plan+src in push mode → warning
- Same-commit plan+src with Trivial-change → no warning
- Separate commits (plan then src) → no warning
- PR mode with mixed commit → warning

### 3. Update docstring

## Acceptance criteria

- [x] Same-commit plan+src produces a warning
- [x] Trivial-change trailer exempts the warning
- [x] Separate commits produce no warning
- [x] Existing tests still pass
- [x] Warning does not change exit code (exit 0 for warn)
