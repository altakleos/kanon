---
status: accepted
date: 2026-04-23
implements: docs/specs/aspects.md
---
# Design: Aspect model — manifest registry, namespaced markers, and legacy-tier auto-migration

## Context

`docs/specs/aspects.md` defines *what* an aspect is and what the model guarantees. This design doc specifies *how* the kit's source layout, manifest shape, AGENTS.md rendering, CLI construction flow, and consistency enforcement change to realise that spec.

The v0.1 kit (post-ADR-0011) has one implicit aspect (SDD) with tier membership in a single top-level `manifest.yaml`. This refactor promotes aspects to first-class citizens: each aspect owns a directory under `src/kanon/kit/aspects/<name>/` with its own sub-manifest; the top-level manifest becomes an aspect registry.

Two shaping goals:

1. **The v0.2 refactor ships `sdd` as the only aspect.** Zero user-visible behaviour change for existing consumers; the refactor proves the mechanism end-to-end. A follow-up plan introduces the first non-SDD aspect (`worktrees`).
2. **Legacy config auto-migrates on first `upgrade`.** v0.1 consumer projects continue to work unchanged; `.kanon/config.yaml` schema v1 → v2 is one-way and automatic.

## Architecture

### Producer layout (`src/kanon/kit/`)

```
src/kanon/kit/
├── manifest.yaml              # NEW: aspect registry
├── harnesses.yaml             # unchanged
├── kit.md                     # unchanged (kernel doc template)
└── aspects/                   # NEW top-level bucket
    └── sdd/                   # all v0.1 tier content lives here
        ├── manifest.yaml      # per-aspect depth-0..depth-3 membership
        ├── agents-md/         # formerly kit/agents-md/; tier-N.md → depth-N.md
        ├── sections/          # formerly kit/sections/
        ├── protocols/         # formerly kit/protocols/
        └── files/             # formerly kit/files/
```

The v0.1 top-level `kit/agents-md/`, `kit/sections/`, `kit/protocols/`, `kit/files/` directories no longer exist. Their contents move under `kit/aspects/sdd/…` via `git mv`. Only `src/kanon/cli.py` imports from these paths.

### Top-level manifest shape (aspect registry)

```yaml
# src/kanon/kit/manifest.yaml (v0.2 shape)
aspects:
  sdd:
    path: aspects/sdd
    stability: stable
    depth-range: [0, 3]
    default-depth: 1
    requires: []
```

Compared to v0.1, this registry carries no per-tier content lists — those move into per-aspect sub-manifests. Future aspects (`worktrees`, `versioning`, `release`) add entries here.

### Per-aspect sub-manifest shape

```yaml
# src/kanon/kit/aspects/sdd/manifest.yaml
depth-0:
  files: [CLAUDE.md]
  protocols: []
  sections: []
depth-1:
  files:
    - docs/development-process.md
    - docs/decisions/README.md
    - docs/decisions/_template.md
    - docs/plans/README.md
    - docs/plans/_template.md
  protocols: [tier-up-advisor.md, verify-triage.md]
  sections: [plan-before-build, protocols-index]
depth-2:
  files: [docs/specs/README.md, docs/specs/_template.md]
  protocols: [spec-review.md]
  sections: [spec-before-design]
depth-3:
  files:
    - docs/design/README.md
    - docs/design/_template.md
    - docs/foundations/README.md
    - docs/foundations/vision.md
    - docs/foundations/principles/README.md
    - docs/foundations/personas/README.md
  protocols: []
  sections: []
```

Strict-superset semantics carry over from v0.1: `_aspect_files(sdd, depth=N)` returns the union of `depth-0..depth-N` file lists.

Sections now live per-depth in the sub-manifest rather than in a top-level `agents-md-sections` map. This binds section activation to aspect depth instead of tier, and generalises when multiple aspects independently declare sections.

### Consumer layout (`.kanon/`)

```
.kanon/
├── config.yaml               # schema v2 (see § Config schema)
├── kit.md                    # unchanged (rendered from kit/kit.md)
└── protocols/
    └── sdd/                  # NEW namespace; v0.2 upgrade migrates flat → sdd/
        ├── tier-up-advisor.md
        ├── verify-triage.md
        └── spec-review.md
```

Consumer `AGENTS.md` marker sections gain an aspect prefix:

```markdown
<!-- kanon:begin:sdd/plan-before-build -->
...
<!-- kanon:end:sdd/plan-before-build -->
```

The exception is `protocols-index`, which stays unprefixed because it is cross-aspect by definition (see § AGENTS.md rendering below).

## Config schema (v2)

```yaml
# .kanon/config.yaml v2
kit_version: 0.2.0
aspects:
  sdd:
    depth: 2
    enabled_at: 2026-04-23T14:02:11+00:00
    config: {}
```

### Auto-migration from v1

On `kanon upgrade`, if the loaded config has no `aspects:` key, the CLI synthesises one from legacy `tier:` + `tier_set_at:`:

```python
# pseudocode
if "aspects" not in config:
    config = {
        "kit_version": __version__,
        "aspects": {
            "sdd": {
                "depth": config["tier"],
                "enabled_at": config.get("tier_set_at", _now_iso()),
                "config": {},
            },
        },
    }
    click.echo("Migrated legacy tier config to aspect model.")
```

One-way. After `upgrade` writes v2, `tier:` and `tier_set_at:` are removed; older kanon CLIs will not parse the new config.

## Construction flows

### `kanon init <target> --tier N` (backwards-compat)

Equivalent to `kanon init <target> --aspect sdd --depth N` — preserves the v0.1 entry point verbatim:

1. Load top-level manifest (aspect registry).
2. Resolve requested aspects (default: `sdd` at depth N).
3. For each aspect, load its sub-manifest; union depths 0..requested for file/protocol/section lists.
4. Write scaffolded files atomically; protocol files → `.kanon/protocols/<aspect>/<name>.md`.
5. Assemble AGENTS.md (§ below).
6. Render `kit/kit.md` → `.kanon/kit.md`.
7. Generate shims from `harnesses.yaml`.
8. Write `.kanon/config.yaml` v2 with `aspects: {sdd: {depth: N, enabled_at: …, config: {}}}`.

### `kanon aspect add <target> <name> [--depth N]`

1. Load aspect registry; validate `<name>` exists and `stability != deprecated`.
2. Validate `requires:` — every named dep must be enabled in target config.
3. Compute file/protocol/section set at requested depth.
4. Scaffold missing files atomically; never overwrite existing ones (mirrors tier-up, ADR-0008).
5. Rewrite AGENTS.md inserting new marker sections.
6. Append entry to `.kanon/config.yaml` `aspects:` mapping.

### `kanon aspect remove <target> <name>`

1. Load target config; confirm aspect enabled.
2. Validate no other enabled aspect `requires:` this one (fail fast; user removes dependents first).
3. Remove this aspect's marker sections from AGENTS.md; consumer content outside markers untouched.
4. Delete config entry.
5. Report scaffolded files as "beyond required" — leave on disk, user chooses disposition (mirrors tier-down, ADR-0008).

### `kanon upgrade`

1. Load config. If legacy v1 shape, run auto-migration first (§ above).
2. Migrate flat `.kanon/protocols/*.md` under `.kanon/protocols/kanon-sdd/` if still flat.
3. For each enabled aspect, re-render its AGENTS.md sections from the installed kit.
4. Rewrite `.kanon/kit.md`.
5. Update `kit_version` in config.
6. Atomic writes throughout; consumer content outside kit-managed markers untouched.

## AGENTS.md rendering — multi-aspect

AGENTS.md assembly walks enabled aspects in stable order (sorted by aspect name). For each, the sub-manifest at the aspect's current depth yields a section-name list. Section fragments at `kit/aspects/<aspect>/sections/<name>.md` are wrapped:

```
<!-- kanon:begin:<aspect>/<section> -->
<fragment content>
<!-- kanon:end:<aspect>/<section> -->
```

### The unified `protocols-index` block

`protocols-index` is a *special* section. Any aspect's sub-manifest may name it, but its body is rendered dynamically rather than read from a file. The renderer:

1. Walks every enabled aspect's active-depth protocols.
2. Reads each protocol file's frontmatter (`invoke-when`, `tier-min` which v0.2 renames to `depth-min`).
3. Emits a single catalog grouped by aspect:

```markdown
## Active protocols

### sdd (depth 3)
| Protocol | Depth-min | Invoke when |
| --- | --- | --- |
| [tier-up-advisor](.kanon/protocols/kanon-sdd/tier-up-advisor.md) | 1 | … |
…

### worktrees (depth 1)
| Protocol | Depth-min | Invoke when |
…
```

The block is wrapped once in `<!-- kanon:begin:protocols-index --> … <!-- kanon:end:protocols-index -->` (unprefixed).

## Enforcement (`ci/check_kit_consistency.py`)

New invariants:

1. **Aspect path resolution.** Every `aspects.<name>.path` resolves to a directory containing a sub-manifest.
2. **Per-aspect file resolution.** Every path listed in any sub-manifest resolves under `kit/aspects/<name>/files/` or `kit/aspects/<name>/protocols/`.
3. **Cross-aspect ownership exclusivity.** No two aspects scaffold the same relative consumer-path (computed across all aspects' maximum depth).
4. **Whitelist re-scoped per-aspect.** Byte-equality whitelist entries move under the new paths (`kit/aspects/sdd/files/docs/development-process.md` ↔ `docs/development-process.md`; `kit/aspects/sdd/protocols/*.md` ↔ `.kanon/protocols/kanon-sdd/*.md`). Total whitelist stays ≤ 50 entries (maintenance red line).
5. **Stability label validity.** Each registry entry's `stability` ∈ `{experimental, stable, deprecated}`.
6. **Section namespace discipline.** Marker pairs in `kit/aspects/<aspect>/agents-md/depth-*.md` use the `<aspect>/<section>` prefix — except the unprefixed `protocols-index`.

## Interfaces

New or changed helpers in `src/kanon/cli.py`:

- `_load_top_manifest() -> dict` — cached aspect-registry loader.
- `_load_aspect_manifest(aspect: str) -> dict` — cached per-aspect sub-manifest loader.
- `_aspect_files(aspect: str, depth: int) -> list[str]` — union of depth-0..depth file lists.
- `_aspect_protocols(aspect: str, depth: int) -> list[str]` — same for protocols.
- `_aspect_sections(aspect: str, depth: int) -> list[str]` — same for sections.
- `_build_bundle(aspects: dict[str, int], context) -> dict[path, content]` — generalised to iterate aspects.
- `_assemble_agents_md(aspects: dict[str, int], project_name: str) -> str` — generalised; renders per-aspect marker sections and the unified `protocols-index`.
- `_render_protocols_index(aspects: dict[str, int]) -> str` — generalised to group rows by aspect.
- `_migrate_legacy_config(config: dict) -> dict` — one-way v1 → v2 transformer.

New Click subgroup `kanon aspect` with commands `list`, `info`, `add`, `remove`, `set-config`, `set-depth`. Existing `kanon tier set` preserved as backwards-compat sugar for `kanon aspect set-depth <target> sdd <N>`.

`src/kanon/_atomic.py` is unchanged.

## Decisions

- **ADR-0012** — aspect model core (aspects subsume tiers, depth is per-aspect, namespaced markers).
- **ADR-0013** — vision amendment enabling reference automation snippets under aspects with deterministic tails.
- **ADR-0003** — canonical AGENTS.md + shims (unchanged; aspects compose orthogonally).
- **ADR-0006** — tier semantics (preserved as `sdd` aspect's depth semantics).
- **ADR-0008** — tier-migration contract (generalised to `aspect add/remove`).
- **ADR-0010** — protocol layer (namespace extended to `<aspect>/<name>`).
- **ADR-0011** — kit-bundle refactor (manifest-driven data shape; this design extends it by nesting per-aspect manifests).
