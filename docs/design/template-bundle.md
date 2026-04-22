---
status: accepted
date: 2026-04-22
implements: docs/specs/template-bundle.md
---
# Design: Template bundle — file-level layout and construction

## Context

`docs/specs/template-bundle.md` specifies *what* the four tier bundles contain. This design doc specifies *how* they are constructed and maintained: which files are canonical vs derived, how strict-subset invariants are enforced, and where placeholder substitution happens.

## Architecture

Four template directories under `src/agent_sdd/templates/`:

```
templates/
├── tier-0/
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   └── .agent-sdd/config.yaml.tmpl        # rendered at init
├── tier-1/
│   ├── AGENTS.md
│   ├── CLAUDE.md
│   ├── docs/
│   │   ├── development-process.md          # byte-identical to repo's copy
│   │   ├── decisions/
│   │   │   ├── README.md
│   │   │   └── _template.md
│   │   └── plans/
│   │       ├── README.md
│   │       └── _template.md
│   └── .agent-sdd/config.yaml.tmpl
├── tier-2/   # strict superset of tier-1
│   └── (as tier-1 plus docs/specs/{README,_template}.md)
├── tier-3/   # strict superset of tier-2 and byte-identical to repo's canonical sources
│   └── (as tier-2 plus docs/design/, docs/foundations/)
├── harnesses.yaml                          # shim registry
└── agents-md-sections/                     # per-tier marker-delimited fragments
    ├── tier-0.md
    ├── tier-1.md
    ├── tier-2.md
    └── tier-3.md
```

### Source-of-truth rules

- **Tier-3's `docs/development-process.md`** is byte-identical to the kit's repo-root `docs/development-process.md`. Enforced by `ci/check_template_consistency.py`.
- **Tier-3's `AGENTS.md` marker-delimited sections** are byte-identical to the kit's repo-root `AGENTS.md` marker-delimited sections. Enforced by the same validator.
- **Tier-N (N<3) bundles** are strict subsets of tier-3. Every file in tier-N exists in tier-(N+1) byte-identical. No independent authoring.
- **`agents-md-sections/tier-<N>.md`** holds the exact marker-delimited content inserted into AGENTS.md for tier N. These fragments are authored once and reused by both `init` (to produce initial AGENTS.md) and `tier set` (to rewrite AGENTS.md on migration).

### Construction at `init` time

`agent-sdd init <target> --tier <N>` executes:

1. Read `src/agent_sdd/templates/tier-<N>/` as the source bundle.
2. For each file, substitute `string.Template` placeholders against a context `{project_name, tier, kit_version, iso_timestamp}`.
3. Write the rendered tree to `<target>/` using atomic write primitives (copy-to-tmp + fsync-dir + swap + fsync-dir — ported from Sensei `src/sensei/cli.py:_atomic_replace_engine`).
4. Generate shims from `harnesses.yaml`, writing each to its harness-specific path under `<target>/`.
5. Assemble AGENTS.md by concatenating (a) the project-specific preamble from the template, (b) each enabled tier-N marker section from `agents-md-sections/tier-<N>.md`.
6. Write `.agent-sdd/config.yaml` with `{kit_version, tier, tier_set_at}`.

### Construction at `tier set` time

`agent-sdd tier set <target> <N>` executes:

1. Read current tier from `<target>/.agent-sdd/config.yaml`.
2. If equal to `<N>`, noop (per idempotency invariant).
3. Compute additions (tier-up) or removals (tier-down) as set differences between the current tier's file list and the target tier's file list.
4. For tier-up: write the added files atomically. Rewrite AGENTS.md by replacing the marker-delimited blocks with those from `agents-md-sections/tier-<N>.md`. User content outside markers is preserved.
5. For tier-down: rewrite AGENTS.md by removing the marker-delimited blocks that aren't in tier-<N>'s section list. Existing artifact directories (e.g., `docs/specs/` when going from tier-2 to tier-1) stay on disk; a warning lists them as "beyond required."
6. Update `.agent-sdd/config.yaml` with the new tier and timestamp.
7. Atomic via tmp-dir swap.

### Enforcement

`ci/check_template_consistency.py` runs at CI time and asserts:

- Every file in `tier-3/` that has a counterpart in the repo's `docs/` or `AGENTS.md` markers is byte-identical.
- Every file in `tier-N/` for N < 3 has a byte-identical counterpart in `tier-(N+1)/`.
- Every AGENTS.md template has balanced `<!-- agent-sdd:begin:* -->` / `<!-- agent-sdd:end:* -->` markers; every begin has a matching end; section names are in the known set.
- `harnesses.yaml` parses and every entry has required fields.

## Interfaces

- `src/agent_sdd/cli.py::init` calls a pure function `build_bundle(tier, context) -> dict[path, content]` that returns the file tree to write. Tests parametrise on tier.
- `src/agent_sdd/cli.py::tier_set` calls a pure function `tier_migration_diff(current_tier, target_tier) -> (additions, removals, agents_md_rewrite_plan)`.
- `src/agent_sdd/_atomic.py::atomic_replace_tree(src, dst)` — atomic tree swap, ported from Sensei.

## Decisions

See `../decisions/0003-agents-md-canonical-root.md`, `../decisions/0006-tier-model-semantics.md`, `../decisions/0008-tier-migration.md`.
