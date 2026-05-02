---
status: approved
slug: v040a1-followup
date: 2026-05-02
---

# Plan: v0.4.0a2 follow-up — paper-cuts deferred from v040a1-release-prep

## Goal

Sweep the 9 minor findings the v0.3.1a2..HEAD critic review surfaced that were intentionally deferred from `v040a1-release-prep` because they were paper-cuts (not release blockers). All addressable in one batch since each is a small isolated change. Ships as `v0.4.0a2`.

## Background

After `v040a1-release-prep` shipped (PRs #80-83), the critic review's minor list remained:
1. Stale module docstrings (`_dialects.py`, `_realization_shape.py`, `_composition.py`) still say "Wiring into ... lands in a later sub-plan" / "deferred" — but PRs #77, #78, and `kanon contracts validate` already wired all three.
2. 7 reference-manifest header comments still cite the legacy `src/kanon/kit/aspects/<aspect>/files/` path — the content moved to `src/kanon_reference/data/<aspect>/` in Phase A.7.
3. `docs/design/preflight.md:90-101,215` still references the retired `${test_cmd}` / `${lint_cmd}` / `${typecheck_cmd}` / `${format_cmd}` placeholders. The kanon-testing config-schema retiring them landed in Phase A.4.
4. 9 spec/design files reference the retired `src/kanon/kit/aspects/` path: `docs/specs/aspects.md:62`, `docs/specs/aspect-config.md:65,88`, `docs/specs/project-aspects.md:63,71,81,108`, `docs/design/aspect-model.md:12,37,57,191,228,230,232`, `docs/design/distribution-boundary.md:54,58`, `docs/design/kernel-reference-interface.md:55,201`, `docs/specs/spec-graph-rename.md:55,80`. Specs are normative; the wrong path puts publisher onboarding in conflict with the actual layout.
5. `tests/test_realization_shape.py` lacks a cardinality test on `len(V1_DIALECT_VERBS) == 9` — accidentally dropping a verb in a future commit produces no test failure.
6. `tests/test_resolutions.py` has a coverage gap on the `invalid-realization-shape` error path through `_validate_shape_against_contract` (the `parse_realization_shape` raise inside the function); the equivalent shape-side branch at `cli.py:1234` is also unreachable in the test suite.
7. Bare-name CLI hint in `_emit_init_hints` (`cli.py:135-140`) still suggests `kanon aspect add . testing` with bare names — these will trigger the Phase A.5 deprecation warnings the messages recommend. Update to `kanon-<local>` form.
8. CHANGELOG line-ref drift (`CHANGELOG.md:51` cites `cli.py:309-322` for deleted `_detect.py` block — those line numbers no longer exist post-deletion). CHANGELOG entries are append-only history per project convention, so this is annotative drift; document the convention to clarify or strip the line refs.
9. Open the `bare-name-removal-horizon` ADR (or add to the deprecation tracker) — the deprecation warning ships in v0.4 but no removal date is ratified anywhere.

## Scope

In scope: items 1-7. They're all small, isolated, no semantic risk. Land as one PR.

Out of scope (deferred):
- Item 8 (CHANGELOG line-ref): annotative; CHANGELOG is append-only history. If we adopt a convention of stripping line refs from past entries, that's a separate cleanup pass over the entire CHANGELOG.
- Item 9 (bare-name removal horizon): needs a small ADR draft (one paragraph), not a paper-cut sweep. Track separately.

## Acceptance criteria

- AC1: `_dialects.py:18-19`, `_realization_shape.py:11-13`, `_composition.py:12-13` module docstrings reflect the post-wiring reality (no "deferred" / "lands in later sub-plan" language).
- AC2: All 7 `src/kanon_reference/data/<aspect>/manifest.yaml` header comments cite the correct `src/kanon_reference/data/<aspect>/files/` path, not the legacy location.
- AC3: `docs/design/preflight.md` no longer references retired `${test_cmd}` / `${lint_cmd}` / `${typecheck_cmd}` / `${format_cmd}` placeholders. Sections updated to describe the post-A.4 reality (consumers wire their own preflight; aspect-contributed preflight no longer uses templated config keys).
- AC4: 9 spec/design files updated to reference `src/kanon_reference/data/<aspect>/` instead of `src/kanon/kit/aspects/<aspect>/`. Verified via `grep -r "src/kanon/kit/aspects" docs/specs/ docs/design/` returning 0 (modulo `## Changelog` style historical mentions, which retain their context).
- AC5: New test `tests/test_realization_shape.py::test_v1_dialect_verbs_count_is_nine` asserts `len(V1_DIALECT_VERBS) == 9` so accidental verb drops fail loudly.
- AC6: New test `tests/test_resolutions.py::test_validate_shape_against_contract_invalid_shape_surfaces` covers the `parse_realization_shape` raise path inside `_validate_shape_against_contract` (writes a contract with a malformed `realization-shape:` block, runs replay, asserts `code: invalid-realization-shape` ReplayError).
- AC7: `cli.py:_emit_init_hints` grow-hints use canonical `kanon-<local>` aspect names: `kanon aspect add . kanon-testing`, etc. Test `tests/test_cli.py::test_init_hints_use_canonical_names` (or extend an existing init-hints test) asserts the bare-name forms are absent.
- AC8: Full pytest passes (974+2 new tests, 5 deselected).
- AC9: 8 gates green.
- AC10: Version bumped to `0.4.0a2`; CHANGELOG `## [Unreleased]` renamed to `## [0.4.0a2] — <date>`; fresh empty `## [Unreleased]` above.

## Steps

Single PR; mechanical changes batched together since each item is small.

1. Apply Edit ops to AC1 (3 module docstrings).
2. Apply Edit ops to AC2 (7 manifest YAML header comments).
3. Apply Edit ops to AC3 (`docs/design/preflight.md`; rewrite sections referencing the retired placeholders to describe the post-A.4 model).
4. Apply Edit ops to AC4 (9 spec/design files; either update path OR remove the reference if it was a code-pointer that no longer makes sense).
5. AC5: append cardinality test to `tests/test_realization_shape.py`.
6. AC6: append `invalid-realization-shape` coverage test to `tests/test_resolutions.py` using the existing `_build_synthetic_target` + `_write_contract_with_shape` helpers.
7. AC7: update `cli.py:_emit_init_hints` strings; update or add test assertion.
8. AC10: bump `src/kanon/__init__.py` `__version__` to `0.4.0a2`; bump `.kanon/config.yaml` `kit_version`; rename CHANGELOG `## [Unreleased]` heading.
9. Run gates + full pytest.
10. Recapture fidelity lock.
11. Commit + push + open PR + merge with `gh pr merge --squash`.
12. Clean up worktree.

## Verification

- `kanon verify .` → ok
- 7 standalone gates → ok
- `pytest --no-cov -q` → 976 passed
- `grep -r "src/kanon/kit/aspects" docs/specs/ docs/design/ src/kanon_reference/data/` → empty (or only `## History` style mentions)
- `grep -r '${test_cmd}\|${lint_cmd}\|${typecheck_cmd}\|${format_cmd}' docs/design/ docs/specs/` → empty
- `kanon init /tmp/scratch --profile solo` then check stderr for hints — must not contain bare names like `aspect add . testing` (must use `kanon-testing`).
- `kanon contracts validate` smoke against a synthetic bundle still produces the expected JSON shape (sanity).

## Out of scope, deferred

Item 8 (CHANGELOG line-ref convention) and item 9 (bare-name removal horizon ADR) carry over to the next plan cycle.
