---
status: accepted
date: 2026-04-28
depth-min: 2
invoke-when: A change introduces a new user-visible capability, or the agent is unsure whether a spec is needed
---
# Protocol: Spec Before Design

## Purpose

Ensure every new user-visible capability has an approved spec before design docs, ADRs, plans, or implementation begin.

## Steps

### 1. Classify the change

A change **needs a spec** (spec first) if any of these apply:

- introduces a new CLI command, mode, or subcommand
- adds a new output dimension users can observe or consume
- makes a new guarantee to users that must survive implementation changes
- multiple design approaches exist and the spec constrains which are viable
- you are unsure whether it falls below this line

A change **does NOT need a spec** (skip directly to design/plan/implementation) if it is:

- an implementation refactor that preserves observable behaviour
- a configuration-value or threshold adjustment
- a single-file bug fix
- adding a check, validator, or test
- adding a new output type that follows an existing pattern already governed by a spec

### 2. Consult foundations (if available)

If `docs/foundations/` exists, scan it before writing the spec:

- Read `vision.md` to verify the capability aligns with the project's mission and non-goals.
- Scan `principles/` for principles that constrain the design space. Note any the spec should `realize:` in its frontmatter.
- Scan `personas/` for personas whose stress dimensions are relevant. Note any the spec should list in `stressed_by:` frontmatter.

Carry these forward into the spec's frontmatter fields. This step is informational — it does not block if foundations are absent or incomplete.

If `kanon verify` has flagged a foundations-coherence warning (vision.md changed but principles/personas have not been updated), surface this to the user before proceeding. Stale foundations may lead to specs grounded in outdated project stances.

### Foundations onboarding (first spec only)

If `vision.md` contains only scaffolded template content (e.g., `status: draft` with no project-specific narrative), pause and ask the user:

> "I don't have your project's vision yet. A quick description will make this spec — and every future spec — sharper. What's the one-paragraph pitch?"

If the user provides a description, populate `vision.md` with their answer, structured into Mission, Non-goals, and Key bets sections.

Then, in a single checkpoint, present extracted foundations:

> "From your vision I extracted **principles** [list] and identified potential **personas** [list, if derivable]. Should I capture any of these? (all / principles only / skip)"

Write whichever artifacts the user approves, then proceed to write the spec.

If the user declines to provide a vision description, proceed to write the spec without foundations context. This is a recommendation, not a gate — the user's choice is respected.

This flow fires only when foundations are empty templates. Once populated, subsequent specs skip directly to consulting the existing foundations.

### 3. Write the spec

Your **first output** is a spec file at `docs/specs/<slug>.md`, followed by explicit user approval. You may not write a design doc, ADR, plan, or implementation before the spec is approved.

### 4. Design-doc skip convention

When skipping a design doc (all conditions in the SDD method doc § "When to Skip" are met), declare the skip in the plan's YAML frontmatter as `design: "Follows ADR-NNNN"` — citing the ADR that already covers the design space.

### 5. State the audit sentence

**Before your first design-doc, ADR, plan, or source-modifying tool call, state in one sentence:** "Spec at `<path>` has been approved." If you cannot truthfully emit that sentence, stop and write the spec.

## Exit criteria

- A spec file exists at `docs/specs/<slug>.md`.
- The user has explicitly approved the spec.
- The audit sentence has been stated before the first design/plan/source tool call.
