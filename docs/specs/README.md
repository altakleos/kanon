# Specs

Product intent — WHAT the kit does from its consumers' perspective. See `../development-process.md` § Specs for the layer's role and `§ When to Write a Spec` for the triggers.

## Core specs (shipping in v0.1)

| Spec | Intent |
|---|---|
| [cli](cli.md) | The `agent-sdd` CLI surface and contracts |
| [template-bundle](template-bundle.md) | What gets scaffolded by `init` and what `upgrade` replaces |
| [cross-harness-shims](cross-harness-shims.md) | The shim registry and per-harness contracts |
| [tiers](tiers.md) | Tier-0 through tier-3 content and triggers |
| [tier-migration](tier-migration.md) | `tier set` semantics — mutable, idempotent, non-destructive |
| [verification-contract](verification-contract.md) | What `agent-sdd verify` guarantees about a consumer repo |

## Deferred specs (scheduled for v0.2+)

See [`../plans/roadmap.md`](../plans/roadmap.md). Each is a real spec file with `status: deferred`.

| Spec | Capability | Target |
|---|---|---|
| [fidelity-lock](fidelity-lock.md) | Spec-SHA ↔ artifact-SHA commitment file | v0.2 |
| [spec-graph-tooling](spec-graph-tooling.md) | Atomic rename + orphan detection + spec-diff | v0.2 |
| [ambiguity-budget](ambiguity-budget.md) | Two-agents-one-spec falsifier | v0.2 |
| [multi-agent-coordination](multi-agent-coordination.md) | Reservations ledger + plan SHA + handshake | v0.2 |
| [expand-and-contract-lifecycle](expand-and-contract-lifecycle.md) | Pattern for breaking spec changes | v0.3 |
| [invariant-ids](invariant-ids.md) | Stable per-invariant anchors + `verified_by:` | v0.2 |

## Template

```markdown
---
status: draft | accepted | deferred | provisional | superseded
date: YYYY-MM-DD
realizes: [P-slug, ...]      # optional; principles this spec embodies
serves: [slug, ...]          # optional; foundations/specs this one supports
stressed_by: [persona-slug]  # optional
fixtures: [tests/path]       # required if realizes/serves declared
# or:
fixtures_deferred: reason
---
# Spec: <title>

## Intent
## Invariants
## Rationale
## Out of Scope
## Decisions
```
