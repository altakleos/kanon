---
status: accepted
date: 2026-05-04
---
# ADR-0057: Move foundations to depth 2 — LLM context for spec authoring

## Context

Foundations — vision, personas, and principles — are currently scaffolded at
depth 3 alongside design docs. The original placement treated them as optional
strategic documents that humans write for humans: high-ceremony artifacts that
arrive late in the depth progression because they were seen as companions to
architectural design rather than prerequisites for specification.

In LLM-agent-driven development, foundations serve a second purpose that the
original depth assignment did not anticipate: they are context artifacts that
improve the quality of every downstream SDD artifact. An agent writing a spec
with access to vision, principles, and personas produces fundamentally better
specs than one operating without that context. Personas stress-test requirements
by surfacing edge-case user needs the agent would otherwise overlook. Principles
constrain design choices by providing explicit trade-off guidance. Vision
provides strategic alignment that prevents specs from drifting toward local
optima that conflict with the project's direction.

The spec-review protocol (depth 2) already validates foundations references: it
checks that `realizes:` slugs resolve to principles and asks reviewers to
consider personas. But spec-before-design (also depth 2) has no foundations
reference — agents write specs without consulting foundations, then encounter
foundations expectations only at review time, too late to shape the spec's
direction. This creates a gap: the review protocol assumes context the authoring
protocol never provided.

Foundations are lower ceremony than design docs. They are written once and
rarely updated, whereas design docs are per-change artifacts with dedicated
gates. The depth progression reflects ceremony level: depth 1 brings decisions
and plans, depth 2 brings specs, depth 3 brings design docs. Foundations fit
the depth-2 ceremony profile — lightweight, written early, consulted often —
not the depth-3 profile of per-change architectural artifacts.

## Decision

Move the four foundations files (`README.md`, `vision.md`,
`personas/README.md`, `principles/README.md`) from depth-3 to depth-2 in the
SDD aspect manifest. Projects that opt into depth 2 will have foundations
scaffolded alongside specs.

Add a foundations-context step (Step 1.5) to the spec-before-design protocol:
before writing a spec, scan `docs/foundations/` if it exists, identify relevant
principles and personas, and carry these into the spec's frontmatter as
`realizes:` and `personas:` references. This is a classification enrichment
step, not a gate — it does not block if foundations are absent, and it does not
fail if no principles or personas are relevant to the change. The step ensures
that agents consult available context before authoring, closing the gap between
spec-before-design and spec-review.

Update the foundations `README.md` to describe foundations as "context consulted
during spec authoring" rather than "not a processing stage." The current
self-description reflects the depth-3 placement where foundations were passive
reference material; the new placement makes them active inputs to the spec
authoring flow.

Design docs remain at depth 3. The overall depth range stays [0, 3].

## Alternatives Considered

1. **Split depth-3 into depth-3 (foundations) + depth-4 (design docs).**
   Rejected: adding a depth level provides no proportional value. The 0–3 range
   is a natural ceiling that the panel consensus and existing documentation
   reinforce. A fifth level risks teams stopping at depth 3 and losing design
   docs entirely, since each additional depth is a harder sell to adopt.

2. **Keep foundations at depth 3, add a new foundations-context-load protocol.**
   Rejected: ADR-0056 explicitly rejected a foundations protocol on the grounds
   that foundations are human-directed strategic artifacts that do not need
   autonomous agent triggers. A step inside an existing protocol is lighter than
   a new protocol — it adds no entry to the protocol index, no new trigger, and
   no new audit sentence. The enrichment step respects ADR-0056's reasoning
   while still closing the context gap.

3. **Keep foundations at depth 3, no changes.** Rejected: foundations arrive too
   late to influence spec quality. The spec-review protocol already references
   foundations but spec-before-design does not, creating a gap where agents write
   specs without consulting available context and only discover the expectation
   at review time. This ordering inversion wastes a review round on feedback
   that could have been incorporated during authoring.

## Consequences

- **Positive.** Teams at depth 2 automatically get foundations scaffolded
  alongside specs. Agents consult vision, personas, and principles before
  writing specs, improving spec quality without requiring depth-3 adoption.

- **Positive.** The spec-before-design → spec-review pipeline becomes coherent:
  foundations are consulted at authoring time (spec-before-design Step 1.5) and
  validated at review time (spec-review). The review protocol no longer assumes
  context the authoring protocol never provided.

- **Negative.** Depth-2 projects that do not want foundations still get the
  files scaffolded. The files are lightweight — four READMEs with templates —
  and can be left empty without triggering verification failures.

- **Negative.** The foundations `README.md` self-description changes from "not a
  processing stage" to "context for the flow," which is a semantic shift in how
  the substrate frames these artifacts. Consumers who have read the current
  README may need to update their mental model.

## References

- [ADR-0056: SDD protocol gaps](0056-sdd-protocol-gaps.md)
- [docs/foundations/README.md](../foundations/README.md)
