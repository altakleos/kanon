---
status: approved
slug: migration-pr-b-kill-packaging
date: 2026-05-02
---

# Plan: Migration PR B — Kill `packaging/` (per ADR-0049 §Implementation Roadmap step B)

## Goal

Delete the inert `packaging/{substrate,reference,kit}/pyproject.toml` schema-of-record tree that ADR-0049's panel archaeology identified as dead weight (zero entries in top-10 most-touched files; broken `../../README.md` relative paths; never invoked by the build). Honors ADR-0049 §1(1) ("kill `packaging/`") at the lowest possible blast radius.

## Background

ADR-0049 §1(1) commits to "one pyproject per distribution, co-located with its source." The destination shape is a 3-distribution workspace (kanon-substrate, kanon-reference, kanon-kit) with `[tool.uv.workspace]` at the root. Today there is ONE active distribution: `kanon-kit` v0.4.x. The `packaging/<dist>/pyproject.toml` files are schema-of-record for the eventual split but are not built; the active build path is the top-level `pyproject.toml`.

This PR honors the "kill packaging/" rule by deleting the schema-of-record. The full workspace rearchitecture (3 co-located pyprojects + workspace root) is deferred to the future PR that actually splits the distribution (when `pip install kanon-substrate` becomes a real install path). Deferring keeps PR B at low blast radius while removing the panel-flagged inert artifact.

## Scope

In scope:
- Delete `packaging/substrate/`, `packaging/reference/`, `packaging/kit/`, including their pyproject.toml + any other files under each.
- Delete `ci/check_packaging_split.py` (no longer has a schema to validate).
- Delete `tests/ci/test_check_packaging_split.py`.
- Remove `check_packaging_split.py` invocation from `.github/workflows/checks.yml` (or wherever it's wired).
- CHANGELOG entry noting the deletion and the deferral of the workspace rearchitecture.

Out of scope (deferred to future PRs):
- The actual 3-distribution workspace structure (co-located pyprojects + `[tool.uv.workspace]` root). This lands when `pip install kanon-substrate` becomes a real install need.
- Other ADR-0049 migration steps (PR C-F).

## Acceptance criteria

- AC1: `packaging/` directory no longer exists.
- AC2: `ci/check_packaging_split.py` no longer exists.
- AC3: `tests/ci/test_check_packaging_split.py` no longer exists.
- AC4: GitHub Actions workflow no longer invokes `check_packaging_split.py`.
- AC5: Full pytest passes (one fewer test file; everything else unchanged).
- AC6: 7 standalone gates pass (one fewer gate: `check_packaging_split` removed).
- AC7: `kanon verify .` exits 0.
- AC8: CHANGELOG entry under `## [Unreleased]`.

## Steps

1. `git rm -rf packaging/`.
2. `git rm ci/check_packaging_split.py`.
3. `git rm tests/ci/test_check_packaging_split.py`.
4. Edit `.github/workflows/checks.yml` (or `.github/workflows/verify.yml`) to remove `check_packaging_split.py` step.
5. Run gates + pytest.
6. CHANGELOG entry.
7. Commit + push + PR + merge.

## Verification

- `test ! -d packaging && echo OK`
- `test ! -f ci/check_packaging_split.py && echo OK`
- `pytest --no-cov -q` → 977 passed (one fewer file's worth of tests; no new failures)
- `kanon verify .` → ok
- 7 gates → ok
