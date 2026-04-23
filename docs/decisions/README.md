# Architecture Decision Records

Each file in this directory records a single architectural decision with its context, the choice made, alternatives considered, and consequences.

See [`../development-process.md`](../development-process.md) § ADRs for the format, status taxonomy (extended to include `deferred` per ADR-0007), and when-to-write rules.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-distribution-as-pip-package.md) | Distribution as pip package | accepted |
| [0002](0002-self-hosted-bootstrap.md) | Self-hosted bootstrap — commits 1–3 are pre-SDD | accepted |
| [0003](0003-agents-md-canonical-root.md) | AGENTS.md is the canonical root; shims are pointers | accepted |
| [0004](0004-verification-co-authoritative-source.md) | Verification is a co-authoritative source, not compiled output | accepted |
| [0005](0005-model-version-compatibility-contract.md) | Model-version compatibility contract (`validated-against:`) | accepted |
| [0006](0006-tier-model-semantics.md) | Tier model semantics — consumer insulation, producer-facing migration runbooks | accepted |
| [0007](0007-status-taxonomy.md) | Status taxonomy — adds `deferred` as a first-class value | accepted |
| [0008](0008-tier-migration.md) | Tier migration is mutable, idempotent, non-destructive | accepted |
| [0009](0009-project-rename-from-agent-sdd-to-kanon.md) | Project rename from `agent-sdd` to `kanon` | accepted |

## ADR Template

```markdown
---
status: draft | accepted | accepted (lite) | deferred | provisional | superseded
date: YYYY-MM-DD
---
# ADR-NNNN: <Title>

## Context
## Decision
## Alternatives Considered
## Consequences
## Config Impact (optional)
## References
```

See `../development-process.md` § When to Write an ADR for the full/lite distinction and triggers.
