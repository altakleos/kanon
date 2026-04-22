---
status: deferred
date: 2026-04-22
realizes:
  - P-cross-link-dont-duplicate
target-release: v0.2
---
# Spec: Multi-agent coordination — reservations ledger, SHA pins, decision handshake

## Intent

Make `agent-sdd`-managed repos safe for multiple concurrent LLM agents — parallel worktrees, orchestrators spawning sub-agents, long-running background jobs. The kit's artifacts become the inter-agent protocol, not just human documentation.

## Problem

Two agents working the same repo in parallel worktrees today have no coordination layer. Both could claim the same ADR number, both could write plans that depend on the same subsystem, one could update a spec out from under the other's plan. These are real failure modes for platform-team persona.

## Sketched invariants

1. **Reservations ledger.** `docs/.coordination/reservations.yaml` is an append-only file where each worktree declares the spec/plan/ADR slots it intends to touch. Written by `worktree-setup`, read by peers.
2. **ADR number pre-claim.** Worktree setup touches `docs/decisions/NNNN-<slug>-<worktree>.md` with `status: reserved` so two worktrees can't both claim NNNN.
3. **Plan SHA pinning.** Each plan frontmatter carries `spec-sha: <git-hash-of-serving-spec>`. On merge, teardown verifies the SHA still matches HEAD; mismatch flags "agent B changed the spec out from under agent A's plan."
4. **Plan-task state `[?]`.** New task-checkbox state meaning "blocked awaiting decision from another agent." Agent A emits a stub ADR with `status: blocked-on-decision`, `requires-input-from: <plan-B>`; agent B authors the ADR, promotes to accepted; agent A's next `verify` run unblocks.
5. **Sub-agent AGENTS.md inheritance.** `agent-sdd agents-preamble` CLI emits the resolved AGENTS.md boot chain as a single blob; orchestrators prepend this to every sub-agent system prompt.

## Out of Scope in v0.1

All of it. v0.1 does not ship the reservations ledger, the decision handshake, or the agents-preamble CLI.

## Why deferred

Real engineering effort (file-level protocol design, validator, CLI subcommand, orchestrator integration docs). Appropriate for v0.2 after the core kit stabilises.

## References

- Multi-agent coordination architect agent report during v0.1 planning.
- ADR-0016 (Sensei) — worktree-agent-isolation — for precedent.
