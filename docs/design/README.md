# Design Docs

Technical architecture — HOW features are built at a high level.

## What is a design doc

A design doc describes HOW a feature is built at a high level. It takes a spec's intent and proposes an architecture: which components interact, how data flows, what state model applies, what trade-offs were accepted. Design docs are where technical philosophy lives — the decisions about mechanisms, patterns, and system shape.

Design docs are technical but not procedural. They describe the architecture of a solution without specifying step-by-step execution. If numbered steps appear, the content belongs in an implementation artifact, not a design doc.

Design docs may be ephemeral in the sense that the implementation can diverge from the original plan. The ADRs capture the decisions that survive; the design doc captures the thinking that led to them.

## When to write a design doc

A design doc is warranted when:

- A new technical mechanism is being introduced (a new state model, a new verification approach, a new algorithm).
- The architecture is not obvious from reading the implementation alone — the reader needs to understand the system-level thinking.
- Trade-offs were evaluated and the design doc captures the reasoning before it fades.

A design doc is NOT needed for: threshold tuning, bug fixes, adding content to an existing output type, extending a vocabulary.

Design docs use a lightweight format: YAML frontmatter (`status`, `date`, `implements`), then sections for Context, Specs, Architecture, Interfaces, and Decisions.

## When to skip a design doc

A design doc may be skipped when **all four** conditions hold:

1. **Pattern instantiation** — the feature follows an architecture already documented in an accepted ADR or design doc. No new mechanism is introduced.
2. **Single-concern scope** — the feature touches one component boundary (e.g., one script + one schema, or one configuration surface). No novel cross-component interactions.
3. **Spec carries the reasoning** — the spec's Rationale section explains the *why* sufficiently that a design doc would only restate it with file paths.
4. **Plan exists** — a plan captures the file-level breakdown that a design doc's Architecture section would have provided.

When skipping, the plan's frontmatter should declare `design: "Follows ADR-NNNN"` (referencing the ADR or design doc whose pattern is being instantiated) so the skip is auditable, not silent.

**Watch for false skips.** If a "pattern instantiation" feature produces a new ADR during implementation, that signals the feature was more novel than assumed. Add a retrospective design doc in that case.

## Index

| Doc | Implements |
|---|---|
| [kit-bundle](kit-bundle.md) | **Retired** — superseded by [aspect-model](aspect-model.md). Historical v0.1 manifest-driven layout |
| [aspect-model](aspect-model.md) | `../specs/aspects.md` — manifest registry, namespaced markers, and legacy-tier auto-migration |

More design docs will land as features grow beyond pattern-instantiation.
