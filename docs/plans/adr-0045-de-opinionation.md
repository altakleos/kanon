---
status: draft
slug: adr-0045-de-opinionation
date: 2026-05-01
design: "No new design surface. ADR-0045 ratifies the migration commit sequence and ordering of Phase A's deletions; the actual deletion mechanics live in distribution-boundary.md (per ADR-0043) and kernel-reference-interface.md (per ADR-0040). This ADR is sequencing + commitment ratification."
---

# Plan: Phase 0 — ADR-0045 de-opinionation transition

## Context

The seventh and final Phase 0 ADR. ADRs 0039–0044 ratified the substrate's runtime model, discovery interface, contract grammar, verification scope, distribution boundary, and self-conformance discipline. ADR-0045 closes Phase 0 by ratifying the **transition path** — the ordered sequence of commits that moves the kanon repo from kit-shape (today) to protocol-substrate-shape (post-Phase A).

Three coupled commitments:

1. **Phase 0.5 self-host hand-over comes BEFORE Phase A deletions.** The kanon repo's `.kanon/config.yaml` is rewritten to opt-in form via the publisher recipe BEFORE Phase A removes `defaults:`, `_detect.py`, kit-global `files:`, etc. Reverse order would break self-host between commits.

2. **Phase A deletions ordered to maintain self-host green at every commit.** Round-5 panel called this the load-bearing sequencing concern. The substrate-self-conformance discipline (ADR-0044) means failures between commits are P0/P1; ordering avoids them.

3. **No backward-compatibility shims for v0.3.x consumers.** Per ADR-0048's clean-break commitment: there are no current consumers; the kanon repo is its own first migration target; the `kanon migrate v0.3 → v0.4` script (per ADR-0043 design) handles this repo's transition and is deprecated-on-arrival.

Round-5 planner produced this sequencing as a roadmap; round-6 critic validated it; this ADR ratifies it as the canonical transition specification.

## Goal

Land a single self-contained PR that:

1. **Authors ADR-0045** ratifying the de-opinionation transition: the Phase 0.5 hand-over → Phase A deletions sequence, ordering rules, and clean-break commitment.
2. **No new spec, no new design.** The mechanism lives in ADR-0040's design (kernel-reference interface) and ADR-0043's design (distribution boundary + migration script outline). This ADR is sequencing-and-commitment.
3. **No source / aspect-manifest / protocol-prose / CI changes.** Phase A executes per the ratified sequence.

## Scope

### In scope

#### A. ADR-0045

`docs/decisions/0045-de-opinionation-transition.md`. Sections:

- **Context** — why a separate ADR for the transition; references to ADR-0048 (commitment), ADR-0040 (interface), ADR-0043 (distribution), ADR-0044 (self-conformance discipline).
- **Decision** — three numbered claims:
  1. Phase 0.5 (self-host hand-over) ships before Phase A deletions.
  2. Phase A deletions ship in a documented order; substrate-self-conformance gates each commit.
  3. No v0.3.x backward compatibility; clean break per ADR-0048.
- **The transition sequence** — concrete ordered list:
  - **Phase 0.5**: rewrite `.kanon/config.yaml` to opt-in form; copy `reference-default` recipe to `.kanon/recipes/`; commit. Self-host stays green.
  - **Phase A.1**: split distribution (substrate / reference / meta-alias `pyproject.toml` files) — commit. CI matrix updates accordingly.
  - **Phase A.2**: `_kit_root()` retirement; aspect path lookup goes through registry. Substrate-independence gate authored and runs (likely red on first try).
  - **Phase A.3**: kit-global `files:` field deleted; `.kanon/kit.md` migrates to an aspect or is deleted. `defaults:` field deleted.
  - **Phase A.4**: `_detect.py` deleted. Testing-aspect's `config-schema:` for runtime commands removed.
  - **Phase A.5**: Bare-name CLI sugar deprecated with shim (one-cycle deprecation).
  - **Phase A.6**: Resolution engine (`_resolutions.py`), dialect parser (`_dialects.py`), composition resolver (`_composition.py`) authored.
  - **Phase A.7**: `kanon resolve`, `kanon resolutions check`, `kanon resolutions explain`, `kanon contracts validate` CLI verbs authored.
  - **Phase A.8**: All four scaffolded `ci/check_*.py` files retired from `kanon-reference`'s scaffolded files; consumer-side equivalents remain in the kanon repo as authored realizations (per the protocol-substrate's "kit teaches; consumer realizes; agent binds" model).
  - **Phase A.9**: `kanon migrate v0.3 → v0.4` script lands; deprecated-on-arrival.
- **Alternatives Considered** — at least 4 (deletions before hand-over; informal ordering; backward-compat shims for v0.3.x; defer transition to v1.0).
- **Consequences** — what changes for Phase A's PR sequencing; for the substrate-independence gate's expected first-run-red status; for `kanon-substrate==1.0.0a1` shipping as a hard cut.
- **Config Impact** — `.kanon/config.yaml` v3 → v4 migration is the kanon repo's first lived event; downstream consumers (none today) would migrate via the script.
- **References** — ADR-0048 (commitment), ADR-0040 (interface), ADR-0043 (distribution + migration design), ADR-0044 (self-conformance gate), the de-opinionation manifesto.

Length target: ~180–220 lines.

#### B. Index updates

- `docs/decisions/README.md` — adds ADR-0045 row.

#### C. CHANGELOG entry

One paragraph under `## [Unreleased]` § Added — the seventh and final Phase 0 paragraph.

#### D. CHANGELOG closing note

After ADR-0045 lands, Phase 0 is complete. Add a brief one-line note in the CHANGELOG under `[Unreleased]` confirming Phase 0 closure: "All seven Phase 0 ADRs (0039–0045) are now ratified; Phase 0.5 self-host hand-over and Phase A implementation follow."

### Out of scope

- **All code changes.** Phase A executes the transition.
- **Phase 0.5 actual implementation** (rewriting `.kanon/config.yaml`). Phase 0.5 has its own plan after this ADR ships.
- **No new spec, no new design.** Mechanism lives in prior ADRs' designs.
- **`acme-` publisher migration guidance.** Phase B/C; `acme-` publishers don't exist yet.

## Approach

1. **ADR first.** Author ADR-0045 with the three normative claims and the concrete Phase 0.5 → Phase A sequence.
2. **Index + CHANGELOG.**
3. **Run gates locally.**
4. **Regenerate fidelity lock if needed (likely no-op since no spec or principle changes).**

## Acceptance criteria

### ADR

- [ ] AC-A1: `docs/decisions/0045-de-opinionation-transition.md` exists with `status: accepted`.
- [ ] AC-A2: ADR-0045 cites ADR-0048, ADR-0040, ADR-0043, ADR-0044, the de-opinionation manifesto.
- [ ] AC-A3: At least four Alternatives Considered.
- [ ] AC-A4: Concrete Phase 0.5 + 9-step Phase A sequence in the Decision section.

### Indexes + CHANGELOG

- [ ] AC-X1: `docs/decisions/README.md` updated with ADR-0045 row.
- [ ] AC-X2: `CHANGELOG.md` `[Unreleased] §Added` gains a paragraph naming ADR-0045.
- [ ] AC-X3: CHANGELOG `[Unreleased]` notes Phase 0 closure (all seven ADRs ratified).

### Cross-cutting

- [ ] AC-X4: `kanon verify .` → `status: ok`, zero warnings.
- [ ] AC-X5: `python ci/check_links.py` → ok.
- [ ] AC-X6: `python ci/check_foundations.py` → ok.
- [ ] AC-X7: `python ci/check_invariant_ids.py` → ok.
- [ ] AC-X8: No source / aspect-manifest / protocol-prose / CI / new-spec / new-design changes.

## Risks / concerns

- **Risk: the 9-step Phase A sequence may need amendment when Phase A starts.** Mitigation: ADR-0045's Decision specifies *ordering rules* (hand-over before deletions; self-conformance gates each commit) more strongly than specific step numbers. If Phase A finds the sequence needs reordering, the ordering rules survive; specific step-numbers are advisory.
- **Risk: ADR-0045 may seem like a plan, not a decision.** Mitigation: this ADR ratifies *clean-break + ordered-transition + hand-over-before-deletions* as commitments. The 9-step list is the canonical sequence; future contributors who skip the hand-over or reorder catastrophically violate the ADR.
- **Risk: spending all this ADR effort on a sequence whose code lives in Phase A.** Mitigation: the sequence is the most consequential single decision — getting it wrong breaks self-host between commits, which is P0/P1 per ADR-0044. Ratifying explicitly is cheap; not ratifying is expensive.

## Documentation impact

- **New files:** `docs/decisions/0045-de-opinionation-transition.md`.
- **Touched files:** `docs/decisions/README.md`, `CHANGELOG.md`, `.kanon/fidelity.lock` (if regenerated).
- **No source / aspect-manifest / protocol-prose / CI / new-spec / new-design changes.**
