---
status: accepted
date: 2026-04-22
---
# ADR-0007: Status taxonomy — adds `deferred` as a first-class value

## Context

Sensei's status taxonomy (inherited via `docs/development-process.md`) is `draft | accepted | accepted (lite) | provisional | superseded`. `kanon` ships with deferred capabilities that are intent-committed but implementation-scheduled for later releases — fidelity-lock, spec-graph-tooling, ambiguity-budget, multi-agent-coordination, expand-and-contract-lifecycle, invariant-ids (per `docs/plans/roadmap.md`).

None of the existing status values fits:
- `draft` means "under active discussion for imminent acceptance" — too immediate.
- `accepted` + `fixtures_deferred:` is a workaround, not a first-class status.
- `provisional` means "accepted but flagged for revisit" — implies the decision might reverse, which is not the intent here.

## Decision

Add `deferred` as a first-class status value. The full taxonomy is now:

| Status | Meaning |
|---|---|
| `draft` | Under active discussion; not yet committed. |
| `accepted` | Committed; behaviour must match. |
| `accepted (lite)` | Same weight as accepted, using the ADR-lite format (per ADR-0005 in Sensei's lineage). |
| `deferred` | Commitment to ship; implementation scheduled for a later release. Transitions to `draft` when work begins, then `accepted` on landing. |
| `provisional` | Accepted on current evidence, flagged for revisit when verification evidence lands. A commitment to revisit, not a deferral. |
| `superseded` | Replaced by a later artifact. The superseding artifact's identifier must appear in the old one's header. |

A `deferred` spec is a real spec file with real content (problem statement, sketched invariants, expected acceptance criteria) — just not implemented yet. `ci/check_foundations.py` accepts `deferred` status as a valid `realizes:`/`serves:` reference target. A consumer repo adopting the kit at tier-2+ can safely link to `deferred` specs without breaking validators.

`deferred` is distinct from `draft` (implementation-scheduled, not discussion-active), from `provisional` (committed-not-subject-to-reversal), and from `accepted (lite)` (which is just a format variant, not a time-ordering).

## Alternatives Considered

1. **Keep `fixtures_deferred:` pattern, no new status.** Works for fixtures but doesn't generalise to "spec whose implementation is deferred." Rejected — would force other coordination mechanisms for the 6 deferred capabilities.
2. **Use `draft` for deferred capabilities.** Conflates "under discussion" with "scheduled for later." Rejected — a reader cannot tell whether the spec needs input now or later.
3. **Add `deferred`** (chosen). Minimal semantic addition, orthogonal to existing values.

## Consequences

- `ci/check_foundations.py` (Phase D) accepts `deferred` status in principle/spec frontmatter.
- The six deferred-capability specs in v0.1 use this status.
- The `docs/plans/roadmap.md` index is the human-readable entry point for all `deferred` specs.
- When work on a deferred capability begins, the expected transition is `deferred` → `draft` → `accepted`. A deferred spec that transitions directly to `accepted` (skipping `draft`) is a process smell but not a validator error.

## Config Impact

None at the Python level. Affects `docs/development-process.md` § Status values list.

## References

- Session plan — Phase B deferred-capability capture.
- Sensei's existing taxonomy as the starting point.
