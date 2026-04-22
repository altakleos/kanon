---
status: accepted
date: 2026-04-22
realizes:
  - P-tiers-insulate
stressed_by:
  - solo-engineer
  - platform-team
fixtures_deferred: "Cross-tier tests (subset invariant, byte-equality) land in Phase D (ci/check_template_consistency.py, tests/test_template_integrity.py)"
---
# Spec: Tiers — content and triggers

## Intent

Define the four tiers — tier-0 through tier-3 — by what artifacts each includes, when a project should adopt each, and how one tier relates to the next.

## Invariants

1. **Tier taxonomy.** Four tiers, in strict inclusion order.
   - **Tier-0** — `AGENTS.md` + harness shims + `.agent-sdd/config.yaml`. No `docs/` structure. No process gates active.
   - **Tier-1** — Tier-0 plus `docs/development-process.md` + `docs/decisions/` (README + _template) + `docs/plans/` (README + _template). **Plan-before-build gate active** in AGENTS.md.
   - **Tier-2** — Tier-1 plus `docs/specs/` (README + _template). **Spec-before-design gate active** in AGENTS.md.
   - **Tier-3** — Tier-2 plus `docs/design/` (README + _template) + `docs/foundations/` (vision, principles/, personas/, README).
2. **Triggers (suggested, not enforced).**
   - Move to tier-1 when: shipping anything beyond a prototype; more than one session's worth of work; want to remember decisions.
   - Move to tier-2 when: making user-visible promises; specs constrain implementation; second developer joins.
   - Move to tier-3 when: multiple teams consume the project; cross-cutting vision needs capturing; compliance or audit requirements.
3. **Strict inclusion.** Every file in tier-N exists in tier-(N+1). The converse — tier-(N+1) has files tier-N doesn't — is what makes tiers additive.
4. **Tier is stored explicitly** in `.agent-sdd/config.yaml` (`tier: <N>`). Not inferred from filesystem contents (see ADR-0008 for rationale).
5. **Tier is mutable.** `agent-sdd tier set` migrates between any two tiers; see `tier-migration.md`.
6. **Process gates are tier-dependent.**
   - Plan-before-build: active at tier ≥ 1.
   - Spec-before-design: active at tier ≥ 2.
   - At tier-0, no gates are active — the kit is giving the consumer a pointer to AGENTS.md and nothing else.
7. **AGENTS.md section enablement.** The section-marker rewriter (see `tier-migration.md`) enables/disables kit-managed AGENTS.md sections according to tier. User content outside the markers is never touched.

## Rationale

Four tiers was the minimum that cleanly captured the four meaningful classes of project the design team identified: prototype, solo-shipped-tool, team-with-promises, platform-scale. Fewer tiers forces users with genuinely different needs into the same mold; more tiers creates arbitrary distinctions and confuses users.

Gate activation is tier-dependent because the gates cost friction — asking a tier-0 prototype to plan before every change wastes time; not asking a tier-2 team library defeats the point.

## Out of Scope

- Cross-tier dependency contracts (tier-3 library depending on tier-0 utility). Producer concern, deferred to a v0.2 runbook.
- Per-artifact tier overrides ("this spec is tier-2 but that plan is tier-1"). Not a real need surfaced in design.

## Decisions

See ADR-0006 (tier semantics), ADR-0008 (tier migration).
