---
status: approved
slug: phase-a.2.2-substrate-discovery
notes: "Decision points: (1) approved — LOADER shape extension; (2) substrate-independence gate rolled into A.3 (not a separate A.2.3); (3) approved — partial _kit_root() retirement now, full retirement in A.3."
date: 2026-05-02
design: docs/design/kernel-reference-interface.md
---

# Plan: Phase A.2.2 — substrate-side entry-point discovery (`_load_aspect_registry`)

## Context

Phase A.2.1 (PR #63) authored the `kanon_reference` Python package with seven LOADER `MANIFEST` stubs. The entry-points block in `packaging/reference/pyproject.toml` is active. **But the substrate's runtime doesn't yet read them.** `_load_top_manifest()` still walks `_kit_root() / manifest.yaml`; `_aspect_path()` still walks `_kit_root() / <aspect-relative-path>`.

Phase A.2.2 wires the substrate to discover aspects via `importlib.metadata.entry_points(group="kanon.aspects")` per ADR-0040 / [`docs/design/kernel-reference-interface.md`](../design/kernel-reference-interface.md).

### Important shape gap discovered during planning

The design says the LOADER MANIFEST "has the same shape as today's `src/kanon/kit/aspects/<aspect>/manifest.yaml`" — and Phase A.2.1 implemented this literally, mirroring the **sub-manifest** shape (`files:`, `depth-N: {...}`, `byte-equality:`, `config-schema:`).

But the substrate's `_load_top_manifest()` returns a registry whose per-aspect entries carry **top-manifest fields**: `path`, `stability`, `depth-range`, `default-depth`, `description`, `requires`, `provides`. These currently come from `src/kanon/kit/manifest.yaml`'s `aspects.<X>:` blocks — NOT from the sub-manifests.

For substrate-side discovery to work end-to-end, the registry must surface **both** sets of fields per aspect. The cleanest fix: extend each LOADER MANIFEST to include both registry-level fields (from the top manifest) AND content-level fields (from the sub-manifest). The `path:` field is dropped (publisher_path replaces it at runtime). The equivalence test updates to verify the union shape.

## Goal

Single PR that:

1. Wires substrate-side discovery via entry-points (`_load_aspect_registry`).
2. Extends LOADER MANIFESTs to carry both registry + content fields.
3. Replaces the two `_kit_root()` call sites in `_aspect_path()` with registry lookups.
4. Authors namespace-ownership validator.
5. Keeps the existing kit YAML at `src/kanon/kit/manifest.yaml` as the load source for `defaults:` + `files:` (kit-globals retired by A.3, not A.2.2).

**Substrate-independence CI gate is OUT OF SCOPE for A.2.2** — see "Decision points" below.

## Scope

### In scope

#### A. Extend LOADER MANIFESTs with registry fields

Each `src/kanon_reference/aspects/kanon_<X>.py` MANIFEST gains the six registry fields from `src/kanon/kit/manifest.yaml`'s `aspects.<X>:`:

```python
MANIFEST: dict[str, Any] = {
    # Registry fields (added by A.2.2; previously lived in kit/manifest.yaml).
    "stability": "stable",
    "depth-range": [0, 3],
    "default-depth": 1,
    "description": "Spec-Driven Development: plans, specs, design docs",
    "requires": [],
    "provides": ["planning-discipline", "spec-discipline"],
    # Content fields (from A.2.1, byte-mirroring the sub-manifest).
    "files": [],
    "depth-0": {...},
    ...
}
```

The `path:` field is NOT included — publisher_path resolution at runtime replaces it.

#### B. Update `tests/test_kanon_reference_manifests.py`

Equivalence assertion changes from `MANIFEST == sub_manifest_yaml` to:

```python
expected = {**top_manifest_entry, **sub_manifest_yaml}
expected.pop("path", None)  # path dropped per A.2.2
assert MANIFEST == expected
```

#### C. Top-level `pyproject.toml`

Add `[project.entry-points."kanon.aspects"]` mirroring `packaging/reference/pyproject.toml`. After `uv sync`, `importlib.metadata.entry_points(group="kanon.aspects")` returns the seven aspects from the kanon-kit installed distribution. **This is the only top-level pyproject change** — wheel layout, scripts, and dependencies are unchanged.

#### D. New: `_load_aspect_registry(target)` in `_manifest.py`

```python
def _load_aspect_registry(target: Path | None = None) -> dict[str, Any]:
    """Load the unified aspect registry from entry-points + project-aspects + overlays.

    Returns the same shape as today's _load_top_manifest()['aspects'] — but
    sourced from importlib.metadata.entry_points(group="kanon.aspects") rather
    than the kit YAML.
    """
    registry: dict[str, dict[str, Any]] = {}
    for ep in importlib.metadata.entry_points(group="kanon.aspects"):
        _validate_namespace_ownership(ep.name, ep.dist)
        manifest = ep.load()  # the MANIFEST dict
        if not isinstance(manifest, dict):
            raise click.ClickException(
                f"entry-point {ep.name}: MANIFEST must be a dict (got {type(manifest).__name__})"
            )
        # Stamp publisher_path so callers can resolve aspect-relative paths.
        publisher_path = Path(ep.dist.locate_file("")) if ep.dist else None
        entry = dict(manifest)
        entry["_publisher_path"] = str(publisher_path) if publisher_path else None
        entry["_source"] = "entry-point"
        if ep.name in registry:
            raise click.ClickException(f"duplicate aspect {ep.name!r} from multiple sources")
        registry[ep.name] = entry
    # Source 2: project-aspects (preserved per ADR-0028).
    if target is not None:
        for slug, entry in _discover_project_aspects(target).items():
            if slug in registry:
                raise click.ClickException(f"duplicate aspect {slug!r}")
            entry["_source"] = "project-aspect"
            registry[slug] = entry
    # Source 3: test overlay.
    overlay = os.environ.get("KANON_TEST_OVERLAY_PATH")
    if overlay:
        for slug, entry in _load_overlay(overlay).items():
            entry["_source"] = "test-overlay"
            registry[slug] = entry
    return registry
```

#### E. New helper: `_validate_namespace_ownership(slug, dist)`

Per ADR-0040 §5: an entry-point may only register aspect slugs in its distribution's namespace. Rules:

- `kanon-*` slugs require dist name `kanon-reference` OR `kanon-kit` (transitional, while top-level pyproject is `kanon-kit`).
- `project-*` slugs are forbidden via entry-points (must come from `<target>/.kanon/aspects/`).
- `acme-*` slugs are allowed; loose validation (warning, not error) until ADR-0028's `acme-` grammar is fully ratified.
- Unknown namespaces → warning.

Lives in `_manifest.py` near `_load_aspect_registry`.

#### F. Rewire `_load_top_manifest()`

`_load_top_manifest()` keeps reading `_kit_root() / manifest.yaml` for kit-globals (`defaults:`, `files:`), but its `aspects:` field is now sourced from `_load_aspect_registry()` rather than the YAML.

```python
@lru_cache(maxsize=1)
def _load_top_manifest() -> dict[str, Any]:
    path = _kit_root() / "manifest.yaml"
    yaml_data = _load_yaml(path) if path.is_file() else {}
    # Aspects come from entry-points, not the YAML.
    yaml_data["aspects"] = _load_aspect_registry()
    return yaml_data
```

The kit YAML's `aspects:` block is now dead in the substrate's eyes (A.3 deletes it).

#### G. Replace `_kit_root()` call sites in `_manifest.py:402, 565`

These are inside `_aspect_path()` for kit aspects. Today: `_kit_root() / entry["path"]`. After A.2.2: use `entry["_publisher_path"]` if set, else fall back to `_kit_root() / entry["path"]` (project-aspects keep `_source` from `_discover_project_aspects`, which is already absolute).

`_kit_root()` itself remains (`_scaffold.py` still uses it; A.3 retires those).

#### H. CHANGELOG entry under `[Unreleased] § Added`.

#### I. New tests

- `tests/test_aspect_registry.py` — direct tests of `_load_aspect_registry()`: returns the seven canonical aspects; each has registry + content fields; namespace-ownership validator rejects illegal entries; project-aspect overlay composes correctly.
- `tests/test_kanon_reference_manifests.py` updates per (B).

### Out of scope

- **`ci/check_substrate_independence.py` gate** — see "Decision points" below.
- **`_kit_root()` call sites in `_scaffold.py`** (lines 28, 181, 245, 416, 443) — A.3 territory; they read aspect-data files (templates, agents-md fragments) that still live at `src/kanon/kit/aspects/<X>/`. Retiring them requires the content move.
- **Deleting `src/kanon/kit/manifest.yaml`'s `aspects:` block** — A.3 territory.
- **Deleting `defaults:` / `files:` from kit YAML** — A.3 territory.
- **Aspect content move from `src/kanon/kit/aspects/` to `src/kanon_reference/aspects/`** — A.3 territory.
- **No new ADR / spec / design / principle changes.**

## Decision points

### Why defer `ci/check_substrate_independence.py` to a separate sub-plan

Per ADR-0040 §6, the gate asserts the substrate's test suite passes with `kanon_reference` uninstalled. Today this gate would fail catastrophically:

- 800+ tests assume `kanon_reference`'s aspects are available
- `_scaffold.py` reads template files from `src/kanon/kit/aspects/<X>/` — substrate-internal but `kanon-`-namespaced
- `test_kit_integrity.py`, `test_e2e_lifecycle.py`, etc. all depend on the seven reference aspects being discoverable

Making the gate green requires (a) a `kanon_substrate_dev` test marker that excludes reference-dependent tests, OR (b) a synthetic test-overlay publisher injected via `KANON_TEST_OVERLAY_PATH`. Both are substantial. Per ADR-0044, the gate is normative — but ADR-0045 ratified the canonical 9-step sequence as a *sequence*; staging A.2.2's discovery rewrite separately from the gate-greening work is consistent with the spirit.

**Recommendation:** ship A.2.2 as the discovery rewrite; ship a successor sub-plan (A.2.3?) that ships the gate green by adding the test-overlay publisher mechanism and refactoring kernel-only tests. Alternative: roll the gate into A.3 (which moves content; would naturally green the gate by then).

### Risk: breaking `_load_top_manifest()`'s caller assumptions

`_load_top_manifest()` is called from many places. Today's callers expect `top["aspects"][name]` to have `path:`, `stability:`, etc. After A.2.2, `aspects:` is sourced from entry-points; entries have `_publisher_path` instead of `path`. Callers that read `entry["path"]` will need adjustment.

Audit during implementation; the failure mode is loud (KeyError); not silent breakage.

## Acceptance criteria

### LOADER extensions

- [ ] AC-L1: Each of the seven `src/kanon_reference/aspects/kanon_<X>.py` MANIFESTs contains the six registry fields (`stability`, `depth-range`, `default-depth`, `description`, `requires`, `provides`).
- [ ] AC-L2: No MANIFEST contains a `path:` field.
- [ ] AC-L3: `tests/test_kanon_reference_manifests.py` equivalence test updated; passes.

### Top-level pyproject

- [ ] AC-Y1: `pyproject.toml` gains `[project.entry-points."kanon.aspects"]` with the seven canonical entries targeting `kanon_reference.aspects.kanon_<id>:MANIFEST`.
- [ ] AC-Y2: `uv sync` regenerates `kanon-kit` install metadata; `importlib.metadata.entry_points(group="kanon.aspects")` returns the seven aspects.

### Substrate

- [ ] AC-S1: `_load_aspect_registry(target)` exists in `_manifest.py`, reads entry-points + project-aspects + test overlays.
- [ ] AC-S2: `_validate_namespace_ownership(slug, dist)` exists; rejects `project-*` from entry-points; warns on unknown namespace.
- [ ] AC-S3: `_load_top_manifest()` sources `aspects:` from `_load_aspect_registry()`; `defaults:` and `files:` continue from the kit YAML.
- [ ] AC-S4: `_aspect_path()` uses `_publisher_path` for entry-point aspects; falls back to `_kit_root()` only when neither `_publisher_path` nor `_source` is set.
- [ ] AC-S5: `_kit_root()` survives (used by `_scaffold.py`).

### Tests

- [ ] AC-T1: New `tests/test_aspect_registry.py` covers (a) registry returns seven aspects, (b) each has registry + content fields, (c) namespace-ownership rejects `project-*` from entry-points, (d) project-aspect overlay composes.
- [ ] AC-T2: Full pytest suite — 0 failures (was 843; new test count varies with `_aspect_path` test additions).

### Cross-cutting

- [ ] AC-X1: `CHANGELOG.md` `[Unreleased] § Added` gains a paragraph naming Phase A.2.2.
- [ ] AC-X2: `kanon verify .` returns `status: ok`, zero warnings.
- [ ] AC-X3: `python ci/check_links.py` passes.
- [ ] AC-X4: `python ci/check_foundations.py` passes.
- [ ] AC-X5: `python ci/check_kit_consistency.py` passes (or: noted change with explicit allowlist if the kit YAML's `aspects:` is no longer the registry).
- [ ] AC-X6: `python ci/check_invariant_ids.py` passes.
- [ ] AC-X7: `python ci/check_packaging_split.py` passes.

## Risks / concerns

- **Risk: `_load_top_manifest()`'s callers break on missing `path:`.** Mitigation: audit during implementation; provide a transitional fallback `entry["path"]` derived from the slug if absent.
- **Risk: `check_kit_consistency.py` fails because the kit YAML's `aspects:` block no longer matches the registry.** Mitigation: gate is gate-author-side; if it fires, narrow it to skip the `aspects:` field comparison (the registry is now the source of truth). Or it may keep working since `aspects:` block remains in the kit YAML even if unused by the substrate.
- **Risk: cache invalidation.** `_load_top_manifest()` is `@lru_cache`d; entry-points discovery may change between processes if `pip install` runs mid-test. Likely fine for tests but worth noting.
- **Risk: editable install vs. wheel install behaviour drift.** `importlib.metadata.entry_points` behaviour with editable installs needs checking. Most modern setups (hatch + uv) handle this correctly; verify locally.
- **Risk: PR scope creep.** A.2.2 already touches LOADER MANIFESTs, top pyproject, _manifest.py, equivalence test, new registry test. Adding the substrate-independence gate would push it from "substantial" to "huge". Scope guard: stop at the discovery rewrite; defer gate to a follow-up.

## Documentation impact

- **New files:** `docs/plans/phase-a.2.2-substrate-discovery.md`, `tests/test_aspect_registry.py`.
- **Touched files:** `pyproject.toml` (entry-points block), `src/kanon/_manifest.py` (`_load_aspect_registry`, namespace validator, `_load_top_manifest` rewire, `_aspect_path` registry lookup), seven `src/kanon_reference/aspects/kanon_*.py` (registry fields added), `tests/test_kanon_reference_manifests.py` (equivalence shape change), `CHANGELOG.md`.
- **No changes to:** `src/kanon/_scaffold.py` (5 `_kit_root()` call sites preserved for A.3), `src/kanon/kit/manifest.yaml` (still authoritative for `defaults:` + `files:`; `aspects:` block dead but preserved), `src/kanon/kit/aspects/<X>/manifest.yaml` (kept until A.3), specs, designs, ADRs, foundations, protocol prose.
