---
status: accepted
date: 2026-05-04
---
# ADR-0060: Foundations review protocol and downstream impact validator

## Context

ADR-0058 added a coherence validator that detects when `vision.md` changes
without corresponding updates to principles or personas. ADR-0059 added a
foundations-authoring protocol for initial population of the foundations layer.

The gap sits between detection and response. When the coherence warning fires,
the agent has no actionable next step. Principles may be invalidated, personas
may become irrelevant, and specs whose `realizes:` or `stressed_by:` frontmatter
references point at stale principles are grounded in outdated project stances.

The coherence validator tells you *something* changed. It does not tell you
*what to do about it*.

## Decision

Add two artifacts:

1. **`foundations-review` protocol** (depth-min 2, gate) — triggered when the
   coherence warning is active or the user requests a foundations review. The
   agent reads the new vision, classifies each principle as
   keep / amend / retire / new-implied, classifies each persona similarly,
   presents a disposition table for user approval, and executes approved
   changes. This is a judgment task requiring agent reasoning and user sign-off.

2. **`foundations_impact` validator** (depth 2) — mechanically traces
   `realizes:` and `stressed_by:` frontmatter references in specs to retired
   or superseded foundations and emits an affected-spec list during
   `kanon verify`. This is a computation task: deterministic grep over YAML
   frontmatter.

The protocol handles judgment (with user approval). The validator handles
computation (mechanical grep). Neither auto-rewrites specs — the impact list
is a triage input for the user.

## Alternatives Considered

1. **Unified protocol with create / review / evolve modes.** Rejected: create
   (ADR-0059) and review share zero steps; forcing them together makes the
   agent read 3× the prose for every invocation.

2. **Extend coherence validator only, no protocol.** Rejected: semantic
   alignment judgment (is this principle still relevant given the new vision?)
   requires agent reasoning, not mechanical checks.

3. **Auto-rewrite affected specs.** Rejected: spec rewrites are project-wide
   refactors needing their own plans. The impact list is the triage input;
   the user decides what to rewrite and when.

## Consequences

**Positive:** Vision changes trigger a structured review with downstream
impact visibility. The coherence warning becomes actionable instead of
informational.

**Negative:** One more protocol in the index. The review flow takes ~15
minutes for a project with many principles.

## References

- [ADR-0058](0058-foundations-coherence.md) — coherence validator
- [ADR-0059](0059-foundations-onboarding-cascade.md) — foundations-authoring protocol
