# Specs

Product intent — WHAT the kit does from its consumers' perspective. See `../development-process.md` § Specs for the layer's role and `§ When to Write a Spec` for the triggers.

## Core specs (shipping in v0.1 / v0.2)

| Spec | Intent | Accepted |
|---|---|---|
| [cli](cli.md) | The `kanon` CLI surface and contracts | v0.1 |
| [template-bundle](template-bundle.md) | What gets scaffolded by `init` and what `upgrade` replaces | v0.1 |
| [cross-harness-shims](cross-harness-shims.md) | The shim registry and per-harness contracts | v0.1 |
| [tiers](tiers.md) | Tier-0 through tier-3 content and triggers | v0.1 |
| [tier-migration](tier-migration.md) | `tier set` semantics — mutable, idempotent, non-destructive | v0.1 |
| [verification-contract](verification-contract.md) | What `kanon verify` guarantees about a consumer repo | v0.1 |
| [protocols](protocols.md) | Prose-as-code judgment procedures at `.kanon/protocols/` | v0.1.0a2 |
| [aspects](aspects.md) | Opt-in discipline bundles; aspects subsume tiers | v0.2.0a1 |
| [worktrees](worktrees.md) | Isolated parallel execution for concurrent LLM agents | v0.2.0a2 |
| [aspect-decoupling](aspect-decoupling.md) | Remove sdd as structurally privileged aspect | v0.2.0a4 |
| [release](release.md) | Disciplined release publishing | v0.2.0a5 |
| [invariant-ids](invariant-ids.md) | Stable anchors for spec invariants | v0.2.0a5 |
| [fidelity-lock](fidelity-lock.md) | Spec-SHA drift detection | v0.2.0a5 |
| [verified-by](verified-by.md) | Invariant-to-test traceability | v0.2.0a5 |
| [testing](testing.md) | Test discipline for LLM-agent-driven repos | v0.2.0a5 |
| [security](security.md) | Hardened defaults for LLM-agent-authored code | v0.2.0a5 |
| [deps](deps.md) | Dependency hygiene for LLM-agent-driven repos | v0.2.0a5 |

## Deferred specs (scheduled for v0.2+)

See [`../plans/roadmap.md`](../plans/roadmap.md). Each is a real spec file with `status: deferred`.

| Spec | Capability | Target |
|---|---|---|
| [spec-graph-tooling](spec-graph-tooling.md) | Atomic rename + orphan detection + spec-diff | v0.2 |
| [ambiguity-budget](ambiguity-budget.md) | Two-agents-one-spec falsifier | v0.2 |
| [multi-agent-coordination](multi-agent-coordination.md) | Reservations ledger + plan SHA + handshake | v0.2 |
| [expand-and-contract-lifecycle](expand-and-contract-lifecycle.md) | Pattern for breaking spec changes | v0.3 |

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
