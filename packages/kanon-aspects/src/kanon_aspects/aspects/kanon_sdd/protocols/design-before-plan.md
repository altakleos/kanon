---
status: accepted
date: 2026-05-04
depth-min: 3
invoke-when: About to write a plan for a change where a spec exists and the change introduces new component boundaries, cross-component interfaces, or non-obvious architectural mechanisms
gate: hard
label: Design Before Plan
summary: changes introducing new component boundaries require a design doc before planning.
audit: 'Design doc at `<path>` covers the architectural scope.'
priority: 300
question: 'Does this change introduce new component boundaries or cross-component interfaces? If yes, does a design doc exist? If not — **stop and write the design doc.**'
---
# Protocol: Design Before Plan

## Purpose

Ensure architectural decisions are captured in a reviewable design doc before implementation planning begins, preventing component boundaries and interface contracts from being improvised during planning.

## Steps

### 1. Check for existing design doc

If a design doc already exists for this spec and covers the architectural scope of the planned change, state the audit sentence and proceed to planning.

### 2. Write the design doc

If no design doc exists, or the existing one does not cover the new scope, create one at `docs/design/<slug>.md` using the template. The design doc must include:

- **Context** — what problem the design solves.
- **Architecture** — names components and their boundaries.
- **Interfaces** — public contracts between components.
- **Decisions** — non-obvious choices made.

### 3. Link the design doc

The frontmatter must include `implements:` linking to the relevant ADR or spec.

### 4. State the audit sentence

**Before proceeding to plan, state:** "Design doc at `<path>` covers the architectural scope."

## When NOT to fire

- The change follows an existing pattern with no new boundaries.
- The change is a bug fix or threshold tuning.
- The spec is self-contained and the implementation is obvious.
- The plan would be identical to the design doc (no added value).

## Exit criteria

- Design doc exists with valid frontmatter.
- Architecture section names components.
- Interfaces section lists boundaries.
- Audit sentence stated.
