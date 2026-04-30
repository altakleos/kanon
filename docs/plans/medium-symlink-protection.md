---
status: done
date: 2026-04-30
slug: medium-symlink-protection
---
# Plan: Symlink Protection (Item 10)

## Goal

Add path-containment checks to prevent symlink-based writes outside the target directory.

## Context

`_write_tree_atomically()` already has a containment check (scaffold.py:590-595).
`_write_config()` does NOT. No `is_symlink()` checks exist anywhere.

## Changes

### Add `_ensure_within(path, base)` helper to `_scaffold.py`

A small helper that resolves a path and verifies it stays within the base directory:

```python
def _ensure_within(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise click.ClickException(
            f"Path escapes target directory: {path}"
        )
    return resolved
```

### Apply to `_write_config()`

Before writing `config_dir / "config.yaml"`, call `_ensure_within(config_dir, target)`.

### Apply to `_migrate_flat_protocols()`

Before `sdd_dir.mkdir()`, call `_ensure_within(sdd_dir, target)`.

### Consolidate existing check in `_write_tree_atomically()`

Replace the inline check at line 593 with a call to `_ensure_within(dst, target)`.

### Tests

Add tests in `tests/test_scaffold_symlink.py`:
- Symlink inside target pointing outside → raises ClickException
- Normal path within target → succeeds
- Nested symlink → raises ClickException

## Acceptance criteria

- [ ] `_ensure_within` helper exists and is used in all 3 write paths
- [ ] Inline containment check in `_write_tree_atomically` replaced with helper call
- [ ] New test file with symlink attack scenarios
- [ ] All existing tests pass
