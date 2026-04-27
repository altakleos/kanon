---
status: done
design: "Follows ADR-0028"
date: 2026-04-27
---
# Plan: Index Consistency Validator

## Goal

Add a kit validator that detects duplicate entries in scaffolded index
README files (`docs/specs/README.md`, `docs/decisions/README.md`,
`docs/plans/README.md`, `docs/design/README.md`).  Duplicate rows are a
common LLM-agent error (agents append without checking existing content)
and were found during the sensei reference-adoption audit.

## Scope

- New validator module: `src/kanon/_validators/index_consistency.py`
- Registered under `kanon-sdd` depth-1 (decisions + plans READMEs exist
  at depth 1; the validator gracefully skips directories that don't exist
  at lower depths).
- Emits **errors** (not warnings) for duplicate link targets within the
  same index file — a duplicate row is never intentional.
- Tests following the existing validator test pattern.

## Out of scope

- Validating that index rows link to files that exist (covered by
  `link_check`).
- Validating table formatting or column count.
- Bullet-list index formats (all kanon-scaffolded indexes use tables).

## Tasks

- [x] Write `src/kanon/_validators/index_consistency.py` with
  `check(target, errors, warnings)` entrypoint
- [x] Register in `src/kanon/kit/aspects/kanon-sdd/manifest.yaml` under
  `depth-1: validators:`
- [x] Add tests: duplicate detection, no false positives on clean index,
  self-hosting `test_real_repo_passes`
- [x] Verify: `pytest` green, `ruff check` clean

## Acceptance Criteria

1. `kanon verify .` on a project with a duplicate index row reports an
   error mentioning the file, the duplicate slug, and the line numbers.
2. `kanon verify .` on the kanon repo itself passes (no false positives).
3. The validator skips index files that don't exist (depth-1 project
   without specs/).
4. Code blocks inside README files are ignored (no false matches on
   template examples).
