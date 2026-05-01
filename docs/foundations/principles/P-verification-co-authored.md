---
id: P-verification-co-authored
kind: technical
tier: public-protocol
status: accepted
date: 2026-04-22
---
# Verification is a co-authoritative source, not derived

## Statement

Tests, transcript fixtures, CI validators, and resolution-replay artifacts are not subordinate artifacts derived from specs. They are co-authoritative with specs. Specs state product intent; verification states observable behaviour. Both must agree, and when they disagree the disagreement is the bug.

## Rationale

Under the "specs are source, code is derived" frame (`P-specs-are-source`), the intuitive conclusion is that tests are also derived — compiled output from specs. That would be wrong. Python tests are authored by humans or agents in the same way specs are authored. Transcript fixtures capture observed agent behaviour that no spec fully predicts. Resolutions capture an agent's evidence-grounded reading of a contract against a specific repo. If verification were subordinate, a spec-authoring mistake could pass verification without anyone noticing (because verification was silently adjusted to match the broken spec). Giving verification its own authority channel prevents that failure mode.

## Implications

- The document authority hierarchy in `docs/sdd-method.md` has multiple tops: Specs, Verification fixtures, and (under the protocol-substrate commitment) Resolutions. None can be overridden by another without explicit commit.
- When a spec change breaks a fixture, the path forward is either (a) update the spec to match observed desired behaviour and re-run verification, or (b) fix the implementation so verification passes the new spec. Both directions are valid; neither is the "default answer."
- `kanon verify` does not rank spec-violations higher than fixture-violations. Both are equally release-blocking.
- Verification artifacts carry provenance (`validated-against:` for model version, `verified_by:` from spec invariants — see ADR-0005 and `docs/specs/invariant-ids.md`).

### Resolutions as co-authoritative evidence (added per ADR-0048)

- **A resolution is verification evidence**, not configuration. It captures *what an agent read in this repo* and *what invocation the agent identified as realizing the contract*. The kernel replays it; the contract authored it; the resolution stands as the third co-authoritative artifact.
- **Stale resolutions are verification failures**, not configuration drift. When evidence files change, the resolution's claim about what the contract resolves to in this repo is no longer evidence-grounded. Re-resolution is required; the kernel refuses to silently accept stale state.
- **Cross-publisher resolutions inherit the principle.** When a `kanon-` reference contract and an `acme-` contract both target the same surface, both resolutions stand as co-authoritative evidence. Disagreement between them is a bug to be diagnosed, not a precedence question for the substrate to resolve.

## Exceptions / Tensions

- When a test is explicitly a regression test for a fixed bug (not a spec invariant), it's implementation-authored and less spec-aligned. Those tests still count as verification but are not paired with spec-level invariants.
- Some specs have no mechanical fixture (prose invariants about readability, etc.). Those use `fixtures_deferred:` or are flagged as non-testable at the spec template level.
- LLM resolution semantic correctness is *outside the kernel's mechanical verification boundary* (per the verification-contract spec's INV-11 disclosure). A structurally valid resolution can still be semantically wrong; the verifier surfaces structural coherence, not semantic correctness. Human review and fidelity fixtures fill the remaining gap.

## Source

ADR-0004 of this project — the explicit amendment the user requested during v0.1 planning. Surfaced as a gap by the fair-adversary agent during the design synthesis round.

## Tier

This principle is **public-protocol** (per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md)). Publishers authoring `acme-` aspects can rely on the substrate honouring co-authoritativity of fixtures, validators, and resolutions. Body is immutable post-acceptance under the same discipline that protects ADR bodies (extended from ADR-0032 by ADR-0048). The amendment that added §"Resolutions as co-authoritative evidence" landed in the same PR that ratified the public-tier discipline; future amendments require dialect supersession.

## Historical Note

Pre-amendment body (without the §"Resolutions as co-authoritative evidence" section and without the LLM-semantic-correctness exception) is preserved at commit `ded4e77`. The amendment extended the principle's scope to resolution artifacts under the protocol-substrate commitment without altering the original specs/fixtures co-authoritativity claim.
