---
status: accepted
date: 2026-04-24
---
# ADR-0022: Security aspect — hardened defaults for LLM-agent-authored code

## Context

LLM agents produce predictable security anti-patterns: hardcoded secrets, string-interpolated SQL, disabled TLS, permissive CORS. A single pushed secret is irreversible. No existing aspect addresses secure coding practices.

## Decision

1. **Depth range 0–2.** Depth 0 = opt-out. Depth 1 = prose guidance (protocol + AGENTS.md section). Depth 2 = prose + CI pattern scanner.
2. **No cross-aspect dependency.** `requires: []`. Security is useful at every maturity level.
3. **Language-agnostic.** Protocols describe principles. CI validator uses generic regex patterns.
4. **Best-effort detection.** The CI validator is a safety net, not a SAST replacement.
5. **Stability: experimental.**

## Alternatives Considered

**Depth 0–3 with threat modeling.** Rejected — threat modeling is too heavyweight for an aspect.
**Require sdd >= 1.** Rejected — security matters even for vibe-coding prototypes.

## Consequences

- New aspect directory `src/kanon/kit/aspects/security/`.
- Fifth shipping aspect.
- CI validator `ci/check_security_patterns.py` at depth 2.

## References

- [Spec: Security](../specs/security.md)
- [Spec: Aspects](../specs/aspects.md)
