---
status: done
date: 2026-04-30
slug: low-hygiene-fixes
---
# Plan: Low-Priority Hygiene Fixes

## Goal

Address all 7 low/informational issues identified during the codebase analysis.

## Changes

### 1. Fix broken doc link in `docs/design/aspect-model.md`

**File:** `docs/design/aspect-model.md:213`
**Problem:** Link `[tier-up-advisor](.kanon/protocols/kanon-sdd/tier-up-advisor.md)` resolves relative to `docs/design/`, pointing to a nonexistent path.
**Fix:** Change to `[tier-up-advisor](../../.kanon/protocols/kanon-sdd/tier-up-advisor.md)`.

### 2. Promote preflight spec/design from draft to accepted

**Files:** `docs/specs/preflight.md:2`, `docs/design/preflight.md:2`
**Problem:** Both still say `status: draft` but preflight shipped in v0.3.0a6.
**Fix:** Change to `status: accepted`.

### 3. ~~Move banner entry from [Unreleased] to [0.3.0a6]~~ — DROPPED

**Reason:** Code review found the banner was committed *after* the v0.3.0a6 tag, so it correctly belongs in `[Unreleased]`. No change needed.

### 4. Align CLI tagline with README

**File:** `src/kanon/cli.py:386`
**Problem:** CLI says "SDD kit" but README says "development-discipline kit". The broader framing is correct (7 aspects, not just SDD).
**Fix:** Change docstring to `"""kanon — portable, self-hosting development-discipline kit for LLM-agent-driven repos."""`

### 5. Add docstrings to 6 validator `check()` functions

**Files:**
- `src/kanon/_validators/adr_immutability.py:27`
- `src/kanon/_validators/link_check.py:15`
- `src/kanon/_validators/index_consistency.py:16`
- `src/kanon/_validators/test_import_check.py:18`
- `src/kanon/_validators/plan_completion.py:12`
- `src/kanon/_validators/spec_design_parity.py:14`

**Fix:** Add a one-line docstring to each: `"""Validate <what> and append findings to errors/warnings."""`

### 6. Fix ruff I001 in `_banner.py`

**File:** `src/kanon/_banner.py:11`
**Problem:** Unsorted import block.
**Fix:** Run `ruff check --fix src/kanon/_banner.py`.

### 7. Replace `time.sleep(1.1)` with deterministic check

**File:** `tests/test_cli.py:609`
**Problem:** 1.1s wall-clock sleep to detect churn-writes. Adds latency, theoretically flaky.
**Fix:** Compare file content bytes before/after upgrade instead of relying on timestamp difference. Read `config_path.read_bytes()` before and after, assert equality.

## Acceptance criteria

- [ ] `kanon verify .` passes (no broken links)
- [ ] `ruff check src/kanon/` clean
- [ ] `mypy src/kanon/` clean
- [ ] All 765+ tests pass
- [ ] No `time.sleep` in the modified test

## Scope exclusions

- CI script `main()` docstrings (4 files in `kit/aspects/`) — these are scaffolded templates, not core source
- The `docs/design/scaffold-v2.md` and `docs/specs/scaffold-v2.md` draft status — scaffold-v2 hasn't shipped yet
