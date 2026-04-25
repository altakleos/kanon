---
status: accepted (lite)
date: 2026-04-25
weight: lite
---
# ADR-0026: `provides:` capability registry + generalised `requires:`

## Decision

Each top-level aspect entry in `src/kanon/kit/manifest.yaml` may declare an optional `provides: [<capability>, ...]` list. The existing `requires:` field is generalised to accept two predicate forms in the same list:

- **Depth predicate** (3 whitespace-separated tokens): `"sdd >= 1"` — semantics unchanged.
- **Capability presence** (1 token matching `^[a-z][a-z0-9-]*$`): `"planning-discipline"` — satisfied iff at least one enabled aspect declares the capability in its `provides:`.

The token-count discriminator routes parsing unambiguously. `ci/check_kit_consistency.py` hard-fails when any capability-presence predicate references a capability no aspect provides.

## Why

Aspect renames today silently re-target every `"sdd >= 1"`-style predicate that names the renamed aspect. A capability namespace decouples *what* an aspect provides from *which* aspect supplies it, so future aspects (e.g., a hypothetical `lean-sdd` providing `planning-discipline`) can substitute for `sdd` without breaking dependents. Generalising the existing field beats adding a parallel `requires-capabilities:` field because kit authors already model dependencies as a single list — splitting that list into two places would force them to mentally route every dependency twice (which field, then which predicate). The capability-name regex (no underscores, no whitespace, no operators) cannot match anything that would parse as a depth predicate's first token in a 3-token form, so the discriminator has zero ambiguity. No predicate that succeeds today changes meaning under the generalised parser; only 1-token predicates that today raise `ValueError: not enough values to unpack` now resolve cleanly as capability checks.

## Alternative

Add a parallel `requires-capabilities: [...]` field. Rejected because it grows the kit-author surface for no semantic gain — both forms are dependencies and belong in one place.

## References

- [`docs/specs/aspect-provides.md`](../specs/aspect-provides.md) — the contract.
- [ADR-0012](0012-aspect-model.md) — aspect model this extends.
- [ADR-0009](0009-project-rename-from-agent-sdd-to-kanon.md) — concrete example of an aspect-name rename, the cost this ADR insures against.
