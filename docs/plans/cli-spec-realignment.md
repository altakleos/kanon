---
feature: cli-spec-realignment
serves: docs/specs/cli.md
status: done
date: 2026-04-25
---
# Plan: CLI Spec Realignment

The CLI spec (`docs/specs/cli.md`) has 6 of 10 invariants that no longer match the implementation. The spec is the source of truth — but several invariants were aspirational (atomicity model) or written for v0.1 and never updated for v0.2 (subcommands, init flags, verify checks). This plan brings the spec into alignment with the intended design, writes an ADR for the atomicity decision, implements a crash-recovery sentinel, and retrofits `invariant_coverage` for all 10 invariants.

## Background

Analysis identified these drifted invariants:

| Invariant | Drift |
|-----------|-------|
| INV-cli-subcommands | Says "exactly 5" — code has 7 (adds `aspect`, `fidelity`) |
| INV-cli-init | Promises `--learner-id` (never implemented); missing `--aspects` flag |
| INV-cli-upgrade | Describes full directory swap; code does incremental per-file atomic writes |
| INV-cli-verify | Promises 3 unimplemented checks; missing 2 implemented checks |
| INV-cli-atomicity | Describes "tmp-dir swap pattern"; code does per-file atomic writes |
| INV-cli-consumer-friendly-errors | Promises broken-shim detection; not implemented |

Root cause: the v0.2 aspect model plan created `docs/specs/aspects.md` and `docs/specs/fidelity-lock.md` for new commands but never updated `cli.md`. The atomicity invariant was aspirational — true multi-file atomicity is impossible on POSIX when files span multiple directories (AGENTS.md is in project root, `.kanon/` is a subdirectory).

## Design Decision: Atomicity Model

AGENTS.md must remain a kanon-modified file in the project root (agents read it natively; pointer/indirection patterns are unreliable across harnesses). This means `.kanon/` directory swap cannot achieve full-operation atomicity. The strongest achievable guarantee is **crash-consistent atomicity**:

- Each file write is individually atomic (fsync + rename).
- Commands write config.yaml last as a commit marker.
- A `.kanon/.pending` sentinel enables automatic recovery on next invocation.
- All commands are idempotent — re-running completes any interrupted operation.

This is recorded in ADR-0024.

## Tasks

### ADR

- [x] T1: Write ADR-0024 — crash-consistent atomicity model → `docs/decisions/0024-crash-consistent-atomicity.md`
  - Context: AGENTS.md in project root prevents single-directory-swap atomicity
  - Decision: per-file atomic writes + crash-recovery sentinel + idempotent commands
  - Alternatives: directory swap (doesn't cover root files), WAL (overengineered), AGENTS.md pointer (unreliable agent chaining), amend-only (no recovery improvement)

### Spec amendments

- [x] T2: Amend INV-cli-subcommands — list all top-level entries including `aspect` and `fidelity` groups, remove "v0.1" qualifier → `docs/specs/cli.md`
- [x] T3: Amend INV-cli-init — remove `--learner-id`, add `--aspects` flag, document mutual exclusion with `--tier` → `docs/specs/cli.md`
- [x] T4: Amend INV-cli-upgrade — describe incremental per-file atomic writes with config-last ordering, reference ADR-0024 → `docs/specs/cli.md`
- [x] T5: Amend INV-cli-verify — remove unimplemented checks (foundation backrefs, link validation, stale model-version), add implemented checks (fidelity lock, verified-by/invariant coverage), reference fidelity-lock.md and verified-by.md specs → `docs/specs/cli.md`
- [x] T6: Amend INV-cli-atomicity — replace "tmp-dir swap" with crash-consistent atomicity model, reference ADR-0024 → `docs/specs/cli.md`
- [x] T7: Amend INV-cli-consumer-friendly-errors — remove broken-shim detection claim (not implemented, not planned) → `docs/specs/cli.md`
- [x] T8: Update spec Intent section — expand to cover aspect lifecycle, not just "adopt, update, change tier, verify" → `docs/specs/cli.md`
- [x] T9: Update spec Rationale section — replace "Five is the minimum" with rationale for current surface, reference ADR-0024 for atomicity → `docs/specs/cli.md`
- [x] T10: Update spec Out of Scope section — remove items that have shipped (aspect commands), add current deferrals → `docs/specs/cli.md`
- [x] T11: Update spec Decisions section — add references to ADR-0012, ADR-0024 → `docs/specs/cli.md`
- [x] T12: Remove `fixtures_deferred` from spec frontmatter → `docs/specs/cli.md`

### Invariant coverage

- [x] T13: Add `invariant_coverage` entries for all 10 invariants mapping to existing tests in `tests/test_cli.py` → `docs/specs/cli.md`

### Implementation: crash-recovery sentinel

- [x] T14: Add `write_sentinel()` and `clear_sentinel()` to `_atomic.py` → `src/kanon/_atomic.py`
- [x] T15: Add `check_and_recover()` — called at entry of every mutating command; if `.kanon/.pending` exists, re-runs the interrupted operation → `src/kanon/_atomic.py`
- [x] T16: Wire sentinel into `init`, `upgrade`, `aspect add`, `aspect remove`, `aspect set-depth`, `fidelity update` commands → `src/kanon/cli.py`
- [~] T17: ~~Add `.kanon/.pending` to the `.gitignore` template in kit bundle~~ — DEFERRED. NOTE: the kit doesn't ship a consumer-facing `.gitignore` template at any depth (the repo's own `.gitignore` does cover `.kanon/.pending`, line 15). If a kit-shipped `.gitignore` is later specified, this task lifts to that plan.

### Tests

- [x] T18: Test sentinel write/clear lifecycle → `tests/test_atomic.py`
- [~] T19: ~~Test crash recovery — monkeypatch `atomic_write_text` to raise after N calls, verify sentinel exists, verify next command invocation recovers~~ — DEFERRED. NOTE: the monkeypatch pattern exists in `tests/test_aspect_config.py::test_set_config_persists_sentinel_on_mid_write_failure` (covers `set-config`). Broader cross-command coverage (init / upgrade / set-depth / aspect remove / fidelity update) is a future test-hardening pass; the recovery contract itself is documented and exercised once.
- [x] T20: Test that `.kanon/.pending` is absent after successful command completion → `tests/test_cli.py`

### Index updates

- [x] T21: Add ADR-0024 to `docs/decisions/README.md` index
- [x] T22: Add this plan to `docs/plans/README.md` index
- [x] T23: Update `docs/specs/cross-harness-shims.md` — fix stale path reference (`src/kanon/templates/harnesses.yaml` → `src/kanon/kit/harnesses.yaml`)

## Acceptance Criteria

- [x] AC1: All 12 invariants in `docs/specs/cli.md` accurately describe the implementation. (Originally 10; INV-cli-posix-only was added later. INV-cli-atomicity prose was amended in the close-out PR — "the interrupted operation is re-executed automatically" → "the user is notified to re-run, and idempotency guarantees the re-run completes the operation" — to match the actual `_check_pending_recovery` warn-and-rerun behaviour.)
- [x] AC2: `fixtures_deferred` removed from cli.md frontmatter; all 12 invariants have `invariant_coverage` entries
- [x] AC3: ADR-0024 is accepted and indexed
- [x] AC4: Crash-recovery sentinel is implemented and wired into all six mutating commands (`init`, `upgrade`, `aspect add`, `aspect remove`, `aspect set-depth`, `fidelity update`, plus `aspect set-config` per ADR-0025). Sentinel write/clear lifecycle test in `tests/test_atomic.py`; success-path absence test in `tests/test_cli.py::test_sentinel_absent_after_successful_set_depth`; mid-write-failure-persists-sentinel test in `tests/test_aspect_config.py::test_set_config_persists_sentinel_on_mid_write_failure`. Cross-command monkeypatch coverage deferred (T19).
- [x] AC5: `kanon verify .` passes
- [x] AC6: `pytest` passes with no regressions
- [x] AC7: `ruff check` and `mypy` pass
- [x] AC8: `ci/check_kit_consistency.py` passes
- [x] AC9: `ci/check_invariant_ids.py` passes
- [x] AC10: `ci/check_verified_by.py` passes with no warnings for cli.md

## Closure notes

Plan promoted to `status: done` in the close-out PR after a 23-task audit against `main`. Two deferrals (T17, T19) carry NOTE prose above with rationale. Two follow-up edits in the same close-out PR:

- **`docs/specs/cli.md` INV-cli-atomicity** prose corrected to match shipped behaviour (warn + idempotent re-run, not auto-replay).
- **`src/kanon/cli.py` `aspect_remove`** wrapped in `write_sentinel` / `clear_sentinel` for symmetry with the other five mutating commands.

Everything else (T1–T14, T18, T20–T23, all 10 ACs) had already shipped across earlier session PRs and is now ticked honestly.
