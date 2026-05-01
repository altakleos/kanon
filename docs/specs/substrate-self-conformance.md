---
status: accepted
date: 2026-05-01
design: "docs/design/kernel-reference-interface.md"
realizes:
  - P-self-hosted-bootstrap
  - P-protocol-not-product
  - P-publisher-symmetry
stressed_by:
  - acme-publisher
fixtures_deferred: "Phase A authors `ci/check_substrate_independence.py` (per ADR-0040 design) and the kanon-repo self-host CI integration. The substrate-self-conformance invariants below are the contract; tests and gates land in the implementation PR."
---
# Spec: Substrate self-conformance — independence + self-host + public CI signal

## Intent

Define the substrate's discipline for proving its own claim. The substrate commits to being a substrate, not a kit; the discipline below is the operational signal that proves the commitment.

Three commitments compose into one discipline:

- **Independence**: `kanon-substrate` runs without `kanon-reference`. Forever.
- **Self-host**: the kanon repo, opting into reference aspects via the publisher recipe, passes `kanon verify .` against itself.
- **Public CI signal**: the gates enforcing the above are publicly-readable; `acme-` publishers can replicate.

Per [ADR-0044](../decisions/0044-substrate-self-conformance.md), this spec carries the invariants the substrate's CI gates enforce.

## Invariants

<!-- INV-substrate-self-conformance-independence -->
1. **Substrate-independence.** `kanon-substrate`'s test suite passes when run in a clean Python environment with no `kanon-reference` installed and no `kanon.aspects` entry-points visible. This invariant is permanent — every kernel-version-bump commit on the substrate's main branch must satisfy it. Failure is P0; the kernel does not ship without independence green.

<!-- INV-substrate-self-conformance-self-host-passes -->
2. **Self-host passes.** The kanon repo (this repo) opts into reference aspects via the `kanon-reference`-shipped recipe and passes `kanon verify .` against itself on every kernel-version-bump commit. Self-host is the substrate's primary correctness probe under vision-led design; failures are P1.

<!-- INV-substrate-self-conformance-recipe-opt-in -->
3. **Self-host opt-in is recipe-mediated.** The kanon repo's `.kanon/config.yaml` declares aspects via a publisher recipe with `provenance:` recording attribution (per [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) self-host commitment and [ADR-0043](../decisions/0043-distribution-boundary-and-cadence.md) recipe artifact). No kernel-side carve-out treats the kanon repo specially; it opts in like any other consumer.

<!-- INV-substrate-self-conformance-gate-public -->
4. **Independence gate is publicly-readable.** The substrate's CI workflow runs `ci/check_substrate_independence.py` (per [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) design) on every PR and merge-to-main. Workflow logs are public; results visible to anyone reading the substrate's repo. Closed-source CI is a violation.

<!-- INV-substrate-self-conformance-replicable -->
5. **Independence gate is replicable.** The gate's algorithm is documented sufficient that any publisher (including `acme-` authors) can run it against their own bundles and claim substrate-conformance. Independence is not a private property of `kanon-substrate`; it's a published technique.

## Rationale

The five invariants together codify the substrate's "kernel-as-product, reference-as-demonstration" identity in operationally-checkable form. Without invariant 1 (independence), the de-opinionation commitment is words on paper. Without invariant 2 (self-host), the substrate's correctness has no falsification surface — the kanon repo IS the empirical universe under vision-led design. Without invariant 3 (recipe-mediated opt-in), the kanon repo would be a privileged consumer whose self-host claim doesn't apply to anyone else. Without invariant 4 (gate public), the substrate's "we don't depend on reference" is unfalsifiable. Without invariant 5 (replicable), `acme-` publishers can't claim conformance to the same standard the substrate holds itself to.

The discipline is opinionated by design. It costs the substrate iteration speed (every kernel commit gates on independence + self-host) in exchange for a credible, verifiable claim. Round-5 panel: this is the trade vision-led design must accept.

## Out of Scope

- **The CI gate implementation.** Phase A authors per [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) design.
- **`acme-` publisher conformance test framework.** Phase B/C; this spec specifies what the substrate's gate checks, not the publisher-facing framework around it.
- **Multi-substrate-version testing.** Future ADR territory if a real consumer hits the deprecation horizon.
- **Performance benchmarks for independence-vs-with-reference.** This spec specifies correctness, not performance; benchmarks are out of scope.

## Decisions

- [ADR-0044](../decisions/0044-substrate-self-conformance.md) — substrate self-conformance discipline (this spec's parent).
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment.
- [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) — kernel/reference runtime interface; the independence-invariant origin.
- [ADR-0043](../decisions/0043-distribution-boundary-and-cadence.md) — distribution boundary + recipe artifact; the recipe-mediated opt-in mechanism.
- [ADR-0042](../decisions/0042-verification-scope-of-exit-zero.md) — verification scope-of-exit-zero; complementary discipline (consumer-facing claim).
