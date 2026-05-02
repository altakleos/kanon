---
status: accepted
date: 2026-04-22
depth-min: 1
invoke-when: The user or agent is considering raising this project's sdd depth, or asks "should we increase depth?"
---
# Protocol: Tier-up advisor

## Purpose

Help decide whether this project should move to a higher depth — and if so, to which one. Increasing depth is cheap (non-destructive per ADR-0008), so the bias is toward raising when signals are mixed but real; the bigger cost is increasing depth too early and dragging a short-lived prototype through gates it doesn't need.

## Steps

### 1. Collect signals

Read the current state of the repo. Note:

- **Contributor count / agent count.** Solo vs. pair vs. team? Multiple LLM sessions in parallel?
- **Artifact count.** How many ADRs, plans, specs exist already? Are they growing?
- **Rate of change.** Is every commit touching multiple files or just one? Are CHANGELOG entries accumulating?
- **Downstream users.** Is anyone depending on this repo's stability? Public release? Internal users? Just the author?
- **Lifespan signal.** Is the user talking about "shipping", "releases", "breaking changes"? Or "trying this out", "exploring"?
- **Coordination pain.** Has the user recently complained about losing context, redoing work, agents making unapproved changes?

### 2. Fit each depth against the signals

Consult `docs/specs/tiers.md` (available at depth ≥ 2) or the summary below:

- **depth 0** fits: vibe-coding, one-off utilities, short-lived experiments, solo prototypes.
- **depth 1** fits: any shipped project with a CHANGELOG, any work where "plan before build" would prevent known rework.
- **depth 2** fits: projects with user-facing promises (public CLI, API, SLA) — something a spec would help pin down before design.
- **depth 3** fits: platform-scale (principles/personas/vision matter; multi-team coordination exists).

### 3. Tiebreaker

When the signals point to two adjacent depths, **prefer the lower one**. Increasing depth is cheap: when the project grows into the higher depth, one `kanon aspect set-depth` command gets it there. Decreasing depth is non-destructive but the sunk cost of unused structure is real.

Exception: if the user has already been burned by the current depth's looseness (e.g., "an agent overwrote my work", "we lost the reasoning for that change") and the next depth's gates directly address that, recommend the higher depth.

### 4. Produce a recommendation

State:
- **Recommended depth.** One number.
- **Why.** Three signals that tipped the decision.
- **What changes.** Which gates turn on, which artifact directories appear, what the user's next action looks like. Reference specific files/sections from `docs/specs/tiers.md` when possible.
- **What stays the same.** Reassure: no existing content is deleted; user edits survive.

### 5. Halt if inconsistent with user intent

If the user's stated goal conflicts with the recommendation, **stop and ask**. Example: user says "this is just a throwaway", signals say depth 2 — ask whether the lifespan signal has actually changed, don't just override. Judgment beats signals.

## Out of scope

- Running `kanon aspect set-depth` on the user's behalf. This protocol advises; the user (or a subsequent tool-use decision) executes.
- Multi-repo coordination. Each repo's depth is independent.

## Exit criteria

You have either:
- Delivered a depth recommendation with rationale, OR
- Halted with a specific clarification question.
