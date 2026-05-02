---
status: draft
slug: adr-0044-substrate-self-conformance
date: 2026-05-01
design: "No new design surface — Phase A authors `scripts/check_substrate_independence.py` per ADR-0040's design doc; this ADR ratifies the discipline (the gate is part of substrate's permanent CI). The design lives in [`docs/design/kernel-reference-interface.md`](../../design/kernel-reference-interface.md)."
---

# Plan: Phase 0 — ADR-0044 substrate self-conformance discipline

## Context

The sixth Phase 0 ADR. ADR-0040 introduced the **independence invariant** as a single bullet inside the kernel/reference runtime interface decision: "the substrate's test suite must pass with `kanon-reference` uninstalled." Round-5 panel (architect, critic, code-reviewer, verifier) all converged on this as load-bearing — without it, the de-opinionation commitment is words on paper.

ADR-0044 elevates the independence invariant from a downstream consequence of ADR-0040 to a top-level **substrate self-conformance discipline** with its own ADR, its own spec, and its own permanent CI gate. The substrate's "kernel-as-product, reference-as-demonstration" identity is exactly what this discipline enforces in code paths.

This ADR is small in code-impact (the CI gate is Phase A; this PR is documentation) but large in normative weight (it makes substrate-independence a permanent commitment, not a Phase A milestone).

Three coupled commitments:

1. **Substrate-independence as permanent invariant.** `kanon-substrate`'s test suite passes with `kanon-reference` uninstalled. Forever. Future kernel work must preserve this.
2. **Self-host as primary correctness probe** (per the foundations rewrite). The kanon repo is its own first consumer; the substrate's correctness is measured against this repo's own state.
3. **The substrate's CI publishes self-conformance as a public signal.** Future `acme-` publishers can verify the substrate's independence claim by running the gate themselves.

## Goal

Land a single self-contained PR that:

1. **Authors ADR-0044** ratifying substrate self-conformance as a discipline (independence invariant + self-host probe + public-CI-signal).
2. **Authors `docs/specs/substrate-self-conformance.md`** as a new spec carrying invariants for substrate-independence, self-host-probe, and CI-gate visibility.
3. **No new design.** Phase A's gate algorithm lives in [`docs/design/kernel-reference-interface.md`](../../design/kernel-reference-interface.md) (ratified per ADR-0040); this ADR cites it.
4. **No source / aspect-manifest / protocol-prose / CI changes.** Phase A authors the actual `scripts/check_substrate_independence.py`; this PR is documentation only.

## Scope

### In scope

#### A. ADR-0044

`docs/decisions/0044-substrate-self-conformance.md`. Sections:

- **Context** — why elevate independence from ADR-0040 bullet to top-level ADR; references to round-5 panel convergence; the foundations rewrite's "self-hosting as falsification" framing.
- **Decision** — three numbered claims:
  1. Independence invariant: `kanon-substrate` tests pass with `kanon-reference` uninstalled — permanent, not Phase A milestone.
  2. Self-host probe: the kanon repo's CI runs `kanon verify .` against itself, including with reference aspects opted-in via the publisher recipe per ADR-0048's self-host commitment.
  3. CI-gate visibility: the substrate-independence gate's status is publicly readable; future `acme-` publishers can replicate the gate against their own bundles.
- **Alternatives Considered** — at least 4 (independence as ADR-0040 bullet only; independence as Phase A milestone only; substrate self-conformance via informal review; integrate into ADR-0042 verification scope).
- **Consequences** — what changes for Phase A's CI gate authoring; for self-host commit sequencing per Phase 0.5; for `acme-` publisher onboarding.
- **References** — ADR-0048, ADR-0040, ADR-0043, the new spec, the foundations rewrite's de-opinionation manifesto.

Length target: ~140–180 lines.

#### B. Spec — `docs/specs/substrate-self-conformance.md` (new)

Sections:

- Frontmatter with `realizes:` (`P-self-hosted-bootstrap`, `P-protocol-not-product`, `P-publisher-symmetry`).
- **Definition** — what substrate self-conformance IS (substrate-independence + self-host-probe + public-signal).
- **Invariants** with anchor IDs:
  - `INV-substrate-self-conformance-independence`: `kanon-substrate` tests pass with no `kanon-reference` installed and no `kanon.aspects` entry-points visible.
  - `INV-substrate-self-conformance-self-host-passes`: the kanon repo passes `kanon verify .` on every kernel-version-bump commit.
  - `INV-substrate-self-conformance-recipe-opt-in`: the kanon repo's `.kanon/config.yaml` opts into reference aspects via a publisher recipe with `provenance:` recording attribution; no kernel-side privilege.
  - `INV-substrate-self-conformance-gate-public`: the substrate-independence CI gate runs in a publicly-readable workflow; results are visible to anyone reading the substrate's repo.
  - `INV-substrate-self-conformance-replicable`: the gate's algorithm is documented sufficient that any publisher (including `acme-` authors) can replicate it against their own bundles.
- **Verification approach** — fixtures Phase A authors.

Length target: ~120–160 lines.

#### C. Index updates

- `docs/decisions/README.md` — adds ADR-0044 row.
- `docs/specs/README.md` — adds `substrate-self-conformance.md` row.

#### D. CHANGELOG entry

One paragraph under `## [Unreleased]` § Added summarizing ADR-0044's discipline elevation.

### Out of scope

- **The actual CI gate (`scripts/check_substrate_independence.py`).** Phase A authors per ADR-0040's design doc.
- **The kanon repo's `.kanon/config.yaml` rewrite to opt-in form.** Phase 0.5 (self-host hand-over).
- **De-opinionation transition** mechanics — ADR-0045.
- **Migration script** — Phase A.
- **`acme-` publisher conformance test framework** — Phase B/C.
- **No new design.** Phase A's gate algorithm lives in `docs/design/kernel-reference-interface.md` (per ADR-0040).

## Approach

1. **ADR first.** Author ADR-0044 with the three normative claims; cite ADR-0040 (the source of the independence invariant), ADR-0048 (self-host commitment), ADR-0043 (the distribution shape that makes independence testable).
2. **Spec second.** Author `docs/specs/substrate-self-conformance.md` with five invariant anchors.
3. **Indexes + CHANGELOG.**
4. **Run gates locally.**
5. **Regenerate fidelity lock.**

## Acceptance criteria

### ADR

- [ ] AC-A1: `docs/decisions/0044-substrate-self-conformance.md` exists with `status: accepted`.
- [ ] AC-A2: ADR-0044 cites ADR-0048, ADR-0040, ADR-0043, the new spec.
- [ ] AC-A3: At least four Alternatives Considered.

### Spec

- [ ] AC-S1: `docs/specs/substrate-self-conformance.md` exists with `status: accepted`, `realizes:`, `stressed_by:`, and at least five substrate-self-conformance invariant anchors.
- [ ] AC-S2: `fixtures_deferred: true` (Phase A).

### Indexes + CHANGELOG

- [ ] AC-X1: `docs/decisions/README.md` updated.
- [ ] AC-X2: `docs/specs/README.md` updated.
- [ ] AC-X3: `CHANGELOG.md` `[Unreleased] §Added` gains a paragraph.

### Cross-cutting

- [ ] AC-X4: `kanon verify .` → `status: ok`, zero warnings.
- [ ] AC-X5: `python scripts/check_links.py` → ok.
- [ ] AC-X6: `python scripts/check_foundations.py` → ok.
- [ ] AC-X7: `python scripts/check_invariant_ids.py` → ok.
- [ ] AC-X8: No source / aspect-manifest / protocol-prose / CI / new-design changes.

## Risks / concerns

- **Risk: ADR-0044 may seem redundant with ADR-0040's independence invariant bullet.** Mitigation: ADR-0040 introduced the invariant as a downstream consequence; ADR-0044 ratifies it as a top-level discipline with its own spec, INVs, and CI-gate visibility. Same content, different authority surface — the bullet was contingent on ADR-0040; the ADR makes it permanent and citable.
- **Risk: today's kernel does NOT pass independence.** Mitigation: ADR-0040 already names this honestly. ADR-0044 inherits the framing: this PR ratifies the *discipline*; Phase A makes it *true*. The substrate-independence gate's first run will likely fail; iteration to green is the deliverable.

## Documentation impact

- **New files:** `docs/decisions/0044-substrate-self-conformance.md`; `docs/specs/substrate-self-conformance.md`.
- **Touched files:** `docs/decisions/README.md`, `docs/specs/README.md`, `CHANGELOG.md`, `.kanon/fidelity.lock`.
- **No source / aspect-manifest / protocol-prose / CI / new-design changes.**
