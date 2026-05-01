---
status: draft
slug: adr-0042-verification-scope
date: 2026-05-01
design: "No new design surface. ADR-0042 ratifies the public claim wording for `kanon verify` exit-0 building on INV-11 (already added in PR #53). The verification mechanism is unchanged; this ADR is normative scope-of-claim."
---

# Plan: Phase 0 — ADR-0042 verification scope-of-exit-zero

## Context

The fourth Phase 0 ADR. INV-11 was added to `docs/specs/verification-contract.md` in PR #53 (alongside ADR-0039) and disclosed the structural exit-zero scope boundary at the spec level. ADR-0042 broadens the same claim into the public-facing protocol commitment: what `kanon verify` exit-0 promises to consumers and `acme-` publishers, and — equally importantly — what it does NOT promise.

This ADR is **normative scope-of-claim**, not new mechanism. INV-11 already lives in the verification-contract spec; ADR-0042 ratifies the claim's *public surface* (the wording the substrate's CLI help text, README, and `acme-` publisher onboarding documentation will use) and elevates it to a protocol-substrate commitment publishers can rely on.

It is the smallest of the Phase 0 ADRs by code-impact (zero implementation; documentation only) and is also the most consequential one for consumer expectations. Round-5 verifier identified the disproportionate weight: "the strongest single claim `kanon verify` can promise" needs explicit ratification because consumers will read exit-0 as a correctness endorsement unless the substrate explicitly says otherwise.

## Goal

Land a single self-contained PR that:

1. **Authors ADR-0042** ratifying the public scope-of-claim for `kanon verify` exit-0; codifies the wording the substrate uses across CLI help, README, and onboarding docs.
2. **Amends `docs/specs/verification-contract.md`** to point at ADR-0042 from INV-11 (cross-reference; no INV body change).
3. **No new spec, no new design.** The mechanism lives in the existing verification-contract spec; this ADR is scope-of-claim ratification.
4. **No source / aspect-manifest / protocol-prose / CI changes.** Phase A (when CLI help text gains the wording) is downstream.

## Scope

### In scope

#### A. ADR-0042

`docs/decisions/0042-verification-scope-of-exit-zero.md`. Sections:

- **Context** — INV-11 already lives in verification-contract.md; why a separate ADR rather than amending INV-11; the public-facing claim distinction.
- **Decision** — three numbered claims:
  1. The exit-zero claim verbatim (what `kanon verify` exit-0 means and does NOT mean).
  2. Cross-publisher symmetry (`kanon-`, `project-`, `acme-` aspects verify identically; no warranty exemption by namespace).
  3. The wording is canonical across surfaces (CLI help text, README, onboarding docs, error messages); future substrate releases honour it.
- **Alternatives Considered** — at least 4 (don't ratify publicly; ratify in vision.md instead; ratify per-aspect-spec; defer to publisher contracts).
- **Consequences** — what changes for `kanon verify`'s `--help` text (Phase A), README (Phase A or earlier), `acme-publisher` onboarding (Phase B/C); the public commitment substrate honours.
- **References** — INV-11 in verification-contract.md, ADR-0039, ADR-0041, ADR-0048.

Length target: ~120–160 lines.

#### B. Spec amendment — `docs/specs/verification-contract.md`

INV-11's body is unchanged. Add a cross-reference paragraph at the end of the spec (or alongside INV-11) noting that ADR-0042 ratifies the public claim wording.

This is the smallest possible spec amendment: no INV change, just a citation. The fidelity-locked SHA may bump.

#### C. Index updates

- `docs/decisions/README.md` — adds ADR-0042 row.
- `docs/specs/README.md` — no change (verification-contract.md was already noted as having INV-11 added in v0.4 per ADR-0039; ADR-0042 is the public-surface ratification of the same INV).

#### D. CHANGELOG entry

One paragraph under `## [Unreleased]` § Added (alongside ADR-0039 / ADR-0040 / ADR-0041 paragraphs) summarizing ADR-0042's normative claim ratification.

### Out of scope

- **CLI help text changes.** Phase A — when `kanon verify --help` is rewritten to use the canonical wording.
- **README changes.** README rewrite is a separate cohesive PR.
- **`acme-publisher` onboarding documentation.** Phase B/C territory.
- **New verification mechanism.** No new spec, no new design, no new code. Pure scope-of-claim ratification.
- **Distribution boundary** — ADR-0043.
- **Substrate self-conformance** — ADR-0044.
- **De-opinionation transition** — ADR-0045.

## Approach

1. **ADR first.** Author ADR-0042 with the canonical wording the substrate uses.
2. **Verification-contract amendment.** Add cross-reference to ADR-0042 in `verification-contract.md`.
3. **Index + CHANGELOG.**
4. **Run gates locally.**
5. **Regenerate fidelity lock** if `verification-contract.md` SHA bumps.

## Acceptance criteria

### ADR

- [ ] AC-A1: `docs/decisions/0042-verification-scope-of-exit-zero.md` exists with `status: accepted` and the six required ADR sections.
- [ ] AC-A2: ADR-0042 cites ADR-0048, ADR-0039, ADR-0041, the verification-contract spec, and INV-11.
- [ ] AC-A3: At least four Alternatives Considered.
- [ ] AC-A4: Decision section includes the canonical exit-zero wording verbatim — short, citable, copy-pasteable.

### Spec amendment

- [ ] AC-S1: `docs/specs/verification-contract.md` gains a cross-reference paragraph pointing at ADR-0042; INV-11's body unchanged.

### Indexes + CHANGELOG

- [ ] AC-X1: `docs/decisions/README.md` updated with ADR-0042 row.
- [ ] AC-X2: `CHANGELOG.md` `[Unreleased] §Added` gains a paragraph naming ADR-0042.

### Cross-cutting

- [ ] AC-X3: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X4: `python ci/check_links.py` passes.
- [ ] AC-X5: `python ci/check_foundations.py` passes, zero warnings.
- [ ] AC-X6: `python ci/check_invariant_ids.py` passes, zero warnings.
- [ ] AC-X7: No source / aspect-manifest / protocol-prose / CI / spec-body changes (only verification-contract.md amendment is a cross-reference, no INV body changes; only NEW spec content is none).

## Risks / concerns

- **Risk: ADR-0042 may seem redundant with INV-11.** Mitigation: INV-11 is the *spec invariant* (what the kernel enforces); ADR-0042 is the *public claim wording* (what consumers and publishers can cite). Same content, different surface. The ADR's value is making the wording stable across substrate releases — INV-11 lives in a spec the substrate could quietly amend; ADR-0042 makes the canonical wording an immutable public commitment.
- **Risk: the canonical wording may need to change as the substrate evolves.** Mitigation: ADR-immutability discipline applies; if a future substrate version genuinely needs different wording, a superseding ADR is the path. The wording is intentionally minimal and structural so future evolution is unlikely.
- **Risk: ADR-0042 underspecifies what "an aspect's contracts" means relative to ADR-0041's realization-shape grammar.** Mitigation: ADR-0042 cites ADR-0041 explicitly; the canonical wording uses "the contracts of the aspects the consumer has enabled" without dictating shape.

## Documentation impact

- **New files:** `docs/decisions/0042-verification-scope-of-exit-zero.md`.
- **Touched files:** `docs/specs/verification-contract.md` (cross-reference paragraph), `docs/decisions/README.md`, `CHANGELOG.md`, `.kanon/fidelity.lock` (regenerated if SHA bumps).
- **No source / aspect-manifest / protocol-prose / CI / new-spec / new-design changes.**
