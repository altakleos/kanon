---
status: accepted
date: 2026-05-03
---
# ADR-0053: Phase A implementation deferral pending forcing function

## Context

ADR-0048 committed the kanon project to a protocol-substrate shape. ADR-0043 + ADR-0051 ratified the three-distribution PyPI split: `kanon-core` (substrate kernel) + `kanon-aspects` (reference aspect bundles) + `kanon-kit` (meta-package). ADR-0049 ratified the monorepo layout. ADR-0050 + ADR-0052 navigated two specific Hatch editable-install constraints by deferring directory-level renames.

The Phase A implementation roadmap (per ADR-0045 §Decision and ADR-0049 §Implementation Roadmap) calls for actual per-package pyproject co-location (`kernel/pyproject.toml`, `src/kanon_reference/pyproject.toml`, `kit-meta/pyproject.toml`), root-pyproject conversion to a uv workspace coordinator, release.yml reshape to publish three wheels, and PyPI registration of the two new distributions. ADR-0049 PR B (PR #89) shipped only the **delete-half** of "kill packaging/"; the **co-location half** never landed.

Today (2026-05-03), an experimental attempt to author `kernel/pyproject.toml` confirmed the same Hatch + `editables`-library constraint that produced ADR-0050 also blocks per-package pyprojects when each pyproject lives **inside** its package directory:

```
kernel/pyproject.toml
[tool.hatch.build.targets.wheel]
sources = {"" = "kernel"}
```

Wheel build via `python -m build --wheel .` succeeds. The PEP 660 editable install via `pip install -e .` fails with the exact ADR-0050 error: *"Dev mode installations are unsupported when any path rewrite in the `sources` option changes a prefix rather than removes it."* The constraint is structural — `editables` only supports prefix STRIP, not prefix RENAME or prefix ADD — and there is no Hatch primitive that says "the package IS the current directory" cleanly enough to satisfy `editables`.

Three forward-options were considered:

1. **Move source one level deeper** (e.g., `kernel/kernel/__init__.py`). Standard Hatch layout; satisfies `editables`. **Rejected**: this is exactly the source-tree restructure ADR-0050 spent 12 hours of autopilot rhythm avoiding (PRs #97, #98, #99, #100, #102, #104, #107). Defeats the kernel-flatten purpose.
2. **uv workspace + dual root pyproject**. Root pyproject keeps `[project] name = "kanon-kit"` for dev-loop convenience (`pip install -e '.[dev]'` works as today); per-package pyprojects only get used by `python -m build` at release time. The `kit-meta/pyproject.toml` (canonical kanon-kit publish target) and the root pyproject (dev-only convenience) would both name the same distribution — confusing duplication that needs disambiguation (e.g., rename root to `kanon-monorepo-dev`). **Rejected**: the duplication is structural, not cosmetic; future contributors will read both pyprojects and ask which is canonical.
3. **Pause Phase A implementation; commit to all prior decisions but defer the actual PyPI three-distribution split until a forcing function appears.** Selected.

## Decision

**Phase A implementation is paused indefinitely. The substrate-shape commitment (ADR-0048), the distribution-name ratification (ADR-0051), the monorepo-layout ratification (ADR-0049), and all per-decision deferrals (ADR-0050, ADR-0052) stand. The actual three-distribution PyPI split — per-package pyprojects, root-pyproject workspace conversion, release.yml reshape, PyPI registration of `kanon-core` + `kanon-aspects` — does not execute until a forcing function appears.**

A forcing function is defined as **any** of:

1. **A real downstream consumer asking for `kanon-core` only** (i.e., wanting to depend on the substrate kernel without paying for the seven reference aspects). Today there are zero consumers, per ADR-0048 §Decision §3 and the lead's deferred-audience commitment.
2. **`hatchling` or the `editables` library upstream gaining prefix-add (or per-pyproject-source-root) support** that allows a per-package pyproject to live inside its package directory without breaking PEP 660 editable installs. Tracked at [pfmoore/editables#20](https://github.com/pfmoore/editables/issues/20) (referenced by the actual error message Hatch produces). When that issue resolves, the architectural blocker for Option 1 (per-package pyproject co-location) goes away and Phase A can proceed via the canonical Hatch layout without source-tree restructuring.
3. **A panel-class re-review judging the implementation cost has been paid down** by some other change (e.g., the project moving away from Hatch entirely, or a contributor stepping forward to absorb the 4–6 hours of build-config trial-and-error in exchange for the architectural cleanliness).

Any of those three reopens Phase A. Until then, the kanon-kit monolith stays the single ship target. `pip install kanon-kit` continues to install everything.

This ADR is **honest about what's deferred** versus what isn't:

| Decision | Status |
|---|---|
| ADR-0048 substrate-shape commitment | Accepted, in force, no rollback |
| ADR-0051 distribution naming (`kanon-core` + `kanon-aspects` + `kanon-kit`) | Accepted, in force; names reserved-by-decision-not-by-PyPI |
| ADR-0049 monorepo layout | Accepted, in force; 6 of 8 §1 rules implemented; §1(2) executed via ADR-0050 Option A; §1(7) deferred per ADR-0052 |
| ADR-0050 kernel-flatten Option A | Executed in v0.5.0a2 |
| ADR-0052 aspects-flatten Option C | Accepted, in force; deferred indefinitely |
| **Phase A.β** per-package pyprojects | **Deferred per this ADR** |
| **Phase A.γ** release.yml reshape for three-wheel publishing | **Deferred per this ADR** |
| **Phase A.δ** PyPI registration of `kanon-core` + `kanon-aspects` | **Deferred per this ADR** |
| **Phase A.ε** first three-package release | **Deferred per this ADR** |
| **Phase A.9** migration script (`kanon migrate v0.3 → v0.4`) | **Deferred per this ADR** — same forcing-function gate (no v0.3 consumer to migrate) |

## Alternatives Considered

1. **Plough ahead with Option 2 (uv workspace + dual root pyproject)**. Rejected per §Context. Workable but the structural duplication is a permanent contributor confusion source; the cost recurs every onboarding.
2. **Plough ahead with Option 1 (move kernel source one level deeper)**. Rejected per §Context. Replays ADR-0050's 12-hour cost class for diminishing returns.
3. **Continue informally pausing without an ADR**. Rejected. The Phase A roadmap is referenced in 8+ ADRs and 30+ docs as the planned future; readers tracing those references deserve an explicit "this is paused, here's why, here's what unpauses it" record. ADR-0050's precedent of authoring follow-up ADRs to refine ADR-0048's commitments rather than letting them rot is the right model.
4. **Roll back the substrate commitment (ADR-0048) entirely**. Considered briefly. Rejected — ADR-0048's commitment is sound; its cost is just bigger than the architectural ratification implied. The cost shows up in implementation, not in concept. Rolling back the concept to escape the implementation cost would be over-correction.

## Consequences

### Documentation

- ADR-0049 §1(7) (aspects-flatten) is already deferred per ADR-0052; this ADR adds a parallel deferral for ADR-0049 §Implementation Roadmap PR B (per-pyproject co-location half).
- The Phase A.9 plan (`docs/plans/active/phase-a.9-migration-script.md`) carries an explicit deferral note pointing at this ADR. (`status: approved` stays — the plan is correct; its execution is gated.)
- `docs/design/distribution-boundary.md` should gain a one-paragraph ADR-0053 note clarifying that the three-distribution layout described therein is the **target architecture**, not the **current implementation**, and that the current ship is `kanon-kit` monolithically.
- Future ADRs that name the planned distributions (e.g., a hypothetical `kanon-publisher-substrate` extension) should reference this ADR's forcing-function gate.

### Engineering

- **Zero immediate engineering work.** The kanon-kit monolith continues to ship as today.
- The existing release pipeline (validated in PR #100 + #106 + #107) stays correct.
- The 3 unused PyPI distribution names (`kanon-core`, `kanon-aspects`) remain unclaimed (HTTP 404 as of 2026-05-03). When a forcing function appears, claim happens at that time.
- The substrate-self-conformance invariant (ADR-0044) continues to be probed by `kanon verify .` exit-0 against the kanon repo's own `.kanon/config.yaml`. The split being deferred does not affect this — self-host conformance is wheel-shape-agnostic.

### Reversal

- Reversing this ADR is one of three signals: (a) a downstream consumer arrives, (b) `pfmoore/editables#20` resolves upstream, (c) panel re-review. The reverser writes a new ADR superseding this one (per ADR-0032 immutability) and Phase A executes.

## References

- [ADR-0048](0048-kanon-as-protocol-substrate.md) — substrate-shape commitment; in force.
- [ADR-0049](0049-monorepo-layout.md) — monorepo layout; in force; §Implementation Roadmap PR B's co-location half deferred per this ADR.
- [ADR-0050](0050-kernel-flatten-deferral.md) — kernel-flatten deferral that established the precedent of "constraint-acknowledging ADR for a Hatch+editables blocker."
- [ADR-0051](0051-distribution-naming.md) — distribution names ratified; PyPI registration deferred per this ADR.
- [ADR-0052](0052-aspects-flatten.md) — aspects-flatten deferral; this ADR is its sibling for the per-pyproject co-location.
- [`pfmoore/editables#20`](https://github.com/pfmoore/editables/issues/20) — the upstream issue whose resolution would unblock Option 1.
- v0.5.0a2 release cycle: PRs #96, #97, #98, #99, #100, #102, #104, #107 — the empirical cost of Option-1-class moves.
- 2026-05-03 experimental attempt: `wt/phase-a-beta-pyprojects` branch (deleted; never PR'd) confirmed the editables error against an isolated `kernel/pyproject.toml` test.
