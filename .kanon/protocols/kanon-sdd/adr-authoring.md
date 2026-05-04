---
status: accepted
date: 2026-05-04
depth-min: 1
invoke-when: A non-obvious technical choice is being made during design or planning, or the agent identifies a choice with genuine alternatives, or the agent is unsure whether an ADR is needed
---
# Protocol: ADR Authoring

## Purpose

Ensure architectural decisions are recorded proactively as reviewable artifacts, not buried in implementation commits or written retroactively.

## Steps

### 1. Classify the decision

Consult the rubric in `docs/decisions/README.md`:

- **Full ADR** — model change, genuine debate, constrains future work.
- **ADR-lite** — gate/default/boundary change within an existing model.
- **No ADR needed** — bug fix, threshold tuning, pattern-following.

If no ADR is needed, stop here.

### 2. Search existing ADRs

Scan `docs/decisions/` for ADRs touching the same component or capability. List related ADRs for the References section of the new ADR.

### 3. Write the ADR

Use `docs/decisions/_template.md`. Number sequentially after the highest existing ADR. Write as `status: draft` — never `status: accepted`. The user promotes status after review.

### 4. Quality gate

- **Alternatives Considered** must list ≥2 genuine alternatives for full ADRs (≥1 for lite). "Do nothing" counts as one alternative.
- **Consequences** must include at least one tradeoff or cost.
- **Decision** statement must be a single declarative sentence.

### 5. Ordering guard

An ADR records a decision *being made*, not a decision already implemented. If the code already exists, flag this to the user — it is a Historical Note, not a standard ADR.

### 6. State the audit sentence

**Before proceeding, state:** "ADR at `<path>` has been drafted for review."

## Anti-patterns

- **Retroactive ADRs** disguised as forward decisions.
- **Strawman alternatives** — "Alternative: don't do it" with no analysis.
- **Missing cross-references** to related ADRs.
- **Writing as `status: accepted`** — bypasses review.

## Exit criteria

- ADR file exists at `docs/decisions/NNNN-<slug>.md`.
- Valid frontmatter with `status: draft`.
- All required sections populated.
- Audit sentence stated.
