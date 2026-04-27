---
status: accepted (lite)
date: 2026-04-27
weight: lite
protocols: [verify-triage]
---
# ADR-0029: Verification-contract carve-out for fidelity-fixture replay

## Decision

`docs/specs/verification-contract.md` gains INV-10 — a single, narrowly-scoped carve-out from INV-9's "does not execute code" rule. When and only when an aspect declaring the `behavioural-verification` capability (per ADR-0026) is enabled at depth ≥ 1 — including the kit-shipped `kanon-fidelity` aspect, when it ships — `kanon verify` MAY load committed `.kanon/fidelity/<protocol>.dogfood.md` capture files and run lexical assertions over them (`forbidden_phrases`, `required_one_of`, `required_all_of` over named-actor turns). The carve-out is text-only, read-only-against-committed-files, aspect-gated, and adds no measurable latency to the default flow. Tier-2 (workstation capture) and Tier-3 (live-LLM nightly) are explicitly out of scope and require their own ADRs.

## Why

INV-9 ("does not execute code") is correct for the default flow but, as written, forecloses every behavioural-verification proposal — including the cheapest, lowest-risk form (committed-text-against-committed-text). The Round-2 verifier panelist surfaced this as a hard architectural blocker that Round-1 had not noticed: every EH-V1 / EH-V2 / EH-V5 candidate would have been in spec-conflict from day 1.

Sensei's transcript-fixture pattern (`tests/transcripts/`) demonstrates that lexical replay catches a class of prose-conformance failures that structural verify cannot see. Kanon commit `b9524aa9` ("fix: enforce worktree usage with audit sentence") is the in-tree witness: an audit-sentence enforcement pattern was added to a protocol with no mechanism to verify it. Tier-1 replay closes that loop without violating INV-9's spirit (no agency invocation, no model call, no test-runner invocation).

The carve-out is bounded so the kit's "no harness adapters, no session daemons, no tool-call filters" stance from `docs/foundations/vision.md:35` is preserved: kanon does not intercept agent actions at runtime; it only inspects what the consumer chose to commit.

## Alternative

Leave INV-9 unmodified and ship behavioural verification as project-aspect machinery only (each consumer forks the kit). Rejected: forecloses kit-shipped fixture authoring, duplicates effort across every consumer who wants the pattern, relegates a battle-tested sensei pattern to "copy-paste from sensei." The cost-distribution argument from ADR-0028 alternative #1 applies one layer up — the kit absorbs the small spec amendment so consumers don't each pay for one.

A second alternative — **expand the carve-out to authorise Tier-2 and Tier-3 in the same ADR** — was rejected as scope-creep. Tier-2 introduces a new CLI subcommand (`kanon transcripts capture`) and a workstation-evidence-as-CI-artifact pattern that warrants its own decision record. Tier-3 introduces a recurring CI cost on consumers (paid LLM nightly) that the kit should not impose; document the recipe and let consumers operate it.

## References

- [`docs/specs/verification-contract.md`](../specs/verification-contract.md) — INV-9 (default-flow rule) and INV-10 (carve-out).
- [ADR-0026](0026-aspect-provides-and-generalised-requires.md) — `provides:` capability registry; this ADR's carve-out is gated on the `behavioural-verification` capability flag.
- [ADR-0028](0028-project-aspects.md) — project-aspect namespace; consumers MAY ship a `project-fidelity-*` aspect declaring the same capability and inherit the carve-out.
- [ADR-0005](0005-model-version-compatibility-contract.md) — `validated-against:` model-version metadata for fixtures (will apply to fidelity captures).
