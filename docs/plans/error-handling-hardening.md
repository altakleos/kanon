---
status: done
date: 2026-04-29
---
# Plan: Error Handling Hardening

## Problem

Three code paths produce raw Python tracebacks instead of user-friendly `ClickException` messages when encountering missing/unreadable files or malformed config.

## Changes

### E1. `_rename.py` — wrap unprotected `read_text()` calls

- `compute_principle_rewrites()` line ~223: `canonical_src.read_text()` — wrap in try/except `OSError` → `ClickException`
- `rewrites_extend_with_frontmatter()` line ~288: `md.read_text()` — wrap in try/except `OSError` → `ClickException`

### E2. `cli.py` — guard `_rewrite_assembled_views()` against missing AGENTS.md

- Line ~1231: `(target / "AGENTS.md").read_text()` — check `is_file()` first, return early if missing (the file will be created by the next `_write_tree_atomically` call anyway).

### E3. `_scaffold.py` — validate config structure in `_migrate_legacy_config()` and `_config_aspects()`

- `_migrate_legacy_config()` line ~83: when `aspects` is not a dict, raise `ClickException` instead of silently returning the broken config.
- `_config_aspects()` line ~120: validate each entry is a dict with a `depth` key before accessing.

### Tests

- `test_rename.py`: test that `compute_principle_rewrites` raises `ClickException` on missing principle file
- `test_cli.py`: test that `_rewrite_assembled_views` handles missing AGENTS.md gracefully
- `test_cli.py`: test that `_config_aspects` raises on malformed entry

## Acceptance criteria

- [x] All three error paths produce `ClickException` with file path context
- [x] No raw tracebacks for missing files or malformed config
- [x] Tests cover each error path
- [x] Existing tests pass
