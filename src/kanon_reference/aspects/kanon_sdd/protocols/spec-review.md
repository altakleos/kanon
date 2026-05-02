---
status: accepted
date: 2026-04-22
depth-min: 2
invoke-when: A draft spec is ready for review (status:draft), or the user asks for a spec review, or a spec is about to be promoted to status:accepted
---
# Protocol: Spec review

## Purpose

Review a draft spec (`docs/specs/<slug>.md`) before it ships. The review surfaces structural gaps, falsifiability weaknesses, and ambiguities that would only otherwise be found once the spec is wrong. Output is a three-tier feedback block (what works, prioritized issues, one key learning) plus a readiness verdict.

## Steps

### 1. Structural checks

Verify the spec has the required shape:

- **Frontmatter present.** At minimum: `status`, `date`. Likely-required: `realizes` (principles) or `serves` (other specs), `fixtures` (test paths) or `fixtures_deferred` (reason).
- **Required sections present.** `## Intent`, `## Invariants`, `## Rationale`, `## Out of Scope`, `## Decisions`. Absent sections flagged.
- **Invariants are numbered.** Each invariant is a top-level numbered item under `## Invariants`. A wall of prose fails; so does an un-numbered bullet list (no way to cite).
- **Realizes/serves references resolve.** Every principle slug in `realizes:` exists under `docs/foundations/principles/`. Every spec slug in `serves:` exists under `docs/specs/`.

If structure fails, report the gap and stop — revising with structural holes wastes effort. Invite the user to patch structure first.

### 2. Invariant falsifiability probe

For each numbered invariant, ask: **"What observation would falsify this?"**

- **Falsifiable** — e.g., "tier-3 bundle is byte-identical to repo's canonical `AGENTS.md`" — a diff either agrees or not.
- **Unfalsifiable** — e.g., "the kit is a good SDD kit" — flag as prose, not an invariant. Suggest refactor: either drop it or turn it into a specific, checkable claim.
- **Ambiguous** — if two readers would genuinely disagree on whether the invariant holds, flag it. Specific phrasings to watch: "appropriately", "reasonable", "where applicable".

### 3. Ambiguity pass

Scan the full spec text for:

- **Passive-voice escape hatches** — "should be considered", "is expected to", "may be used" often hide an undecided rule.
- **Defined-nowhere terms** — if the spec introduces a term (e.g., "bundle", "fidelity", "gate") without a definition, flag it. Either the term is defined elsewhere (link it) or define it here.
- **Trailing TODOs.** Inline `TODO:`, `XXX`, `FIXME`, or bracketed placeholders like `[TBD]`.

### 4. Steelman the opposition

Find the strongest argument *against* this spec's direction:

- Who might reasonably object to this design? (A specific persona from `docs/foundations/personas/` if they exist.)
- What tradeoff is this spec making that a reasonable person would make differently?
- Is the `## Out of Scope` section actually principled, or is it hiding decisions the spec is avoiding?

State the strongest objection in one paragraph. If the spec's `## Rationale` doesn't already address it, flag that.

### 5. Three-tier feedback

Produce three blocks, in this order:

- **What works (≤ 3 bullets).** Specific, not generic. "Invariant 4's byte-equality check is sharp and testable" beats "invariants look good."
- **Prioritized issues (ranked, each with severity).** Structural (must-fix before ship), ambiguity (should-fix), stylistic (nice-to-have). Each issue cites a section/line; proposes a concrete revision or asks a focused question.
- **One key learning.** The single most important thing the author should take from this review. Not a summary — a pivot point. If you can't find one, say so.

### 6. Readiness verdict

One of:

- **Ship.** Structure sound, invariants falsifiable, ambiguities negligible. Proceed to `status: accepted`.
- **Ship with small edits.** Minor revisions listed above should be folded in; no further review required.
- **Revise and re-review.** Structural or falsifiability issues warrant another pass before `accepted`.
- **Rescope.** The spec is mixing multiple specs' worth of intent; split or narrow before continuing.

Justify the verdict in one sentence.

## Exit criteria

You have delivered three feedback blocks plus a one-line verdict. No file modifications — the review is input for the spec author, not a patch.

## Anti-patterns

- **"Looks good to me."** That's not a review.
- **Editing the spec.** Not your job. Feedback only.
- **Praising generically.** Specific observations beat general compliments.
- **Skipping the steelman.** It's the step most likely to catch a real flaw.
