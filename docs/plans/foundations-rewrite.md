---
status: draft
slug: foundations-rewrite
date: 2026-05-01
design: "This plan IS the design for Phase 0.4. The protocol commitment was settled across rounds 1–5 of panel review (see conversation log); this plan executes the foundations-layer consequences. No companion design doc."
---

# Plan: Phase 0.4 — Foundations rewrite for protocol commitment

## Context

Across five rounds of panel review and explicit lead ratification, kanon committed to becoming a **protocol substrate** for prose-as-code engineering discipline (de-opinionated; reference aspects de-installable). The kit-shape was a transitional prototype against the project's DNA. The foundations layer (vision, principles, personas) is now materially out of date and must be brought into coherence with the commitment before Phase 0 ADRs land.

Two structural commitments emerged in ratification:

1. **The substrate publishes its principles as stable protocol commitments** — versioned with the dialect, citable by `acme-` publishers, immutable post-acceptance.
2. **Principles split into two tiers**: public protocol commitments (six) and kit-author internal stances (two).

This plan executes the foundations rewrite as a single cohesive change. Phase 0 ADRs (0039–0045) follow in subsequent plans.

## Goal

Deliver a foundations layer that:

- Reads coherently to a fresh contributor as describing a protocol substrate, not a kit
- Makes the public-vs-internal principle split explicit and machine-checkable
- Replaces tier vocabulary with depth/recipe/aspect vocabulary throughout
- Adds the missing artifacts (de-opinionation manifesto, `acme-publisher` persona, three new principles)
- Retires what the protocol commitment supersedes
- Lands one superseding ADR ratifying the commitment so future readers understand the inflection point

## Scope

### In scope

#### A. New superseding ADR

- **ADR-0048: kanon as protocol substrate.** Ratifies the protocol commitment, the de-opinionation choice, the publish-principles-as-protocol-commitments stance, and the public/internal tier split. Supersedes ADR-0012 (aspect model — kit-shape) in part. Cites the conversation log as design evidence.

#### B. Vision rewrite

- **Replace `docs/foundations/vision.md` in place.** The old body remains as a `## Historical Note` section at the bottom (per ADR-immutability discipline applied to vision). New body covers:
  - Opening: kanon is a protocol substrate, not a kit
  - Three defining properties: prose-as-code, de-opinionated, self-hosting (revised meanings)
  - Section: **Public protocol commitments** — listing the six public principles by ID with one-line statements
  - Section: **Substrate guarantees** — what `kanon-substrate` provides regardless of which aspects a consumer enables
  - Section: **Non-goals** (refreshed) — what the protocol explicitly will not do
  - Section: **Why prose-as-code is the bet** — the founding axiom, traced to the lead's framing
  - Section: **Self-hosting under vision-led design** — epistemological role, not dogfooding
  - Section: **Amendment trail** — preserves the existing trail; adds the protocol commitment entry
  - Section: **Historical Note** — preserves the v0.1 kit-shape vision body verbatim with link to the predecessor commit SHA

#### C. Principles — tiering + amendments + new + retirements

##### Tier the existing 6 principles via `tier:` frontmatter

| Principle | Tier | Action |
|---|---|---|
| `P-prose-is-code` | `public-protocol` | Add tier; elevate to first principle (README order); body unchanged |
| `P-specs-are-source` | `public-protocol` | Add tier; amend body — add §"Resolutions are derived" clause covering protocol-mode runtime bindings |
| `P-tiers-insulate` | (retire) | Status → `superseded`; superseded-by ADR-0048; body preserved |
| `P-self-hosted-bootstrap` | `kit-author-internal` | Add tier; amend body — peer-consumer framing (kanon repo opts in via publisher recipe, no privileged status); self-hosting becomes the falsification probe |
| `P-cross-link-dont-duplicate` | `kit-author-internal` | Add tier; body unchanged |
| `P-verification-co-authored` | `public-protocol` | Add tier; amend body lightly — resolutions become a third co-authoritative source |

##### Author 3 new principles

| New principle | Tier | Statement |
|---|---|---|
| `P-protocol-not-product` | `public-protocol` | The kit ships a contract grammar and replay substrate; reference aspects are demonstrations, not the product. Bans privileging `kanon-` aspects in kernel code. |
| `P-publisher-symmetry` | `public-protocol` | The substrate treats kit-shipped, project-defined, and third-party aspects identically at every code path. Asymmetries must be justified or refactored. |
| `P-runtime-non-interception` | `public-protocol` | The substrate MUST NOT acquire a runtime component that intercepts or validates LLM-agent behavior. Prose gates are enforced by agent compliance; no daemon, hook, or session supervisor compensates for non-compliant agents. (Promoted from vision Non-Goal #2.) |

##### Update `docs/foundations/principles/README.md`

- Index reorganized by tier (public-protocol section first, kit-author-internal second)
- Add a "Public protocol commitments" preamble explaining the dialect-citation discipline
- Update kit-author-scope language: public-tier principles ARE part of the substrate's published spec; kit-author-internal principles are not

#### D. Personas — amend, new, retire

| Persona | Action |
|---|---|
| `solo-engineer` | Status → `superseded`; superseded-by `solo-with-agents`; body preserved with note explaining tier vocabulary is gone |
| `solo-with-agents` | Amend: replace tier vocabulary with depth/recipe/aspect; remove `multi-agent-coordination` deferred-spec references that don't fit protocol shape; add "and may consume `acme-` aspects" framing |
| `platform-team` | Status → `superseded`; rationale: audience explicitly deferred under vision-led commitment; body preserved |
| `onboarding-agent` | Amend: replace `tier-3` vocabulary with `substrate-with-recipe`; update boot chain reading order (vision.md is now the first foundations doc to read); remove deferred-roadmap reference |
| `acme-publisher` (NEW) | Author: a third-party publisher authoring a contract bundle. The Tuesday-afternoon SRE writing `acme-fintech-compliance`. Stresses dimensions: dialect grammar conformance, capability namespace collision, recipe authorship, conformance-test affordances. |

##### Update `docs/foundations/personas/README.md`

- Index reflects retirements + new persona
- Add a "Active vs Superseded" section header

#### E. New manifesto

- **`docs/foundations/de-opinionation.md`** — a manifesto-style document codifying the lead's framing. Not an ADR (the ADR ratifies; the manifesto explains). Not a principle (principles are normative stance; this is strategy commitment). Sections:
  - "Prose is the new source" — the founding bet
  - "The kit was a prototype against our DNA" — what kanon stopped being
  - "What de-opinionation means" — the audience-de-opinionation vs. protocol-de-opinionation distinction (analyst's catch)
  - "What the substrate refuses" — the negative scope list (3 normative refusals from the document-specialist's Markdown/Plan 9/Scheme synthesis)
  - "Self-hosting as falsification" — epistemological framing
  - Cites the conversation log as design evidence

#### F. Cross-cutting docs touch

- **Update `docs/foundations/README.md`** if it exists (tbd from worktree state) to list de-opinionation manifesto alongside principles + personas
- **No spec changes** — those land in subsequent Phase 0 ADR plans (0039–0045)
- **No source changes** — Phase A territory
- **No protocol changes** — the principles drive future protocol changes; this PR doesn't touch `.kanon/protocols/`

### Out of scope (explicitly deferred)

- Phase 0 ADRs (0039 contract-resolution, 0040 kernel/reference interface, 0041 realization-shape+grammar, 0042 verification scope, 0043 distribution+cadence, 0044 self-conformance, 0045 de-opinionation transition) — separate plans
- Phase 0.5 self-host hand-over (`.kanon/config.yaml` rewrite) — separate plan
- Phase A implementation (`_resolutions.py`, dialect parser, `kanon contracts validate`, etc.) — separate plans
- Migration script (`kanon migrate v0.3→v0.4`) — Phase A territory
- Source code, test code, CI script changes
- Aspect manifest changes
- Protocol prose under `.kanon/protocols/` or `src/kanon/kit/aspects/*/protocols/`
- README.md changes (the kit's top-level README also needs a rewrite, but that's a separate cohesive change)

## Approach

Sequencing within Phase 0.4:

1. **ADR-0048 first.** Ratifies the commitment; gives every other change in this PR something to cite.
2. **Vision rewrite.** Cites ADR-0048; lists public-tier principles by ID (forward references resolved by step 4).
3. **De-opinionation manifesto.** Cites vision + ADR-0048.
4. **Tier existing principles + author new principles + amend principles.** Each amended principle gains a `## Historical Note` section with the predecessor SHA.
5. **Retire P-tiers-insulate.** Frontmatter status change; body preserved; superseded-by ADR-0048.
6. **Update principles README** with tier reorganization.
7. **Personas.** Amend the two surviving; retire the two; author `acme-publisher`.
8. **Update personas README.**
9. **Run gates locally.** `kanon verify .`, `python ci/check_links.py`, `python ci/check_foundations.py`.

Order matters because the principles README depends on principle frontmatter being current; vision references principles by ID.

## Acceptance criteria

### Vision

- [ ] AC-V1: `vision.md` opens with "kanon is a portable, self-hosting protocol substrate for prose-as-code engineering discipline."
- [ ] AC-V2: Vision contains a **Public protocol commitments** section listing exactly the six public principles by ID with one-line statements.
- [ ] AC-V3: Vision retires tier vocabulary throughout; uses depth/aspect/recipe/dialect/publisher consistently.
- [ ] AC-V4: Vision contains an **Amendment trail** preserving existing entries (ADR-0013, ADR-0015) and adding ADR-0048.
- [ ] AC-V5: Vision contains a **Historical Note** preserving the v0.1 kit-shape vision body verbatim with predecessor commit SHA.

### Principles

- [ ] AC-P1: Every existing principle file gains a `tier: public-protocol | kit-author-internal` frontmatter field.
- [ ] AC-P2: Three new principle files exist: `P-protocol-not-product.md`, `P-publisher-symmetry.md`, `P-runtime-non-interception.md`. All `tier: public-protocol`. All carry `status: accepted`.
- [ ] AC-P3: `P-tiers-insulate.md` carries `status: superseded` + `superseded-by: 0048`; body preserved verbatim.
- [ ] AC-P4: `P-specs-are-source.md`, `P-self-hosted-bootstrap.md`, `P-verification-co-authored.md` each carry a `## Historical Note` section preserving their pre-amendment body with predecessor commit SHA.
- [ ] AC-P5: `docs/foundations/principles/README.md` index reorganized: 6 public-protocol entries first, 2 kit-author-internal second, 1 superseded section. Preamble explains dialect-citation discipline.

### Personas

- [ ] AC-Per1: `solo-with-agents.md` and `onboarding-agent.md` each carry an `## Amendments` section with the protocol-shape vocabulary refresh.
- [ ] AC-Per2: `solo-engineer.md` and `platform-team.md` carry `status: superseded` + brief rationale; bodies preserved.
- [ ] AC-Per3: `acme-publisher.md` exists with `status: accepted`, follows the existing persona template (one-sentence summary, Context, Goals, What stresses the kit, What does NOT stress, Success).
- [ ] AC-Per4: `docs/foundations/personas/README.md` index updated with active/superseded split.

### Manifesto

- [ ] AC-M1: `docs/foundations/de-opinionation.md` exists with the six sections specified above.
- [ ] AC-M2: Manifesto cites vision.md and ADR-0048; is cited from vision.md.

### ADR

- [ ] AC-A1: `docs/decisions/0048-kanon-as-protocol-substrate.md` exists with `status: accepted`, follows ADR template, contains: Context, Decision, Alternatives Considered, Consequences (including the public/internal principle tiering and the supersession of ADR-0012 in part).
- [ ] AC-A2: `docs/decisions/README.md` index updated with ADR-0048.

### Cross-cutting

- [ ] AC-X1: `kanon verify .` returns `status: ok` (one pre-existing fidelity warning unrelated is acceptable).
- [ ] AC-X2: `python ci/check_links.py` passes.
- [ ] AC-X3: `python ci/check_foundations.py` passes.
- [ ] AC-X4: No source / spec / aspect-manifest / protocol-prose changes.
- [ ] AC-X5: CHANGELOG.md gains an `## [Unreleased]` entry summarizing the foundations rewrite (this IS user-visible — substrate identity changes).
- [ ] AC-X6: Doc length: vision ≤ 300 lines; manifesto ≤ 200 lines; each new principle ≤ 100 lines; new persona ≤ 100 lines.

## Risks / concerns

- **Risk: principle body amendments could be challenged on ADR-immutability grounds.** Mitigation: ADR-0048 explicitly ratifies the amendments as the moment the public-tier principles cross over into stable-commitment status. Future amendments are dialect changes; this one is the inflection point. State this explicitly in ADR-0048's Consequences.
- **Risk: retiring `solo-engineer` and `platform-team` personas without replacement could be read as scope-shrinkage.** Mitigation: the manifesto's "What de-opinionation means" section names this honestly — audience is explicitly vision-led-deferred. Future plans may resurrect either persona under protocol-mode framing.
- **Risk: vision.md's Historical Note section could rot — links break, predecessor SHA becomes meaningless without git context.** Mitigation: link is to a content-addressed commit SHA, which doesn't rot in git. Note that any future kanon migration tool must preserve the link.
- **Risk: doc length budget could blow.** Mitigation: caps in AC-X6. If pressure exceeds, the manifesto absorbs first (it's strategy, not normative); principles next; vision's Historical Note last (preserve verbatim is non-negotiable).

## Documentation impact

- **New files**: `docs/decisions/0048-kanon-as-protocol-substrate.md`; `docs/foundations/de-opinionation.md`; `docs/foundations/principles/P-protocol-not-product.md`; `docs/foundations/principles/P-publisher-symmetry.md`; `docs/foundations/principles/P-runtime-non-interception.md`; `docs/foundations/personas/acme-publisher.md`.
- **Touched files**: `docs/foundations/vision.md`; all 6 existing `docs/foundations/principles/P-*.md`; `docs/foundations/principles/README.md`; 4 existing `docs/foundations/personas/*.md`; `docs/foundations/personas/README.md`; `docs/decisions/README.md`; `CHANGELOG.md`.
- **No spec / source / ADR-immutability-violation / aspect-manifest / protocol-prose changes.**
- **CHANGELOG**: yes, this is user-visible (substrate identity); one-paragraph entry under `## [Unreleased]`.
