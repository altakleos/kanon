# Plan: Fix upgrade config preservation

## Problem

`kanon upgrade` drops three categories of user data from `.kanon/config.yaml`:

1. **Per-aspect `config` dicts** (e.g., `test_cmd`, `lint_cmd`) — replaced with `{}`
2. **Per-aspect `enabled_at` timestamps** — reset to current time
3. **Root-level extra keys** (e.g., `preflight-stages`) — dropped entirely

Root cause: three functions in `src/kanon/_scaffold.py` form a lossy pipeline:
- `_config_aspects()` extracts only `{name: depth}`, discarding `enabled_at` and `config`
- `_aspects_with_meta()` rebuilds entries from scratch with fresh timestamps and empty config
- `_write_config()` writes only `{kit_version, aspects}`, dropping root-level keys

## Approach

### Phase 1: Failing tests (RED)

Add three tests to `tests/test_cli.py`:

1. `test_upgrade_preserves_aspect_config` — set custom `config` keys on an aspect, upgrade, assert they survive
2. `test_upgrade_preserves_enabled_at_on_version_bump` — set old version, upgrade, assert `enabled_at` is unchanged
3. `test_upgrade_preserves_extra_root_keys` — add `preflight-stages` to config, upgrade, assert it survives

### Phase 2: Fix (GREEN)

1. **`_config_aspects()`** → return full aspect entries (not just depths), or stop using it in upgrade path
2. **`_aspects_with_meta()`** → accept optional existing metadata, preserve `enabled_at` and `config` when present
3. **`_write_config()`** → accept optional extra root-level keys and include them in the payload

Alternatively, introduce a new `_merge_config_for_upgrade()` that reads the old config and merges only `kit_version` while preserving everything else.

### Phase 3: Verify

- All new tests pass
- Existing tests still pass
- `test_upgrade_noop_does_not_churn_enabled_at` still passes

## Files touched

- `tests/test_cli.py` — new tests
- `src/kanon/_scaffold.py` — fix `_config_aspects`, `_aspects_with_meta`, `_write_config`
- Possibly `src/kanon/cli.py` — adjust upgrade call site if signatures change

## Acceptance criteria

- [ ] `kanon upgrade` preserves per-aspect `config` dicts
- [ ] `kanon upgrade` preserves per-aspect `enabled_at` timestamps on version bump
- [ ] `kanon upgrade` preserves root-level extra keys like `preflight-stages`
- [ ] All existing tests pass
