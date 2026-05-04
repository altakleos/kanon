---
status: draft
date: 2026-05-04
---
# ADR-0055: Manifest unification — YAML as single source of truth

## Context

Every reference aspect currently has **three** representations of its metadata:

1. **`kit/manifest.yaml`** — top-level registry fields (stability, depth-range,
   default-depth, description, requires, provides, suggests) for all seven
   aspects in one file.
2. **Per-aspect `manifest.yaml`** — content fields (kanon-dialect, files,
   depth-N blocks with protocols/sections/validators).
3. **Per-aspect `loader.py`** — a Python dict that is the union of #1 and #2,
   registered as an `importlib.metadata` entry-point.

The `loader.py` files were introduced in Phase A.2.1 as "short-lived stubs" but
have persisted through Phase A.3 and beyond. A CI test
(`test_kanon_reference_manifests.py`) guards against drift between `loader.py`
and `manifest.yaml`, but the duality creates maintenance burden and has already
caused bugs (e.g., `sections: null` vs `[]`).

Publisher symmetry — a core substrate principle — requires all three publisher
types (`kanon-*`, `project-*`, `acme-*`) to have identical authoring
experiences. Project-aspect authors write only `manifest.yaml`. Kit and
third-party publishers currently must also maintain `loader.py`, breaking that
symmetry.

When `kanon-core` and `kanon-aspects` become separate PyPI packages (deferred
by ADR-0053), core cannot read YAML files from aspects via filesystem paths —
entry-points are the only cross-package discovery mechanism. The unification
must therefore preserve the entry-point contract while eliminating semantic
duplication.

## Decision

**YAML is the single source of truth for all aspect metadata.**

Each aspect's `manifest.yaml` is expanded to include the registry fields
(stability, depth-range, default-depth, description, requires, provides,
suggests) currently housed in `kit/manifest.yaml`. Each `loader.py` is replaced
with a three-line trampoline that reads its sibling `manifest.yaml` via
`importlib.resources`:

```python
from importlib.resources import files
import yaml
MANIFEST = yaml.safe_load(
    files(__package__).joinpath("manifest.yaml").read_text("utf-8")
)
```

The entry-point contract (`loader:MANIFEST` returns a dict) is preserved
unchanged. `_load_aspect_manifest()` in core is simplified to consume the
entry-point dict directly for kit aspects, eliminating the separate
YAML-from-disk read path. The `kit/manifest.yaml` aspects block is reduced to
only fields that are genuinely kit-level (not per-aspect).

## Alternatives Considered

1. **Delete YAML, make Python dicts canonical** (the original Phase A.3 plan).
   Rejected: breaks publisher symmetry, raises the barrier for non-Python
   publishers, and makes manifests harder to read, edit, and lint.

2. **Generate `loader.py` from YAML at build time.** Rejected: adds build-step
   complexity, complicates editable installs, and is strictly worse than runtime
   loading via `importlib.resources`.

3. **Keep both files with drift test** (status quo). Rejected: triple
   representation is architecturally unsound, has already caused bugs, and
   maintenance burden scales linearly with aspect count.

4. **Eliminate `loader.py` entirely; have core discover YAML via
   `importlib.resources` directly.** Rejected: entry-points must resolve to a
   Python object; the trampoline is the minimal bridge between YAML-as-source
   and entry-point-as-contract.

## Consequences

- **Positive.** Single source of truth per aspect. Zero semantic duplication.
  Publisher symmetry restored — all three namespaces author only
  `manifest.yaml`. The drift test becomes unnecessary.

- **Positive.** `importlib.resources` works across package boundaries (installed
  wheels, editable installs, zip imports), future-proofing the design for the
  distribution split deferred by ADR-0053.

- **Negative.** `pyyaml` becomes a runtime import-time dependency of
  `kanon-aspects`. It is already a transitive dependency via `kanon-core`, but
  should be declared explicitly in `kanon-aspects`' dependency list to make the
  coupling visible.

- **Negative.** ~2 ms per-aspect YAML parse at import time (~14 ms total for
  seven aspects). Negligible for a CLI tool, and `_load_aspect_manifest` is
  `@cache`-decorated so the cost is paid once per process.

## References

- [ADR-0040: Kernel/reference runtime interface](0040-kernel-reference-runtime-interface.md)
- [ADR-0053: Phase A implementation deferral](0053-phase-a-implementation-deferral.md)
- [ADR-0054: Final layout and core vocabulary](0054-final-layout-and-core-vocabulary.md)
- [Design doc: Manifest unification](../design/manifest-unification.md)
