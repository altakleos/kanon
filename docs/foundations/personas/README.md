# Personas

Design-stressing scenarios the substrate must serve. Each persona carries a `stresses:` list pointing at the specs and principles it exercises.

## Active

| ID | Role | Stress dimensions |
|---|---|---|
| [solo-with-agents](solo-with-agents.md) | Single human, N concurrent LLM agents on the same repo | Agent-agent collision, worktree isolation, resolution-determinism, cross-publisher composition |
| [acme-publisher](acme-publisher.md) | Third-party engineer or organization authoring a contract bundle for kanon | Dialect grammar conformance, capability collision, recipe authorship, validator entry-point stability |
| [onboarding-agent](onboarding-agent.md) | Any LLM agent picking up an unfamiliar repo | Boot-chain discoverability, process-gate clarity, substrate-vs-reference distinction, runtime-non-interception |

## Superseded

Per [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md), two kit-shape personas were retired when kanon committed to becoming a protocol substrate. Their stress dimensions (tier vocabulary, multi-team adoption story, tier-3 platform-team ergonomics) no longer apply. Bodies preserved per the immutability discipline; future plans may resurrect either persona under protocol-mode framing if and when the audience becomes real.

| ID | Role | Superseded by |
|---|---|---|
| [solo-engineer](solo-engineer.md) | Single developer shipping a real tool | [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) |
| [platform-team](platform-team.md) | Multi-team platform engineering group | [ADR-0048](../../decisions/0048-kanon-as-protocol-substrate.md) |
