---
id: P-runtime-non-interception
kind: technical
tier: public-protocol
status: accepted
date: 2026-05-01
---
# The substrate does not intercept LLM-agent behaviour at runtime

## Statement

The substrate MUST NOT acquire a runtime component that intercepts, blocks, validates, or supervises LLM-agent actions. Prose gates are enforced by *agent compliance* — observable from transcripts after the fact — not by *runtime supervision* before it. No daemon, no harness adapter, no session monitor, no tool-call filter compensates for non-compliant agents. If an agent does not honour a prose gate, the failure surfaces in the transcript and in `kanon verify`'s evidence layer, not at the moment of the would-be violation.

## Rationale

`P-prose-is-code` makes prose the source of truth for agent behaviour; runtime supervision would invert that — a session monitor blocking an attempted edit before the audit sentence is emitted trusts code-as-code, with prose as an advisory comment. Three downstream costs of runtime supervision argue for this refusal:

1. **Adapter proliferation.** Every harness (Claude Code, Cursor, Codex, Windsurf, …) has different tool-call shapes; a supervisor would need an adapter per harness. Cross-harness coverage becomes fragile in exactly the surface area the substrate's shim registry was designed to keep simple.
2. **Identity collapse.** If the substrate enforces gates at runtime, the substrate is a runtime tool, not a prose substrate. The aspect model, the cross-harness shims, the dialect grammar — all become subordinate to "the supervisor." `acme-` publishers would author against the supervisor's behaviour, not against the published prose.
3. **Falsifiability erosion.** Runtime supervision hides agent non-compliance. Without supervision, transcripts surface non-compliance as an absent audit sentence — which fidelity replay catches. With supervision, the agent does what the supervisor lets it do; the substrate cannot distinguish an obedient agent from a constrained one.

The substrate refuses runtime supervision and accepts the cost: agents that ignore prose gates produce visible failures, and the substrate's job is to make those failures auditable, not to prevent them.

## Implications

- **No agent-harness adapters.** The substrate ships no code that runs inside any harness's tool-call path. Cross-harness reach is achieved through `harnesses.yaml` shim files (pointers, not interceptors).
- **No session daemons.** The substrate has no long-running process. `kanon` is invoked, runs, exits. No background watcher, no pre-commit-time agent-monitor, no MCP server **shipped by `kanon-core`**. Consumers may install MCP integrations of their own; the substrate does not require, ship, or supervise any.
- **No tool-call filters.** The substrate does not validate, transform, or block tool calls an agent makes inside a harness.
- **Gates are forced-token sentences, not interceptions.** Audit-trail sentences (per `P-prose-is-code`) are the enforcement mechanism: their absence in a transcript is how violations get caught, after the fact.
- **`kanon verify` is read-only against committed evidence.** It examines committed `.dogfood.md` captures, manifests, and resolutions; it does not invoke an agent or replay a session.
- **Reference automation snippets are consumer-executed, not substrate-executed.** GitHub Actions templates, pre-commit configs, Makefile targets that aspects ship are run *by the consumer's CI/git/build system*, not by the substrate. (Carve-out per [ADR-0013](../../decisions/0013-vision-amendment-reference-automation.md).)

## Exceptions / Tensions

- **`kanon preflight` runs subprocess commands.** This is a consumer-executed command runner; the consumer authors the commands in `.kanon/preflight.yaml` (or, in the protocol-substrate model, the resolutions YAML). The substrate orchestrates execution but does not intercept the agent's prior decisions. Trust boundary: repo write-access (per [ADR-0036](../../decisions/0036-secure-defaults-config-trust-carveout.md)).
- **Resolution replay in CI executes invocations.** Same trust model: invocations are committed YAML; CI replays mechanically; the substrate is not supervising an agent at the moment of replay. The agent's decisions were made on a developer machine and committed.
- **Fidelity replay reads transcripts.** `kanon verify` evaluates regex assertions against committed `.dogfood.md` captures. This is a *read-after-the-fact* operation, not interception. The carve-out is text-only (no subprocess, no LLM, per [ADR-0029](../../decisions/0029-verification-fidelity-replay-carveout.md) INV-10).

These three are not exceptions to non-interception — they are the substrate's actual behaviour. Each runs against committed evidence after agent decisions have been made. None of them sits between an agent and its tool call.

## Source

Promoted from [`vision.md`](../vision.md)'s Non-Goal #2 to a public-tier principle by [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md). The promotion was recommended by the document-specialist's prior-art analysis (rounds 4–5 of panel review): every protocol that lasted 20+ years had one architectural-decision-as-axiom that all subsequent work deferred to. For TCP/IP it was end-to-end; for Smalltalk it was uniform message passing; for kanon it is runtime non-interception. Living the commitment as a Non-Goal made it erodable; living it as a public-tier principle anchors it. The principle is part of the substrate's published protocol commitments; it is versioned with the dialect and immutable post-acceptance.
