---
id: solo-with-agents
status: accepted
date: 2026-04-23
stresses:
  - P-prose-is-code
  - aspects
  - multi-agent-coordination
  - cli
---
# Persona: Solo Developer With N Concurrent Agents

**One sentence:** A single human who spawns multiple LLM agents — often across different harnesses — to work on the same repo in parallel, hitting agent-vs-agent collisions the moment two of them touch the same files.

## Context

Works from one laptop. The human isn't typing code most of the time; they're issuing plans and reviewing diffs. Three or four agents may be active simultaneously — one in Claude Code editing feature code, one in a subagent refactoring tests, one in Codex drafting docs, one in a verify loop. The repo is single-author by `git blame` but multi-author by session count. Encounters parallel-agent problems human teams traditionally hit at 5–10 contributors — plan-lock contention, overlapping edits to shared files like `CHANGELOG.md`, ADR-number races, inconsistent assumptions about which branch is canonical — except these hit on day one.

This persona didn't exist when the tier model and earlier personas were authored: `solo-engineer` implicitly assumes a single executor; `platform-team` assumes multiple humans. Neither names the "one human, N agents" configuration that is kanon's actual default user.

## Goals with `kanon`

- Run multiple concurrent agents without them overwriting each other's work.
- Get worktree-style isolation on day one, not "when a second human joins."
- Have a shared source of truth — plan SHAs, decision-number reservations — that every agent session reads before writing.
- Opt into coordination aspects (`worktrees`, `multi-agent-coordination`) early without taking on team-scale ceremony (spec-review, RFC-light, code-review rituals).

## What stresses the kit

- **Agent-first aspect framing.** The `worktrees` aspect's `invoke-when` trigger must name agent-agent collision explicitly, not "second contributor." Tier-placement must reflect that this is a tier-1 pain, not a tier-2 one. See `docs/specs/aspects.md` INV-aspects-every-aspect-self-hosted and ADR-0012 § agent-first rationale.
- **Cross-harness boot-chain consistency.** Every agent session — regardless of harness — lands on the same AGENTS.md, reads the same protocol catalog, obeys the same gates. Any drift between shim targets (ADR-0003) produces agent-vs-agent behavioral divergence.
- **Reservation mechanics.** Two agents drafting ADRs in parallel can both claim `0014`; two agents approving plans can each believe their own plan is the approved one. The deferred `multi-agent-coordination` spec (reservations ledger, plan-SHA pins, decision handshake) is the mitigation — its elevation from "platform-team eventually" to "agent-first early" shifts with this persona.
- **Atomicity under concurrent CLI invocation.** Two agents running `kanon aspect add` on the same target simultaneously must not corrupt `.kanon/config.yaml`. File-level atomicity (existing `_atomic.py`) covers the write; operation-level coordination is v0.2+.

## What does NOT stress the kit

- Reviewer-cohort ergonomics. One human reviews what N agents produce; no cross-team review process.
- Cross-repo spec dependencies. Single repo.
- Compliance and audit. Typically absent at this scale — the incidental ADR + plan + transcript-fixture trail is nice-to-have, not load-bearing.

## Success when using `kanon`

- Three concurrent agents across two harnesses edit the same repo for a week without a single merge conflict on kit-managed files.
- Every fresh agent session — on wake, after a compaction, or across harness boundaries — lands on the correct AGENTS.md and knows which plan is currently approved.
- `kanon aspect add worktrees` lands on day one of a new project; the human never types `git worktree add` manually.
- A week-later resume with a fresh session reads the kit's artifacts and becomes productive in under five minutes, indistinguishable from the agents that ran last week.
