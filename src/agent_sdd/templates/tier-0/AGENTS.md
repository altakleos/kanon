# AGENTS.md — ${project_name}

A tier-0 `agent-sdd` project. The kit is installed but no process gates are active yet — ideal for vibe-coding, prototypes, or short-lived utilities.

## Boot chain

Read this file. That's it for tier-0. There are no further artifacts required.

## What `agent-sdd` gives you at tier-0

- A pointer file (`AGENTS.md`) that every supported LLM agent harness will read (via shims).
- Consistent `.agent-sdd/config.yaml` bookkeeping (tier, kit version).

## Graduating to tier-1

When you're ready for plan-before-build discipline (and `docs/decisions/` and `docs/plans/` structure), run:

```bash
agent-sdd tier set <project-path> 1
```

Tier migration is non-destructive — your existing files are never modified, moved, or deleted by the kit. Tier-up only adds new structure; tier-down only relaxes gates.

## Contribution Conventions (suggested)

- **Commit messages** — prefer [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- **Changelog** — append user-visible changes to a `CHANGELOG.md` if the project has one.
