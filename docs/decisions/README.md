# Architecture Decision Records

Each file in this directory records a single architectural decision with its context, the choice made, alternatives considered, and consequences.

See [`../sdd-method.md`](../sdd-method.md) § ADRs for the format, status taxonomy (extended to include `deferred` per ADR-0007), and when-to-write rules.

## Index

| ADR | Title | Status | Category |
|---|---|---|---|
| [0001](0001-distribution-as-pip-package.md) | Distribution as pip package | accepted | kit-internals |
| [0002](0002-self-hosted-bootstrap.md) | Self-hosted bootstrap — commits 1–3 are pre-SDD | accepted | process |
| [0003](0003-agents-md-canonical-root.md) | AGENTS.md is the canonical root; shims are pointers | accepted | kit-internals |
| [0004](0004-verification-co-authoritative-source.md) | Verification is a co-authoritative source, not compiled output | accepted | process |
| [0005](0005-model-version-compatibility-contract.md) | Model-version compatibility contract (`validated-against:`) | accepted | process |
| [0006](0006-tier-model-semantics.md) | Tier model semantics — consumer insulation, producer-facing migration runbooks | accepted | aspects |
| [0007](0007-status-taxonomy.md) | Status taxonomy — adds `deferred` as a first-class value | accepted | process |
| [0008](0008-tier-migration.md) | Tier migration is mutable, idempotent, non-destructive | accepted | aspects |
| [0009](0009-project-rename-from-agent-sdd-to-kanon.md) | Project rename from `agent-sdd` to `kanon` | accepted | kit-internals |
| [0010](0010-protocol-layer.md) | Protocol layer — prose-as-code judgment procedures at `.kanon/protocols/` | accepted | process |
| [0011](0011-kit-bundle-refactor.md) | Kit bundle refactor — `templates/` → `kit/` with manifest-driven tier membership | accepted | kit-internals |
| [0012](0012-aspect-model.md) | Aspect model — aspects subsume tiers; SDD becomes the first aspect | accepted | aspects |
| [0013](0013-vision-amendment-reference-automation.md) | Vision amendment — reference automation snippets are kit-shippable | accepted | kit-internals |
| [0014](0014-worktrees-aspect.md) | Worktrees aspect — isolated parallel execution via git worktrees | accepted | aspects |
| [0015](0015-vision-amendment-aspect-identity.md) | Vision amendment — aspect-oriented identity | accepted | aspects |
| [0016](0016-aspect-decoupling.md) | Aspect decoupling — remove sdd as structurally privileged | accepted | aspects |
| [0017](0017-release-aspect.md) | Release aspect — disciplined release publishing | accepted | release |
| [0018](0018-invariant-ids.md) | Invariant IDs — stable anchors for spec invariants | accepted | testing |
| [0019](0019-fidelity-lock.md) | Fidelity Lock — spec-SHA drift detection | accepted | testing |
| [0020](0020-verified-by.md) | Verified-By — invariant-to-test traceability | accepted | testing |
| [0021](0021-testing-aspect.md) | Testing aspect — test discipline for LLM-agent-driven repos | accepted | testing |
| [0022](0022-security-aspect.md) | Security aspect — hardened defaults for LLM-agent-authored code | accepted | aspects |
| [0023](0023-deps-aspect.md) | Deps aspect — dependency hygiene for LLM-agent-driven repos | accepted | aspects |
| [0024](0024-crash-consistent-atomicity.md) | Crash-consistent atomicity for multi-file CLI operations | accepted | cli |
| [0025](0025-aspect-config-parsing.md) | Aspect-config CLI parsing — YAML scalar + optional schema | accepted (lite) | cli |
| [0026](0026-aspect-provides-and-generalised-requires.md) | `provides:` capability registry + generalised `requires:` | accepted (lite) | aspects |
| [0027](0027-graph-rename-ops-manifest.md) | Ops-manifest extension to ADR-0024 for `kanon graph rename` | accepted (lite) | cli |
| [0028](0028-project-aspects.md) | Project-defined aspects via prefixed source-namespacing | accepted | aspects |
| [0029](0029-verification-fidelity-replay-carveout.md) | Verification-contract carve-out for fidelity-fixture replay | accepted (lite) | testing |
| [0030](0030-recovery-model.md) | Recovery model — auto-replay for graph-rename, idempotent re-run for the rest | accepted (lite) | cli |
| [0031](0031-fidelity-aspect.md) | `kanon-fidelity` aspect — Tier-1 behavioural-conformance verification | superseded | testing |
| [0032](0032-adr-immutability-gate.md) | ADR-immutability gate — mechanical enforcement with a calibrated escape hatch | accepted | process |
| [0033](0033-fidelity-quantitative-families.md) | Fidelity quantitative assertion families and turn-format extensibility | accepted | testing |
| [0034](0034-routing-index-agents-md.md) | Routing-index AGENTS.md — refined enforcement proximity | accepted | process |

**Reading guide:** Focus on ADRs matching your task's category. For CLI work, read `cli` + `aspects`. For test work, read `testing`. For process questions, read `process`. The `kit-internals` category is relevant only when modifying the kit bundle or scaffold logic.

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

See `../sdd-method.md` § When to Write an ADR for the full/lite distinction and triggers.
