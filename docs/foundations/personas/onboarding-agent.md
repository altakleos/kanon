---
id: onboarding-agent
status: accepted
date: 2026-04-22
stresses:
  - P-prose-is-code
  - P-cross-link-dont-duplicate
  - template-bundle
  - cross-harness-shims
---
# Persona: Onboarding Agent

**One sentence:** An LLM agent — any harness, any model — picking up an unfamiliar repo for the first time and needing to build a correct mental model of what the project is and what rules govern contributions.

## Context

Opens the repo fresh — no memory from prior sessions. Has a limited context window. The agent may be running in Claude Code, Codex, Cursor, Windsurf, Cline, Roo, Kiro, or JetBrains AI. The user asks "implement feature X" or "fix this bug." The agent has seconds to orient before producing its first tool call, and it must emit the correct audit-trail sentence ("Plan at X has been approved" or "Spec at Y has been approved" or "This change is trivial: Z").

## Goals with `agent-sdd`

- Discover the boot chain via whatever file its harness reads — `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.mdc`, `.github/copilot-instructions.md`, etc. — and follow the boot chain to the authoritative rules.
- Understand the project's process gates (plan-before-build, spec-before-design) before the first edit.
- Discover deferred capabilities via `docs/plans/roadmap.md` so it doesn't propose re-inventing something the project already intends to build.
- Work within attention-dilution limits: rules must be front-loaded and short.

## What stresses the kit

- **Harness variance.** The agent may not read `AGENTS.md` natively. The shim from its harness's rule file must exist and must point at `AGENTS.md`.
- **Context-budget pressure.** The agent's attention drops sharply past ~600 tokens of actionable instruction. The process gates must fit in the high-attention zone of AGENTS.md.
- **Forgery pressure.** The audit-trail sentence must be designed such that emitting it falsely is harder than planning correctly. The binary opener (plan-path OR trivial-claim) is the current design.
- **Roadmap discoverability.** The agent must be able to name the deferred capabilities from a single file (`docs/plans/roadmap.md`) without chasing links.

## What does NOT stress the kit

- Historical archaeology (ADR supersession chains, old plans). The onboarding agent is focused on current state, not history. History matters for future-you (a different persona not currently called out but worth naming: "six-months-later-you" — may add in a future revision).

## Success when using `agent-sdd`

- The agent reads `AGENTS.md` + `docs/foundations/vision.md` + `docs/plans/roadmap.md` in that order and has a correct mental model within 30 seconds of opening the repo.
- The agent's first tool call for any non-trivial task is writing a plan file (not an edit). Exceptions are declared via the trivial-criteria checklist.
- The agent's audit-trail sentence is emitted truthfully. Transcript review surfaces any forgery.
