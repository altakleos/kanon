---
id: P-publisher-symmetry
kind: technical
tier: public-protocol
status: accepted
date: 2026-05-01
---
# Publisher symmetry: kit-shipped, project-defined, and third-party aspects resolve identically

## Statement

The substrate treats aspects from all three publisher namespaces — `kanon-` (kit-shipped reference), `project-` (consumer-defined per [ADR-0028](../../decisions/0028-project-aspects.md)), and `acme-` (third-party publisher) — identically at every code path. Asymmetries between namespaces must be justified in writing or refactored to symmetry. A privilege that quietly accumulates for `kanon-` aspects is a violation of this principle, regardless of how small the privilege is.

## Rationale

The capability registry ([ADR-0026](../../decisions/0026-aspect-provides-and-generalised-requires.md)) defines substitutability through `provides:` capabilities. For substitutability to be real, the *substrate* must not distinguish publishers when resolving capability satisfaction, depth ranges, validator imports, scaffolded files, or marker injection. If the resolver fast-paths `kanon-testing` because it ships in the reference distribution, then a future `acme-strict-testing` declaring the same capability cannot truly substitute — it gets the slow path through which different bugs surface.

Publisher symmetry is what makes the substrate a *protocol*. Without it, the substrate is a kit pretending to admit extensions.

## Implications

- **`_load_aspect_registry()` unions all three sources symmetrically.** No source is loaded first or has implicit precedence. Collisions (two publishers declaring the same aspect name) fail at load time with a single explicit error citing both publishers.
- **Capability resolution is publisher-blind.** When two enabled aspects declare the same `provides:` capability, the substrate's resolution rule treats them symmetrically. Consumer-side `prefer:` directives or explicit `replaces:` declarations break the tie; the substrate does not pick a winner by namespace.
- **Validators load through the same import path.** Whether a validator module is shipped by `kanon-reference` or by an `acme-` publisher, `kanon verify` imports it the same way and trusts it the same way (per ADR-0028's documented in-process trust boundary).
- **Scaffolded files travel through the same pipeline.** No publisher gets a "kit-global" file privilege; the substrate's `_scaffold` engine does not differentiate file ownership by publisher.
- **CI gates the symmetry empirically.** A kit-author CI check builds the substrate without `kanon-reference` installed and runs the full kernel test suite; if any test fails because reference aspects are absent, the symmetry has been violated.
- **Documentation calls out symmetry violations as bugs.** A bug report describing "substrate does X for `kanon-` aspects but not `acme-`" is a P1 unless the asymmetry is explicitly justified by another principle (e.g., `P-protocol-not-product`'s carve-out for self-hosting demonstration).

## Exceptions / Tensions

- **Self-hosting demonstration.** The kanon repo opts into reference aspects to prove the substrate works end-to-end (per `P-self-hosted-bootstrap`). This is *consumer-side* opt-in, not substrate-side privilege. The substrate would treat any other publisher identically.
- **Recipes are publisher-shipped.** `kanon-reference` ships a recipe (`reference-default`) that opts the consumer into all seven reference aspects. An `acme-` publisher could ship its own recipe with the same mechanism; the substrate has no opinion about which recipe a consumer adopts.
- **Bare-name sugar (deprecation period).** Through the v0.4 deprecation horizon, bare-name CLI flags (`--aspects sdd:1`) sugar to `kanon-` for backward compatibility. This asymmetry is documented, time-bounded, and explicitly violates `P-publisher-symmetry` for the deprecation window only. After the horizon, bare names are rejected with a clear error.

## Source

Synthesized across rounds 3–5 of panel review during the protocol-commitment ratification. The architect's call: "the substrate must treat `acme-testing` and `kanon-testing` identically at every code path." Codified as a public-tier principle by [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md). The principle is part of the substrate's published protocol commitments; it is versioned with the dialect and immutable post-acceptance.
