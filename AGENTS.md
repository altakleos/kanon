# AGENTS.md — kanon Source Repository

You are operating the `kanon` source repository. This is the upstream project — the kit itself. Users install this kit via `pip install kanon-kit` (the PyPI distribution is `kanon-kit`; the import / CLI name remains `kanon`) and run `kanon init` to scaffold their own projects.

This repo is itself a `kanon` project, operating at `sdd` depth 3 and `worktrees` depth 2. See [`.kanon/config.yaml`](.kanon/config.yaml) for the current aspect depths and kit-version pin.

## What `kanon` Is

A portable, self-hosting kit packaging development disciplines — starting with Spec-Driven Development and worktree isolation — as prose the agent reads and obeys. See [`docs/foundations/vision.md`](docs/foundations/vision.md).

## Contributor Boot Chain

0. Read [`docs/foundations/vision.md`](docs/foundations/vision.md) — what `kanon` is and is not.
1. Read [`docs/sdd-method.md`](docs/sdd-method.md) — the SDD method (project-agnostic).
2. Read [`docs/kanon-implementation.md`](docs/kanon-implementation.md) — how this project instantiates Implementation and Verification.
3. Read [`docs/decisions/README.md`](docs/decisions/README.md) — what has already been decided.
4. **Before editing any source file** for a non-trivial change, produce a plan and wait for approval — see § "Required: Plan Before Build" below. The full artifact flow (spec → design → ADR → plan → implementation → verification) is in [`docs/sdd-method.md`](docs/sdd-method.md) § "How Work Flows Through the Layers".
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
│   ├── sdd-method.md  (project-agnostic SDD reference)
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

- `docs/sdd-method.md` is **project-agnostic**. Do not mention the kit's own CLI commands, aspect/depth model specifics, or any `kanon`-brand terms in it. Kit-specific material lives in `docs/kanon-implementation.md`.
- **Process rules belong in `docs/sdd-method.md`**. README files in artifact directories (`specs/`, `design/`, `plans/`, `decisions/`, `foundations/`) carry indexes, templates, and pointers — not process definitions. When adding a new process concept, put it in the method doc and add a pointer from the relevant README.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.
- The kit bundle at `src/kanon/kit/` shares source of truth with this repo's own `docs/`, `AGENTS.md` section markers, and `.kanon/protocols/`. `ci/check_kit_consistency.py` enforces byte-equality against a narrow whitelist (see ADR-0011).
- Aspect membership is data in `src/kanon/kit/manifest.yaml` (aspect registry) and per-aspect sub-manifests at `src/kanon/kit/aspects/<name>/manifest.yaml`. To scaffold a new file at depth-N for consumers, add it under `kit/aspects/<name>/files/` or `kit/aspects/<name>/protocols/` and list its path under the appropriate `depth-N` entry in the sub-manifest. Strict-superset semantics are preserved by manifest-union.

## Task Playbook

Match your current activity to the phase below. For each phase, prefer a specialist capability (agent, skill, or mode) matching the listed profile if one is available in your session; otherwise handle it directly using the referenced protocol.

| Phase | Capability profile | Protocol / guidance |
|-------|-------------------|---------------------|
| Planning | Planner, interviewer, deep-reasoning | § Plan Before Build |
| Architecture | Architect, design critic | Review against ADRs + design docs |
| Implementation | Executor, code generator | Follow approved plan, verify each AC |
| Exploration | Explorer, codebase search | Pattern discovery, file navigation |
| Code review | Reviewer, code critic | Severity ratings; check spec/plan drift |
| Debugging | Debugger, tracer, root-cause analysis | `error-diagnosis` protocol |
| Testing | Test engineer, TDD specialist | `test-discipline` + `ac-first-tdd` |
| Security | Security reviewer, vulnerability scanner | `secure-defaults` + CI scanner |
| Completion check | Verifier, checklist runner | `completion-checklist` protocol |
| Documentation | Writer, doc specialist | Match project tone |
| Git operations | Git specialist, rebase/commit tooling | Use git CLI |
| Release | — | `release-checklist` protocol |

## Quick Start by Task Type

The full boot chain is mandatory for new features. For other task types, read only what's relevant — the gates in AGENTS.md always apply regardless.

| Task type | Must read | Can skip |
|-----------|-----------|----------|
| **New feature** (user-visible capability) | Full boot chain (steps 0–5) | — |
| **Bug fix** (single file, clear cause) | AGENTS.md gates + `kanon-implementation.md` | vision, dev-process, foundations |
| **Refactor** (no behavior change) | AGENTS.md gates + `kanon-implementation.md` | vision, specs, foundations |
| **Test addition** | AGENTS.md gates + `test-discipline` protocol | vision, dev-process, foundations |
| **Docs / prose only** | AGENTS.md § Contribution Conventions | everything else |
| **CI / tooling** | AGENTS.md gates + `kanon-implementation.md` | vision, dev-process, foundations |

The two hard gates (Plan Before Build, Spec Before Design) and worktree isolation apply to **all task types** — they are never skippable.

<!-- kanon:begin:kanon-sdd/plan-before-build -->
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
<!-- kanon:end:kanon-sdd/plan-before-build -->

<!-- kanon:begin:kanon-sdd/spec-before-design -->
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

When skipping a design doc (all conditions in `docs/sdd-method.md` § "When to Skip" are met), declare the skip in the plan's YAML frontmatter as `design: "Follows ADR-NNNN"` — citing the ADR that already covers the design space. This makes the skip auditable.

**Before your first design-doc, ADR, plan, or source-modifying tool call, state in one sentence:** "Spec at `<path>` has been approved." If you cannot truthfully emit that sentence, stop and write the spec.
<!-- kanon:end:kanon-sdd/spec-before-design -->

<!-- kanon:begin:protocols-index -->
## Active protocols

Prose-as-code procedures available at this depth. When a trigger fires, read the protocol file in full and follow its numbered steps.

### kanon-deps (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`dependency-hygiene`](.kanon/protocols/kanon-deps/dependency-hygiene.md) | 1 | Adding, removing, or updating project dependencies |

### kanon-fidelity (depth 1)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`fidelity-fixture-authoring`](.kanon/protocols/kanon-fidelity/fidelity-fixture-authoring.md) | 1 | Adding a new fidelity fixture, updating an existing fixture's assertions, or recapturing a `.dogfood.md` after a protocol's prose has changed |
| [`fidelity-discipline`](.kanon/protocols/kanon-fidelity/fidelity-discipline.md) | 1 | Committing fidelity captures, editing protocol prose, or working with fidelity fixtures |

### kanon-release (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`release-checklist`](.kanon/protocols/kanon-release/release-checklist.md) | 1 | A release is being prepared, or the user asks to cut a release |
| [`publishing-discipline`](.kanon/protocols/kanon-release/publishing-discipline.md) | 1 | A release is being prepared, or executing release publish steps |

### kanon-sdd (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`tier-up-advisor`](.kanon/protocols/kanon-sdd/tier-up-advisor.md) | 1 | The user or agent is considering raising this project's sdd depth, or asks "should we increase depth?" |
| [`verify-triage`](.kanon/protocols/kanon-sdd/verify-triage.md) | 1 | A `kanon verify` run returns a non-ok status, or the user asks "what does this verify report mean?" |
| [`completion-checklist`](.kanon/protocols/kanon-sdd/completion-checklist.md) | 1 | An agent is about to declare a plan or task complete, or the user asks "is this done?" |
| [`scope-check`](.kanon/protocols/kanon-sdd/scope-check.md) | 1 | An agent discovers during implementation that the current task requires changes not described in the approved plan |
| [`plan-before-build`](.kanon/protocols/kanon-sdd/plan-before-build.md) | 1 | A non-trivial source change is about to begin, or the agent is unsure whether a change is trivial |
| [`spec-review`](.kanon/protocols/kanon-sdd/spec-review.md) | 2 | A draft spec is ready for review (status:draft), or the user asks for a spec review, or a spec is about to be promoted to status:accepted |
| [`spec-before-design`](.kanon/protocols/kanon-sdd/spec-before-design.md) | 2 | A change introduces a new user-visible capability, or the agent is unsure whether a spec is needed |
| [`adr-immutability`](.kanon/protocols/kanon-sdd/adr-immutability.md) | 3 | An ADR is being modified after acceptance, or a contributor proposes a body edit on an `accepted` / `accepted (lite)` ADR |

### kanon-security (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`secure-defaults`](.kanon/protocols/kanon-security/secure-defaults.md) | 1 | Writing or modifying code that handles secrets, user input, network requests, file operations, or authentication |

### kanon-testing (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`test-discipline`](.kanon/protocols/kanon-testing/test-discipline.md) | 1 | Writing or modifying code |
| [`error-diagnosis`](.kanon/protocols/kanon-testing/error-diagnosis.md) | 1 | A test fails, a build breaks, or a command produces an unexpected error during implementation |
| [`ac-first-tdd`](.kanon/protocols/kanon-testing/ac-first-tdd.md) | 2 | Implementing a plan or spec invariant at testing depth >= 2 |

### kanon-worktrees (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`worktree-lifecycle`](.kanon/protocols/kanon-worktrees/worktree-lifecycle.md) | 1 | A file-modifying operation is about to begin, or `git worktree list` shows active worktrees from other work streams |
| [`branch-hygiene`](.kanon/protocols/kanon-worktrees/branch-hygiene.md) | 1 | A file-modifying operation is about to begin |
<!-- kanon:end:protocols-index -->

<!-- kanon:begin:kanon-worktrees/branch-hygiene -->
## Worktree Branch Hygiene

Use a dedicated git worktree for any change that modifies files. Read-only operations (reviewing code, running builds, answering questions) stay in the main checkout.

**Before your first file-modifying tool call, state in one sentence:** "Working in worktree `.worktrees/<slug>/` on branch `wt/<slug>`." If you cannot truthfully emit this sentence, stop and create the worktree. This sentence is the audit trail — its absence in a transcript is how violations get caught.

**When to create a worktree:**

- You are about to modify any file — no exceptions.
- `git worktree list` shows other worktrees — parallel work is in progress.
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
<!-- kanon:end:kanon-worktrees/branch-hygiene -->

<!-- kanon:begin:kanon-worktrees/body -->
The `worktrees` aspect is active with automation helpers. All file-modifying changes should be isolated in git worktrees under `.worktrees/<slug>/`.

## Key Constraints

- Worktree creation is triggered by **any file modification**, not concurrency detection.
- Never force-remove a worktree with uncommitted changes.
- Branch naming convention: `wt/<slug>`.
- Use the helper scripts in `scripts/` for consistent lifecycle management:
  - `scripts/worktree-setup.sh <slug>` — create a worktree
  - `scripts/worktree-teardown.sh <slug>` — safely remove a worktree
  - `scripts/worktree-status.sh` — list all active worktrees
<!-- kanon:end:kanon-worktrees/body -->

<!-- kanon:begin:kanon-sdd/body -->
A `kanon` project with `sdd` at depth 3. Full stack: foundations + specs + design + ADRs + plans + verification. All process gates are active.

## Boot chain

0. Read [`docs/foundations/vision.md`](docs/foundations/vision.md) — what the project is and is not.
1. Read [`docs/sdd-method.md`](docs/sdd-method.md) — the SDD method.
2. Read [`docs/decisions/README.md`](docs/decisions/README.md) — what has already been decided.
3. **Before editing any source file** for a non-trivial change, produce a plan and wait for approval — see § "Required: Plan Before Build" below.
4. **Before writing a design doc, ADR, plan, or implementation** for a new user-visible capability, produce a spec and wait for approval — see § "Required: Spec Before Design" below.

## Key Constraints

- Process rules belong in `docs/sdd-method.md`. README files in artifact directories carry indexes and templates, not process definitions.
- ADRs are immutable once accepted. To reverse one, write a superseding ADR.
- Principles in `docs/foundations/principles/` are the project's cross-cutting stances. Specs and ADRs reference them via frontmatter.

## References

- [`docs/foundations/vision.md`](docs/foundations/vision.md) — product vision
- [`docs/foundations/principles/`](docs/foundations/principles/) — cross-cutting stances
- [`docs/sdd-method.md`](docs/sdd-method.md) — the SDD method
- [`docs/decisions/README.md`](docs/decisions/README.md) — ADR index
- [`docs/specs/README.md`](docs/specs/README.md) — spec index
- [`docs/design/README.md`](docs/design/README.md) — design doc index
- [`docs/plans/README.md`](docs/plans/README.md) — plan index
<!-- kanon:end:kanon-sdd/body -->

<!-- kanon:begin:kanon-release/body -->
The `release` aspect is active with automation helpers. Follow the release checklist protocol before cutting any release.

- `ci/release-preflight.py` — validates version, changelog, tests, and lint before publish.
- `.github/workflows/release.yml` — reference CI workflow triggered by version tags.
<!-- kanon:end:kanon-release/body -->

<!-- kanon:begin:kanon-testing/body -->
The `testing` aspect is active with automated enforcement. Follow the test-discipline and ac-first-tdd protocols when writing or modifying code.

- At depth 2+: translate plan acceptance criteria into failing tests before implementation.
- For spec invariants: red-green-refactor loop.
- `ci/check_test_quality.py` — validates test quality (no empty tests, no assert-True-only).
<!-- kanon:end:kanon-testing/body -->

<!-- kanon:begin:kanon-security/secure-defaults -->
## Secure Defaults

LLM agents produce predictable security anti-patterns. Every code change follows these rules:

**Never hardcode secrets.** API keys, tokens, passwords, and credentials go in environment variables or a secret manager — never in source code. If a value looks like a secret, it is one.

**Always use parameterized queries.** Never string-interpolate SQL, shell commands, or LDAP queries. Use the language's parameterized query API or prepared statements.

**Never disable TLS verification.** No `verify=False`, no `rejectUnauthorized: false`, no `NODE_TLS_REJECT_UNAUTHORIZED=0`. If a certificate is invalid, fix the certificate — don't disable the check.

**Use least-privilege file permissions.** Never `chmod 777` or `0o777`. Files default to owner-only unless there is a documented reason for broader access.

**Never use wildcard CORS in production.** `Access-Control-Allow-Origin: *` is acceptable only in local development. Production CORS must specify allowed origins explicitly.

**Validate all external input.** User input, API responses, file contents, and environment variables are untrusted. Validate type, length, and format before use. Reject unexpected values rather than coercing them.

**At depth 2: CI pattern scanner.** `ci/check_security_patterns.py` detects common anti-patterns via regex. It is a safety net, not a SAST replacement — passing the scanner does not mean the code is secure.
<!-- kanon:end:kanon-security/secure-defaults -->

<!-- kanon:begin:kanon-security/body -->
The `security` aspect is active with CI enforcement. Follow the secure-defaults protocol when writing or modifying code.

- `ci/check_security_patterns.py` — language-agnostic regex scanner for common security anti-patterns.
<!-- kanon:end:kanon-security/body -->

<!-- kanon:begin:kanon-deps/dependency-hygiene -->
## Dependency Hygiene

LLM agents add dependencies casually. Every dependency change follows these rules:

**Always pin exact versions.** Use `==` in requirements.txt, exact versions in pyproject.toml, and exact versions (no `^` or `~`) in package.json. Unpinned dependencies break reproducibility.

**Never add a dependency without justification.** Before adding a package, check whether the standard library or an existing dependency already covers the need. Duplicate-purpose libraries bloat the dependency tree and create maintenance burden.

**Audit before adding.** Verify the package is actively maintained, has a compatible license, and is not a typosquat. Prefer well-known packages over obscure alternatives.

**Remove unused dependencies.** When removing code that was the sole consumer of a dependency, remove the dependency too. Phantom dependencies are tech debt.

**Keep manifests consistent.** If the project uses multiple manifest formats (e.g., pyproject.toml and requirements.txt), keep them in sync. Conflicting version constraints across manifests cause silent failures.

**At depth 2: CI dependency scanner.** `ci/check_deps.py` detects unpinned versions and duplicate-purpose packages. It is a safety net — passing the scanner does not mean the dependency tree is optimal.
<!-- kanon:end:kanon-deps/dependency-hygiene -->

<!-- kanon:begin:kanon-deps/body -->
The `deps` aspect is active with CI enforcement. Follow the dependency-hygiene protocol when adding or modifying dependencies.

- `ci/check_deps.py` — scans manifest files for unpinned versions and duplicate-purpose packages.
<!-- kanon:end:kanon-deps/body -->

<!-- kanon:begin:kanon-testing/test-discipline -->
## Test Discipline

Tests exist to protect behavior, not to produce a green badge. Every code change follows these rules:

**Tests accompany code changes.** Every new function, behavior change, or bug fix gets a test in the same commit or adjacent commit. No untested code ships.

**Tests are not deleted without justification.** When removing a test, document what now covers the behavior it protected, or acknowledge the coverage gap. Never delete a test solely because it's failing — fix the code or fix the test.

**Assertions are not weakened to make tests pass.** Changing an expected value requires explaining why the old value was wrong. If the test is failing, the implementation is wrong — not the test.

**Prefer test-first.** Before implementing, consider "how will I verify this works?" and let that shape the implementation. Write the test, watch it fail, then implement.

**Maintain coverage at or above the configured floor.** The coverage floor is declared in `.kanon/config.yaml` under `aspects.testing.config.coverage_floor` (default 80%). The kit declares this value as advisory metadata; consumers wire it into their own CI pipeline (e.g., `pytest --cov-fail-under=$VALUE` or the equivalent in another language's tooling). The kit does not auto-wire the configured value into a test runner. Do not merge changes that drop coverage below the project's threshold.

**At depth 2+: AC-first testing.** Translate plan acceptance criteria into failing tests before implementation. For spec invariants, follow the red-green-refactor loop. See the `ac-first-tdd` protocol.
<!-- kanon:end:kanon-testing/test-discipline -->

<!-- kanon:begin:kanon-release/publishing-discipline -->
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
<!-- kanon:end:kanon-release/publishing-discipline -->

<!-- kanon:begin:kanon-fidelity/body -->
The `kanon-fidelity` aspect is active. Behavioural-conformance fixtures live under `.kanon/fidelity/`; `kanon verify` runs lexical assertions against committed `.dogfood.md` captures. Follow the `fidelity-fixture-authoring` protocol when adding or updating fixtures. Per ADR-0029 / ADR-0031; consumes the INV-10 carve-out of `docs/specs/verification-contract.md`.
<!-- kanon:end:kanon-fidelity/body -->

<!-- kanon:begin:kanon-fidelity/fidelity-discipline -->
## Fidelity Discipline

The `kanon-fidelity` aspect verifies that an LLM agent's *actual behaviour* matches the prose your protocols promise. Lexical assertions over committed `.kanon/fidelity/<protocol>.dogfood.md` captures fail `kanon verify` when the agent's recorded turns drift from the fixture's `forbidden_phrases` / `required_one_of` / `required_all_of` rules.

**Commit fixtures before tagging.** A release tag stamps the protocol prose at a SHA; the paired dogfood capture must reflect agent behaviour at that SHA. Tagging with stale captures ships a hidden contract violation.

**Recapture when the protocol changes.** If you edit a protocol's prose, the previous dogfood capture no longer reflects what the agent should now do. Recapture as part of the same change; commit the new dogfood alongside the prose edit.

**Never weaken an assertion to make a fixture pass.** A failing fidelity assertion means the agent did the wrong thing. Fix the agent's prompt, fix the protocol prose, or accept that the rule does not actually hold — and remove the assertion deliberately, with a note. Silently relaxing the regex is the same anti-pattern as weakening a unit-test assertion.

**Failures are errors; missing dogfood is a warning.** If you have a fixture without its paired capture, you have in-flight work — `kanon verify` warns. If you have a capture that fails the assertions, you have a real defect — `kanon verify` errors and your CI breaks.

The aspect ships only Tier 1 (lexical replay over committed text). Tier 2 (workstation capture) and Tier 3 (paid live-LLM nightly) are out of scope at this depth and require their own ADRs.
<!-- kanon:end:kanon-fidelity/fidelity-discipline -->

## Contribution Conventions

- **Commit messages** — prefer [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Soft CI check warns on non-conforming messages but does not block merges.
- **Changelog** — append every user-visible change to `## [Unreleased]` in `CHANGELOG.md` in the same commit that introduces it. Don't batch at release time. Refactors, internal tests, and docs-only edits don't need a changelog entry.
- **Version references** — always write pre-release versions in full (`v0.1.0a9` or `0.1.0a9`), never the bare suffix (`a9`). A bare suffix is a PEP 440 pre-release marker that attaches to any `X.Y.Z`.

## References

- [`docs/sdd-method.md`](docs/sdd-method.md) — the SDD method
- [`docs/kanon-implementation.md`](docs/kanon-implementation.md) — kanon's instantiation
- [`docs/decisions/README.md`](docs/decisions/README.md) — ADR index
- [`docs/foundations/vision.md`](docs/foundations/vision.md) — product vision
- [`docs/plans/roadmap.md`](docs/plans/roadmap.md) — deferred capabilities
