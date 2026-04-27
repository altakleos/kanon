---
feature: fidelity-and-immutability
serves: docs/specs/verification-contract.md
design: "Follows ADR-0028 (project-aspects), ADR-0029 (verify carve-out — drafted in this plan's Track 0)"
status: in-progress
date: 2026-04-27
---
# Plan: v0.3 — fidelity track + ADR-immutability + (optional) principle override

## Context

Round-2 panel surfaced two findings that gate v0.3 work:

1. **`docs/specs/verification-contract.md` INV-9 ("does not execute code") forecloses every behavioural-verification proposal** without a deliberate spec amendment. Without the carve-out, the EH-V1 / EH-V2 / EH-V5 track from Round-1 cannot ship — they would be in spec-conflict from day 1.
2. **Post-acceptance ADR mutation is real-incidence in kanon's own history** (≥4 unannotated body modifications: `0cbcbdd`, `021d178`, `45cd42d` touching three ADRs). The discipline named in `docs/development-process.md:82` ("ADRs are immutable once accepted") has zero mechanical enforcement.

Three tracks land. Track 1 is gated on Track 0 landing. Tracks 2 and 3 are independent.

- **Track 0** — Verification-contract carve-out. Spec amendment + ADR-0029. Gates everything in Track 1.
- **Track 1** — `kanon-fidelity` aspect, Tier 1 only. Lexical fixture engine + one exemplar fixture (`worktree-lifecycle`).
- **Track 2** — ADR-immutability gate. Kit-internal CI script + protocol prose at `kanon-sdd` depth 3.
- **Track 3 (gated on maintainer Q2 framing)** — principle override mechanism. Either Option (b) primitives if "authoritative," or docs-only update if "exemplary."

Tier-2 (workstation `kanon transcripts capture`) and Tier-3 (paid nightly e2e) are explicitly out of scope; documented as deferred below.

## Tasks

### Track 0 — Verification-contract carve-out (gates Track 1)

- [x] T0-1: Amend `docs/specs/verification-contract.md` to add INV-10 (carve-out), bound to `kanon-fidelity` aspect at depth ≥1 → `docs/specs/verification-contract.md`
- [x] T0-2: Land ADR-0029 ratifying T0-1 → `docs/decisions/0029-verification-fidelity-replay-carveout.md` (depends: T0-1)
- [x] T0-3: Update ADR index → `docs/decisions/README.md` (depends: T0-2)

### Track 1 — `kanon-fidelity` aspect, Tier 1 only (depends: T0-1, T0-2)

- [x] T1-1: Spec defining the aspect's invariants (fixture schema, actor-turn extractor, assertion families) → `docs/specs/fidelity.md`
- [x] T1-2: ADR-lite for the aspect's depth dial (0, 1) and `provides: behavioural-verification` capability per ADR-0026 → `docs/decisions/0031-fidelity-aspect.md` (depends: T1-1) — *landed as a full ADR rather than lite (matching the precedent of every other aspect-introduction ADR — ADR-0014/0017/0021/0022/0023). Slot bumped from 0030 → 0031 during rebase: PR-34 `fix: review-followups batch 1` shipped the recovery-model ADR as 0030 between Track 0 and Track 1.*
- [x] T1-3: Aspect manifest with `depth-0: {}` and `depth-1: {files, protocols, sections}` → `src/kanon/kit/aspects/kanon-fidelity/manifest.yaml` (depends: T1-2)
- [x] T1-4: Engine — `parse_fixture`, `extract_actor_text`, `evaluate_fixture`, `discover_fixtures` (~250 LOC) → `src/kanon/_fidelity.py` (depends: T1-3)
- [x] T1-5: `_verify.py` integration — `check_fidelity_assertions` called only when an aspect declaring `behavioural-verification` is enabled, honours INV-10 bounds → `src/kanon/_verify.py` + `src/kanon/cli.py` (depends: T1-4)
- [x] T1-6: Exemplar fixture pair — schema instance + captured exemplar → `.kanon/fidelity/worktree-lifecycle.md`, `.kanon/fidelity/worktree-lifecycle.dogfood.md` (depends: T1-5)
- [x] T1-7: Tests — 35 tests covering every spec invariant, including 2 deliberate-bad-dogfood tests against the exemplar → `tests/test_fidelity.py` (depends: T1-4)
- [x] T1-8: AGENTS.md section under `kanon-fidelity/body` marker for depth-1 → `src/kanon/kit/aspects/kanon-fidelity/agents-md/depth-1.md` (depends: T1-3)
- [x] T1-9: Promote spec to `status: accepted` once T1-7 passes → `docs/specs/fidelity.md` (depends: T1-7)

### Track 2 — ADR-immutability gate (parallel to Track 1)

- [x] T2-1: Full ADR-0032 for the immutability rule, including `Allow-ADR-edit: NNNN — <reason>` trailer escape hatch from sensei. Cites Round-2 Verifier evidence (≥4 violations in kanon's own history) → `docs/decisions/0032-adr-immutability-gate.md`
- [x] T2-2: Port `ci/check_adr_immutability.py` from sensei. Strip sensei-specific path constants. Add tests for the trailer parser → `ci/check_adr_immutability.py`, `tests/ci/test_check_adr_immutability.py` (depends: T2-1) — *19 tests pass; gate surfaces all 4 documented historical violations when run against root..main; PR mode against `origin/main` is clean.*
- [x] T2-3: Wire into `.github/workflows/verify.yml`. **Kit-internal only** — do NOT list under any aspect's `depth-N.files` → `.github/workflows/verify.yml` (depends: T2-2) — *checkout step bumped to `fetch-depth: 0` so PR mode against `origin/<base_ref>` works.*
- [x] T2-4: Author protocol prose listing enforcement options (CI gate, pre-commit hook, manual review) at `kanon-sdd` depth 3 → `src/kanon/kit/aspects/kanon-sdd/protocols/adr-immutability.md` (depends: T2-1)
- [x] T2-5: Update `docs/development-process.md` § ADRs to mention the trailer (depends: T2-1) — *kit + repo copies updated together; byte-equality preserved.*

### Track 3 — Principle override mechanism (CLOSED — superseded by `principles-clarification` plan)

**Closed without shipping.** The maintainer corrected the framing both round-1 and round-2 panels operated under: kanon's own kit-author `P-*.md` files **do not propagate to consumers**. The kit-sdd aspect at depth 3 scaffolds only `docs/foundations/principles/README.md` (an empty starter index), never the kit's own principle files. There is therefore nothing for a consumer to override — the proposed override mechanism (Option b) and the alternative "exemplary" reframe were both addressing a problem consumers don't have.

Replacement plan: [`docs/plans/principles-clarification.md`](principles-clarification.md) ships a one-paragraph clarification to the kit-shipped principles README (consumer-facing) plus a parallel one-line note to kanon's own repo copy (kit-author-facing). No spec, no ADR, no validator extension; no new aspect. AC4 is now satisfied by that plan landing rather than by anything in this track.

- [~] T3-1: Spec for `kanon:`/`project:` principle-id namespace — *deferred indefinitely; not needed*. Original target: `docs/specs/principle-override.md`.
- [~] T3-2..T3-5: ADR / validator extension / docs / tests — *all deferred indefinitely*; same reason.

## Acceptance Criteria

- [ ] AC1: Track 0 — `docs/specs/verification-contract.md` carries INV-10 (fidelity carve-out), bounded to `kanon-fidelity` enabled at depth ≥1; ADR-0029 status `accepted (lite)`; ADR index updated.
- [ ] AC2: Track 1 — kanon's own repo enables `kanon-fidelity:1`; `kanon verify .` returns `ok`; one fixture demonstrably catches the worktree-audit-sentence failure mode described in commit `b9524aa9` (deliberate-bad transcript fails the assertion).
- [ ] AC3: Track 2 — kanon's own CI hard-fails on a synthetic post-acceptance ADR body mutation; passes when the same commit carries an `Allow-ADR-edit:` trailer; consumer-facing protocol describes the rule but does not ship a default-on script.
- [~] AC4: Track 3 — superseded by [`docs/plans/principles-clarification.md`](principles-clarification.md). The maintainer's framing correction (kit principles do not propagate to consumers) made the originally-specced override mechanism unnecessary; the docs-clarification plan ships the only deliverable that actually pays rent.
- [ ] AC5: `kanon verify .` passes with no warnings on the kanon repo itself.
- [ ] AC6: `pytest`, `ruff check src/ tests/ ci/`, `mypy src/kanon` all pass.
- [ ] AC7: `python ci/check_kit_consistency.py` returns `status: ok`.
- [ ] AC8: All new INVs (INV-10 in Track 0, plus Track 1's spec INVs) have `invariant_coverage` mappings (or explicit `fixtures_deferred:` justification).

## Documentation Impact

- `CHANGELOG.md` `[Unreleased]` — three new sections (verification carve-out, fidelity aspect, immutability gate). Plus principle-override note iff Track 3 lands.
- `README.md` — aspect table gains `kanon-fidelity` row.
- `docs/foundations/vision.md` § Success Criteria — note v0.3 adds fidelity aspect under `experimental` stability.

## Out of Scope (deferred)

- **Tier 2** (workstation capture via `kanon transcripts capture`): defer to v0.4. Requires a separate ADR for the capture-as-evidence-artifact pattern.
- **Tier 3** (paid nightly e2e against real LLM): defer indefinitely. Document the recipe in a future Tier-3 protocol prose; do not ship in kanon itself.
- Persona expansion beyond current 4.
- Sensei's full 21-principle library (only the ≤2 transferable technical principles are panel-recommended; out of scope here).
- Sensei's release-audit-log gate (separate release-ladder track from Round-1 synthesis).
