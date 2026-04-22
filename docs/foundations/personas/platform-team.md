---
id: platform-team
status: accepted
date: 2026-04-22
stresses:
  - P-specs-are-source
  - P-verification-co-authored
  - tiers
  - verification-contract
  - multi-agent-coordination
---
# Persona: Platform Team

**One sentence:** A multi-person engineering group building shared infrastructure (library, service, tool, framework) consumed by other teams inside the same company, where specs are the contract between producers and consumers.

## Context

Works across timezones. Multiple contributors, multiple LLM agents, occasional parallel worktrees. The shared infrastructure makes promises that downstream teams rely on, so spec-level invariants matter. Regulatory compliance sometimes applies. The team has product managers and auditors who read specs but never code. Code reviews happen at the PR level with multiple reviewers.

## Goals with `agent-sdd`

- Adopt the kit across every platform repo with consistent conventions.
- Use full tier-3 discipline: foundations (vision, principles, personas), specs as the producer-consumer contract, design docs for mechanism choices, ADRs for decision archaeology, plans for execution records, verification as co-authoritative source.
- Enable cross-team onboarding: a new team picks up a platform library and gets fluent by reading the SDD artifacts, not by reading the code.
- Run parallel LLM-agent worktrees without coordination disasters.

## What stresses the kit

- **Scale.** Tier-3 projects have 20+ specs, 30+ ADRs, 40+ plans over a year. Navigation must remain fast. Spec-graph tooling (deferred to v0.2) is the mitigation.
- **Reviewer ergonomics.** Reviewers need to read spec diffs first, not code diffs. The spec-diff renderer (deferred to v0.2 per `docs/specs/spec-graph-tooling.md`) is the mitigation.
- **Multi-agent coordination.** Two agents in parallel worktrees can collide on ADR numbers, plan locks, spec SHAs. The coordination manifest (deferred to v0.2 per `docs/specs/multi-agent-coordination.md`) is the mitigation.
- **Audit trail.** An auditor asks "does the code match this spec invariant?" and expects a mechanical answer. The fidelity lock (deferred to v0.2 per `docs/specs/fidelity-lock.md`) is the mitigation.

## What does NOT stress the kit at tier-3

- Adoption friction in the sense of solo-engineer. Platform teams accept meaningful ceremony; they already have it in other tools. The kit's job is to make the ceremony worthwhile.

## Success when using `agent-sdd`

- A new reviewer can review a PR by reading the plan + spec diff, touching code only for confirmation.
- A new team consumer of a platform library is productive against the library in under a day by reading the spec tree.
- Over a year, ADR supersession chains remain traceable; no "why did we do this?" question goes unanswered.
- Parallel agent workflows produce mergeable plans, not three-way merge conflicts on documentation.
