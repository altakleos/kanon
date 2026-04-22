---
status: accepted
date: 2026-04-22
---
# ADR-0006: Tier model semantics — consumer insulation, producer-facing migration runbooks

## Context

`agent-sdd` needs to serve projects across a wide complexity range: from a 200-line CLI utility to a multi-team platform project. A single uniform "full SDD" method would overwhelm the former; a single uniform "minimal SDD" would underserve the latter. The kit adopts a tiered model.

Tiers insulate consumer experience — a tier-0 consumer never sees tier-3 artifacts or their associated process gates. They do **not** insulate producer experience — migrating between tiers is an active operation with its own failure modes (see ADR-0008).

## Decision

Four tiers, each a strict superset of the one below:

| Tier | For | Adds |
|---|---|---|
| 0 | Vibe-coding, prototypes, short-lived scripts | `AGENTS.md` + `CLAUDE.md` shim + `.agent-sdd/config.yaml`. No `docs/` structure. |
| 1 | Solo developer shipping a real tool | + `docs/development-process.md`, `docs/decisions/`, `docs/plans/`. Plan-before-build gate active. |
| 2 | Team work with user-facing promises | + `docs/specs/`. Spec-before-design gate active. |
| 3 | Platform projects, multi-team, cross-cutting concerns | + `docs/design/`, `docs/foundations/` (vision, principles, personas). |

Tier is stored in `.agent-sdd/config.yaml` (field: `tier`). The CLI reads this field to determine expected layout and which AGENTS.md sections to enable. Tier is **not** inferred from filesystem contents (that would be ambiguous when a user deletes a directory).

Each AGENTS.md section that is tier-dependent (notably `§Required: Plan Before Build` and `§Required: Spec Before Design`) is delimited by HTML comment markers (see ADR-0008) so `tier set` can enable/disable them idempotently without touching user content.

## Alternatives Considered

1. **Single uniform method, no tiers.** Scale-mismatch — "sledgehammer for every task." Documented as a classic failure mode by the methodology researcher agent. Rejected.
2. **Two tiers (minimal + full).** Too coarse. A solo-dev shipping a real tool needs ADRs; a team shipping user-facing software needs specs. Collapsing these gives users the wrong trade-off. Rejected.
3. **Five+ tiers.** Diminishing returns; tier boundaries become arbitrary. Four was the minimum that cleanly captured the four classes of project the design team identified. Chosen.
4. **Tier inferred from filesystem contents.** Ambiguous and fragile. Rejected (see ADR-0008).

## Consequences

- Every consumer repo declares its tier explicitly in `.agent-sdd/config.yaml`.
- `agent-sdd verify` computes the expected file set as a function of declared tier and hard-fails if expected files are missing.
- Cross-tier consumer dependencies (a tier-3 library depending on a tier-0 utility) do not break the kit — each consumer is validated against its own tier. Dependency-level concerns (a tier-3 library's spec requiring invariants the tier-0 utility's non-spec can't encode) are a *producer* concern handled via runbooks, not a kit-level assertion.
- **Scope note for v0.1**: all four tier templates ship in v0.1 (per the session plan). This is not the original scope; it was expanded after the user pushed back on "tier-3 dogfood example only" positioning.

## Config Impact

`.agent-sdd/config.yaml`:

```yaml
kit_version: "0.1.0a1"
tier: 1                  # 0 | 1 | 2 | 3 — mutable via `agent-sdd tier set`
```

## References

- Fair-adversary agent report — tier-migration failure modes.
- Friction critic agent report — "sledgehammer problem" and tier need.
- Session plan — v0.1 scope clarification on all-four-tiers.
