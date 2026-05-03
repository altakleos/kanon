---
status: draft
slug: adr-0041-realization-shape
date: 2026-05-01
design: "This plan delivers the design alongside the ADR (`docs/design/dialect-grammar.md`); no companion design exists yet because this PR creates it."
---

# Plan: Phase 0 — ADR-0041 realization-shape, dialect grammar, and composition algebra

## Context

The third Phase 0 ADR. ADR-0039 ratified the runtime-binding model (resolutions); ADR-0040 ratified the discovery interface (entry-points). ADR-0041 ratifies the **contract grammar** itself — the shape of what publishers ship.

Three coupled commitments live in this ADR:

1. **Realization-shape schema**: each contract declares per-contract frontmatter specifying allowed verbs, evidence kinds, stage keys. The kernel validates resolutions at replay against this schema. Round-5 panel: 5/6 agents converged on this as the strongest single addition.

2. **Dialect grammar versioning**: aspect manifests pin a `kanon-dialect: 2026-05-01` (date-stamped artifact); the substrate honours at least N-1 dialects with a deprecation horizon. Round-3 architect: prevents kit-shape grammar fork at year-5 scale. Round-5 document-specialist: JSON Schema dialects model is the closest precedent.

3. **Composition algebra**: contracts targeting the same execution surface declare `surface:` + `before/after:` ordering; `replaces:` provides substitution. Topo-sorted at replay; cycles fail loudly.

Three commitments in one ADR is unusual but they're tightly coupled — realization-shape is meaningless without dialect-versioning (which makes shape evolution safe), and composition algebra is meaningless without realization-shape (composition needs typed surface/before/after declarations). Round-5 planner explicitly merged these three into a single ADR.

## Goal

Land a single self-contained PR that:

1. **Authors ADR-0041** ratifying realization-shape, dialect grammar, and composition algebra as one coherent decision.
2. **Authors `docs/design/dialect-grammar.md`** as the companion design — concrete schema for `realization-shape:`, dialect frontmatter shape, composition resolution algorithm.
3. **Amends `docs/specs/aspects.md`** (append-only) with INVs for shape conformance, dialect-pin, and composition order. Optionally splits a new spec `docs/specs/dialect-grammar.md` if the new surface is large enough to warrant standalone treatment — decision in this plan.
4. **No source / aspect-manifest / protocol-prose / CI changes.** Phase A implementation comes in subsequent plans.

## Scope decision: one spec or two?

Round-5 architect proposed extracting `docs/specs/dialect-grammar.md` as a standalone spec. Round-5 planner kept it inside `aspects.md`. Choosing **standalone spec** for two reasons:

- Dialect grammar is *the* publisher-facing contract; it deserves its own INV anchor surface for `acme-` publishers to cite.
- Realization-shape is grammar; composition algebra is grammar; both belong with the dialect-grammar spec, not with the aspect spec.

Decision: **new spec `docs/specs/dialect-grammar.md`**. Aspects.md gains a one-paragraph cross-reference; no additional INVs in aspects.md.

## Scope

### In scope

#### A. ADR-0041

`docs/decisions/0041-realization-shape-dialect-grammar.md`. Sections:

- **Context** — three coupled commitments; why one ADR; references to ADR-0039 (resolutions) and ADR-0040 (discovery).
- **Decision** — three numbered ratifications: realization-shape per contract; dialect-version pin; composition algebra (surface + before/after + replaces).
- **Alternatives Considered** — at least 5 (one big amorphous schema; per-aspect schemas instead of per-contract; no dialect versioning; semver instead of date-stamping; runtime composition order vs. publisher-declared).
- **Consequences** — what changes for `_resolutions.py` (validates shape at replay); for `_manifest.py` (refuses unknown dialects); for `kanon contracts validate` (the new CLI verb); for `acme-` publishers (the public contract they depend on).
- **Config Impact** — `.kanon/config.yaml` v3 → v4 finalized (the publisher-id, recipe-provenance, dialect-pin sketched in ADR-0039 is now fully ratified).
- **References** — ADR-0048 (substrate commitment), ADR-0039 (resolutions), ADR-0040 (discovery), ADR-0026 (capability registry), the new design doc and spec.

Length target: ~180–240 lines.

#### B. Design doc — `docs/design/dialect-grammar.md`

Concrete mechanism. Sections:

- **Context** — what ADR-0041 ratifies; what this design specifies.
- **Realization-shape schema** — the per-contract frontmatter shape (allowed verbs, evidence-kind enums, stage keys, additional-properties policy). YAML example for a `preflight.commit` contract; one for a `release-gate` contract.
- **Dialect frontmatter shape** — the `kanon-dialect:` field grammar (date-stamped: `YYYY-MM-DD`); how publishers declare it; how the substrate honours N-1 dialects.
- **Composition resolution algorithm** — topo-sort over contracts targeting the same surface, with `before/after:` edges; cycle detection with explicit error message; `replaces:` substitution before topo-sort.
- **Validator algorithm** — `kanon contracts validate <bundle-path>` walk: parse manifest, check dialect-pin against substrate-known dialects, validate every contract against its declared realization-shape, run composition pre-flight (ensure no cycles).
- **Phase A implementation footprint**.

Length target: ~200–300 lines.

#### C. Spec — `docs/specs/dialect-grammar.md` (new)

New spec. Sections:

- Frontmatter `realizes:` (`P-prose-is-code`, `P-publisher-symmetry`, `P-protocol-not-product`, `P-specs-are-source`).
- **Definition** — what a dialect IS; what realization-shape IS; what composition IS.
- **Invariants** (six dialect-grammar anchors):
  - `INV-dialect-grammar-pin-required`: every aspect manifest pins `kanon-dialect:`; absence is a load-time error.
  - `INV-dialect-grammar-version-format`: dialect-version is `YYYY-MM-DD`; the substrate honours at least N-1 dialects with deprecation warnings.
  - `INV-dialect-grammar-realization-shape-required`: every contract declares `realization-shape:` frontmatter; absence rejects the contract.
  - `INV-dialect-grammar-shape-validates-resolutions`: kernel validates every resolution entry against its contract's realization-shape; mismatches surface as `code: shape-violation`.
  - `INV-dialect-grammar-composition-acyclic`: composition graph (`surface:` + `before/after:`) MUST be acyclic; cycles are load-time errors with explicit cycle-path reporting.
  - `INV-dialect-grammar-replaces-substitution`: `replaces: <contract-id>@<version-range>` declarations resolve before composition; replacing-contract inherits the replaced-contract's `provides:` capability.
- **Verification approach** — fixtures and tests Phase A authors.

Length target: ~150–220 lines.

#### D. Spec amendment — `docs/specs/aspects.md`

One-paragraph cross-reference to `dialect-grammar.md`. Append-only; no INV body changes.

#### E. Index updates

- `docs/decisions/README.md` — adds ADR-0041 row.
- `docs/design/README.md` — adds `dialect-grammar.md` row.
- `docs/specs/README.md` — adds `dialect-grammar.md` spec row.

#### F. CHANGELOG entry

One paragraph under `## [Unreleased]` § Added (alongside ADR-0039 and ADR-0040 paragraphs) summarizing ADR-0041's three commitments.

### Out of scope

- **All code changes.** Phase A authors the dialect parser, shape validator, composition resolver, and `kanon contracts validate` CLI verb.
- **Verification scope-of-exit-zero broader wording** — ADR-0042.
- **Distribution boundary** — ADR-0043.
- **Substrate self-conformance** — ADR-0044.
- **De-opinionation transition** — ADR-0045.
- **Defining specific realization-shapes for the seven `kanon-` reference aspects** — those are publisher artifacts, ratified when `kanon-aspects` is split out (Phase A scope).
- **`acme-` publisher onboarding documentation** — that's part of Phase B once dialect grammar is real.

## Approach

1. **ADR first.** Author ADR-0041 with three coherent decisions; cite ADR-0039, ADR-0040, ADR-0048.
2. **Spec second.** Author `docs/specs/dialect-grammar.md` with INV anchors.
3. **Design third.** Author `docs/design/dialect-grammar.md` with concrete schemas and algorithm pseudocode.
4. **Aspects.md amendment.** One paragraph cross-referencing new spec.
5. **Indexes + CHANGELOG.**
6. **Run gates locally.**
7. **Regenerate fidelity lock.**

## Acceptance criteria

### ADR-0041

- [ ] AC-A1: `docs/decisions/0041-realization-shape-dialect-grammar.md` exists with `status: accepted` and the six required ADR sections.
- [ ] AC-A2: ADR-0041 cites ADR-0048, ADR-0039, ADR-0040, ADR-0026.
- [ ] AC-A3: At least five Alternatives Considered.

### Spec

- [ ] AC-S1: `docs/specs/dialect-grammar.md` exists with `status: accepted`, `realizes:` and `stressed_by:` lists, and at least six dialect-grammar invariant anchors.
- [ ] AC-S2: `fixtures_deferred: true` in frontmatter (Phase A authors fixtures).
- [ ] AC-S3: `docs/specs/aspects.md` gains a cross-reference paragraph; existing INVs unchanged.

### Design

- [ ] AC-D1: `docs/design/dialect-grammar.md` contains worked YAML examples of `realization-shape:` for at least two contract types.
- [ ] AC-D2: Composition resolution algorithm specified in pseudocode.
- [ ] AC-D3: `kanon contracts validate` walk specified in pseudocode.

### Indexes + CHANGELOG

- [ ] AC-X1: `docs/decisions/README.md` updated.
- [ ] AC-X2: `docs/design/README.md` updated.
- [ ] AC-X3: `docs/specs/README.md` updated.
- [ ] AC-X4: `CHANGELOG.md` `[Unreleased] §Added` gains a paragraph.

### Cross-cutting

- [ ] AC-X5: `kanon verify .` → `status: ok`, zero warnings.
- [ ] AC-X6: `python scripts/check_links.py` → ok.
- [ ] AC-X7: `python scripts/check_foundations.py` → ok.
- [ ] AC-X8: `python scripts/check_invariant_ids.py` → ok.
- [ ] AC-X9: No source / aspect-manifest / protocol-prose / CI changes.

## Risks / concerns

- **Risk: three coupled commitments in one ADR may overwhelm review.** Mitigation: ADR's Decision section is three numbered claims; each Alternative Considered targets one claim; reviewers can engage per-claim.
- **Risk: shape schema may be too permissive or too strict.** Mitigation: Phase A's `kanon contracts validate` test suite is the falsification surface; if the shape rejects valid contracts, Phase A reveals it and we amend in ADR follow-up. If too permissive, kit-author audits surface drift.
- **Risk: dialect-versioning collides with semver of `kanon-core` itself.** Mitigation: dialects are date-stamped (`YYYY-MM-DD`), substrate is semver. Different vocabularies, different artifacts. ADR-0041 explains the distinction.
- **Risk: composition algebra too restrictive (forbidding cycles makes some legitimate flows impossible).** Mitigation: cycles in `before/after:` graphs are universally bugs; if a real use case emerges, it's the seed of a future ADR. Today's substrate has zero composition cycles.

## Documentation impact

- **New files:** `docs/decisions/0041-realization-shape-dialect-grammar.md`; `docs/design/dialect-grammar.md`; `docs/specs/dialect-grammar.md`.
- **Touched files:** `docs/specs/aspects.md`, `docs/decisions/README.md`, `docs/design/README.md`, `docs/specs/README.md`, `CHANGELOG.md`, `.kanon/fidelity.lock` (regenerated).
- **No source / aspect-manifest / protocol-prose / CI changes.**
