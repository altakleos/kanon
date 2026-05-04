---
status: accepted
date: 2026-05-04
depth-min: 2
invoke-when: The foundations-coherence warning is active (vision.md has changed), or the user asks to review foundations for alignment
---
# Protocol: Foundations Review

## Purpose

Review existing foundations (principles, personas) against a changed vision to identify stale, contradictory, or missing artifacts.

## Steps

### 1. Read the current vision

Read `docs/foundations/vision.md` in full. Identify the key stances: mission, non-goals, and key bets.

### 2. Classify each principle

For each file in `docs/foundations/principles/`:

- **Keep** — the principle's stance still serves the vision. No changes needed.
- **Amend** — the stance is directionally right but the rationale, implications, or exceptions need updating to reflect the new vision.
- **Retire** — the stance contradicts or is no longer relevant to the new vision. Add `status: superseded` and `superseded-by:` frontmatter.
- **New implied** — the new vision introduces a stance not covered by any existing principle.

### 3. Classify each persona

For each file in `docs/foundations/personas/`:

- **Keep** — the persona and its stress dimensions are still relevant.
- **Amend** — the persona is relevant but its `stresses:` list needs updating.
- **Retire** — the persona is no longer relevant. Add `status: superseded` frontmatter.
- **New implied** — the new vision implies a user type not covered by any existing persona.

### 4. Present disposition table

Present the classification as a table for user approval:

| Artifact | Disposition | Rationale |
|----------|------------|----------|
| P-example | amend | Rationale changed due to new mission |
| persona-example | retire | No longer a target user |
| (new) P-new-stance | new | Vision introduces X stance |

The user may override any disposition.

### 5. Execute approved changes

Amend files in-place for "amend" dispositions. Add `status: superseded` frontmatter for "retire" dispositions. Create new files for "new implied" dispositions.

### 6. Clear the coherence warning

The `foundations_coherence` validator auto-clears when downstream files are touched. Verify by running `kanon verify`.

## Exit criteria

- Every principle and persona has a disposition (keep/amend/retire).
- User has approved the disposition table.
- Approved changes are committed.
- `kanon verify` coherence warning is cleared.
