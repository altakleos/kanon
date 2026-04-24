---
status: accepted
date: 2026-04-24
---
# ADR-0023: Deps aspect — dependency hygiene for LLM-agent-driven repos

## Context

LLM agents add dependencies casually — unpinned versions, phantom imports, duplicate-purpose libraries. Concurrent agents multiply the problem. No existing aspect addresses dependency management discipline.

## Decision

1. **Depth range 0–2.** Depth 0 = opt-out. Depth 1 = prose guidance (protocol + AGENTS.md section). Depth 2 = prose + CI validator.
2. **No cross-aspect dependency.** `requires: []`.
3. **Language-agnostic.** Protocols describe principles. CI validator recognizes common manifest formats.
4. **Stability: experimental.**

## Alternatives Considered

**Integrate with security aspect.** Rejected — dependency hygiene and security are different concerns (supply-chain security is a subset of security, not all of deps).
**Require sdd >= 1.** Rejected — dependency hygiene is useful even for prototypes.

## Consequences

- New aspect directory `src/kanon/kit/aspects/deps/`.
- Sixth shipping aspect.

## References

- [Spec: Deps](../specs/deps.md)
