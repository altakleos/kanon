---
status: accepted
date: 2026-05-01
---
# ADR-0048: kanon as protocol substrate

## Context

kanon was conceived around a single bet: that **prose consumed by an LLM agent is the new source of truth**, and that engineering discipline can be packaged as prose contracts the agent reads, follows, and produces evidence against. v0.1 and v0.2 prototyped this as a *kit* — a curated bundle of opinionated aspects (`kanon-sdd`, `kanon-testing`, `kanon-worktrees`, …) shipped through a single pip wheel and auto-enabled by `kanon init` profiles. v0.3 layered the aspect model and capability registry (ADR-0012, ADR-0026, ADR-0028) on top of that kit shape.

By v0.3.1 the kit shape had revealed itself as a transitional artifact, not the destination. Three forces converged:

1. **The kit privileges Python.** `_detect.py` hardcodes ecosystem detection for pyproject/package.json/Cargo/go.mod; the testing aspect's `config-schema:` encodes that "testing means having a `test_cmd` string"; the kit scaffolds Python `ci/check_*.py` files into consumer trees. The substrate's whole point — prose for agents — does not require any of this.
2. **The `kanon-` namespace is privileged in resolver paths and at scaffold time.** `defaults:` in the top manifest auto-enables five aspects; bare-name CLI flags sugar to `kanon-` exclusively; the kit-global `files:` field is a privilege no other publisher has. Each privilege is small in isolation; collectively they make the substitutability promise of the capability registry (ADR-0026) honour-system-only.
3. **The bet that makes kanon kanon does not require any of these privileges.** Prose-as-code is a substrate property: the kit's job is to publish a contract grammar and a replay engine; the disciplines are demonstrations a publisher can ship, not products the kit *is*.

ADR-0012 §Alternatives recorded the substrate-shape option ("Kernel + sibling kits") and rejected it for v0.2 with an explicit revival condition: *"if in-tree fails past ~10 aspects."* That threshold is not what triggers this decision. What triggers it is the recognition that the project's foundational principle — `P-prose-is-code` — is incompatible with the kit's continuing privilege, regardless of aspect count. The kit was the detour; the protocol is the destination.

## Decision

**kanon is a protocol substrate for prose-as-code engineering discipline.**

Specifically:

1. **The substrate's deliverable is a contract grammar plus a replay engine**, not a curated discipline bundle. The pip distribution `kanon-substrate` ships the kernel (atomic writes, scaffolding, verify orchestration, fidelity replay, resolution-replay engine, dialect grammar parser, structural validators). It scaffolds nothing on its own behalf into consumer trees.

2. **Reference aspects (`kanon-sdd`, `kanon-testing`, `kanon-worktrees`, `kanon-release`, `kanon-security`, `kanon-deps`, `kanon-fidelity`) are demonstrations, not the product.** They ship in a separate, opt-in `kanon-reference` distribution. They are de-installable and replaceable by any publisher offering the same capabilities. A `kanon-kit` meta-package alias preserves the convenience-install path.

3. **The substrate publishes a defined set of principles as stable protocol commitments.** Six principles cross over into public-tier status: `P-prose-is-code`, `P-protocol-not-product`, `P-publisher-symmetry`, `P-runtime-non-interception`, `P-specs-are-source`, `P-verification-co-authored`. Two remain kit-author-internal: `P-self-hosted-bootstrap`, `P-cross-link-dont-duplicate`. Public-tier principles are versioned with the dialect, citable by `acme-` publishers, and immutable post-acceptance under the same discipline that protects ADR bodies (ADR-0032).

4. **`P-tiers-insulate` is retired.** The "tier" vocabulary it codified was a kit-shape consumer-experience concern; the substrate model uses depth dials per aspect and recipe-shaped opt-in by publisher, neither of which the principle's body addresses. The principle file is preserved with `status: superseded; superseded-by: 0048`.

5. **The kanon repo opts into reference aspects as a peer consumer.** The repo's `.kanon/config.yaml` declares aspects via the same recipe path any new project uses; no kernel-side carve-out treats the kanon repo specially. Self-hosting becomes the substrate's primary falsification probe, not a kit-shape demonstration.

6. **De-opinionation is two distinct properties, both committed to.**
   - **Audience de-opinionation:** the substrate makes no assumption about which disciplines a consumer adopts. `kanon init` enables nothing by default. Recipes are publisher-shipped; the substrate has no `defaults:`.
   - **Protocol opinionation, retained:** the substrate IS opinionated about contract grammar, dialect semantics, capability symmetry, and the public principle set. These are what a publisher relies on when authoring `acme-` bundles.

## Alternatives Considered

1. **Stay kit-shape; ship more aspects.** Rejected. Every additional aspect deepens the kit's privilege over `acme-` and makes the eventual substrate transition more expensive. ADR-0012's "revive past ~10 aspects" condition was demand-led; this decision is vision-led.

2. **Hybrid: protocol substrate but `kanon-` aspects auto-enable at init for "out-of-the-box experience."** Rejected. The privilege is exactly what the protocol commitment is removing. Auto-enabling reference aspects creates a "secret default" path that re-establishes kit-shape behaviour through a side door. Recipes (publisher-authored, target-tree YAML) are the right path for users who want a starter set; the substrate has no opinion about which recipe.

3. **Defer the protocol commitment until a real `acme-` author asks.** Rejected. The lead has zero current consumers and full optionality. The point of no return is the first non-kanon publisher: once `acme-X` ships and a downstream consumer pins it, the kit cannot revert without breaking that consumer. Committing while consumers are zero is the cheapest moment.

4. **Keep all principles kit-author-internal; do not publish any as protocol commitments.** Rejected. Publishers need stable guarantees to author against. Without a public principle commitment, every substrate version-bump is a potential breaking change for `acme-` bundles. The choice is between explicit guarantees the substrate honours and implicit ones publishers have to reverse-engineer; the former is cheaper to maintain.

5. **Author this commitment as an amendment to ADR-0012 instead of a new ADR.** Rejected. The change is large enough — distribution boundary, namespace privilege, principle public-tier, persona retirements, vision rewrite — that an amendment to ADR-0012 would either understate the scope or violate ADR-immutability. A new ADR (this one) supersedes ADR-0012 *in part* (the kit-shape framing); ADR-0012's aspect-model decision survives intact.

## Consequences

### Substrate-level

- **`kanon-substrate` ships the kernel only.** The current `kanon-kit` wheel splits: substrate (kernel + grammar parser + structural validators), reference (the seven `kanon-` aspects as data), meta-alias (`kanon-kit`) for the convenience-install path. Phase 0 ADRs (0039–0044, plus 0040.5 kernel/reference runtime interface) author the implementation.
- **`kanon init` produces a bare scaffold.** No aspects auto-enabled. The scaffolded `AGENTS.md` teaches the substrate's nature; recipes are discovered via documentation, not built into the kernel.
- **`defaults:` and `_detect.py` are removed.** Both are kit-shape vestiges that contradict publisher symmetry.
- **Bare-name CLI sugar (`--aspects sdd:1`) is deprecated.** Future invocations require explicit publisher prefixes. A deprecation shim runs for one minor version with a warning.
- **Kit-global `files:` field is removed from the top manifest.** Aspects own all their scaffolded files; the substrate scaffolds nothing on its own.

### Principles

- **The principles README reorganises by tier.** Public-protocol principles list first; kit-author-internal second; superseded principles in a third section.
- **Public-tier principle bodies become immutable post-acceptance.** Future amendments require dialect supersession, not in-place edits. The CI gate currently protecting accepted ADRs (`ci/check_adr_immutability.py` per ADR-0032) extends to public-tier principles. This applies *prospectively*: the amendments to `P-specs-are-source`, `P-self-hosted-bootstrap`, and `P-verification-co-authored` ratified in this PR are the moment public-tier principles cross over into stable-commitment status. The amendments are explicit and recorded; future amendments are not.
- **Three new principles ship with this ADR**: `P-protocol-not-product`, `P-publisher-symmetry`, `P-runtime-non-interception`. The third is promoted from vision Non-Goal #2.
- **`P-tiers-insulate` is retired.** Its body is preserved per immutability; its frontmatter changes to `status: superseded; superseded-by: 0048`.

### Personas

- **`solo-engineer` and `platform-team` are retired.** Both personas assume a target audience the lead has explicitly deferred; their tier vocabulary is gone. Bodies preserved.
- **`solo-with-agents` and `onboarding-agent` are amended.** Tier vocabulary replaced with depth/aspect/recipe; references to deferred specs adjusted.
- **`acme-publisher` is added.** A persona was missing for the third-party publisher authoring contract bundles against the substrate's grammar.

### Self-hosting

- **The kanon repo's `.kanon/config.yaml` is rewritten in Phase 0.5** to opt into reference aspects via a publisher recipe with no privileged status. This commit lands BEFORE Phase A's `defaults:` deletion; the deletion is then a no-op for the kanon repo's behaviour.
- **`P-self-hosted-bootstrap` amends accordingly.** Self-hosting becomes the substrate's primary falsification probe, not a kit-shape demonstration. The principle's claim — "the kit uses itself to develop itself" — is preserved; the *configuration* by which it does so is no longer privileged.

### Migration

- **Clean break with explicit migration script.** `kanon-substrate==1.0.0a1` ships as a hard cut from `kanon-kit==0.3.x`. A `kanon migrate v0.3→v0.4` script exists, marked deprecated-on-arrival, deleted after the kanon repo migrates itself. The script's existence is acknowledged honestly: `P-self-hosted-bootstrap` makes a literal clean break impossible (the kit's own working tree is the first migration victim).

### Versioning

- **Kernel ships daily-alpha. Reference ships weekly. Dialect ships quarterly minimum, annual default.** A breaking dialect change is never a kernel release; it always cuts a new dialect spec. Substrate honours at least N-1 dialects (deprecation horizon = 4 quarters). Future ADRs (Phase 0) author the cadence policy in detail.

### Scope

- **Supersedes ADR-0012 in part.** The kit-shape framing in ADR-0012 (sections describing the kit as a curated bundle) is superseded. ADR-0012's aspect-model decision (aspects as the unit of opt-in discipline, depth-dialed) survives intact; that primitive is what the substrate composes over.
- **Does not supersede ADR-0026 or ADR-0028.** The capability registry (ADR-0026) and project-aspect namespacing (ADR-0028) are exactly the substrate primitives this ADR commits to. They survive verbatim; their semantics extend to the `acme-` plane.
- **No reverse compatibility with v0.3.x consumers.** There are no current consumers; the cost is zero. Any future fork of the v0.3.x line is its forker's responsibility.

## Config Impact

- `.kanon/config.yaml` schema bumps v3 → v4. Phase 0 ADR-0040 specifies the v4 shape (publisher-id field, recipe provenance, dialect-version pin). The kanon repo's own config rewrites in Phase 0.5; downstream consumers (none today) would migrate via the `kanon migrate` script.
- Top-level `manifest.yaml` `defaults:` and `files:` fields are removed. Phase A deletion.

## References

- [`docs/foundations/vision.md`](../foundations/vision.md) — rewritten in this PR; v0.1 body preserved as Historical Note linked to commit `7b7d8d4`.
- [`docs/foundations/de-opinionation.md`](../foundations/de-opinionation.md) — manifesto codifying the lead's framing; cited from vision.md.
- [`docs/foundations/principles/`](../foundations/principles/) — six tiered, three new, three amended, one retired in this PR.
- [`docs/foundations/personas/`](../foundations/personas/) — two amended, two retired, one new in this PR.
- [ADR-0012](0012-aspect-model.md) — aspect model; superseded in part (kit-shape framing) by this ADR; aspect-as-primitive decision survives.
- [ADR-0013](0013-vision-amendment-reference-automation.md) — prior vision amendment; preserved.
- [ADR-0015](0015-vision-amendment-aspect-identity.md) — prior vision amendment; preserved.
- [ADR-0026](0026-aspect-provides-and-generalised-requires.md) — capability registry; preserved verbatim; semantics extend to the `acme-` plane.
- [ADR-0028](0028-project-aspects.md) — project-aspect namespacing; preserved; the `acme-` plane it reserved is now in-scope, not deferred.
- [ADR-0032](0032-adr-immutability-gate.md) — ADR body immutability; this ADR extends the discipline to public-tier principles.
- Conversation log — five rounds of panel review and explicit lead ratification across rounds 4–5; not formally citable but referenced as design evidence.
