---
status: in-progress
date: 2026-05-01
spec: ../specs/cli.md
adr: ../decisions/0038-init-merge-into-existing-agents-md.md
---
# Plan: `kanon init` merges into existing `AGENTS.md`

## Goal

Implement INV-cli-init-agents-md-merge per ADR-0038: three-branch merge into existing AGENTS.md instead of silent skip.

## Tasks

- [x] T1: Spec amendment in `docs/specs/cli.md` (new INV-cli-init-agents-md-merge as #4 + invariant_coverage entries + renumber 4–14 → 5–15 + date bump).
- [x] T2: ADR-0038 authored at `docs/decisions/0038-init-merge-into-existing-agents-md.md`.
- [x] T3: ADR-0038 indexed in `docs/decisions/README.md`.
- [x] T4: Plan indexed in `docs/plans/README.md`.
- [x] T5: `src/kanon/cli.py` — `init()` AGENTS.md write replaced with three-branch logic. Branch detection: existence + `"<!-- kanon:begin:" in existing` marker probe.
- [x] T6: 3 new tests in `tests/test_cli.py` covering INV-cli-init-agents-md-merge: absent → full kit AGENTS.md; existing with markers → marker bodies refreshed, prose outside markers preserved; existing without markers → kit content prepended, existing prose preserved verbatim under `## Project context`.
- [x] T7: `CHANGELOG.md` entry under `## [Unreleased]` (Changed: init merges instead of skipping).
- [x] T8: `kanon verify .` clean; `ruff check` clean; full pytest passing.

## Acceptance criteria

- [x] `kanon init <target>` against an empty target writes the full kit-rendered AGENTS.md.
- [x] `kanon init <target>` against a target with kanon markers refreshes marker bodies, preserves outside content byte-for-byte.
- [x] `kanon init <target>` against a target with a non-kanon AGENTS.md writes the kit content above the existing prose, separated by a `## Project context` H2; existing prose is preserved verbatim.
- [x] No branch requires `--force`.
- [x] All 3 INV-cli-init-agents-md-merge tests pass.
- [x] `kanon verify .` returns `status: ok`.

## Out of scope

- Surfacing a stderr "merged" notice during init (would clutter the success line; the test suite verifies the contract). Worth a follow-up if a real consumer asks.
- Changing `kanon upgrade`'s merge behavior. INV-cli-upgrade already prescribes merge; `init` is converging on `upgrade`, not the reverse.
- Detecting "AGENTS.md is meaningfully equivalent to a fresh kit-rendered AGENTS.md" to skip the merge. Optimization; not a contract concern.
