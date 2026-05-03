# Architecture Decision Records

Each file in this directory records a single architectural decision with its context, the choice made, alternatives considered, and consequences.

## What is an ADR

An Architecture Decision Record captures a single decision with its context, the choice made, alternatives considered, and consequences. ADRs are the "why" layer — they explain reasoning that might otherwise seem arbitrary to a future reader.

ADRs are NOT the starting point for new work. They are produced DURING design and implementation, as decisions crystallize. A feature might produce zero ADRs (if it follows existing patterns) or several (if it requires novel choices).

ADRs are **immutable** once accepted. To reverse a decision, write a new ADR that supersedes it and set the old one's status to `superseded`.

The immutability rule honours three exception classes for normal lifecycle: (1) **frontmatter-only changes** (status FSM transitions, date updates, `superseded-by:` annotations), (2) **appending a `## Historical Note` (or deeper) section** at the end of the file, and (3) **explicit opt-out via a commit-message trailer** of the form `Allow-ADR-edit: NNNN — <reason>` citing the four-digit ADR number with a non-empty reason. Multiple ADRs can be listed comma-separated; em-dash, en-dash, ASCII hyphen, or colon all work as the separator before the reason. The trailer is the post-hoc audit log for the rare case (typo, factual correction, INV-ID migration) where superseding is the wrong tool. Projects that want to enforce this discipline mechanically can run a CI gate over `git log` against `docs/decisions/*.md`.

## Status values

- `accepted` — decision is committed; behavior must match.
- `accepted (lite)` — ADR-lite format; same weight as `accepted`.
- `provisional` — accepted on current evidence, flagged for review when verification evidence lands (e.g., the protocol it governs gains a passing transcript fixture, or a superseding ADR proves the original wrong). A commitment to revisit, not a deferral.
- `superseded` — replaced by a later ADR. The superseding ADR's number must appear in the original's header.

Authors of new ADRs should prefer `provisional` when the decision governs a feature still in draft or when no fixture has yet validated the design property the decision turns on.

## When to write an ADR

ADRs come in two weights.

### Full ADR (~40 lines)

Use when the decision changes the **model** — new architecture, new enforcement philosophy, genuine debate with multiple viable alternatives. Format: YAML frontmatter (`status`, `date`), then Context, Decision, Alternatives Considered, Consequences, optional Config Impact.

Warranted when:
- The decision has genuine alternatives that were debated.
- A future reader might ask "why was it done this way?" and need a full narrative.
- The decision constrains future work (establishing an invariant, choosing a data format, picking an architecture pattern).
- The decision was debated or reversed a previous approach.

When in doubt whether a decision warrants a full ADR or an ADR-lite, default to full ADR. The cost of over-documenting a decision is low; the cost of under-documenting one that a future contributor needs to understand is high.

### ADR-lite (~12 lines)

Use when the decision changes **behavior within an existing model** — gate changes, default changes, boundary changes. Format: YAML frontmatter (`status`, `date`, `weight: lite`, `protocols: [names]`), then three fields: Decision, Why, Alternative.

Concrete triggers (any one):
1. Changes a human approval gate (adds, removes, or bypasses).
2. Changes a default that alters out-of-box behavior.
3. Moves something from blocked to allowed (or vice versa).
4. Introduces a config knob whose existence encodes a design choice.

### No ADR needed

Bug fixes, threshold tuning, documentation improvements, presentation/formatting changes, adding a new output type that follows existing patterns, routine implementation updates with no meaningful alternative.

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
| [0035](0035-tier-as-uniform-aspect-raise.md) | Tier as uniform aspect-depth raise | accepted | aspects |
| [0036](0036-secure-defaults-config-trust-carveout.md) | Secure-defaults carve-out for same-repo config commands | accepted (lite) | process |
| [0037](0037-profile-rename-and-max.md) | `--profile full` renamed to `all`, new `max` profile added | accepted (lite) | cli |
| [0038](0038-init-merge-into-existing-agents-md.md) | `kanon init` merges into an existing `AGENTS.md` instead of skipping | accepted (lite) | cli |
| [0048](0048-kanon-as-protocol-substrate.md) | kanon as protocol substrate — supersedes kit-shape framing in ADR-0012 | accepted | process |
| [0039](0039-contract-resolution-model.md) | Contract-resolution model — prose contracts → agent-resolved YAML → kernel replay | accepted | process |
| [0040](0040-kernel-reference-runtime-interface.md) | Kernel/reference runtime interface — Python entry-points group `kanon.aspects`; publisher-symmetric registry; substrate-independence invariant | accepted | aspects |
| [0041](0041-realization-shape-dialect-grammar.md) | Realization-shape, dialect grammar, composition algebra — `kanon-dialect:` pin, per-contract `realization-shape:`, `surface:`+`before/after:`+`replaces:` | accepted | aspects |
| [0042](0042-verification-scope-of-exit-zero.md) | Verification scope-of-exit-zero — canonical public claim wording for what `kanon verify` exit-0 means and does NOT mean | accepted | process |
| [0043](0043-distribution-boundary-and-cadence.md) | Distribution boundary, release cadence, recipe artifact — `kanon-core`+`kanon-aspects`+`kanon-kit` meta-alias; kernel-daily / reference-weekly / dialect-quarterly cadence; recipes as inert YAML | accepted | release |
| [0044](0044-substrate-self-conformance.md) | Substrate self-conformance discipline — independence invariant elevated to permanent commitment; self-host as primary correctness probe; CI gate publicly-readable | accepted | process |
| [0045](0045-de-opinionation-transition.md) | De-opinionation transition — Phase 0.5 self-host hand-over before Phase A deletions; canonical 9-step Phase A sequence; clean break, no v0.3.x backward compat | accepted | process |
| [0049](0049-monorepo-layout.md) | Monorepo layout — 6 of 8 §1 rules for the kanon repo's directory shape (per-aspect bundles, `ci/`→`scripts/`, `plans/active`+`archive`, byte-mirror loosen, etc.); §1(2) kernel-flatten + §1(7) aspects-flatten initially deferred | accepted | process |
| [0050](0050-kernel-flatten-deferral.md) | Kernel-flatten deferral — Hatch editable-install constraint blocked the in-place `src/kanon/` → `kernel/` rename via `wheel.sources` source-remap; deferred with three forward-options (A: Python module rename, B: `kernel/kanon/` wrapper, C: skip) — Option A executed in v0.5.0a2 | accepted | process |
| [0051](0051-distribution-naming.md) | Distribution naming for the three-package split — `kanon-core`+`kanon-aspects`+`kanon-kit` (supersedes ADR-0048 names only) | accepted | release |
| [0052](0052-aspects-flatten.md) | Aspects-flatten path selection — defers `src/kanon_reference/` → `aspects/` (same Hatch editable-install constraint as ADR-0050; Option C accepted-debt over Option B's 6–8h rename cost) | draft | process |

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
