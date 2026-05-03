---
id: onboarding-agent
status: accepted
date: 2026-04-22
stresses:
  - P-prose-is-code
  - P-cross-link-dont-duplicate
  - P-runtime-non-interception
  - cross-harness-shims
---
# Persona: Onboarding Agent

**One sentence:** An LLM agent — any harness, any model — picking up an unfamiliar repo for the first time and needing to build a correct mental model of what the project is and what rules govern contributions.

## Context

Opens the repo fresh — no memory from prior sessions. Has a limited context window. The agent may be running in Claude Code, Codex, Cursor, Windsurf, Cline, Roo, Kiro, JetBrains AI, or GitHub Copilot. The user asks "implement feature X" or "fix this bug." The agent has seconds to orient before producing its first tool call, and it must emit the correct audit-trail sentence ("Plan at X has been approved" or "Spec at Y has been approved" or "This change is trivial: Z").

Under the protocol-substrate commitment ([ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md)), the agent is the substrate's primary runtime executor: prose gates are enforced by agent compliance, observable from the transcript, not by a runtime supervisor. The substrate's whole identity rests on the onboarding agent reading prose correctly and acting on it.

## Goals with `kanon`

- Discover the boot chain via whatever file its harness reads — `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/*.mdc`, `.github/copilot-instructions.md`, etc. — and follow the boot chain to the authoritative rules.
- Understand the project's process gates (plan-before-build, spec-before-design) before the first edit.
- Discover which aspects are enabled and which contracts apply to the change at hand.
- Work within attention-dilution limits: rules must be front-loaded and short.

## What stresses the substrate

- **Harness variance.** The agent may not read `AGENTS.md` natively. The shim from its harness's rule file must exist and must point at `AGENTS.md`.
- **Context-budget pressure.** The agent's attention drops sharply past ~600 tokens of actionable instruction. The process gates must fit in the high-attention zone of `AGENTS.md`.
- **Forgery pressure.** The audit-trail sentence must be designed such that emitting it falsely is harder than planning correctly. The binary opener (plan-path OR trivial-claim) is the current design.
- **Aspect discovery.** The agent must be able to determine which aspects are enabled at which depths, and which contracts they bring, without scanning the full project tree. The `protocols-index` marker section in `AGENTS.md` and per-aspect README files satisfy this.
- **Substrate vs reference distinction.** The agent must understand that the substrate enables protocols but does not invent them; reference aspects ship the prose. A bare `kanon-core` install with no aspects enabled produces an `AGENTS.md` that says so explicitly, so the agent does not hallucinate gates that aren't active.

## What does NOT stress the substrate

- Historical archaeology (ADR supersession chains, old plans). The onboarding agent is focused on current state, not history. History matters for future-you (a different persona not currently called out).
- Multi-publisher arbitration. When `kanon-` and `acme-` aspects compose, the substrate's resolution rules are deterministic (per `P-publisher-symmetry`); the agent reads the resolved state, not the arbitration rules.

## Success when using `kanon`

- The agent reads `AGENTS.md` + `docs/foundations/vision.md` + `docs/foundations/de-opinionation.md` in that order and has a correct mental model within 30 seconds of opening the repo.
- The agent's first tool call for any non-trivial task is writing a plan file (not an edit). Exceptions are declared via the trivial-criteria checklist.
- The agent's audit-trail sentence is emitted truthfully. Transcript review (and fidelity replay where fixtures exist) surfaces any forgery.
- The agent never attempts to enforce a gate at runtime — it follows the gate or declares exemption. Runtime enforcement is `P-runtime-non-interception`-forbidden; transcripts record compliance.

## Amendments

| Date | ADR | What changed |
|---|---|---|
| 2026-05-01 | [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) | Tier-3 vocabulary replaced with substrate/aspect/contract/publisher; reading order updated to vision + de-opinionation; multi-publisher arbitration added to non-stress list; `P-runtime-non-interception` cited; `stresses:` updated; deferred-roadmap reference removed. |
