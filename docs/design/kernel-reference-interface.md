---
status: accepted
date: 2026-05-01
implements: docs/specs/aspects.md
---
# Design: Kernel/reference runtime interface — entry-point discovery, registry composition, and `_kit_root()` retirement

## Context

[ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) ratified the discovery mechanism: Python entry-points group `kanon.aspects`. This document specifies the concrete shape — entry-point format, registry composition algorithm, the independence-invariant CI gate, and the `_kit_root()` retirement walkthrough.

[ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) is the protocol-substrate commitment that makes the split necessary.

## Entry-point shape

Publishers register aspects via `[project.entry-points."kanon.aspects"]` in their package's `pyproject.toml`:

```toml
# kanon-reference/pyproject.toml (the kit-author's reference bundle)
[project]
name = "kanon-reference"
version = "1.0.0"
dependencies = ["kanon-substrate>=1.0"]

[project.entry-points."kanon.aspects"]
kanon-sdd = "kanon_reference.aspects.kanon_sdd:MANIFEST"
kanon-testing = "kanon_reference.aspects.kanon_testing:MANIFEST"
kanon-worktrees = "kanon_reference.aspects.kanon_worktrees:MANIFEST"
kanon-release = "kanon_reference.aspects.kanon_release:MANIFEST"
kanon-security = "kanon_reference.aspects.kanon_security:MANIFEST"
kanon-deps = "kanon_reference.aspects.kanon_deps:MANIFEST"
kanon-fidelity = "kanon_reference.aspects.kanon_fidelity:MANIFEST"
```

A third-party publisher (`acme-fintech-compliance`) registers analogously:

```toml
# acme-fintech-compliance/pyproject.toml
[project]
name = "acme-fintech-compliance"
version = "1.0.0"
dependencies = ["kanon-substrate>=1.0"]

[project.entry-points."kanon.aspects"]
acme-fintech-compliance = "acme_fintech_compliance.kanon:MANIFEST"
```

### Resolver shape — what the entry-point value resolves to

The entry-point value is a dotted Python path resolving to one of:

1. **A module attribute named `MANIFEST`** containing the parsed manifest dict (most common).
2. **A callable** (function or class) returning the manifest dict when invoked with no arguments.

Phase A's entry-point loader tries (1) first, then (2). The kernel does not import the publisher's full package — only the module the entry-point names. The manifest dict has the same shape as today's `src/kanon/kit/aspects/<aspect>/manifest.yaml` (preserved per ADR-0028).

### Why `MANIFEST`-as-attribute is the recommended shape

Static attribute (vs. callable) makes the manifest discoverable to type-checkers, lints, and offline analysis tools. Publishers writing in pure-data style produce a YAML→Python conversion at package-build time; the runtime cost at substrate-startup is one module import per publisher.

## Registry composition algorithm

`_load_aspect_registry(target: Path) -> AspectRegistry`. Pseudocode:

```python
def _load_aspect_registry(target: Path) -> AspectRegistry:
    registry = AspectRegistry()

    # Source 1: entry-point publishers.
    for ep in importlib.metadata.entry_points(group="kanon.aspects"):
        aspect_slug = ep.name  # e.g., "kanon-sdd", "acme-fintech-compliance"
        publisher_dist = ep.dist  # the distribution object
        validate_namespace_ownership(aspect_slug, publisher_dist)  # see below
        manifest = load_manifest_via_entry_point(ep)
        publisher_path = Path(publisher_dist.locate_file(""))  # distribution root
        registry.register(
            aspect=aspect_slug,
            manifest=manifest,
            publisher_path=publisher_path,
            source="entry-point",
        )

    # Source 2: project-aspects (per ADR-0028; preserved verbatim).
    project_aspects_dir = target / ".kanon" / "aspects"
    if project_aspects_dir.exists():
        for aspect_dir in sorted(project_aspects_dir.iterdir()):
            if not aspect_dir.is_dir():
                continue
            if not aspect_dir.name.startswith("project-"):
                continue  # source-bounded namespace per ADR-0028
            manifest_path = aspect_dir / "manifest.yaml"
            if not manifest_path.exists():
                continue
            manifest = load_yaml(manifest_path)
            registry.register(
                aspect=aspect_dir.name,
                manifest=manifest,
                publisher_path=aspect_dir,
                source="project-aspect",
            )

    # Source 3: test overlays (development only).
    overlay = os.environ.get("KANON_TEST_OVERLAY_PATH")
    if overlay:
        for aspect_dir in Path(overlay).iterdir():
            # ... same shape as project-aspects ...
            registry.register(..., source="test-overlay")

    # Collision detection: same aspect slug from multiple sources is an error.
    registry.check_collisions()

    return registry
```

### Namespace ownership validation

Per ADR-0040 Decision §5: an entry-point may only register aspect slugs that match its distribution's namespace. The validator:

```python
def validate_namespace_ownership(aspect_slug: str, dist: Distribution) -> None:
    parts = aspect_slug.split("-", 1)
    if len(parts) < 2:
        raise InvalidAspectError(f"aspect slug must be <namespace>-<local>: {aspect_slug}")
    namespace, _local = parts

    if namespace == "kanon":
        if dist.metadata["name"] != "kanon-reference":
            raise NamespaceViolationError(
                f"aspect '{aspect_slug}' uses 'kanon-' namespace but is registered "
                f"by distribution '{dist.metadata['name']}', not 'kanon-reference'"
            )
    elif namespace == "project":
        raise NamespaceViolationError(
            f"aspect '{aspect_slug}' uses 'project-' namespace; project aspects "
            "must be declared in <target>/.kanon/aspects/, not via entry-points"
        )
    elif namespace.startswith("acme-") or namespace == "acme":
        # acme-<vendor>-<aspect>: dist must be 'acme-<vendor>'
        # ... validation logic per ADR-0028's namespace grammar ...
        pass
    else:
        # Unknown namespace; allowed but warned (future ADRs may reserve)
        warnings.warn(f"unknown publisher namespace '{namespace}' in aspect '{aspect_slug}'")
```

### Aspect path resolution

Per ADR-0040 Decision §7: aspect path lookup goes through the registry. Each registered aspect carries a `publisher_path` (the distribution's file-system root). Aspect-relative paths concatenate:

```python
def aspect_path(registry: AspectRegistry, aspect: str) -> Path:
    entry = registry.get(aspect)
    if entry is None:
        raise UnknownAspectError(aspect)
    # The manifest's `path:` field is publisher-relative.
    return entry.publisher_path / entry.manifest["path"]
```

This replaces every call site of `_kit_root() / aspect_relative_path`.

## The independence invariant — CI gate algorithm

Per ADR-0040 Decision §6: `kanon-substrate`'s test suite must pass with `kanon-reference` uninstalled.

```bash
# ci/check_substrate_independence.py (Phase A authors)
#
# 1. Create a clean venv.
# 2. pip install -e ./kanon-substrate    (kernel only — no kanon-reference)
# 3. Run pytest against tests/.
# 4. Assert exit 0.
# 5. Optionally: assert no test was skipped due to "kanon-reference not available".

import subprocess, tempfile, sys
from pathlib import Path

def main():
    with tempfile.TemporaryDirectory() as tmp:
        venv = Path(tmp) / ".venv"
        subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
        pip = venv / "bin" / "pip"
        pytest = venv / "bin" / "pytest"
        subprocess.check_call([str(pip), "install", "-e", "."])  # substrate only
        result = subprocess.run([str(pytest), "-x", "tests/"])
        if result.returncode != 0:
            print(f"substrate-independence: FAIL — kernel tests require kanon-reference", file=sys.stderr)
            sys.exit(1)
    print("substrate-independence: OK")

if __name__ == "__main__":
    main()
```

This gate is what proves ADR-0040's central claim. Phase A authors it as part of the substrate/reference split work; on first run, it will likely fail (revealing today's hidden dependencies). Phase A's iteration loop is "make this gate green, ship the split."

### What the kernel's tests need from `kanon-reference` today

Audit reveals (Phase A will confirm):

- `test_e2e_lifecycle.py`: scaffolds `kanon-sdd` and other aspects to test full lifecycles.
- `test_kit_integrity.py`: byte-equality checks against `src/kanon/kit/aspects/`.
- `test_cli_*.py`: many tests assume default aspects are available.
- `test_fidelity.py`: uses the `kanon-fidelity` capability.

Each will need refactoring to either (a) use a synthetic test-overlay publisher injected via the registry's source-3 overlay mechanism, or (b) move into `kanon-reference`'s own test suite.

## `_kit_root()` retirement walkthrough

Today's call sites of `_kit_root()` (audit on current main):

| File | Line | What it does | Replacement under ADR-0040 |
|---|---|---|---|
| `_manifest.py:127` | The function definition itself | Returns `kanon.__file__/.parent/kit` | Delete entirely |
| `_manifest.py:202` | Inside `_load_top_manifest`: `(_kit_root() / "manifest.yaml")` | Reads kit-global manifest | Delete; the "top manifest" (`defaults:`, kit-global `files:`) is retired per ADR-0048 |
| `_manifest.py:388` | Inside `_aspect_path` for kit aspects | Joins kit root + aspect path | Replace: `registry.get(aspect).publisher_path / aspect_relative_path` |
| `_manifest.py:402` | Same | Same | Same |
| `_manifest.py:565` | Inside `_aspect_path` fallback | Same | Same |
| `_scaffold.py:28` | At module import time, computes paths | Reads kit-shipped templates | Replace: per-publisher path lookup via registry |
| `_scaffold.py:245` | Inside `_build_bundle` for kit-global files | Reads `.kanon/kit.md` from kit root | Delete; kit-global `files:` field retired |
| `_scaffold.py:388` | Inside agents-md assembly | Reads kit-shipped template | Replace: per-publisher path |
| `_scaffold.py:416` | Same | Same | Same |
| `_scaffold.py:443` | Same | Same | Same |
| `_scaffold.py:527` | Same | Same | Same |

Phase A walks each call site explicitly. The pattern is consistent: every `_kit_root() / X` becomes a registry lookup keyed on the publisher whose aspect owns `X`.

## CLI verbs touched (Phase A scope)

- `kanon aspect list` — Phase A: enumerate the registry's aspects with their publisher attribution.
- `kanon aspect info <aspect>` — Phase A: include `publisher:` field in the output (which package shipped this aspect).
- `kanon init` — Phase A: scaffold no aspects by default (per ADR-0048's de-opinionation); rely on recipes (ADR-0043) for opt-in starter sets.
- `kanon verify` — Phase A: registry-keyed walk of enabled aspects.

## Phase A implementation footprint

| Surface | LOC delta | What |
|---|---:|---|
| `_manifest.py` | ~+120 / -50 | Add registry composition; delete `_kit_root()`; replace call sites |
| `_scaffold.py` | ~+40 / -30 | Replace `_kit_root()` references with registry lookups |
| `_validators.py` (new helper module) | ~+30 | `validate_namespace_ownership()` |
| New `pyproject.toml` for `kanon-reference` | ~+40 | Entry-point declarations for the seven aspects |
| `ci/check_substrate_independence.py` | ~+60 | The CI gate above |
| Test extensions | ~+150 | New `test_aspect_registry.py`; refactor `test_e2e_lifecycle.py` and `test_kit_integrity.py` to use registry overlays |
| Migration of `.kanon/kit.md` ownership | ~+10 | Move to `kanon-sdd` aspect or delete |

Total: ~+450 LOC source / -80 LOC source / +150 LOC tests. Roughly 12 files touched.

## Decisions

- [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md) — kernel/reference runtime interface (this design's parent decision).
- [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (the why).
- [ADR-0028](../decisions/0028-project-aspects.md) — project-aspect namespace grammar; preserved; entry-point discovery composes alongside.
- [ADR-0026](../decisions/0026-aspect-provides-and-generalised-requires.md) — capability registry; resolves identically across all three sources.
