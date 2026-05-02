# Plans

Task breakdowns for features. Written AFTER design and ADRs, BEFORE implementation. Plans are permanent records and stay after a feature ships as historical documentation of how it was built.

## What is a plan

A plan is an ordered task breakdown written AFTER design and BEFORE implementation. It tells the implementing agent exactly what to build, in what order, touching which files. Plans are the bridge between "we know HOW to build it" (design) and "we're building it" (implement).

Plans are feature-scoped, not mechanism-scoped. A plan answers: What are the ordered steps? Which files are created or modified? What are the acceptance criteria for each step? What depends on what?

Plans are committed to the feature branch as the first commit and kept as permanent records after the feature ships. They serve as historical records of how features were built — useful for understanding implementation decisions that don't rise to ADR level.

## Checkbox convention

Plans use GFM `- [ ]` / `- [x]` checkboxes. A task's checkbox reflects whether the task has shipped:

- **`status: done`** — every task must be `- [x]` or explicitly deferred with `- [~]` and a `NOTE:` explaining why. A `done` plan with unticked items is an internal contradiction.
- **Partial deferrals** — mark as `- [~] T7: ... (deferred — see NOTE)` with rationale in a post-execution notes section.

The rule exists because plans are permanent records. A future reader must determine "shipped vs. skipped vs. forgotten" from checkbox state alone.

## How plans are executed

Plans are executed by an implementing agent (LLM or human). Each task falls into one of three categories:

| Task type | Examples | Execution mode |
|---|---|---|
| **Mechanical** | File edit, test run, lint fix, deterministic refactor, dependency install, read/search | Stream through. Report one line per task. |
| **Decision** | Choose between architectures, resolve scope surprise, pick a library, name a thing | Stop. Present options. Wait for input. |
| **Destructive** | `git push --force`, delete files/branches, drop DB tables, publish to PyPI, production deploy | Stop. Describe intent and blast radius. Wait for explicit approval. |

**Streaming** means: execute consecutive mechanical tasks without pausing between them. Report progress inline with a single status line per task (`✓ T3: Created lib.py`). Summarize at the end, not after each step. The user can interrupt at any time by typing any message — the agent stops and awaits direction.

**Default mode negotiation**: At the start of a plan's execution, the agent announces the plan and asks whether to execute autonomously (stream mechanical tasks, stop only at decisions and destructive ops) or step-by-step (pause after each task). If the user confirms the plan with "go", "run it", or equivalent, the default is autonomous. If the user says "walk me through it" or asks detailed questions up front, the default is step-by-step.

**Pause triggers during a streaming batch** — even in autonomous mode, the agent stops when:

- A command fails in a non-obvious way (not a typo, not a missing import — a real failure)
- An audit or investigation reveals scope materially larger than planned
- The next task would violate a spec invariant or skip a layer-stack prerequisite
- The agent is about to execute a task not in the original plan

**Anti-pattern — approval theater**: pausing between consecutive mechanical tasks to ask "continue?" when the user has no realistic reason to say no. If a user response of "next" or "continue" is repeated more than twice in a row without any course correction, the agent is over-gating. Stream.

**Progress reporting** during streaming should be terse. Group trivial steps (`✓ T3–T5: created 3 test files, all passing`). Do not re-explain the plan. Do not ask for permission to continue unless a real pause trigger fires. At batch end, summarize what changed, any deviations, and the next decision point.

## Branching and integration

All changes land on `main` through a branch and pull request. Direct pushes to `main` are not allowed.

### Branch naming

Use descriptive slash-prefixed names that match the change type:

| Change type | Branch name pattern | Example |
|---|---|---|
| New feature | `feat/<slug>` | `feat/hints-ingestion` |
| Bug fix | `fix/<slug>` | `fix/profile-schema-crash` |
| Documentation | `docs/<slug>` | `docs/hints-spec` |
| Refactor | `refactor/<slug>` | `refactor/config-loader` |
| Chore / tooling | `chore/<slug>` | `chore/ci-mypy-strict` |

### Pull request workflow

1. Create a branch from `main`.
2. Commit work to the branch. Plans are the first commit on a feature branch.
3. Push the branch and open a pull request. PR title follows the same conventional-commit prefix as the branch (`feat:`, `fix:`, `docs:`, etc.).
4. Review, iterate, merge. Squash-merge is the default for single-concern branches. Merge commits are acceptable when the branch contains multiple atomic commits worth preserving individually.
5. Delete the branch after merge.

### What belongs in one branch

A branch covers one concern — a feature, a bug fix, a spec, a refactor. If work spans multiple unrelated concerns, split into separate branches. A branch that touches both a new spec and an unrelated bug fix is too broad.

Batching related commits on one branch is fine: a spec commit + its design doc commit + its plan commit all serve the same feature and belong together.

## Index

*(empty — add plans as you start features)*

## Template

See [`_template.md`](_template.md).
