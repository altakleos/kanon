---
id: acme-publisher
status: accepted
date: 2026-05-01
stresses:
  - P-protocol-not-product
  - P-publisher-symmetry
  - P-prose-is-code
  - aspects
  - aspect-provides
  - project-aspects
---
# Persona: acme- Publisher

**One sentence:** A third-party engineer or organization authoring a contract bundle for kanon — discipline aspects under the `acme-<name>-` namespace — to share with their team or publish for others, exercising the substrate as a substrate rather than as a kit.

## Context

A site-reliability engineer at a fintech, a platform-engineering lead at a regulated company, an OSS maintainer building reusable engineering discipline — the audience is whoever has authoring discipline they want to package as kanon-shaped contracts and ship under their own publisher namespace. They have read [`vision.md`](../vision.md) and [`de-opinionation.md`](../de-opinionation.md); they accept the substrate's bet that prose-as-code is the right packaging medium. They are *not* the substrate's maintainer; they have no privileged access to kernel internals.

They are sitting down on a Tuesday afternoon with a problem like "our compliance review process needs to be encoded so every commit reviews against the same checklist," or "our team has a particular release-discipline shape that doesn't match `kanon-release`," or "this kind of fidelity assertion would help us catch a class of agent failures we keep seeing." Their job is to produce an aspect bundle — a directory of prose contracts, manifests, and (optionally) Python validators — that resolves through the substrate identically to a `kanon-` reference aspect.

This persona did not exist under kit-shape; aspect authoring was implicitly the kit-author's job. Under the protocol-substrate commitment ([ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md)), the third-party publisher is a first-class user, and the substrate's published protocol commitments exist specifically to give them stable guarantees to author against.

## Goals with `kanon`

- Author a contract bundle (`acme-<name>-<aspect>`) following the substrate's dialect grammar, with the substrate honouring it identically to a `kanon-` reference aspect.
- Cite the substrate's public-tier principles by ID and dialect-version pin from the bundle's documentation, with confidence those principles will not silently change underneath the bundle.
- Ship a recipe (target-tree YAML) that opts a consumer into the bundle's aspects without the substrate having any opinion about which recipe is right.
- Publish the bundle to PyPI (or analogous registry) with a `kanon-dialect:` manifest pin, and have it resolve through the substrate when the consumer installs it.
- Validate the bundle against the substrate's grammar before publishing, via `kanon contracts validate <bundle-path>`.

## What stresses the substrate

- **Dialect-version conformance.** The publisher's manifest pins `kanon-dialect: 2026-XX-XX`; the substrate must refuse manifests pinning unknown dialects, must honour at least N-1 dialects with deprecation warnings, and must not silently coerce shapes between dialect versions.
- **Capability namespace collision.** When `acme-fintech-testing` declares `provides: [test-discipline]` in the same consumer that has `kanon-testing` enabled, the substrate's resolution rules (per `P-publisher-symmetry`) must produce a deterministic outcome the publisher can predict without reading kernel source.
- **Recipe authorship grammar.** Recipes are publisher-shipped target-tree YAML. The substrate must accept any conforming recipe regardless of which publisher authored it — `acme-fintech-default` and `kanon-reference-default` resolve through the same code path.
- **Validator entry-point stability.** Bundles whose aspects ship Python validators (per ADR-0028's in-process trust boundary) need the validator entry-point contract — `def check(target, errors, warnings) -> None` — to be stable across substrate versions. The publisher cannot author against private kernel symbols.
- **Cross-publisher resolution evidence.** When a consumer's resolutions cite evidence files under both `kanon-` and `acme-` aspect contracts, the resolution-replay engine treats both citations identically. Publisher attribution is recorded in `provenance:` but does not change replay semantics.
- **Documentation discoverability.** A would-be publisher reading `vision.md`, `de-opinionation.md`, the public-tier principles, the dialect spec, and the aspect-grammar reference must be able to ship their first bundle without reading kernel source. If they cannot, the substrate's public-protocol claim is incomplete.

## What does NOT stress the substrate

- Registry mechanics (a kanon-hosted index, content-trust signatures, "verified publisher" badges). The substrate is registry-agnostic; PyPI + naming convention is sufficient. (Per [`de-opinionation.md`](../de-opinionation.md) negative scope.)
- Trust delegation across publishers (e.g., "I trust `acme-fintech-` but not `acme-marketing-`"). Trust boundary is repo write-access, identical to a `Makefile`'s trust model. Consumers gate trust at install time.
- Cross-publisher recipe import grammar. A future ADR may add it; today, recipes are flat target-tree YAML the consumer copies from any publisher.

## Success when using `kanon`

- A first-time publisher reads `vision.md` + `de-opinionation.md` + the dialect spec + one example reference aspect, and ships a working `acme-<name>-<aspect>` bundle that passes `kanon contracts validate` on a Tuesday afternoon.
- The bundle's aspects resolve through the substrate identically to a `kanon-` reference aspect — same `kanon verify` exit codes, same fidelity replay behaviour (when the bundle declares `behavioural-verification`), same composition algebra under `surface:` and `before/after:`.
- The bundle's documentation cites public-tier principles by ID and dialect-version pin; future substrate releases honour those citations without breaking the bundle.
- A consumer running `pip install acme-<name>-<aspect>` and `kanon aspect add . acme-<name>-<aspect>` gets a working configuration with no kernel-side privilege over what `kanon-reference` aspects would have provided.
- When the substrate ships a new dialect, the bundle's existing manifest pins continue to work for the deprecation horizon; the publisher migrates at their own pace.
