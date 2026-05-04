---
status: accepted
date: 2026-05-04
---
# ADR-0056: Close SDD protocol gaps — ADR authoring gate and design-before-plan gate

## Context

The SDD aspect's protocol coverage follows a clear pattern: dangerous activities
— irreversible source changes, capability introductions, post-acceptance ADR
edits — have gate or guard protocols that fire before the agent acts.
Deliberative activities like writing documentation rely on templates and README
guidance instead. This split is intentional: gates are expensive, and the
substrate should only impose them where unsupervised agent behaviour produces
artifacts that are costly to fix after the fact.

Two gaps have been identified where autonomous LLM agents in consumer repos lack
behavioural triggers.

First, ADR authoring is undisciplined at every depth. The decisions directory
and template are scaffolded at depth 1, and the README contains rich guidance on
when and how to write ADRs, but no protocol operationalises that guidance into
agent-executable steps. Without a trigger, agents exhibit four failure modes:
retroactive authoring (documenting decisions already implemented), strawman
alternatives that exist only to be rejected, missing cross-references to related
ADRs, and status lifecycle abuse (writing directly as `accepted` rather than
starting in `draft`). The substrate's own repo has 55 ADRs written under human
supervision; the gap only manifests when an agent is the primary author.

Second, design doc creation has no gate at depth 3. The SDD method prescribes
Spec → Design Doc → ADRs → Plan → Implementation, but only spec-before-design
and plan-before-build have hard gates today. Agents skip the design doc step and
bake architectural decisions into plans implicitly, producing plans that contain
unreviewed structural choices with no dedicated artifact to challenge them.

These gaps do not affect human-driven repos — humans internalise the SDD method
and self-trigger. They affect agent-driven consumer repos where the agent needs
an explicit protocol trigger to follow the prescribed sequence.

## Decision

Add an `adr-authoring` protocol at depth-min 1 with gate type. The trigger
fires when a non-obvious technical choice is being made during design or
planning. The protocol requires the agent to search existing ADRs for related
decisions, classify the decision's weight (full vs lite), produce genuine
alternatives with real trade-off analysis, enforce `draft` status on new ADRs,
and guard against retroactive authoring. The audit sentence is "ADR at `<path>`
has been drafted for review."

Add a `design-before-plan` protocol at depth-min 3 with gate type. The trigger
fires when the agent is about to write a plan for a change where a spec exists
and the change introduces new component boundaries or cross-component
interfaces. The protocol requires the agent to verify a design doc exists or
create one, and to ensure it covers architecture, interfaces, and key decisions
before the plan is written. The audit sentence is "Design doc at `<path>` covers
the architectural scope."

Do not add a foundations-authoring protocol. Vision, personas, and principles
are human-directed strategic artifacts — agents do not autonomously decide to
create them, and the existing templates and README guidance are sufficient for
the rare cases where a human asks an agent to help draft one.

## Alternatives Considered

1. **Add full protocol suite (design-review + foundations-authoring +
   adr-authoring).** Rejected: a foundations protocol solves a problem that does
   not exist in practice — humans drive those artifacts, and agents are not the
   initiating actor. A design-review protocol adds quality enforcement but the
   higher-value gap is the missing gate (design-before-plan); review discipline
   can follow in a later release once the gate exists.

2. **Add no protocols — enrich templates with exit criteria instead.** Rejected:
   templates do not change agent behaviour. The gap is behavioural (agents skip
   steps), not informational (agents do not know what to write). Only triggers
   — protocol entries in the AGENTS.md protocol index — change behaviour.

3. **Add only adr-authoring, skip design-before-plan.** Considered viable but
   rejected: the spec-to-plan skip at depth 3 produces plans with implicit
   architectural decisions that never get recorded as reviewable artifacts. The
   design-before-plan gate closes the last sequencing gap in the SDD method's
   depth-3 flow.

## Consequences

- **Positive.** Agents in consumer repos will produce ADRs proactively during
  design rather than retroactively after implementation, with genuine
  alternatives and proper cross-references to related decisions. The `draft`
  status requirement restores the review checkpoint that agents currently bypass.

- **Positive.** Depth-3 projects will get design docs as first-class artifacts
  in the SDD flow. Architectural decisions will live in dedicated, reviewable
  documents instead of being buried in plan prose where they escape scrutiny.

- **Negative.** Two more protocols in AGENTS.md's protocol index. This is a
  marginal cognitive-load increase for the agent's boot document, though both
  protocols are gate-typed and therefore only fire on specific triggers rather
  than on every task.

- **Negative.** `adr-authoring` at depth 1 adds a decision point to every
  non-trivial change: "does this warrant an ADR?" The protocol must keep the
  classification step lightweight so that the common-case answer ("no, this is a
  routine change") is fast and does not slow down the agent's primary task.

## References

- [ADR-0055: Manifest unification](0055-manifest-unification.md)
- [Design doc: SDD protocol gaps](../design/sdd-protocol-gaps.md)
- [P-protocol-not-product principle](../foundations/vision.md)
