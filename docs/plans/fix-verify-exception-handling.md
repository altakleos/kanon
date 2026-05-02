---
status: approved
slug: fix-verify-exception-handling
date: 2026-05-01
design: "No new design surface — bugfix to existing exception handlers in _verify.py."
---

# Plan: Fix verify exception handling — too-narrow except clauses

## Context

Four tests fail on `main` (verified independently from Phase A.1 PR #61):

- `tests/test_cli_verify.py::test_verify_unknown_aspect` — fails with `Error: Unknown aspect: 'kanon-bogus'`, exit 1
- `tests/test_fidelity.py::test_run_project_validators_manifest_load_failure` — fails with uncaught `Exception("manifest broken")`
- `tests/test_verify_validators.py::test_kit_validator_lookup_failure_warns` — fails with uncaught `RuntimeError("boom")`
- `tests/test_verify_validators.py::test_fidelity_capability_lookup_failure_warns` — fails with uncaught `RuntimeError("boom")`

All four share **one root cause**: the exception-handler tuples in `src/kanon/_verify.py` at three call sites are too narrow.

```python
# src/kanon/_verify.py:220, :273, :339
except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
    ...append("...lookup failed: {exc}")
    continue
```

The handlers were tightened at some point from `Exception` to a specific subclass tuple, but:

1. `_aspect_provides()` / `_aspect_validators()` / `_aspect_depth_validators()` raise `click.ClickException` for unknown aspects (`_manifest.py:244`, `:507`, `:547`) — not in the narrow tuple, so it propagates and crashes verify with "Error: Unknown aspect…", exit 1. **This breaks the spec invariant that unknown aspects must warn + exit 0** (per `docs/specs/aspects.md` invariant 4 — upstream-deprecation scenario).
2. The tests deliberately patch with `Exception` / `RuntimeError` to model "any lookup error", and the production code claims via docstring that "failed to load" is the contract — but the narrow tuple admits only four specific subclasses.

The function docstrings already promise broad failure handling ("Failures raised by a validator (import error, missing entrypoint, exception during ``check``) are recorded as errors and verify continues"). The tuple is the implementation drift; the docstring + tests are the intent.

## Goal

Land a single PR that:

1. Widens the three `except` clauses in `src/kanon/_verify.py` from `(OSError, yaml.YAMLError, KeyError, TypeError)` to `Exception`.
2. All four failing tests turn green.
3. No other test regresses.
4. CHANGELOG entry under `[Unreleased] § Fixed`.

## Scope

### In scope

- `src/kanon/_verify.py` lines 220, 273, 339 — three `except` clause widenings.
- `CHANGELOG.md` — one paragraph under `[Unreleased] § Fixed`.

### Out of scope

- Refactoring the surrounding error-handling shape (no introduction of new helper functions, no message rephrasing).
- Touching `_manifest.py` to change what `_aspect_*` raises (that's the documented contract; the bug is in the *handlers*, not the *raisers*).
- Adding new tests — the four pre-existing tests are the proof; they pass after the fix.
- Plan / spec / design / ADR / principle changes — none.

## Approach

1. Read `_verify.py` at the three call sites to confirm exact tuple.
2. Replace `except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:` → `except Exception as exc:` at each site.
3. Run the four previously-failing tests; confirm green.
4. Run full test suite to confirm no regression.
5. Run all standard gates.
6. Author CHANGELOG entry.
7. Commit + push + PR.

## Acceptance criteria

- [ ] AC-F1: `tests/test_cli_verify.py::test_verify_unknown_aspect` passes.
- [ ] AC-F2: `tests/test_fidelity.py::test_run_project_validators_manifest_load_failure` passes.
- [ ] AC-F3: `tests/test_verify_validators.py::test_kit_validator_lookup_failure_warns` passes.
- [ ] AC-F4: `tests/test_verify_validators.py::test_fidelity_capability_lookup_failure_warns` passes.
- [ ] AC-X1: Full pytest suite — 834 passed (was 830 + 4 fixed), 0 failed (was 4).
- [ ] AC-X2: `kanon verify .` returns `status: ok`.
- [ ] AC-X3: `python scripts/check_links.py` passes.
- [ ] AC-X4: `python scripts/check_foundations.py` passes.
- [ ] AC-X5: `python scripts/check_kit_consistency.py` passes.
- [ ] AC-X6: `python scripts/check_invariant_ids.py` passes.
- [ ] AC-X7: `python scripts/check_packaging_split.py` passes.
- [ ] AC-X8: `CHANGELOG.md` `[Unreleased] § Fixed` gains a paragraph naming the regression.
- [ ] AC-X9: Only `src/kanon/_verify.py`, `CHANGELOG.md`, and the plan file change.

## Risks / concerns

- **Risk: widening to `Exception` masks unrelated bugs.** Mitigation: the handlers append a descriptive message including the exception type and message (`type(exc).__name__: exc`). Operators see exactly what failed. The handlers are *fault-tolerant boundaries* by design — unknown-aspect / malformed-manifest / arbitrary-runtime-error in `_aspect_*` lookup is not a verify-time crash; it's a warning the user can act on.
- **Risk: catching `KeyboardInterrupt` or `SystemExit`.** Mitigation: `Exception` does not include `BaseException` subclasses like `KeyboardInterrupt` or `SystemExit`, so Ctrl-C still works.
- **Risk: spec drift.** The docstrings already promise broad handling ("import error, missing entrypoint, exception during ``check``"). The fix realigns implementation with documented contract; no spec update needed.

## Documentation impact

- **Touched files:** `src/kanon/_verify.py`, `CHANGELOG.md`.
- **New files:** `docs/plans/fix-verify-exception-handling.md`.
- **No changes to:** specs, designs, ADRs, foundations, aspect manifests, protocol prose, CI gates.
