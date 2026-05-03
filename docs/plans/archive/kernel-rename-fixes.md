---
slug: kernel-rename-fixes
status: done
owner: makutaku
created: 2026-05-03
related-adr: 0050
related-pr: 96
shipped-in: PR #97 (v0.5.0a2)
---

# Plan — Kernel-rename follow-up fixes (v0.5.0a2)

## Context

PR #96 (`feat: ADR-0050 Option A — rename Python package kanon → kernel`) merged at commit `5af7c65` and bumped the package version to v0.5.0a1. An adversarial critic pass against the merge commit identified 3 critical operational blockers, 3 major issues, and 4 cosmetic minors. The v0.5.0a1 release tag has **not** been cut yet; it is being held until these blockers are fixed.

This plan bundles all critical+major+minor follow-ups into a single PR and bumps to v0.5.0a2. The ratio of fix-size to risk is small enough that a paper-cuts split is unnecessary churn.

## Acceptance criteria

- AC1: `make typecheck` succeeds (Makefile mypy target points at `kernel/`).
- AC2: `make check` succeeds end-to-end.
- AC3: `.venv/bin/python -c "import kernel; print(kernel.__version__)"` prints `0.5.0a2`.
- AC4: `kanon release --tag v0.5.0a2 --dry-run` (or equivalent preflight invocation) does not fail at the `import kanon` line; release-preflight stage executes `import kernel` and version-asserts.
- AC5: Push-stage preflight commands resolve to existing files (`scripts/check_security_patterns.py`, `scripts/check_deps.py`).
- AC6: `pytest tests/scripts/test_check_security_patterns.py -v` passes; the test's assertion message no longer cites `src/kanon/`.
- AC7: `scripts/release-preflight.py` scans only `kernel/` for `__init__.py` (no longer rglobs `src/`).
- AC8: CHANGELOG `## [0.5.0a2] — 2026-05-03` section exists and lists the fixes.
- AC9: All 7 standalone gates green; full pytest passes.
- AC10: Fidelity recaptured.

## Scope

### In
- `.kanon/config.yaml` — fix release-stage `import kanon` → `import kernel`; fix push-stage `ci/` → `scripts/`; bump `kit_version: 0.5.0a2`.
- `Makefile` — `mypy src/kanon/` → `mypy kernel/`.
- `tests/scripts/test_check_security_patterns.py` — replace `src/kanon/` in docstring + assertion message with `kernel/`.
- `scripts/release-preflight.py` — narrow `_find_version()` to scan only `kernel/__init__.py`.
- `kernel/__init__.py` — `__version__ = "0.5.0a2"`.
- `CHANGELOG.md` — new `## [0.5.0a2]` section under Unreleased.
- Cosmetic minors:
  - `kernel/_cli_helpers.py:286`, `kernel/_rename.py:13` — Sphinx cross-refs `kanon.` → `kernel.`
  - `src/kanon_reference/aspects/kanon_fidelity/manifest.yaml:9` — comment path
  - `docs/design/distribution-boundary.md` — stale `src/kanon/` cites at lines 52/189/193/228

### Out
- ADR-immutability does not fire (no ADR body edits).
- No new tests; existing `tests/scripts/` coverage is sufficient and the criticals are configuration/path errors that any fresh `make check` would expose. Adding a `check_preflight_resolvable.py` gate is a worthwhile follow-up but out of scope here (separate PR).
- `src/kanon_reference/` rename to `aspects/` (ADR-0049 §1(7)) — same Hatch constraint as the kernel-flatten; deferred.

## Steps

1. Edit `.kanon/config.yaml`: lines 45, 47 (`ci/` → `scripts/`); line 50 (`import kanon` → `import kernel`, `kanon.__version__` → `kernel.__version__`); line 13 (`kit_version`).
2. Edit `Makefile:11` (`src/kanon/` → `kernel/`).
3. Edit `tests/scripts/test_check_security_patterns.py:17,30` (path-cites).
4. Edit `scripts/release-preflight.py:31-39` (narrow `_find_version()` to `kernel/__init__.py` only).
5. Edit `kernel/__init__.py` (version bump 0.5.0a1 → 0.5.0a2).
6. Edit `CHANGELOG.md` (new 0.5.0a2 section).
7. Edit `kernel/_cli_helpers.py:286`, `kernel/_rename.py:13` (Sphinx cross-refs).
8. Edit `src/kanon_reference/aspects/kanon_fidelity/manifest.yaml:9` (comment).
9. Edit `docs/design/distribution-boundary.md` (4 stale cites).
10. Run `.venv/bin/python -c "import kernel; print(kernel.__version__)"` → expect `0.5.0a2`.
11. Run `make check` → expect success.
12. Run full pytest → expect 964 passing.
13. Run `kanon fidelity update` to refresh `.kanon/fidelity.lock`.
14. Run all 7 standalone gates.
15. Commit, push, PR with auto-merge.

## Risks

- **Version-bump ordering**: changing `kit_version` in `.kanon/config.yaml` independently of `kernel/__init__.py` would create a drift the release-preflight catches. Both are bumped in the same commit. ✓
- **fidelity recapture**: editing `.kanon/config.yaml` will cause the fidelity hash for the config-mirror to change. Recapture in step 13 covers this.
- **CHANGELOG promotion**: keep entries under `## [0.5.0a2]`, do NOT touch the existing `## [0.5.0a1]` history (that release was conceptually shipped — even though no tag was cut, the merge to main is the de-facto shipment).
