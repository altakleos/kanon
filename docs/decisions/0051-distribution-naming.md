---
status: accepted
date: 2026-05-03
---
# ADR-0051: distribution naming for the three-package split

## Context

ADR-0048 (`kanon as protocol substrate`) committed to splitting the current single `kanon-kit` distribution into three:

1. The substrate kernel (atomic writes, scaffolding, verify orchestration, fidelity replay, resolution-replay engine, dialect grammar parser, structural validators).
2. The reference content (the seven `kanon-` aspects' manifests, protocols, files, loaders).
3. A meta-package alias preserving the convenience-install path.

ADR-0048 §Decision named these `kanon-substrate`, `kanon-reference`, and `kanon-kit` respectively. That naming was provisional — chosen at the moment the architectural decision was made, when "what to call the distributions" was the least-load-bearing detail of a much larger commitment. The architectural decision has been ratified and partially executed (the Python module rename per ADR-0050 Option A landed in v0.5.0a2 on 2026-05-03); the distribution split itself has not. Neither `kanon-substrate` nor `kanon-reference` has been published to PyPI (verified 2026-05-03; both names return HTTP 404). Renaming the planned distributions today costs zero PyPI history to migrate and zero downstream consumers to coordinate with.

Two friction points with the ADR-0048 names emerged in subsequent discussion and use:

1. **`substrate` is in-house jargon.** The biology-flavored framing was pedagogically useful inside ADR-0048's argument ("the layer beneath upon which other things sit, not the disciplines themselves"). It does not survive contact with a Python ecosystem newcomer, who searches for `<project>-core`. The substrate concept is preserved in narrative; the distribution name is what people install.

2. **`reference` reads as a description, not a content label.** The package's actual contents are *aspects* — the project's central domain term. `kanon-reference` requires the reader to know that "reference content" means "aspects"; `kanon-aspects` requires no such knowledge. This is the single biggest discoverability win available without changing semantics.

The meta-package name `kanon-kit` survives unchanged: "kit" already perfectly captures meta-package shape and is the historical name users have installed since v0.1.

## Decision

The three-package split per ADR-0048 will use these distribution names:

| Role | Distribution name | What it ships |
|------|------------------|---------------|
| Substrate kernel | `kanon-core` | The kernel: atomic writes, scaffolding, verify orchestration, fidelity replay, resolution-replay engine, dialect grammar parser, structural validators. Ships zero aspects. |
| Reference content | `kanon-aspects` | The seven `kanon-<slug>` reference aspects as data: manifests, protocols, files, loaders. Opt-in. |
| Meta-package | `kanon-kit` | Convenience install — depends on `kanon-core` + `kanon-aspects`. Preserves the historical `pip install kanon-kit` ergonomics. |

This supersedes ADR-0048 §Decision §1 and §2 *only as to the distribution names*. Every other commitment of ADR-0048 — substrate-as-protocol, publisher symmetry, capability registry, principle public-tier, persona retirements, recipe-shaped opt-in — survives verbatim.

### Naming rationale (per package)

1. **`kanon-core` over `kanon-substrate`** — `core` is the Python ecosystem's standard term for "the foundational package without optional content" (django-core, flask-core, jupyter-core). It carries no jargon load, sorts adjacent to other `kanon-*` packages alphabetically near where users expect, and is what users will type into PyPI search. The substrate concept is preserved in ADR-0048's narrative — the distribution name does not need to teach the architecture; the architecture documentation does.

2. **`kanon-aspects` over `kanon-reference`** — the package's content IS aspects; the package name should say so. ADR-0028's namespacing semantics are unchanged: aspect slugs remain `kanon-<local>` (`kanon-sdd` etc.); the distribution `kanon-aspects` is "the kanon publisher's set of aspects", parallel to how a third party would publish `acme-aspects` for their own bundle. The name follows the `<publisher>-aspects` convention rather than claiming an unqualified "*the* aspects" — see §Publisher symmetry below.

3. **`kanon-kit` unchanged** — backward-compatible install command. Users who have `pip install kanon-kit` muscle memory keep it; the meta-package's deps shift from "the monolith" to "core + aspects".

### Publisher symmetry: how the `acme-` plane is meant to read

Under the new naming, a third-party publisher follows this exact pattern:

```
acme-core         # ← does NOT exist; there is only one substrate
acme-aspects      # ← the acme publisher's set of aspects
acme-kit          # ← optional; meta-package depending on acme-aspects + kanon-core
```

The substrate (`kanon-core`) is unique by design — only one kernel ships the contract grammar and replay engine. The `<publisher>-aspects` pattern is the substitutable plane (per ADR-0026's capability registry, ADR-0028's project-aspect namespacing). `kanon-aspects` is one set among many that may exist; it is *the reference set* by virtue of being shipped by the kanon project, not by virtue of its name.

This subtlety must be documented in the kit-author docs (the `acme-` plane explanation in `docs/foundations/de-opinionation.md` and the publisher persona). Failure to do so risks readers concluding "kanon owns the term *aspects*" when the project's whole point is publisher symmetry.

### Entry-point group `kanon.aspects`

The Python entry-point group `kanon.aspects` (per ADR-0040) is preserved unchanged. It is the protocol contract by which the substrate discovers aspect bundles regardless of publisher; renaming it would be a breaking-protocol change and is explicitly out of scope. Note that `kanon-aspects` (the distribution) and `kanon.aspects` (the entry-point group) share a word but are independent concepts:

- `kanon-aspects` is **one possible distribution** that registers under the entry-point group.
- `kanon.aspects` is **the universal entry-point group** all publisher-bundles register under (`acme-aspects`, `widgets-aspects`, etc.).

This independence will be documented in ADR-0040's reference notes (under an `Allow-ADR-edit:` trailer) and in the publisher-author docs.

## Alternatives Considered

1. **Keep `kanon-substrate` + `kanon-reference` per ADR-0048.** Rejected. The names work but cost discoverability without a counterbalancing benefit. The argument for keeping them is "we already wrote them down"; the argument against is "they will be installed by humans typing into shells for the lifetime of the project." The latter wins given zero migration cost today.

2. **`kanon-substrate` + `kanon-aspects`.** Mixed: take the aspects rename but keep substrate. Rejected as half-measure. If the principle is "names should match what users search and what content is", apply it to both. Substrate has the same jargon problem as reference.

3. **`kanon-kernel` over `kanon-core`.** Considered. Rejected because (a) "kernel" is the *role* the package plays in the architecture (the term ADR-0048 uses internally, and the term the Python module `kernel/` per ADR-0050 uses); (b) "core" is what users *install*. The two roles can use different vocabulary: the source tree at `kernel/` documents the architectural role; the PyPI distribution `kanon-core` is the user-facing handle. This separation already exists with the CLI command `kanon` ≠ distribution name `kanon-kit`.

4. **Drop the `kanon-` prefix entirely (`core`, `aspects`, `kit`).** Rejected. `core` and `aspects` are unowned PyPI namespaces (squatted in some cases) but with no clear ownership claim — using them collides with ecosystem conventions and forfeits the publisher-symmetry framing (`acme-aspects` works only if the prefix carries publisher identity).

5. **Wait until the Phase A split is actually executed before naming.** Rejected. The names appear in ADR-0048 §Decision (twice each), in ADR-0049 §Implementation Roadmap (referring to the planned wheels), in `docs/design/distribution-boundary.md` (the architecture spec for the split), and in scattered commit messages and CHANGELOG entries. Each of those references would need updating later; better to update them once now while the count is small than later when Phase A has multiplied them.

6. **Issue the rename as an ADR-0048 amendment via `Allow-ADR-edit:` rather than a new ADR.** Rejected. ADR-0032's immutability gate exists because in-place ADR edits hide the decision history readers later rely on to understand "why was X named Y". Naming changes are exactly the class of decision future readers will trace; a separate ADR with its own context, decision, and consequences is the right shape. ADR-0050 set this precedent for ADR-0049's deferral; this ADR follows it.

## Consequences

### Distribution-level

- **PyPI registrations**: `kanon-core` and `kanon-aspects` will be claimed at the moment Phase A ships its first pre-release (alongside the kanon-kit bump that re-targets its dependencies). Both names are unclaimed today (verified 2026-05-03); no squatter risk in the immediate term, but Phase A authors should claim quickly once the split lands.
- **`kanon-kit`'s `[project.dependencies]` list rewrites**: `kanon-substrate` → `kanon-core`; new entry `kanon-aspects`. Currently `kanon-kit` ships everything; post-split it ships nothing of its own and depends on the two real packages. Version pin: `>=` minimum is the major.minor at split time.

### Documentation

- **ADR-0048 references**: every `kanon-substrate` → `kanon-core`, every `kanon-reference` → `kanon-aspects`. Per the immutability gate, this requires an `Allow-ADR-edit: 0048 — distribution rename per ADR-0051` trailer on the commit that touches it. The same trailer pattern applies to ADR-0049 and any other ADR that names the planned distributions.
- **`docs/design/distribution-boundary.md`**: this is the architecture-narrative doc for the split; its entire vocabulary updates. Not ADR-immutable; edit freely.
- **`docs/foundations/de-opinionation.md`** and the **publisher persona**: gain the `<publisher>-aspects` convention paragraph (Decision §Publisher symmetry above). Without it, the symmetry argument is a footnote a reader may miss.
- **`README.md`**, **`CHANGELOG.md`**, **`docs/contributing.md`**: update install-command examples and the package-map table.

### Code

- **No code changes today** — the split itself is deferred per ADR-0049 §Implementation Roadmap and the ADR-0050 deferral. The distribution names appear only in `pyproject.toml` strings and in documentation. When Phase A executes, it uses the new names from the start.
- **Source tree paths unchanged** by this ADR. The Python module is still `kernel/` (per ADR-0050 Option A); aspect data is still at `src/kanon_reference/aspects/kanon_<slug>/` (per ADR-0049 PR A). The directory `src/kanon_reference/` may be renamed to align with `kanon-aspects` when Phase A executes, but is out of scope for this ADR (it's a source-tree refactor with the same Hatch editable-install constraint that produced ADR-0050; needs its own ADR).

### Migration

- **Zero PyPI migration**: no consumer can have installed `kanon-substrate` or `kanon-reference`; both 404 today. The rename is a doc + future-pyproject change only.
- **Internal references**: searched at write time, ~15 cites across ADR-0048, ADR-0049, `docs/design/distribution-boundary.md`, `docs/plans/active/v040a4-release.md`, and a handful of design docs. A single follow-up PR sweeps all of them.

### Scope

- **Supersedes ADR-0048 in part** — only the three distribution names in §Decision §1 and §2. Every other ADR-0048 commitment (substrate-as-protocol, publisher symmetry, capability registry, principle public-tier, persona retirements, recipe-shaped opt-in, no-defaults, no-bare-name-sugar, `acme-` plane recognition, `_detect.py` removal, kit-global `files:` removal, dialect cadence, kernel-daily / reference-weekly / dialect-quarterly versioning) survives intact.
- **Does not touch** ADR-0026, ADR-0028, ADR-0040, ADR-0049 §Implementation Roadmap (other than the names it cites), or any ADR predating ADR-0048 in the architectural lineage.
- **No backwards-compatibility shim** — there are no consumers; the cost of providing `kanon-substrate` and `kanon-reference` as legacy aliases is non-zero (PyPI registrations, deprecation tooling) and the benefit is zero (no one to deprecate to).

## Config Impact

None. `.kanon/config.yaml` schema is unaffected; aspect slugs (`kanon-sdd` etc.) are unaffected; entry-point group `kanon.aspects` is unaffected.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — distribution split decision; this ADR supersedes its naming choices only.
- [ADR-0026](0026-aspect-provides-and-generalised-requires.md) — capability registry; the substitutability plane the `<publisher>-aspects` convention serves.
- [ADR-0028](0028-project-aspects.md) — project-aspect namespacing; the `acme-` plane reservation that makes `kanon-aspects` (vs unqualified "aspects") important.
- [ADR-0040](0040-kernel-reference-runtime-interface.md) — entry-point group `kanon.aspects`; preserved verbatim by this ADR. Reference notes will gain a clarification of the package-vs-group distinction.
- [ADR-0049](0049-monorepo-layout.md) — implementation roadmap that references the planned distribution names.
- [ADR-0050](0050-kernel-flatten-deferral.md) — Phase A deferral; same precedent of authoring follow-up ADRs to refine ADR-0048's commitments rather than amending in-place.
- PyPI availability check (2026-05-03): `kanon-substrate`, `kanon-reference`, `kanon-core`, `kanon-aspects` all return HTTP 404; rename is unencumbered.
