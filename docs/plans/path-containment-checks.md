---
status: done
date: 2026-04-29
---
# Plan: Path Containment Checks

## Problem

Two code paths accept relative file paths from user-controlled sources (project-aspect manifests, rename ops-manifests) and join them with a root directory without validating the resolved path stays within that root. This allows path traversal via `../../` sequences.

## Changes

### 1. `_scaffold.py` — `_write_tree_atomically()`

Add a containment check before writing each file:

```python
resolved = (target / rel).resolve()
if not resolved.is_relative_to(target.resolve()):
    raise click.ClickException(
        f"Scaffold path escapes target directory: {rel!r}"
    )
```

### 2. `_rename.py` — `read_ops_manifest()`

Add containment checks when constructing `FileRewrite` entries from JSON:

```python
root = repo_root.resolve()
for entry in data.get("files", []):
    src = (repo_root / entry["src"]).resolve()
    dst = (repo_root / entry["dst"]).resolve()
    if not src.is_relative_to(root) or not dst.is_relative_to(root):
        raise click.ClickException(
            f"Path traversal in ops-manifest: src={entry['src']!r}, "
            f"dst={entry['dst']!r} escapes repo root."
        )
```

### 3. Tests

Add tests for both paths:
- `test_scaffold.py::test_path_traversal_blocked` — project-aspect with `../../escape` in files list
- `test_rename.py::test_ops_manifest_path_traversal` — ops-manifest JSON with traversal paths

## Out of scope

- Symlink checks (LOW severity, `os.replace()` mitigates primary vector)
- Validator trust model (accepted risk by design)
- Preflight shell injection (accepted risk by design)

## Acceptance criteria

- [ ] `_write_tree_atomically()` raises `ClickException` for paths resolving outside target
- [ ] `read_ops_manifest()` raises `ClickException` for paths resolving outside repo root
- [ ] Tests cover both happy path and traversal rejection
- [ ] Existing tests pass
