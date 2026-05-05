---
feature: adr-0042-wording-gate
status: done
date: 2026-05-05
---
# Plan: ADR-0042 wording parity CI gate

## Context

ADR-0042 §1 ratifies the canonical exit-zero wording for `kanon verify` as a stable protocol commitment, immutable post-acceptance under ADR-0032's discipline. The same prose is also embedded as the `_ADR_0042_VERIFY_SCOPE` Python constant at `packages/kanon-core/src/kanon_core/cli.py:86-104`, surfaced verbatim via `kanon verify --help` and cited in failure error messages (`cli.py:665-672`).

ADR-0032's `check_adr_immutability.py` gate freezes the ADR body but does **not** check the CLI constant. If a contributor edits the constant in `cli.py` without touching the ADR, no validator catches it; the substrate's most-public claim drifts silently between two surfaces. The briefing on this codebase flagged this as a real gap (§9, "Open Questions").

This plan adds a small CI gate that fires when the four load-bearing MUST-NOT clauses in the canonical wording diverge between the ADR and the CLI constant.

## Tasks

- [x] T1: New validator `scripts/check_adr_0042_wording.py` — extracts ADR-0042 §"1. The canonical exit-zero wording" body (between the `### 1.` heading and the next `### ` heading) and the `_ADR_0042_VERIFY_SCOPE` constant body via `ast` parsing of `packages/kanon-core/src/kanon_core/cli.py`. Normalises both (strip markdown bullets/whitespace, collapse spaces). Asserts the four MUST-NOT clauses (each identified by a stable phrase: `good engineering practices`, `correctness or quality endorsement`, `static structural check`, `semantically correct realizations`) appear in both. Pattern-instantiates the existing `check_*.py` shape (single `def main() -> int`, exit 0 on pass, exit 1 with structured error on fail). → `scripts/check_adr_0042_wording.py`
- [x] T2: New test `tests/scripts/test_check_adr_0042_wording.py` — three cases: (a) parity holds → exit 0; (b) clause removed from CLI constant → exit 1 with the missing-clause cited; (c) clause removed from ADR §1 → exit 1. Uses `tmp_path` fixtures with rewritten fragments per the existing `test_check_adr_immutability.py` style. → `tests/scripts/test_check_adr_0042_wording.py`
- [x] T3: Wire into CI workflow — add a step running `python scripts/check_adr_0042_wording.py` to `.github/workflows/checks.yml`, alongside the other `check_*.py` invocations near line 90. → `.github/workflows/checks.yml`
- [x] T4: CHANGELOG entry under `## [Unreleased]` — "Added: CI gate enforcing parity of the ADR-0042 canonical exit-zero wording between the ADR body and the `_ADR_0042_VERIFY_SCOPE` CLI constant." → `CHANGELOG.md`

## Acceptance Criteria

- [x] AC1: `python scripts/check_adr_0042_wording.py` exits 0 against current main (parity holds today).
- [x] AC2: Mutation test — temporarily stripping any one of the four MUST-NOT clauses from `cli.py:_ADR_0042_VERIFY_SCOPE` causes the script to exit 1 with the missing clause named. (Verified manually before commit; revert mutation.)
- [x] AC3: Same mutation against the ADR body causes the script to exit 1.
- [x] AC4: New script's tests pass (`pytest tests/scripts/test_check_adr_0042_wording.py`).
- [x] AC5: `kanon verify .` still passes.
- [x] AC6: CI workflow runs the new gate (visible in PR check status).

## Documentation Impact

None. The validator is kit-internal CI and is not surfaced to consumer projects (mirrors `check_adr_immutability.py`'s scope per ADR-0032). CHANGELOG note is the only user-visible artifact.

## Notes

- **Why phrase-substring rather than byte-equality.** The ADR body is markdown (with `- ` bullets); the CLI constant is a Python string with `\n` and indented continuation. Byte-equality would require either a brittle one-way transform or refactoring the CLI to load the wording from the ADR at runtime — too large for this gate. Phrase-substring on the four load-bearing MUST-NOT clauses captures the actual invariant: any change that drops a clause from either surface fires the gate. If the CLI prose later diverges in formatting (e.g., reorders the bullets or rewords a connective) without dropping a clause, the gate stays green — that is the intended scope.
- **Why phrase set lives in the validator, not in YAML.** The phrases are the validator's internal definition of "the four claims this gate checks." Storing them externally would just add an indirection layer for a list of four constants.
- **No design doc needed.** Pattern instantiation of the existing `scripts/check_*.py` shape per `docs/design/README.md` skip conditions §1 (existing pattern, no new mechanism). No new component boundary.
- **No spec needed.** Internal CI gate; no user-visible capability change.
- **No ADR needed.** No new model, no genuine alternatives debated, no decision constraining future work — this is one validator instantiating an existing pattern in service of an already-ratified ADR (ADR-0042 + ADR-0032).
