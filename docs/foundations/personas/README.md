# Personas

Design-stressing scenarios the kit must serve. Each persona carries a `stresses:` list pointing at the specs and principles it exercises.

## Index

| ID | Role | Stress dimensions |
|---|---|---|
| [solo-engineer](solo-engineer.md) | Single developer shipping a real tool | Tier-0 → tier-1 migration, low-friction adoption |
| [solo-with-agents](solo-with-agents.md) | Single human, N concurrent LLM agents on the same repo | Agent-agent collision, worktree isolation, reservation mechanics |
| [platform-team](platform-team.md) | Multi-team platform engineering group | Tier-3 scale, cross-tier dependencies, reviewer ergonomics |
| [onboarding-agent](onboarding-agent.md) | Any LLM agent picking up an unfamiliar repo | Boot-chain discoverability, process-gate clarity |
