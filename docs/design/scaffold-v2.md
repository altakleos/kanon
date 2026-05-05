---
status: accepted
implements: docs/specs/scaffold-v2.md
date: 2026-04-28
---
# Design: Scaffold v2 — thin kernel, routing-index AGENTS.md

## Context

The current scaffold architecture has three problems:

1. **AGENTS.md is a content repository** (406 lines at depth 3). 71%
   is inlined discipline prose that duplicates protocol files. Every
   token competes with the agent's actual task.
2. **No file categories.** All files are aspect-depth-specific. Files
   that should be aspect-wide (sdd-method.md) or kit-global
   (kit.md) are hacked into depth-0/1 declarations.
3. **sdd is structurally privileged.** CLAUDE.md lives under sdd
   depth-0. kit.md hardcodes `${sdd_depth}`. worktrees requires sdd.

## Architecture

### File resolution pipeline

```
kit-global files          (top manifest `files:`)
  ∪ harness shims         (harnesses.yaml, filtered by --harness)
  ∪ for each (aspect, depth) in enabled_aspects:
      aspect-level files  (sub-manifest top-level `files:`)
      ∪ depth-level files (sub-manifest `depth-0..depth-N: files:`)
      ∪ protocols         (sub-manifest `depth-0..depth-N: protocols:`)
  ∪ AGENTS.md             (synthesized: base template + protocols-index)
  ∪ .kanon/config.yaml    (synthesized)
```

### Manifest schema changes

**Top-level manifest** — new `files:` key:

```yaml
files:                    # kit-global: always scaffolded
  - .kanon/kit.md

defaults: [kanon-sdd]    # CLI convenience, not structural requirement
aspects: { ... }          # unchanged
```

Source directory: `src/kanon/kit/files/`. Resolved before aspects.

**Sub-manifest** — new top-level `files:` key, `sections:` removed:

```yaml
files:                    # aspect-level: scaffolded at any depth
  - docs/sdd-method.md

depth-0:
  files: []               # CLAUDE.md removed (harness shim)
  protocols: []
  # sections: key REMOVED

depth-1:
  files:
    - docs/decisions/README.md
    - docs/plans/README.md
    # ...
  protocols:
    - plan-before-build.md    # NEW: was AGENTS.md section
    - spec-before-design.md   # NEW: was AGENTS.md section
    - completion-checklist.md
    - scope-check.md
    - tier-up-advisor.md
    - verify-triage.md
  # sections: key REMOVED
```

### Python changes

**`_load_aspect_manifest()`** — accept optional `files:` at top level
(list of strings, same shape as `depth-N.files`). No validation change
needed — the loader already ignores unknown top-level keys.

**`_aspect_files(aspect, depth)`** — prepend aspect-level files:

```python
def _aspect_files(aspect: str, depth: int) -> list[str]:
    sub = _load_aspect_manifest(aspect)
    base = list(sub.get("files", []) or [])
    base.extend(_aspect_items(aspect, depth, "files"))
    return base
```

**`_build_bundle()`** — add kit-global file loop before aspect loop:

```python
top = _load_top_manifest()
kit_files_root = _kit_root() / "files"
for rel in top.get("files", []):
    src = kit_files_root / rel
    bundle[rel] = _render_placeholder(src.read_text(...), context)
# ... then existing aspect loop (which now picks up aspect-level files)
```

**`_expected_files()`** — add kit-global files:

```python
top = _load_top_manifest()
paths.extend(top.get("files", []))
```

**`_assemble_agents_md()`** — simplify dramatically:

```python
def _assemble_agents_md(aspects, project_name):
    base = (_kit_root() / "agents-md-base.md").read_text(...)
    context = {"project_name": project_name, ...}
    text = _render_placeholder(base, context)
    # Render protocols-index into the single remaining marker
    index = _render_protocols_index(aspects)
    text = _replace_section(text, "protocols-index", index)
    return text
```

No body injection. No section filling. No inactive-section sweep.
The base template IS the complete routing index; protocols-index is
the only dynamic element.

**`_render_protocols_index()`** — gains rows for former section
protocols (plan-before-build, spec-before-design, branch-hygiene).
No structural change — these are just more protocol files with
frontmatter `invoke-when:` triggers.

### AGENTS.md base template (new)

The `agents-md-base.md` template becomes the complete routing index.
It uses `${project_name}` and `${active_aspects_summary}` placeholders
plus the `<!-- kanon:begin:protocols-index -->` marker.

Structure (~80 lines at depth 3, ~60 at depth 1):

```
# AGENTS.md — ${project_name}
[1-line identity]

## Contributor Boot Chain
[numbered links to docs — varies by which aspects are enabled]

## Project Layout
[directory tree — static]

## Key Constraints
[3-5 lines — static]

## Hard Gates
| Gate | Protocol |
[3 rows max: plan-before-build, spec-before-design, worktree-isolation]
[each row: trigger + one-sentence summary + audit sentence + link]

## Task Playbook
[phase → capability profile → protocol table]

## Quick Start by Task Type
[task type → must-read → can-skip table]

<!-- kanon:begin:protocols-index -->
## Active Protocols
[dynamically rendered table grouped by aspect]
<!-- kanon:end:protocols-index -->

## Contribution Conventions
[commit messages, changelog, versions]

## References
[links to key docs]
```

The hard-gates table is static in the template but conditionally
rendered: only gates whose aspect is enabled appear. This is handled
by `_render_placeholder` with conditional blocks or by a small
rendering function that filters gate rows by enabled aspects.

### Content migration map

| Current location | New location | Category |
|-----------------|-------------|----------|
| AGENTS.md `plan-before-build` section (24 lines) | `.kanon/protocols/kanon-sdd/plan-before-build.md` | depth-1 protocol |
| AGENTS.md `spec-before-design` section (24 lines) | `.kanon/protocols/kanon-sdd/spec-before-design.md` | depth-2 protocol |
| AGENTS.md `branch-hygiene` section (28 lines) | `.kanon/protocols/kanon-worktrees/branch-hygiene.md` | depth-1 protocol |
| AGENTS.md `secure-defaults` section (18 lines) | Already exists as protocol — delete section | — |
| AGENTS.md `dependency-hygiene` section (16 lines) | Already exists as protocol — delete section | — |
| AGENTS.md `test-discipline` section (16 lines) | Already exists as protocol — delete section | — |
| AGENTS.md `publishing-discipline` section (20 lines) | `.kanon/protocols/kanon-release/publishing-discipline.md` | depth-1 protocol |
| AGENTS.md `fidelity-discipline` section (14 lines) | `.kanon/protocols/kanon-fidelity/fidelity-discipline.md` | depth-1 protocol |
| AGENTS.md aspect body sections (~55 lines total) | Eliminated — content folded into protocol preambles or dropped | — |
| `sections/` directories (all aspects) | Deleted | — |
| `agents-md/depth-N.md` body files (all aspects) | Deleted | — |
| `docs/sdd-method.md` (458 lines) | `docs/sdd-method.md` (~50 lines, sdd aspect-level file) | aspect-level |
| `.kanon/kit.md` (sdd-specific) | `.kanon/kit.md` (aspect-neutral, kit-global file) | kit-global |
| `CLAUDE.md` (sdd depth-0 file) | Harness shim (already handled by harnesses.yaml) | harness shim |

### sdd de-privileging

1. **CLAUDE.md** removed from sdd depth-0 files. Already rendered by
   `_render_shims()` from harnesses.yaml — the sdd declaration was
   redundant.
2. **worktrees** `requires: "kanon-sdd >= 1"` → `suggests:`. Worktree
   isolation is orthogonal to planning discipline.
3. **kit.md** rewritten with `${active_aspects_summary}` placeholder
   instead of `${sdd_depth}`. Aspect-neutral.
4. **`_default_aspects()`** unchanged — `defaults: [kanon-sdd]` stays
   in the manifest as a CLI convenience. The distinction: it's a
   default, not a requirement. `kanon init --aspects testing:1` works.

### Upgrade path

`kanon upgrade` on a pre-v2 project:

1. Detects old-style AGENTS.md (has `kanon:begin/end` marker sections
   beyond `protocols-index`).
2. Strips all marker sections except `protocols-index`.
3. Replaces the base content with the new routing-index template.
4. Preserves any user content outside markers (existing
   `_merge_agents_md` logic handles this).
5. Scaffolds new protocol files (plan-before-build.md, etc.) if
   missing.
6. Removes `sections/` from `.kanon/protocols/` if present.

### Byte-equality impact

- `sdd-method.md` entry removed (file renamed).
- `sdd-method.md` entry added.
- Section-file entries removed (sections eliminated).
- New protocol-file entries added (plan-before-build.md, etc.).
- kit.md entry updated (now kit-global, not sdd-owned).

## Alternatives considered

| Alternative | Why rejected |
|------------|-------------|
| Keep AGENTS.md as content repository, add depth-gating | Doesn't solve duplication; 71% of content still inlined |
| Template/conditional sections in AGENTS.md | `string.Template` doesn't support conditionals; adding Jinja adds a dependency |
| Move hard gates to protocol-only (full routing) | Violates ADR-0010 enforcement-proximity principle; hard gates must be visible at boot |
| Keep sdd structurally required | Violates aspect model's own design principle (opt-in disciplines) |

## Risks

1. **Agents may not read protocol files on trigger.** Mitigated by
   keeping hard gates inline (compressed) and using audit-trail
   sentences as enforcement.
2. **Upgrade strips user customizations in marker sections.** Mitigated
   by `_merge_agents_md` preserving content outside markers.
3. **Breaking change for consumers.** Mitigated by `kanon upgrade`
   handling the transition automatically.

## Status under ADR-0048 + ADR-0062

[ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) (de-opinionation transition) and [ADR-0062](../decisions/0062-declarative-hard-gates.md) (declarative hard gates) shipped after this design was drafted. They preserve most of the design's intent, retire two of its proposed mechanisms entirely, and amend one. The historical body above is preserved verbatim per the design-doc convention used by [`aspect-model.md`](aspect-model.md); this section is the canonical bridge between then-and-now.

### Survives

- **Slim AGENTS.md as routing index.** The `_assemble_agents_md` simplification proposed in §"Python changes" landed: load base template, render `${project_name}` placeholder, replace the `protocols-index` marker, leave the rest as-is. Implementation: [`packages/kanon-core/src/kanon_core/_scaffold.py`](../../packages/kanon-core/src/kanon_core/_scaffold.py) `_assemble_agents_md`.
- **sdd de-privileging.** CLAUDE.md is a harness shim (rendered from [`packages/kanon-core/src/kanon_core/kit/harnesses.yaml`](../../packages/kanon-core/src/kanon_core/kit/harnesses.yaml)), not an sdd file. `kanon-worktrees` declares `suggests: ["kanon-sdd >= 1"]` not `requires:` ([`packages/kanon-aspects/src/kanon_aspects/aspects/kanon_worktrees/manifest.yaml`](../../packages/kanon-aspects/src/kanon_aspects/aspects/kanon_worktrees/manifest.yaml)). All hard `kanon-sdd` requirements have been refactored away.
- **Per-aspect protocol files.** `plan-before-build.md`, `spec-before-design.md`, `branch-hygiene.md`, `publishing-discipline.md`, `fidelity-discipline.md` ship as discrete protocol files, scaffolded into `.kanon/protocols/<aspect>/` per the design's content migration map. The aspect-level `files:` key landed (under [ADR-0055](../decisions/0055-manifest-unification.md)'s unified manifest shape).
- **Dynamic `protocols-index`.** Cross-aspect catalog rendered from each aspect's protocol-file frontmatter (`invoke-when:`, `depth-min:`). Implementation: `_render_protocols_index` in `_scaffold.py`.

### Superseded by ADR-0048 (Phase A.3 de-opinionation)

- **Top-level kit-global `files:` field.** §"Manifest schema changes" proposed retaining a top-level `files: [.kanon/kit.md]` block. ADR-0048 retired all kit-global file scaffolding entirely. The substrate scaffolds nothing on its own behalf; aspects own all the files they ship. The `files:` key (and the entire `kanon_core/kit/manifest.yaml` file, retired in plan [`retire-kit-aspects-yaml`](../plans/active/retire-kit-aspects-yaml.md) T4) is gone; the canonical aspect registry is now the per-aspect manifests under [`packages/kanon-aspects/src/kanon_aspects/aspects/`](../../packages/kanon-aspects/src/kanon_aspects).
- **`defaults: [kanon-sdd]` as a "CLI convenience".** §"sdd de-privileging" §4 proposed keeping `defaults:` in the manifest as a CLI convenience for `kanon init` with no flags. ADR-0048 deleted the `defaults:` block entirely. Today, `kanon init` with no flags scaffolds an empty project; the consumer must explicitly opt in via `--aspects`, `--tier`, `--lite`, or `--profile` (see [`packages/kanon-core/src/kanon_core/cli.py`](../../packages/kanon-core/src/kanon_core/cli.py) `init`, lines 272-276). `_default_aspects()` was retired.
- **`${active_aspects_summary}` placeholder for `kit.md`.** §"sdd de-privileging" §3 proposed rewriting `kit.md` with the placeholder. `kit.md` itself was retired alongside the kit-global `files:` field. The placeholder is unused.

### Amended by ADR-0062 (declarative hard gates)

- **Hard-gates table rendering.** §"AGENTS.md base template (new)" proposed a static template containing the hard-gates table, with conditional row rendering by enabled aspect. ADR-0062 made the table fully dynamic: gates are declared in protocol-file frontmatter (`gate: hard`, `label`, `summary`, `audit`, `priority`, `question`, `skip-when`); `_render_hard_gates` in `_scaffold.py` walks every enabled protocol, filters by `gate: hard` and `depth-min`, sorts by priority, and emits the markdown table plus a dynamic decision-tree numbered checklist. Any aspect — including `acme-` and `project-` aspects — can declare hard gates the substrate honours identically (publisher symmetry per [`P-publisher-symmetry`](../foundations/principles/P-publisher-symmetry.md)).
