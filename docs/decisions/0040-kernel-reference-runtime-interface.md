---
status: accepted
date: 2026-05-01
---
# ADR-0040: Kernel/reference runtime interface

## Context

[ADR-0048](0048-kanon-as-protocol-substrate.md) committed `kanon-substrate` (kernel) and `kanon-reference` (the seven `kanon-` aspects) to ship as separate distributions. [ADR-0039](0039-contract-resolution-model.md) ratified the runtime-binding model — but neither addresses the load-bearing question Round-5 panel review surfaced independently across three reviewers (architect, critic, code-reviewer): **how does the kernel discover aspects shipped by a separately-installed reference package?**

Today's kernel hardcodes the assumption "the kit ships exactly one of itself" via [`_kit_root()` at `src/kanon/_manifest.py:127`](../../kernel/_manifest.py), referenced 10+ times across `_manifest.py` and `_scaffold.py`. The function returns `Path(kanon.__file__).parent / "kit"` — the kit-author's source tree. Under the protocol-substrate commitment, that path no longer exists in `kanon-substrate`'s distribution; the kernel must locate aspects by other means.

The discovery mechanism is the public contract on which third-party (`acme-`) publishers will rely. Choosing it commits the substrate to:

1. A *publisher-registration shape* (what does an `acme-` publisher's `pyproject.toml` look like?).
2. A *runtime-discovery algorithm* (how does the kernel find aspects at process startup?).
3. A *publisher-symmetry contract* (no privilege for `kanon-` over `acme-` at any code path; per [`P-publisher-symmetry`](../foundations/principles/P-publisher-symmetry.md)).
4. An *independence invariant* (`kanon-substrate`'s test suite must pass with `kanon-reference` uninstalled).

This ADR ratifies all four. It does not yet specify wheel-packaging mechanics (release cadence, version-pinning across the substrate/reference split) — those land in ADR-0043. ADR-0040 is the *interface*; ADR-0043 will be the *packaging*.

## Decision

**The kernel discovers aspects via Python entry-points group `kanon.aspects`.** Publishers register entries in their package's `pyproject.toml`; the kernel resolves at startup via `importlib.metadata.entry_points(group="kanon.aspects")`. Specifically:

1. **Entry-point group: `kanon.aspects`.** This is the substrate's stable public contract. The name `kanon.aspects` is part of the published protocol commitment under ADR-0048; publishers depend on it; the substrate honours it across dialect supersessions.

2. **Each entry is one aspect.** A publisher's `pyproject.toml` declares one entry per aspect under `[project.entry-points."kanon.aspects"]`. The entry name is the aspect's full namespaced slug (e.g., `kanon-sdd`, `kanon-testing`, `acme-fintech-compliance`). The entry value is a dotted Python module path that resolves to the aspect's manifest provider — a callable returning the aspect manifest dict, or a module exposing a `MANIFEST` variable. (The exact resolver shape is a Phase A detail per the companion design.)

3. **Three-source registry composition.** `_load_aspect_registry(target)` returns the union of:
   - **Entry-point publishers** discovered via `importlib.metadata.entry_points(group="kanon.aspects")` — every published aspect bundle visible to the running Python interpreter, including kit-shipped, reference-shipped, and any `acme-` packages a consumer has installed.
   - **Project-aspects** at `<target>/.kanon/aspects/project-*/manifest.yaml` per [ADR-0028](0028-project-aspects.md) (preserved verbatim; the consumer-side filesystem mechanism survives).
   - **Test overlays** (development-only) when an environment variable signals a fixture overlay; intended for the kernel's own test suite.

4. **Publisher-symmetric resolution.** Source order does not imply privilege. A `kanon-testing` aspect from `kanon-reference` and a hypothetical `acme-strict-testing` resolve through the same code paths: same manifest validation, same depth-range enforcement, same capability registry semantics, same scaffolding pipeline. Asymmetries between namespaces are bugs, not features (per `P-publisher-symmetry`).

5. **Namespace ownership remains source-bounded** (per [ADR-0028](0028-project-aspects.md) Decision §"Namespace ownership is source-bounded"). An entry-point-discovered publisher MAY register `kanon-*` aspects only if its distribution name matches the canonical `kanon-reference` package; it MAY register `acme-<vendor>-*` aspects only if it is the `acme-<vendor>` package. The kernel detects mis-namespaced entry-points (e.g., a third-party shipping under `kanon-`) and refuses to load them with `code: namespace-violation`.

6. **The substrate's test suite passes with `kanon-reference` uninstalled.** This is an independence invariant: `kanon-substrate`'s pytest run, executed in a clean venv with only `kanon-substrate` installed and no entry-point publishers visible, MUST pass green. This proves the kernel does not depend on reference content for its own correctness.

7. **`_kit_root()` is retired.** Phase A deletes `_kit_root()` and every reference. Aspect path lookup goes through the publisher registry: each registry entry carries the publisher's distribution path (resolved at entry-point time), and aspect path = `<publisher_dist_path>/<aspect_relative_path>`. The "the kit ships exactly one of itself" assumption is gone.

8. **Kit-global `files:` field is retired.** The top-level `files:` in `src/kanon/kit/manifest.yaml` (currently `[.kanon/kit.md]`) is a kit-shape privilege. Phase A moves `.kanon/kit.md` to ownership by an aspect (likely `kanon-sdd` or a new `kanon-meta`), or deletes it. The substrate scaffolds nothing on its own behalf.

## Alternatives Considered

1. **Filesystem-walk-only discovery.** The kernel scans `<some-path>/kanon-aspects/` for manifest files. **Rejected.** Re-invents pip's installation discipline; doesn't compose with PyPI; offers no publisher attribution; can't honour Python virtualenv isolation (a consumer with multiple venvs would see global aspect bundles bleeding in).

2. **Environment-variable path overlay.** The kernel reads `$KANON_PUBLISHERS` (colon-separated paths) at startup. **Rejected.** Fragile (env-var setup becomes part of kanon's config surface); doesn't compose with packaged publishers; conflicts with virtualenv hygiene; CI/dev parity hard to achieve.

3. **Namespace-package discovery.** `kanon-substrate` declares a namespace package `kanon_aspects`; publishers ship `kanon_aspects.foo` modules; the kernel discovers via Python's namespace package resolution. **Rejected.** Namespace packages are notoriously fragile (PEP 420 has subtle pitfalls with editable installs and zipped distributions); `importlib.metadata.entry_points` is the modern, well-supported mechanism for the same use case. Pip and other tools use entry-points; reusing the convention is cheaper.

4. **`kanon-substrate` vendoring `kanon-reference`.** Single wheel, single distribution; kernel ships reference aspects internally and exposes them via the registry. **Rejected.** Re-establishes the kit shape under a different name; reference aspects become non-de-installable; `acme-` publishers are second-class; `P-publisher-symmetry` collapses. ADR-0048 explicitly retires this shape.

5. **Hardcoded "the seven `kanon-` aspects" in the kernel.** `kanon-substrate`'s code explicitly lists `kanon-sdd, kanon-testing, kanon-worktrees, …` and looks them up in known paths. **Rejected.** Fastest to ship; absolutely the wrong commitment. Privileges `kanon-` aspects in code paths; cannot accommodate `acme-` substitution; bakes "the seven" assumption into the kernel forever; explicitly contradicts `P-protocol-not-product`.

## Consequences

### Substrate-level

- **`_load_aspect_registry()` is the single source of truth** for which aspects are visible to the kernel. Phase A rewrites it to the three-source union described above. Existing call sites that read directly from `_load_top_manifest()` migrate to the registry interface.
- **`_kit_root()` is deleted in Phase A.** Every call site walked in the companion design doc; replaced by registry-publisher-path lookups.
- **Kit-global `files:` field is deleted from the top manifest.** `.kanon/kit.md` either migrates to an aspect or disappears. Phase A decides the migration target; ADR-0040 ratifies the deletion.
- **Mis-namespaced entry-points fail at load time.** A third-party publisher declaring an aspect named `kanon-fakery` is rejected with a clear error. The kernel does not silently load (or silently skip) ill-formed entries.

### `pyproject.toml` shape (publisher-side)

```toml
[project]
name = "acme-fintech-compliance"
version = "1.0.0"
# ...

[project.entry-points."kanon.aspects"]
acme-fintech-compliance = "acme_fintech_compliance.kanon:MANIFEST"
```

(`kanon-reference` ships its seven aspects analogously, one entry per aspect.) The exact resolver shape — whether the entry-point value points to a callable, a module attribute, or a package — is a Phase A detail; the design doc specifies one option.

### Independence invariant

- **CI gate**: a new check (`ci/check_substrate_independence.py` or analogous) installs `kanon-substrate` in a clean venv with no `kanon-reference` and runs the full pytest suite. Pass = green; fail = the kernel has accidentally taken a hard dependency on reference content. Phase A authors this gate.
- **Today's reality**: the kernel currently *does* depend on reference content via `_kit_root()` (the kit dir contains the seven `kanon-*` aspects). The independence invariant is a *future* commitment; Phase A's first job is to make the kernel pass the gate. Reaching the gate is the deliverable that completes ADR-0040's runtime intent.

### Spec amendments

- **`docs/specs/aspects.md`** gains a "Protocol-substrate composition" section referencing ADR-0040. The existing INVs (aspect-as-primitive, depth-dial, namespace grammar) survive; the section explains how they compose under the entry-point discovery mechanism.
- **`docs/specs/project-aspects.md`** gains a parallel section explaining how project-aspect filesystem discovery (existing) composes with entry-point discovery (new) under the unified `_load_aspect_registry` algorithm.

Both amendments are append-only, no INV body changes.

### Out of scope (deferred to subsequent Phase 0 ADRs)

- **Wheel split mechanics** — the actual `pyproject.toml` for `kanon-substrate` and `kanon-reference`, version-pinning across the split, release cadence: ADR-0043 (distribution + cadence).
- **Realization-shape schema, dialect grammar, composition algebra** (`surface:`, `before/after:`, `replaces:`): ADR-0041.
- **Verification scope-of-exit-zero broader wording**: ADR-0042.
- **Substrate self-conformance** as a top-level spec with INVs: ADR-0044.
- **De-opinionation transition** (the migration commit sequence; `defaults:` removal; `_detect.py` deletion): ADR-0045.

## Config Impact

- **No consumer-side `.kanon/config.yaml` change** caused by this ADR. The schema bump (v3 → v4) ratified by ADR-0041 is orthogonal; ADR-0040's effect is invisible to consumer config.
- **Publisher-side `pyproject.toml` shape** is documented above. New publishers declare entry-points; existing consumer projects do nothing.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment (parent decision).
- [ADR-0028](0028-project-aspects.md) — project-aspect namespace grammar; preserved; entry-point discovery composes alongside.
- [ADR-0026](0026-aspect-provides-and-generalised-requires.md) — capability registry; preserved verbatim; semantics extend across the entry-point-discovered plane.
- [ADR-0039](0039-contract-resolution-model.md) — resolution model; this ADR is the discovery layer that resolution operates over.
- [`docs/design/kernel-reference-interface.md`](../design/kernel-reference-interface.md) — concrete mechanism (entry-point shape, registry composition, independence-invariant CI gate, `_kit_root()` retirement walkthrough).
- [`docs/foundations/principles/P-publisher-symmetry.md`](../foundations/principles/P-publisher-symmetry.md) — the principle this ADR enforces in code paths.
- [`docs/foundations/principles/P-protocol-not-product.md`](../foundations/principles/P-protocol-not-product.md) — the principle that retires kit-global privileges.
