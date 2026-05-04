---
status: accepted
date: 2026-05-04
depth-min: 2
invoke-when: Foundations are empty templates and a spec is about to be written, or the user asks to populate foundations
---
# Protocol: Foundations Authoring

## Purpose

Partner with the user to populate project foundations (vision, principles, personas) so that every downstream SDD artifact is grounded in project identity.

## Steps

### 1. Detect empty foundations

If `vision.md` contains only scaffolded template content (e.g., `status: draft` with no project-specific narrative), proceed to step 2. If vision.md has project-specific content, this protocol does not apply — return to the invoking protocol.

### 2. Populate vision

Ask the user:

> "I don't have your project's vision yet. A quick description will make this spec — and every future spec — sharper. What's the one-paragraph pitch?"

If the user provides a description, populate `vision.md` with their answer, structured into Mission, Non-goals, and Key bets sections.

If the user declines, return to the invoking protocol and proceed without foundations context. This is a recommendation, not a gate — the user's choice is respected.

### 3. Extract principles and personas

In a single checkpoint, present extracted foundations:

> "From your vision I extracted **principles** [list] and identified potential **personas** [list, if derivable]. Should I capture any of these? (all / principles only / skip)"

Write whichever artifacts the user approves.

### 4. Return to invoking protocol

Foundations are now populated. Return to the invoking protocol (e.g., spec-before-design Step 2) and proceed with the populated foundations as context.

## Exit criteria

- Vision.md contains project-specific content (or user explicitly declined).
- Approved principles and personas are written to their respective directories.
- Control returned to the invoking protocol.
