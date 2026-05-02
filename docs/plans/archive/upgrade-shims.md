---
status: done
serves: docs/specs/cli.md
design: "Follows existing upgrade() pattern"
touches:
  - src/kanon/cli.py
  - tests/test_cli.py
---

# Plan: Add shim re-rendering to upgrade command

## Motivation

CLI spec INV-cli-upgrade says upgrade "re-renders AGENTS.md sections,
kit.md, and harness shims." The code re-renders AGENTS.md and kit.md
but does NOT call `_render_shims()`. Shims are only rendered during
`init`. This means `kanon upgrade` after a kit update that adds or
changes a harness shim leaves stale shims on disk.

## Tasks

- [x] T1: Add `_render_shims()` call to `upgrade()` in cli.py,
  between the kit.md write and the config write. Iterate the returned
  dict and write each shim via `atomic_write_text()`, creating parent
  dirs as needed.
- [x] T2: Add a test that verifies upgrade refreshes shims (e.g.,
  init a project, corrupt a shim, run upgrade, assert shim is
  restored).

## Acceptance criteria

1. `kanon upgrade` re-renders all harness shims from the installed
   kit's templates.
2. Parent directories for shims (e.g., `.cursor/rules/`) are created
   if missing.
3. Existing test suite passes.
4. New test verifies shim re-rendering on upgrade.
