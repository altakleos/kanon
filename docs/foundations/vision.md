---
status: accepted
date: 2026-04-23
---
# Vision — What `kanon` Is, and What It Is Not

## What `kanon` Is

`kanon` is a portable, self-hosting kit that packages development disciplines — starting with Spec-Driven Development (SDD) and worktree isolation — as prose an LLM agent reads and obeys. A single pointer in the consumer repo's `CLAUDE.md` or `AGENTS.md` is enough to make any LLM-agent-driven project process-disciplined: plans before building, specs before designing, verification alongside implementation.

Three properties define the kit:

1. **Portable.** Works across Claude Code, OpenAI Codex, Cursor, GitHub Copilot, Windsurf, Cline, Roo Code, JetBrains AI, and Kiro via a per-harness shim registry. New harnesses are added to a data file; no code change required.
2. **Aspect-oriented.** Disciplines are packaged as *aspects* — opt-in bundles of prose rules, protocols, AGENTS.md sections, and scaffolded files. Each aspect has its own depth dial: `sdd` spans 0–3 (vibe-coding to full platform-scale SDD); `worktrees` spans 0–2 (prose guidance to scripted automation). `kanon aspect set-depth` moves any aspect between depths non-destructively. The legacy `kanon tier set` command is preserved as sugar for the `sdd` aspect's depth.
3. **Self-hosting.** The kit is itself a `kanon` project running `sdd` at depth 3 and `worktrees` at depth 2. Its own `docs/` tree shares source of truth with the templates it ships; CI enforces byte-equality. If you can't use the kit to develop the kit, the kit isn't good enough.

## Current Promises

A consumer repo that adopts `kanon` gets:

- **Aspect-based opt-in discipline** — enable only the aspects you need (`sdd`, `worktrees`, and future aspects). Each aspect has a depth dial; projects grow without ceremony they don't need yet.
- **Plan-before-build and spec-before-design gates** in AGENTS.md that any major LLM agent harness will read and honour (via the `sdd` aspect).
- **Worktree isolation for concurrent agents** — prose guidance and optional shell helpers so parallel agents don't collide in a shared working tree (via the `worktrees` aspect).
- **Cross-harness consistency** — the same rules apply in Claude Code, Cursor, Codex, and the rest, via pointer shims that never duplicate content.
- **Non-destructive aspect lifecycle** — aspects are added, depth-adjusted, or removed without losing user content. Files scaffolded by a removed aspect stay on disk.
- **Verification as first-class authoritative source** (per ADR-0004) — tests and fixtures are co-authored with specs, not derived from them.
- **Model-version compatibility signals** (per ADR-0005) — transcript fixtures declare which model versions they were validated against; `kanon verify` warns when a fixture hasn't been re-run on the current model.
- **A roadmap of `status: deferred` specs** so a fresh session can discover what's coming without reading external plans.

## Non-Goals

`kanon` explicitly does not:

- **Generate code from specs.** There is no deterministic spec-to-code compiler. Agents read specs and write code; the kit does not try to close that loop mechanically.
- **Ship harness-specific enforcement hooks for agent behavior.** The kit does not intercept, block, or validate LLM-agent actions at runtime — no harness adapters, no session daemons, no tool-call filters. LLM agency rises to meet prose gates; agents don't need runtime supervision. *Scope carve-out:* reference automation snippets for cryptographic, irreversible, or stateful operations the *consumer* executes (release-pipeline GitHub Actions templates, pre-commit configs, Makefile targets) are in scope for aspects that package those operations. See [ADR-0013](../decisions/0013-vision-amendment-reference-automation.md).
- **Replace product-management tooling.** Plans and ADRs are engineering artifacts. If a project needs Jira, Linear, or a product-roadmap tool, that lives outside the kit.
- **Prescribe what counts as "trivial" at fine granularity.** The kit ships a decision checklist; teams tune it to their context inside their AGENTS.md project-specific blocks (outside the kit-managed HTML-comment sections).
- **Serve broad public adoption in v0.1.** The primary audience is the author's company's future projects. Open source because there's no reason to gate it; not optimised for random external adoption until patterns stabilise.

## Why It Exists

Sensei, the reference implementation, is a pedagogy product built under proprietary SDD discipline. As the author moved on to plan other projects, the obvious question was: should each project reinvent SDD, or should the method be packaged and shared? Packaging wins for two reasons: the conventions reduce per-project overhead, and the accumulated craft (atomic-write contracts, cross-harness shims, CI validators, transcript fixtures) shouldn't be reconstructed from scratch every time.

`kanon` is the packaging. Sensei remains the reference implementation that proves the method under real pedagogy constraints.

## Design Stance — "Specs Are Source"

In an AI-coded future where humans read specs far more than they read generated code, SDD artifacts become the authoritative source. A spec is not documentation of code; the code is a compiled artifact of the spec. This stance reframes the value of more SDD layers: under "specs are overhead" logic, fewer layers is better; under "specs are source" logic, each layer captures authoritative knowledge no other layer can. The kit is opinionated toward the latter frame — captured as principle `P-specs-are-source` (Phase B).

## Success Criteria

### v0.1 (achieved)

- The `kanon` repo itself passes `kanon verify .` as a tier-3 consumer.
- `kanon init <target> --tier <N>` produces a valid project for every N ∈ {0, 1, 2, 3}.
- Tier migration chain (0 → 1 → 2 → 3 → back) preserves user-authored content end-to-end.
- PyPI release cut without manual intervention beyond the trusted-publishing gate.

### v0.2 (achieved)

- Aspects subsume tiers: `sdd` is the first aspect; `kanon tier set` is preserved as sugar.
- The kit ships **six aspects**: `sdd` (stable, depth 0–3), `worktrees`, `release`, `testing`, `security`, `deps` (all `experimental`, depths 0–2 or 0–3). Each declares a capability under the `provides:` registry (ADR-0026), so future aspects can substitute without breaking dependents.
- The kit self-hosts the full set (`sdd:3`, `worktrees:2`, `release:2`, `testing:3`, `security:2`, `deps:2`) and `kanon verify .` passes with no warnings.
- `kanon aspect set-config` and `aspect add --config` give consumers a typed CLI surface for per-aspect configuration values (ADR-0025).
- Two deferred specs from the v0.1 roadmap have shipped: `fidelity-lock` (spec-SHA drift detection) and `invariant-ids` (stable per-invariant anchors with `verified-by` traceability).

### v0.2 (ongoing)

- The remaining deferred specs (`spec-graph-tooling`, `ambiguity-budget`, `multi-agent-coordination`, `expand-and-contract-lifecycle`) land one by one without forcing a second method redesign.

## Amendment Trail

| Date | ADR | What changed |
|---|---|---|
| 2026-04-23 | [ADR-0013](../decisions/0013-vision-amendment-reference-automation.md) | Non-Goal #2 scope carve-out for reference automation snippets |
| 2026-04-23 | [ADR-0015](../decisions/0015-vision-amendment-aspect-identity.md) | §What kanon Is, §Current Promises, §Success Criteria updated to reflect aspect model |