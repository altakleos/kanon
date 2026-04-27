---
feature: review-followups-batch-1
serves:
  - vision
status: done
date: 2026-04-27
---
# Plan: Review-followups batch 1 — recovery model, coverage floor, vocabulary, capability docs

## Context

Closes four "documented but not delivered" gaps surfaced by the comprehensive v1-readiness review:

1. **Recovery prose vs. implementation** — ADR-0024 §Consequences promises *"after any interruption, the next `kanon` invocation completes the transition before doing anything else"*, but `_check_pending_recovery` only emits a warning. `recover_pending_rename` exists in `_rename.py` but is never wired in. The honest model is hybrid: graph-rename auto-recovers via its ops-manifest; other sentinels rely on idempotent re-run. This plan delivers the wiring for graph-rename and ratifies the hybrid via an ADR-lite that amends ADR-0024 §Consequences.
2. **Coverage-floor disconnect** — the kit-testing aspect declares `coverage_floor: integer (default 80)` in its `config-schema:`, the kit's own `.kanon/config.yaml` carries `coverage_floor: 80`, and the AGENTS.md test-discipline prose claims to enforce "the configured floor". But pyproject's `--cov-fail-under=90` is the only enforcement, and nothing reads the configured value. This is a P-prose-is-code violation. The fix here is prose-only: clarify that `coverage_floor` is advisory metadata that consumers wire into their own CI; document that the kit's own stricter 90 is internal, not the documented floor.
3. **`Tier:` vocabulary in kit.md** — `src/kanon/kit/kit.md` line 7 still labels the depth value as `**Tier:**`, residue from before ADR-0012 introduced the aspect-depth model. Visible to every consumer's `.kanon/kit.md`.
4. **Capability depth-0 supplier semantics** — `_check_requires` rejects a depth-0 supplier for capability-presence predicates (the `>= 1` guard), but no doc mentions this. A reader of the spec would assume depth-0 suppliers count.

## Tasks

### Phase 0 — ADR-lite

- [x] T1: Write ADR-0029 — ADR-lite (~15 lines) capturing the actual recovery model. Hybrid: `graph-rename` auto-recovers via its ops-manifest (existing `recover_pending_rename` in `_rename.py:485`); all other sentinels emit a warning suggesting manual re-run, relying on idempotent commands. Amends ADR-0024 §Consequences without superseding it. → `docs/decisions/0029-recovery-model.md`

### Phase 1 — Recovery integration

- [x] T2: Wire `recover_pending_rename` into `_check_pending_recovery` for the `graph-rename` sentinel. Successful recovery emits `Recovered interrupted '<op>' operation by replaying ops-manifest.` instead of the warn-and-rerun message. Other sentinels keep the existing warn message. → `src/kanon/cli.py`
- [x] T3: Test: a partial graph-rename whose ops-manifest is on disk gets auto-replayed on the next CLI invocation; sentinel and ops-manifest are cleared; the "Recovered" message is emitted; the warning is NOT emitted. → `tests/test_graph_rename.py`

### Phase 2 — Coverage floor reconciliation

- [x] T4: Update the kit-testing test-discipline prose to clarify the actual contract: `coverage_floor` is the configured advisory value in `.kanon/config.yaml`; the kit declares it for consumer reference but does not auto-wire it into `pytest --cov-fail-under` (consumers wire that themselves in their own `pyproject.toml` / CI). → `src/kanon/kit/aspects/kanon-testing/sections/test-discipline.md` (the byte-equal mirror in this repo's AGENTS.md re-renders via upgrade)
- [x] T5: Add a comment to the kit-testing manifest's `config-schema:` entry noting that `coverage_floor` is advisory metadata. → `src/kanon/kit/aspects/kanon-testing/manifest.yaml`

### Phase 3 — Vocabulary cleanup

- [x] T6: `src/kanon/kit/kit.md` line 7 — change `**Tier:** ${sdd_depth}` to `**SDD depth:** ${sdd_depth}`. Re-render this repo's own `.kanon/kit.md` via `kanon upgrade .`. → `src/kanon/kit/kit.md`, `.kanon/kit.md`

### Phase 4 — Capability depth-0 doc

- [x] T7: Add a "Depth-0 supplier semantics" sentence to `docs/specs/aspect-provides.md` clarifying that a capability supplier at depth 0 does not satisfy a 1-token capability `requires:` predicate; depth ≥ 1 is required. Add the same clarification as a docstring note in `_check_requires`. → `docs/specs/aspect-provides.md`, `src/kanon/cli.py`

### Phase 5 — CHANGELOG + verify

- [x] T8: Single CHANGELOG entry under `## [Unreleased]` summarising the four fixes and referencing ADR-0029. → `CHANGELOG.md`
- [x] T9: `kanon fidelity update .` to track the spec SHA changes from T7. → `.kanon/fidelity.lock`

## Acceptance Criteria

- [x] AC1: `_check_pending_recovery` automatically completes a partial `graph-rename` op when the sentinel and ops-manifest are both present; the "Recovered" message is emitted; no manual re-run is required.
- [x] AC2: Test-discipline prose accurately describes `coverage_floor` as advisory consumer-side metadata; readers no longer infer that the kit auto-wires it into pytest.
- [x] AC3: `src/kanon/kit/kit.md` no longer references "Tier:" anywhere.
- [x] AC4: `docs/specs/aspect-provides.md` documents the depth-0 supplier semantics.
- [x] AC5: pytest, ruff, mypy pass; coverage above floor; `kanon verify .` is `status: ok` with zero warnings.

## Out of Scope

- **Wiring `coverage_floor` into pytest dynamically.** A future helper command (`kanon testing coverage-floor <target>`) could emit the value for consumer wiring; deferred until a real consumer asks for it.
- **Auto-recovery for non-graph-rename sentinels.** The ADR-lite explicitly says manual re-run is the model for those (idempotent commands; sentinel name signals which command to re-run).
- **Promoting `multi-agent-coordination.md` from deferred to draft.** Separate roadmap decision.
- **Beefing up `kanon-implementation.md`.** Doc cleanup deferred.

## Documentation Impact

- AGENTS.md test-discipline section text changes (visible to every consumer on next `kanon upgrade`).
- README.md unchanged (the project-aspects PR already covered the namespace grammar).
- CHANGELOG `[Unreleased]` gains a single Fixed entry.
