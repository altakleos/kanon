---
status: done (superseded by docs/plans/cli-modularization — merged)
date: 2026-04-30
slug: medium-cli-modularization
---
# Plan: cli.py + test_cli.py Modularization (Items 13 + 14)

## Goal

Split `cli.py` (1586 lines, 37 functions) and `test_cli.py` (~3000 lines, 131 tests)
into logical modules.

## Status: DEFERRED

This is a large structural refactor with high risk of merge conflicts and no
functional change. Deferring until the higher-priority items (critical + high)
are addressed. The current structure works — it's a maintainability concern,
not a correctness issue.

## Proposed split (for future reference)

### cli.py → 5 modules

| Module | Functions | ~Lines |
|--------|-----------|--------|
| `cli.py` | main group, init, upgrade | ~320 |
| `_cli_verify.py` | verify, preflight, _emit_verify_report | ~190 |
| `_cli_aspect.py` | aspect group, list/info/add/remove/set-depth/set-config, helpers | ~420 |
| `_cli_release.py` | release_cmd, tier group, tier_set | ~100 |
| `_cli_fidelity.py` | fidelity group, fidelity_update, graph group, graph_orphans, graph_rename | ~220 |

### test_cli.py → matching test modules

Split tests to mirror the source module split.
