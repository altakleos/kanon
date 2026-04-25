---
feature: aspect-depth-refactor
serves: docs/specs/cli.md
design: "Pattern instantiation: ADR-0024 (crash-consistent atomicity) + ADR-0008 (tier migration is mutable, idempotent, non-destructive). No new mechanism."
status: done
date: 2026-04-25
---
# Plan: Refactor `_set_aspect_depth` into named helpers under one sentinel

## Context

Audit risk R6. `_set_aspect_depth` (`src/kanon/cli.py:516-611`) is 97 lines and currently does:

1. validation + config read,
2. early-return for `current == n` (with its own sentinel + `_write_config`),
3. compute new state,
4. open-coded tier-up branch (additive file writes),
5. open-coded tier-down branch (print "beyond" diagnostics),
6. AGENTS.md re-merge,
7. kit.md re-render,
8. config.yaml commit,
9. sentinel clear.

Two problems:

- **Two `_write_config` callsites** (one in the noop branch at line 553, one in the main path at line 607) — divergence-prone; the noop branch was previously found to wrongly rewrite `enabled_at` on a true noop, fixed in the `## [Unreleased]` CHANGELOG entry but the duplication remains.
- **Tier-up vs tier-down logic interleaved** with shared post-amble code (AGENTS.md / kit.md / config). Reading the function requires holding both branches in mind even though they describe two distinct lifecycle operations.

The sentinel already wraps the right scope (per ADR-0024: write before first mutation, clear after `_write_config`). Crash anywhere in the sequence leaves `.kanon/.pending` in place; the next CLI invocation warns the user, and re-running the same `aspect set-depth N` is idempotent (additive writes skip extant files, AGENTS.md merge is a fixed point on well-formed input — see R1).

The refactor is **structural only**: same observable behavior, same sentinel scope, same atomic-write order, same exit codes, same stdout. No CLI flag changes, no config-schema changes. This is the "implementation refactor that preserves observable behaviour" carve-out from AGENTS.md — no spec amendment.

## Design

Split into four private helpers in `cli.py`:

| Helper | Responsibility | Pure / I/O |
|---|---|---|
| `_apply_tier_up(target, target_bundle)` | Write additive new-bundle files; return added count. | I/O (file writes via `atomic_write_text`); no config touch |
| `_apply_tier_down(target, old_aspects, new_aspects)` | Compute "beyond required" diagnostic; return rel-path list. No file writes. | Pure compute |
| `_rewrite_assembled_views(target, new_aspects, project_name)` | Re-merge AGENTS.md and re-render kit.md. | I/O |
| `_commit_aspect_meta(target, kit_version, aspects_meta, aspect_name, depth)` | Stamp `aspects_meta[aspect_name]` (depth, enabled_at, config) and call `_write_config`. | I/O |

`_set_aspect_depth` becomes a linear orchestration:

```python
def _set_aspect_depth(target, aspect_name, n, legacy_tier_verb=False):
    target = target.resolve()
    config = _read_config(target)
    _check_pending_recovery(target)
    top = _load_top_manifest()
    _validate_aspect_and_depth(aspect_name, n, top)              # extract validation block

    aspects = _config_aspects(config)
    proposed = {**aspects, aspect_name: n}
    err = _check_requires(aspect_name, proposed, top)
    if err:
        raise click.ClickException(err)

    kit_version = config.get("kit_version", __version__)
    current = aspects.get(aspect_name, -1)
    aspects_meta = dict(config.get("aspects", {}))

    write_sentinel(target / ".kanon", "set-depth")
    try:
        if current == n:
            _commit_aspect_meta(target, kit_version, aspects_meta, aspect_name, n)
            verb = "Tier" if legacy_tier_verb else f"Aspect {aspect_name} depth"
            click.echo(f"{verb} already {n}. Noop (timestamp refreshed).")
            return

        new_aspects = {**aspects, aspect_name: n}
        target_bundle = _build_bundle(new_aspects, {"project_name": target.name, "tier": str(n)})

        if n > current:
            added = _apply_tier_up(target, target_bundle)
            verb = "Tier-up" if legacy_tier_verb else f"Aspect-up ({aspect_name})"
            click.echo(f"{verb} {current} → {n}: added {added} new file(s).")
        else:
            beyond = _apply_tier_down(target, aspects, new_aspects)
            verb = "Tier-down" if legacy_tier_verb else f"Aspect-down ({aspect_name})"
            click.echo(f"{verb} {current} → {n} is non-destructive.")
            if beyond:
                click.echo("The following artifacts are now beyond required for this depth:")
                for rel in beyond:
                    click.echo(f"  - {rel}")
                click.echo("You may keep, archive, or delete them as you choose.")

        _rewrite_assembled_views(target, new_aspects, target.name)
        _commit_aspect_meta(target, kit_version, aspects_meta, aspect_name, n)
        verb = "Tier" if legacy_tier_verb else f"Aspect {aspect_name} depth"
        click.echo(f"{verb} set to {n} in .kanon/config.yaml.")
    finally:
        # Sentinel cleared only on success path. If an exception escapes, the
        # sentinel stays so the next CLI invocation warns the user (existing
        # ADR-0024 contract).
        pass
    clear_sentinel(target / ".kanon")
```

The `try/finally` is intentionally empty: on exception the sentinel must persist (matches today's behavior — `clear_sentinel` is unreached on raise). The `try` block is there so the structural intent is visible without changing semantics.

## Tasks

- [x] T1: Added `_apply_tier_up(target, target_bundle) -> int` to `src/kanon/cli.py` — additive-write loop, returns count.

- [x] T2: Added `_apply_tier_down(target, old_aspects, new_aspects) -> list[str]` — pure compute, no I/O, no deletions.

- [x] T3: Added `_rewrite_assembled_views(target, new_aspects, project_name) -> None` — AGENTS.md merge + kit.md render. The "no atomic_write_text on identity" optimisation for AGENTS.md is preserved (compares `merged != existing_agents` before writing).

- [x] T4: Added `_commit_aspect_meta(target, kit_version, aspects_meta, aspect_name, depth) -> None` — single source of truth for stamping the aspect meta entry and writing config. Both prior `_write_config` callsites now go through this helper.

- [x] T5: Added `_validate_aspect_and_depth(aspect_name, n, top) -> None`.

- [x] T6: Rewrote `_set_aspect_depth` body. New body is 51 lines (was 97). Sentinel write happens once at the top; `clear_sentinel` runs only after `_commit_aspect_meta` on the success path. Stdout strings, write order, and atomic-write semantics are unchanged.

- [x] T7: All 10 set-depth/tier-related tests pass against the refactor (`test_aspect_set_depth`, `test_aspect_set_depth_down`, `test_aspect_set_depth_invalid`, `test_aspect_set_depth_unknown_aspect`, `test_aspect_set_depth_requires_check`, `test_tier_set_idempotent`, `test_tier_set_down_legacy_verb`, `test_tier_migration_round_trip_preserves_user_file[chain0/1]`, `test_sentinel_absent_after_successful_set_depth`).

- [x] T8: Added `tests/test_set_aspect_depth_helpers.py` — two cases verifying `_apply_tier_down` returns only existing files AND does not mutate the filesystem.

- [x] T9: No CHANGELOG entry (internal refactor).

## Acceptance Criteria

- [x] AC1: `pytest` — full suite passes (verified locally; 312 = 310 prior + 2 new in T8).
- [x] AC2: `kanon verify .` — `status: ok`.
- [x] AC3: `python ci/check_kit_consistency.py` — exit 0.
- [x] AC4: `ruff check` clean on changed files.
- [x] AC5: `_set_aspect_depth` body is 51 lines; no inlined file-write loops, no inlined config mutation, no inlined AGENTS.md / kit.md rendering.
- [x] AC6: Sentinel write at line 615 (once); `_apply_tier_up` / `_apply_tier_down` / `_rewrite_assembled_views` / `_commit_aspect_meta` all run *between* sentinel write and clear; `clear_sentinel` is only on success paths (noop-branch return and end of main path); a raise from any helper leaves the sentinel in place.

## Documentation Impact

- None. Internal refactor; no user-facing surface changes; no spec amendments; no CHANGELOG entry.
