---
status: accepted
date: 2026-05-01
implements: docs/specs/release-cadence.md
---
# Design: Distribution boundary — pyproject shapes, recipe schema, migration outline

## Context

[`docs/specs/release-cadence.md`](../specs/release-cadence.md) defines the cadence invariants the substrate enforces; [ADR-0043](../decisions/0043-distribution-boundary-and-cadence.md) ratifies the distribution boundary, cadence policy, and recipe artifact in one decision. This design specifies *how* the substrate packages: concrete `pyproject.toml` shapes for `kanon-core`, `kanon-aspects`, and `kanon-kit`; concrete recipe YAML schema; the cadence-CI-gate algorithm; and the `kanon migrate v0.3 → v0.4` script outline.

## `pyproject.toml` shapes

### `kanon-core/pyproject.toml`

The kernel-only distribution. Ships zero aspects.

```toml
[project]
name = "kanon-core"
version = "1.0.0a1"
description = "Protocol substrate for prose-as-code engineering discipline in LLM-agent-driven repos."
readme = "README.md"
requires-python = ">=3.10"
license = { file = "LICENSE" }
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Operating System :: POSIX",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
]

[project.scripts]
kanon = "kanon.cli:main"

[project.urls]
Homepage = "https://github.com/altakleos/kanon"
Documentation = "https://github.com/altakleos/kanon/blob/main/docs/foundations/vision.md"

[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["kernel"]
exclude = [
    "kernel/kit/aspects/**",  # kit-shape aspects retired; ship none
]
```

Critical: the `exclude` clause ensures no kit-shape aspect content leaks into the substrate wheel. Phase A authors a CI assertion that verifies the wheel contains zero `kanon/kit/aspects/` files.

### `kanon-aspects/pyproject.toml`

Ships the seven reference aspects as data. Declares Python entry-points per [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md).

```toml
[project]
name = "kanon-aspects"
version = "1.0.0a1"
description = "Reference discipline aspects for the kanon protocol substrate."
readme = "README.md"
requires-python = ">=3.10"
license = { file = "LICENSE" }
dependencies = [
    "kanon-core>=1.0.0a1,<2.0",
]

[project.entry-points."kanon.aspects"]
kanon-sdd = "kanon_reference.aspects.kanon_sdd:MANIFEST"
kanon-testing = "kanon_reference.aspects.kanon_testing:MANIFEST"
kanon-worktrees = "kanon_reference.aspects.kanon_worktrees:MANIFEST"
kanon-release = "kanon_reference.aspects.kanon_release:MANIFEST"
kanon-security = "kanon_reference.aspects.kanon_security:MANIFEST"
kanon-deps = "kanon_reference.aspects.kanon_deps:MANIFEST"
kanon-fidelity = "kanon_reference.aspects.kanon_fidelity:MANIFEST"

[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/kanon_reference"]
```

### `kanon-kit/pyproject.toml` (meta-alias)

Ships zero source. Pins `kanon-core` and `kanon-aspects` at coordinated versions.

```toml
[project]
name = "kanon-kit"
version = "1.0.0a1"
description = "Convenience meta-package: installs kanon-core plus kanon-aspects."
readme = "README.md"
requires-python = ">=3.10"
license = { file = "LICENSE" }
dependencies = [
    "kanon-core==1.0.0a1",
    "kanon-aspects==1.0.0a1",
]

[build-system]
requires = ["hatchling>=1.18"]
build-backend = "hatchling.build"
```

The exact version pins (rather than `>=` ranges) ensure `pip install kanon-kit==1.0.0a1` produces a reproducible install across the three packages. `kanon-core` and `kanon-aspects` may evolve independently; `kanon-kit` ships coordinated bundles at lockstep versions.

## Recipe YAML schema

A recipe is publisher-shipped target-tree YAML. Schema:

```yaml
# kanon-aspects/recipes/reference-default.yaml (shipped as data in kanon-aspects)
---
schema-version: 1
recipe-id: reference-default
publisher: kanon-aspects
recipe-version: "1.0"
target-dialect: "2026-05-01"
description: "Default reference recipe — opts the consumer into all seven kanon-aspects aspects at their default depths."
aspects:
  - id: kanon-sdd
    depth: 1
  - id: kanon-testing
    depth: 1
  - id: kanon-worktrees
    depth: 1
  - id: kanon-release
    depth: 1
  - id: kanon-security
    depth: 1
  - id: kanon-deps
    depth: 1
  - id: kanon-fidelity
    depth: 1
```

### Field semantics

- **`schema-version`**: `1`. Reserved for future schema evolution under dialect supersession.
- **`recipe-id`**: a stable slug identifying this recipe within the publisher's namespace. `<publisher-name>-<recipe-name>` is conventional but not required.
- **`publisher`**: the distribution name of the publisher shipping this recipe. Used by the substrate's provenance tracking.
- **`recipe-version`**: semver string; recipes evolve under publisher discretion.
- **`target-dialect`**: the dialect-version pin this recipe expects (per `INV-dialect-grammar-pin-required`). The substrate refuses to apply a recipe whose target-dialect it does not support.
- **`description`**: human-readable; rendered by `kanon aspect list --recipes`.
- **`aspects`**: list of `{id, depth, [config]}` triples. The `config:` field is optional; per-aspect-config overrides the aspect's defaults.

### Consumer-side application

The recipe lives in the consumer's repo at `.kanon/recipes/<recipe-name>.yaml` (committed). Consumer applies via:

```bash
# Copy the recipe from the publisher bundle to the consumer repo.
cp $(pip show kanon-aspects | grep Location | awk '{print $2}')/kanon_reference/recipes/reference-default.yaml \
   .kanon/recipes/reference-default.yaml

# Commit it.
git add .kanon/recipes/reference-default.yaml
git commit -m "feat: opt into reference-default recipe (kanon-aspects 1.0)"

# kanon next read of .kanon/config.yaml + .kanon/recipes/* enables the recipe's aspects.
kanon verify .
```

The substrate has no `kanon recipes apply` verb. Application is a copy + commit; the kernel reads `.kanon/recipes/` at registry composition time.

## Cadence policy — release-workflow CI gate algorithm

Phase A's `scripts/check_release_cadence.py` (or analogous) enforces `INV-release-cadence-breaking-not-in-kernel`:

```python
# scripts/check_release_cadence.py (Phase A)
#
# Fails if a `kanon-core` kernel release commit also touches
# dialect-grammar files (which would breach INV-release-cadence-breaking-not-in-kernel).

import subprocess, sys
from pathlib import Path

KERNEL_VERSION_FILE = Path("kanon-core/kernel/__init__.py")
DIALECT_GRAMMAR_PATHS = [
    Path("docs/specs/dialect-grammar.md"),
    Path("docs/design/dialect-grammar.md"),
    Path("kanon-core/kernel/_dialects.py"),
]

def main():
    # Detect: was this commit a kernel-version bump?
    diff = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
    ).decode().splitlines()
    kernel_release = str(KERNEL_VERSION_FILE) in diff

    if not kernel_release:
        print("not a kernel release; cadence gate inactive")
        return

    # Was a dialect-grammar file also touched?
    dialect_touched = any(str(p) in diff for p in DIALECT_GRAMMAR_PATHS)
    if dialect_touched:
        print("FAIL: kernel release commit must not touch dialect-grammar.", file=sys.stderr)
        print("Per INV-release-cadence-breaking-not-in-kernel, breaking changes ship as", file=sys.stderr)
        print("dialect supersessions, not kernel releases.", file=sys.stderr)
        sys.exit(1)

    print("cadence gate: OK")

if __name__ == "__main__":
    main()
```

The check is conservative: it rejects coincidental same-commit bundling. If a release genuinely needs both kernel and dialect changes, the resolution is two commits across two PRs.

## Migration script — `kanon migrate v0.3 → v0.4` outline

The migration script (Phase A) transitions a v0.3.x consumer repo to v0.4. It is deprecated-on-arrival per [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md)'s migration commitment; deleted after the kanon repo's own migration commit lands.

```python
# kanon-core/kernel/_migration_v3_to_v4.py (Phase A; deprecated-on-arrival)
#
# Migrates a v0.3.x consumer repo to v0.4.
#
# - Rewrites .kanon/config.yaml to opt-in form (no defaults; explicit aspect+depth list)
# - Copies kanon-aspects's reference-default recipe to .kanon/recipes/
# - Adds kanon-dialect: 2026-05-01 to migrated config
# - Records migration provenance

def migrate_v3_to_v4(target: Path) -> MigrationReport:
    report = MigrationReport()
    config = parse_yaml(target / ".kanon" / "config.yaml")
    if config.get("schema-version") == 4:
        report.skip("already-v4", "config already at schema-version 4")
        return report
    if config.get("schema-version", 3) > 4:
        report.error("future-schema", "config newer than v4; cannot downgrade")
        return report

    # 1. Rewrite to opt-in form.
    new_config = {
        "schema-version": 4,
        "kanon-dialect": "2026-05-01",
        "aspects": {},
        "provenance": [
            {
                "recipe": "migration-v3-to-v4",
                "publisher": "kanon-core",
                "applied_at": iso8601_now(),
            },
        ],
    }
    for aspect_name, aspect_config in config.get("aspects", {}).items():
        new_config["aspects"][aspect_name] = {
            "depth": aspect_config["depth"],
            "config": aspect_config.get("config", {}),
        }
    write_yaml_atomic(target / ".kanon" / "config.yaml", new_config)
    report.add("rewrote-config", "schema v3 → v4")

    # 2. Copy reference-default recipe if kanon-aspects is installed.
    if importlib.util.find_spec("kanon_reference"):
        recipe_src = Path(importlib.util.find_spec("kanon_reference").origin).parent / "recipes" / "reference-default.yaml"
        recipe_dst = target / ".kanon" / "recipes" / "reference-default.yaml"
        if recipe_src.exists():
            recipe_dst.parent.mkdir(parents=True, exist_ok=True)
            recipe_dst.write_bytes(recipe_src.read_bytes())
            report.add("copied-recipe", "reference-default")

    return report
```

## Phase A implementation footprint

| Surface | LOC delta | What |
|---|---:|---|
| `kanon-core/pyproject.toml` | ~+50 | New file (kernel-only distribution shape) |
| `kanon-aspects/pyproject.toml` | ~+30 | New file (entry-points declaration) |
| `kanon-kit/pyproject.toml` | ~+20 | New file (meta-alias) |
| `kanon-aspects/recipes/reference-default.yaml` | ~+30 | First recipe; opts into seven aspects at default depths |
| `_migration_v3_to_v4.py` | ~+100 | Migration script (deprecated-on-arrival) |
| `scripts/check_release_cadence.py` | ~+80 | Cadence-gate CI script |
| Release workflows (`.github/workflows/release.yml` rewrite) | ~+150 | Three publish jobs (substrate, reference, meta-alias) |
| Tests | ~+200 | Recipe-shape validation; cadence-gate tests; migration-script tests |

Total: ~+660 LOC source / +200 LOC tests across ~10 files.

## Decisions

- [ADR-0043](../decisions/0043-distribution-boundary-and-cadence.md) — parent decision.
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment.
- [ADR-0041](../decisions/0041-realization-shape-dialect-grammar.md) — dialect grammar.
- [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) — runtime interface.
