---
status: done
date: 2026-04-30
spec: ../specs/cli.md
adr: ../decisions/0037-profile-rename-and-max.md
---
# Plan: `--profile full` rename + new `max` profile

## Goal

Implement INV-cli-init-profile per ADR-0037: rename `full → all`, add `max`, reject `full` outright.

## Tasks

- [x] T1: Spec amendment in `docs/specs/cli.md` (INV-cli-init-profile + flag enumeration update + invariant_coverage entries + date bump).
- [x] T2: ADR-0037 authored at `docs/decisions/0037-profile-rename-and-max.md`.
- [x] T3: ADR-0037 indexed in `docs/decisions/README.md`.
- [x] T4: Plan indexed in `docs/plans/README.md`.
- [x] T5: `src/kanon/cli.py` — `_PROFILES` dict updated: `full` removed, `all` added (every kit aspect at `default-depth`), `max` added (every kit aspect at `depth-range[1]`).
- [x] T6: `src/kanon/cli.py` — `--profile` click choice updated to `["solo", "team", "all", "max"]`; help string rewritten to enumerate the four values with their semantics.
- [x] T7: 5 new tests in `tests/test_cli.py` covering INV-cli-init-profile (`solo`, `team`, `all`, `max`, `full → rejected`).
- [x] T8: `CHANGELOG.md` entry under `## [Unreleased]` (Changed: rename + new `max`; Removed: `full`).
- [x] T9: `kanon verify .` clean; `ruff check` clean; full pytest suite passing.

## Acceptance criteria

- [x] `--profile full` is rejected with click's choice error (no deprecation alias).
- [x] `--profile all` enables every kit-shipped aspect at its `default-depth`.
- [x] `--profile max` enables every kit-shipped aspect at the upper end of its `depth-range`.
- [x] `--profile solo` and `--profile team` semantics unchanged.
- [x] All 5 INV-cli-init-profile tests pass.
- [x] `kanon verify .` returns `status: ok`.

## Out of scope

- Renaming `solo`/`team` profiles. They are explicit aspect-depth lists by design (ADR-0037 § Decision); no change.
- Adding more profiles (e.g., `dev`, `release-only`). Out of scope until a real use case appears.
