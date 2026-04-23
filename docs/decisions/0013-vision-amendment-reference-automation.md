---
status: accepted
date: 2026-04-23
---
# ADR-0013: Vision amendment — reference automation snippets are kit-shippable for deterministic-tail operations

## Context

`docs/foundations/vision.md` § Non-Goals currently reads:

> Ship harness-specific enforcement hooks. The base kit is prose-only. Harness-specific enforcement adapters (Claude Code hooks, pre-commit scripts, etc.) are out of scope — the kit's premise is that LLM agency is rising to meet prose gates.

This clause was authored when the only discipline kanon packaged was Spec-Driven Development. SDD is prose-gate-shaped: every step (plan, spec, design, ADR, review) is a judgment an LLM agent performs. "Prose-only" makes sense in that context — the agent *is* the enforcer.

The aspect model (ADR-0012) absorbs disciplines beyond SDD. Some of those disciplines contain irreducibly non-prose operations:

- **Cryptographic** — signing a tag, generating an SLSA provenance attestation, publishing via OIDC-provisioned PyPI credentials.
- **Irreversible** — pushing to a public registry, cutting a GitHub Release, triggering a deploy.
- **Persistent state across sessions** — dependency-triage ledgers, incident action-item tracking, worktree staleness detection.

No LLM-agency trajectory turns "sign this tag" into a prose-executable step. A `release` aspect that refuses to ship a reference GitHub Action leaves every consumer reinventing the same workflow — the opposite of the scaffolding discipline kanon exists to provide.

The question: may the kit ship *reference automation snippets* for operations the consumer (human or CI) executes deterministically, without violating the prose-only promise on **agent** behavior?

## Decision

**Yes, with a narrow scope.** The kit may ship reference automation snippets — GitHub Actions YAML, pre-commit configs, Makefile targets, similar — for operations that are (a) cryptographic, (b) irreversible, or (c) require persistent state. These snippets are scaffolded under the relevant aspect's `files/` tree and treated like any other kit-shipped file (byte-equality enforced, non-destructively added/removed).

The prose-only promise remains in force for **agent-behavior gating**. The kit still does not ship:

- Runtime hooks that intercept, block, or validate LLM-agent actions.
- Harness-specific enforcement adapters (Claude Code hooks, session daemons, tool-call filters).
- Runtime supervisors or process monitors.

The narrowing applies only to **reference templates for deterministic operations the consumer — not the agent — executes**.

### Before-state (vision.md § Non-Goals, current item #2)

> Ship harness-specific enforcement hooks. The base kit is prose-only. Harness-specific enforcement adapters (Claude Code hooks, pre-commit scripts, etc.) are out of scope — the kit's premise is that LLM agency is rising to meet prose gates.

### After-state (applied to vision.md in the same commit that lands this ADR)

> Ship harness-specific enforcement hooks for agent behavior. The kit does not intercept, block, or validate LLM-agent actions at runtime — no harness adapters, no session daemons, no tool-call filters. The premise is that LLM agency rises to meet prose gates, not that agents need runtime supervision.
>
> (Reference automation snippets for cryptographic, irreversible, or stateful operations the *consumer* executes — release-pipeline GitHub Actions templates, pre-commit configs, Makefile targets — are in scope for aspects that package those operations. See ADR-0013.)

### Why

Without this narrowing, any aspect with a deterministic tail (release, publish, dependency-triage, signing) fails its purpose: prose describing a workflow without a template to copy leaves every consumer authoring the same boilerplate. The narrowing holds the line where the line matters (no agent supervision) without foreclosing scaffolding of non-agent operations.

## Alternatives Considered

1. **Leave the prose-only promise intact; document operations in prose, scaffold nothing.** Rejected: every consumer reinvents the same `release.yml`; the kit's value as a discipline-packager collapses for any discipline with a deterministic tail.
2. **Allow any kit-shipped enforcement, including agent-behavior hooks.** Rejected: violates the vision's core stance that LLM agency meets prose gates, and reintroduces harness-coupling that ADR-0003's pointer-shim model deliberately avoided.
3. **Ship automation as a sibling package (e.g., `kanon-release-ci`).** Rejected for v0.2: consumers who want the aspect want the snippets; a separate package is an arbitrary boundary to cross. Revive if reference-snippet surface grows past maintainability in-tree.
4. **Make snippet-shipping a per-aspect opt-in via config.** Rejected: a consumer who wants the aspect wants the snippets; making opt-out the default is a footgun. Consumers who don't want a kit-shipped `release.yml` delete it like any other file (drift is reported by `verify`).

## Consequences

- **Vision text is edited in place** in the same commit that lands this ADR. The `date:` frontmatter in `vision.md` bumps; the ADR is the archaeological trail for the wording change.
- **Aspects may include `.github/workflows/`, `.pre-commit-config.yaml`, `Makefile`, and similar files** under their scaffolded-files tree, subject to the exclusive-ownership invariant from the aspects spec.
- **`ci/check_kit_consistency.py` whitelist grows** by the snippet count per aspect. Must stay under the ~50-entry maintenance red line.
- **Byte-equality applies to snippets** — a consumer who edits a kit-shipped `release.yml` triggers a drift warning on `kanon verify`, consistent with how consumer edits to `docs/development-process.md` are treated today.
- **Non-goal #2 becomes narrower but sharper.** "No runtime agent supervision" is more defensible than "prose-only everything"; it matches what the kit actually delivers post-aspects.

## References

- `docs/foundations/vision.md` — § Non-Goals clause this ADR supersedes; edited in place on landing.
- ADR-0012 — the aspect model that makes this narrowing necessary.
- ADR-0003 — canonical-AGENTS.md-with-shims (the cross-harness discipline this ADR preserves on the agent-behavior side).
- `docs/specs/aspects.md` — invariant 8 (reference automation snippets are kit-shippable).
