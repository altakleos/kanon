---
status: deferred
date: 2026-04-22
realizes:
  - P-specs-are-source
  - P-verification-co-authored
target-release: v0.2
---
# Spec: Ambiguity budget — two-agents-one-spec falsifier

## Intent

Provide a mechanical falsifier for the specs-as-source claim. For each sampled spec invariant, invoke two independent agents with only the spec as context, ask each to implement the invariant, diff the outputs. High divergence means the spec underspecifies. Over time, an "ambiguity budget" per spec trends toward zero as the spec tightens.

## Problem

`P-specs-are-source` is aspirational until there's a test that says whether a spec is actually a sufficient source. Without such a test, the claim is unfalsifiable — it cannot be wrong, which (per the fair adversary) is itself a problem. The ambiguity budget gives the method a scorable health metric.

## Sketched invariants

1. `agent-sdd ambiguity-budget [--spec <path>] [--agents <n>] [--seed <seed>]` invokes N ≥ 2 agents against the spec's invariants.
2. Each agent receives only: the spec file, relevant foundation files (principles referenced by `realizes:`), and a neutral "implement this" prompt. No code context.
3. Outputs are diffed at a semantic level — (deferred sub-question) either AST-level for code, behavioural-level for tests, or simple text diff. v0.2 starts with text diff, refines.
4. The run produces a per-spec divergence score. Budget: the project declares an acceptable maximum divergence per spec; `agent-sdd verify` can consume the score and warn when budget is exceeded.
5. Cost-gated: ambiguity-budget runs are expensive (LLM calls). Consumers opt in per-spec or per-CI-run; not on every `verify` invocation.

## Out of Scope in v0.1

All of it. v0.1 does not ship API-key integration, ambiguity measurement, or divergence scoring.

## Why deferred

Requires model-access orchestration the kit does not yet own. Requires decisions about diff semantics. Requires cost model. v0.2 is the earliest realistic target; may slip to v0.3.

## References

- Fair-adversary agent report during v0.1 planning — "ambiguity-budget as the one CI falsifier."
- User confirmation on adoption.
