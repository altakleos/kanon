---
status: approved
slug: phase-a.4-detect-removal
date: 2026-05-02
design: docs/design/distribution-boundary.md
---

# Plan: Phase A.4 — `_detect.py` deletion + testing-aspect runtime config-schema removal

## Context

Per [ADR-0045](../decisions/0045-de-opinionation-transition.md) §Decision step 4: "`_detect.py` deleted; testing-aspect runtime config-schema removed". Per [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) (de-opinionation): the substrate has no opinion about which build tools a consumer uses (pytest vs unittest vs npm test) nor about which config keys an aspect's user-config block should contain. Auto-detection of pytest/ruff/mypy/npm and the substrate-side reading of `${test_cmd}` / `${lint_cmd}` / `${typecheck_cmd}` / `${format_cmd}` from the kanon-testing aspect's config block both violate de-opinionation.

## Substrate consumers

**`_detect.py` (71 LOC):**
- `src/kanon/_detect.py` — auto-detects pytest / ruff / mypy / npm test from project files; returns dict matching kanon-testing's config-schema keys
- `src/kanon/cli.py:309-322` — single call site: `kanon init` invokes `detect_tool_config()` and merges results into `aspects_meta["kanon-testing"]["config"]`
- `tests/test_detect.py` (104 LOC, 7 tests)

**Testing-aspect runtime config-schema (`test_cmd`, `lint_cmd`, `typecheck_cmd`, `format_cmd`):**
- `src/kanon/cli.py:97-119` — `_emit_init_hints()` "Preflight readiness" section reads `testing_cfg.get("test_cmd"/...)` and emits stderr feedback about which preflight checks are armed
- The kanon-testing aspect's `config-schema:` block declares these 4 keys + `coverage_floor` (in both `src/kanon_reference/aspects/kanon_testing.py:MANIFEST` and `src/kanon/kit/aspects/kanon-testing/manifest.yaml`)

## Goal

Single PR that:

1. Deletes `src/kanon/_detect.py` (71 LOC) entirely.
2. Deletes `tests/test_detect.py` (104 LOC).
3. Removes `_detect.py`'s import + invocation from `cli.py:309-322` (the `kanon init` auto-detect block).
4. Removes the testing-aspect runtime config-schema usage in `_emit_init_hints()` (`cli.py:97-119` Preflight readiness section).
5. Deletes the `config-schema:` block from `kanon-testing`'s LOADER MANIFEST (`src/kanon_reference/aspects/kanon_testing.py`) and the YAML source-of-truth (`src/kanon/kit/aspects/kanon-testing/manifest.yaml`). Also delete the corresponding `config:` block from `.kanon/recipes/reference-default.yaml` (no longer meaningful).
6. Audits any tests that depend on `_emit_init_hints` preflight-readiness output or kanon-testing's config-schema.
7. Recaptures `.kanon/fidelity.lock`.
8. CHANGELOG entry under `[Unreleased] § Removed`.

## Scope

### In scope

#### A. Delete `src/kanon/_detect.py` and `tests/test_detect.py`

Files removed entirely.

#### B. Remove auto-detect block from `cli.py:309-322`

```python
# Auto-detect project type and pre-fill testing config.
aspects_meta = _aspects_with_meta(aspects_to_enable)
if "kanon-testing" in aspects_meta:
    from kanon._detect import detect_tool_config
    detected_tools = detect_tool_config(target)
    if detected_tools:
        existing_config: dict[str, Any] = aspects_meta["kanon-testing"].get("config", {})
        for key, val in detected_tools.items():
            existing_config.setdefault(key, val)
        aspects_meta["kanon-testing"]["config"] = existing_config
        click.echo(
            f"  Detected project tools: {', '.join(detected_tools.keys())}",
            err=True,
        )
```

Replaced with a single comment marking the removal.

`aspects_meta = _aspects_with_meta(aspects_to_enable)` line is preserved (still needed downstream).

#### C. Remove preflight-readiness section from `_emit_init_hints()` (`cli.py:97-119`)

Lines 102-119 read kanon-testing's `config:` block for `test_cmd`/`lint_cmd`/`typecheck_cmd`/`format_cmd` and emit stderr feedback. Delete this section. The function's `grow_hints` section (suggesting which aspects to add) stays — that's a separate concern A.5+ may revisit.

If `_emit_init_hints` becomes empty after removing both sections, delete the function entirely + its callsite.

#### D. Delete `config-schema:` from kanon-testing MANIFEST + YAML

- `src/kanon_reference/aspects/kanon_testing.py` — delete the `"config-schema": {...}` block (lines 39-70)
- `src/kanon/kit/aspects/kanon-testing/manifest.yaml` — delete the corresponding `config-schema:` block

The publisher (kanon-reference) keeps full control over the aspect; it just no longer declares opinionated config keys. `acme-` publishers can declare their own config-schema if they want to.

#### E. Recipe + repo config cleanup

- `.kanon/recipes/reference-default.yaml` carries a `config:` block under `kanon-testing` that hardcodes the 4 testing keys. Delete that block (the recipe still lists kanon-testing as an aspect — just without runtime config).
- `.kanon/config.yaml` (kanon repo's self-host config) carries the same hardcoded testing-config under v3 `aspects.kanon-testing.config`. **Decision: leave for A.4 OR clean up here?** Leaving it preserves backward-compat with current tooling that may still read it (e.g., release-preflight scripts). Deleting it aligns with de-opinionation. Plan: **delete from .kanon/config.yaml** since the substrate no longer reads these keys.

#### F. Audit tests

- `tests/test_cli.py` — search for "Preflight readiness", "Detected project tools", "test_cmd"/"lint_cmd" references; update or delete tests that asserted these outputs.
- `tests/test_cli_aspect.py` / `tests/test_e2e_lifecycle.py` — search for testing-config assertions.

#### G. Recapture fidelity lock

`.kanon/fidelity.lock` will pick up the kanon-testing manifest changes; regenerate via `kanon fidelity update .`.

#### H. CHANGELOG entry

Paragraph under `[Unreleased] § Removed`.

### Out of scope

- **Aspect content move** (`src/kanon/kit/aspects/` → `src/kanon_reference/aspects/`) — dedicated sub-plan.
- **`_kit_root()` retirement in `_scaffold.py`** — blocks on content move.
- **`scripts/check_substrate_independence.py` gate** — blocks on content move.
- **Bare-name CLI sugar deprecation** — A.5.
- **`_emit_init_hints` grow_hints section** — separate concern; A.5+ may revisit.
- **Kit YAML's `aspects:` block deletion** — bundle with content-move.
- **Spec / design / ADR / principle changes** — none.

## Approach

1. Delete `src/kanon/_detect.py` + `tests/test_detect.py`.
2. Remove auto-detect block from `cli.py:309-322`.
3. Remove preflight-readiness section from `cli.py:97-119` (`_emit_init_hints()`).
4. Delete `config-schema:` block from kanon-testing MANIFEST + YAML (both sources).
5. Delete `config:` block from `.kanon/recipes/reference-default.yaml`'s kanon-testing entry.
6. Delete kanon-testing config keys from `.kanon/config.yaml` (the kanon repo's self-host config).
7. Audit tests; update or delete obsolete ones.
8. Recapture fidelity lock with `kanon fidelity update .`.
9. Run all gates + full pytest. Fix regressions.
10. CHANGELOG entry under `[Unreleased] § Removed`.
11. Commit + push + auto-merge per "when done, merge".

## Acceptance criteria

### File deletions

- [ ] AC-D1: `src/kanon/_detect.py` no longer exists.
- [ ] AC-D2: `tests/test_detect.py` no longer exists.

### Substrate code

- [ ] AC-S1: No source file imports `kanon._detect`.
- [ ] AC-S2: `cli.py` `kanon init` no longer auto-fills `aspects_meta["kanon-testing"]["config"]`.
- [ ] AC-S3: `cli.py:_emit_init_hints()` no longer emits "Preflight readiness" section (function body trimmed or function deleted entirely).

### LOADER MANIFEST + YAML

- [ ] AC-M1: `src/kanon_reference/aspects/kanon_testing.py:MANIFEST` no longer contains a `config-schema` key.
- [ ] AC-M2: `src/kanon/kit/aspects/kanon-testing/manifest.yaml` no longer contains a `config-schema:` block.
- [ ] AC-M3: `.kanon/recipes/reference-default.yaml`'s kanon-testing entry no longer carries a `config:` block.
- [ ] AC-M4: `.kanon/config.yaml`'s `aspects.kanon-testing.config` block deleted (or empty `{}`).

### Tests

- [ ] AC-T1: `tests/test_kanon_reference_manifests.py` parametrized tests pass (LOADER MANIFEST union with top-entry equals expected — config-schema removed from both sources, equivalence still holds).
- [ ] AC-T2: Audit completed; tests that asserted preflight-readiness output or testing config-schema updated/deleted.
- [ ] AC-T3: Full pytest passes.

### Fidelity

- [ ] AC-F1: `.kanon/fidelity.lock` regenerated; `kanon verify .` returns `status: ok`, zero warnings.

### CHANGELOG

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Removed` gains a paragraph naming Phase A.4.

### Cross-cutting

- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3..X6: standard gates pass (`check_links`, `check_foundations`, `check_kit_consistency`, `check_invariant_ids`, `check_packaging_split`).
- [ ] AC-X7: No `src/kanon_reference/` change beyond the kanon-testing config-schema deletion.
- [ ] AC-X8: No aspect content moved.
- [ ] AC-X9: No `_kit_root()` call sites in `_scaffold.py` retired (those are deferred to content-move sub-plan).

## Risks / concerns

- **Risk: tests that assert "Detected project tools: pytest" in stderr break.** Mitigation: audit during implementation; delete those assertions.
- **Risk: tests that assert "Preflight readiness" in stderr break.** Same mitigation.
- **Risk: real users' release-preflight scripts depended on `${test_cmd}` substitution.** The kanon repo's `.kanon/config.yaml` declares `test_cmd: .venv/bin/python -m pytest --no-cov -q` — release-preflight may interpolate this. Audit `scripts/release-preflight.py`. If it reads `aspects.kanon-testing.config.test_cmd`, that becomes a hardcode in the script (or moves to a new location).
- **Risk: `kanon fidelity update .` regenerate may fail if the kanon-testing config-schema removal cascades through fixtures.** Mitigation: run regen interactively; if it fails, narrow the scope of cleanup.
- **Risk: backward-compat for v0.3.x consumers.** Per ADR-0045 there is no backward-compat. The migration script (A.9) handles the kanon repo's own transition.

## Documentation impact

- **Deleted files:** `src/kanon/_detect.py`, `tests/test_detect.py`.
- **Touched files:** `src/kanon/cli.py` (~25 lines removed); `src/kanon_reference/aspects/kanon_testing.py` (config-schema block); `src/kanon/kit/aspects/kanon-testing/manifest.yaml` (config-schema block); `.kanon/recipes/reference-default.yaml` (config block); `.kanon/config.yaml` (testing config keys); audited test files; `.kanon/fidelity.lock`; `CHANGELOG.md`.
- **New files:** `docs/plans/phase-a.4-detect-removal.md`.
- **No changes to:** specs, designs, ADRs, foundations, principles, protocol prose, `src/kanon_reference/` beyond the noted block, aspect content, top-level `pyproject.toml`.
