---
status: draft
date: 2026-05-04
implements: ADR-0055
---
# Design: Manifest Unification

## Context

[ADR-0055](../decisions/0055-manifest-unification.md) ratifies collapsing the three manifest representations into one. This document describes HOW.

Today every kit aspect has three sources of truth:

1. **Per-aspect `loader.py`** — a hand-written Python dict (`MANIFEST`) that unions registry and content fields. Registered as an entry-point under `kanon.aspects`.
2. **Per-aspect `manifest.yaml`** — holds content fields (`kanon-dialect`, `files`, `depth-N` blocks with `files`, `protocols`, `sections`, `validators`).
3. **Two load paths** — `_load_aspects_from_entry_points()` reads `loader.py` MANIFEST dicts via `importlib.metadata` for registry discovery; `_load_aspect_manifest()` separately reads `manifest.yaml` from disk for content fields.

The `loader.py` dict and `manifest.yaml` must stay in sync manually. A drift test binds them, but the duplication is structural debt.

## Architecture

### Current state (before)

```
kanon_aspects/aspects/kanon_sdd/
├── loader.py          # Python dict: registry + content fields (entry-point target)
├── manifest.yaml      # YAML: content fields only (read by _load_aspect_manifest)
├── files/
├── protocols/
└── sections/
```

Two load paths converge at runtime:

```python
# Path 1: registry discovery (entry-points)
_load_aspects_from_entry_points()
    → importlib.metadata.entry_points(group="kanon.aspects")
    → ep.load()  # imports loader.py, returns MANIFEST dict
    → registry fields: stability, depth-range, default-depth, description, ...

# Path 2: content loading (disk)
_load_aspect_manifest("kanon-sdd")
    → _aspect_path("kanon-sdd") / "manifest.yaml"
    → _load_yaml(sub_path)
    → content fields: files, depth-0, depth-1, ...
```

### Target state (after)

```
kanon_aspects/aspects/kanon_sdd/
├── loader.py          # 3-line trampoline (reads manifest.yaml, exports MANIFEST)
├── manifest.yaml      # YAML: ALL fields — single source of truth
├── files/
├── protocols/
└── sections/
```

One load path per aspect type:

```python
# Kit aspects: entry-point returns the full dict (registry + content)
_load_aspects_from_entry_points()
    → ep.load()  # trampoline reads YAML, returns complete dict
    → ALL fields in one dict

# _load_aspect_manifest() for kit aspects:
#   returns the already-loaded entry-point dict — no second disk read
```

### Unified `manifest.yaml` (example: `kanon-sdd`)

```yaml
kanon-dialect: "2026-05-01"
stability: stable
depth-range: [0, 3]
default-depth: 1
description: "Spec-Driven Development: plans, specs, design docs"
requires: []
provides: [planning-discipline, spec-discipline]
suggests: []
byte-equality:
  - { kit: docs/sdd-method.md, repo: docs/sdd-method.md }
files: []
depth-0:
  files: []
  protocols: []
  sections: []
depth-1:
  files: [docs/sdd-method.md, docs/decisions/README.md, ...]
  protocols: [tier-up-advisor.md, verify-triage.md, ...]
  sections: [protocols-index]
  validators: [kanon_core._validators.plan_completion, ...]
depth-2:
  files: [docs/specs/README.md, docs/specs/_template.md]
  protocols: [spec-review.md, spec-before-design.md, adr-immutability.md]
  sections: []
  validators: [kanon_core._validators.link_check, ...]
depth-3:
  files: [docs/design/README.md, docs/design/_template.md, ...]
  protocols: []
  sections: []
  validators: [kanon_core._validators.spec_design_parity]
```

### Trampoline `loader.py` (replaces hand-written dict)

```python
from importlib.resources import files
import yaml

MANIFEST = yaml.safe_load(files(__package__).joinpath("manifest.yaml").read_text("utf-8"))
```

### `_load_aspect_manifest()` simplification

```python
@cache
def _load_aspect_manifest(aspect: str) -> dict[str, Any]:
    entry = _aspect_entry(aspect)
    if entry is None:
        raise click.ClickException(f"Unknown aspect: {aspect!r}.")
    # Kit aspects: the entry-point dict already contains all fields.
    if aspect.startswith(f"{_KANON_NAMESPACE}-"):
        return entry
    # Project aspects: read from .kanon/aspects/<name>/manifest.yaml (unchanged).
    sub_path = _aspect_path(aspect) / "manifest.yaml"
    if not sub_path.is_file():
        raise click.ClickException(f"aspect sub-manifest missing: {sub_path}")
    return _load_yaml(sub_path)
```

## Interfaces

### Entry-point contract (unchanged)

- Group: `kanon.aspects`
- Each entry-point resolves to a `MANIFEST` dict.
- The dict now contains **all** fields — registry and content merged.

### Unified manifest.yaml schema

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `kanon-dialect` | `str` | yes | Dialect pin (validated by `validate_dialect_pin`) |
| `stability` | `str` | yes | `"stable"` or `"experimental"` |
| `depth-range` | `[int, int]` | yes | `[min, max]` |
| `default-depth` | `int` | yes | Must be within depth-range |
| `description` | `str` | yes | Human-readable summary |
| `requires` | `list[str]` | yes | Capability predicates; `[]` if none |
| `provides` | `list[str]` | yes | Capability tokens; `[]` if none |
| `suggests` | `list[str]` | yes | Soft dependencies; `[]` if none |
| `files` | `list[str]` | yes | Top-level files; `[]` if none |
| `depth-N` | `mapping` | yes (per range) | Keys: `files`, `protocols`, `sections`, `validators` — all `list`, never null |

### `_load_aspect_manifest()` simplified contract

- **`kanon-*` aspects**: returns the entry-point dict directly (already loaded by `_load_aspects_from_entry_points`). No disk read.
- **`project-*` aspects**: reads `manifest.yaml` from `.kanon/aspects/<name>/` on disk (unchanged).
- Cache: `@cache` decorated (unchanged).

## Decisions

1. **YAML over Python for canonical representation** — declarative data belongs in a declarative format. The `loader.py` dict was a transitional artifact; YAML is the natural home.
2. **`importlib.resources` over `importlib.metadata` for YAML access** — `resources` is designed for package-relative data files; `metadata` is for entry-point objects. The trampoline bridges the two.
3. **Trampoline over codegen** — runtime YAML loading is simpler than build-time code generation and works correctly with editable installs (`pip install -e .`).
4. **Merge registry into per-aspect YAML over keeping a central registry** — eliminates the third source of truth. The drift test between `loader.py` and `manifest.yaml` becomes unnecessary.
5. **All list fields must be `[]`, never null** — enforced by schema validation, prevents the `NoneType` iteration bugs that null YAML values cause.
