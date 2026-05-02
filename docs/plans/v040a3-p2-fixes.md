---
status: approved
slug: v040a3-p2-fixes
date: 2026-05-02
---

# Plan: v0.4.0a3 — address 2 P2s from the v0.3.1a2..HEAD re-review

## Goal

Address the two P2 (non-blocking) findings the second critic review (agent `aca79d08a9e3bc30b`, 2026-05-02) surfaced after the v0.4.0a2 release-prep batch. Ship as `v0.4.0a3`. P3s in that report are positive confirmations (correctly-designed code paths); no fix work.

## Background

Second-pass critic review found 0 P0/P1 (release-ready for v0.4.0a2) and 2 P2s:
1. **`kanon migrate` schema-version YAML quirk**: the `isinstance(schema_version, int)` guard at `cli.py:1445` bypasses string (`"5"`) and float (`5.0`) `schema-version` values. Today's blast radius is zero (no v5 kanon exists; verb is deprecated-on-arrival), but the failure mode — silent v4-shape augmentation beneath a future-version header — is exactly the "hybrid that no reader understands" the existing PR 3 guard exists to prevent.
2. **`kanon contracts validate` JSON schema non-uniformity**: the missing-manifest branch returns `{"errors":[{"code":"missing-manifest", ...}], "status":"fail"}` without `dialect` or `contracts` keys, breaking schema parity with the success path. Tooling consuming the verb's JSON has to special-case the failure shape.

## Scope

In scope: P2 #1 + P2 #2.

Out of scope: P3s (all confirmations of correctly-designed paths). Future-cycle work: items 8 (CHANGELOG line-ref convention) and 9 (bare-name removal-horizon ADR) from the original critic-review minor list remain deferred.

## Acceptance criteria

- AC1: `kanon migrate --target <dir-with-schema-version-string-5>` exits non-zero with the same diagnostic as the integer-5 case. Same for `schema-version: 5.0` (float).
- AC2: `tests/test_cli_migrate.py` gains 2 new tests covering the string and float bypass paths.
- AC3: `kanon contracts validate <bundle-without-manifest>` JSON output includes `"dialect": null` and `"contracts": []` keys for schema parity with the success path.
- AC4: `tests/test_cli_resolutions_contracts.py::test_contracts_validate_missing_manifest_*` (or extend the existing missing-manifest test) asserts the JSON envelope carries `dialect` + `contracts` even on failure.
- AC5: Full pytest passes (976 + ≥3 new).
- AC6: 8 gates green; ruff clean.
- AC7: Version bumped to `0.4.0a3`; CHANGELOG `## [Unreleased]` renamed to `## [0.4.0a3] — <date>`.

## Steps

1. Fix `src/kanon/cli.py` migrate forward-version guard: replace `if isinstance(schema_version, int) and schema_version > 4:` with a coerce-then-compare pattern that handles int, str-numeric, and float values uniformly. Refuse anything that's not an integer ≤ 4.
2. Fix `src/kanon/cli.py:contracts_validate` missing-manifest branch: include `"dialect": None, "contracts": []` in the JSON output so the schema is uniform.
3. Add 2 regression tests for migrate (string `"5"` and float `5.0`).
4. Extend the existing missing-manifest test to assert `dialect` and `contracts` keys are present.
5. Bump `__version__` and `.kanon/config.yaml` `kit_version` to `0.4.0a3`.
6. Rename CHANGELOG `## [Unreleased]` → `## [0.4.0a3] — 2026-05-02`; insert empty `## [Unreleased]`.
7. Run gates + full pytest. Recapture fidelity.
8. Commit + push + PR + merge.
9. Cleanup worktree.

## Verification

- `kanon migrate --target /tmp/v5-string` (config: `schema-version: "5"`) → exit 1 with "Unknown schema-version: 5" diagnostic.
- `kanon migrate --target /tmp/v5-float` (config: `schema-version: 5.0`) → exit 1 with same diagnostic.
- `kanon contracts validate /tmp/empty-bundle` → JSON contains `"dialect": null` and `"contracts": []`.
- `pytest --no-cov -q` → 976+ passed.
- `kanon verify .` → ok; 7 standalone gates → ok.
