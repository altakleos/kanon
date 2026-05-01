---
status: accepted
date: 2026-05-01
---
# ADR-0043: Distribution boundary, release cadence, and recipe artifact

## Context

[ADR-0040](0040-kernel-reference-runtime-interface.md) ratified the *runtime interface* — Python entry-points group `kanon.aspects` is how the kernel discovers aspects at startup. [ADR-0041](0041-realization-shape-dialect-grammar.md) ratified the *grammar* — what shape contracts have, how dialects evolve. Neither addresses the *packaging mechanics*: how `kanon-substrate` and `kanon-reference` actually ship as separately-installable distributions, what release cadence the substrate honours across its kernel/reference/dialect surfaces, or how a consumer adopts a starter set without re-introducing kit-shape behaviour through a side door.

This ADR ratifies all three as one coherent decision because they are coupled by the protocol commitment:

1. **Distribution boundary**: ADR-0040 said "publishers register entry-points"; this ADR says how `kanon-substrate` (kernel) and `kanon-reference` (seven `kanon-` aspects as data) actually package separately. Round-5 code-reviewer's option-B (substrate + reference + meta-alias) over per-aspect-wheels ("theatre") and single-wheel (kit-shape vestige).

2. **Release cadence**: today's `kanon-kit` ships daily-alpha. Under the protocol commitment with dialect grammar (per ADR-0041), unrestrained daily-alpha would shred any future `acme-` author. Round-5 planner: "a breaking dialect change every day would shred any future `acme-` author." Cadence discipline keeps kernel evolution fast while keeping dialect evolution slow.

3. **Recipe artifact**: under the de-opinionation commitment (per ADR-0048), `kanon init` enables nothing by default. Consumers who want a starter set adopt one via a publisher-shipped *recipe* — target-tree YAML the consumer copies. Round-5 code-reviewer's option-3: recipes are inert YAML, not a kernel verb. The substrate has no opinion about which recipe is right.

## Decision

Three numbered ratifications:

### 1. Distribution boundary

The `kanon-substrate` and `kanon-reference` distributions are separately installable. A `kanon-kit` meta-package alias provides the convenience-install path.

- **`kanon-substrate`** ships the kernel: `_atomic.py`, `_scaffold.py`, `_manifest.py`, `_verify.py`, `_fidelity.py`, `_resolutions.py` (Phase A), `_dialects.py` (Phase A), `_composition.py` (Phase A), `_validators/` (in-process kit-side correctness), `cli.py`, dialect-grammar parsers, structural validators. Zero aspects ship in this distribution. Per [ADR-0040](0040-kernel-reference-runtime-interface.md)'s independence invariant, the substrate's test suite passes with `kanon-reference` uninstalled.
- **`kanon-reference`** ships the seven reference aspects (`kanon-sdd`, `kanon-testing`, `kanon-worktrees`, `kanon-release`, `kanon-security`, `kanon-deps`, `kanon-fidelity`) as data. It declares Python entry-points under `kanon.aspects` per [ADR-0040](0040-kernel-reference-runtime-interface.md)'s entry-point shape. Depends on `kanon-substrate>=1.0`.
- **`kanon-kit`** is a meta-package alias. It declares `kanon-substrate` and `kanon-reference` as dependencies and ships no source. `pip install kanon-kit` installs both; `pip install kanon-substrate` installs only the kernel.

The package names are public and stable. `kanon-kit` is preserved (rather than introduced as a new alias) because the v0.3.x audience may have it pinned in CI configs; the meta-alias semantics are honoured for backward compatibility through the deprecation horizon.

### 2. Release cadence

Three cadences govern three release surfaces:

- **Kernel: daily-alpha permitted.** `kanon-substrate` may ship daily alpha releases under semver (e.g., `1.0.0a1`, `1.0.0a2`). Daily-alpha is the substrate-author's option, not an obligation. Bug fixes, contract validators, CLI ergonomics, structural validator improvements — these are kernel-cadence work.
- **Reference: weekly cadence.** `kanon-reference` ships at weekly cadence (substrate-author discretion). Reference releases never include kernel-level changes. A change that affects both kernel and reference (e.g., a new dialect that bumps both surfaces) ships as separate, coordinated releases — kernel ships first; reference ships within the same week.
- **Dialect: quarterly minimum, annual default.** A new dialect (`kanon-dialect: YYYY-MM-DD` per ADR-0041) ships at quarterly minimum, annual default. Dialect supersession is calendar-driven; an ADR ratifies the new dialect; the new dialect's spec describes what changed relative to its predecessor; publishers migrate at their own pace within the deprecation horizon.

**A breaking dialect change is never a kernel release.** This is the cadence discipline's load-bearing rule. If a substrate evolution requires a grammar change, it ships as a *dialect supersession* (a new ADR + a new dialect spec + the substrate honouring the previous dialect for at least the deprecation horizon), not as a kernel release. This is what makes daily-alpha kernel releases safe for `acme-` publishers who pin against a dialect: the dialect — not the kernel — is the API surface they author against.

### 3. Recipe artifact

Recipes are publisher-shipped target-tree YAML. They live in the publisher's distribution as data; the consumer copies the chosen recipe into `.kanon/recipes/<recipe-name>.yaml` and applies it.

- **Recipe shape**: a YAML file declaring a list of aspect-id + depth pairs to enable, plus optional metadata (publisher attribution, recipe semantic version, target-substrate-dialect-pin). The exact schema lives in [`docs/design/distribution-boundary.md`](../design/distribution-boundary.md).
- **Recipe location in the consumer repo**: `.kanon/recipes/<recipe-name>.yaml`. Consumers commit recipes; the substrate replays them. Multiple recipes may coexist; the consumer chooses which to apply at any time.
- **Substrate has no kernel verb for recipes.** No `kanon recipes apply`, no `kanon init --recipe X`. The kernel's contribution is reading `.kanon/recipes/` files and resolving them through `_load_aspect_registry`. Application is a consumer-side action — `cp publisher-bundle/recipes/web-default.yaml .kanon/recipes/`, then commit.
- **The kanon repo's own self-host opt-in uses this mechanism** (per [ADR-0048](0048-kanon-as-protocol-substrate.md)'s self-host commitment). The repo's `.kanon/config.yaml` declares aspects via a publisher recipe with `provenance:` recording attribution; no kernel-side privilege.

This satisfies de-opinionation (no kernel feature dictating which recipe is right) while giving consumers a working starter path (publishers ship opinionated recipes; consumers choose one).

## Alternatives Considered

1. **Single wheel** (current `kanon-kit`): kernel + reference ship together. **Rejected.** Re-establishes the kit shape under a different name; reference aspects become non-de-installable; `acme-` publishers are second-class. ADR-0048 explicitly retires this shape.

2. **Per-aspect wheels** (`kanon-sdd`, `kanon-testing`, …, each separately installable). **Rejected** as "theatre" by Round-5 code-reviewer: "8 wheels is theatre. The 7 reference aspects ship in lockstep (they share a release cycle, a CHANGELOG, a CI), so granularity gains nothing and the build/release surface octuples." Per-aspect granularity is what `acme-` publishers do for *their* aspects; the kanon-team's reference aspects are one product.

3. **Vendor reference into substrate**: kernel ships reference aspects internally and exposes them via the registry. **Rejected.** Same as Alternative #1 — re-establishes kit shape. Failed publisher-symmetry check.

4. **Daily-alpha across all surfaces** (kernel + reference + dialect): same cadence everywhere. **Rejected.** Daily-alpha dialect changes shred publisher-symmetry; an `acme-` publisher pinning `kanon-dialect: 2026-05-01` cannot rely on the pin if the substrate ships dialect changes daily. Cadence separation by surface is what makes the substrate safe for publishers.

5. **Recipes as kernel feature**: `kanon recipes apply <recipe-name>` is a kernel verb that applies a recipe by reading from a publisher's installed package. **Rejected** for two reasons. (a) The kernel having a recipe-resolution verb means it has knowledge of "which recipes exist" — re-introduces kit-shape opinion. (b) Recipes are publisher artifacts; the kernel resolving them adds a privileged code path on the consumer side. Inert YAML in the consumer repo, copied from a publisher's bundle, preserves `P-protocol-not-product`: recipes are explicitly one publisher's curation, not a kernel feature.

## Consequences

### Distribution

- **Phase A authors three `pyproject.toml` files**: `kanon-substrate/pyproject.toml`, `kanon-reference/pyproject.toml`, `kanon-kit/pyproject.toml` (meta-alias). Each declares its dependencies, version, and (for reference) `[project.entry-points."kanon.aspects"]` per [ADR-0040](0040-kernel-reference-runtime-interface.md).
- **`kanon-kit` meta-alias depends on `kanon-substrate` and `kanon-reference`** at exact versions for each release. Coordinating across the split is part of Phase A's release-workflow.
- **The `kanon migrate v0.3 → v0.4` script** (per ADR-0048's migration commitment) migrates a v0.3.x consumer repo to v0.4 by rewriting `.kanon/config.yaml` to opt-in form, copying the `reference-default` recipe to `.kanon/recipes/`, and deprecating itself on first use. Phase A authors.

### Cadence

- **Phase A authors a release-cadence CI gate** (`ci/check_release_cadence.py` or analogous) that fails if a kernel release commit also touches dialect grammar files. The gate prevents the cadence-discipline breach (per [`docs/specs/release-cadence.md`](../specs/release-cadence.md) `INV-release-cadence-breaking-not-in-kernel`).
- **Phase A authors release workflows** (GitHub Actions or analogous) that publish substrate, reference, and meta-alias separately on tag push.
- **Today's `release.yml` workflow** is replaced (kernel/reference/meta-alias release flows). Phase A migrates the existing workflow.

### Recipes

- **`kanon-reference` ships at least one recipe**: `reference-default` (opts the consumer into all seven reference aspects at their default depths). Phase A authors. Per [ADR-0048](0048-kanon-as-protocol-substrate.md)'s commitment, the kanon repo's own self-host uses this recipe.
- **The substrate scaffolds `.kanon/recipes/.gitkeep`** at `kanon init` (Phase A) so the directory exists; consumers populate it by `cp`-ing recipes from publisher bundles.
- **`kanon aspect list`** (Phase A) gains a `--recipes` flag that enumerates recipes available in installed publishers (read-only inspection; no application).

### Out of scope (deferred)

- **Substrate self-conformance** as a top-level spec — ADR-0044.
- **De-opinionation transition** mechanics — ADR-0045.
- **`acme-` publisher cadence guidance** — Phase B/C; `acme-` publishers set their own.

## Config Impact

- **No consumer-side `.kanon/config.yaml` schema change** caused by this ADR. The v3 → v4 schema bump (publisher-id, recipe-provenance, dialect-pin) ratified across ADR-0039 / ADR-0041 is unaffected.
- **`pyproject.toml` shapes** for the three packages are documented in `docs/design/distribution-boundary.md`.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (parent).
- [ADR-0040](0040-kernel-reference-runtime-interface.md) — runtime interface; this ADR ratifies the packaging that the runtime interface lives in.
- [ADR-0041](0041-realization-shape-dialect-grammar.md) — dialect grammar; this ADR's cadence policy governs dialect supersession.
- [ADR-0039](0039-contract-resolution-model.md) — runtime-binding model.
- [`docs/specs/release-cadence.md`](../specs/release-cadence.md) — invariants this ADR ratifies.
- [`docs/design/distribution-boundary.md`](../design/distribution-boundary.md) — concrete pyproject shapes, recipe schema, migration outline.
- [`docs/foundations/principles/P-protocol-not-product.md`](../foundations/principles/P-protocol-not-product.md) — the principle that drives recipe-as-publisher-artifact.
