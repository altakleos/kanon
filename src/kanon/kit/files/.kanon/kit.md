# kanon kit — ${project_name}

> **Kernel doc.** Scaffolded by `kanon init` and refreshed by `kanon upgrade`. This file describes what the kanon kit gives this repo at its current configuration.

## Active aspects

${active_aspects_summary}

## Boot chain

1. **`AGENTS.md`** — the repo-canonical entry point. All harness shims route here.
2. **This file (`.kanon/kit.md`)** — kit context and routing index.

AGENTS.md is the canonical source of in-force rules; this file is the catalog.

## Protocols

Protocol files live at `.kanon/protocols/<aspect>/*.md`. Each has YAML frontmatter with `invoke-when` (the trigger). See the `protocols-index` section in `AGENTS.md` for the depth-gated catalog.

When a trigger fires, read the matching protocol file in full and follow its numbered steps.

## Depth migration

`kanon aspect set-depth <target> <aspect> <N>` changes an aspect's depth. Migration is mutable, idempotent, and non-destructive.

## Something missing or wrong?

Run `kanon verify .` to catch drift.
