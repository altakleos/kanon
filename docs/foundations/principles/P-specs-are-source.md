---
id: P-specs-are-source
kind: technical
status: accepted
date: 2026-04-22
---
# Specs are the authoritative source; code is compiled output

## Statement

In an AI-coded project, SDD artifacts (specs, ADRs, plans, design docs, verification fixtures) are the authoritative source of truth. Generated code is a compiled artifact — non-deterministically compiled by an LLM, but still downstream of the artifacts that described what the code should do.

## Rationale

Humans in an AI-coded project read specs far more than they read code. The reviewer opens the spec diff, not the code diff. The auditor checks invariants against specs, not against Python. The new hire navigates via the spec tree, not via grep. If specs are the thing the humans read, specs must be the thing the humans author. Code follows.

This inverts the classical assumption that code is the truth and docs are documentation. Under the classical frame, more SDD layers is overhead. Under this frame, each SDD layer captures a different kind of authoritative knowledge no other layer can.

## Implications

- The kit invests in SDD-layer tooling (spec-graph rename, spec-diff rendering, fidelity locks — several deferred to v0.2+) at the expense of code-generation tooling.
- Review workflows optimise for reading spec diffs first; code diffs are confirmatory.
- `ci/check_template_consistency.py` enforces byte-equality between the repo's canonical SDD artifacts and the tier-3 template, because the artifacts *are* the source.
- Non-determinism of LLM codegen is handled honestly (see `P-verification-co-authored.md` and ADR-0004) — code is not regenerated from specs mechanically; it is authored by agents reading specs and is re-validated by fixtures that live co-authoritative with the specs.

## Exceptions / Tensions

- Debugging a runtime bug still means stepping through the code. The spec doesn't help at the debugger level. The mitigation is invariant-to-failure traceability (deferred to v0.2, see `docs/specs/invariant-ids.md`).
- For short-lived scripts and prototypes (tier-0), the spec-first overhead exceeds the value. That's why tier-0 has no specs directory. The principle applies at tier-2+ where there's a spec layer at all.

## Source

Design synthesis conducted during v0.1 planning. The frame came from the user ("in the age where AI is writing code, having more stages is more beneficial since humans will not read the code but the SDD specs/files"). Adopted as the project's design stance in `docs/foundations/vision.md`.
