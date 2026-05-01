---
id: P-specs-are-source
kind: technical
tier: public-protocol
status: accepted
date: 2026-04-22
---
# Specs are the authoritative source; code and resolutions are derived

## Statement

In an AI-coded project, SDD artifacts (specs, ADRs, plans, design docs, verification fixtures, principles, contracts) are the authoritative source of truth. Generated code is a compiled artifact — non-deterministically compiled by an LLM, but still downstream of the artifacts that described what the code should do. Under the protocol-substrate commitment, runtime bindings (`.kanon/resolutions.yaml`) are also derived artifacts: they are produced by an LLM agent resolving a prose contract against the consumer's specific repo, and replayed mechanically by the kernel. The contract is the source; the resolution is downstream.

## Rationale

Humans in an AI-coded project read specs far more than they read code. The reviewer opens the spec diff, not the code diff. The auditor checks invariants against specs, not against Python. The new hire navigates via the spec tree, not via grep. If specs are the thing the humans read, specs must be the thing the humans author. Code follows.

This inverts the classical assumption that code is the truth and docs are documentation. Under the classical frame, more SDD layers is overhead. Under this frame, each SDD layer captures a different kind of authoritative knowledge no other layer can.

The protocol-substrate commitment extends the same logic one layer down. Runtime configuration was historically maintained imperatively (Makefiles, `package.json` scripts, hardcoded `_detect.py` rules). Under prose-as-code, runtime bindings are not user-maintained either: they are derived from prose contracts by agent resolution, with evidence citations and SHA-pinning. The contract is what humans review; the resolution is what the kernel replays.

## Implications

- The kit invests in SDD-layer tooling (spec-graph rename, spec-diff rendering, fidelity locks) at the expense of code-generation tooling.
- Review workflows optimise for reading spec and contract diffs first; code and resolution diffs are confirmatory.
- Non-determinism of LLM codegen is handled honestly (see `P-verification-co-authored` and ADR-0004) — code is not regenerated from specs mechanically; it is authored by agents reading specs and is re-validated by fixtures that live co-authoritative with the specs.

### Resolutions are derived (added per ADR-0048)

- **Resolutions are machine-only-owned, evidence-grounded, SHA-pinned cache artifacts** of an agent's interpretation of a prose contract against this repo's state. The contract — not the resolution — is authoritative.
- **Hand-editing `.kanon/resolutions.yaml` is forbidden.** Edits travel through re-resolution by an agent reading the same contract. The kernel may refuse hand-edited resolutions where detectable.
- **CI replays cached resolutions; it does not regenerate them.** The resolver runs only on developer machines. This preserves the property that the source-of-truth (the contract) is what humans review, while the derived artifact (the resolution) is what runs.
- **Stale-detection drives re-resolution, not reconciliation.** When evidence files change, the resolution is invalidated. The fix is to re-resolve from the contract, not to patch the resolution.

## Exceptions / Tensions

- Debugging a runtime bug still means stepping through the code. The spec doesn't help at the debugger level. The mitigation is invariant-to-failure traceability (per `docs/specs/invariant-ids.md`).
- For short-lived scripts and prototypes, the spec-first overhead exceeds the value. That's why low-depth aspect configurations have minimal spec layers. The principle applies where there's a spec layer at all.

## Source

Design synthesis conducted during v0.1 planning. The frame came from the user ("in the age where AI is writing code, having more stages is more beneficial since humans will not read the code but the SDD specs/files"). Adopted as the project's design stance in `docs/foundations/vision.md`.

## Tier

This principle is **public-protocol** (per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md)). Publishers authoring `acme-` aspects can rely on the substrate honouring the spec-source / code-derived inversion, including for runtime bindings. Body is immutable post-acceptance under the same discipline that protects ADR bodies (extended from ADR-0032 by ADR-0048). The amendment that added §"Resolutions are derived" landed in the same PR that ratified the public-tier discipline; future amendments require dialect supersession.

## Historical Note

Pre-amendment body (without the §"Resolutions are derived" section) is preserved at commit `ded4e77`. The amendment extended the principle's scope to runtime bindings under the protocol-substrate commitment without altering the original spec-source / code-derived inversion.
