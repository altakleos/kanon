---
status: draft
slug: adr-0043-distribution-cadence
date: 2026-05-01
design: "This plan delivers the design alongside the ADR (`docs/design/distribution-boundary.md`); no companion design exists yet because this PR creates it."
---

# Plan: Phase 0 — ADR-0043 distribution boundary + release cadence

## Context

The fifth Phase 0 ADR. ADR-0040 ratified entry-point discovery as the runtime interface; this ADR ratifies the **packaging mechanics** the substrate ships under: how `kanon-substrate` and `kanon-reference` split into separately-installable distributions, what version-pinning across the split looks like, what release cadence the substrate honours.

Three coupled commitments:

1. **Distribution boundary**: `kanon-substrate` (the kernel) ships separately from `kanon-reference` (the seven `kanon-` aspects as data). A `kanon-kit` meta-package alias provides the convenience-install path. Round-5 code-reviewer's preferred answer (rejected per-aspect wheels as "theatre"; rejected single-wheel as kit-shape vestige).

2. **Release cadence**: kernel ships daily-alpha permitted; reference ships weekly cadence; dialects ship quarterly minimum, annual default. A breaking dialect change is *never* a kernel release; it always cuts a new dialect spec. Round-5 planner: "the kit ships daily alpha. Under B-flavor with dialect grammar, is daily alpha still safe? A breaking dialect change every day would shred any future `acme-` author."

3. **Recipe artifact**: the path by which a consumer adopts a starter set (publisher-shipped target-tree YAML at `.kanon/recipes/<recipe-name>.yaml`). Round-5 code-reviewer's option-3 (recipes as inert YAML in target tree, not a kernel verb): publisher-shipped recipes preserve `P-protocol-not-product` (the kernel has no opinion about which recipe is right).

## Goal

Land a single self-contained PR that:

1. **Authors ADR-0043** ratifying distribution boundary, release cadence, and recipe artifact in one decision.
2. **Authors `docs/design/distribution-boundary.md`** as the companion design — concrete `pyproject.toml` shapes for substrate / reference / meta-alias, recipe YAML schema, cadence policy.
3. **Authors `docs/specs/release-cadence.md`** as a new spec carrying invariants for cadence and dialect-vs-kernel separation.
4. **No source / aspect-manifest / protocol-prose / CI changes.** Phase A implements the wheel split, recipe scaffolding, and cadence-CI checks.

## Scope

### In scope

#### A. ADR-0043

`docs/decisions/0043-distribution-boundary-and-cadence.md`. Sections:

- **Context** — three coupled commitments; references to ADR-0040 (entry-point interface) and ADR-0041 (dialect grammar — what cadence governs).
- **Decision** — three numbered claims:
  1. Distribution shape: `kanon-substrate` + `kanon-reference` + `kanon-kit` meta-alias.
  2. Cadence policy: kernel daily-alpha; reference weekly; dialect quarterly minimum / annual default; breaking-dialect changes are never kernel releases.
  3. Recipe artifact: publisher-shipped target-tree YAML; consumer copies to `.kanon/recipes/`; substrate has no kernel verb.
- **Alternatives Considered** — at least 5 (single wheel kit-shape; per-aspect wheels; vendor reference into substrate; daily-alpha across all surfaces; recipes as kernel feature).
- **Consequences** — what changes for `pyproject.toml` (Phase A); release workflows (Phase A); the `kanon migrate v0.3 → v0.4` script (Phase A); release-cadence CI gate (Phase A).
- **Config Impact** — none for consumer config; `pyproject.toml` shape ratified for the three packages.
- **References** — ADR-0048, ADR-0040, ADR-0041, the new design and spec.

Length target: ~180–220 lines.

#### B. Design — `docs/design/distribution-boundary.md`

Concrete mechanism. Sections:

- **Context** — what ADR-0043 ratifies.
- **`pyproject.toml` shapes** — concrete examples for `kanon-substrate`, `kanon-reference`, `kanon-kit` meta-alias.
- **Recipe YAML schema** — concrete shape; worked example for `kanon-reference`'s `reference-default` recipe.
- **Cadence policy** — kernel daily-alpha rules; reference weekly cadence rules; dialect quarterly cadence rules; breaking-change-not-in-kernel rule.
- **Migration script** — `kanon migrate v0.3 → v0.4` outline (Phase A authors).
- **Release-workflow CI gate** — what the cadence-discipline CI gate checks.
- **Phase A implementation footprint**.

Length target: ~200–280 lines.

#### C. Spec — `docs/specs/release-cadence.md` (new)

New spec. Sections:

- Frontmatter with `realizes:` (`P-publisher-symmetry`, `P-protocol-not-product`).
- **Definition** — what cadence IS; what dialect-cadence-vs-kernel-cadence separation means.
- **Invariants** (five release-cadence anchors):
  - `INV-release-cadence-kernel-daily-alpha-permitted`: `kanon-substrate` may ship daily alpha releases under semver.
  - `INV-release-cadence-reference-weekly`: `kanon-reference` ships at weekly cadence (substrate-author discretion); reference releases never include kernel-level changes.
  - `INV-release-cadence-dialect-quarterly-minimum`: a new dialect (`kanon-dialect: YYYY-MM-DD`) ships at quarterly minimum, annual default; date-stamping per ADR-0041.
  - `INV-release-cadence-breaking-not-in-kernel`: a breaking dialect change is never a kernel release; it always ships as a dialect supersession.
  - `INV-release-cadence-substrate-honours-n-minus-1`: at any time, `kanon-substrate` honours at least the current dialect (N) and the previous dialect (N-1); manifests pinning N-2 receive a deprecation warning.
- **Verification approach** — fixtures Phase A authors.

Length target: ~120–180 lines.

#### D. Index updates

- `docs/decisions/README.md` — adds ADR-0043 row.
- `docs/design/README.md` — adds `distribution-boundary.md` row.
- `docs/specs/README.md` — adds `release-cadence.md` row.

#### E. CHANGELOG entry

One paragraph under `## [Unreleased]` § Added summarizing ADR-0043's three commitments.

### Out of scope

- **All code changes.** Phase A authors the actual `pyproject.toml` for `kanon-substrate`, `kanon-reference`, `kanon-kit`; the migration script; the release-workflow CI gate.
- **Substrate self-conformance** — ADR-0044.
- **De-opinionation transition** — ADR-0045.
- **Specific recipe contents** — `kanon-reference`'s `reference-default` recipe is a publisher artifact; this PR specifies the shape, not the contents.
- **acme- publisher cadence guidance** — Phase B/C; `acme-` publishers set their own cadence.

## Approach

1. **ADR first.**
2. **Spec second.**
3. **Design third.**
4. **Indexes + CHANGELOG.**
5. **Run gates locally.**
6. **Regenerate fidelity lock.**

## Acceptance criteria

### ADR

- [ ] AC-A1: `docs/decisions/0043-distribution-boundary-and-cadence.md` exists with `status: accepted` and the six required sections.
- [ ] AC-A2: ADR-0043 cites ADR-0048, ADR-0040, ADR-0041.
- [ ] AC-A3: At least five Alternatives Considered.

### Spec

- [ ] AC-S1: `docs/specs/release-cadence.md` exists with `status: accepted`, `realizes:`, and at least five release-cadence invariant anchors.
- [ ] AC-S2: `fixtures_deferred: true` (Phase A authors fixtures).

### Design

- [ ] AC-D1: `docs/design/distribution-boundary.md` contains worked `pyproject.toml` examples for substrate, reference, and meta-alias.
- [ ] AC-D2: Recipe YAML schema with worked example.
- [ ] AC-D3: Cadence policy fully specified.

### Indexes + CHANGELOG

- [ ] AC-X1: `docs/decisions/README.md` updated.
- [ ] AC-X2: `docs/design/README.md` updated.
- [ ] AC-X3: `docs/specs/README.md` updated.
- [ ] AC-X4: `CHANGELOG.md` `[Unreleased] §Added` gains a paragraph.

### Cross-cutting

- [ ] AC-X5: `kanon verify .` → `status: ok`, zero warnings.
- [ ] AC-X6: `python ci/check_links.py` → ok.
- [ ] AC-X7: `python ci/check_foundations.py` → ok.
- [ ] AC-X8: `python ci/check_invariant_ids.py` → ok.
- [ ] AC-X9: No source / aspect-manifest / protocol-prose / CI changes.

## Risks / concerns

- **Risk: distribution boundary may overlap with ADR-0040.** Mitigation: ADR-0040 is the *runtime interface* (how the kernel discovers); ADR-0043 is the *packaging mechanics* (how the kernel ships). Clean separation.
- **Risk: cadence policy is opinionated.** Mitigation: invariants are minimal (5); future ADRs can refine if real-world signal demands.
- **Risk: recipe schema may need to evolve.** Mitigation: schema lives in `docs/design/distribution-boundary.md`; future ADRs supersede.

## Documentation impact

- **New files:** `docs/decisions/0043-distribution-boundary-and-cadence.md`; `docs/design/distribution-boundary.md`; `docs/specs/release-cadence.md`.
- **Touched files:** `docs/decisions/README.md`, `docs/design/README.md`, `docs/specs/README.md`, `CHANGELOG.md`, `.kanon/fidelity.lock` (regenerated).
- **No source / aspect-manifest / protocol-prose / CI changes.**
