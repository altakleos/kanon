---
status: done
date: 2026-04-30
slug: medium-config-fixes
---
# Plan: Medium Config/Packaging Fixes (Items 9 + 11)

## Goal

Fix unpinned runtime dependencies and the empty release depth-3 gate.

## Changes

### Item 9: Pin runtime dependencies with compatible-release upper bounds

**File:** `pyproject.toml`
**Current:** `click>=8.0`, `pyyaml>=6.0`
**Fix:** Keep `>=` lower bounds (standard for libraries per PEP 440). No change needed.

**Rationale:** Research confirms that `>=` is the correct convention for published
PyPI libraries. pytest, Django, and click all use `>=` floor-only ranges. Exact
pins or `~=` are for applications, not libraries. The original analysis flagged
this as a supply-chain risk, but the Python packaging ecosystem explicitly
discourages upper bounds for libraries (PEP 440, PyPA guidance). **Dropping this
item — no change.**

### Item 11: Lower release gate from depth 3 to depth 2

**File:** `src/kanon/cli.py:875-879`
**Current:** `if release_depth < 3` — but depth 3 adds zero files/protocols/sections
**Fix:** Change gate to `if release_depth < 2`. Depth 2 provides the preflight
script and release workflow — everything needed for `kanon release` to work.

Also update:
- The error message on the same line (change "3" to "2")
- The CLI help docstring for release_cmd (change "depth >= 3" to "depth >= 2")
- Any tests that assert on the depth-3 gate

## Acceptance criteria

- [x] `kanon release` works at depth 2
- [x] `kanon release` fails at depth 1 with clear error
- [x] All existing tests pass
- [x] No depth-3 references remain for the release gate
