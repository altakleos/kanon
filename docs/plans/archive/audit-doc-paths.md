---
status: done
shipped-in: PR #79
slug: audit-doc-paths
date: 2026-05-01
---

# Plan: audit-doc-paths

## Goal

Audit non-ADR docs for stale `src/kanon/kit/aspects/<aspect>/` references and update them to the post-content-move canonical location `src/kanon_reference/data/<aspect>/`.

## Background

Phase A.7 (substrate-content-move sub-plan) moved the seven reference aspects' data (manifests, protocols, files) from `src/kanon/kit/aspects/<aspect>/` to `src/kanon_reference/data/<aspect>/`. Live wiring (LOADER manifests, entry-points, tests) was updated in that sub-plan, but downstream prose docs were not swept. This plan addresses the remaining drift.

## Scope

In scope:
- `docs/contributing.md` — module-tree section, architecture overview, "where does my change go?" decision matrix.

Out of scope (intentional):
- ADR bodies — frozen by `adr-immutability` (depth 3); they describe state at acceptance time.
- Historical `docs/plans/*.md` — plans are append-only records of past implementation; rewriting their paths would falsify the historical record.

## Acceptance criteria

- AC1: `grep -r "src/kanon/kit/aspects" docs/contributing.md` returns 0 matches.
- AC2: All 8 gates green (`kanon verify .` + 7 standalone CI checks).
- AC3: Full pytest suite passes.
- AC4: CHANGELOG entry under `## [Unreleased]` describing the doc-path audit.

## Steps

1. Identify the 6 stale references in `docs/contributing.md` (lines 35, 153, 155, 167, 168, 169, 172 in pre-edit state).
2. Apply Edits replacing the legacy path with the new canonical path; for line 155 (scaffolded ci/ files retired in Phase A.8), rewrite the description rather than just swap the path; for the new-aspect row (line 169), include the LOADER stub + entry-point declaration.
3. Run gates + full pytest.
4. Add CHANGELOG entry.
5. Commit + push + open PR + auto-merge.

## Verification

- `grep -r "src/kanon/kit/aspects" docs/contributing.md` → 0
- `kanon verify .` → ok
- `python scripts/check_links.py`, `check_foundations`, `check_kit_consistency`, `check_invariant_ids`, `check_packaging_split`, `check_verified_by`, `check_substrate_independence` → ok
- `pytest --no-cov -q` → all passing
