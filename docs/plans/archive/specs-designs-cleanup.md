---
status: done
shipped-in: PR #51
slug: specs-designs-cleanup
date: 2026-05-01
design: "Follows ADR-0048 — bringing designs and specs into coherence with the protocol-substrate commitment ratified in Phase 0.4. No new design surface."
---

# Plan: Phase 0.4.5 — Specs and designs cleanup

## Context

Phase 0.4 (PR #50) brought the foundations layer into coherence with ADR-0048's protocol-substrate commitment. The next adjacent layer — design docs in `docs/design/` and spec docs in `docs/specs/` — has its own staleness:

- Specs realising the now-retired `P-tiers-insulate` need retirement.
- One spec (`template-bundle.md`) was the v0.1 template-bundle spec; its design counterpart (`kit-bundle.md`) was already retired in v0.2; the spec was left behind.
- One design (`aspect-model.md`) — the surviving aspect-model design — needs a "Status under ADR-0048" section noting the aspect primitive survives but the kit-shape framing is superseded.

## Scope (deliberately tight)

This plan handles **only unambiguous retirements + one design amendment**. Anything that requires a new ADR, a new INV, or substantive prose rewrite defers to the Phase 0 ADRs that drive those changes.

### In scope

#### Specs (frontmatter-only retirements)

| Spec | Action | Why |
|---|---|---|
| `docs/specs/tiers.md` | `status: accepted` → `status: superseded`, add `superseded-by: 0048` | Realises `P-tiers-insulate` (retired in PR #50); the tier model itself is gone under protocol-shape. |
| `docs/specs/tier-migration.md` | Same retirement | Same `P-tiers-insulate` realisation. |
| `docs/specs/template-bundle.md` | Same retirement | Its design counterpart `kit-bundle.md` was already retired in v0.2; the spec was left behind. ADR-0048's distribution-boundary commitment formally retires its substance. |

Bodies preserved per immutability discipline. Retirement is frontmatter-only.

#### Designs (one amendment)

| Design | Action | Why |
|---|---|---|
| `docs/design/aspect-model.md` | Append a `## Status under ADR-0048` section with predecessor commit SHA pointer | Aspect primitive survives ADR-0048; kit-shape framing in the doc does not. Same pattern applied to `P-self-hosted-bootstrap` in PR #50. |
| `docs/design/kit-bundle.md` | **No action** — already retired in v0.2 with `superseded-by: aspect-model.md`. | The chain is intact; ADR-0048 doesn't change kit-bundle's already-superseded status. |

#### Index updates

| File | Action |
|---|---|
| `docs/specs/README.md` | Verify Active vs Superseded split (or add it if missing); ensure the three retired specs surface under Superseded with ADR-0048 attribution. |
| `docs/design/README.md` | No action expected; kit-bundle was already shown as retired. Verify the index reads cleanly. |

### Out of scope (deferred to Phase 0 / Phase A)

- **All other spec amendments** — `cli.md`, `aspects.md`, `aspect-config.md`, `aspect-provides.md`, `project-aspects.md`, `verification-contract.md`, `testing.md`, `deps.md`, `preflight.md`, `scaffold-v2.md`, `protocols.md`, etc. These need amendments tied to Phase 0/A code changes and the ADRs that ratify them.
- **All other design amendments** — `scaffold-v2.md`, `preflight.md` will amend in Phase A when their underlying code changes.
- **New designs** — `resolutions-engine.md`, `dialect-grammar.md`, `kernel-reference-interface.md`, `verification-scope.md`, `distribution-boundary.md` ride along with their Phase 0 ADRs (0039–0045).
- **New INVs** — INV-11 in `verification-contract.md` (verifier panel proposed wording) defers to ADR-0041's plan.
- **No source / aspect-manifest / protocol-prose changes.**
- **No new ADR.** ADR-0048 already supersedes the kit-shape framing; these retirements are consequences, not new decisions.

## Approach

1. **Spec retirements first** (frontmatter-only edits to three specs). Each gets `status: superseded` + `superseded-by: 0048`. Bodies preserved.
2. **Design amendment** (append `## Status under ADR-0048` section to `aspect-model.md` with predecessor commit SHA pointer).
3. **README updates** if needed.
4. **Run gates locally** (`kanon verify .`, `python scripts/check_links.py`, `python scripts/check_foundations.py`, `python scripts/check_status_consistency.py`).
5. **Commit + push + PR.**

No CHANGELOG entry. Designs and specs in retired state are kit-author-internal cleanup; the substrate identity (CHANGELOG-worthy event) was the foundations rewrite in PR #50.

## Acceptance criteria

- [x] AC-S1: `docs/specs/tiers.md` carries `status: superseded`, `superseded-by: 0048`. Body unchanged.
- [x] AC-S2: `docs/specs/tier-migration.md` carries `status: superseded`, `superseded-by: 0048`. Body unchanged.
- [x] AC-S3: `docs/specs/template-bundle.md` carries `status: superseded`, `superseded-by: 0048`. Body unchanged.
- [x] AC-D1: `docs/design/aspect-model.md` carries an appended `## Status under ADR-0048` section explaining the survives/superseded split, with predecessor commit SHA reference.
- [x] AC-D2: `docs/design/kit-bundle.md` is unchanged (already retired correctly).
- [x] AC-X1: `kanon verify .` returns `status: ok` (one pre-existing fidelity warning unrelated is acceptable).
- [x] AC-X2: `python scripts/check_links.py` passes.
- [x] AC-X3: `python scripts/check_foundations.py` passes.
- [x] AC-X4: `python scripts/check_status_consistency.py` passes (or warns predictably; not a hard-fail check).
- [x] AC-X5: No source / spec body / aspect-manifest / protocol-prose / CI changes.
- [x] AC-X6: No CHANGELOG entry (kit-author internal cleanup).

## Risks / concerns

- **Risk: `template-bundle.md` retirement may be challenged** if some still-active spec links to it. Mitigation: `scripts/check_links.py` will catch broken inbound references; if the check fires, either fix the citing spec or hold the retirement.
- **Risk: `check_status_consistency.py` may flag the retirements as drift.** Acceptable; the soft check is informational and these are deliberate frontmatter changes.
- **Risk: appending to `aspect-model.md` body may be challenged on ADR-immutability grounds.** The current ADR-immutability gate applies to ADR bodies, not design docs. Per the same treatment we applied to `P-self-hosted-bootstrap` in PR #50, appending a `## Status under ADR-XXXX` section is the standard amendment pattern and does not violate immutability.

## Documentation impact

- **Touched files (frontmatter-only):** `docs/specs/tiers.md`, `docs/specs/tier-migration.md`, `docs/specs/template-bundle.md`.
- **Touched files (body amendment):** `docs/design/aspect-model.md` (one appended section).
- **Index updates if needed:** `docs/specs/README.md`, `docs/design/README.md`.
- **No CHANGELOG entry.**
- **No source / aspect-manifest / protocol-prose / CI changes.**
