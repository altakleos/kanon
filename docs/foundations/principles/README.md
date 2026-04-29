# Principles

Cross-cutting stances this project commits to. One principle per file. See [`../README.md`](../README.md) § Sub-namespaces for the `kind:` taxonomy (`pedagogical` / `technical` / `product`).

> **Kit-author scope.** This catalog lists kanon's *own* internal principles. They are **not** scaffolded into downstream consumers by `kanon init`. The kit-shipped consumer-facing starter template lives at [`src/kanon/kit/aspects/kanon-sdd/files/docs/foundations/principles/README.md`](../../../src/kanon/kit/aspects/kanon-sdd/files/docs/foundations/principles/README.md) and ships an empty index. Consumers own their own `docs/foundations/principles/` directory entirely; they never receive the kit's `P-*.md` files.

## Index

| ID | Title | Kind |
|---|---|---|
| [P-prose-is-code](P-prose-is-code.md) | Prose read by an LLM runtime is code | technical |
| [P-specs-are-source](P-specs-are-source.md) | Specs are the authoritative source; code is compiled output | technical |
| [P-tiers-insulate](P-tiers-insulate.md) | Tiers insulate consumer experience, not producer experience | product |
| [P-self-hosted-bootstrap](P-self-hosted-bootstrap.md) | The kit uses itself to develop itself | technical |
| [P-cross-link-dont-duplicate](P-cross-link-dont-duplicate.md) | Cross-link artifacts; never duplicate content | technical |
| [P-verification-co-authored](P-verification-co-authored.md) | Verification is a co-authoritative source, not derived | technical |
