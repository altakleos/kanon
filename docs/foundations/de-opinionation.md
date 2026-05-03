---
status: accepted
date: 2026-05-01
---
# De-opinionation: kanon as a protocol substrate, not a discipline curator

This document codifies the lead's framing of kanon's identity. It is neither an ADR (the ADR — [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — *ratifies* the commitment) nor a principle (principles are normative stances; this is a strategy commitment). It explains why kanon refuses to bundle defaults, what de-opinionation does and does not mean, and what the substrate explicitly will not absorb. Read it after `vision.md`.

## Prose is the new source

kanon's foundational bet has been the same since the first commit: **prose consumed by an LLM agent is the new source of truth**. Specs, ADRs, plans, protocols, contracts — these are not documentation describing code that exists somewhere else. They are the authoritative artifacts. Code is a downstream artifact of prose authored to instruct an agent.

Every other choice in the substrate's design is a downstream consequence of this bet: the cross-harness shim registry exists because the prose has to reach the agent regardless of harness; the aspect model exists because disciplines need to compose without overwriting each other's prose; the fidelity replay engine exists because prose-as-code needs an evidence layer that catches when the agent did not in fact obey.

The substrate commits to this bet without hedging. If frontier LLMs cannot reliably resolve prose contracts into evidence-grounded runtime bindings, the substrate is reducible to a fancy Makefile with version-pinning — and the project would have been wrong to ship. Every architectural decision pushes the bet harder, not softer.

## The kit was a prototype against our DNA

v0.1 through v0.3 prototyped kanon as a *kit* — a curated bundle of opinionated aspects shipped through a single pip wheel and auto-enabled by `kanon init` profiles. The kit shape proved out three load-bearing properties: the aspect model, the cross-harness shim registry, and self-hosting. Without the kit, none of those would have been demonstrable.

But the kit shape was incompatible with the founding bet. A kit privileges its own opinions; a substrate publishes a grammar over which any opinions compose. The kit's `defaults:` block (auto-enable five aspects) made the substitutability promise of the capability registry honour-system-only: every privilege the kit kept made the eventual substrate transition more expensive. The longer the kit ran, the more lock-in accumulated.

The protocol commitment is not a redirection — it is the path the project always was reaching toward. The kit was useful; it was not the destination. v0.4 retires the kit shape and ratifies the substrate.

## What de-opinionation means

De-opinionation operates at one specific layer: **the substrate makes no assumption about which disciplines a consumer adopts.** Specifically:

- **Audience de-opinionation** (committed): the substrate has no `defaults:`. `kanon init` enables nothing. Reference aspects are de-installable. Recipes (the path to a starter set) are publisher-shipped target-tree YAML, not a kernel feature. A consumer who installs only `kanon-core` and runs `kanon init` gets a bare scaffold and a clear next-step prompt. They choose what discipline to adopt.

- **Protocol opinionation, retained**: the substrate IS opinionated about contract grammar, dialect semantics, capability symmetry, and the public principle set. These are not user choices — they are the publisher-facing protocol. A would-be `acme-X` author relies on the substrate's published guarantees; without them, every authoring decision is reverse-engineered from observed behaviour.

The two are different axes. Conflating them produces the false dichotomy "either kanon dictates everything or kanon dictates nothing." The substrate dictates neither: it dictates *the protocol over which dictation happens.*

Concretely:
- The substrate is opinionated that contracts are prose. It is de-opinionated about what disciplines those contracts express.
- The substrate is opinionated that resolutions are machine-only-owned and evidence-grounded. It is de-opinionated about which evidence files a publisher cites.
- The substrate is opinionated that the `behavioural-verification` capability gates fidelity replay. It is de-opinionated about which publisher provides that capability.

## What the substrate refuses

Three normative refusals, drawn from prior-art lessons (Markdown's refusal to standardize syntax extensions, Plan 9's refusal to absorb POSIX, Scheme's refusal to accumulate features). The substrate commits to these as part of the public-protocol surface.

1. **The substrate SHALL NOT acquire a runtime component that intercepts or validates LLM-agent behaviour.** Prose gates are enforced by agent compliance, observable from transcripts. No daemon, no hook, no session supervisor compensates for non-compliant agents. (Codified as [`P-runtime-non-interception`](principles/P-runtime-non-interception.md).)

2. **The substrate SHALL NOT define a machine-parseable schema for `AGENTS.md` prose, protocol prose, or principle prose bodies.** Manifests are machine-parsed; the substrate's human/agent prose surface is read, not validated against a schema. (Principles carry a stable `id:` frontmatter field for citation purposes; that is identity, not schema. `realization-shape:` schemas exist at the per-contract artifact level; they govern contract structure, not prose content.)

3. **The substrate SHALL NOT ship code-generation tooling that derives code from specs.** Agents read specs and write code. The substrate does not close that loop mechanically; closing it would make specs documentation again, contradicting [`P-specs-are-source`](principles/P-specs-are-source.md).

These are stated negatively because the prior art is clear: every protocol that lasted 20+ years had explicit refusals built into its governance culture before it had a community. CommonMark's refusal to standardize until consensus emerged, robots.txt's refusal to absorb authentication, Conventional Commits' refusal to define a custom-type taxonomy — each survived because the boundary was committed to upfront. The substrate adopts the discipline.

## Self-hosting as falsification

Under demand-led design, self-hosting is dogfooding — the team uses the thing so it feels the user's pain. Under vision-led design with no current external consumers, self-hosting is categorically different: **it is the only falsification surface available.**

The kanon repo is not a user sample. It is the entire empirical universe. If `kanon verify .` cannot pass on the kanon repo, the substrate has failed its one controlled experiment. If a substrate feature cannot be exercised by the kanon repo's own state, the feature is speculative and must not ship until self-host can falsify it.

This elevates self-hosting from a quality practice to an epistemological requirement. The substrate's primary correctness probes are layered:

- **P1 — self-host-from-clone:** the kanon repo cannot self-host on the latest substrate from a fresh clone with explicit opt-in. Failure means the substrate cannot run on its own evidence; halt before any other probe matters.
- **P2 — substrate-determinism:** two `kanon verify` runs on the same SHA must produce byte-equal JSON. Failure means the verification layer is non-deterministic; results from any other probe become uninterpretable.
- **P0 — resolution-determinism (Tier-2, deferred):** two clean LLM resolutions of the same `(contract, model, inputs)` must agree. Failure falsifies the late-binding premise. Wired only when Tier-2 resolver infrastructure exists.

P1 and P2 fire on the substrate's own evidence with no LLM, no consumers, no Tier-2 infrastructure.

[`P-self-hosted-bootstrap`](principles/P-self-hosted-bootstrap.md) codifies the technical discipline. This document codifies the epistemological framing. The principle says *how* to self-host; this document says *why* self-host is load-bearing in the absence of consumers.

## What this commits us to

- **The first non-kanon publisher is the point of no return.** Once an `acme-X` ships and a downstream consumer pins it, the substrate cannot revert without breaking that consumer. Today, with zero consumers, retreat is a CHANGELOG note. The protocol commitment is being made now precisely because the commitment is reversible *now* and will not be reversible *then*.

- **The cost of being right alone is patience.** Vision-led architecture has no demand-pull correction signal. The substrate manufactures correction signal through self-host probes, fidelity fixtures, and the eventual `acme-` author's experience. None of these are as fast as a frustrated user. The lead accepts this cost knowingly.

- **The substrate refuses to bundle defaults that would re-establish kit-shape behaviour through a side door.** A "recommended" meta-aspect that auto-enables five reference aspects is the kit's `defaults:` wearing a wig. The substrate has neither.

- **The substrate's identity is the protocol, not the reference.** When `kanon-sdd` and `acme-strict-sdd` both ship, the substrate has no opinion about which is right. Both resolve through the same code path; both can be cited in `requires:` predicates; both pass or fail `kanon verify` by the same rules. The kit-author's reference implementations are demonstrations the substrate's grammar can be implemented well — they are not the substrate's product.

## What this is not

- **This is not a retreat from opinion.** The substrate is heavily opinionated about prose-as-code, runtime-non-interception, publisher-symmetry, and the public principle set. These opinions are stronger now, not weaker.
- **This is not a deferral of audience.** The lead has explicitly named the audience as "vision-led with no current external consumers." That is a positive commitment, not a deferred decision. Future plans may resurrect the retired `solo-engineer` and `platform-team` personas under protocol-mode framing if their audiences become real.
- **This is not a promise of `acme-` ecosystem adoption.** The substrate enables it; it does not predict it. Success at v1.0 is the substrate working, the dialect cadence holding, and the self-host probes staying green. External adoption is welcome and unrequired.

## References

- [`vision.md`](vision.md) — what kanon is and is not
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — the decision this document codifies
- [`principles/P-prose-is-code.md`](principles/P-prose-is-code.md) — the founding axiom
- [`principles/P-protocol-not-product.md`](principles/P-protocol-not-product.md) — the substrate-not-curator commitment
- [`principles/P-publisher-symmetry.md`](principles/P-publisher-symmetry.md) — the namespace-equal-treatment commitment
- [`principles/P-runtime-non-interception.md`](principles/P-runtime-non-interception.md) — the no-runtime-supervisor commitment
- [`principles/P-self-hosted-bootstrap.md`](principles/P-self-hosted-bootstrap.md) — the self-hosting discipline
