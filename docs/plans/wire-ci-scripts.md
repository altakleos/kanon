---
status: done
design: "Follows existing CI workflow pattern in verify.yml"
---

# Plan: Wire unwired CI scripts into GitHub Actions workflows

## Problem

7 of 13 CI scripts in `ci/` are not invoked by any GitHub Actions workflow.
AGENTS.md and aspect body sections claim these scripts are active enforcement —
contributors believe they're enforced; they aren't.

## Changes

### 1. Add 5 scripts to `verify.yml` test job

Append these steps after the existing `check_commit_messages` step:

| Script | Step name | Invocation | Fail mode |
|--------|-----------|------------|-----------|
| `check_test_quality.py` | Check test quality | `python ci/check_test_quality.py` | hard-fail |
| `check_security_patterns.py` | Check security patterns (warnings) | `python ci/check_security_patterns.py` | warn-only (no `--strict`) |
| `check_deps.py` | Check dependency hygiene (warnings) | `python ci/check_deps.py` | warn-only |
| `check_status_consistency.py` | Check status consistency (warnings) | `python ci/check_status_consistency.py` | warn-only |
| `check_verified_by.py` | Check spec invariant coverage | `python ci/check_verified_by.py` | hard-fail |
| `check_invariant_ids.py` | Check invariant IDs | `python ci/check_invariant_ids.py` | hard-fail |

Notes:
- `check_security_patterns.py` runs without `--strict` — matching its documented
  "warn" behavior in AGENTS.md. The `--strict` flag exists but the aspect body
  says "safety net, not a SAST replacement."
- None of these scripts need git history or `--base-ref`.
- No new dependencies required.

### 2. `release-preflight.py` — no change

This script requires `--tag` and internally runs pytest/ruff/kanon-verify.
It's a release-gate script, not a PR check. It's already referenced by the
`release-checklist` protocol as a manual pre-tag step. Wiring it into
`release.yml` would duplicate the verify job's pytest/ruff/mypy steps.
Leave as-is — it's intentionally a manual gate.

### 3. Verify existing CI passes with new steps

Run all 6 new scripts locally to confirm they pass on the current codebase
before committing the workflow change.

## Acceptance criteria

- [x] All 6 scripts appear as named steps in `verify.yml`
- [x] Hard-fail scripts (`check_test_quality`, `check_verified_by`, `check_invariant_ids`) exit 0 on current codebase
- [x] Warn-only scripts (`check_security_patterns`, `check_deps`, `check_status_consistency`) run without error
- [x] No changes to `release.yml`
- [x] `release-preflight.py` remains unwired (intentional — documented in plan)

## Out of scope

- Changing any script's exit-code behavior
- Adding `--strict` to `check_security_patterns.py`
- Wiring `release-preflight.py` into `release.yml`
