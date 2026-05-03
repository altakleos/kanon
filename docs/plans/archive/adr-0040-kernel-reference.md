---
status: done
shipped-in: PR #54
slug: adr-0040-kernel-reference
date: 2026-05-01
design: "This plan delivers the design alongside the ADR (`docs/design/kernel-reference-interface.md`); no companion design exists yet because this PR creates it."
---

# Plan: Phase 0 — ADR-0040 kernel/reference runtime interface

## Context

The second ADR of Phase 0. The most urgent in the round-5 panel review: three agents (architect, critic, code-reviewer) independently named the kernel/reference runtime interface as **critical and unspecified**. Without this ADR, the substrate's "de-installable reference aspects" claim is words on paper — the kernel currently has no mechanism to discover aspects from a separately-installed package.

Today's `_kit_root()` at [`src/kanon/_manifest.py:127`](../../../kernel/_manifest.py) is referenced 10+ times across `_manifest.py` and `_scaffold.py`; every reference embeds the assumption that the kit ships exactly one of itself. Under the protocol-substrate commitment, the kernel (`kanon-core`) and reference aspects (`kanon-aspects`) ship as separate distributions. The kernel must discover reference aspects (and future `acme-` aspects) without privileging any.

ADR-0040 ratifies the **discovery mechanism**: Python entry-points (`importlib.metadata.entry_points(group="kanon.aspects")`). Plus the publisher-symmetric registry semantics, and the `kanon-core`-must-pass-tests-without-`kanon-aspects` invariant.

## Goal

Land a single self-contained PR that:

1. **Authors ADR-0040** ratifying the kernel/reference runtime interface: entry-point discovery group `kanon.aspects`, publisher-id resolution, the no-kit-global-files commitment, and the substrate-self-conformance test invariant.
2. **Authors `docs/design/kernel-reference-interface.md`** as the companion design doc — concrete entry-point shape, registry composition algorithm, the `kanon-core`-without-`kanon-aspects` test design.
3. **Amends `docs/specs/aspects.md` and `docs/specs/project-aspects.md`** to reference the new entry-point discovery (small, frontmatter + 1-2 paragraph additions; specs survive but gain protocol-substrate clauses).
4. **No source / aspect-manifest / protocol-prose / CI changes.** Phase A implementation comes in subsequent plans.

## Scope

### In scope

#### A. ADR-0040

`docs/decisions/0040-kernel-reference-runtime-interface.md`. Sections:

- **Context** — why the substrate needs a runtime discovery mechanism; the kit-shape `_kit_root()` problem; the publisher-symmetry requirement; the need to pass tests with `kanon-aspects` uninstalled.
- **Decision** — Python entry-points group `kanon.aspects` is the discovery mechanism. Publishers register entries via their package's `pyproject.toml`. The substrate's `_load_aspect_registry` unions: (a) entry-point-discovered publishers, (b) consumer-side `.kanon/aspects/project-*/` per ADR-0028, (c) optionally project-overlay (test fixtures). No publisher is privileged at any code path.
- **Alternatives Considered** — at least 5 (filesystem-walk-only; environment-variable path overlay; namespace-package discovery; kanon-core vendoring kanon-aspects; kanon-core hardcoding "the seven kanon- aspects").
- **Consequences** — what changes for `_kit_root()` (deleted), kit-global `files:` field (deleted), `_load_top_manifest` (becomes per-publisher), `_load_aspect_registry` (tri-source union), and the substrate's CI gate (must build kernel without reference and run full test suite).
- **Config Impact** — `pyproject.toml` shape for `kanon-core`, `kanon-aspects`, future `acme-X` (each declares its publisher namespace + aspect list under `[project.entry-points."kanon.aspects"]`).
- **References** — ADR-0048, ADR-0028, ADR-0026, ADR-0039, the new design doc.

Length target: ~140–180 lines.

#### B. Design doc — `docs/design/kernel-reference-interface.md`

Concrete mechanism. Sections:

- **Context** — what ADR-0040 ratifies; what this design specifies.
- **Entry-point group structure** — `[project.entry-points."kanon.aspects"]` shape; one entry per aspect; resolved at substrate-startup.
- **Publisher registry composition algorithm** — `_load_aspect_registry()` v2 algorithm (entry-points + project-aspects + optional overlay), keyed by publisher id, with namespace-collision detection.
- **The independence invariant** — `kanon-core`'s test suite must pass with no `kanon-aspects` installed. CI gate algorithm: install kernel only, run pytest, assert green.
- **`_kit_root()` retirement** — every call site walked: what replaces it (publisher path lookup via registry), where the publisher path comes from (entry-point's distribution path).
- **Phase A implementation footprint** — `_manifest.py` changes (~120 LOC; replace `_kit_root` with publisher-keyed lookups), new `pyproject.toml` for the eventual `kanon-aspects` package (~30 LOC), CI gate addition (~30 LOC), test extensions (~80 LOC).

Length target: ~150–250 lines.

#### C. Spec amendments

- **`docs/specs/aspects.md`**: amend to reference the entry-point discovery as the canonical kit-shipped publisher mechanism (1-paragraph addition; preserves all existing INVs; cites ADR-0040 as the ratifying decision).
- **`docs/specs/project-aspects.md`**: amend to clarify how project-aspects compose alongside entry-point-discovered publishers (1-paragraph addition; preserves all existing INVs; cites ADR-0040).

Both amendments are scope-disciplined: no new INVs, no INV body changes. Just one-paragraph "How this composes under the protocol substrate" sections referencing ADR-0040.

#### D. Index updates

- `docs/decisions/README.md` — adds ADR-0040 row.
- `docs/design/README.md` — adds `kernel-reference-interface.md` row.
- `docs/specs/README.md` — no row addition (no new specs); aspects.md and project-aspects.md rows may gain an "amended in v0.4 per ADR-0040" note.

#### E. CHANGELOG entry

One paragraph under `## [Unreleased]` § Added (alongside the ADR-0039 paragraph) summarizing ADR-0040's discovery-mechanism commitment.

### Out of scope

- **All code changes.** Phase A implements entry-point discovery, retires `_kit_root()`, splits the wheel into `kanon-core` + `kanon-aspects`, ships the substrate-without-reference CI gate. This PR is documentation only.
- **Distribution boundary specifics** — the actual `pyproject.toml` for `kanon-core` / `kanon-aspects` lands in ADR-0043 (distribution + cadence) and Phase A. ADR-0040 specifies the *interface*; ADR-0043 specifies the *packaging mechanics*.
- **Realization-shape schema** — ADR-0041.
- **Dialect grammar versioning** — ADR-0041.
- **Composition algebra** (`surface:`, `before/after:`, `replaces:`) — ADR-0041.
- **Verification scope-of-exit-zero broader wording** — ADR-0042.
- **Substrate self-conformance** as a top-level spec — ADR-0044.
- **De-opinionation transition** — ADR-0045.
- **Migration script** — Phase A.

## Approach

1. **ADR first.** Author ADR-0040 with the ratification-grade Decision; cite ADR-0048 (parent commitment), ADR-0028 (project-aspect namespace), ADR-0026 (capability registry), ADR-0039 (resolution model).
2. **Design doc.** Author the entry-point shape, registry composition algorithm, independence invariant, and `_kit_root()` retirement walkthrough.
3. **Spec amendments.** Aspects.md and project-aspects.md gain protocol-substrate clauses.
4. **Indexes + CHANGELOG.**
5. **Run gates locally.** `kanon verify .`, `python scripts/check_links.py`, `python scripts/check_foundations.py`, `python scripts/check_invariant_ids.py`, `python scripts/check_verified_by.py`.
6. **Regenerate `.kanon/fidelity.lock`** if amended specs bump SHAs.

## Acceptance criteria

### ADR

- [x] AC-A1: `docs/decisions/0040-kernel-reference-runtime-interface.md` exists with `status: accepted` and the six required ADR sections.
- [x] AC-A2: ADR-0040 cites ADR-0048 (parent), ADR-0028 (project-aspect grammar), ADR-0026 (capability registry), ADR-0039 (resolution model).
- [x] AC-A3: At least five Alternatives Considered, each with clear rejection rationale.

### Design

- [x] AC-D1: `docs/design/kernel-reference-interface.md` contains the `[project.entry-points."kanon.aspects"]` shape with worked example.
- [x] AC-D2: Registry composition algorithm specified with enough detail that Phase A can implement without further design work.
- [x] AC-D3: Independence invariant test design specified concretely (CI gate algorithm).
- [x] AC-D4: Every call site of `_kit_root()` walked with replacement specified.

### Spec amendments

- [x] AC-S1: `docs/specs/aspects.md` gains a one-paragraph "Protocol-substrate composition" section citing ADR-0040; existing INVs unchanged.
- [x] AC-S2: `docs/specs/project-aspects.md` gains a parallel section.

### Indexes + CHANGELOG

- [x] AC-X1: `docs/decisions/README.md` updated with ADR-0040 row.
- [x] AC-X2: `docs/design/README.md` updated with `kernel-reference-interface.md` row.
- [x] AC-X3: `CHANGELOG.md` `## [Unreleased] § Added` gains a paragraph naming ADR-0040.

### Cross-cutting

- [x] AC-X4: `kanon verify .` returns `status: ok` (zero warnings; regenerate fidelity lock if needed).
- [x] AC-X5: `python scripts/check_links.py` passes.
- [x] AC-X6: `python scripts/check_foundations.py` passes.
- [x] AC-X7: `python scripts/check_invariant_ids.py` passes (no new INVs).
- [x] AC-X8: `python scripts/check_verified_by.py` passes (only pre-existing scaffold-v2 warnings acceptable).
- [x] AC-X9: No source / aspect-manifest / protocol-prose / CI changes.

## Risks / concerns

- **Risk: ADR-0040 may overlap with ADR-0043 (distribution boundary).** Mitigation: ADR-0040 specifies the *runtime interface* (how the kernel discovers aspects at startup); ADR-0043 specifies the *packaging mechanics* (wheel split, release cadence). Clean separation; ADR-0043 cites ADR-0040 for the interface.
- **Risk: spec amendments to aspects.md and project-aspects.md may be challenged on immutability grounds.** Mitigation: the amendments are append-only (new section appended) and do not modify existing INV bodies. Same pattern applied to verification-contract.md INV-11 in PR #53. ADR-0040 ratifies the amendment; predecessor SHAs are recorded in fidelity.lock.
- **Risk: Phase A implementation may diverge from the design.** Mitigation: design pseudocode is intentionally minimal; Phase A authors a more detailed implementation plan that this design doc references back. Divergence within the registry-composition algorithm's outputs is fine; divergence on the entry-point group name (`kanon.aspects`) is NOT — that's the public contract `acme-` publishers depend on.
- **Risk: `kanon-core` test suite may not actually pass without `kanon-aspects` today.** Mitigation: ADR-0040's independence invariant is a *future* commitment; Phase A is responsible for making the kernel pass tests independently. The ADR commits to the invariant; the implementation lands the gate. Calling out the gap explicitly in Consequences.

## Documentation impact

- **New files:** `docs/decisions/0040-kernel-reference-runtime-interface.md`; `docs/design/kernel-reference-interface.md`.
- **Touched files:** `docs/specs/aspects.md` (one-paragraph append), `docs/specs/project-aspects.md` (one-paragraph append), `docs/decisions/README.md`, `docs/design/README.md`, `CHANGELOG.md`.
- **Possibly touched:** `.kanon/fidelity.lock` (if amended specs bump SHAs).
- **No source / aspect-manifest / protocol-prose / CI changes.**
