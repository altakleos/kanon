---
id: P-prose-is-code
kind: technical
status: accepted
date: 2026-04-22
---
# Prose read by an LLM runtime is code

## Statement

Prose consumed by an LLM agent as instructions is code. It must be reviewed, versioned, tested, and held to the same standard of unambiguity as a compiled programming language. Ambiguity in an instruction is a bug in the same sense that an undefined variable is a bug.

## Rationale

LLM agents execute prose the way a CPU executes bytecode. If the instruction is imprecise, the agent either fails, misbehaves, or rationalises a wrong answer. The consequence is identical to runtime UB in traditional code, except that detection is harder because the executor is stochastic.

## Implications

- Every prose artifact in the kit (AGENTS.md, sdd-method.md, each spec, each ADR, each principle) is authored with the same care as a Python module.
- Changes to prose instructions are reviewed for unambiguity, not just grammar.
- Sections that gate agent behaviour (plan-before-build, spec-before-design) carry audit-trail sentences (forced-token gates) that make compliance observable from the transcript.
- Prose length matters — instructions buried past line ~600 in a document attract less attention from the reader and the model. Kit documents are kept short where they gate behaviour, long where they explain context.

## Exceptions / Tensions

The principle is weaker for non-gating prose — principle descriptions, vision narratives, history. Those can be written for a human reader first. But if a prose block ever becomes load-bearing for agent behaviour, it must be refactored to the instruction-grade standard.

## Source

Sensei's foundational principle of the same name, ported unchanged. The user's company has been piloting this discipline inside Sensei for months; `kanon` packages the discipline.
