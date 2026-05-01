---
id: solo-engineer
status: superseded
superseded-by: 0048
date: 2026-04-22
stresses:
  - P-tiers-insulate
  - tiers
  - tier-migration
  - cli
---
# Persona: Solo Engineer

> **Status:** Superseded by [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md). The "tier" vocabulary, the `--tier 1` adoption flow, and the "tier promotion" concerns this persona stressed are kit-shape concepts; under the protocol-substrate commitment they no longer apply. Audience is explicitly vision-led-deferred per [`de-opinionation.md`](../de-opinionation.md). Body preserved verbatim per the immutability discipline applied to personas from ADR-0048 onward; the file remains as historical record. A future plan may resurrect this persona under protocol-mode framing if and when the audience becomes real.

**One sentence:** A developer building a project alone, likely in Python/TypeScript/Go/Rust, who wants SDD discipline without the overhead of a multi-team process.

## Context

Works from a laptop. Uses one or two LLM harnesses (typically Claude Code plus occasional Cursor or Codex). Ships small tools that later sometimes grow into larger ones. Has tried heavier methodologies (Scrum, CMMI, full RFC processes) and found them overkill for their scale. Has encountered the "I'm a month in and can't remember why I made this choice" problem — wants ADRs. Has encountered the "the LLM agent starts refactoring before I've clarified the goal" problem — wants plan-before-build.

## Goals with `kanon`

- Adopt the kit in under five minutes.
- Get plan-before-build and an ADR discipline without writing specs for throwaway scripts.
- When a prototype graduates to something users touch, promote to tier-2 (add specs) without rewriting anything.
- Never lose a design decision to "I'll remember it later."

## What stresses the kit

- **Adoption friction.** If `kanon init --tier 1` takes more than one minute and doesn't produce something immediately useful, the solo engineer closes the tab.
- **Tier promotion.** When moving from tier-1 to tier-2, the kit must not force retroactive specs for every shipped feature. Tier-up is additive only (per ADR-0008).
- **Minimal ceremony at tier-0 and tier-1.** No foundations, no personas, no design docs required. Just `AGENTS.md` + `docs/decisions/` + `docs/plans/`.

## What does NOT stress the kit

- Team coordination concerns. Solo.
- Cross-repo spec dependencies. Single repo.
- Regulatory compliance. Not in scope for the typical solo engineer.

## Success when using `kanon`

- One month in, can answer "why is this here?" from the ADR index in under 30 seconds.
- Six months in, has graduated one project from tier-1 to tier-2 without rewriting history.
- Never once needs to ask "does my tool support AGENTS.md?" — the shims handle it.
