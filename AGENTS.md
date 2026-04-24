# AGENTS.md — kanon Source Repository

You are operating the `kanon` source repository. This is the upstream project — the kit itself. Users install this kit via `pip install kanon-kit` (the PyPI distribution is `kanon-kit`; the import / CLI name remains `kanon`) and run `kanon init` to scaffold their own projects.

This repo is itself a `kanon` project, operating at `sdd` depth 3 and `worktrees` depth 2. See [`.kanon/config.yaml`](.kanon/config.yaml) for the current aspect depths and kit-version pin.

## What `kanon` Is

A portable, self-hosting kit packaging development disciplines — starting with Spec-Driven Development and worktree isolation — as prose the agent reads and obeys. See [`docs/foundations/vision.md`](docs/foundations/vision.md).

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
├── AGENTS.md                 (this file — contributor entry point)
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
│   ├── cli.py                  (click CLI: init/upgrade/verify/tier/aspect)
│   ├── _manifest.py            (kit manifest loading, aspect queries)
│   ├── _scaffold.py            (AGENTS.md assembly, config I/O, bundle building)
│   ├── _atomic.py              (crash-safe atomic file writes)
│   └── kit/                    (aspect bundles — manifest.yaml + aspects/{sdd,worktrees}/)
└── tests/                    (CLI, kit integrity, aspect lifecycle, E2E)
```

## Key Constraints

- `docs/development-process.md` is **project-agnostic**. Do not mention the kit's own CLI commands, aspect/depth model specifics, or any `kanon`-brand terms in it. Kit-specific material lives in `docs/kanon-implementation.md`.
- **Process rules belong in `docs/development-process.md`**. README files in artifact directories (`specs/`, `design/`, `plans/`, `decisions/`, `foundations/`) carry indexes, templates, and pointers — not process definitions. When adding a new process concept, put it in the method doc and add a pointer from the relevant README.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.
- The kit bundle at `src/kanon/kit/` shares source of truth with this repo's own `docs/`, `AGENTS.md` section markers, and `.kanon/protocols/`. `ci/check_kit_consistency.py` enforces byte-equality against a narrow whitelist (see ADR-0011).
- Aspect membership is data in `src/kanon/kit/manifest.yaml` (aspect registry) and per-aspect sub-manifests at `src/kanon/kit/aspects/<name>/manifest.yaml`. To scaffold a new file at depth-N for consumers, add it under `kit/aspects/<name>/files/` or `kit/aspects/<name>/protocols/` and list its path under the appropriate `depth-N` entry in the sub-manifest. Strict-superset semantics are preserved by manifest-union.

<!-- kanon:begin:sdd/plan-before-build -->
## Required: Plan Before Build

For any non-trivial change, your **first output** is a plan file under `docs/plans/<slug>.md`, followed by explicit user approval. You may not call Edit, Write, or mutating Bash on source files before the user has approved the plan.

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

**Retroactive plans are evidence of past violation, not a norm.** Do not add to that pile.
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
<!-- kanon:end:sdd/spec-before-design -->

<!-- kanon:begin:protocols-index -->
## Active protocols

Prose-as-code procedures available at this depth. When a trigger fires, read the protocol file in full and follow its numbered steps.

### release (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`release-checklist`](.kanon/protocols/release/release-checklist.md) | 1 | A release is being prepared, or the user asks to cut a release |

### sdd (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`tier-up-advisor`](.kanon/protocols/sdd/tier-up-advisor.md) | 1 | The user or agent is considering raising this project's sdd depth, or asks "should we increase depth?" |
| [`verify-triage`](.kanon/protocols/sdd/verify-triage.md) | 1 | A `kanon verify` run returns a non-ok status, or the user asks "what does this verify report mean?" |
| [`spec-review`](.kanon/protocols/sdd/spec-review.md) | 2 | A draft spec is ready for review (status:draft), or the user asks for a spec review, or a spec is about to be promoted to status:accepted |

### testing (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`test-discipline`](.kanon/protocols/testing/test-discipline.md) | 1 | Writing or modifying code |
| [`ac-first-tdd`](.kanon/protocols/testing/ac-first-tdd.md) | 2 | Implementing a plan or spec invariant at testing depth >= 2 |

### worktrees (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`worktree-lifecycle`](.kanon/protocols/worktrees/worktree-lifecycle.md) | 1 | A multi-file or multi-step change is about to begin, or `git worktree list` shows active worktrees from other work streams |
<!-- kanon:end:protocols-index -->

<!-- kanon:begin:worktrees/branch-hygiene -->
## Worktree Branch Hygiene

Use a dedicated git worktree for any change that touches multiple files or requires multiple steps. Trivial single-file edits (typos, one-liner fixes) stay in the main checkout.

**When to create a worktree:**

- The change is multi-file or multi-step.
- `git worktree list` shows other worktrees — parallel work is likely in progress.
- You are unsure — prefer isolation; an unnecessary worktree is harmless.

**Worktree location and naming:**

- Path: `.worktrees/<slug>/` where `<slug>` derives from the plan or task name.
- Branch: `wt/<slug>` — always use this prefix for worktree branches.

**Integration cadence:**

- Rebase from `main` before starting significant new work in the worktree.
- Resolve conflicts immediately — do not let them accumulate.

**Teardown rules:**

- Never force-remove a worktree with uncommitted changes.
- Commit or stash all work before running `git worktree remove`.
- Delete the `wt/<slug>` branch only after it has been merged.
<!-- kanon:end:worktrees/branch-hygiene -->

<!-- kanon:begin:worktrees/body -->
The `worktrees` aspect is active with automation helpers. Multi-file or multi-step changes should be isolated in git worktrees under `.worktrees/<slug>/`.

## Key Constraints

- Worktree creation is triggered by **change scope**, not concurrency detection.
- Never force-remove a worktree with uncommitted changes.
- Branch naming convention: `wt/<slug>`.
- Use the helper scripts in `scripts/` for consistent lifecycle management:
  - `scripts/worktree-setup.sh <slug>` — create a worktree
  - `scripts/worktree-teardown.sh <slug>` — safely remove a worktree
  - `scripts/worktree-status.sh` — list all active worktrees

<!-- kanon:begin:worktrees/branch-hygiene -->
## Worktree Branch Hygiene

Use a dedicated git worktree for any change that touches multiple files or requires multiple steps. Trivial single-file edits (typos, one-liner fixes) stay in the main checkout.

**When to create a worktree:**

- The change is multi-file or multi-step.
- `git worktree list` shows other worktrees — parallel work is likely in progress.
- You are unsure — prefer isolation; an unnecessary worktree is harmless.

**Worktree location and naming:**

- Path: `.worktrees/<slug>/` where `<slug>` derives from the plan or task name.
- Branch: `wt/<slug>` — always use this prefix for worktree branches.

**Integration cadence:**

- Rebase from `main` before starting significant new work in the worktree.
- Resolve conflicts immediately — do not let them accumulate.

**Teardown rules:**

- Never force-remove a worktree with uncommitted changes.
- Commit or stash all work before running `git worktree remove`.
- Delete the `wt/<slug>` branch only after it has been merged.
<!-- kanon:end:worktrees/branch-hygiene -->
<!-- kanon:end:worktrees/body -->

<!-- kanon:begin:sdd/body -->
A `kanon` project with `sdd` at depth 3. Full stack: foundations + specs + design + ADRs + plans + verification. All process gates are active.

## Boot chain

0. Read [`docs/foundations/vision.md`](docs/foundations/vision.md) — what the project is and is not.
1. Read [`docs/development-process.md`](docs/development-process.md) — the SDD method.
2. Read [`docs/decisions/README.md`](docs/decisions/README.md) — what has already been decided.
3. **Before editing any source file** for a non-trivial change, produce a plan and wait for approval — see § "Required: Plan Before Build" below.
4. **Before writing a design doc, ADR, plan, or implementation** for a new user-visible capability, produce a spec and wait for approval — see § "Required: Spec Before Design" below.

## Key Constraints

- Process rules belong in `docs/development-process.md`. README files in artifact directories carry indexes and templates, not process definitions.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.
- Principles in `docs/foundations/principles/` are the project's cross-cutting stances. Specs and ADRs reference them via frontmatter.

<!-- kanon:begin:sdd/plan-before-build -->
## Required: Plan Before Build

For any non-trivial change, your **first output** is a plan file under `docs/plans/<slug>.md`, followed by explicit user approval. You may not call Edit, Write, or mutating Bash on source files before the user has approved the plan.

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

**Retroactive plans are evidence of past violation, not a norm.** Do not add to that pile.
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
<!-- kanon:end:sdd/spec-before-design -->

<!-- kanon:begin:protocols-index -->
## Active protocols

Prose-as-code procedures available at this depth. When a trigger fires, read the protocol file in full and follow its numbered steps.

### release (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`release-checklist`](.kanon/protocols/release/release-checklist.md) | 1 | A release is being prepared, or the user asks to cut a release |

### sdd (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`tier-up-advisor`](.kanon/protocols/sdd/tier-up-advisor.md) | 1 | The user or agent is considering raising this project's sdd depth, or asks "should we increase depth?" |
| [`verify-triage`](.kanon/protocols/sdd/verify-triage.md) | 1 | A `kanon verify` run returns a non-ok status, or the user asks "what does this verify report mean?" |
| [`spec-review`](.kanon/protocols/sdd/spec-review.md) | 2 | A draft spec is ready for review (status:draft), or the user asks for a spec review, or a spec is about to be promoted to status:accepted |

### testing (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`test-discipline`](.kanon/protocols/testing/test-discipline.md) | 1 | Writing or modifying code |
| [`ac-first-tdd`](.kanon/protocols/testing/ac-first-tdd.md) | 2 | Implementing a plan or spec invariant at testing depth >= 2 |

### worktrees (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`worktree-lifecycle`](.kanon/protocols/worktrees/worktree-lifecycle.md) | 1 | A multi-file or multi-step change is about to begin, or `git worktree list` shows active worktrees from other work streams |
<!-- kanon:end:protocols-index -->

## References

- [`docs/foundations/vision.md`](docs/foundations/vision.md) — product vision
- [`docs/foundations/principles/`](docs/foundations/principles/) — cross-cutting stances
- [`docs/development-process.md`](docs/development-process.md) — the SDD method
- [`docs/decisions/README.md`](docs/decisions/README.md) — ADR index
- [`docs/specs/README.md`](docs/specs/README.md) — spec index
- [`docs/design/README.md`](docs/design/README.md) — design doc index
- [`docs/plans/README.md`](docs/plans/README.md) — plan index
<!-- kanon:end:sdd/body -->

<!-- kanon:begin:release/body -->
The `release` aspect is active with automation helpers. Follow the release checklist protocol before cutting any release.

- `ci/release-preflight.py` — validates version, changelog, tests, and lint before publish.
- `.github/workflows/release.yml` — reference CI workflow triggered by version tags.

<!-- kanon:begin:release/publishing-discipline -->
## Release Publishing Discipline

Every release follows a strict sequence: prepare, validate, tag, publish.

**Version bump:** Update `__version__` in `__init__.py` (or the project's canonical version source) and add a CHANGELOG entry for the new version before any other release step.

**Pre-release checks:** All of the following must pass before tagging:

- Full test suite (`pytest`)
- Lint (`ruff check`)
- `kanon verify .`

**Tag creation:** Create an annotated tag `vX.Y.Z` only after all checks pass. Never tag a dirty tree or a commit with failing checks.

**Publish gate:** CI workflow triggered by tag push handles build and publish. Manual `twine upload` or equivalent is a fallback, not the default.

**CHANGELOG is the source of truth** for release notes. Every user-visible change gets an entry before the release tag is created.

**Never publish without passing preflight checks.** A release that skips validation is a rollback waiting to happen.
<!-- kanon:end:release/publishing-discipline -->
<!-- kanon:end:release/body -->

<!-- kanon:begin:testing/body -->
The `testing` aspect is active with automated enforcement. Follow the test-discipline and ac-first-tdd protocols when writing or modifying code.

- At depth 2+: translate plan acceptance criteria into failing tests before implementation.
- For spec invariants: red-green-refactor loop.
- `ci/check_test_quality.py` — validates test quality (no empty tests, no assert-True-only, coverage floor).

<!-- kanon:begin:testing/test-discipline -->
## Test Discipline

Tests exist to protect behavior, not to produce a green badge. Every code change follows these rules:

**Tests accompany code changes.** Every new function, behavior change, or bug fix gets a test in the same commit or adjacent commit. No untested code ships.

**Tests are not deleted without justification.** When removing a test, document what now covers the behavior it protected, or acknowledge the coverage gap. Never delete a test solely because it's failing — fix the code or fix the test.

**Assertions are not weakened to make tests pass.** Changing an expected value requires explaining why the old value was wrong. If the test is failing, the implementation is wrong — not the test.

**Prefer test-first.** Before implementing, consider "how will I verify this works?" and let that shape the implementation. Write the test, watch it fail, then implement.

**Maintain coverage at or above the configured floor.** The coverage floor is declared in `.kanon/config.yaml` under `aspects.testing.config.coverage_floor` (default 80%). Do not merge changes that drop coverage below this threshold.

**At depth 2+: AC-first testing.** Translate plan acceptance criteria into failing tests before implementation. For spec invariants, follow the red-green-refactor loop. See the `ac-first-tdd` protocol.
<!-- kanon:end:testing/test-discipline -->
<!-- kanon:end:testing/body -->

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
