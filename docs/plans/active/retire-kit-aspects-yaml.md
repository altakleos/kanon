---
feature: retire-kit-aspects-yaml
status: planned
date: 2026-05-05
---
# Plan: Retire the kit-level `aspects:` block, port CI gates to `pyproject.toml` as external oracle

## Context

`packages/kanon-core/src/kanon_core/kit/manifest.yaml` carries an `aspects:` block listing the seven reference aspects with `stability`, `depth-range`, `default-depth`, `requires`, `provides`, and `path` for each. At runtime, `_load_top_manifest` (`packages/kanon-core/src/kanon_core/_manifest.py:354-365`) reads the YAML then **overwrites** the `aspects:` block with the entry-point loader's output (`_load_aspects_from_entry_points`). The YAML's content is runtime-irrelevant.

**Upstream-on-main partial completion (informs this plan's residual scope).** Between this plan PR's first push and its rebase onto `8145448`, the maintainer landed several `_kit_root()` retirement commits directly on main:
- `4b243ff fix: address critical gaps — preflight timeout, _kit_root retirement, bare-name removal` — replaced runtime `_kit_root()` calls with `importlib.resources` via `_kit_data()` (ADR-0045 A.2 complete); bare-name CLI sugar now hard-fails (ADR-0045 A.5 + ADR-0048 publisher-symmetry); wired `INV-resolutions-resolver-not-in-ci` validator.
- `6dd8628 refactor: remove dead _kit_root() function, add _kit_data tests`.
- `9931231` / `9ed7037` / `8015015` — CI-fix iteration that turned main green at `8145448`.

This plan's runtime-side scope (kit YAML's content runtime-irrelevance) is therefore pre-existing. The plan's residual surface — three CI gates that still read the YAML's `aspects:` block (`check_kit_consistency.py`, `check_package_contents.py`, `tests/test_aspect_provides.py:313-318`) — is unchanged by the upstream work. T4's deletion of the YAML's `aspects:` block, plus the gate refactors in T1–T3, together complete ADR-0040 §Decision item 7 (`_kit_root()` retirement); upstream commits `4b243ff` + `6dd8628` did the runtime half, this PR does the CI-gate half.

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
- [ ] T4: **Delete `packages/kanon-core/src/kanon_core/kit/manifest.yaml` outright** (user-approved). Phase A.3 already retired `defaults:` and `files:`; only the `aspects:` block + comments remain, and T1–T3 retire those. `_load_top_manifest` at `packages/kanon-core/src/kanon_core/_manifest.py:354-365` already handles the missing-file path via `if path.is_file() else {}` at line 363; verify nothing else breaks. → `packages/kanon-core/src/kanon_core/kit/manifest.yaml` (delete), `packages/kanon-core/src/kanon_core/_manifest.py` (verify only)
- [ ] T5: Update fixture-synthesizing tests at `tests/scripts/test_check_kit_consistency.py:37,49,70,99,122,138,143,213,223,252,262`. The fixtures construct synthetic kit-level YAML; they must convert to synthesizing per-aspect manifest fixtures + a `pyproject.toml` declaring entry-points. **DRY: extract a `_make_synthetic_aspect_bundle(name, *, depth_range, default_depth, stability, requires=(), provides=(), **fields)` helper in `tests/scripts/conftest.py`** (user-approved) that authors both files atomically. Eleven fixture sites convert to one-line calls. → `tests/scripts/conftest.py`, `tests/scripts/test_check_kit_consistency.py`
- [ ] T6: Update `scripts/check_package_contents.py`'s required-paths constant at line 53 — **remove `kanon_core/kit/manifest.yaml` from the required-paths list** (the file is deleted in T4). → `scripts/check_package_contents.py`
- [ ] T7: Add a generated discoverability artifact at **`docs/reference-aspects.md`** (publisher-neutral name, NOT `docs/kit-aspects.md` — panel R2 ratified the rename). Generated by a small script (e.g., `scripts/gen_reference_aspects.py`) that reads `pyproject.toml`'s `[project.entry-points."kanon.aspects"]` table + each per-aspect `manifest.yaml`, emits a markdown table of slug + stability + depth-range + default-depth + description. Three guardrails per panel:  (a) generation notice at the top of the file citing `pyproject.toml` + `entry_points.txt` as the source; (b) framing in the prose: "Aspects shipped by this distribution" — *never* "kanon's aspects" or "the curated set" or "the kit's aspects" (per `P-protocol-not-product` §Implications); (c) a CI gate (folded into `check_kit_consistency.py` or a new `check_reference_aspects_doc.py`) that runs the generator in `--check` mode and fails if the committed file diverges from regeneration — same pattern as `mypy --strict` or `ruff format --check`. → `docs/reference-aspects.md` (new), `scripts/gen_reference_aspects.py` (new)
- [ ] T8: CHANGELOG entry under `## [Unreleased]` describing the symmetry fix. → `CHANGELOG.md`
- [ ] T9: **Pull-forward — synthetic publisher-symmetry CI overlay.** Ship a synthetic `tests/fixtures/acme-test-aspects/` source tree with its own `pyproject.toml` declaring `[project.entry-points."acme-test-aspects.aspects"]` (or analogous group) plus per-aspect manifests. Add a CI step that points the three refactored gates (`check_kit_consistency.py`, `check_package_contents.py`, the new drift test) at the synthetic overlay and asserts they produce **identical structural findings** (modulo the publisher slug) to what they emit against the kit's own bundle. Wire into `.github/workflows/checks.yml` as a required step. This is the operational signal that `P-publisher-symmetry` §Implications ("CI gates the symmetry empirically") is satisfied — not just claimed. Without this, the entire plan ships a publisher-symmetric refactor whose symmetry is asserted but never enforced. → `tests/fixtures/acme-test-aspects/` (new tree), `tests/scripts/test_publisher_symmetry.py` (new), `.github/workflows/checks.yml`
- [ ] T10: **In the execution PR (NOT this plan PR)** — append a `## Historical Note` section to `docs/decisions/0040-kernel-reference-runtime-interface.md` recording that §Decision item 7 (`_kit_root()` retirement) is operationally complete. The note must reference the two-stage completion: **runtime** retirement landed upstream in commits `4b243ff` (replace `_kit_root()` calls with `_kit_data()`) and `6dd8628` (delete the dead function); **CI-gate** retirement (the documentation-layer residue — kit YAML's `aspects:` block + the three gates that read it) lands in this PR's T4. Body MUST be factually accurate at write time (i.e., land in the same commit that completes T4). Permitted by ADR-0032's three-exception-class discipline (exception class 2: appending `## Historical Note`). → `docs/decisions/0040-kernel-reference-runtime-interface.md`

## Acceptance Criteria

- [ ] AC1: `python scripts/check_kit_consistency.py` exits 0 on the kanon repo with the kit YAML's `aspects:` block deleted.
- [ ] AC2: `python scripts/check_package_contents.py --wheel <path-to-built-wheel> --tag vX.Y.Z` exits 0 against a freshly-built wheel.
- [ ] AC3: `python -m pytest tests/test_aspect_provides.py tests/scripts/test_check_kit_consistency.py tests/scripts/test_check_package_contents.py` all pass.
- [ ] AC4: `python -m pytest` (full suite) passes the 90% coverage gate.
- [ ] AC5: `python scripts/check_substrate_independence.py` still exits 0 (the ADR-0044 gate must continue to hold).
- [ ] AC6: `kanon verify .` status: ok.
- [ ] AC7: **Permanent publisher-symmetry CI gate** — `tests/scripts/test_publisher_symmetry.py` runs on every PR + merge-to-main as a required step in `.github/workflows/checks.yml`, asserts the three refactored gates produce structurally-equivalent findings against `tests/fixtures/acme-test-aspects/` and against the kit's own bundle. This is the operational ratification of `P-publisher-symmetry` §Implications ("CI gates the symmetry empirically") — promoted from a manual sanity check (R1 framing) to a permanent CI invariant per panel R2 unanimous vote.
- [ ] AC8: ADR-0040 §Decision item 7 (`_kit_root()` retirement) is operationally complete — the deletion of `aspects:` from the kit YAML is the last documentation-layer residue, and `docs/decisions/0040-kernel-reference-runtime-interface.md` carries a `## Historical Note` (T10) recording the completion in the execution commit.
- [ ] AC9: **Discoverability artifact regenerates clean.** `python scripts/gen_reference_aspects.py --check` exits 0 against the committed `docs/reference-aspects.md`. The committed file is identical to the regenerated output.
- [ ] AC10: **Self-host atomicity preserved.** `kanon verify .` passes at every commit boundary in this PR (one PR, single semantic operation per panel R2 4A vote — no intermediate non-self-hosting state on `main`).

## Documentation Impact

- **CHANGELOG**: `## [Unreleased]` entry under "Changed" naming the YAML deletion, the new pyproject-as-oracle gate paths, the `tests/fixtures/acme-test-aspects/` overlay, and the new `docs/reference-aspects.md` discoverability artifact.
- **README**: existing "Reference aspects" table at `README.md` lines 49-58 is hand-maintained today; cross-link from it to the new `docs/reference-aspects.md` (which is the always-fresh copy). README's table can be retained or trimmed at author's discretion — the generated artifact is the source of truth, the README is a marketing surface.
- **`docs/reference-aspects.md`** (new) — generated artifact, neutral framing, citation header. T7.
- **`docs/decisions/0040-kernel-reference-runtime-interface.md`**: in the execution PR (T10), append a `## Historical Note` section recording that §Decision item 7 (`_kit_root()` retirement) is operationally complete in this commit. Permitted by ADR-0032 exception-class 2. Body of the ADR remains immutable.

## Risk Register

1. **`check_package_contents.py` runs against a built wheel in `release.yml:25-34`. The new path reads `kanon_kit-*.dist-info/entry_points.txt` from the wheel.** **Resolved 2026-05-05**: built `kanon_kit-0.5.0a7-py3-none-any.whl` locally with hatchling and confirmed (a) `dist-info/entry_points.txt` is present, (b) the `[kanon.aspects]` section lists all seven reference aspects in `slug = module:object` format, (c) the file is reproducibly derived from source-tree `pyproject.toml`'s entry-points table at build time. **Residual mitigation**: T2 still includes a one-line assertion that the file is present before parsing it, so a future hatch backend swap fails loudly rather than silently missing aspects.
2. **Multi-source drift in fixture-synthesizing tests** (T5). Each fixture now needs to construct both `pyproject.toml` and per-aspect `manifest.yaml`, and they must be consistent within the fixture. **Mitigation**: extract a helper `_make_synthetic_aspect_bundle(name, ...)` in `conftest.py` that authors both files atomically.
3. **The drift test (T3) only catches `provides:` drift** — same blind spot as today. The expanded sentinel only matters if it covers fields where divergence matters. **Mitigation**: extend the new test to also cross-check `stability`, `depth-range`, `default-depth` (the verifier panel's blind-spot list).
4. ~~`acme-*` symmetry validation is post-merge-only.~~ **Resolved by T9 + AC7 (panel R2 unanimous)**: the `tests/fixtures/acme-test-aspects/` overlay + permanent CI gate ratify symmetry on every commit, not as a manual post-merge check.
5. **Refactor blast radius**. Three CI scripts + multiple tests + a kit YAML deletion + a new generator script + a new symmetry test + a new fixture tree + an ADR historical note. **Mitigation**: each task lands as a separate commit within the single PR (panel R2 4A vote: atomicity preferred over split for `P-self-hosted-bootstrap` reasons; commits-within-PR give bisectability without the intermediate-state risk surface a multi-PR split would create). Pre-push: each commit individually runs `kanon verify .` + `python scripts/check_kit_consistency.py` + `pytest tests/scripts/` locally.
6. **Generator-script drift** (T7 introduces `scripts/gen_reference_aspects.py`). If the generator's output format changes without `docs/reference-aspects.md` being regenerated, AC9 fails. **Mitigation**: AC9 is the regression test; the generator's output format is stable-by-construction (markdown table, alphabetical aspect ordering, no timestamps).
7. **Symmetry-overlay maintenance** (T9 introduces `tests/fixtures/acme-test-aspects/`). The overlay's manifests must stay in sync with the substrate's dialect grammar — if a future dialect bumps a required field, the overlay needs a parallel update or AC7's CI step turns red. **Mitigation**: the overlay tree is minimal (one synthetic aspect, e.g., `acme-test-foo`, declaring stability/depth-range/provides as required by current dialect). Document its purpose in a top-level README inside the fixture tree so a future dialect-bump contributor knows to update it.

## Notes

- **Why this is a plan-only PR.** The user specifically chose option 2 from the panel-synthesis options ("plan-only — draft the plan and let me review before executing"). The plan is the artifact; execution awaits approval.
- **Why no design doc.** The architectural choice (delete + port to pyproject-as-oracle) is the panel's converged recommendation and is captured in the Context section above. ADR-0055 already ratified per-aspect manifest as canonical; ADR-0040 §7 already ratified the kit-root retirement. This plan operationalises the residue. No new component boundary, no new mechanism — the gates are pattern-instantiations of the existing `check_*.py` shape pointed at a different external oracle.
- **Why no spec.** No new user-visible capability. Internal CI hygiene + the runtime contract that already shipped (`_load_top_manifest` overwrites the YAML's aspects block; behavior unchanged).
- **Why no ADR.** The architectural decisions (publisher symmetry, kit-root retirement, per-aspect canonicality) are already ratified in ADR-0040, ADR-0055, ADR-0044, ADR-0048. This plan is a pattern-instantiation of those decisions; ADR-0032's "no ADR needed for routine pattern-following" rule applies.

## Panel Synthesis (preserved for review)

Two rounds, five agents (architect / critic / code-reviewer / document-specialist / verifier). Full reports preserved in the conversation transcript.

### Round 1 — Initial findings (informed T1–T6 architecture)

- **Architect**: Delete YAML's `aspects:` block. Port gates to publisher-agnostic checks over `(entry_points("kanon.aspects"), per-aspect manifest.yaml)`. Optional generated discoverability index.
- **Critic**: "Deliberately-redundant schema-of-record" framing is motivated reasoning. Real axis is declarative-static (per-aspect, ADR-0055) vs executable-dynamic (entry-points, ADR-0040). Vestigial aggregator.
- **Code-reviewer**: REQUEST CHANGES on naive deletion. **Critical insight**: post-deletion, `check_package_contents.py` becomes self-referential unless replaced with an external oracle. Recommends `pyproject.toml`'s entry-points table as the new oracle (declarative, version-controlled, external).
- **Document-specialist**: Cites ADR-0040 §7 (`_kit_root()` retirement) and ADR-0044 (substrate-independence). Atomic deletion is the operational completion signal.
- **Verifier**: YAML is mostly illusory falsification. The one structurally grounded use is `check_package_contents.py`'s offline wheel-shape check — and even there, the YAML's `depth-range` can go stale silently.

### Round 2 — Editorial decisions (informed T7–T10 + AC7–AC10)

R2 ran on four contested editorial questions. Final tallies:

- **Q1 (discoverability artifact)**: 5–0 for 1A (generated `docs/reference-aspects.md`), with publisher-neutral rename + framing guardrails. Doc-specialist's R1 dissent (1C drop) updated to 1A under the renaming compromise — `docs/reference-aspects.md` framed as "Aspects shipped by this distribution" preserves discoverability without privileging the `kanon-` namespace in prose. → T7.
- **Q2 (acme-test overlay)**: 5–0 for 2A unanimous in both rounds — pull forward, ship `tests/fixtures/acme-test-aspects/` + permanent CI gate. P-publisher-symmetry §Implications ("CI gates the symmetry empirically") demands an automated gate, not a manual sanity check. → T9 + AC7.
- **Q3 (ADR-0040 historical note)**: 4–1 for 3A (note in execution PR). Critic and code-reviewer flipped from R1's 3C ("single review context") to 3A under verifier's "false claim" rebuttal — a note recording completion must be factually true at write time. Architect held a creative 3C re-framing the note as "plan-of-record" but was outvoted. → T10.
- **Q4 (PR scope split)**: 3–2 for 4A (single PR). Code-reviewer's R2 walked the verifier's intermediate-state scenario and found it doesn't fire as originally described, but verifier and doc-specialist held 4A on `P-self-hosted-bootstrap` atomicity grounds; architect and code-reviewer held 4B on bisectability. **User broke the tie in favor of 4A.** → AC10 + Risk-5 mitigation framing.

### What the panel is NOT recommending

- No deferred follow-up plans — every panel-ratified item is in *this* plan's scope (T9 was the highest-pressure one to defer; pulled forward unanimously).
- No multi-PR split — atomicity wins per panel + user.
- No README-only discoverability — the generated artifact is required, not optional.
