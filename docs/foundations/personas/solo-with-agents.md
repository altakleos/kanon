---
id: solo-with-agents
status: accepted
date: 2026-04-23
stresses:
  - P-prose-is-code
  - P-publisher-symmetry
  - P-runtime-non-interception
  - aspects
  - cli
---
# Persona: Solo Developer With N Concurrent Agents

**One sentence:** A single human who spawns multiple LLM agents — often across different harnesses — to work on the same repo in parallel, hitting agent-vs-agent collisions the moment two of them touch the same files.

## Context

Works from one laptop. The human isn't typing code most of the time; they're issuing plans and reviewing diffs. Three or four agents may be active simultaneously — one in Claude Code editing feature code, one in a subagent refactoring tests, one in Codex drafting docs, one in a verify loop. The repo is single-author by `git blame` but multi-author by session count. Encounters parallel-agent problems human teams traditionally hit at 5–10 contributors — plan-lock contention, overlapping edits to shared files like `CHANGELOG.md`, ADR-number races, inconsistent assumptions about which branch is canonical — except these hit on day one.

This persona is kanon's actual default user. `solo-engineer` and `platform-team` were kit-shape personas tied to the tier model and a multi-team adoption story; both were retired under the protocol-substrate commitment ([ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md)). `solo-with-agents` survives because the substrate's protocol — prose contracts, agent-resolved bindings, machine-only-owned resolutions — is shaped exactly for the one-human-N-agents configuration.

## Goals with `kanon`

- Run multiple concurrent agents without them overwriting each other's work.
- Get worktree-style isolation on day one, not "when a second human joins."
- Have a shared source of truth — plan SHAs, decision-number reservations — that every agent session reads before writing.
- Adopt a starter recipe (`kanon-aspects`'s `reference-default` recipe, or any other publisher's recipe) without losing the substrate's de-opinionated core.
- Optionally consume `acme-` aspects as they appear, with publisher-symmetric resolution semantics.

## What stresses the substrate

- **Agent-first aspect framing.** The `kanon-worktrees` reference aspect's `invoke-when` trigger names agent-agent collision explicitly, not "second contributor." Depth choice reflects that worktree isolation is needed at depth-1, not deferred to depth-2.
- **Cross-harness boot-chain consistency.** Every agent session — regardless of harness — lands on the same `AGENTS.md`, reads the same protocol catalog, obeys the same gates. Any drift between shim targets (per ADR-0003) produces agent-vs-agent behavioural divergence.
- **Reservation mechanics.** Two agents drafting ADRs in parallel can both claim `0014`; two agents approving plans can each believe their own plan is the approved one. The deferred `multi-agent-coordination` capability (reservations ledger, plan-SHA pins, decision handshake) is the mitigation.
- **Atomicity under concurrent CLI invocation.** Two agents running `kanon aspect add` on the same target simultaneously must not corrupt `.kanon/config.yaml`. File-level atomicity (existing `_atomic.py`) covers the write; operation-level coordination is post-Phase-A.
- **Resolution-determinism under parallel resolvers.** Two agents in two harnesses resolving the same contract against the same evidence files must produce structurally-equivalent resolutions. Disagreement is a P0 falsification probe (per ADR-0048 and the verification-contract spec).

## What does NOT stress the substrate

- Reviewer-cohort ergonomics. One human reviews what N agents produce; no cross-team review process.
- Cross-repo spec dependencies. Single repo.
- Compliance and audit. Typically absent at this scale — the incidental ADR + plan + transcript-fixture trail is nice-to-have, not load-bearing.

## Success when using `kanon`

- Three concurrent agents across two harnesses edit the same repo for a week without a single merge conflict on substrate-managed files.
- Every fresh agent session — on wake, after a compaction, or across harness boundaries — lands on the correct `AGENTS.md` and knows which plan is currently approved.
- A new project enables `kanon-worktrees` on day one via the publisher recipe; the human never types `git worktree add` manually.
- A week-later resume with a fresh session reads the substrate's artifacts and becomes productive in under five minutes, indistinguishable from the agents that ran last week.

## Amendments

| Date | ADR | What changed |
|---|---|---|
| 2026-05-01 | [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) | Tier vocabulary replaced with depth/aspect/recipe/publisher; `acme-` consumption added to goals; resolution-determinism added to stress list; sibling personas (`solo-engineer`, `platform-team`) noted as retired; `stresses:` updated to cite public-tier principles. |
