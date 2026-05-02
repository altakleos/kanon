---
status: done
serves: docs/specs/cross-harness-shims.md
design: "Follows ADR-0003"
touches:
  - src/kanon/cli.py
  - src/kanon/_scaffold.py
  - docs/specs/cli.md
  - tests/test_cli.py
---

# Plan: Harness filtering for `kanon init`

## Tasks

- [x] T1: Add `--harness` option to `init` in cli.py (repeatable,
  default "auto"). Pass the value to `_render_shims()`.
- [x] T2: Update `_render_shims()` in _scaffold.py to accept an
  optional filter. When "auto", inspect target dir for existing
  harness config dirs; when none found, return only CLAUDE.md.
  When explicit names given, filter to those. When called from
  `upgrade()`, pass no filter (all shims, backward compat).
- [x] T3: Update cli.md INV-cli-init to add `--harness` to the
  flag signature.
- [x] T4: Update/add tests:
  - test_init_auto_detect_writes_only_matching_shims
  - test_init_harness_explicit_filters
  - test_init_no_dotdirs_defaults_to_claude_md
  - test_upgrade_still_writes_all_shims (existing test covers this)

## Acceptance criteria

1. `kanon init ~/proj` in a clean dir writes only AGENTS.md + CLAUDE.md
   (no other shims).
2. `kanon init ~/proj` in a dir with `.cursor/` writes AGENTS.md +
   CLAUDE.md + `.cursor/rules/kanon.mdc`.
3. `kanon init ~/proj --harness cursor --harness kiro` writes only
   those two shims + AGENTS.md.
4. `kanon upgrade` still writes all shims.
5. All existing tests pass.
6. `kanon verify .` passes.
