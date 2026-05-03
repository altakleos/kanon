---
status: draft
slug: kernel-rename-option-a
date: 2026-05-03
---

# Plan: Kernel rename (ADR-0050 Option A) — `kanon` Python package → `kernel`

## Status

**Draft — not yet authorized for execution.** This plan exists to scope the work outlined in ADR-0050 §Decision Option A so a future cycle can pick it up with concrete acceptance criteria. Promote `status: draft` → `status: approved` only when the user has reviewed + authorized the rename. Until promoted, this plan is informational only.

## Goal

Rename the substrate Python package from `kanon` → `kernel` so the source tree matches ADR-0049's intent (`kernel/cli.py` at depth 2). Preserve:
- The user-facing CLI command name `kanon` (Click app stays named `kanon`).
- The distribution names `kanon-substrate` / `kanon-reference` / `kanon-kit` (PyPI surface unchanged).
- The entry-point group name `kanon.aspects` (per ADR-0040's runtime contract for `acme-` publishers).
- The aspect slugs `kanon-sdd`, `kanon-testing`, etc.
- The consumer's `.kanon/` directory + config schema.

Change:
- The Python import path: `from kanon.X import Y` → `from kernel.X import Y` (substrate-internal).
- The wheel-imported package name: when a consumer's pyproject lists `kanon-substrate`, `pip install kanon-substrate` lands `kernel/` on `sys.path`.
- 49 substrate-internal files updated by mechanical grep-replace.

## Background

ADR-0050 ratified the kernel-flatten deferral and named three options. Option A (Python package rename) is the destination per the panel's depth-2 ergonomic goal. Why deferred: the rename was not in the panel's vocabulary; the panel envisioned a filesystem-only `git mv` + Hatch source-remap; the editable-install constraint discovered during ADR-0050 PR-E execution forced a different path.

Per ADR-0048, kanon has zero current external consumers. The Python-import-path rename has zero downstream cost; the substrate-internal rename is bounded to ~49 files (per quick grep at plan-write time).

## Scope

In scope:
- `git mv src/kanon kernel`.
- Bulk grep-replace `kanon\.` → `kernel\.` in:
  - `tests/**/*.py` (ImportError-class refs).
  - `kernel/_validators/**/*.py` (validators imported back into `kanon._validators`).
  - `scripts/check_*.py` (a few scripts import from substrate).
  - `kernel/cli.py`'s docstrings + click `version_option(__version__, prog_name="kanon")` — note: `prog_name="kanon"` STAYS (CLI command name).
  - `pyproject.toml`: `[tool.hatch.version] path = "kernel/__init__.py"`; `[tool.hatch.build.targets.wheel] packages = ["kernel", "src/kanon_reference"]`; `[tool.mypy] packages = ["kernel"]`; `[tool.coverage.run] source = ["kernel"]`; `[tool.ruff] src = ["kernel", "src", "tests", "scripts"]`; `[project.scripts] kanon = "kernel.cli:main"`.
- Update `kernel/_manifest.py:_kit_root` if it uses `Path(kanon.__file__)` (it should use `Path(__file__).parent / "kit"` which is robust). Verify.
- Update `kernel/__init__.py` docstring.
- Update active doc refs (contributing.md, kanon-implementation.md, etc.) where they cite the substrate-internal Python import path.
- Recapture fidelity lock.

Out of scope:
- The user-facing CLI command name (`kanon` stays).
- Distribution names (`kanon-substrate`, `kanon-kit`, `kanon-reference` stay).
- Entry-point group `kanon.aspects` (stays — it's the protocol contract per ADR-0040).
- The `aspects/` rename (ADR-0049 §1(7); separate plan; same constraint applies if attempted via Hatch).
- Any consumer-facing config (`.kanon/`, `kanon init`, etc.).
- ADR / spec / done-plan body edits (immutable; their refs to `kanon.X` describe historical state).

## Acceptance criteria

- AC1: `src/kanon/` no longer exists; `kernel/` contains the substrate source at depth 1.
- AC2: `from kernel.cli import main` works in tests + at runtime.
- AC3: `from kanon.cli import main` raises `ModuleNotFoundError` (the rename is COMPLETE; no shim).
- AC4: `kanon --version` prints `0.4.0a5` (or whatever the bump version is).
- AC5: `kanon verify .` exits 0.
- AC6: `kanon-substrate` wheel `pip install`s and `python -c "import kernel; print(kernel.cli.main)"` works.
- AC7: 7 standalone gates pass; full pytest passes.
- AC8: Active docs reference `kernel.X` for substrate imports; ADR/done-plan/CHANGELOG history preserved.
- AC9: Version bump to `0.4.0a5` (or 0.5.0a1 if breaking-change framing is preferred — see "Versioning question" below).

## Steps

1. Author Allow-ADR-edit trailers list (which accepted ADRs cite `kanon.` import paths and need link/text updates).
2. `git mv src/kanon kernel`.
3. Update `pyproject.toml` build/version/lint config.
4. `uv sync --reinstall` to re-link.
5. Smoke: `python -c "import kernel; print(kernel.__version__)"` works.
6. Bulk sed: `from kanon\.` → `from kernel\.`; `import kanon\.` → `import kernel\.`. Restrict to `tests/**`, `kernel/**`, `scripts/**`. DO NOT touch `kanon_reference` package or `aspects/` consumer.
7. Update doc refs (contributing.md path-cites of `src/kanon/` → `kernel/`).
8. Run gates iteratively + fix.
9. Run full pytest + fix any test path/import constants.
10. Recapture fidelity.
11. CHANGELOG entry.
12. Bump version.
13. Commit + push + PR + merge (with `Allow-ADR-edit:` trailers per accepted ADRs that need link/text updates).

## Versioning question

The rename is BREAKING for any code that does `from kanon.X import Y`. There are no current external consumers per ADR-0048, so the cost is zero externally. Two framings:

- **Patch-class bump (0.4.0a4 → 0.4.0a5)**: substrate-internal-only change; consumers see no API change (everything routes through `kanon` CLI / `kanon-kit` wheel). Honest IF we accept "the importable Python module name is internal API."
- **Minor-class bump (0.4.0a4 → 0.5.0a1)**: signals the breaking nature of the import rename. Conservative; correct per SemVer for any future PyPI release that anyone DOES `pip install kanon-substrate` against (the importable module changes from `kanon` to `kernel`).

Recommendation: **0.5.0a1**. Even with zero current consumers, the rename changes a public surface (the importable wheel package) and SemVer-correct framing helps downstream tooling reason about it.

## Risk + rollback

Risk: moderate. Touches every substrate-internal Python file. The grep-replace is mechanical but easy to miss edge cases (string literals containing `kanon.`, doctests, etc.). Mitigation: run pytest after each batch; ruff to catch obvious miss; manual scan of remaining `kanon\.` refs to triage internal vs. CLI-name / distribution-name / entry-point-group / aspect-slug.

Rollback: `git revert <merge-commit>`. The PR is a single squash merge; revert is atomic. The substrate's runtime entry-points (consumer's `.kanon/config.yaml` references aspect SLUGS, not Python module names) are unaffected; consumers won't break by either direction.

## Out of scope, deferred

- The `aspects/` flatten (ADR-0049 §1(7)). Same engineering constraint applies; needs its own ADR + plan.
- Setuptools migration (ADR-0050 §Alternatives Considered #3). Scope too large for a focused rename PR.
- Renaming the entry-point group `kanon.aspects` → `kernel.aspects`. Would break ADR-0040's protocol contract; out of scope without a fresh ADR.

## Promotion criteria (when to flip status: draft → approved)

- User has reviewed this plan and explicitly authorized the rename.
- A version-bump decision (0.4.0a5 vs. 0.5.0a1) is locked.
- A maintenance window is allocated (1-2 hours of focused execution + CI cycle).
- No competing in-flight migration PR (this rename touches files other PRs may also touch).

Until those four conditions are met, this plan stays `status: draft`.
