---
slug: migrate-expanded
status: approved
owner: makutaku
created: 2026-05-04
related-adr: 0045 0048 0053
---

# Plan — Collapse `kanon migrate` into `kanon upgrade` (Option A)

## Context

User-driven simplification (2026-05-04 session). The current CLI splits migration responsibility across two verbs:

- `kanon upgrade <target>` — refreshes kit content (AGENTS.md, harness shims) AND chains v1/v2 → v3 schema migration
- `kanon migrate --target <path>` — one-shot v3 → v4 schema rewrite, deprecated-on-arrival

A user has no obvious way to know which one to run. Asymmetry is a smell: `upgrade` handles v1/v2 → v3 but not v3 → v4; `migrate` handles v3 → v4 but not kit refresh; both touch `.kanon/config.yaml`. User confirmed: collapse to **`kanon upgrade` as the single user-facing verb that handles the entire transition** (Option A).

Three real consumers gate this work (per ADR-0053 Historical Note + 2026-05-04 audit):
- **kanon** (self-host): hybrid v3+v4
- **website**: v3-only (`kit_version: 0.3.1a2`)
- **sensei**: v2-era (`kit_version: 0.2.0a11`)

After this PR ships + a v0.5.0a3 tag, all three can run `pip install -U kanon-kit && kanon upgrade .` and land cleanly on v4.

## Acceptance criteria

- AC1: `kanon upgrade <target>` is the **single** user-facing migration entry point. Detects schema version (v1/v2/v3/hybrid/v4) and applies all needed transformations atomically.
- AC2: Schema chain: v1 (`tier:`) → v2 (bare-key `aspects:`) → v3 (`kanon-<slug>:` namespaced) → v4 (`schema-version: 4` + `kanon-dialect` + `provenance`).
- AC3: Strips deprecated config keys — kanon-testing's retired `test_cmd`, `lint_cmd`, `typecheck_cmd`, `format_cmd`, `coverage_floor` (Phase A.4).
- AC4: When v4 is present (or being added), strips deprecated v3 fields: `kit_version` (redundant with `schema-version` + per-package `__version__`); empty `aspects.<slug>.config: {}` blocks left after retired-key stripping.
- AC5: Cleans stale `.kanon/protocols/<aspect>/` dirs for aspects NOT in the current `aspects:` set (safe-direction only — no surprise deletes for enabled aspects).
- AC6: `kanon migrate` is **removed from the CLI** entirely. It was deprecated-on-arrival (shipped in v0.5.0a2 ~24 hours ago); no external script depends on it. Tests get rebased onto `upgrade`.
- AC7: `kanon upgrade <target>` accepts **positional `target`** (consistent with `init`/`verify`/`preflight`). No flag-based form.
- AC8: All existing `upgrade` behaviors preserved: kit-content refresh, marker-block re-assertion, AGENTS.md merge, harness shim render, `_migrate_flat_protocols` for tier-1 → tier-N.
- AC9: Idempotent — re-running on a v4 config with no kit drift is a clean no-op.
- AC10: Atomic — uses `_atomic_write_text` per ADR-0024. Partial-write recovery via `.pending` sentinel.
- AC11: Tests cover (a) v1→v4 single-shot via upgrade, (b) v2→v4, (c) v3→v4, (d) hybrid v3+v4 → v4-clean, (e) already-v4 no-op, (f) retired-keys strip, (g) stale protocols-dir cleanup, (h) idempotency (run twice, second is no-op for state changes), (i) `kanon migrate` is no longer registered (verb absent from `--help`).
- AC12: All 7 standalone gates green; pytest passes.
- AC13: `make wheel-check` returns `status: ok` against the new wheel.
- AC14: Version bump to 0.5.0a3 across `kanon_core/__init__.py`, `kanon_aspects/__init__.py`, `kit-meta/pyproject.toml`, `.kanon/config.yaml` `kit_version` (irony noted: kit_version is one of the v3 fields the new upgrade strips; we keep it during this PR's lifetime since the kanon repo's own `.kanon/config.yaml` is the test target for the next PR).
- AC15: CHANGELOG `[Unreleased]` entry under `### Changed` (CLI surface change).
- AC16: Cut tag v0.5.0a3 after merge (release-checklist protocol). Then user can `pip install -U kanon-kit && kanon upgrade .` in each consumer.

## Scope

### In
- Hoist v3 → v4 logic from `migrate()` (cli.py:1381+) into a private helper `_migrate_to_current_schema()` callable from `upgrade()`.
- Extend the helper to chain v1/v2/v3 → v4 (call existing `_migrate_legacy_config()` first, then v3→v4).
- Add retired-key stripping + v3-field stripping + stale-protocols cleanup to the helper.
- Update `upgrade()` (cli.py:348) to call the new umbrella helper.
- Remove `@main.command("migrate")` registration. Keep the function as `_migrate_to_current_schema()` (private) for testability.
- Rebase `tests/test_cli_migrate.py` to drive `upgrade` (or split into unit-tests of the helper + integration-tests of upgrade).
- Add new tests for v1/v2/hybrid chain + retired-key strip + protocols cleanup + `kanon migrate` absence.
- Bump version to 0.5.0a3 (3 files).
- CHANGELOG entry.
- Cut tag after merge.

### Out
- `.kanon/recipes/` cleanup (deferred — needs recipe-registry design).
- `kanon upgrade` adopting `--quiet` semantics consistent with `init` (already done; just verify untouched).
- Aspect-bundle source-tree directory rename (deferred per ADR-0052/0054).
- The deprecated `--target` flag form on migrate (gone with the verb).
- An `--schema-only` mode on upgrade (initially: no — keep one mode; revisit if a user needs to refresh kit content separately from schema).

## Steps

1. Author `_migrate_to_current_schema(target, config) -> (new_config, file_changes)` in `_scaffold.py` or a new `_migration.py`. Pure function over the loaded config + a directory walk for stale-protocols detection.
2. Update `_migrate_legacy_config()` to be a building block of the umbrella (or absorb its logic).
3. Wire `upgrade()` (cli.py:348) to call the umbrella after the existing `_migrate_legacy_config()` step (or replace that call).
4. Delete `@main.command("migrate")` block from cli.py. Keep the schema-detection + change-application logic as private functions.
5. Rebase `tests/test_cli_migrate.py` → `tests/test_upgrade_migration.py` (or merge into existing `tests/test_cli.py`'s upgrade tests). Drive upgrade with synthetic v1/v2/v3/hybrid configs in tmp_path; assert post-state matches v4 + cleaned.
6. Add new test for "kanon migrate is no longer a registered command".
7. Bump versions to 0.5.0a3.
8. CHANGELOG `[Unreleased]` entry.
9. `kanon verify .`; fidelity recapture.
10. `make wheel-check`.
11. Commit, push, PR. Wait for ALL CI jobs. Manual merge (no `--auto`).
12. Run release-checklist; cut tag v0.5.0a3.

## Risks

- **Existing `_migrate_legacy_config()` couples to scaffold side effects.** Extracting cleanly may need refactor. Acceptable to keep tight coupling and just call it sequentially.
- **`kanon migrate` removal is a CLI break.** Mitigated by: ADR-0048's zero-consumer commitment; deprecated-on-arrival framing; <24h on PyPI; no scripts can have adopted it.
- **Stale-protocols cleanup**: only deletes `<aspect>/` dirs for aspects NOT in current `aspects:` set. Safe direction. If a user's config drops kanon-testing → upgrade also drops `.kanon/protocols/kanon-testing/`. Could surprise — but: the directory only exists because the aspect was previously enabled, and dropping the aspect implies dropping its protocol mirror is the right call.
- **Sensei's v0.2 schema unknown unknowns**: I haven't read sensei's actual config. The current `_migrate_legacy_config()` claims to handle v1+v2; if sensei is something else, upgrade will error rather than corrupt the file. User can iterate.
- **Auto-merge race**: do NOT use `--auto`; manual merge after all CI jobs green per PRs #112-#119 lessons.
