---
status: accepted
date: 2026-04-22
---
# ADR-0004: Verification is a co-authoritative source, not compiled output

## Context

`agent-sdd`'s design stance is "specs are source; code is compiled output" (see `docs/foundations/vision.md`). This frame implies authoritative knowledge flows from specs downward: specs → implementation. Under the frame, code is a cached artifact the agent regenerates when the spec changes.

But tests and transcript fixtures cannot be derived from specs deterministically. Python `pytest` files are authored, not compiled. Transcript fixtures capture observed agent behaviour, not spec-derived invariants. If specs are source and code is compiled output, where do tests sit?

The fair-adversary agent in the design round identified this as a structural gap. The user explicitly requested resolution as an ADR.

## Decision

**Verification is a co-authoritative source, not compiled output.** The document-authority hierarchy in `docs/development-process.md` has two tops, not one:

- **Specs** state product intent — what the system must do from the user's perspective.
- **Verification** states observable behaviour — what the system in fact does.

Both must agree. Neither is subordinate to the other. When they disagree, the disagreement is the bug, and the fix is either (a) update the spec to reflect the new intent and re-run verification, or (b) update the implementation to match the spec and re-run verification. Verification can fail a spec change (the new spec invariant isn't actually realised); a spec can fail a verification change (the new observable behaviour isn't actually desired). Both directions are valid.

Concretely:

- `docs/specs/*.md` carry `fixtures:` frontmatter naming the verification artifacts that prove each invariant.
- Verification artifacts (pytest files, transcript fixtures) carry inverse references via `verified_by:` on spec invariants (convention introduced optionally in v0.1, mandatory in a follow-on per `specs/invariant-ids.md`).
- `ci/check_foundations.py` validates that every `fixtures:` entry resolves.
- When a model-version change would invalidate a fixture (see ADR-0005), `agent-sdd verify` flags the inconsistency — it does not silently prefer one source over the other.

## Alternatives Considered

1. **Treat tests as compiled output; derive them from specs.** Would require a deterministic spec→test compiler. None exists for prose specs. LLM-based derivation is non-deterministic and loses coverage that humans intentionally author. Rejected.
2. **Treat tests as implementation; subordinate to specs.** Matches classical methodology but loses the fact that tests often catch behaviours specs didn't anticipate. Rejected.
3. **Two-tops hierarchy** (chosen). Honest about the fact that Python tests are authored prose-as-code in the same sense that specs are authored prose-as-code.

## Consequences

- `docs/development-process.md` § Document Authority is updated in Phase B to list Verification as a peer of Specs at the top of the authority chain.
- Review workflow: reviewer reads both the spec diff AND the verification diff; either can reject the other.
- When spec/verification disagreement is discovered, the authoring commit that introduced the gap is the defect, regardless of which side "caused" it.

## Config Impact

None at the Python/config level. The consequence propagates through prose: process doc authority list, spec template `fixtures:` field, verification artifacts' `verified_by:` field.

## References

- Fair-adversary agent report (v0.1 design synthesis, second round).
- User confirmation during v0.1 scoping.
