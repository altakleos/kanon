---
status: accepted
date: 2026-05-01
---
# ADR-0042: Verification scope-of-exit-zero — the canonical public claim

## Context

`kanon verify` is the substrate's most visible CLI surface. Its exit code is what consumers, CI systems, and `acme-` publishers will read as the substrate's certification of consumer-repo health. Without a precise, public, citable claim about what exit-0 means — and equally importantly, what it does NOT mean — consumers will read it as a correctness endorsement, and the substrate will silently inherit a warranty it cannot honour.

[ADR-0048](0048-kanon-as-protocol-substrate.md)'s public-tier principle commitment included the exit-zero scope boundary, but only in passing. [PR #53](https://github.com/altakleos/kanon/pull/53) added INV-11 ("Exit-zero scope boundary") to [`docs/specs/verification-contract.md`](../specs/verification-contract.md) at the spec level, ratifying the structural invariant the kernel enforces. Neither artifact ratifies the *public claim wording* — the prose the substrate uses across CLI help text, README, error messages, and `acme-` publisher onboarding documentation.

Round-5 verifier identified the disproportionate weight of this claim: consumers read exit codes as endorsements; the substrate must explicitly disclaim or own the endorsement. Without ADR-immutability protecting the wording, the spec INV alone could drift across releases — a hostile (or hasty) substrate version could quietly weaken the disclaimer; a future contributor could narrow the scope without realising the public commitment they were breaking.

This ADR ratifies the wording as a stable protocol commitment under [ADR-0032](0032-adr-immutability-gate.md) (extended to ADR-bodies-of-this-kind by [ADR-0048](0048-kanon-as-protocol-substrate.md)). The canonical text below is what the substrate's surfaces use; it is what publishers cite; it is what future substrate releases honour.

## Decision

Three numbered claims:

### 1. The canonical exit-zero wording

`kanon verify` exit-0 means: the consumer repo conforms to the structural and behavioural contracts expressed in the discipline aspects the consumer has explicitly enabled, at the depths the consumer has declared.

It MUST NOT be interpreted as — and the substrate MUST NOT represent it as:

- a signal that the consumer's repository follows good engineering practices beyond what the enabled aspects define;
- a correctness or quality endorsement of any prose, protocol, or code in the consumer's tree;
- a guarantee that the consumer's declared agent will comply with the enabled protocols at runtime — exit-0 is a static structural check, not a runtime behavioural guarantee;
- confirmation that resolution-replay invocations are semantically correct realizations of their contracts. Resolutions are checked for *structural* coherence (per [`docs/specs/resolutions.md`](../specs/resolutions.md)), not for semantic correctness; the agent's choice of invocation is the resolution publisher's responsibility, not the substrate's.

This wording is canonical. CLI help text, README, error messages, `acme-` publisher onboarding documentation, and any other consumer-facing surface where the substrate states what `kanon verify` certifies MUST use this wording verbatim or by direct citation. Translations into other languages MUST preserve the disclaimer's structure (positive claim followed by four explicit MUST-NOTs).

### 2. Cross-publisher symmetry

The exit-zero claim applies identically across all aspect namespaces — `kanon-`, `project-`, `acme-` — without warranty exemption. A `kanon-testing` aspect from `kanon-reference` and a hypothetical `acme-strict-testing` aspect verify under identical rules; their conformance failures surface identically; their resolutions are validated against identical invariants. The substrate does NOT claim more (or less) for kit-shipped aspects than for third-party aspects.

This is a downstream consequence of [`P-publisher-symmetry`](../foundations/principles/P-publisher-symmetry.md): the exit-code surface is one of the code paths where namespace asymmetry would be a bug.

### 3. Stability across substrate releases

The canonical wording in §1 is immutable post-acceptance under [ADR-0032](0032-adr-immutability-gate.md)'s ADR body immutability discipline. Future substrate releases honour the wording verbatim across kernel-cadence and dialect-cadence updates. If the wording must change to reflect a substantive substrate evolution, the change ships as a superseding ADR — not as a quiet edit to spec or CLI source.

This protects publishers: an `acme-X` publisher authoring against the substrate's exit-zero claim today can rely on the same claim being honoured by every future substrate release until a superseding ADR is published with explicit migration guidance.

## Alternatives Considered

1. **Don't ratify publicly; leave the disclaimer in INV-11 only.** Spec invariants govern kernel behaviour but are not part of the public-tier protocol commitment surface (only public-tier principles are, per ADR-0048). **Rejected.** The exit-zero claim is *the* most-cited part of the substrate's public contract; consumers reference exit codes in CI configs, runbooks, and PR review processes. Leaving it spec-only means publishers and consumers reverse-engineer the claim from observed behaviour, which is exactly what this ADR exists to prevent.

2. **Ratify in `vision.md` instead of a new ADR.** The vision already mentions exit-zero scope; expand it there. **Rejected.** Vision is descriptive, not normative. The exit-zero claim is a precise, citable, structural commitment that needs an ADR's stability discipline. Vision can cite ADR-0042; it cannot replace it.

3. **Ratify per-aspect-spec.** Each aspect spec carries its own claim about what its contracts mean for `kanon verify` exit-0. **Rejected.** Aspect specs evolve at publisher cadence; the exit-zero claim is substrate-wide and substrate-stable. Per-aspect ratification would let claims drift across publishers and re-introduce the warranty-by-namespace asymmetry this ADR explicitly forbids.

4. **Defer to publisher contracts.** Each publisher specifies what its contracts claim; the substrate makes no global claim. **Rejected.** This creates the worst case: consumers read `kanon verify` exit-0 and assume *some* universal meaning; publishers each define a different one; cross-publisher composition produces incoherent claims. The substrate must be the canonical source for what exit-0 universally means; publishers narrow the claim within the universal frame.

## Consequences

### Substrate-side

- **`kanon verify --help` text gains the canonical wording** (Phase A). The wording in §1 is what `--help` prints; the disclaimer is part of every invocation's discoverable interface.
- **Error messages on `kanon verify` failures cite the canonical wording** where relevant (Phase A). For example: "verify failed: <reason>. Note: exit-zero certifies conformance to enabled aspects only — see ADR-0042 for the full claim."
- **The verification-contract spec amendment** (in this PR): a cross-reference paragraph pointing at ADR-0042. INV-11's body is unchanged; the spec gains a citation that fixes the wording's home.
- **The substrate's own README** (next major rewrite, separate plan) uses the canonical wording in its description of `kanon verify`.

### Publisher-side

- **`acme-` publishers can cite ADR-0042 by ID and dialect-version pin** when documenting what their bundles claim about consumer conformance. Publisher onboarding documentation (Phase B/C) walks new publishers through the citation pattern.
- **Bundle-level documentation MUST NOT broaden the substrate's exit-zero claim**. A publisher cannot represent "verify exit-0 means our compliance discipline is satisfied" — they can represent "verify exit-0 means the consumer enabled our compliance contracts and they pass at the structural level." The narrower claim is the substrate's; publishers preserve it.

### Out of scope (deferred)

- **Distribution boundary mechanics** — ADR-0043.
- **Substrate self-conformance specifics** — ADR-0044.
- **De-opinionation transition** — ADR-0045.
- **Per-publisher conformance test framework** — Phase B/C territory; the substrate ratifies the public claim, not the test framework around it.
- **Translation policy for non-English consumer surfaces** — Phase B/C; the wording's structure is preserved (positive claim + four MUST-NOTs); idiomatic translation is the consumer's responsibility.

## Config Impact

- **No config schema change.** ADR-0042 is normative scope-of-claim; `.kanon/config.yaml` is unaffected.
- **CLI help text** is the substrate's primary consumer-facing surface; Phase A's CLI work updates `kanon verify --help` to use the canonical wording.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (parent).
- [ADR-0032](0032-adr-immutability-gate.md) — ADR body immutability discipline; this ADR's wording is protected by it.
- [ADR-0039](0039-contract-resolution-model.md) — runtime-binding model; resolutions are subject to the structural-coherence claim in §1.
- [ADR-0041](0041-realization-shape-dialect-grammar.md) — realization-shape and dialect grammar; exit-zero validates against these structural specs.
- [`docs/specs/verification-contract.md`](../specs/verification-contract.md) — INV-11 (exit-zero scope boundary) — the spec-level invariant this ADR ratifies as a public commitment.
- [`docs/specs/resolutions.md`](../specs/resolutions.md) — the structural-coherence checks the wording cites.
- [`docs/foundations/principles/P-publisher-symmetry.md`](../foundations/principles/P-publisher-symmetry.md) — the principle driving §2 (cross-publisher symmetry).
