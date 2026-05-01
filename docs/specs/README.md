# Specs

Product intent — WHAT the project does from the user's perspective.

## What is a spec

A spec describes WHAT the project does from a product perspective. It is implementation-agnostic — a spec makes sense even if the entire technical architecture changed. Specs capture product intent before any design work begins.

A spec answers: What problem does this solve? What properties must the output have? What invariants must always hold? What is explicitly out of scope?

A spec-level statement describes a user-facing property or invariant without naming any mechanism, data format, or executor. If a sentence mentions which component stores something, which language implements it, or which process runs it, it has crossed into design or implementation territory. See the project's instantiation doc for concrete examples of spec-level invariants.

Specs come BEFORE ADRs. They define the intent that ADRs record decisions about. A feature might reference an existing spec (most new work serves an existing product guarantee) or require a new one (when the project takes on a genuinely new capability).

Specs are named descriptively, not numbered chronologically, because they represent product capabilities with no meaningful ordering — unlike ADRs, where chronological sequence is load-bearing (later decisions build on earlier ones).

Specs use a lightweight format: YAML frontmatter (`status`, `date`, plus optional foundation backreferences `serves`, `realizes`, `stressed_by`, and fixture fields `fixtures`, `fixtures_deferred`), then sections for Intent, Invariants, Rationale, Out of Scope, and Decisions.

### Fixture-naming convention

Any spec claiming to `realize:` a principle or `serve:` a foundation must name at least one concrete fixture that proves it — a test file, a transcript fixture, or an E2E test. If no fixture yet exists, use `fixtures_deferred:` with a reason.

## Core specs (shipping in v0.1 / v0.2)

| Spec | Intent | Accepted |
|---|---|---|
| [cli](cli.md) | The `kanon` CLI surface and contracts | v0.1 |
| [template-bundle](template-bundle.md) | What gets scaffolded by `init` and what `upgrade` replaces | superseded by ADR-0048 — kit-shape bundle retired under protocol-substrate commitment |
| [cross-harness-shims](cross-harness-shims.md) | The shim registry and per-harness contracts | v0.1 |
| [tiers](tiers.md) | Tier-0 through tier-3 content and triggers | superseded by ADR-0048 — tier vocabulary retired; depths are per-aspect dials |
| [tier-migration](tier-migration.md) | `tier set` semantics — mutable, idempotent, non-destructive | superseded by ADR-0048 — tier vocabulary retired |
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
| [fidelity](fidelity.md) | Tier-1 behavioural-conformance verification (lexical replay over committed transcripts) | v0.3 |
| [aspect-config](aspect-config.md) | Aspect configuration values (`kanon aspect set-config`) | v0.2.0a6 |
| [aspect-provides](aspect-provides.md) | Aspect capability namespace (`provides:`) | v0.2.0a6 |
| [process-gates](process-gates.md) | Process-gate CI enforcement | v0.2.0a7 |
| [project-aspects](project-aspects.md) | Project-defined aspects — consumer-specific discipline | v0.2.0a7 |
| [scaffold-v2](scaffold-v2.md) | Thin kernel, routing-index AGENTS.md, three file categories | v0.2.0a12 |
| [kanon-banner](kanon-banner.md) | `kanon` brand banner across init, upgrade, and AGENTS.md | v0.3.0a7 |

## Deferred specs (scheduled for v0.2+)

See [`../plans/roadmap.md`](../plans/roadmap.md). Each is a real spec file with `status: deferred`.

| Spec | Capability | Target |
|---|---|---|
| [spec-graph-tooling](spec-graph-tooling.md) | Atomic rename + orphan detection + spec-diff | superseded — split into `spec-graph-rename`, `spec-graph-orphans`, `spec-graph-diff` |
| [ambiguity-budget](ambiguity-budget.md) | Two-agents-one-spec falsifier | v0.2 |
| [multi-agent-coordination](multi-agent-coordination.md) | Reservations ledger + plan SHA + handshake | v0.2 |
| [expand-and-contract-lifecycle](expand-and-contract-lifecycle.md) | Pattern for breaking spec changes | v0.3 |
| [spec-graph-diff](spec-graph-diff.md) | Invariant-level diff between two snapshots | v0.3+ |
| [spec-graph-orphans](spec-graph-orphans.md) | Find unreferenced nodes in the cross-link graph | v0.3 |
| [spec-graph-rename](spec-graph-rename.md) | Atomic slug rename across the cross-link graph | v0.3 |

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
