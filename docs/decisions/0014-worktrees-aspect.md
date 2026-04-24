---
status: accepted
date: 2026-04-23
---
# ADR-0014: Worktrees aspect — isolated parallel execution via git worktrees

## Context

The deferred `multi-agent-coordination` spec bundles several primitives: reservation ledgers, plan-SHA pins, decision handshakes, and worktree isolation. These have very different landing costs. Worktree isolation is cheap (prose + ~100 LOC of shell) and independently valuable for the `solo-with-agents` persona, where agent-agent filesystem collision is a day-1 concern.

The aspect model (ADR-0012) provides the framework for shipping worktrees as a standalone opt-in discipline. ADR-0013 enables shipping reference shell helpers as kit content.

## Decision

Ship `worktrees` as a standalone aspect with the following properties:

1. **Depth range 0–2** (not binary). Depth 0 = opt-out. Depth 1 = prose guidance (protocol + AGENTS.md section). Depth 2 = prose + automation (adds shell helper scripts). The two layers — knowledge and automation — are independently useful.

2. **Change-scope trigger, not concurrency detection.** An agent cannot reliably detect whether other agents are running (no shared process table, stale lock problem, cross-machine invisibility). The protocol uses change scope as the primary trigger: multi-file or multi-step changes warrant a worktree. `git worktree list` serves as a secondary heuristic — existing worktrees signal likely parallel work.

3. **Scaffolding shape.** Protocol at `.kanon/protocols/worktrees/worktree-lifecycle.md`. AGENTS.md section `worktrees/branch-hygiene`. Shell helpers at `scripts/worktree-{setup,teardown,status}.sh` (depth-2 only, copy-in templates per ADR-0013).

4. **Cross-aspect dependency.** Requires `sdd >= 1` — worktree-per-plan correspondence depends on plans existing as first-class artifacts.

5. **Tier-1 placement.** The `solo-with-agents` persona faces agent-agent collision from day 1. Gating worktrees at tier-2 would force premature tier-up for a concern that exists at the earliest adoption stage.

## Alternatives Considered

**Binary depth (0–1).** Rejected. The protocol+section (knowledge layer) and shell helpers (automation layer) are independently useful. A user who knows `git worktree add` wants the policy guidance without the scripts. Forcing all-or-nothing conflates two separable concerns.

**Concurrency detection via lock files.** Rejected. Lock files are operationally fragile: stale locks after crashes, TOCTOU race conditions, invisible across machines. The failure mode (every agent thinks another is running) is worse than the problem it solves. Change-scope judgment is reliable and never wrong in a dangerous way — an unnecessary worktree is harmless; a missed collision is not.

**Depth 0–3 (four levels).** Rejected. The AGENTS.md section and protocol are not meaningfully separable — the section summarizes the protocol. Splitting them across depths would create a near-ghost cell. The aspect has two natural layers, not four.

## Consequences

- A new aspect directory `src/kanon/kit/aspects/worktrees/` is added to the kit bundle with its own sub-manifest.
- The top-level `manifest.yaml` gains a `worktrees` entry with `stability: experimental`, `depth-range: [0, 2]`, `default-depth: 1`, `requires: ["sdd >= 1"]`.
- `aspects.md` invariant 3 is updated to reflect worktrees as 0–2 (no longer cited as a binary example).
- The `multi-agent-coordination` deferred spec retains its remaining primitives (ledgers, SHA pins, handshakes) as future work.
- Runtime concurrency detection is explicitly out of scope — no lock files, heartbeats, or signal mechanisms.

## References

- [Spec: Worktrees](../specs/worktrees.md)
- [ADR-0012: Aspect model](0012-aspect-model.md)
- [ADR-0013: Vision amendment — reference automation snippets](0013-vision-amendment-reference-automation.md)
- [Spec: Aspects](../specs/aspects.md)
