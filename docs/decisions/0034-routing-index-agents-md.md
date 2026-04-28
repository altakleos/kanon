---
status: accepted
date: 2026-04-28
supersedes: "0010-protocol-layer (§ enforcement-proximity)"
category: process
---
# ADR-0034: Routing-index AGENTS.md — refined enforcement proximity

## Context

ADR-0010 established the protocol layer and stated: "The two load-bearing rule sections (plan-before-build, spec-before-design) stay as AGENTS.md marker sections, not protocols. The distinction: rules that must bind on every turn live in AGENTS.md; procedures invoked under specific triggers live in protocols."

This created a dual-maintenance problem: gate rules existed as both AGENTS.md marker sections (~48 lines inlined) AND as the procedures they described. Soft guidance (test-discipline, secure-defaults, dependency-hygiene) was duplicated identically in AGENTS.md sections and protocol files. AGENTS.md grew to 411 lines at depth 3, with 71% being inlined content.

## Decision

Refine ADR-0010's enforcement-proximity principle:

1. **Hard gates stay inline but compressed.** Plan-before-build, spec-before-design, and worktree-isolation appear in AGENTS.md as a hard-gates table: one row per gate with trigger condition, one-sentence summary, audit-trail sentence, and link to the full protocol file. The agent sees the gate at boot; the detailed procedure is loaded on-demand.

2. **Soft guidance moves to protocol-only.** Content that existed in both AGENTS.md sections and protocol files (test-discipline, secure-defaults, dependency-hygiene, publishing-discipline, fidelity-discipline, branch-hygiene) is eliminated from AGENTS.md. The protocol file is the single source; the protocols-index table is the routing pointer.

3. **Marker sections eliminated (except protocols-index).** The `sections:` mechanism in aspect sub-manifests is removed. The only remaining marker is `protocols-index`, rendered dynamically.

## Consequences

- AGENTS.md shrinks from 411 to ~98 lines at depth 3.
- No content is duplicated between AGENTS.md and protocol files.
- `_assemble_agents_md()` simplifies to: load base template + render protocols-index.
- The `sections/` directories and `agents-md/` body files are deleted from all aspects.
- Hard gates remain visible at boot (enforcement proximity preserved); detailed procedures are on-demand (progressive disclosure).
