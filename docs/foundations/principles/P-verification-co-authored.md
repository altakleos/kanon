---
id: P-verification-co-authored
kind: technical
status: accepted
date: 2026-04-22
---
# Verification is a co-authoritative source, not derived

## Statement

Tests, transcript fixtures, and CI validators are not subordinate artifacts derived from specs. They are co-authoritative with specs. Specs state product intent; verification states observable behaviour. Both must agree, and when they disagree the disagreement is the bug.

## Rationale

Under the "specs are source, code is compiled" frame (P-specs-are-source), the intuitive conclusion is that tests are also compiled output — derived from specs. That would be wrong. Python tests are authored by humans or agents in the same way specs are authored. Transcript fixtures capture observed agent behaviour that no spec fully predicts. If verification were subordinate, a spec-authoring mistake could pass verification without anyone noticing (because verification was silently adjusted to match the broken spec). Giving verification its own authority channel prevents that failure mode.

## Implications

- The document authority hierarchy in `docs/sdd-method.md` has two tops: Specs and Verification. Both sit at the top of the chain; neither can be overridden by the other without explicit commit.
- When a spec change breaks a fixture, the path forward is either (a) update the spec to match observed desired behaviour and re-run verification, or (b) fix the implementation so verification passes the new spec. Both directions are valid; neither is the "default answer."
- `kanon verify` does not rank spec-violations higher than fixture-violations. Both are equally release-blocking.
- Verification artifacts carry provenance (`validated-against:` for model version, `verified_by:` from spec invariants — see ADR-0005 and deferred spec `invariant-ids.md`).

## Exceptions / Tensions

- When a test is explicitly a regression test for a fixed bug (not a spec invariant), it's implementation-authored and less spec-aligned. Those tests still count as verification but are not paired with spec-level invariants.
- Some specs have no mechanical fixture (prose invariants about readability, etc.). Those use `fixtures_deferred:` or are flagged as non-testable at the spec template level.

## Source

ADR-0004 of this project — the explicit amendment the user requested during v0.1 planning. Surfaced as a gap by the fair-adversary agent during the design synthesis round.
