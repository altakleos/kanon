A `kanon` project with `sdd` at depth 0. The kit is installed but no process gates are active yet — ideal for vibe-coding, prototypes, or short-lived utilities.

## Boot chain

Read this file. That's it for depth 0. There are no further artifacts required.

## What `kanon` gives you at depth 0

- A pointer file (`AGENTS.md`) that every supported LLM agent harness will read (via shims).
- Consistent `.kanon/config.yaml` bookkeeping (aspects, depths, kit version).

## Graduating to depth 1

When you're ready for plan-before-build discipline (and `docs/decisions/` and `docs/plans/` structure), run:

```bash
kanon aspect set-depth <project-path> sdd 1
```

Depth migration is non-destructive — your existing files are never modified, moved, or deleted by the kit. Increasing depth only adds new structure; decreasing depth only relaxes gates.
