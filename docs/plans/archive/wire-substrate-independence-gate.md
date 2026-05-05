---
feature: wire-substrate-independence-gate
status: done
date: 2026-05-05
---
# Plan: Wire substrate-independence gate into CI

## Context

ADR-0044 §1 ratifies substrate-independence as a permanent invariant: `kanon-core`'s runtime contract requires the kernel run without `kanon_aspects` importable. ADR-0044 §3 requires the gate be on the substrate's *permanent* CI surface, not a one-time milestone.

`scripts/check_substrate_independence.py` exists and is tested (`tests/scripts/test_check_substrate_independence.py`, 4 tests, all passing). It spawns a sub-process with `kanon_aspects` masked via `sys.meta_path` and exercises substrate-internal queries (`_load_aspects_from_entry_points`, `_aspect_path`, `_resolutions.replay`, `_dialects.validate_dialect_pin`, `_realization_shape.parse_realization_shape`, `_composition.compose`). Failure mode: any substrate code path that attempts `import kanon_aspects` surfaces as `ModuleNotFoundError` and the gate fails.

The gate is **not** wired into `.github/workflows/checks.yml` today. ADR-0044 §1 names this as a P0 substrate halt; it should block merge. This plan wires it.

## Tasks

- [x] T1: Add one step to `.github/workflows/checks.yml` after the existing `check_*` validator block (alongside `check_test_quality`, `check_invariant_ids`, etc.) that runs `python scripts/check_substrate_independence.py`. Required (no `continue-on-error`). → `.github/workflows/checks.yml`
- [x] T2: CHANGELOG entry under `## [Unreleased]`. → `CHANGELOG.md`

## Acceptance Criteria

- [x] AC1: Local `python scripts/check_substrate_independence.py` exits 0 against current main (pre-existing, re-verified).
- [x] AC2: The new workflow step appears in `.github/workflows/checks.yml` and runs without `continue-on-error`.
- [x] AC3: Existing tests (`tests/scripts/test_check_substrate_independence.py`) still pass.
- [x] AC4: `kanon verify .` still passes.
- [x] AC5: PR CI run shows `Check substrate-independence (per ADR-0044)` as a passing required check.

## Documentation Impact

CHANGELOG entry only. No README/docs update needed; ADR-0044 already documents the gate's contract. The README already cites ADR-0044 as part of the substrate's commitments.

## Notes

- **Why no spec/design/ADR.** No new code. No new mechanism. No genuine alternatives — ADR-0044 §1 explicitly mandates the gate on permanent CI surface; the only choice is *when* to wire it, and "now" is the answer this plan delivers.
- **Why not its own job.** The gate uses sub-process isolation (`sys.meta_path` masking) inside the existing test environment; it doesn't need a separate clean venv. Co-locating with the other `check_*.py` validators in the existing `check` matrix follows the established pattern and gives free coverage across (Python 3.10/3.11/3.12/3.13) × (ubuntu/macOS).
- **Why required (not `continue-on-error`).** ADR-0044 §1: failure of the gate is a P0 substrate halt. Soft-failing would let a substrate-vs-aspect coupling bug ship silently — the exact scenario ADR-0044 ratifies the gate to prevent.
