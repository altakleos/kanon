# Principles

Cross-cutting stances this project commits to. One principle per file. See [`../README.md`](../README.md) § Sub-namespaces for the `kind:` taxonomy (`pedagogical` / `technical` / `product`).

## Tiering

Per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md), kanon's principles split into two tiers:

- **Public-protocol** (`tier: public-protocol`): the substrate publishes these as stable protocol commitments. They are versioned with the dialect, citable by `acme-` publishers in their own documentation, and immutable post-acceptance under the same discipline that protects ADR bodies (per [ADR-0032](../../decisions/0032-adr-immutability-gate.md), extended by ADR-0048). Future amendments require dialect supersession, not in-place edits. Publishers may rely on the substrate honouring these principles in code paths.
- **Kit-author-internal** (`tier: kit-author-internal`): these govern how kanon develops kanon. They are not part of the substrate's published protocol; the substrate does not enforce them on consumer repos; publishers do not need to honour them. Body amendments are kit-author concerns and do not require dialect supersession.

> **Kit-author scope, refined.** The kit-shipped consumer-facing starter template at [`src/kanon_reference/aspects/kanon_sdd/files/docs/foundations/principles/README.md`](../../../src/kanon_reference/aspects/kanon_sdd/files/docs/foundations/principles/README.md) ships an empty index. Consumers own their own `docs/foundations/principles/` directory entirely; they never receive the kit's `P-*.md` files as scaffolded prose. However, **the public-protocol tier of this catalog is part of the substrate's published spec surface** — `acme-` publishers and consumer projects may cite the public-tier principles by ID and dialect-version pin from their own documentation without copying the bodies. Kit-author-internal principles remain entirely internal.

## Public protocol commitments

Six principles the substrate publishes as stable commitments:

| ID | Title | Kind |
|---|---|---|
| [P-prose-is-code](P-prose-is-code.md) | Prose read by an LLM runtime is code | technical |
| [P-protocol-not-product](P-protocol-not-product.md) | kanon ships a protocol, not a discipline product | technical |
| [P-publisher-symmetry](P-publisher-symmetry.md) | Kit-shipped, project-defined, and third-party aspects resolve identically | technical |
| [P-runtime-non-interception](P-runtime-non-interception.md) | The substrate does not intercept LLM-agent behaviour at runtime | technical |
| [P-specs-are-source](P-specs-are-source.md) | Specs are the authoritative source; code and resolutions are derived | technical |
| [P-verification-co-authored](P-verification-co-authored.md) | Verification is a co-authoritative source, not derived | technical |

## Kit-author internal

Two principles governing how kanon develops kanon:

| ID | Title | Kind |
|---|---|---|
| [P-self-hosted-bootstrap](P-self-hosted-bootstrap.md) | The kit develops itself as a peer consumer | technical |
| [P-cross-link-dont-duplicate](P-cross-link-dont-duplicate.md) | Cross-link artifacts; never duplicate content | technical |

## Superseded

| ID | Title | Superseded by |
|---|---|---|
| [P-tiers-insulate](P-tiers-insulate.md) | Tiers insulate consumer experience, not producer experience | [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) |

The "tier" vocabulary this principle codified was a kit-shape concern; under the protocol-substrate commitment, tiers are gone (depths are per-aspect dials, not a global axis). Body preserved per immutability discipline; the file remains as historical record.
