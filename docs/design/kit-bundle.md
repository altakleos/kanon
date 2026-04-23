---
status: accepted
date: 2026-04-22
implements: docs/specs/template-bundle.md
---
# Design: Kit bundle — manifest-driven layout and construction

## Context

`docs/specs/template-bundle.md` specifies *what* a consumer repo contains after `kanon init --tier N`. This design doc specifies *how* the kit is structured on the producer side and how the CLI constructs consumer bundles from it.

The prior design shipped four per-tier subdirectories under `src/kanon/templates/`. ADR-0011 replaces that with a unified `src/kanon/kit/` bundle and a `manifest.yaml` declaring tier membership. This document reflects the post-refactor shape.

## Architecture

```
src/kanon/kit/
├── kit.md                 # kernel doc (scaffolded to consumer's .kanon/kit.md)
├── manifest.yaml          # tier → {files, protocols, sections} membership
├── harnesses.yaml         # shim registry
├── agents-md/             # per-tier AGENTS.md base preambles
│   ├── tier-0.md
│   ├── tier-1.md
│   ├── tier-2.md
│   └── tier-3.md
├── sections/              # reusable AGENTS.md marker sections
│   ├── plan-before-build.md
│   ├── spec-before-design.md
│   └── protocols-index.md
├── protocols/             # prose-as-code protocols (mirrored to consumer's .kanon/protocols/)
│   ├── tier-up-advisor.md
│   ├── verify-triage.md
│   └── spec-review.md
└── files/                 # flat scaffold tree (copied to consumer repo root)
    ├── CLAUDE.md
    └── docs/
        ├── development-process.md
        ├── decisions/{README,_template}.md
        ├── plans/{README,_template}.md
        ├── specs/{README,_template}.md
        ├── design/{README,_template}.md
        └── foundations/
            ├── README.md
            ├── vision.md
            ├── principles/README.md
            └── personas/README.md
```

### `manifest.yaml` shape

```yaml
# Tiers are strict supersets: tier-(N+1) includes everything in tier-N.
# Paths under `files:` are relative to src/kanon/kit/files/
# Paths under `protocols:` are relative to src/kanon/kit/protocols/

tier-0:
  files: [CLAUDE.md]
  protocols: []

tier-1:
  files:
    - docs/development-process.md
    - docs/decisions/README.md
    - docs/decisions/_template.md
    - docs/plans/README.md
    - docs/plans/_template.md
  protocols: [tier-up-advisor.md, verify-triage.md]

tier-2:
  files:
    - docs/specs/README.md
    - docs/specs/_template.md
  protocols: [spec-review.md]

tier-3:
  files:
    - docs/design/README.md
    - docs/design/_template.md
    - docs/foundations/README.md
    - docs/foundations/vision.md
    - docs/foundations/principles/README.md
    - docs/foundations/personas/README.md
  protocols: []

agents-md-sections:
  tier-0: []
  tier-1: [plan-before-build, protocols-index]
  tier-2: [plan-before-build, spec-before-design, protocols-index]
  tier-3: [plan-before-build, spec-before-design, protocols-index]
```

### Source-of-truth rules

- **Byte-equality against repo canonical.** Files in `kit/files/` and `kit/protocols/` that have a counterpart in the kit's own repo (e.g., `docs/development-process.md`, the `_template.md` files, the repo's own `.kanon/protocols/*.md`) are byte-identical to those counterparts. Enforced by `ci/check_kit_consistency.py` against a narrow whitelist.
- **Files without repo counterpart are template-only.** Tier-stub READMEs (`docs/specs/README.md`, `docs/design/README.md`, `docs/foundations/…/README.md`) legitimately differ from the kit's own populated indexes. Not byte-checked.
- **Tier-subset is tautological.** Under manifest union, `_build_bundle(tier=N)` cannot emit a file that isn't also present at tier-(N+1). No cross-directory comparison needed.
- **Marker section fragments in `kit/sections/`** are the exact content wrapped by `<!-- kanon:begin:<name> --> … <!-- kanon:end:<name> -->` in consumer AGENTS.md files. Authored once, reused by `init` and `tier set`.

### Construction at `init` time

`kanon init <target> --tier <N>` executes:

1. Load `kit/manifest.yaml` (cached).
2. Compute the file set: union of `manifest['tier-K']['files']` and `manifest['tier-K']['protocols']` for K ∈ {0, …, N}.
3. For each file, substitute `string.Template` placeholders against `{project_name, tier, kit_version, iso_timestamp}`.
4. Write the rendered tree to `<target>/` via atomic write (copy-to-tmp + fsync-dir + swap + fsync-dir, ported from Sensei).
5. Assemble `<target>/AGENTS.md` by reading `kit/agents-md/tier-<N>.md` (the base preamble) and inserting each marker section from `manifest['agents-md-sections']['tier-<N>']` using fragments from `kit/sections/<name>.md`.
6. Render `kit/kit.md` with placeholder substitution → `<target>/.kanon/kit.md`.
7. Generate shims from `kit/harnesses.yaml`, writing each to its harness-specific path.
8. Write `<target>/.kanon/config.yaml` with `{kit_version, tier, tier_set_at}`.

### Construction at `tier set` time

`kanon tier set <target> <N>` executes (per ADR-0008):

1. Read current tier from `.kanon/config.yaml`. Noop if equal (idempotent).
2. Compute additions/removals as manifest-union set differences between current and target tier.
3. Tier-up: atomically write added files. Rewrite AGENTS.md by inserting marker sections newly active at tier N. Rewrite `.kanon/kit.md` to reflect the new tier. User content outside markers preserved.
4. Tier-down: remove marker sections no longer active. Existing artifact directories stay on disk (non-destructive). Rewrite `.kanon/kit.md`.
5. Update `.kanon/config.yaml` with new tier and timestamp.
6. All file writes atomic via tmp-dir swap.

### Enforcement

`ci/check_kit_consistency.py` asserts:

- Every path in `manifest.yaml` (under `files:` or `protocols:`) resolves to an extant file in `kit/files/` or `kit/protocols/`.
- Every file in a narrow whitelist is byte-identical to its repo-canonical counterpart:
  - `kit/files/docs/development-process.md` ↔ `docs/development-process.md`
  - `kit/files/docs/{decisions,plans,specs,design}/_template.md` ↔ repo equivalents
  - `kit/protocols/*.md` ↔ `.kanon/protocols/*.md`
- `kit/kit.md` exists and has a top-level `# ` heading.
- Every AGENTS.md base in `kit/agents-md/` has balanced `<!-- kanon:begin:* -->` / `<!-- kanon:end:* -->` markers; section names are in the known set (`plan-before-build`, `spec-before-design`, `protocols-index`).
- `harnesses.yaml` parses and every entry has required fields.

## Interfaces

- `src/kanon/cli.py::_load_manifest() -> dict` — YAML safe-load with shape validation, cached.
- `src/kanon/cli.py::_expected_files(tier) -> list[str]` — derives expected paths from manifest union over tiers 0..N.
- `src/kanon/cli.py::_build_bundle(tier, context) -> dict[path, content]` — pure function returning file tree to write. Tests parametrise on tier.
- `src/kanon/cli.py::_assemble_agents_md(tier, project_name) -> str` — reads `kit/agents-md/tier-<N>.md` as base; inserts marker sections from `kit/sections/`.
- `src/kanon/_atomic.py::atomic_replace_tree(src, dst)` — ported from Sensei.

## Decisions

See `../decisions/0003-agents-md-canonical-root.md`, `../decisions/0006-tier-model-semantics.md`, `../decisions/0008-tier-migration.md`, `../decisions/0010-protocol-layer.md`, `../decisions/0011-kit-bundle-refactor.md`.
