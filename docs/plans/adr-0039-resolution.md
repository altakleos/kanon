---
status: draft
slug: adr-0039-resolution
date: 2026-05-01
design: "This plan delivers the design alongside the ADR (`docs/design/resolutions-engine.md`); no companion design exists yet because this PR creates it."
---

# Plan: Phase 0 — ADR-0039 contract-resolution model

## Context

The first ADR of Phase 0. Defines the substrate's runtime-binding model: prose contracts (defined per-aspect) get resolved by a consumer's LLM agent into `.kanon/resolutions.yaml`, which the kernel replays mechanically. This is the load-bearing decision the rest of Phase 0 builds on. Without ADR-0039, Phase 0 ADRs 0040, 0040.5, 0041, 0042 have nothing to cite.

## Goal

Land a single self-contained PR that:

1. **Authors ADR-0039** ratifying the contract-resolution model: artifact format, quadruple-pinning, replay-vs-resolve split, evidence-grounded provenance, stale-detection, machine-only-owned ownership.
2. **Authors `docs/design/resolutions-engine.md`** as the companion design doc — concrete YAML schema, replay algorithm, stale-detection algorithm, the resolver's contract with the kernel.
3. **Authors `docs/specs/resolutions.md`** as a new spec carrying invariants the substrate enforces.
4. **No source / aspect-manifest / protocol-prose / CI changes.** Phase A implementation comes in subsequent plans.

## Scope

### In scope

#### A. ADR-0039

`docs/decisions/0039-contract-resolution-model.md`. Sections:

- **Context** — why the substrate needs a runtime-binding model; reference to ADR-0048's protocol-substrate commitment; the prose-contract / agent-resolution / kernel-replay split.
- **Decision** — the single normative claim: contracts are prose; resolutions are machine-only-owned YAML; the resolver runs only on developer machines; the kernel replays cached resolutions mechanically. Quadruple-pin: `contract-version`, `contract-content-SHA`, `resolver-model`, `evidence-SHA`.
- **Alternatives Considered** — five alternatives at minimum (config-driven runtime as in v0.3; live-LLM in CI; subprocess-isolated resolver; resolutions hand-written by user; resolutions auto-resolved at every CI run).
- **Consequences** — what changes for kernel modules, what new spec invariants, what new failure modes, what changes for `kanon verify`.
- **Config Impact** — `.kanon/config.yaml` schema bumps v3→v4 (publisher-id, recipe provenance, dialect-version pin); `.kanon/resolutions.yaml` is new.
- **References** — ADR-0048, ADR-0028, ADR-0029, the new design doc and spec.

Length target: ~120–180 lines.

#### B. Design doc — `docs/design/resolutions-engine.md`

Concrete mechanism. Sections:

- **Context** — what ADR-0039 ratifies; what this design specifies (the *how*).
- **Resolution artifact format** — `.kanon/resolutions.yaml` schema, with a worked example. Top-level keys (`schema-version`, `aspects`, per-contract entries with `realized_by`, `evidence`, `last_resolved`, `last_resolved_against`).
- **Replay algorithm** — kernel reads resolutions, validates pins, executes invocations sequentially, reports findings.
- **Stale-detection algorithm** — SHA computation per evidence file; mismatch surfaces as `code: sha-mismatch` finding.
- **Resolver contract** — the dev-machine resolver inputs (contract prose, repo state) and outputs (resolution entries with provenance). The kernel doesn't ship a resolver; the agent IS the resolver.
- **Hand-edit refusal** — the kernel detects hand-edits by checksum and refuses replay.
- **Phase A implementation footprint** — `_resolutions.py` (~280 LOC), `_validators` extensions, CLI verb hookups (`kanon resolve`, `kanon resolutions explain`).

Length target: ~150–250 lines.

#### C. Spec — `docs/specs/resolutions.md`

New spec carrying invariants. Sections:

- Frontmatter with `realizes:` (`P-prose-is-code`, `P-specs-are-source`, `P-verification-co-authored`, `P-protocol-not-product`) and `stressed_by:` (the `acme-publisher` and `solo-with-agents` personas).
- **Definition** — what a resolution is, structurally.
- **Invariants** with `INV-resolutions-*` anchors:
  - `INV-resolutions-machine-only-owned`: hand-edits to `.kanon/resolutions.yaml` are forbidden; the kernel detects via checksum and refuses replay.
  - `INV-resolutions-quadruple-pin`: every entry pins contract-version + contract-content-SHA + resolver-model + evidence-SHAs.
  - `INV-resolutions-evidence-grounded`: every entry cites at least one evidence file path; cited paths must exist; cited SHAs must match current SHAs (or stale-detection fires).
  - `INV-resolutions-replay-deterministic`: two replays of the same resolutions.yaml against the same repo state produce byte-equal output.
  - `INV-resolutions-resolver-not-in-ci`: the resolver runs only on developer machines; CI replays cached resolutions but never resolves.
  - `INV-resolutions-stale-fails`: stale evidence (SHA mismatch) is a `kanon verify` finding, not silent.
- **Verification approach** — fixtures and tests that will prove each INV in Phase A.

Length target: ~120–200 lines.

#### D. Verification-contract spec amendment

`docs/specs/verification-contract.md` gains a new INV (call it `INV-11`) about exit-zero scope: *"`kanon verify` exit-0 means conformance to enabled aspects only — not a correctness or quality endorsement."* The wording is the verifier panel's R5 output.

This INV addition lives in this PR (not deferred to ADR-0041) because it's a downstream consequence of ADR-0039's "kernel replays mechanically" decision. ADR-0041 (verification scope) ratifies the broader claim wording; ADR-0039's invariant is narrowly about resolution-replay structural conformance.

Length impact: ~10 lines added.

#### E. Index updates

- `docs/decisions/README.md` — adds ADR-0039 row.
- `docs/specs/README.md` — adds `resolutions.md` row.
- `docs/design/README.md` — adds `resolutions-engine.md` row.

#### F. CHANGELOG entry

One paragraph under `## [Unreleased]` summarizing ADR-0039's substrate-level commitment. User-visible (the substrate's runtime-binding model is part of the public protocol surface).

### Out of scope

- **All code changes.** Phase A implements `_resolutions.py`, the replay engine, `kanon resolve`, `kanon resolutions explain`. This PR is documentation only.
- **Composition algebra (`surface:`, `before/after:`, `replaces:`).** ADR-0040 territory.
- **Realization-shape schema.** ADR-0040 territory.
- **Dialect grammar versioning.** ADR-0040 territory.
- **Kernel/reference runtime interface.** ADR-0040 territory (the panel-load-bearing one; renumbered from the planning placeholder "0040.5" to the next integer slot).
- **Verification scope-of-exit-zero broader wording.** ADR-0041 territory; this PR adds the INV but ADR-0041 ratifies the public-facing claim.
- **Distribution boundary.** ADR-0042 territory.
- **Self-conformance.** ADR-0043 territory.
- **De-opinionation transition.** ADR-0044 territory.
- **Recipe definition.** Recipe shape ships in ADR-0042 (distribution) since recipes are publisher artifacts. ADR-0039 mentions recipes only as the path by which a consumer obtains a starter resolution set.
- **Migration script (`kanon migrate v0.3→v0.4`).** Phase A territory.
- **`.kanon/config.yaml` v4 schema.** Sketched in ADR-0039 Config Impact; full ratification in ADR-0040 alongside dialect grammar.

## Approach

1. **ADR first.** Author ADR-0039 with the ratification-grade Decision; cite ADR-0048 throughout.
2. **Spec second.** Author `docs/specs/resolutions.md` with INV anchors that the design will satisfy.
3. **Design third.** Author `docs/design/resolutions-engine.md` with the worked YAML example and replay algorithm.
4. **Verification-contract amendment.** Add `INV-11` and a one-paragraph rationale citing ADR-0039.
5. **Index + CHANGELOG.**
6. **Run gates locally.** `kanon verify .`, `python ci/check_links.py`, `python ci/check_foundations.py`, `python ci/check_invariant_ids.py`, `python ci/check_verified_by.py`.
7. **Regenerate `.kanon/fidelity.lock`** if the verification-contract spec's frontmatter changes.

## Acceptance criteria

### ADR-0039

- [ ] AC-A1: `docs/decisions/0039-contract-resolution-model.md` exists with `status: accepted` and the six required ADR sections.
- [ ] AC-A2: ADR-0039 cites ADR-0048 as the parent commitment, ADR-0028 for namespace integration, ADR-0029 for the verification-contract carve-out it operates within.
- [ ] AC-A3: At least five Alternatives Considered, each with clear rejection rationale.

### Design

- [ ] AC-D1: `docs/design/resolutions-engine.md` contains a worked YAML example showing all top-level keys plus a per-contract entry with `realized_by`, `evidence`, `last_resolved`, `last_resolved_against`.
- [ ] AC-D2: Replay algorithm specified at sufficient detail that Phase A can implement it without further design work.
- [ ] AC-D3: Stale-detection algorithm specified concretely (SHA computation, mismatch handling).

### Spec

- [ ] AC-S1: `docs/specs/resolutions.md` exists with `status: accepted`, frontmatter `realizes:` and `stressed_by:` lists, and at least six `INV-resolutions-*` anchors.
- [ ] AC-S2: Each INV has a falsifiable statement (a Phase A test could plausibly verify it).
- [ ] AC-S3: `verified-by:` mappings deferred to Phase A (when fixtures exist); `fixtures_deferred: true` declared in frontmatter to satisfy `ci/check_verified_by.py`.

### Verification-contract amendment

- [ ] AC-V1: New `INV-11` added to `docs/specs/verification-contract.md` with the exit-zero scope-boundary wording. Predecessor body preserved by appending only — no in-place edits to existing INVs.
- [ ] AC-V2: `ci/check_invariant_ids.py` passes.

### Indexes + CHANGELOG

- [ ] AC-X1: `docs/decisions/README.md` updated with ADR-0039 row.
- [ ] AC-X2: `docs/specs/README.md` updated with `resolutions.md` row.
- [ ] AC-X3: `docs/design/README.md` updated with `resolutions-engine.md` row.
- [ ] AC-X4: `CHANGELOG.md` `## [Unreleased]` gains a paragraph naming ADR-0039.

### Cross-cutting

- [ ] AC-X5: `kanon verify .` returns `status: ok` (zero warnings; regenerate fidelity lock if frontmatter changes bump SHAs).
- [ ] AC-X6: `python ci/check_links.py` passes.
- [ ] AC-X7: `python ci/check_foundations.py` passes.
- [ ] AC-X8: `python ci/check_invariant_ids.py` passes.
- [ ] AC-X9: `python ci/check_verified_by.py` passes (with `fixtures_deferred: true` declared).
- [ ] AC-X10: No source / aspect-manifest / protocol-prose / CI changes.

## Risks / concerns

- **Risk: ADR-0039 may overlap with ADR-0040 (composition).** Mitigation: scope-discipline in this plan keeps composition out; ADR-0040 cites this ADR for the resolution-shape primitives it composes over.
- **Risk: spec INVs may be hard to falsify before code exists.** Mitigation: `fixtures_deferred: true` is the standard mechanism; INVs are stated abstractly enough to be testable when Phase A code lands. INVs that cannot be falsified at all (e.g., "the resolver IS an LLM") are dropped.
- **Risk: adding INV-11 to verification-contract.md before ADR-0041 lands could pre-empt that ADR.** Mitigation: INV-11 is the structural-resolution-replay invariant; ADR-0041 will ratify the broader claim wording. The INV is added now because ADR-0039's resolution-replay decision needs an immediate verification-contract anchor.
- **Risk: the worked YAML example in the design doc may diverge from Phase A implementation.** Mitigation: example is intentionally minimal; `schema-version: 1` is reserved; Phase A can extend without breaking the design's commitments.
- **Risk: large PR (4 new files + 4 edits).** Mitigation: documentation only; reviewer can check cohesion in one pass; no code-review burden.

## Documentation impact

- **New files:** `docs/decisions/0039-contract-resolution-model.md`; `docs/design/resolutions-engine.md`; `docs/specs/resolutions.md`.
- **Touched files:** `docs/specs/verification-contract.md` (INV-11 added), `docs/decisions/README.md`, `docs/specs/README.md`, `docs/design/README.md`, `CHANGELOG.md`.
- **Possibly touched:** `.kanon/fidelity.lock` (if verification-contract.md frontmatter changes bump its SHA).
- **No source / aspect-manifest / protocol-prose / CI changes.**
