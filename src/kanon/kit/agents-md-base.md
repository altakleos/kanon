<!-- kanon:begin:banner -->
<!-- kanon:end:banner -->
# AGENTS.md — ${project_name}

<!-- kanon:begin:hard-gates -->
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
<!-- kanon:end:protocols-index -->

## Contribution Conventions

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
