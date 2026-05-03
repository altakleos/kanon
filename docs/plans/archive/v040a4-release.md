---
status: done
shipped-in: PR #93
slug: v040a4-release
date: 2026-05-03
---

# Plan: v0.4.0a4 release-prep + ADR-0050 (kernel-flatten supersession)

## Goal

(1) Author ADR-0050 documenting the editable-install constraint that blocked ADR-0049 §1(2) (kernel-flatten); supersedes that one rule with a constraint-aware deferral. (2) Cut v0.4.0a4 release capturing the 5 ADR-0049 migration PRs (A, B, C, D, F) that DID land in this cycle.

## Background

PR E attempted `git mv src/kanon kernel` + Hatch `[tool.hatch.build.targets.wheel.sources] "kernel" = "kanon"` mapping. The mapping fails on editable installs (PEP 660): the `editables` library only supports prefix STRIP (`"src" = ""`), not prefix RENAME. ADR-0049 §1(2) presupposed Hatch could do this rename; the assumption was wrong. ADR-0050 documents the constraint + commits to a future direction (rename Python package OR accept depth-3 status quo OR migrate build tool).

## Scope

In scope:
- Author `docs/decisions/0050-kernel-flatten-deferral.md` (status: draft for user review).
- Bump `src/kanon/__init__.py` `__version__` to `0.4.0a4`.
- Bump `.kanon/config.yaml` `kit_version` to `0.4.0a4`.
- Rename CHANGELOG `## [Unreleased]` → `## [0.4.0a4] — 2026-05-03`; insert empty Unreleased above.
- CHANGELOG entry under v0.4.0a4 noting the ADR-0050 draft + the 5 migration PRs already documented above.

Out of scope:
- Cutting the actual release tag (shared-state action; user confirms separately after this PR merges).
- Implementing PR E (deferred per ADR-0050).
- Promoting ADR-0050 to accepted (user reviews then flips).

## Acceptance criteria

- AC1: ADR-0050 exists at `docs/decisions/0050-kernel-flatten-deferral.md` with `status: draft`.
- AC2: `__version__` is `"0.4.0a4"`; `kit_version` matches; CHANGELOG section dated 2026-05-03.
- AC3: 7 standalone gates green.
- AC4: Full pytest passes (no source code changes; should be no-op).

## Steps

1. Author ADR-0050 (status:draft).
2. Bump `__version__` + `kit_version`.
3. Rename CHANGELOG `## [Unreleased]` → `## [0.4.0a4] — 2026-05-03`; insert empty Unreleased.
4. Run gates + pytest.
5. CHANGELOG addition for ADR-0050 draft + version-bump line.
6. Commit + push + open PR + merge.
7. **Out of band**: user cuts the actual release tag.

## Verification

- `kanon verify .` → ok
- `python -c "import kanon; print(kanon.__version__)"` → `0.4.0a4`
- 7 gates → ok
- `pytest --no-cov -q` → 964 passed
