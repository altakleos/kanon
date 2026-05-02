---
status: approved
slug: phase-a.6a-resolutions-engine
date: 2026-05-02
design: docs/design/resolutions-engine.md
---

# Plan: Phase A.6a — `_resolutions.py` engine module (replay, canonicalization, stale-detection)

## Why split A.6 into three sub-plans

[ADR-0045](../../decisions/0045-de-opinionation-transition.md) §Decision step 6 names three new modules: `_resolutions.py`, `_dialects.py`, `_composition.py`. Per their respective designs ([`docs/design/resolutions-engine.md`](../../design/resolutions-engine.md) and [`docs/design/dialect-grammar.md`](../../design/dialect-grammar.md)) the combined footprint is ~+1,500 LOC source / +900 LOC tests across ~10 files. Splitting at the natural seam between the three modules:

- **A.6a (this plan):** `_resolutions.py` engine + synthetic tests. ~280 LOC source / ~600 LOC tests. Standalone module; no integration points changed.
- **A.6b (next plan):** `_dialects.py` + dialect-grammar enforcement. ~250 LOC source / ~150 LOC tests.
- **A.6c (next plan):** `_composition.py` + topo-sort + cycle reporting. ~270 LOC source / ~150 LOC tests.

This plan covers A.6a only.

## Context

Phase 0 ratified [ADR-0039](../../decisions/0039-contract-resolution-model.md): the substrate's runtime-binding model. Prose contracts → agent-resolved YAML → kernel replays mechanically. Six invariants in [`docs/specs/resolutions.md`](../../specs/resolutions.md). Companion design at [`docs/design/resolutions-engine.md`](../../design/resolutions-engine.md) specifies the engine end-to-end.

A.6a authors the engine module per that design. **No real consumer exists yet** — no contract-bearing aspects ship `realization-shape:` frontmatter; the kanon repo has no `.kanon/resolutions.yaml`. The engine is therefore tested entirely via synthetic fixtures. This is intentional: the engine is the substrate's foundational primitive, and a publisher can't demonstrate it until A.6a lands.

## Scope

### In scope

#### A. `src/kanon/_resolutions.py` (new module, ~280 LOC)

Implements the design's:

1. **Schema validator** — parses `.kanon/resolutions.yaml`, validates `schema-version: 1`, top-level shape, per-contract entries. Surfaces parse / shape errors.
2. **Canonicalization** — `canonicalize_entry(entry: dict) -> bytes`: strip `meta-checksum`, sort keys recursively, JSON-serialize with `sort_keys=True, separators=(",", ":")`, return UTF-8 bytes. SHA-256 over those bytes is the `meta-checksum`.
3. **Replay engine** — `replay(target: Path, registry: dict | None = None) -> ReplayReport`. Per-contract loop:
   - Hand-edit detection (recompute meta-checksum, compare).
   - Contract content-SHA pin (locate contract via aspect registry, recompute SHA, compare).
   - Evidence grounding (assert non-empty).
   - Per-evidence SHA pin (recompute SHA per evidence file, compare).
   - Execute realizations — **stubbed for A.6a**: invocation execution returns a placeholder `ExecutionResult(executed=False, reason="A.6a: invocation execution not yet implemented; A.7 wires kanon resolve / preflight integration")`.
4. **`ReplayReport` dataclass** — `errors: list[ReplayError]`, `executions: list[ExecutionRecord]`. `ReplayError` has `code`, `contract`, optional `path`, optional `reason`.
5. **`stale_check(target: Path, registry: dict | None = None) -> ReplayReport`** — alias for the pin-check-only path (no execution). Used by `kanon resolutions check` (A.7).

The "registry" parameter accepts `_load_aspect_registry()`'s output for contract-path lookup; `None` means "use the default" (resolved at function call time).

#### B. `tests/test_resolutions.py` (~600 LOC, ~25 cases)

One positive case + edge cases per invariant:

- INV-resolutions-machine-only-owned: hand-edit detection (positive: passes; edge: tampered checksum; edge: missing checksum)
- INV-resolutions-quadruple-pin: each of the four pins checked (positive + drift case per pin)
- INV-resolutions-evidence-grounded: empty evidence rejected
- INV-resolutions-replay-deterministic: same input → same output (running replay twice; identical reports)
- INV-resolutions-resolver-not-in-ci: not testable directly; this is a CI policy invariant — A.7's `kanon resolve` verb will respect it
- INV-resolutions-stale-fails: any pin drift surfaces an error; replay continues to next contract

Plus integration: full-cycle test (build a synthetic contract + resolution, replay, assert clean report).

#### C. CHANGELOG entry under `[Unreleased] § Added`.

### Out of scope

- **`kanon resolve` / `kanon resolutions check` / `kanon resolutions explain` CLI verbs** — A.7.
- **`_verify.py` integration** — defer until there's a real workload to replay.
- **Invocation execution** — stubbed; A.7 wires it to `kanon preflight` or similar.
- **`_dialects.py`** — A.6b.
- **`_composition.py`** — A.6c.
- **Aspect content move** — separate sub-plan.
- **`_kit_root()` retirement in `_scaffold.py`** — separate sub-plan.
- **`scripts/check_substrate_independence.py` gate** — separate sub-plan.
- **Spec / design / ADR / principle changes** — none.

## Approach

1. Author `src/kanon/_resolutions.py` per the design's `replay()` pseudocode + canonicalization + dataclasses.
2. Author `tests/test_resolutions.py` with synthetic fixtures (build contracts in tmp_path, write resolution.yaml, exercise replay).
3. Run all 6 standalone gates + full pytest. Fix any regressions (none expected — additive module).
4. CHANGELOG entry under `[Unreleased] § Added`.
5. Commit + push + auto-merge per "when done, merge".

## Acceptance criteria

### Module

- [ ] AC-M1: `src/kanon/_resolutions.py` exists with at minimum: `replay`, `stale_check`, `canonicalize_entry`, `ReplayReport`, `ReplayError`, `ExecutionRecord` symbols.
- [ ] AC-M2: `replay(target=Path('/nonexistent'))` returns an empty `ReplayReport` (no `.kanon/resolutions.yaml` = no replay; not an error).
- [ ] AC-M3: `canonicalize_entry({"meta-checksum": "x", "b": 1, "a": [3, 2]})` returns deterministic bytes; `meta-checksum` field stripped.

### Tests

- [ ] AC-T1: `tests/test_resolutions.py` exercises hand-edit detection (3 cases).
- [ ] AC-T2: Quadruple-pin checks (≥8 cases — positive + drift per pin).
- [ ] AC-T3: Evidence grounding (≥2 cases — non-empty passes; empty fails).
- [ ] AC-T4: Replay determinism (2 runs of same input produce identical reports).
- [ ] AC-T5: Stale detection (any pin drift surfaces an error; replay continues).
- [ ] AC-T6: Full-cycle integration (build synthetic contract + resolution, assert clean replay).
- [ ] AC-T7: All tests pass.

### CHANGELOG

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Added` gains a paragraph naming Phase A.6a.

### Cross-cutting

- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3..X7: standard gates pass (`check_links`, `check_foundations`, `check_kit_consistency`, `check_invariant_ids`, `check_packaging_split`, `check_verified_by`).
- [ ] AC-X8: No `src/kanon/cli.py` change (CLI verbs are A.7).
- [ ] AC-X9: No `src/kanon/_verify.py` change (integration deferred).
- [ ] AC-X10: No `src/kanon_reference/` change.
- [ ] AC-X11: Full pytest passes (no regression beyond the new module's tests).

## Risks / concerns

- **Risk: speculative engineering — no real consumer.** Mitigation: stick to the design's spec verbatim; don't add features beyond the 6 invariants. The engine is the substrate's foundational primitive — A.6b/c/A.7 build on it.
- **Risk: invocation-execution stub becomes load-bearing for A.7.** Mitigation: clear inline comment + structured `ExecutionRecord` shape so A.7 just swaps the stub for a real implementation.
- **Risk: contract-path resolution depends on `_load_aspect_registry()`'s shape.** Mitigation: `replay()` accepts an optional `registry` parameter for testability; tests inject synthetic registries.
- **Risk: YAML serializer non-determinism between Python versions / pyyaml versions.** Mitigation: canonicalization uses JSON (not YAML) for SHA computation; YAML is only the on-disk format.
- **Risk: 25 test cases without a real workload feels excessive.** Mitigation: reduce to ~15 if redundancy emerges during implementation; the design's footprint is upper-bound.

## Documentation impact

- **New files:** `src/kanon/_resolutions.py`, `tests/test_resolutions.py`, `docs/plans/phase-a.6a-resolutions-engine.md`.
- **Touched files:** `CHANGELOG.md`.
- **No changes to:** `src/kanon/cli.py`, `src/kanon/_verify.py`, `src/kanon_reference/`, aspect manifests, specs, designs, ADRs, foundations, principles, top-level `pyproject.toml`.
