---
status: accepted
date: 2026-05-01
---
# ADR-0041: Realization-shape, dialect grammar, and composition algebra

## Context

[ADR-0039](0039-contract-resolution-model.md) ratified the runtime-binding model — prose contracts get resolved into `.kanon/resolutions.yaml`, the kernel replays mechanically. [ADR-0040](0040-kernel-reference-runtime-interface.md) ratified the discovery interface — Python entry-points group `kanon.aspects` is how the kernel finds aspects at startup. Neither addresses what *shape* a contract has, how the substrate evolves that shape over time, or how multiple contracts compose when they target the same execution surface. This ADR does.

Three commitments converge in one decision because they are tightly coupled:

1. **Realization-shape per contract.** Each contract declares frontmatter specifying allowed verbs, evidence kinds, and stage keys. Without a typed shape, resolutions are free-form YAML — and the kernel cannot validate them at replay, the agent has no precise authoring target, and `kanon contracts validate` cannot exist. Round-5 panel: 5 of 6 agents independently identified shape schemas as the strongest single addition.
2. **Dialect grammar versioning.** The substrate evolves; aspect grammar evolves. Without dialect-version pinning, every grammar change is potentially a breaking change for every existing publisher. With dialect-version pinning, the substrate honours at least N-1 dialects with a deprecation horizon, and grammar evolution becomes safe. Round-3 architect: prevents the year-5 grammar fork. Round-5 document-specialist: JSON Schema dialects model is the precedent.
3. **Composition algebra.** When `kanon-testing` and `acme-strict-testing` both target the `preflight.commit` surface, the substrate needs a deterministic ordering rule. Without composition algebra, multi-publisher composition is undefined behaviour. Round-5 architect: the substrate's load-bearing publisher-symmetry promise collapses without it.

The three are coupled because realization-shape needs a dialect to evolve under, and composition algebra needs realization-shape to type its `surface:` and `before/after:` declarations. One ADR ratifies all three at once.

This ADR specifies the *grammar*; ADR-0042 will specify what `kanon verify`'s exit-code claim means in light of it; ADR-0043 will specify the wheel-distribution mechanics that ship the dialect with the substrate.

## Decision

Three numbered ratifications:

### 1. Realization-shape per contract

Every contract authored against the substrate's grammar declares `realization-shape:` frontmatter that specifies:

- **`verbs:`** — an enumeration of allowed invocation verbs the resolution may use (e.g., `[lint, test, typecheck, format, scan, audit]`). Resolutions citing verbs not in the set are rejected at replay with `code: shape-violation`.
- **`evidence-kinds:`** — an enumeration of allowed evidence-citation kinds (e.g., `[config-file, ci-workflow, build-script, source-convention]`). Resolutions citing evidence kinds outside the set are rejected.
- **`stages:`** — when applicable, a list of named stages the contract orders against (`commit`, `push`, `release` for preflight contracts; absent for non-staged contracts).
- **`additional-properties:`** — `false` (default) or `true`. When `false`, resolutions with keys outside the declared shape are rejected; when `true`, extra keys are passed through (forward-compatibility hatch for publishers who explicitly accept it).

The kernel validates resolutions against the contract's `realization-shape:` at replay (per [`docs/specs/resolutions.md`](../specs/resolutions.md) `INV-resolutions-quadruple-pin` and the new `INV-dialect-grammar-shape-validates-resolutions`). Shape mismatches are `kanon verify` findings, never silent.

### 2. Dialect grammar versioning

Every aspect manifest pins `kanon-dialect:` to a date-stamped dialect version (e.g., `kanon-dialect: 2026-05-01`). The substrate ships with a list of supported dialects; manifests pinning unknown dialects fail at load time with `code: unknown-dialect`.

- **Format**: `YYYY-MM-DD`. Dialects are date-stamped artifacts, not semver-versioned. This avoids the trap of treating dialect grammar like software (where minor/major distinctions are ambiguous in prose); date-stamping makes ordering trivial and forces every dialect ratification through an ADR-driven calendar event.
- **Honouring**: the substrate honours at least the current dialect (N) and the previous dialect (N-1). Manifests pinning N-2 or older receive a deprecation warning; the kernel still loads them. Manifests pinning N+1 (a dialect newer than the running substrate knows) fail at load.
- **Supersession**: a new dialect is ratified by a future ADR. The new dialect's spec describes what changed relative to its predecessor; publishers migrate at their own pace within the deprecation horizon.

### 3. Composition algebra

Contracts targeting the same execution surface coordinate via three frontmatter fields:

- **`surface:`** — the named execution surface this contract targets (e.g., `preflight.commit`, `preflight.push`, `preflight.release`, `release-gate.tag`, `verify.structural`). The substrate enumerates surfaces; publishers cite them.
- **`before:`** / **`after:`** — declarative ordering: `before: [<contract-id>]` means this contract's invocations execute before the listed contract's; `after:` is the dual. The substrate topologically sorts; cycles fail at load with `code: composition-cycle`, naming the offending edges.
- **`replaces:`** — substitution: `replaces: <contract-id>@<version-range>` means this contract supersedes the listed contract for the duration of the consumer's session. The replacing contract inherits the replaced contract's `provides:` capability declarations (per [ADR-0026](0026-aspect-provides-and-generalised-requires.md)). Replacement is resolved before composition; the replaced contract drops out of the topo-sort.

The substrate is publisher-blind during composition: a `kanon-testing` contract and an `acme-strict-testing` contract on the same surface compose under identical rules. No precedence by namespace. Consumer-side `prefer:` directives in `.kanon/config.yaml` (an extension authored by a future ADR) may resolve ambiguity; absent such directives, two enabled contracts on the same surface with no `before/after:` relationship between them produce a `code: ambiguous-composition` finding.

## Alternatives Considered

1. **One amorphous schema for all contracts.** A single shape covers preflight, testing, security review, release gate, etc. **Rejected.** The shapes diverge meaningfully (preflight has stages; security review has severity levels; release gate has cryptographic-signing fields). Forcing one schema either over-specifies (rejecting valid resolutions) or under-specifies (admitting nonsense). Per-contract realization-shape gives each contract type its own typed surface.

2. **Per-aspect schemas instead of per-contract.** A `kanon-testing` aspect ships one schema covering all its contracts. **Rejected.** Under the substrate's "every contract is independently substitutable" promise (per `P-publisher-symmetry`), per-aspect schemas re-couple contracts to their aspect of origin. A future `acme-strict-testing` aspect substituting only one contract would inherit unwanted shape constraints from `kanon-testing`'s aspect-level schema. Per-contract is the right granularity.

3. **No dialect versioning; all grammar changes are breaking.** Substrate evolution simply breaks publishers; consumers re-resolve. **Rejected.** This collapses the substrate's "publishers can author against stable guarantees" commitment (per ADR-0048). With zero dialect versioning, every `kanon-substrate` release is a potential `acme-` ecosystem extinction event. Dialect-versioning + N-1 honouring lets the substrate evolve without breaking the world.

4. **Semver dialect versioning** (`kanon-dialect: 1.2.3`). **Rejected.** Semver has clean meaning for software (major = breaking, minor = additive, patch = fix); applied to prose grammar, the major/minor/patch distinctions are ambiguous (is "removing a frontmatter field" major or minor? what counts as additive when the field accepts new enum values?). Date-stamping side-steps the ambiguity: each dialect is a snapshot; differences between dialects are recorded in the next dialect's spec. The Markdown ecosystem's CommonMark series uses an analogous date-versioning scheme.

5. **Runtime composition order computed by the kernel.** The kernel observes which contracts are enabled and infers ordering (e.g., alphabetical, by aspect-load-time, by depth). **Rejected.** Implicit ordering means consumers cannot predict execution order without reading kernel source. Publisher-declared `before/after:` makes the order explicit, auditable, and stable across kernel versions.

## Consequences

### Substrate-level

- **`_resolutions.py` validates shape at replay** (Phase A: ~80 LOC added). On shape violation, replay fails for that contract with structured finding.
- **`_manifest.py` validates dialect-pin at load time** (Phase A: ~40 LOC added). Unknown-dialect manifests fail to load with explicit error.
- **`_composition.py` (new module)** implements the topo-sort plus cycle detection plus `replaces:` resolution (Phase A: ~150 LOC).
- **`kanon contracts validate <bundle-path>`** (new CLI verb, Phase A: ~80 LOC). Walks a publisher's bundle, validates all manifests against the substrate's known dialects, validates all contracts against their declared `realization-shape:`, runs composition pre-flight (cycle detection without execution).

### Publisher-side

- **Reference aspects ship `realization-shape:` frontmatter on every contract** (Phase A: a discrete pass through `kanon-reference`'s contract files).
- **Publishers declare `kanon-dialect:` in every aspect manifest**. Migration: Phase A bumps every existing manifest to the v0.4 baseline dialect (date TBD by Phase A; likely `kanon-dialect: 2026-05-01`).

### Verification

- **`kanon verify` exit-code claims gain shape conformance** as a structural check (per ADR-0041's contract-shape semantic; ADR-0042 will state the broader exit-zero claim explicitly).

### Out of scope (deferred to subsequent Phase 0 ADRs)

- **Verification scope-of-exit-zero broader wording** — ADR-0042. (INV-11 added in PR #53 already covers the structural exit-zero scope; ADR-0042 will broaden to the public claim.)
- **Distribution boundary mechanics** — ADR-0043.
- **Substrate self-conformance** — ADR-0044.
- **De-opinionation transition** — ADR-0045.
- **Specific realization-shapes for the seven `kanon-` reference contracts** — those are publisher artifacts ratified by `kanon-reference`'s release.
- **`acme-` publisher onboarding documentation** — Phase B.

## Config Impact

- **Aspect manifest schema**: gains required `kanon-dialect:` field at the top level. Phase A migrates every shipped manifest.
- **Contract frontmatter schema**: gains required `realization-shape:` block per contract; optional `surface:`, `before:`, `after:`, `replaces:` for composition-participating contracts.
- **`.kanon/config.yaml` v3 → v4 finalized**: ADR-0039 sketched v4 (publisher-id, recipe provenance, dialect-pin); ADR-0041 finalizes by adding the recipe-level `kanon-dialect:` pin.
- **`.kanon/resolutions.yaml`**: gains shape-validation as a replay step; the YAML schema itself is unchanged from ADR-0039.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (parent).
- [ADR-0039](0039-contract-resolution-model.md) — runtime-binding model; this ADR's shape-validation slots into the replay path.
- [ADR-0040](0040-kernel-reference-runtime-interface.md) — discovery interface; this ADR's dialect-pin operates on entry-point-discovered manifests.
- [ADR-0026](0026-aspect-provides-and-generalised-requires.md) — capability registry; `replaces:` substitution preserves capability inheritance per this ADR.
- [`docs/specs/dialect-grammar.md`](../specs/dialect-grammar.md) — invariants this ADR ratifies.
- [`docs/design/dialect-grammar.md`](../design/dialect-grammar.md) — concrete shape schemas, composition algorithm, validator pseudocode.
- [`docs/foundations/principles/P-publisher-symmetry.md`](../foundations/principles/P-publisher-symmetry.md) — the principle that drives publisher-blind composition.
