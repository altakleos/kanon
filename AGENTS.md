# AGENTS.md — kanon Source Repository

You are operating the `kanon` source repository. This is the upstream project — the kit itself. Users install this kit via `pip install kanon` and run `kanon init` to scaffold their own projects.

This repo is itself an `kanon` project, operating at **tier 3** (the highest tier). See [`.kanon/config.yaml`](.kanon/config.yaml) for the current tier and kit-version pin.

## What `kanon` Is

A portable, self-hosting kit packaging the Spec-Driven Development (SDD) methodology as prose the agent reads and obeys. See [`docs/foundations/vision.md`](docs/foundations/vision.md).

## Contributor Boot Chain

0. Read [`docs/foundations/vision.md`](docs/foundations/vision.md) — what `kanon` is and is not.
1. Read [`docs/development-process.md`](docs/development-process.md) — the SDD method (project-agnostic).
2. Read [`docs/kanon-implementation.md`](docs/kanon-implementation.md) — how this project instantiates Implementation and Verification.
3. Read [`docs/decisions/README.md`](docs/decisions/README.md) — what has already been decided.
4. **Before editing any source file** for a non-trivial change, produce a plan and wait for approval — see § "Required: Plan Before Build" below. The full artifact flow (spec → design → ADR → plan → implementation → verification) is in [`docs/development-process.md`](docs/development-process.md) § "How Work Flows Through the Layers".
5. **Before writing a design doc, ADR, plan, or implementation** for a new user-visible capability, produce a spec and wait for approval — see § "Required: Spec Before Design" below.

For the roadmap of deferred capabilities, see [`docs/plans/roadmap.md`](docs/plans/roadmap.md).

## Project Layout

```
kanon/
├── AGENTS.md                 (this file — contributor entry point, tier-3)
├── CLAUDE.md                 (Claude Code shim pointing at AGENTS.md)
├── README.md                 (install + quickstart)
├── pyproject.toml            (pip package metadata)
├── docs/
│   ├── development-process.md  (project-agnostic SDD reference)
│   ├── kanon-implementation.md
│   ├── foundations/            (vision, principles, personas)
│   ├── specs/                  (product intent — includes status: deferred specs)
│   ├── design/                 (technical architecture)
│   ├── decisions/              (ADRs — see decisions/README.md for index)
│   └── plans/                  (task breakdowns + roadmap.md)
├── src/kanon/
│   ├── __init__.py
│   ├── cli.py                  (click CLI: init/upgrade/verify/tier)
│   └── kit/                    (unified bundle — manifest.yaml + agents-md/ + files/ + sections/ + protocols/)
└── tests/                    (CLI, kit integrity, tier-migration round-trip)
```

## Key Constraints

- `docs/development-process.md` is **project-agnostic**. Do not mention the kit's own CLI commands, tier model specifics, or any `kanon`-brand terms in it. Kit-specific material lives in `docs/kanon-implementation.md`.
- **Process rules belong in `docs/development-process.md`**. README files in artifact directories (`specs/`, `design/`, `plans/`, `decisions/`, `foundations/`) carry indexes, templates, and pointers — not process definitions. When adding a new process concept, put it in the method doc and add a pointer from the relevant README.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.
- The kit bundle at `src/kanon/kit/` shares source of truth with this repo's own `docs/`, `AGENTS.md` section markers, and `.kanon/protocols/`. `ci/check_kit_consistency.py` enforces byte-equality against a narrow whitelist (see ADR-0011).
- Tier membership is data in `src/kanon/kit/manifest.yaml`. To scaffold a new file at tier-N for consumers, add it under `kit/files/` or `kit/protocols/` and list its path under the appropriate `tier-N` entry in the manifest. Strict-superset semantics are preserved by manifest-union.

<!-- kanon:begin:sdd/plan-before-build -->
## Required: Plan Before Build

For any non-trivial change, your **first output** is a plan file under `docs/plans/<slug>.md` (feature-scoped) or `~/.claude/plans/` (session-scoped), followed by explicit user approval. You may not call Edit, Write, or mutating Bash on source files before the user has approved the plan.

A change is **non-trivial** (plan first) if any of these apply:

- touches more than one function, file, or public symbol
- adds, removes, or pins a dependency
- changes a CLI flag, public schema, JSON/YAML shape, or protocol prose
- warrants a CHANGELOG entry
- multiple agents will collaborate on it
- you are unsure which side of this line it falls on

A change is **trivial** (act directly, no plan needed) only if:

- typo in a comment or string literal
- fixing a single failing assertion with an unambiguous fix
- renaming a local variable
- deleting code the caller can prove is unreachable

**Before your first source-modifying tool call, state in one sentence:** "Plan at `<path>` has been approved." If you cannot truthfully emit that sentence, stop and plan. This sentence is the audit trail — its absence in a transcript is how violations get caught.

**Retroactive plans are evidence of past violation, not a norm.** If you see commits labeled "retroactive plan for X shipped in vY.Z", a prior agent skipped this rule and the user had to ask them to paper over it. Do not add to that pile.
<!-- kanon:end:sdd/plan-before-build -->

<!-- kanon:begin:sdd/spec-before-design -->
## Required: Spec Before Design

For any change that introduces a new user-visible capability, your **first output** is a spec file at `docs/specs/<slug>.md`, followed by explicit user approval. You may not write a design doc, ADR, plan, or implementation before the spec is approved.

A change **needs a spec** (spec first) if any of these apply:

- introduces a new CLI command, mode, or subcommand
- adds a new output dimension users can observe or consume
- makes a new guarantee to users that must survive implementation changes
- multiple design approaches exist and the spec constrains which are viable
- you are unsure whether it falls below this line

A change **does NOT need a spec** (skip directly to design/plan/implementation) if it is:

- an implementation refactor that preserves observable behaviour
- a configuration-value or threshold adjustment
- a single-file bug fix
- adding a check, validator, or test
- adding a new output type that follows an existing pattern already governed by a spec

**Before your first design-doc, ADR, plan, or source-modifying tool call, state in one sentence:** "Spec at `<path>` has been approved." If you cannot truthfully emit that sentence, stop and write the spec.

**Design-doc skip.** A design doc may be skipped when all four conditions in [`docs/development-process.md` § When to Skip a Design Doc](docs/development-process.md#when-to-skip-a-design-doc) hold (pattern instantiation, single-concern scope, spec carries the reasoning, plan exists). The skip must be declared in the plan's frontmatter as `design: "Follows ADR-NNNN"` **before** implementation begins — retroactive declarations don't count.
<!-- kanon:end:sdd/spec-before-design -->

<!-- kanon:begin:protocols-index -->
## Active protocols

Prose-as-code procedures available at this tier. When a trigger fires, read the protocol file in full and follow its numbered steps.

| Protocol | Tier min | Invoke when |
| --- | --- | --- |
| [`tier-up-advisor`](.kanon/protocols/tier-up-advisor.md) | 1 | The user or agent is considering raising this project's kanon tier, or asks "should we tier up?" |
| [`verify-triage`](.kanon/protocols/verify-triage.md) | 1 | A `kanon verify` run returns a non-ok status, or the user asks "what does this verify report mean?" |
| [`spec-review`](.kanon/protocols/spec-review.md) | 2 | A draft spec is ready for review (status:draft), or the user asks for a spec review, or a spec is about to be promoted to status:accepted |
<!-- kanon:end:protocols-index -->

## Contribution Conventions

- **Commit messages** — prefer [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Convention only, no CI gate.
- **Changelog** — append every user-visible change to `## [Unreleased]` in `CHANGELOG.md` in the same commit that introduces it. Don't batch at release time. Refactors, internal tests, and docs-only edits don't need a changelog entry.
- **Version references** — always write pre-release versions in full (`v0.1.0a9` or `0.1.0a9`), never the bare suffix (`a9`). A bare suffix is a PEP 440 pre-release marker that attaches to any `X.Y.Z`.

## References

- [`docs/development-process.md`](docs/development-process.md) — the SDD method
- [`docs/kanon-implementation.md`](docs/kanon-implementation.md) — kanon's instantiation
- [`docs/decisions/README.md`](docs/decisions/README.md) — ADR index
- [`docs/foundations/vision.md`](docs/foundations/vision.md) — product vision
- [`docs/plans/roadmap.md`](docs/plans/roadmap.md) — deferred capabilities
