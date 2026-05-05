---
feature: retire-kit-aspects-yaml
status: planned
date: 2026-05-05
---
# Plan: Retire the kit-level `aspects:` block, port CI gates to `pyproject.toml` as external oracle

## Context

`packages/kanon-core/src/kanon_core/kit/manifest.yaml` carries an `aspects:` block listing the seven reference aspects with `stability`, `depth-range`, `default-depth`, `requires`, `provides`, and `path` for each. At runtime, `_load_top_manifest` (`packages/kanon-core/src/kanon_core/_manifest.py:354-365`) reads the YAML then **overwrites** the `aspects:` block with the entry-point loader's output (`_load_aspects_from_entry_points`). The YAML's content is runtime-irrelevant.

The block is read at CI time by three gates:

1. `scripts/check_kit_consistency.py:65,189-223,378-392` — schema validation (names match `^kanon-`, fields present, `stability ∈ {experimental, stable, deprecated}`, `depth-range` shape, path resolution, `requires:` predicate parsing).
2. `scripts/check_package_contents.py:53,110-122` — reads the wheel's copy of the YAML to enumerate which per-aspect `manifest.yaml` files MUST ship in the wheel.
3. `tests/test_aspect_provides.py:313-318` (`test_kit_manifest_yaml_provides_aligns_with_loader`) — cross-checks the YAML's `provides:` against the entry-point loader output as a drift sentinel.

A 5-agent panel (architect / critic / code-reviewer / document-specialist / verifier — synthesis below) converged on three structural findings:

1. **The kit YAML violates [`P-publisher-symmetry`](../../foundations/principles/P-publisher-symmetry.md).** `acme-*` bundles cannot ship a kit-level YAML; CI gates reading it are structurally `kanon-`-only. ADR-0040 §7 retires `_kit_root()` for the same reason; the YAML is the documentation-layer residue of that retirement.
2. **The drift sentinel is mostly theatre.** Only `provides:` is cross-checked between YAML and entry-points. `stability`, `depth-range`, `requires` drift between the two sources passes silently. The verifier identified a real blind spot at `check_package_contents.py:110-122` — it derives required-files from the YAML's `depth-range`, so a contributor who extends `depth-range` in the entry-point MANIFEST without updating the YAML will see CI happily verify the wheel against the **stale range**, missing the new files entirely.
3. **`check_package_contents.py` is the load-bearing edge case.** It runs against a wheel zip (no Python env, no entry-points). It needs *some* declarative oracle external to the wheel. Replacing the YAML with "iterate entry-points from inside the wheel" makes the gate self-referential.

**The right external oracle**: `pyproject.toml`'s `[project.entry-points."kanon.aspects"]` table at the source-tree root. It is publisher-authored, declarative, source-controlled, external to the wheel, and identical in shape between `kanon-aspects` and any hypothetical `acme-fintech-aspects` (each publisher's own `pyproject.toml` becomes the oracle for their own gate run). This satisfies `P-publisher-symmetry`, removes the self-reference risk, and aligns with ADR-0055's "per-aspect manifest is canonical."

This plan is **plan-only** at user request. Source edits await user approval of this plan.

## Tasks

- [ ] T1: Refactor `scripts/check_kit_consistency.py` so its `_load_top_manifest` (the script's own helper, lines 65) and `_check_registry_and_manifests` (lines 189-223) iterate aspects via `pyproject.toml`'s `[project.entry-points."kanon.aspects"]` table at the workspace root + each aspect's own `manifest.yaml`. The schema fields previously read from the kit YAML are read from each per-aspect `manifest.yaml` instead (canonical per ADR-0055). Cross-aspect exclusivity, byte-equality, AGENTS.md marker discipline, and `requires:` predicate resolution all remain. → `scripts/check_kit_consistency.py`
- [ ] T2: Refactor `scripts/check_package_contents.py:106-130` (`_derive_requirements_from_wheel`). Read the wheel's `kanon_core-*.dist-info/entry_points.txt` (the wheel-internal manifestation of the source-tree `pyproject.toml`'s entry-points) to enumerate aspect slugs, then for each slug iterate the wheel's per-aspect `manifest.yaml` to derive the `depth-N` required-files list. The wheel is no longer self-referential because `entry_points.txt` is reproducibly derived from `pyproject.toml` at build time, not from the kit YAML. → `scripts/check_package_contents.py`
- [ ] T3: Replace `tests/test_aspect_provides.py::test_kit_manifest_yaml_provides_aligns_with_loader` (lines 312-322) with `test_pyproject_entry_points_align_with_per_aspect_manifests`. The new test parses `pyproject.toml`, walks each declared entry-point's resolved per-aspect manifest, and asserts each aspect's `provides:` matches what `_load_top_manifest()['aspects'][slug]['provides']` returns. The drift sentinel survives but its two sources are now the two genuinely-independent declarative artifacts (pyproject + per-aspect manifest), not YAML-vs-entry-point loader. → `tests/test_aspect_provides.py`
- [ ] T4: Delete the `aspects:` block from `packages/kanon-core/src/kanon_core/kit/manifest.yaml`. Update the file's header comment to reflect what the file now is (kit-globals only — currently empty post-Phase-A.3 retirement of `defaults:` and `files:`); recommend deleting the file outright if no kit-globals remain. Update `_load_top_manifest` at `packages/kanon-core/src/kanon_core/_manifest.py:354-365` to no longer expect the file (graceful fallback to `{}` is already in place at line 363). → `packages/kanon-core/src/kanon_core/kit/manifest.yaml`, `packages/kanon-core/src/kanon_core/_manifest.py`
- [ ] T5: Update fixture-synthesizing tests at `tests/scripts/test_check_kit_consistency.py:37,49,70,99,122,138,143,213,223,252,262`. The fixtures construct synthetic kit-level YAML to drive the gate's tests; they must convert to synthesizing per-aspect manifest fixtures + a `pyproject.toml` declaring entry-points. → `tests/scripts/test_check_kit_consistency.py`
- [ ] T6: Update `scripts/check_package_contents.py`'s required-paths constant at line 53 (currently includes `kanon_core/kit/manifest.yaml`). Either remove the line if the file is deleted in T4, or keep the line if the file remains as a kit-globals stub. → `scripts/check_package_contents.py`
- [ ] T7: Add a (non-load-bearing) discoverability artifact: a generated table at `docs/kit-aspects.md` (or extend the README's "Reference aspects" table) listing all aspects with stability/depth/description, rebuilt by the same logic that drives the gates. This restores the at-a-glance index the kit YAML provided to humans without re-introducing a privilege code path. **Optional** — cut from the plan if review concludes the README table is sufficient. → `docs/kit-aspects.md` (new) or `README.md`
- [ ] T8: CHANGELOG entry under `## [Unreleased]` describing the symmetry fix. → `CHANGELOG.md`

## Acceptance Criteria

- [ ] AC1: `python scripts/check_kit_consistency.py` exits 0 on the kanon repo with the kit YAML's `aspects:` block deleted.
- [ ] AC2: `python scripts/check_package_contents.py --wheel <path-to-built-wheel> --tag vX.Y.Z` exits 0 against a freshly-built wheel.
- [ ] AC3: `python -m pytest tests/test_aspect_provides.py tests/scripts/test_check_kit_consistency.py tests/scripts/test_check_package_contents.py` all pass.
- [ ] AC4: `python -m pytest` (full suite) passes the 90% coverage gate.
- [ ] AC5: `python scripts/check_substrate_independence.py` still exits 0 (the ADR-0044 gate must continue to hold).
- [ ] AC6: `kanon verify .` status: ok.
- [ ] AC7: **Symmetry sanity check** — write a one-shot script (post-merge tested only, not committed) that points the gates at a synthetic `acme-fintech-aspects` source tree (with its own `pyproject.toml` declaring entry-points and per-aspect manifests) and confirms the gates produce identical structural findings to what they emit against the kit's own bundle. This is the operational signal that publisher symmetry is achieved at the gate layer, not just claimed.
- [ ] AC8: ADR-0040 §Decision item 7 (`_kit_root()` retirement) is operationally complete (the deletion of `aspects:` from the kit YAML is the last documentation-layer residue).

## Documentation Impact

- CHANGELOG: Unreleased entry under "Changed" or "Removed" naming the YAML deletion + the symmetry fix.
- README: if a generated kit-aspects table replaces the YAML's discoverability role, README's "Reference aspects" section may grow to reflect that. Otherwise no change.
- `docs/decisions/0040-kernel-reference-runtime-interface.md`: §"Out of scope" → §"Resolved" — note that `_kit_root()`-residue YAML retirement landed in this PR. Per ADR-0032 immutability, this is appended as a `## Historical Note` section, not a body edit.

## Risk Register

1. **`check_package_contents.py` runs against an unbuilt-wheel context in CI** (`release.yml:25-34`). The new path reads `entry_points.txt` from the wheel — must verify hatch/setuptools wheel-build emits this file consistently. **Mitigation**: add a unit test that asserts the file is present in any kanon-kit wheel before the gate trusts it.
2. **Multi-source drift in fixture-synthesizing tests** (T5). Each fixture now needs to construct both `pyproject.toml` and per-aspect `manifest.yaml`, and they must be consistent within the fixture. **Mitigation**: extract a helper `_make_synthetic_aspect_bundle(name, ...)` in `conftest.py` that authors both files atomically.
3. **The drift test (T3) only catches `provides:` drift** — same blind spot as today. The expanded sentinel only matters if it covers fields where divergence matters. **Mitigation**: extend the new test to also cross-check `stability`, `depth-range`, `default-depth` (the verifier panel's blind-spot list).
4. **`acme-*` symmetry validation (AC7) is post-merge-only** — no CI surface verifies it ongoing. **Mitigation**: file a follow-up plan to ship a synthetic `acme-test` overlay in `tests/` whose presence in CI runs proves the gates are publisher-blind on every commit.
5. **Refactor blast radius**. Three CI scripts + multiple tests + a kit YAML deletion. **Mitigation**: each task lands as a separate commit; each commit individually runs the gate locally before pushing.

## Notes

- **Why this is a plan-only PR.** The user specifically chose option 2 from the panel-synthesis options ("plan-only — draft the plan and let me review before executing"). The plan is the artifact; execution awaits approval.
- **Why no design doc.** The architectural choice (delete + port to pyproject-as-oracle) is the panel's converged recommendation and is captured in the Context section above. ADR-0055 already ratified per-aspect manifest as canonical; ADR-0040 §7 already ratified the kit-root retirement. This plan operationalises the residue. No new component boundary, no new mechanism — the gates are pattern-instantiations of the existing `check_*.py` shape pointed at a different external oracle.
- **Why no spec.** No new user-visible capability. Internal CI hygiene + the runtime contract that already shipped (`_load_top_manifest` overwrites the YAML's aspects block; behavior unchanged).
- **Why no ADR.** The architectural decisions (publisher symmetry, kit-root retirement, per-aspect canonicality) are already ratified in ADR-0040, ADR-0055, ADR-0044, ADR-0048. This plan is a pattern-instantiation of those decisions; ADR-0032's "no ADR needed for routine pattern-following" rule applies.

## Panel Synthesis (preserved for review)

Five agents ran in parallel; full reports preserved in the conversation transcript. Convergence:

- **Architect**: Delete YAML's `aspects:` block. Port gates to publisher-agnostic checks over `(entry_points("kanon.aspects"), per-aspect manifest.yaml)`. Optional generated discoverability index.
- **Critic**: "Deliberately-redundant schema-of-record" framing is motivated reasoning. Real axis is declarative-static (per-aspect, ADR-0055) vs executable-dynamic (entry-points, ADR-0040). Vestigial aggregator.
- **Code-reviewer**: REQUEST CHANGES on naive deletion. **Critical insight**: post-deletion, `check_package_contents.py` becomes self-referential unless replaced with an external oracle. Recommends `pyproject.toml`'s entry-points table as the new oracle (declarative, version-controlled, external).
- **Document-specialist**: Cites ADR-0040 §7 (`_kit_root()` retirement) and ADR-0044 (substrate-independence). Atomic deletion is the operational completion signal.
- **Verifier**: Confirms YAML is mostly illusory falsification. The one structurally grounded use is `check_package_contents.py`'s offline wheel-shape check — and even there, the YAML's `depth-range` can go stale silently. The current setup misses real drift in `stability`, `depth-range`, `requires`. Per-aspect-manifest-driven validation is strictly more comprehensive.
