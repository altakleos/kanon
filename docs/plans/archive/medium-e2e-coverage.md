---
status: done
date: 2026-04-30
slug: medium-e2e-coverage
---
# Plan: E2E Test Coverage (Item 12)

## Goal

Add e2e lifecycle tests for CLI commands that currently lack them.

## Context

Current e2e coverage (10 tests across 2 files):
- `test_e2e_installed.py`: version, init+verify, full lifecycle, worktrees, upgrade idempotent
- `test_e2e_lifecycle.py`: full project, aspect lifecycle, init-upgrade cycle, multi-aspect, user content

Missing e2e coverage for: `preflight`, `release`, `aspect set-config`, `aspect info`, `fidelity`, `graph`.

## Changes

### Add tests to `tests/test_e2e_lifecycle.py`

New test functions using CliRunner (matching existing pattern):

1. **`test_preflight_lifecycle`** — init with tier 1, run preflight, verify it reports hook status
2. **`test_release_lifecycle`** — init, set release depth 2, run release with --dry-run, verify gate behavior
3. **`test_aspect_set_config_lifecycle`** — init, set-config on an aspect, verify config persists through upgrade
4. **`test_aspect_info_lifecycle`** — init, run aspect info for each enabled aspect, verify output contains description
5. **`test_fidelity_lifecycle`** — init, enable fidelity aspect, run fidelity update, verify output
6. **`test_graph_orphans_lifecycle`** — init at depth 3, create orphan doc, run graph orphans, verify detection

## Acceptance criteria

- [x] 6 new e2e tests added
- [x] All new tests pass
- [x] All existing tests still pass
- [x] Each test exercises the full init → command → verify cycle
