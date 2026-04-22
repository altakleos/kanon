---
status: accepted
date: 2026-04-22
---
# ADR-0003: AGENTS.md is the canonical root; shims are pointers

## Context

Different LLM agent harnesses discover project context via different files — Claude Code reads `CLAUDE.md`, Cursor reads `.cursor/rules/*.mdc`, Copilot reads `.github/copilot-instructions.md`, Windsurf reads `.windsurf/rules/*.md`, Cline reads `.clinerules/*.md`, and so on. Codex and most modern harnesses read `AGENTS.md` natively (convention standardised by the Linux Foundation Agentic AI Foundation, December 2025).

A portable SDD kit needs a single authoritative root that works across all of them.

## Decision

`AGENTS.md` at the repo root is the canonical source of truth for SDD rules. For harnesses that don't read `AGENTS.md` natively, `agent-sdd init` writes a thin **pointer shim** at the harness-specific path. Shims are one-line redirects (`See @AGENTS.md` style), never content duplicates.

The harness registry is externalised to a data file (`src/agent_sdd/templates/harnesses.yaml`), not hardcoded in Python. Adding a new harness is a data-file change + a new kit release; no code change required.

When a consumer repo already has an `AGENTS.md` with project-specific content, `agent-sdd init` injects the kit's rules inside HTML-comment-delimited sections (`<!-- agent-sdd:begin:<section> -->` / `<!-- agent-sdd:end:<section> -->`) so host prose outside those markers is preserved (see ADR-0008).

## Alternatives Considered

1. **Duplicate rule content into each harness-specific file.** Drift-guaranteed. Rejected — Sensei's ADR-0003 settled the same question with the same answer.
2. **Invent a new root file name** (e.g., `SDD.md`, `.sdd/rules.md`). No harness discovers it natively, converting every harness into a shim target. Rejected.
3. **Single-vendor root** (e.g., `.github/copilot-instructions.md` canonical). Other harnesses must shim to it, inverting the ratio. Rejected.
4. **Auto-detect the current harness at init time.** The same repo is opened by different agents across sessions and team members. Flag-gating one harness breaks the others. Rejected.
5. **AGENTS.md canonical + thin pointer shims** (chosen). Matches the industry convergence, minimises duplication, works for multi-harness consumers.

## Consequences

- The consumer repo carries ~8 shim files (CLAUDE.md, .cursor/rules/agent-sdd.mdc, .github/copilot-instructions.md, .windsurf/rules/agent-sdd.md, .clinerules/agent-sdd.md, .roo/rules/agent-sdd.md, .aiassistant/rules/agent-sdd.md, .kiro/steering/agent-sdd.md). Each is 1–5 lines. Acceptable cost for cross-harness coverage.
- When Cursor or Windsurf change their frontmatter schema, only `harnesses.yaml` needs updating — not every consumer repo.
- Shim files need per-harness frontmatter (Cursor's `alwaysApply: true`, Windsurf's `trigger: always_on`). The shim template for each harness lives in `harnesses.yaml`.

## Config Impact

`harnesses.yaml` is the authoritative list. `specs/cross-harness-shims.md` (Phase B) documents it.

## References

- Linux Foundation Agentic AI Foundation — AGENTS.md convention, December 2025.
- Sensei's ADR-0003 — tool-specific agent hooks — for prior art.
