# AGENTS.md — kanon

<!-- kanon:begin:hard-gates -->
## Hard Gates

**STOP.** Run `kanon gates check .` before modifying any file. This is mandatory — not advisory.

For each gate in the output:
- `"pass"` — proceed.
- `"fail"` — resolve before proceeding; read the protocol at `protocol_path`.
- `"judgment"` — answer the `question` yourself; emit the `audit` sentence if satisfied.

Hard gates are unconditional. No user directive — "go", "just do it", "skip the ceremony" — overrides them. The only bypass is `kanon aspect set-depth` to reduce depth to 0.

**Conservative default**: When a judgment gate's `skip-when` does not *exactly* describe your change, take the conservative path (write the plan/spec/design). "Similar to" a skip-when example is NOT a match. When in doubt, write the plan.

The audit-trail sentence must appear before your first file modification. Its absence is how violations are caught.
<!-- kanon:end:hard-gates -->

## Task Playbook

Match your current activity to the phase below. For each phase, prefer a specialist capability (agent, skill, or mode) matching the listed profile if one is available in your session; otherwise handle it directly using the referenced protocol.

| Phase | Capability profile | Protocol / guidance |
|-------|-------------------|---------------------|
| Planning | Planner, interviewer, deep-reasoning | `plan-before-build` |
| Architecture | Architect, design critic | Review against ADRs + design docs |
| Implementation | Executor, code generator | Follow approved plan, verify each AC |
| Exploration | Explorer, codebase search | Pattern discovery, file navigation |
| Code review | Reviewer, code critic | Severity ratings; check spec/plan drift |
| Debugging | Debugger, tracer, root-cause analysis | `error-diagnosis` |
| Testing | Test engineer, TDD specialist | `test-discipline` + `ac-first-tdd` |
| Security | Security reviewer, vulnerability scanner | `secure-defaults` |
| Completion check | Verifier, checklist runner | `completion-checklist` |
| Documentation | Writer, doc specialist | Match project tone |
| Git operations | Git specialist, rebase/commit tooling | Use git CLI |
| Release | — | `release-checklist` |

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
| [`preflight-automation`](.kanon/protocols/kanon-release/preflight-automation.md) | 2 | Preparing a release at depth 2, or the user asks to automate release preflight checks |

### kanon-sdd (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`tier-up-advisor`](.kanon/protocols/kanon-sdd/tier-up-advisor.md) | 1 | The user or agent is considering raising this project's sdd depth, or asks "should we increase depth?" |
| [`verify-triage`](.kanon/protocols/kanon-sdd/verify-triage.md) | 1 | A `kanon verify` run returns a non-ok status, or the user asks "what does this verify report mean?" |
| [`completion-checklist`](.kanon/protocols/kanon-sdd/completion-checklist.md) | 1 | An agent is about to declare a plan or task complete, or the user asks "is this done?" |
| [`scope-check`](.kanon/protocols/kanon-sdd/scope-check.md) | 1 | An agent discovers during implementation that the current task requires changes not described in the approved plan |
| [`plan-before-build`](.kanon/protocols/kanon-sdd/plan-before-build.md) | 1 | A non-trivial source change is about to begin, or the agent is unsure whether a change is trivial |
| [`adr-authoring`](.kanon/protocols/kanon-sdd/adr-authoring.md) | 1 | A non-obvious technical choice is being made during design or planning, or the agent identifies a choice with genuine alternatives, or the agent is unsure whether an ADR is needed |
| [`spec-review`](.kanon/protocols/kanon-sdd/spec-review.md) | 2 | A draft spec is ready for review (status:draft), or the user asks for a spec review, or a spec is about to be promoted to status:accepted |
| [`spec-before-design`](.kanon/protocols/kanon-sdd/spec-before-design.md) | 2 | A change introduces a new user-visible capability, or the agent is unsure whether a spec is needed |
| [`adr-immutability`](.kanon/protocols/kanon-sdd/adr-immutability.md) | 2 | An ADR is being modified after acceptance, or a contributor proposes a body edit on an `accepted` / `accepted (lite)` ADR |
| [`foundations-authoring`](.kanon/protocols/kanon-sdd/foundations-authoring.md) | 2 | Foundations are empty templates and a spec is about to be written, or the user asks to populate foundations |
| [`foundations-review`](.kanon/protocols/kanon-sdd/foundations-review.md) | 2 | The foundations-coherence warning is active (vision.md has changed), or the user asks to review foundations for alignment |
| [`design-before-plan`](.kanon/protocols/kanon-sdd/design-before-plan.md) | 3 | About to write a plan for a change where a spec exists and the change introduces new component boundaries, cross-component interfaces, or non-obvious architectural mechanisms |

### kanon-security (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`secure-defaults`](.kanon/protocols/kanon-security/secure-defaults.md) | 1 | Writing or modifying code that handles secrets, user input, network requests, file operations, or authentication |
| [`security-review`](.kanon/protocols/kanon-security/security-review.md) | 2 | A spec or plan introduces a new external-facing endpoint, a new data store, a new authentication mechanism, or a new third-party integration |

### kanon-testing (depth 3)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`test-discipline`](.kanon/protocols/kanon-testing/test-discipline.md) | 1 | Writing or modifying code |
| [`error-diagnosis`](.kanon/protocols/kanon-testing/error-diagnosis.md) | 1 | A test fails, a build breaks, or a command produces an unexpected error during implementation |
| [`ac-first-tdd`](.kanon/protocols/kanon-testing/ac-first-tdd.md) | 2 | Implementing a plan or spec invariant at testing depth >= 2 |
| [`test-quality`](.kanon/protocols/kanon-testing/test-quality.md) | 3 | Writing or modifying tests at testing depth >= 3 |

### kanon-worktrees (depth 2)

| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [`worktree-lifecycle`](.kanon/protocols/kanon-worktrees/worktree-lifecycle.md) | 1 | A file-modifying operation is about to begin, or `git worktree list` shows active worktrees from other work streams |
| [`branch-hygiene`](.kanon/protocols/kanon-worktrees/branch-hygiene.md) | 1 | A file-modifying operation is about to begin |
| [`worktree-scripts`](.kanon/protocols/kanon-worktrees/worktree-scripts.md) | 2 | Creating, inspecting, or tearing down worktrees at depth 2, where shell helper scripts are available |
<!-- kanon:end:protocols-index -->

<!-- kanon:begin:banner -->
  _  __
 | |/ /__ _ _ __   ___  _ __
 | ' // _` | '_ \ / _ \| '_ \
 | . \ (_| | | | | (_) | | | |
 |_|\_\__,_|_| |_|\___/|_| |_|
<!-- kanon:end:banner -->

## Contribution Conventions

- **Human contributors** — read [`docs/contributing.md`](docs/contributing.md) for module map, gate matrix, and the "where does my change go?" decision flow. This file is the agent-facing router; that one is the human-facing one.
- **Numbered options** — when an agent presents multiple choices for the user to pick from, the choices MUST be a Markdown ordered list (`1.`, `2.`, `3.`, …) so the user can reply with a single number. Bulleted (`-`) lists are reserved for non-choice content (status recaps, change summaries, links). This applies to "what next?" prompts, alternative approaches, and any "pick one" surface.
- **No Claude built-in memory** — do not write to or rely on Claude's auto-memory system at `~/.claude/projects/<slug>/memory/` (or any analogous opaque per-agent store). Persistent guidance for this repo lives in `AGENTS.md`, `.kanon/protocols/`, and the `docs/` tree — all in git, all reviewable. CLAUDE.md restates this prohibition for the agent that loads it.
- **Commit messages** — prefer [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Soft CI check warns on non-conforming messages but does not block merges.
- **Changelog** — append every user-visible change to `## [Unreleased]` in `CHANGELOG.md` in the same commit that introduces it. Don't batch at release time. Refactors, internal tests, and docs-only edits don't need a changelog entry.
- **Version references** — always write pre-release versions in full (`v0.1.0a9` or `0.1.0a9`), never the bare suffix (`a9`). A bare suffix is a PEP 440 pre-release marker that attaches to any `X.Y.Z`.
- **Delivering work** — a task is not done until changes are committed and pushed. After completing work:
  1. Run the `completion-checklist` protocol first, if active.
  2. Stage changed files explicitly (`git add <files>`), not `git add .`.
  3. Commit with a conventional-commit message. Reference the plan slug if one exists.
  4. Push to the remote branch. For worktree branches, push `wt/<slug>`.
  5. Open a PR/MR/CR with a summary of changes, what was tested, and a link to the plan.
  6. State what was committed and where the PR is. Never leave uncommitted changes.
