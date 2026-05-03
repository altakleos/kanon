---
status: accepted
date: 2026-05-03
---
# ADR-0054: final layout for the deferred multi-distribution split + "core" vocabulary

## Context

ADR-0048 + ADR-0043 + ADR-0051 ratified the architectural commitment to a three-distribution PyPI split: `kanon-core` (substrate kernel) + `kanon-aspects` (reference aspect bundles) + `kanon-kit` (meta — depends on the other two). ADR-0049 ratified the monorepo layout. ADR-0050 + ADR-0052 navigated specific Hatch + `editables` constraints by deferring directory-level renames. ADR-0053 deferred the actual implementation of the multi-distribution split itself, pending a forcing function (downstream consumer asking for `kanon-core` only, or an upstream `editables` library fix).

A 7-panelist research-and-debate cycle (2026-05-03; transcripts preserved in the session log) produced a near-unanimous synthesis on **two complementary questions**:

1. **What layout should the multi-distribution split take, when it eventually happens?** Five of six non-self second-choice votes converged on the "P1 layout": `packages/<dist>/src/<pkg>/` co-located per distribution, Hatchling kept as the build backend, the `[tool.hatch.build.targets.wheel]` config using `only-include = ["src"]; sources = ["src"]` — the prefix-REMOVE form that the `editables` library accepts (sidestepping the constraint that produced ADR-0050 + ADR-0052 + ADR-0053). uv workspace coordinates the dev loop. **Independent top-level Python packages, NOT a PEP 420 namespace package** (the panel rejected the namespace approach 5–2 after Round 2 conceded the unified `kanon/__init__.py` loss is not worth the architectural cleanliness for a single-team three-distribution project).

2. **Should the split happen now?** Unanimously NO. The lock-stepped release cadence (kanon-core and kanon-aspects ship together, depend on each other across the seam, with zero current third-party publishers) means the multi-distribution split is forward-looking infrastructure rather than current need. The install-surface optionality the split would provide (`pip install kanon-core` for the lean kernel without aspects) can be delivered today via `[project.optional-dependencies]` extras on the kanon-kit monolith.

This ADR codifies the answer to question (1) — the **final-state layout** — and aligns project vocabulary on "core" prospectively, replacing "kernel" in non-immutable surfaces. The actual implementation (moving toward the final layout while NOT yet publishing the split) is a separate plan.

## Decision

### 1. Final-state layout (when the split happens)

```
kanon/                                      # repo root, uv workspace coordinator
  pyproject.toml                             # [tool.uv.workspace] only; no [project]
  uv.lock
  packages/
    kanon-core/
      pyproject.toml                         # name = "kanon-core"
      src/kanon_core/                        # the substrate Python package
        __init__.py
        cli.py
        ...
    kanon-aspects/
      pyproject.toml                         # name = "kanon-aspects"
      src/kanon_aspects/                     # the reference aspect bundles
        __init__.py
        aspects/
          kanon_<slug>/                      # 7 aspect bundles
            loader.py
            manifest.yaml
            protocols/
            files/
    kanon-kit/
      pyproject.toml                         # name = "kanon-kit" — meta
                                             # dependencies = ["kanon-core==X.Y.Z", "kanon-aspects==X.Y.Z"]
```

### 2. Hatchling build configuration (per per-package pyproject)

Each per-package pyproject uses the prefix-REMOVE `sources` form, which `editables` accepts (the form `pypa/hatch` itself uses for its own monorepo):

```toml
[tool.hatch.build.targets.wheel]
only-include = ["src"]
sources = ["src"]
```

This means a wheel built from `packages/kanon-core/` produces the package `kanon_core/...` (sources stripped of the `src/` prefix), and `pip install -e packages/kanon-core` succeeds for the dev loop. No path-add rewrite; no `editables` constraint hit.

### 3. Python module names

| Distribution | Python module name | Source-tree path |
|---|---|---|
| `kanon-core` | `kanon_core` | `packages/kanon-core/src/kanon_core/` |
| `kanon-aspects` | `kanon_aspects` | `packages/kanon-aspects/src/kanon_aspects/` |
| `kanon-kit` | (no source — meta-package) | `packages/kanon-kit/` |

PEP 503 normalisation: distribution name `kanon-core` ↔ Python module `kanon_core`. Same for `kanon-aspects`.

The current substrate Python package `kernel` becomes `kanon_core`. This **supersedes ADR-0050 Option A** in part: ADR-0050 chose `kernel` as a distinct top-level Python module name to avoid the Hatch+editables constraint when the source-dir was at `kernel/`; now that the per-distribution layout puts the source under `packages/kanon-core/src/`, the canonical PEP-503-normalised name `kanon_core` works cleanly with the prefix-REMOVE form.

### 4. Vocabulary: "core", not "kernel"

The substrate kernel concept is henceforth referred to as **"core"** in all prospective documentation, ADRs, plans, and code surfaces. "Kernel" remains in immutable historical surfaces (prior ADRs, prior CHANGELOG entries, archived plans, git history) and is not retroactively rewritten. This vocabulary alignment matches:

- The PyPI distribution name `kanon-core` (per ADR-0051).
- The Python module name `kanon_core` (per §3 above).
- The `packages/kanon-core/` source-tree directory.

The word "kernel" is allowed in informal prose where it conveys the architectural role (e.g., "the substrate kernel is responsible for…"), but the canonical noun for the artifact is "core".

### 5. Independent top-level packages, NOT PEP 420 namespace

`kanon_core` and `kanon_aspects` are **independent top-level Python packages**, not subpackages of a shared `kanon` namespace. The panel rejected the PEP 420 namespace approach because:

- Modern (post-2022) Python projects with core+plugins architectures (langchain, Airflow, Prefect, OpenTelemetry) all chose independent top-level distributions; PEP 420 namespace splits are the legacy pattern for ecosystem-wide brand-prefix hierarchies (`google.cloud.*`, `azure.*`).
- A stray `__init__.py` anywhere on `sys.path` silently shadows a PEP 420 namespace, producing a class of catastrophic import failures that pre-commit lints can mitigate but not eliminate.
- The unified `kanon/__init__.py` loss (no `kanon.__version__`, no central API re-export surface, every public symbol addressed via leaf subpackage) is not worth the architectural cleanliness for a single-team, three-distribution, lock-stepped project.

Each distribution's wheel ships ONE top-level Python package: `kanon-core` ships `kanon_core/`; `kanon-aspects` ships `kanon_aspects/`; `kanon-kit` ships nothing (meta-package only).

### 6. Release cadence (today and forward)

`kanon-core`, `kanon-aspects`, and `kanon-kit` are released **lock-stepped** today and for the foreseeable future. Same version triple, cut together, tested together, published together. Per-distribution independent versioning is a forward-looking option preserved by the layout, not exercised at the present cadence. ADR-0043's distinction between kernel-daily / reference-weekly / dialect-quarterly cadence is preserved as the **eventual target**, but the de-facto cadence today is "all three together at every release tag".

Once the multi-distribution split actually publishes (per ADR-0053's forcing-function gate), the lock-stepped cadence may stay or evolve. This ADR does not pre-commit either way.

### 7. Move toward the final layout NOW, without publishing the split

The kanon repo will reorganize its source tree to match §1's final-state layout, **but the kanon-kit distribution remains the only PyPI ship target** until ADR-0053's forcing function fires. Specifically:

- Source directories move: `kernel/` → `packages/kanon-core/src/kanon_core/`; `src/kanon_reference/aspects/kanon_<slug>/` → `packages/kanon-aspects/src/kanon_aspects/aspects/kanon_<slug>/`.
- Per-package `pyproject.toml` files exist at `packages/kanon-core/pyproject.toml` and `packages/kanon-aspects/pyproject.toml` and `packages/kanon-kit/pyproject.toml`. **Each is independently buildable** via `python -m build` from its own directory — the wheels are correct, complete, and would publish cleanly if released. They are simply not released.
- Root `pyproject.toml` becomes the uv workspace coordinator (`[tool.uv.workspace] members = ["packages/*"]`) AND the publisher of the kanon-kit monolith via dependencies on the local workspace members. Concretely: root `pyproject.toml` carries `[project] name = "kanon-kit"` with `[project.dependencies] = ["kanon-core", "kanon-aspects"]` resolved from local paths via `[tool.uv.sources]` for the dev loop and via `[tool.hatch.build.targets.wheel].force-include` for the published wheel — collecting both source trees into a single `kanon_kit-X.Y.Z-py3-none-any.whl`.
- Python imports update wholesale: `from kernel.X import Y` → `from kanon_core.X import Y`; `from kanon_reference.aspects.kanon_<slug>.loader import Y` → `from kanon_aspects.aspects.kanon_<slug>.loader import Y`.
- Entry-points group `kanon.aspects` (per ADR-0040) is **preserved unchanged**; the dotted-path values inside the entry-points update to reflect the new module names.
- Validator allow-list (`kernel/_manifest.py:238` → `kanon_core/_manifest.py:238`) updates: `("kanon-aspects", "kanon-kit")` stays — these are distribution names, not module names; both are still acceptable.

The final-layout-without-split-publish path lets the project: (a) prove the layout works end-to-end via the same wheel build + dev-loop install paths as the eventual real split; (b) lock in the "core" vocabulary; (c) eliminate the awkward depth asymmetry that ADR-0052 documented (kernel/ at depth 1, src/kanon_reference/ at depth 3); (d) leave the actual three-distribution PyPI publishing as a one-PR change when the forcing function fires (just enable the publishing pipeline; the wheels are already build-correct).

## Alternatives Considered

1. **Stay with the current layout (kernel/ + src/kanon_reference/) and only adopt extras on kanon-kit.** Rejected. The user explicitly asked to "get as close as we can to the final layout"; merely adding extras leaves the asymmetric depth problem (ADR-0052) and the misaligned vocabulary ("kernel" vs the planned "kanon-core") in place. The cost of moving toward the final layout now (a substantial refactor) is justified by the future-proof discoverability and the elimination of architectural debt.

2. **Adopt PEP 420 namespace package (`kanon.core` + `kanon.aspects`).** Rejected per panel decision and §5 above. The unified `kanon/__init__.py` loss + namespace-shadowing footgun outweigh the import-surface cleanliness for a single-team three-distribution project.

3. **Adopt P5's bare-top-level layout (`kanon-core/`, `kanon-aspects/`, `kanon-kit/` at repo root, no `packages/` parent dir).** Rejected per panel Round 2 concession that the `packages/` parent dir is the safer default for an unknown future distribution count, and matches what most surveyed real-world projects (langchain libs/, Airflow providers/, Prefect src/integrations/) do.

4. **Switch backend to PDM-backend per P3's Round 1 proposal.** Rejected per P3's own Round 2 concession: P1's discovery that Hatchling's prefix-REMOVE `sources = ["src"]` form satisfies `editables` cleanly removes the constraint that originally motivated the backend swap.

5. **Publish the three-distribution split now.** Rejected per ADR-0053 + panel unanimity in Round 2: lock-stepped release cadence + zero current third-party consumers means the split is ceremony for a problem we don't have. Defer until forcing function.

## Consequences

### Documentation

- ADR-0050 is superseded in part. ADR-0050 Option A's choice of Python module `kernel` (a distinct top-level name to avoid the Hatch+editables constraint) is replaced by `kanon_core` under the new per-distribution layout. ADR-0050's body is preserved per ADR-immutability; the supersession is recorded here. Allow-ADR-edit trailer required if ADR-0050's body needs prospective updates.
- ADR-0049 §1(2) (kernel-flatten) and §1(7) (aspects-flatten) are superseded in part by §1 of this ADR. ADR-0049's body is preserved; the new layout is canonical.
- ADR-0052 (aspects-flatten Option C: defer indefinitely) is **revisited and partially reversed by this ADR**: aspects DO move to a new top-level location (`packages/kanon-aspects/src/kanon_aspects/`), just not to a bare top-level `aspects/` directory. The panel's Round 2 finding that the prefix-REMOVE form solves the Hatch+editables constraint that Option A of ADR-0052 rejected means the rejection rationale was based on incomplete information. Allow-ADR-edit trailer required to amend ADR-0052's status to `superseded; superseded-by: 0054`.
- ADR-0053 (Phase A implementation deferral) **stands**: this ADR specifies the layout for IF/WHEN the split happens; ADR-0053's deferral of the actual publish remains in force.
- All prospective documentation uses "core" instead of "kernel". Historical ADRs, archived plans, and CHANGELOG entries are NOT retroactively rewritten (immutability + historical accuracy).

### Code

- A separate plan (`plan-toward-final-layout`) executes §7 above. The plan is non-trivial (likely a multi-PR cycle of source moves + import sweeps + validator updates + fidelity recapture, comparable in scope to the ADR-0050 Option A execution).
- Each per-package pyproject is buildable independently via `python -m build` from its directory and produces a correct wheel that WOULD publish to PyPI cleanly. Publication is gated by ADR-0053.
- The root pyproject becomes a hybrid: uv workspace coordinator + kanon-kit publisher. This is a structural duplication that ADR-0053 §Alternatives rejected as a primary path BUT becomes acceptable here because (a) the duplication is intentional and time-bound to the not-yet-publishing phase, (b) the kanon-kit hybrid form is what eventually executes when the split publishes (a true meta-package depending on the workspace members), and (c) the duplication is cleanly documented as transitional in the root pyproject's comments.

### Migration

- **Zero PyPI migration.** The kanon-kit distribution name and shipping cadence are unchanged. Consumers `pip install kanon-kit` exactly as today.
- The Python module rename (`kernel` → `kanon_core`; `kanon_reference` → `kanon_aspects`) is internal to the kanon repo's own code + tests + docs. Per ADR-0048 §Migration there are no current external consumers; the rename has no downstream coordination cost.

### Forcing function (when ADR-0053 reverses)

When ADR-0053's forcing function fires (downstream consumer arrives, or `pfmoore/editables#20` resolves upstream, or panel re-review flips the cost calculus), the multi-distribution publish becomes a small change: enable `release.yml` to build + publish all three wheels (each pyproject is already build-correct), reserve the `kanon-core` and `kanon-aspects` PyPI names, cut the first three-package release. No layout change required at that point.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — substrate-shape commitment; in force.
- [ADR-0049](0049-monorepo-layout.md) — monorepo layout; §1(2) + §1(7) superseded in part by this ADR.
- [ADR-0050](0050-kernel-flatten-deferral.md) — kernel-flatten Option A; superseded in part by §3 of this ADR.
- [ADR-0051](0051-distribution-naming.md) — distribution naming; preserved verbatim.
- [ADR-0052](0052-aspects-flatten.md) — aspects-flatten Option C; **superseded** by this ADR (the prefix-REMOVE Hatch idiom solves the constraint Option A was rejected for).
- [ADR-0053](0053-phase-a-implementation-deferral.md) — Phase A implementation deferral; **preserved** — this ADR specifies the IF/WHEN layout, not the WHEN.
- 7-panelist synthesis (2026-05-03 session log): Round 1 + Round 2 transcripts. Convergent vote: 5 of 6 non-self second-choice votes for P1's layout.
- [`pypa/hatch`](https://github.com/pypa/hatch) — the canonical example of a Hatchling-built monorepo shipping multiple distributions; this ADR's §1 layout mirrors it.
- [`pfmoore/editables#20`](https://github.com/pfmoore/editables/issues/20) — the upstream constraint that the prefix-REMOVE Hatch idiom sidesteps.
