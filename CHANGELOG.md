# Changelog

All notable user-visible changes to `kanon` are recorded in this file.

The format is based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Substrate-independence CI gate** (per [ADR-0044](docs/decisions/0044-substrate-self-conformance.md), per plan [`sub-substrate-independence`](docs/plans/sub-substrate-independence.md)). New `ci/check_substrate_independence.py` (~125 LOC) verifies that `kanon-substrate`'s runtime code does not depend on `kanon_reference` being importable. Implementation: spawns a Python sub-process with a meta_path finder that masks all `kanon_reference` imports, then exercises substrate-internal queries (`_load_aspects_from_entry_points`, `_aspect_path` fallback, `_resolutions.replay`, `_dialects.validate_dialect_pin`, `_realization_shape.parse_realization_shape`, `_composition.compose`). Fails with structured error if any substrate code attempts `import kanon_reference`. **Partial implementation note:** today's gate verifies the runtime contract (substrate code never reaches into kanon_reference); full ADR-0044 implementation (separately-installed substrate wheel + clean venv test run) requires the packaging split to be build-active per ADR-0043 — a future plan. New `tests/ci/test_check_substrate_independence.py` (4 cases): real-repo-passes, main-exits-zero-on-ok, sub-process-emits-OK-sentinel, failure-when-substrate-imports-kanon_reference (synthesised injection — gate detects + fails).

### Changed

- **Substrate-content-move sub-plan: aspect data moved to `src/kanon_reference/data/`** (per [ADR-0044](docs/decisions/0044-substrate-self-conformance.md), [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md), per plan [`sub-content-move`](docs/plans/sub-content-move.md)). All 7 reference aspects' data (manifest.yaml, protocols/, files/, agents-md/, sections/) — 42 files total — moved from `src/kanon/kit/aspects/<slug>/` to `src/kanon_reference/data/<slug>/`. Substrate-level data at `src/kanon/kit/` (agents-md-base.md, harnesses.yaml, manifest.yaml top registry) stays. The substrate (`kanon-substrate`) now ships ZERO aspect data per ADR-0044's substrate-independence invariant; aspects travel with `kanon-reference`. `_load_aspect_registry()` synthesizes `_source` for kanon-* aspects pointing at the new `kanon_reference.data.<slug>` location via `Path(kanon_reference.__file__).parent / "data" / slug`. `_aspect_path()` fallback updated similarly. Two doc cross-links updated (in `docs/decisions/0036-secure-defaults-config-trust-carveout.md`, `docs/foundations/principles/README.md`). `tests/test_kanon_reference_manifests.py` `KIT_ASPECTS` constant updated to point at new location. `ci/check_kit_consistency.py` gains an `_aspect_root()` helper that checks both new and legacy locations (legacy is now empty for kanon-* aspects but the gate stays robust). Fidelity lock recaptured.

### Added

- **Phase A.9: `kanon migrate v0.3 → v0.4` (deprecated-on-arrival)** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md) step 9, per plan [`phase-a.9-migration-script`](docs/plans/phase-a.9-migration-script.md), per [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md)). New `kanon migrate [--target PATH] [--dry-run]` CLI verb. v3→v4 transitions: adds `schema-version: 4`, `kanon-dialect: "2026-05-01"`, and a `provenance:` entry stamping the migration; strips retired kanon-testing config keys (`test_cmd`/`lint_cmd`/`typecheck_cmd`/`format_cmd`/`coverage_floor` per Phase A.4 deletions). Idempotent — already-v4 configs are no-ops. `--dry-run` previews without writing. Per the canonical sequence, **deprecated-on-arrival**: every output JSON includes a `deprecation:` field; the verb will be removed before v1.0. The kanon repo itself was migrated manually in Phase 0.5; this verb exists for any historical v0.3 consumer resurrecting an old install. New `tests/test_cli_migrate.py` (~115 LOC, 7 cases): already-v4 noop, v3 augmentation, key stripping, dry-run, deprecation banner, missing-config error, idempotence.

### Removed

- **Phase A.8: scaffolded `ci/check_*.py` retirement** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md) step 8, per [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md) de-opinionation, per plan [`phase-a.8-scaffolded-ci-retirement`](docs/plans/phase-a.8-scaffolded-ci-retirement.md)). Five consumer-side CI artifacts retired: `src/kanon/kit/aspects/kanon-deps/files/ci/check_deps.py`, `src/kanon/kit/aspects/kanon-security/files/ci/check_security_patterns.py`, `src/kanon/kit/aspects/kanon-testing/files/ci/check_test_quality.py`, `src/kanon/kit/aspects/kanon-release/files/ci/release-preflight.py`, `src/kanon/kit/aspects/kanon-release/files/.github/workflows/release.yml`. Corresponding `files:` entries deleted from each aspect's depth-N (LOADER MANIFEST + YAML); `preflight:` blocks that referenced the scaffolded scripts (kanon-deps depth-2 push, kanon-security depth-2 push, kanon-release depth-2 release) deleted with them. The substrate no longer scaffolds CI scripts or GitHub-Actions workflow files into consumer repos — consumers wire their own CI per `P-protocol-not-product`. **Important distinction:** the kanon repo's own internal `ci/check_*.py` scripts (e.g., `ci/check_links.py`, `ci/check_foundations.py`, `ci/check_kit_consistency.py`, etc.) are gates the kanon repo runs against itself, not scaffolded; they remain in place. Recipe at `.kanon/recipes/reference-default.yaml` is unchanged (it doesn't reference these scripts). Fidelity lock recaptured.

### Added

- **Phase A.7: CLI verbs for resolutions + contracts** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md) step 7, per plan [`phase-a.7-cli-verbs`](docs/plans/phase-a.7-cli-verbs.md), per [ADR-0039](docs/decisions/0039-contract-resolution-model.md) design, per [ADR-0041](docs/decisions/0041-realization-shape-dialect-grammar.md) design). Four new CLI verbs surface the substrate's resolution + dialect-grammar + composition machinery (Phase A.6a/b/c/d). Two are fully-implemented: (1) `kanon resolutions check [--target PATH]` wraps `_resolutions.stale_check` for cheap pin-check feedback (suitable for IDE integration); emits structured-error JSON, exits 1 on staleness. (2) `kanon contracts validate <BUNDLE>` walks a publisher bundle (per the design's algorithm): validates `kanon-dialect:` pin via `_dialects.validate_dialect_pin`; validates each contract's `realization-shape:` via `_realization_shape.parse_realization_shape`; runs composition pre-flight via `_composition.compose` per surface; surfaces `dialect-invalid`, `missing-realization-shape`, `invalid-realization-shape`, `composition-cycle` errors and `ambiguous-composition` warnings; exits 1 on errors. Two are stubs that surface the verbs in the CLI but defer integration: (3) `kanon resolve [--target PATH] [--contracts SLUG[,SLUG...]]` reports `status: deferred` with rationale (harness-adapter API designed by future ADR). (4) `kanon resolutions explain <CONTRACT-ID>` reports `status: deferred` with rationale (contract registry not yet populated). New `tests/test_cli_resolutions_contracts.py` (~250 LOC, 13 tests) exercises all four verbs end-to-end via `CliRunner`.

- **Phase A.6d: composition algebra module** (per [ADR-0041](docs/decisions/0041-realization-shape-dialect-grammar.md), per plan [`phase-a.6d-composition`](docs/plans/phase-a.6d-composition.md), per design [`docs/design/dialect-grammar.md`](docs/design/dialect-grammar.md) §"Composition resolution algorithm"). New `src/kanon/_composition.py` (~210 LOC) authors topo-sort + cycle detection + `replaces:` resolution. Public surface: `ContractRef` dataclass (contract_id, surface, before, after, replaces); `CompositionError` dataclass (codes: `composition-cycle`, `ambiguous-composition`); `compose(contracts, surface) -> (ordering, findings)` per the design's 6-step algorithm (filter → resolve replaces → build edges → topo-sort with alphabetical tie-break → cycle detection → ambiguity warning). Per INV-dialect-grammar-composition-acyclic and INV-dialect-grammar-replaces-substitution. Cycles fail loudly with explicit cycle-path detail (e.g., `before/after cycle: a --before--> b --before--> a`); ambiguous compositions emit a warning naming the unrelated pairs. Wiring into substrate runtime deferred (no real contracts to compose). New `tests/test_composition.py` (~190 LOC, 16 cases): empty/single/chain orderings, before/after edges, 2-/3-/self-cycles, ambiguity warnings, `replaces:` (drop, chain, cycle, external-target-passthrough), stable-ordering-across-runs.

- **Phase A.6c: realization-shape parser + validator** (per [ADR-0041](docs/decisions/0041-realization-shape-dialect-grammar.md), per plan [`phase-a.6c-realization-shape`](docs/plans/phase-a.6c-realization-shape.md), per design [`docs/design/dialect-grammar.md`](docs/design/dialect-grammar.md)). New `src/kanon/_realization_shape.py` (~155 LOC) authors the substrate's per-contract `realization-shape:` parser + resolution-against-shape validator. Public surface: `V1_DIALECT_VERBS` frozenset (the canonical 9 verbs `lint`/`test`/`typecheck`/`format`/`scan`/`audit`/`sign`/`publish`/`report`); `RealizationShape` dataclass; `ShapeValidationError` dataclass; `parse_realization_shape(raw, *, dialect, source=None) -> RealizationShape` (validates 4 required keys, list-type checks, verb-against-dialect-enumeration); `validate_resolution_against_shape(realized_by, evidence, shape, *, contract=None) -> list[ShapeValidationError]` (walks invocations + evidence; surfaces 4 codes: `invalid-verb`, `invalid-evidence-kind`, `invalid-stage`, `unknown-key`; multiple findings accumulate, no early exit). Per INV-dialect-grammar-shape-validates-resolutions: shape mismatches surface as parallel structures to ReplayError so wiring into `_resolutions.py` replay path (deferred to a later sub-plan, coupled with adding `realization-shape:` to actual contracts) is mechanical. New `tests/test_realization_shape.py` (~270 LOC, 19 cases): V1 verb enumeration, parser success/failure paths (missing keys, non-list verbs, unknown verb, non-bool additional-properties, unsupported dialect, source-label prefixing), validator clean-resolution and structured findings, accumulation-no-early-exit, additional-properties true vs false branches, evidence-without-kind passthrough.

- **Phase A.6b: dialect-grammar module** (per [ADR-0041](docs/decisions/0041-realization-shape-dialect-grammar.md), per plan [`phase-a.6b-dialect-module`](docs/plans/phase-a.6b-dialect-module.md), per design [`docs/design/dialect-grammar.md`](docs/design/dialect-grammar.md), per spec [`docs/specs/dialect-grammar.md`](docs/specs/dialect-grammar.md)). New `src/kanon/_dialects.py` (~80 LOC) authors the substrate's supported-dialect registry + pin-validation primitive. Public surface: `SUPPORTED_DIALECTS = ("2026-05-01",)` (the v0.4 substrate ships v1 dialect only; future supersessions land via ADR-driven additions); `DEPRECATION_WARNING_BEFORE = ()` (nothing deprecated yet — populated when the substrate ships its first supersession); `validate_dialect_pin(manifest_dialect, *, source=None)` which raises `click.ClickException` for missing pin (per INV-dialect-grammar-pin-required) or unknown pin (per INV-dialect-grammar-version-format), and emits a stderr deprecation warning when the pin matches a soon-to-be-retired dialect. Wiring into `_manifest.py` load-time validation is **deferred to a later sub-plan** — coupled with adding `kanon-dialect:` to actual aspect manifests (which currently don't carry it). The validator is exercised via direct tests in `tests/test_dialects.py` (~150 LOC, 17 cases): module-level constant assertions, supported-pin pass-through, missing-pin raises, unknown-pin raises (covering future-format + past-format + malformed), source-label prefixing in error messages, and deprecation-warning behaviour via monkeypatch (synthetic injection — no real deprecation cases yet). Phase A.6c (`_realization_shape.py`) and A.6d (`_composition.py`) follow as separate plans; Phase A.7 wires CLI surfaces.

- **Phase A.6a: resolutions engine module** (per [ADR-0039](docs/decisions/0039-contract-resolution-model.md), per plan [`phase-a.6a-resolutions-engine`](docs/plans/phase-a.6a-resolutions-engine.md), per design [`docs/design/resolutions-engine.md`](docs/design/resolutions-engine.md), per spec [`docs/specs/resolutions.md`](docs/specs/resolutions.md)). New `src/kanon/_resolutions.py` (~290 LOC) authors the substrate's runtime-binding replay engine: prose contracts → agent-resolved YAML → kernel replays mechanically. Public surface: `replay(target, registry=None) -> ReplayReport`; `stale_check(target, registry=None) -> ReplayReport`; `canonicalize_entry(entry) -> bytes`; `ReplayReport`/`ReplayError`/`ExecutionRecord` dataclasses. The engine enforces all six resolutions invariants: hand-edit detection via meta-checksum (INV-resolutions-machine-only-owned); quadruple version-pinning over contract-version + contract-content-SHA + resolver-model + per-evidence-SHA (INV-resolutions-quadruple-pin); evidence-grounding (INV-resolutions-evidence-grounded); replay-determinism (INV-resolutions-replay-deterministic — `resolved-at` excluded from canonicalization; pure functions of inputs); resolver-not-in-ci (the kernel only REPLAYS; the resolver runs only on dev machines via Phase A.7's `kanon resolve` verb); fail-loud staleness (INV-resolutions-stale-fails — any pin drift surfaces a structured `ReplayError`; replay continues to next contract). Canonicalization uses JSON (not YAML) for SHA computation to avoid YAML serializer non-determinism. **Invocation execution stubbed for A.6a** — `ExecutionRecord(executed=False, reason="A.6a stub: ...")` records what *would* execute; Phase A.7 swaps the stub for real subprocess invocation integrated with `kanon preflight`. New `tests/test_resolutions.py` (~360 LOC, 19 cases): all six invariants exercised via synthetic fixtures (no contract-bearing aspects ship `realization-shape:` frontmatter yet — the kanon repo has no real `.kanon/resolutions.yaml`). No CLI verbs / `_verify.py` integration yet (A.7). Phase A.6b (`_dialects.py`) and A.6c (`_composition.py`) follow as separate plans.

### Deprecated

- **Phase A.5: bare-name CLI sugar** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md) step 5, per [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md) publisher-symmetry, per plan [`phase-a.5-bare-name-deprecation`](docs/plans/phase-a.5-bare-name-deprecation.md)). The CLI's bare-name shorthand (`sdd` → `kanon-sdd`, `worktrees` → `kanon-worktrees`, etc.) now emits a stderr deprecation warning when used at any aspect-name input surface (`kanon init --aspects sdd:1`, `kanon aspect add . sdd`, `kanon aspect set-depth . sdd 2`, etc.). The shorthand still functions — sugaring continues; only a warning is emitted. Reason: bare names privilege the `kanon-` namespace at the CLI surface, breaking the substrate's symmetry between `kanon-`, `project-`, and `acme-` publishers (an `acme-fintech` user has no equivalent shorthand). Migration: replace bare names with the full `kanon-<X>` form in all CLI invocations, scripts, and documentation. Future cleanup will delete the bare-name code path entirely once consumers and tests have migrated. New `tests/test_bare_name_deprecation.py` (4 tests) asserts the warning fires for bare names and is silent for namespaced names.

### Removed

- **Phase A.4: `_detect.py` + testing-aspect runtime config-schema** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md) step 4, per [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md) de-opinionation, per plan [`phase-a.4-detect-removal`](docs/plans/phase-a.4-detect-removal.md)). Two opinionated mechanisms retired: (1) `src/kanon/_detect.py` (71 LOC) and `tests/test_detect.py` (104 LOC, 7 tests) deleted entirely — the auto-detection of pytest/ruff/mypy/npm-test from project files is no longer the substrate's job. The `kanon init` block at `cli.py:309-322` that called `detect_tool_config()` and merged results into `aspects_meta["kanon-testing"]["config"]` is removed. The "Detected project tools: pytest" stderr emission is gone. (2) The kanon-testing aspect's `config-schema:` block (declaring `coverage_floor` / `test_cmd` / `lint_cmd` / `typecheck_cmd` / `format_cmd`) deleted from both LOADER MANIFEST (`src/kanon_reference/aspects/kanon_testing.py`) and YAML source-of-truth (`src/kanon/kit/aspects/kanon-testing/manifest.yaml`). The kanon-testing aspect's depth-1 `preflight:` block (which used `${test_cmd}` / `${lint_cmd}` / `${typecheck_cmd}` / `${format_cmd}` placeholders) also deleted — it depended on the removed schema variables. The `_emit_init_hints()` function's "Preflight readiness" stderr emission deleted; the `grow_hints` section preserved (separate concern). Recipe at `.kanon/recipes/reference-default.yaml` no longer carries kanon-testing's `config:` block. The kanon repo's self-host `.kanon/config.yaml` `aspects.kanon-testing.config` reset to `{}`. Tests adapted: `tests/test_cli.py::test_upgrade_preserves_user_aspect_config` switched to arbitrary user-config keys (substrate preserves any keys verbatim); `tests/test_preflight.py::test_resolve_aspect_defaults` switched from kanon-testing to kanon-deps for aspect-contributed-preflight coverage. Doc updated: `docs/contributing.md` module table no longer references the deleted `_detect.py`. Behaviour change for users: `kanon init` no longer auto-fills the kanon-testing config block based on detected tooling — consumers configure aspects explicitly via `kanon aspect set-config` (or by editing `.kanon/config.yaml`).

- **Phase A.3: kit-globals deletion** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md) step 3, per [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md) de-opinionation, per plan [`phase-a.3-kit-globals-deletion`](docs/plans/phase-a.3-kit-globals-deletion.md)). Three kit-shape vestiges retired: (1) `defaults:` block deleted from `src/kanon/kit/manifest.yaml` along with all 3 substrate consumers (`cli.py:_default_aspects` fallback, `tier set` command's iteration, `_manifest.py:_default_aspects()` helper); (2) `files:` block deleted along with all 3 consumers (kit-global file scaffolding in `cli.py` + `_scaffold.py:_build_bundle`, manifest-fields helper in `_manifest.py`); (3) `kit.md` template + scaffolded artifact deleted entirely (template at `src/kanon/kit/kit.md`, consumer artifact at `.kanon/kit.md`, `_scaffold.py:_render_kit_md()`, atomic-writes in `cli.py` + `_cli_aspect.py`, `ci/check_kit_consistency.py:_check_kit_md_exists()`, 2 obsolete gate tests). **Behaviour change for `kanon init` with no flags**: previously auto-enabled the kit-defaults set (`kanon-sdd`, `kanon-testing`, `kanon-security`, `kanon-deps`, `kanon-worktrees`); now scaffolds an empty project. Consumers must opt in via `--aspects`, `--tier`, `--lite`, or `--profile`. **Behaviour change for `--tier N`**: previously raised every aspect in `defaults:` to depth N; now raises every kit-shipped (`kanon-`) aspect to depth N (capped per aspect). 9 obsolete tests deleted/updated across `test_cli.py`, `test_cli_helpers.py`, `test_kit_integrity.py`. The 9 remaining `_kit_root()` call sites in `_scaffold.py` (template/file reads) retire in a subsequent sub-plan when aspect data moves under `src/kanon_reference/aspects/`. The substrate-independence CI gate (per ADR-0044) is rolled into that same content-move sub-plan.

### Fixed

- **`kanon verify` no longer hard-fails on unknown aspects** (per plan [`fix-verify-exception-handling`](docs/plans/fix-verify-exception-handling.md)). Three exception-handler tuples in `src/kanon/_verify.py` (`run_project_validators`, `run_kit_validators`, `check_fidelity_assertions`) had been narrowed to `(OSError, yaml.YAMLError, KeyError, TypeError)` at some point — but the `_aspect_*` lookup helpers in `_manifest.py` raise `click.ClickException` for unknown aspects, which propagated uncaught. Restored to bare `Exception` to match the documented contract ("import error, missing entrypoint, exception during `check`"). Worst symptom: when a consumer's `.kanon/config.yaml` referenced an aspect the kit no longer ships (the upstream-deprecation scenario covered by spec invariant 4), `kanon verify` crashed with "Error: Unknown aspect: 'kanon-bogus'", exit 1 — instead of warning + exit 0 as the spec requires. Four tests turn green: `test_cli_verify::test_verify_unknown_aspect`, `test_fidelity::test_run_project_validators_manifest_load_failure`, `test_verify_validators::test_kit_validator_lookup_failure_warns`, `test_verify_validators::test_fidelity_capability_lookup_failure_warns`.

### Added

- **Phase A.2.2 substrate-side entry-point discovery** (per [ADR-0040](docs/decisions/0040-kernel-reference-runtime-interface.md), per plan [`phase-a.2.2-substrate-discovery`](docs/plans/phase-a.2.2-substrate-discovery.md), per design [`docs/design/kernel-reference-interface.md`](docs/design/kernel-reference-interface.md)). The substrate now discovers aspects via `importlib.metadata.entry_points(group="kanon.aspects")` rather than walking `_kit_root() / manifest.yaml`. Top-level `pyproject.toml` declares the `[project.entry-points."kanon.aspects"]` block (mirroring `packaging/reference/pyproject.toml`); after `uv sync`, the seven canonical kanon-* aspects are discoverable from the installed `kanon-kit` distribution. New `_load_aspects_from_entry_points()` reads each entry-point's `MANIFEST` dict, validates the registry fields, and synthesizes a backward-compat `path:` field (`aspects/<slug>`) for transitional callers in `_scaffold.py`. New `_validate_namespace_ownership(slug, dist)` enforces ADR-0040 §5: `kanon-*` requires `kanon-reference`/`kanon-kit` distribution; `project-*` is rejected (those live under consumer's `.kanon/aspects/`); unknown namespaces warn. The seven LOADER MANIFESTs in `src/kanon_reference/aspects/kanon_*.py` were extended with the registry fields (`stability`, `depth-range`, `default-depth`, `description`, `requires`, `provides`, optional `suggests`) — `path:` is now synthesized by the substrate, not carried in the LOADER. New `KANON_TEST_OVERLAY_PATH` environment variable substitutes the entry-point source with a synthetic-aspects directory (used by tests). `_load_top_manifest()` keeps reading the kit YAML for kit-globals (`defaults:`, `files:`); A.3 retires those when content moves. Two of `_kit_root()`'s eleven call sites are now no-ops because every registry entry carries `_source` from `_load_aspect_registry()`. `_kit_root()` itself survives — the remaining nine call sites in `_scaffold.py` (template/file reads) retire in **Phase A.3** when aspect data moves under `src/kanon_reference/aspects/`. Substrate-independence CI gate (`ci/check_substrate_independence.py` per ADR-0044) is **rolled into Phase A.3** rather than shipped here — the gate would catastrophically fail today (~800 tests assume `kanon_reference` is present) and greening it is naturally co-located with the content move. New `tests/test_aspect_registry.py` (15 tests) covers entry-point discovery, namespace-ownership rules, overlay substitution, and unified-registry composition. `tests/test_kanon_reference_manifests.py` updated: equivalence asserts MANIFEST == union of top-entry (minus `path:`) + sub-manifest, plus a no-`path:` assertion per AC-L2.

- **Phase A.2.1 `kanon_reference` package + LOADER stubs** (per [ADR-0040](docs/decisions/0040-kernel-reference-runtime-interface.md), per plan [`phase-a.2.1-loader-package`](docs/plans/phase-a.2.1-loader-package.md), per design [`docs/design/kernel-reference-interface.md`](docs/design/kernel-reference-interface.md)). New top-level Python package at `src/kanon_reference/` with seven aspect modules at `src/kanon_reference/aspects/kanon_{deps,fidelity,release,sdd,security,testing,worktrees}.py`, each carrying a `MANIFEST: dict[str, Any]` literal that mirrors the corresponding `src/kanon/kit/aspects/<aspect>/manifest.yaml` byte-for-byte (modulo YAML→Python conversion). The `[project.entry-points."kanon.aspects"]` block in `packaging/reference/pyproject.toml` is now active (uncommented from Phase A.1's stubs) and points each of the seven aspect IDs at `kanon_reference.aspects.kanon_<id>:MANIFEST` per the design's recommended static-attribute resolver shape (corrected from the A.1 stubs' `:LOADER` attribute name). Substrate runtime is unchanged: `_kit_root()` still loads from `src/kanon/kit/aspects/`. Substrate-side `_load_aspect_registry()` discovery rewrite + `_kit_root()` retirement (11 call sites) + namespace-ownership validator + `ci/check_substrate_independence.py` gate land in **Phase A.2.2** as a separate plan. New `tests/test_kanon_reference_manifests.py` (parametrized over the seven aspects) asserts each LOADER MANIFEST equals `yaml.safe_load(<corresponding YAML>)` — this contract prevents drift while both sources coexist; Phase A.3 deletes the YAML and the LOADER stubs become canonical. `ci/check_packaging_split.py` gains a new check that validates the seven entry-points are present and target the canonical `kanon_reference.aspects.kanon_<id>:MANIFEST` paths; corresponding gate-test additions cover missing-entry-points and wrong-target failure modes. Placeholder `packaging/reference/src/_kanon_reference_placeholder/` from A.1 is deleted.

- **Phase A.1 distribution-split skeletons** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md) step 1, per plan [`phase-a.1-distribution-split`](docs/plans/phase-a.1-distribution-split.md), per [ADR-0043](docs/decisions/0043-distribution-boundary-and-cadence.md) design [`docs/design/distribution-boundary.md`](docs/design/distribution-boundary.md)). Three new `pyproject.toml` files at `packaging/substrate/`, `packaging/reference/`, `packaging/kit/` lock in the canonical shape for the eventual `kanon-substrate` (kernel) / `kanon-reference` (aspects) / `kanon-kit` (meta-alias) split, all pinned at `1.0.0a1`. Substrate excludes `src/kanon/kit/aspects/**` from the wheel; reference depends on `kanon-substrate==1.0.0a1`; kit-meta depends on both. The skeletons are *schema-of-record* — not yet runtime-functional. The substrate's `_kit_root()` retirement and `kanon_reference` Python package + LOADER stubs land in Phase A.2; aspect content moves in later steps. Top-level `pyproject.toml` remains the active build path for `kanon-kit` v0.3.x. Reference's `[project.entry-points."kanon.aspects"]` block ships as commented-out stubs (`kanon-deps`, `kanon-fidelity`, `kanon-release`, `kanon-sdd`, `kanon-security`, `kanon-testing`, `kanon-worktrees`) for traceability — Phase A.2 uncomments them when LOADER infrastructure lands. New CI gate `ci/check_packaging_split.py` validates name / version / dependencies / exclude-paths against the canonical shape on every commit; new test suite `tests/ci/test_check_packaging_split.py` covers green path + 10 invariant-failure cases.

- **Contract-resolution model ratified** (per [ADR-0039](docs/decisions/0039-contract-resolution-model.md)). The substrate's runtime-binding model: prose contracts (per-aspect, published by `kanon-`/`project-`/`acme-` namespaces) get resolved by a consumer's LLM agent into `.kanon/resolutions.yaml` — a machine-only-owned, evidence-grounded, quadruple-pinned cache (contract-version + contract-content-SHA + resolver-model + per-evidence-SHA) the kernel replays mechanically. The resolver runs only on developer machines; CI replays cached resolutions with no LLM cost. Six invariants ratified in new spec [`docs/specs/resolutions.md`](docs/specs/resolutions.md): machine-only-ownership, quadruple-pinning, evidence-grounding, replay-determinism, resolver-not-in-CI, stale-fails-never-silent. Companion design at [`docs/design/resolutions-engine.md`](docs/design/resolutions-engine.md) specifies the YAML schema, replay algorithm, and Phase A implementation footprint (~390 LOC source + ~600 LOC tests). Verification-contract spec gains INV-11 (exit-zero scope boundary): `kanon verify` exit-0 means conformance to enabled aspects only — not a correctness or quality endorsement; aspects from any namespace verify identically. Phase A implementation (the `_resolutions.py` module, `kanon resolve`/`kanon resolutions check`/`kanon resolutions explain` CLI verbs, and Phase A test suite) follows in subsequent plans.

- **Kernel/reference runtime interface ratified** (per [ADR-0040](docs/decisions/0040-kernel-reference-runtime-interface.md)). The substrate's discovery mechanism: Python entry-points group `kanon.aspects`. Publishers register aspects via `[project.entry-points."kanon.aspects"]` in their `pyproject.toml`; `kanon-substrate` resolves them at startup via `importlib.metadata.entry_points`. `_load_aspect_registry()` unions three sources — entry-point publishers, project-aspects (filesystem, per ADR-0028), and test overlays — with publisher-symmetric resolution: `kanon-`, `project-`, and `acme-` aspects flow through identical code paths. Namespace ownership is source-bounded; mis-namespaced entry-points fail at load time. The substrate's `_kit_root()` is retired (10+ call sites walked in the companion design); the kit-global `files:` field is deleted. New independence invariant: `kanon-substrate`'s test suite must pass with `kanon-reference` uninstalled — Phase A authors a CI gate (`ci/check_substrate_independence.py`) that proves the kernel does not depend on reference content. Spec amendments to [`docs/specs/aspects.md`](docs/specs/aspects.md) and [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md) (append-only "Protocol-substrate composition" sections) explain how the existing INVs compose under the new discovery interface; no INV bodies changed. Companion design at [`docs/design/kernel-reference-interface.md`](docs/design/kernel-reference-interface.md). Phase A footprint: ~+450 LOC source / -80 LOC source / +150 LOC tests across ~12 files.

- **Realization-shape, dialect grammar, and composition algebra ratified** (per [ADR-0041](docs/decisions/0041-realization-shape-dialect-grammar.md)). The substrate's contract grammar — what *shape* aspect manifests and contracts must conform to. Three coupled commitments in one ADR: (1) per-contract `realization-shape:` frontmatter (allowed verbs, evidence kinds, stage keys; the kernel validates resolutions against this at replay); (2) date-stamped dialect-version pinning (`kanon-dialect: YYYY-MM-DD`; substrate honours at least N-1 with a deprecation horizon; ADR-driven supersession); (3) composition algebra (`surface:` + `before/after:` + `replaces:`; topo-sorted at replay; cycles fail loudly with explicit cycle-path reporting). New spec [`docs/specs/dialect-grammar.md`](docs/specs/dialect-grammar.md) carries six dialect-grammar invariants `acme-` publishers can cite by ID. Companion design at [`docs/design/dialect-grammar.md`](docs/design/dialect-grammar.md) specifies the v1 dialect's verb enumeration, the topo-sort algorithm with cycle reporting, the `kanon contracts validate <bundle-path>` walk, and the Phase A implementation footprint (~+800 LOC source + ~+250 LOC tests across ~15 files). Spec amendment to [`docs/specs/aspects.md`](docs/specs/aspects.md): append-only cross-reference paragraph; no INV body changes.

- **Verification scope-of-exit-zero ratified as public claim** (per [ADR-0042](docs/decisions/0042-verification-scope-of-exit-zero.md)). The canonical wording for what `kanon verify` exit-0 means and does NOT mean. INV-11 (added in #53) lives at the spec level; ADR-0042 elevates the claim to a public protocol commitment immutable across substrate releases under [ADR-0032](docs/decisions/0032-adr-immutability-gate.md). Three normative claims: the exit-zero wording itself (positive claim + four MUST-NOTs covering "good engineering practices", "correctness/quality endorsement", "runtime behavioural guarantee", "semantic correctness of resolution invocations"); cross-publisher symmetry (`kanon-`, `project-`, `acme-` aspects verify identically with no warranty exemption by namespace); stability across substrate releases (CLI help text, README, error messages, `acme-` publisher onboarding all use the wording verbatim or by direct citation). Phase A wires the wording into `kanon verify --help` and error messages; this PR is documentation only. Spec amendment to [`docs/specs/verification-contract.md`](docs/specs/verification-contract.md): one cross-reference; no INV body changes.

- **Distribution boundary, release cadence, and recipe artifact ratified** (per [ADR-0043](docs/decisions/0043-distribution-boundary-and-cadence.md)). Three coupled commitments in one ADR: (1) `kanon-substrate` (kernel) ships separately from `kanon-reference` (seven `kanon-` aspects as data); a `kanon-kit` meta-package alias preserves the convenience-install path; (2) cadence policy: kernel daily-alpha permitted; reference weekly; dialect quarterly minimum / annual default; **breaking dialect changes are never kernel releases** — they always ship as dialect supersessions per ADR-0041; (3) recipes are publisher-shipped target-tree YAML at `.kanon/recipes/`; consumer copies, substrate has no kernel verb (preserving `P-protocol-not-product`). New spec [`docs/specs/release-cadence.md`](docs/specs/release-cadence.md) carries five release-cadence invariants (daily-alpha-permitted, reference-weekly, dialect-quarterly-minimum, breaking-not-in-kernel, substrate-honours-N-1). Companion design at [`docs/design/distribution-boundary.md`](docs/design/distribution-boundary.md) specifies concrete `pyproject.toml` shapes for the three packages, the recipe YAML schema with worked example (`reference-default`), the cadence-CI-gate algorithm, and the `kanon migrate v0.3 → v0.4` script outline. Phase A footprint: ~+660 LOC source / +200 LOC tests across ~10 files (three pyproject files, recipe data, migration script, cadence-gate CI script, release-workflow rewrite).

- **Substrate self-conformance discipline ratified** (per [ADR-0044](docs/decisions/0044-substrate-self-conformance.md)). Elevates ADR-0040's independence-invariant bullet to a top-level discipline with its own ADR, its own spec, and its own permanent CI gate. Three normative claims: (1) substrate-independence — `kanon-substrate`'s test suite passes with no `kanon-reference` installed and no `kanon.aspects` entry-points visible; permanent invariant on every kernel-version-bump commit; failure is P0; (2) self-host probe — the kanon repo opts into reference aspects via the publisher recipe and passes `kanon verify .` against itself on every kernel-version-bump; failure is P1; (3) public CI signal — the substrate-independence gate is publicly-readable; algorithm documented sufficient that `acme-` publishers can replicate it against their own bundles. New spec [`docs/specs/substrate-self-conformance.md`](docs/specs/substrate-self-conformance.md) carries five substrate-self-conformance invariants (independence, self-host-passes, recipe-opt-in, gate-public, replicable). No new design — Phase A's gate algorithm lives in `docs/design/kernel-reference-interface.md` (per ADR-0040). This ADR is small in code-impact (Phase A authors `ci/check_substrate_independence.py`) but large in normative weight: it makes substrate-independence permanent, not a Phase A milestone.

- **De-opinionation transition ratified** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md)). The seventh and final Phase 0 ADR. Three commitments: (1) Phase 0.5 self-host hand-over (rewrite kanon repo's `.kanon/config.yaml` to opt-in form via publisher recipe) ships BEFORE any Phase A deletion — reverse order would break self-host between commits and trip ADR-0044's substrate-self-conformance gate; (2) Phase A deletions follow a canonical 9-step sequence (distribution split → `_kit_root()` retirement → kit-global `files:`+`defaults:` deleted → `_detect.py` deleted → bare-name CLI sugar deprecated → resolution+dialect+composition modules → new CLI verbs → scaffolded CI scripts retired → migration script); each step gates on substrate-self-conformance staying green; (3) no backward compatibility for v0.3.x consumers — clean break per ADR-0048; the `kanon migrate v0.3 → v0.4` script (Phase A.9) handles the kanon repo's own transition and is deprecated-on-arrival. Four Alternatives Considered cover deletions-before-hand-over (rejected: breaks self-host), informal ordering (rejected: multi-agent coordination requires canonical sequence), backward-compat shims (rejected: zero current consumers), defer-to-v1.0 (rejected: each kit-shape release accumulates lock-in).

**Phase 0 is now complete.** All seven Phase 0 ADRs (0039 contract-resolution, 0040 kernel/reference runtime interface, 0041 realization-shape + dialect grammar + composition, 0042 verification scope-of-exit-zero, 0043 distribution + cadence + recipe, 0044 substrate self-conformance, 0045 de-opinionation transition) are ratified. Phase 0.5 (self-host hand-over) and Phase A (implementation) follow in subsequent plans.

### Changed

- **Phase 0.5 self-host hand-over** (per [ADR-0045](docs/decisions/0045-de-opinionation-transition.md), per plan [`phase-0.5-self-host-handover`](docs/plans/phase-0.5-self-host-handover.md)). The kanon repo now opts into reference aspects via the publisher recipe — the same mechanism any external consumer would use. New file at `.kanon/recipes/reference-default.yaml` (recipe data per ADR-0043 schema, listing the seven reference aspects at the kanon repo's current self-host depths: kanon-sdd:3, kanon-testing:3, kanon-worktrees:2, kanon-release:2, kanon-security:2, kanon-deps:2, kanon-fidelity:1). `.kanon/config.yaml` augmented with v4 fields (`schema-version: 4`, `kanon-dialect: "2026-05-01"`, `provenance:` block citing the recipe) prepended above the existing v3 fields (`kit_version`, `aspects:`, `preflight-stages:`) which are preserved verbatim. Today's kit's `_read_config()` ignores unknown top-level keys, so `kanon verify .` stays green; the v4 fields are activated by Phase A.1 (distribution split). Symbolic event under ADR-0044 substrate-self-conformance: by stamping the kanon repo's config with the v4 shape *before* any Phase A deletion, Phase A's deletions are no-ops for self-host by construction. Phase A.1 onward follows in subsequent plans.

- **kanon committed as a protocol substrate** (per [ADR-0048](docs/decisions/0048-kanon-as-protocol-substrate.md)). The kit-shape framing of v0.1–v0.3 is retired; reference aspects (`kanon-sdd`, `kanon-testing`, etc.) become de-installable demonstrations rather than the product. Six principles cross over into public-tier status (versioned with the dialect, citable by `acme-` publishers, immutable post-acceptance): `P-prose-is-code`, `P-protocol-not-product`, `P-publisher-symmetry`, `P-runtime-non-interception`, `P-specs-are-source`, `P-verification-co-authored`. Two remain kit-author-internal: `P-self-hosted-bootstrap`, `P-cross-link-dont-duplicate`. `P-tiers-insulate` is retired (tier vocabulary is gone under protocol-shape; depths are per-aspect dials, not a global axis). Three new principles authored: `P-protocol-not-product`, `P-publisher-symmetry`, `P-runtime-non-interception` (the third promoted from vision Non-Goal #2). Three principles amended in scope (`P-specs-are-source`, `P-self-hosted-bootstrap`, `P-verification-co-authored`); pre-amendment bodies preserved at predecessor commit `ded4e77`. The `solo-engineer` and `platform-team` personas are retired (kit-shape audience explicitly deferred); `solo-with-agents` and `onboarding-agent` amended for protocol-shape vocabulary; new `acme-publisher` persona added. Vision rewritten end-to-end; predecessor body preserved at commit `7b7d8d4`. New manifesto at `docs/foundations/de-opinionation.md` codifies the lead's framing. Phase 0 ADRs (0039–0045), Phase 0.5 self-host hand-over, and Phase A implementation follow in subsequent plans.

## [0.3.1a2] — 2026-04-30

### Fixed

- **Per-worktree venv isolation for release preflight** — `ci/release-preflight.py` now uses the local `.venv/bin/python` for all subprocess invocations (pytest, ruff, kanon verify), ensuring worktree preflight validates the worktree's code, not the main tree's. The fragile `PYTHONPATH` hack is removed. Fails fast with a clear error if no local `.venv/` exists.
- **`worktree-setup.sh` auto-runs `uv sync`** for Python projects (detected via `pyproject.toml`), giving each worktree its own `.venv/` with correct editable-install paths.
- **`kanon-release` config depth lowered from 3 to 2** in the self-hosting `.kanon/config.yaml` to match the corrected depth-range.

### Changed

- **Removed dead code in `_cli_helpers.py`** — unreachable boolean type-check branch and unreachable empty-result guard. Coverage now 100% (was 98%).
- **`worktree-lifecycle` protocol strengthened** — per-worktree dependency install is now documented as mandatory for Python projects, with an explanation of why editable installs require it.

## [0.3.1a1] — 2026-04-30

### Fixed

- **`kanon-release` depth-range corrected from `[0, 3]` to `[0, 2]`** — the manifest declared depth 3 but it was empty (zero files, protocols, or sections over depth 2). `--profile max` now correctly sets `kanon-release:2`. README, spec (INV-release-depth-range), and CHANGELOG already documented the range as 0–2; the manifest was a stale artifact. ADR-0037 updated with `Allow-ADR-edit` trailer.
- **`_preflight.py` now surfaces exception details** — when a preflight command raises (e.g., `FileNotFoundError` for a missing binary), the exception message is printed to stderr instead of being silently swallowed.
- **`_scaffold.py` catches non-numeric depth values** — a non-integer `depth:` in `.kanon/config.yaml` (e.g., `"high"`) now raises a clean `ClickException` instead of an ugly `ValueError` traceback.

### Changed

- **`_cli_helpers.py` test coverage raised from 82% to 98%** — 23 new tests covering all error branches. Two remaining uncovered lines are dead code.
- **CI test boilerplate deduplicated** — new `tests/ci/conftest.py` provides shared `load_ci_script` fixture and `_git` helper, eliminating ~210 lines of duplicated importlib/git boilerplate across 14 CI test files.

## [0.3.0a9] — 2026-04-30

### Changed

- **`kanon init` no longer silently skips an existing `AGENTS.md`** (per [ADR-0038](docs/decisions/0038-init-merge-into-existing-agents-md.md)). Three branches by precedence: (1) absent → write the full kit-rendered file; (2) existing with at least one `<!-- kanon:begin:... -->` marker → refresh marker bodies and preserve outside content byte-for-byte (same primitive `kanon upgrade` uses); (3) existing without markers → prepend the full kit-rendered AGENTS.md above the existing prose, separated by a `## Project context` H2 (existing prose preserved verbatim under the H2). Closes a UX defect surfaced after v0.3.0a8 shipped — `kanon init . --profile max` against a project with a pre-existing 23-line AGENTS.md left the canonical agent boot doc untouched, with zero references to any of the depth-3 protocols the kit just scaffolded. `--force` is not required for any branch; init never destroys user-authored prose. Spec amendment in `docs/specs/cli.md` (new INV-cli-init-agents-md-merge).

## [0.3.0a8] — 2026-04-30

### Changed

- **`kanon init --profile full` renamed to `--profile all`**, and a new `--profile max` was added (per [ADR-0037](docs/decisions/0037-profile-rename-and-max.md)). `all` enables every kit-shipped aspect at its `default-depth` (every aspect at depth 1 today); `max` enables every aspect at the upper end of its `depth-range` (`kanon-sdd:3`, `kanon-release:2`, `kanon-testing:3`, `kanon-security:2`, `kanon-deps:2`, `kanon-worktrees:2`, `kanon-fidelity:1`). The rename addresses a UX defect surfaced after v0.3.0a7 shipped: users reading "full" naturally expected "every aspect cranked", but the actual behaviour was "every aspect at the kit's recommended starting depth". `solo` and `team` semantics are unchanged. Spec amendment in `docs/specs/cli.md` (new INV-cli-init-profile).

### Removed

- **`kanon init --profile full` is removed outright** (no deprecation alias — kanon has no public consumers yet). `--profile full` now exits with click's standard "invalid choice" error pointing at the four accepted values: `solo`, `team`, `all`, `max`.

## [0.3.0a7] — 2026-04-30

### Added

- **`kanon` brand banner** — emitted on `kanon init` and `kanon upgrade` (stderr only, suppressed automatically when stderr is not a TTY) and rendered at the top of scaffolded `AGENTS.md` inside a `<!-- kanon:begin:banner -->` marker block. Single source of truth (`src/kanon/_banner.py`) feeds all three surfaces; bytes are frozen and asserted by test. New `--quiet` / `-q` flag on both commands suppresses the banner regardless of TTY (and the trailing "Next steps" advisory on `init`).
- **Symlink/path-traversal protection** — new `_ensure_within()` helper validates that resolved paths stay inside the target directory before scaffold writes. Applied to `_write_config`, `_write_tree_atomically`, and `_migrate_flat_protocols`.
- **Security model section in README** — documents the trust boundary for `kanon preflight` and `kanon verify` code execution (repo write-access, same as Makefile/package.json scripts). References ADR-0036.
- **24 new tests** — validator error-branch tests, error-path tests for `_detect`, `_fidelity`, `_graph`, `_validators`, and 6 new e2e lifecycle tests (preflight, release, aspect set-config, aspect info, graph orphans, fidelity).

### Changed

- **`kanon release` gate lowered from depth 3 to depth 2** — depth 3 added zero files/protocols/sections over depth 2. The gate was an empty level; now `kanon release` works at depth 2 which provides the preflight script and release workflow.
- **CLI tagline aligned with README** — `kanon --help` now says "development-discipline kit" (was "SDD kit").
- **cli.py modularized** — extracted `_cli_helpers.py` (7 pure-logic functions), `_cli_aspect.py` (6 aspect-depth-engine functions), and moved 3 fidelity helpers to `_fidelity.py`. cli.py reduced from 1,589 to 1,084 lines (-32%).
- **test_cli.py split** — split into 5 focused files: `test_cli.py` (init/upgrade), `test_cli_aspect.py`, `test_cli_helpers.py`, `test_cli_verify.py`, `test_cli_fidelity.py`. Reduced from 2,978 to 1,129 lines (-62%).
- **Oversized functions extracted** — `parse_fixture` (178→108 lines), `init` (158→113 lines) via 5 new helper functions.
- **Silent exceptions surfaced in `_verify.py`** — two bare `except Exception: continue` blocks now capture and append warnings to the verify report.
- **Preflight spec/design promoted** from `status: draft` to `status: accepted`.

### Fixed

- **`kanon init` no longer crashes with raw traceback** on invalid paths — now shows `Error: Cannot create target directory: ...`.
- **README `tier set` description corrected** — was incorrectly described as sugar for `aspect set-depth sdd`; actually does a uniform raise across all default aspects (ADR-0035).
- **Broken doc link fixed** in `docs/design/aspect-model.md` (incorrect relative path to tier-up-advisor protocol).
- **Ruff I001 import-sort issue fixed** in `_banner.py`.
- **Validator `check()` functions** now have docstrings (6 validators).

### Changed

- **Secure-defaults protocol gains a same-repo config trust-boundary carve-out** (per [ADR-0036](docs/decisions/0036-secure-defaults-config-trust-carveout.md)). `subprocess.run(cmd, shell=True, ...)` is acceptable when `cmd` originates from a config file inside the running CLI's repo — the trust boundary is repo write-access. The kit-shipped `secure-defaults` § Injection paragraph spells the carve-out out so a future reader doesn't have to re-derive it. `src/kanon/_preflight.py:96` (the first lived call site) now carries a `# nosec` comment naming the ADR; refactoring to argv form was rejected because it would silently break consumer commands using shell features (`$VAR`, `&&`, pipes, redirection).
- **`docs/specs/scaffold-v2.md` promoted from `draft` to `accepted`.** INV-7 had two pre-acceptance defects fixed in the same commit: a self-referential rename (`docs/sdd-method.md is renamed to docs/sdd-method.md` → `docs/development-process.md is renamed to docs/sdd-method.md`, matching the v0.2.0a1 ship) and a stale line-count target (`~50` → `~85`, matching the post-trim file). Surfaced by the `spec-review` protocol applied during the audit closeout.

### Fixed

- **`ci/check_process_gates.py` is robust to developer `diff.external` settings.** The spec co-presence regex scans `git diff` output for `+`-prefixed lines; when a developer's global git config sets `diff.external` (e.g., `difft`, `delta`), those markers are stripped and the gate silently misses real violations. `_diff_content` now passes `--no-ext-diff` to both `git diff` invocations. CI was unaffected; this fix only matters for local pytest runs.

## [0.3.0a6] — 2026-04-29

### Added

- **Project-type auto-detection at init** — detects pyproject.toml, package.json, Cargo.toml, go.mod and pre-fills test/lint/typecheck/format commands. Preflight works on first commit with zero config.
- **Post-init preflight health check** — shows which preflight hooks are armed vs unconfigured with copy-pasteable fix commands.
- **Aspect descriptions in `kanon aspect list`** — one-liner per aspect from manifest `description:` field.
- **Self-check questions in AGENTS.md hard-gates** — forces trivial/non-trivial classification before every source-modifying tool call.
- **`kanon release` command** — gates tag creation on preflight checks (release depth 3).

### Changed

- **Default aspects** reduced from all 7 to 5 (sdd+testing+security+deps+worktrees). Release and fidelity are opt-in.
- **Profile names** renamed: lean→solo, standard→team.
- **Post-init hints** are now dynamic — only suggest aspects that aren't already enabled.
- **Aspect descriptions** moved from hardcoded Python map to manifest `description:` field.

### Fixed

- **Ruff line-length error** in tier help string (caused v0.3.0a4 CI failure).
- **Deps preflight hook** added at depth 2 (parity with security).

## [0.3.0a5] — 2026-04-29

### Added

- **`kanon release` command** — gates tag creation on preflight checks (release depth 3). Runs `kanon preflight --stage release`, creates annotated tag only if all checks pass. No version bump, no push — just the mechanical gate.

### Fixed

- **Ruff line-length error** in tier help string (caused v0.3.0a4 CI failure).

## [0.3.0a4] — 2026-04-29

### Added

- **`kanon tier set` now raises all aspects uniformly** — `kanon tier set . 2` raises every enabled aspect to at least depth 2 (ADR-0035).

### Fixed

- **Fidelity lock** regenerated after tier-uniform-raise spec/test changes.

### Changed

- **`--tier N` now applies a uniform aspect-depth raise** (ADR-0035). The flag iterates every aspect listed in the kit manifest's `defaults:` set and enables each at `min(N, aspect.max_depth)`. Previously, `--tier N` was sugar for `--aspects sdd:N` only.
- **`defaults:` widened to enumerate every shipped aspect.** `kanon init --tier 1` now scaffolds `sdd`, `worktrees`, `release`, `testing`, `security`, `deps`, and `fidelity` at depth 1 in the new project — not sdd alone. Strict superset of prior behaviour: existing `--tier 1` projects get more, never less. No-flag `kanon init` now also scaffolds the same default set.
- **`kanon tier set <target> N` is raise-only.** Aspects already at or above their per-aspect target depth (`min(N, max)`) are not lowered. The previous tier-down semantics (which printed "non-destructive") no longer apply: lowering targets are no-ops.
- **ADR-0006 (tier model semantics) and ADR-0008 (tier migration) marked superseded** by ADR-0035. Their bodies remain (immutable per protocol); their `status:` transitioned to `superseded` with `superseded-by: 0035`.

## [0.3.0a3] — 2026-04-29

### Changed

- **sdd-method.md trimmed from 458 to 87 lines** — content redistributed to artifact-directory READMEs (decisions, design, foundations, specs, plans). The method doc retains only the layer stack, routing paths, document authority, and glossary.

## [0.3.0a2] — 2026-04-28

### Added

- **`kanon preflight` command** — staged local validation that catches CI failures before pushing. Three stages (commit ⊂ push ⊂ release), each a strict superset. Runs `kanon verify` first, then consumer-configured checks (lint, tests, typecheck, security scan). Aspects contribute default checks via `preflight:` manifest entries.
- **Testing aspect config keys** — `test_cmd`, `lint_cmd`, `typecheck_cmd`, `format_cmd` for language-agnostic tool configuration.
- **Aspect-contributed preflight defaults** — testing, security, and release aspects declare what checks they contribute to which stages.
- **Dynamic hard-gates table** in AGENTS.md — only shows gates whose aspects are enabled at sufficient depth.

## [0.3.0a1] — 2026-04-28

### Added

- **Scaffold v2: three file categories** — kit-global files (always scaffolded), aspect-level files (scaffolded when aspect enabled at any depth), and depth-level files (existing). Top-level manifest gains `files:` key; aspect sub-manifests gain top-level `files:` key.
- **Scaffold v2: AGENTS.md routing index** — AGENTS.md shrinks from 411 to ~100 lines. Hard gates stay inline as a dynamic table; all discipline content moves to protocol files loaded on-demand. Marker sections eliminated (except protocols-index and hard-gates).
- **Scaffold v2: sdd fully optional** — any aspect including sdd can be completely disabled. `kanon init --aspects worktrees:1,testing:1` produces a valid project with zero sdd files. `kanon init --aspects ""` produces a bare project.
- **5 new protocol files** created from former AGENTS.md sections: `plan-before-build`, `spec-before-design`, `branch-hygiene`, `publishing-discipline`, `fidelity-discipline`.
- **`--harness` flag for `kanon init`** — auto-detects harness from existing dotdirs, defaults to CLAUDE.md only. Explicit `--harness cursor --harness kiro` for manual selection.
- **`--lite` flag for `kanon init`** — sugar for sdd at depth 0 (just AGENTS.md, no docs/).
- **`--profile` flag for `kanon init`** — preset aspect bundles: `lean` (sdd:1), `standard` (sdd+testing+security+deps), `full` (all aspects).
- **Actionable post-init message** with next-step commands and growth path.
- **ADR-0034** — routing-index AGENTS.md, refined enforcement proximity (supersedes ADR-0010 § enforcement-proximity).

### Changed

- **`docs/development-process.md` renamed to `docs/sdd-method.md`** — signals sdd ownership; not scaffolded when sdd is off.
- **`kanon-worktrees` dependency on sdd** demoted from `requires` to `suggests`.
- **`.kanon/kit.md` is now aspect-neutral** — no sdd-specific references; rendered from kit-global files.
- **`CLAUDE.md` removed from sdd depth-0** — it's a harness shim handled by `harnesses.yaml`.
- **Zero-aspect `kanon verify`** now warns instead of erroring.
- **Hard-gates table in AGENTS.md** is now dynamic — only shows gates whose aspects are enabled at sufficient depth.

### Removed

- **All `sections/` directories** across all aspects — content moved to protocol files.
- **All `agents-md/` body files** across all aspects — AGENTS.md is now a static routing template.

## [0.2.0a11] — 2026-04-28

### Added

- **Capability-neutral Task Playbook** in AGENTS.md — replaces the OMC-specific agent routing table with a phase-based playbook using generic capability profiles (planner, architect, debugger, etc.). Every harness matches what it has locally.
- **Merge-caution guidance** in worktree-lifecycle protocol § 5 — when integrating a worktree while others exist on disk, check for file overlap before merging.
- **`# nosec` inline suppression** in `check_security_patterns.py` — lines containing `# nosec` are skipped by the security scanner. Follows the Bandit convention.
- **9 missing CI scripts** added to `release.yml` — release workflow now runs the same checks as the PR workflow.

### Changed

- **`kanon upgrade` now re-renders harness shims** — previously only `init` rendered shims. Upgrade now refreshes all shims from the installed kit's templates, matching CLI spec INV-3.
- **Named extension-point convention** in `development-process.md` — the intro paragraph now names the `<project>-implementation.md` companion document convention explicitly.

### Fixed

- **CLI spec synced with actual surface** — added `set-config` to aspect group, added `graph` group (`orphans`, `rename`), and new INV-cli-graph-group invariant.
- **Verification-contract spec synced with implementation** — INV-1/2 updated from tier to aspect terminology, INV-3/7 clarified as CI-only checks, INV-4 depth corrected to ≥ 2, INV-8 output field corrected from `tier` to `aspects`.
- **12 plans and 7 specs** added to their respective README indexes.
- **Broken protocol path** in `aspect-model.md` corrected (`sdd/` → `kanon-sdd/`).
- **18 stale protocol/aspect paths** across 11 files corrected to use `kanon-` namespace prefix.
- **7 plans** given missing `status: done` frontmatter.
- **`check_test_quality.py`** no longer flags validator modules in `src/` as test files.
- **README** updated: added fidelity aspect to table, corrected version to v0.2.0a10, corrected aspect count to seven.
- **`kit-bundle.md` design doc** retired with tombstone pointing to `aspect-model.md`.
- **Fidelity lock** regenerated to match current spec SHAs.

## [0.2.0a10] — 2026-04-28

### Fixed

- **`kanon verify` now fully green at depth 3** — resolved all pre-existing errors and warnings.
- **Plan acceptance criteria** checked off in 5 completed plans that were triggering `plan-completion` validator errors.
- **Spec-design parity** — added `design:` frontmatter to all 22 accepted specs, referencing the governing ADR or companion design doc.
- **Fidelity lock** regenerated after spec frontmatter updates.
- **Lint fix** — renamed ambiguous variable `l` → `ln` in `check_process_gates.py`.

## [0.2.0a9] — 2026-04-28

### Added

- **Task-type triage table** in AGENTS.md — agents now read only what's relevant for their task type (bug fix, refactor, test, docs, CI), reducing effective boot chain load by 40–60% for non-feature work.
- **ADR category tags** — 33 ADRs in `docs/decisions/README.md` tagged by category (`cli`, `process`, `kit-internals`, `aspects`, `testing`, `release`) with a reading guide for targeted lookup.
- **Plan/src commit-separation warning** — `check_process_gates.py` now warns when a single commit touches both `docs/plans/` and `src/` files, detecting retroactive plan creation. Warning only (does not block); exemptable per-commit via `Trivial-change:` trailer.

### Changed

- **Spec gate broadened** — `check_process_gates.py` now catches all Click decorator registration patterns (`@main.command()`, `@aspect.command('list')`, `@click.group()`, etc.), not just `@cli.command()`. The previous regex was effectively a no-op for this project's actual CLI registration style.
- **Completion checklist streamlined** — N/A items can be dismissed in one line rather than justifying each sub-bullet individually.

### Fixed

- **7 CI scripts wired into `verify.yml`** — `check_test_quality`, `check_security_patterns`, `check_deps`, `check_status_consistency`, `check_verified_by`, and `check_invariant_ids` were never invoked by any GitHub Actions workflow despite AGENTS.md claiming they were active enforcement. Now wired with correct fail modes (3 hard-fail, 3 warn with `continue-on-error`).
- **Coverage floor aligned** — `.kanon/config.yaml` declared `coverage_floor: 80` but `pyproject.toml` enforced 90% via `--cov-fail-under`. Config updated to match the enforced value.
- **False documentation claims corrected** — removed incorrect "coverage floor" claim from `check_test_quality.py` description; replaced "no CI gate" with accurate description of the soft commit-message check.

## [0.2.0a8] — 2026-04-27

### Added

- **Kit-aspect validators — three built-in validators run from the installed kanon-kit package during `kanon verify`.** No static file copies in consumer repos; validators update with `pip install --upgrade`. Uses the same `check(target, errors, warnings)` signature as project-aspect validators. Three validators ship with `kanon-sdd`: `plan_completion` (done plans must have all tasks ticked, depth 1+), `link_check` (markdown relative links must resolve, depth 2+), `adr_immutability` (accepted ADR bodies are immutable, depth 2+). Kit-aspect manifests gain `validators:` entries at each depth level; `_manifest._aspect_depth_validators()` returns the depth-gated union; `_verify.run_kit_validators()` discovers and runs them after structural checks.
- **Index-consistency validator** (`kanon-sdd` depth 1+) — detects duplicate link-target entries in scaffolded index README files under `docs/{decisions,plans,specs,design}/`. Skips code blocks and handles missing directories at lower SDD depths.
- **Test-import-check validator** (`kanon-testing` depth 2+) — detects test files under `tests/ci/` referencing CI scripts that don't exist on disk. Catches orphaned test companions left behind after CI script deletion.
- **Quantitative fidelity assertion families** (`word_share`, `pattern_density`) and bracket turn markers (`[ACTOR]` style). `word_share` compares actor word-count share against a band; `pattern_density` counts regex matches per turn with optional code-fence stripping. Per [ADR-0033](docs/decisions/0033-fidelity-quantitative-families.md) and fidelity spec amendments.
- **Parallel worktree coordination** guidance added to `worktree-lifecycle` protocol — covers lock-file contention, shared-state awareness, and merge ordering.
- **Design-doc skip frontmatter convention** — plans may declare `design: "Follows ADR-NNNN"` to make a design-doc skip auditable. Added to `spec-before-design` AGENTS.md section.

### Changed

- **`worktree-setup.sh` hardened** — aborts on dirty working directory (uncommitted staged or unstaged changes), skips idempotently if worktree already exists, reuses existing branch instead of failing on `-b` conflict, and accepts multiple slug arguments.

### Fixed

- **`kanon verify` now adds the target directory to `sys.path`** before importing project-aspect validator modules, fixing `ModuleNotFoundError` when validators live in the consumer's tree.
- **`docs/development-process.md` no longer contains hardcoded `kanon-implementation.md` links** — the project-agnostic method doc now avoids kit-specific cross-references.

## [0.2.0a7] — 2026-04-27

### Added

- **ADR-immutability gate (kit-internal CI + consumer-facing protocol prose).** The kit's own CI now hard-fails on any post-acceptance ADR-body modification that is not (a) a frontmatter-only change, (b) an appended `## Historical Note` section, or (c) explicitly opted out via an `Allow-ADR-edit: NNNN — <reason>` commit-message trailer. Em-dash, en-dash, ASCII hyphen, or colon are all accepted as the trailer's separator before the reason. Multiple ADRs may be cited comma-separated. Two operating modes: PR mode walks every commit in `BASE..HEAD`; push mode (default) checks only `HEAD`. The gate ships at `ci/check_adr_immutability.py` (kit-internal — **not** scaffolded to consumers as part of any aspect's `files:` per ADR-0032's "consumer discipline ladder" stance), wired into `.github/workflows/verify.yml` (the `actions/checkout@v5` step bumps to `fetch-depth: 0` so PR-mode against `origin/<base>` works). Consumers wanting the same discipline get a new protocol at `.kanon/protocols/kanon-sdd/adr-immutability.md` shipped at `kanon-sdd` depth 3 listing several enforcement options (CI gate via copying the script, pre-commit hook, manual review checklist). `docs/development-process.md` § ADRs gains a paragraph naming the trailer's exact shape so authors find it without reading the ADR. Per [`docs/decisions/0032-adr-immutability-gate.md`](docs/decisions/0032-adr-immutability-gate.md). Track 2 of [`docs/plans/fidelity-and-immutability.md`](docs/plans/fidelity-and-immutability.md).
- **`kanon-fidelity` aspect — Tier-1 behavioural-conformance verification.** New experimental aspect (depth-range `[0, 1]`, default depth 1) that closes the loop the verification-contract carve-out (INV-10, ADR-0029) opened: when enabled, `kanon verify` evaluates lexical fixtures against committed agent transcripts, catching the class of prose-conformance failures structural verify cannot see. Three regex-based assertion families operate over named-actor turns extracted from `.kanon/fidelity/<protocol>.dogfood.md` capture files: `forbidden_phrases` (any match fails), `required_one_of` (at least one must match), `required_all_of` (every regex must match somewhere). Aspect declares `provides: [behavioural-verification]` per ADR-0026, so a `project-fidelity-*` aspect can substitute. Engine in `src/kanon/_fidelity.py` (~250 LOC, text-only — no subprocess, no LLM, no test-runner per spec INV-7); integrated into `kanon verify` via `_verify.check_fidelity_assertions`, gated on the capability. Ships one exemplar fixture (`.kanon/fidelity/worktree-lifecycle.{md,dogfood.md}`) verifying the kit's own worktree audit-sentence rule. Tier-2 (workstation `kanon transcripts capture`) and Tier-3 (paid live-LLM nightly) are explicitly out of scope and require their own ADRs. Per [`docs/specs/fidelity.md`](docs/specs/fidelity.md) and [ADR-0031](docs/decisions/0031-fidelity-aspect.md). Track 1 of [`docs/plans/fidelity-and-immutability.md`](docs/plans/fidelity-and-immutability.md).
- **Project-aspect validators-as-extensions (Phase 4).** A project-aspect's `manifest.yaml` may now declare a `validators: [<dotted.module.path>, ...]` list. During `kanon verify`, each declared module is imported in-process via `importlib.import_module`, and its `check(target, errors, warnings) -> None` entrypoint is invoked. Findings flow into the same JSON report the kit's structural checks populate. Per project-aspects spec INV-9 (validator non-overriding), kit structural checks run AFTER project-validators, so any `errors.clear()` from a hostile validator is overwritten by the kit's appends. Import failures (`ModuleNotFoundError`), missing entrypoints, and exceptions raised inside `check()` are all recorded as errors and verify continues with the remaining checks. The trust boundary is in-process and documented; subprocess sandboxing is out of scope for v0.3 (a future spec may revisit if a real consumer demands it). Per [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md) INV-7/9 and [ADR-0028](docs/decisions/0028-project-aspects.md). Phase 4 of 5 — Phase 5 (spec promotion + docs polish) follows.
- **Project-defined aspects (Phase 3 — discovery + runtime exclusivity).** Consumers may now declare their own aspects under `.kanon/aspects/project-<local>/manifest.yaml`; the CLI discovers them transparently and they participate in `aspect list --target`, `aspect info <name> --target`, `aspect add`, `aspect remove`, `aspect set-depth`, `aspect set-config`, and `verify` alongside kit-shipped aspects. New `kanon._manifest._discover_project_aspects(target)` walks the consumer directory, validates registry-required fields (`stability`, `depth-range`, `default-depth`, optional `requires`/`provides`), and rejects directories whose name is not in the `project-` namespace per ADR-0028 / spec INV-4. New `_load_aspect_registry(target)` returns the unified kit + project registry and sets a process-global overlay so the existing `_aspect_*` helpers see project-aspects without parameter-threading. The cross-source path-collision check (previously CI-only) lifts into `_build_bundle` runtime: a project-aspect that scaffolds the same consumer-relative file path as a kit-aspect raises `ClickException` naming both aspects and the path. Capability substitutability (ADR-0026) is source-neutral: a project-aspect's `provides:` capability satisfies a kit-aspect's 1-token capability `requires:` predicate. Per [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md) and [ADR-0028](docs/decisions/0028-project-aspects.md). Phase 3 of 5 — Phase 4 (in-process validator extension) and Phase 5 (spec promotion + docs polish) follow.
- **`kanon graph orphans`** — read-only report listing principles, personas, specs, and capabilities with no inbound edges in the cross-link graph. Supports `--type <namespace>` to filter and `--format json|text` (default text). Per [`docs/specs/spec-graph-orphans.md`](docs/specs/spec-graph-orphans.md): deferred and superseded specs are excluded both as inbound-edge sources and as orphan candidates; nodes may opt out via `orphan-exempt: true` paired with a required `orphan-exempt-reason:`. The command always exits 0 — orphans are informational, not errors. Underlying primitive (`src/kanon/_graph.py`) is shared with the in-flight `kanon graph rename` command. `ci/check_foundations.py` now validates the `orphan-exempt:` / `orphan-exempt-reason:` pairing rule.

### Changed

- **The kit-shipped `docs/foundations/principles/README.md` (consumer-facing starter template) now states explicitly that the directory belongs to the consumer's project and that kanon's own kit-author principles (`P-prose-is-code`, `P-tiers-insulate`, `P-self-hosted-bootstrap`, etc.) are *not* scaffolded into consumer trees.** The pre-existing kit behaviour was already correct — only the empty `README.md` ships at `kanon-sdd:3`, never the kanon-internal `P-*.md` files — but the README itself did not say so, and the absence of an explicit statement led the v0.3 round-2 review to reason about a "principle override mechanism" for a propagation that does not happen. Kanon's own `docs/foundations/principles/README.md` (kit-author internal catalog) gains a parallel one-line note pointing at the kit-shipped starter and confirming that consumers do not receive the kanon-internal `P-*.md` files. No new aspect, no new validator, no new ADR. Per [`docs/plans/principles-clarification.md`](docs/plans/principles-clarification.md); supersedes Track 3 of [`docs/plans/fidelity-and-immutability.md`](docs/plans/fidelity-and-immutability.md).
- **`docs/specs/verification-contract.md` gains INV-10 — a narrowly-scoped carve-out from INV-9's "does not execute code" rule that authorises lexical replay of `.kanon/fidelity/<protocol>.dogfood.md` capture files when an aspect declaring the `behavioural-verification` capability (per ADR-0026) is enabled at depth ≥ 1.** The carve-out is text-only (no LLM calls, no subprocesses, no test-runner invocation), read-only against committed files, and aspect-gated — bare `kanon verify` on a project without the aspect is structural-only as before. Tier-2 (workstation `kanon transcripts capture`) and Tier-3 (paid live-LLM nightly) are explicitly out of scope for this carve-out and require their own ADRs. Ratified by [ADR-0029](docs/decisions/0029-verification-fidelity-replay-carveout.md). The kit-shipped `kanon-fidelity` aspect that consumes this capability lands in a subsequent PR (Track 1 of [`docs/plans/fidelity-and-immutability.md`](docs/plans/fidelity-and-immutability.md)).
- **Aspect names now carry a source namespace prefix (`kanon-` for kit-shipped, `project-` reserved for consumer-defined; ADR-0028).** All six kit-shipped aspects rename: `sdd` → `kanon-sdd`, `worktrees` → `kanon-worktrees`, `release` → `kanon-release`, `testing` → `kanon-testing`, `security` → `kanon-security`, `deps` → `kanon-deps`. Bare names at every CLI input surface (`--aspects`, `aspect set-depth`, `aspect add`/`remove`/`set-config`/`info`, `requires:` predicates) sugar to the `kanon-` namespace, so existing invocations continue to work unchanged. Capability names (`provides:` / 1-token `requires:`) are unaffected — they remain an abstract substitutability namespace. The `.kanon/config.yaml` schema bumps from v2 (bare keys) to v3 (`kanon-` prefixed keys); first `kanon upgrade` after this lands auto-migrates the config, AGENTS.md markers, and `.kanon/protocols/<bare>/` → `kanon-<bare>/` directories one-way and idempotently. `ci/check_kit_consistency.py` hard-fails when a kit-side aspect carries a non-`kanon-` name. Per [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md), [`docs/plans/project-aspects.md`](docs/plans/project-aspects.md), and [ADR-0028](docs/decisions/0028-project-aspects.md). Phase 1 of 5 — discovery of project-aspects under `.kanon/aspects/` and the in-process validator extension surface arrive in subsequent PRs.
- **Kit-shipped reference release workflow** (`src/kanon/kit/aspects/release/files/.github/workflows/release.yml`) now uses Node-24-compatible action majors: `actions/checkout@v5` and `actions/setup-python@v6`. New consumers enabling the `release` aspect at depth 2 inherit the bumped versions; existing consumers can refresh by re-running `kanon upgrade` (or apply the bump manually). The repo's own workflows were already bumped in v0.2.0a6 (PRs #10, #12); this aligns the consumer-facing template.

### Fixed

- **Review-followups batch 1 — closes four documented-but-not-delivered gaps surfaced by the v1-readiness review.** (a) `_check_pending_recovery` now auto-recovers an interrupted `kanon graph rename` by replaying the ops-manifest via `kanon._rename.recover_pending_rename`; the user sees `Recovered interrupted 'graph-rename' operation by replaying the ops-manifest.` instead of the warn-and-rerun message. Per [ADR-0030](docs/decisions/0030-recovery-model.md), which amends ADR-0024 §Consequences and ratifies the hybrid model (graph-rename auto-replays; other sentinels rely on idempotent re-run because their commands are already idempotent). (b) The kit-testing aspect's `coverage_floor` config-schema entry is now documented as **advisory** metadata: the kit declares the value but does not auto-wire it into a test runner; consumers feed it into their own CI (`pytest --cov-fail-under=$VALUE` or equivalent). The test-discipline AGENTS.md section text is amended accordingly. (c) `src/kanon/kit/kit.md` line 7 — `**Tier:** ${sdd_depth}` → `**SDD depth:** ${sdd_depth}` (vocabulary residue from before ADR-0012 introduced the aspect-depth model). (d) Capability-presence resolution rule's depth-0 corner case is now explicit in `docs/specs/aspect-provides.md` (INV-resolution): a depth-0 supplier does not satisfy a capability `requires:` predicate; depth ≥ 1 is required. Same clarification added to the `_check_requires` docstring in `src/kanon/cli.py`.
- **`_migrate_legacy_config` hard-fails on mixed-state v2/v3 aspect keys.** A consumer config that contains both a bare aspect key (`sdd`) and the namespaced equivalent (`kanon-sdd`) now raises a `ClickException` listing every collision and asking the user to deduplicate manually. Previously the bare key would silently overwrite the namespaced entry under last-wins ordering. Per [`docs/specs/project-aspects.md`](docs/specs/project-aspects.md) and [`docs/plans/project-aspects.md`](docs/plans/project-aspects.md) (Phase 2 / T17 mixed-state defence).
- **Recovery warning after an interrupted operation now suggests the correct user-facing command.** Previously, if a `.kanon/.pending` sentinel was found from an interrupted `aspect set-depth` / `aspect set-config` / `aspect remove` / `fidelity update`, the warning suggested invalid forms like `kanon set-depth` or `kanon aspect-remove`. The recovery message now consults a single source-of-truth mapping (`_PENDING_OP_TO_COMMAND` in `src/kanon/cli.py`) and produces the correct sub-group form (e.g., `kanon aspect remove`, with a space). Internal sentinel operation strings are now named constants (`_OP_INIT`, `_OP_UPGRADE`, `_OP_SET_DEPTH`, `_OP_SET_CONFIG`, `_OP_ASPECT_REMOVE`, `_OP_FIDELITY_UPDATE`) — no more free-form string literals at `write_sentinel(...)` callsites.

## [0.2.0a6] — 2026-04-25

### Added

- **Aspect capability registry — `provides:` and generalised `requires:`.** Each top-level aspect entry in `src/kanon/kit/manifest.yaml` may now declare `provides: [<capability>, ...]`. The existing `requires:` field accepts two forms in the same list: depth predicates (`"sdd >= 1"`, semantics unchanged) or capability presence (`"planning-discipline"`, satisfied iff at least one enabled aspect declares the capability in its `provides:`). The token-count discriminator routes parsing unambiguously; no existing predicate changes meaning. All six shipped aspects now declare a capability — `sdd: planning-discipline, spec-discipline`; `worktrees: worktree-isolation`; `release: release-discipline`; `testing: test-discipline`; `security: security-discipline`; `deps: dependency-hygiene`. `kanon aspect info` surfaces the new `Provides:` line. `ci/check_kit_consistency.py` hard-fails on dangling capability-presence predicates. See [ADR-0026](docs/decisions/0026-aspect-provides-and-generalised-requires.md) and [`docs/specs/aspect-provides.md`](docs/specs/aspect-provides.md).
- **`kanon aspect set-config <target> <name> <key>=<value>`** — set one config value on an enabled aspect. Each invocation sets exactly one key; the command is idempotent. Value is parsed as a YAML scalar (e.g., `coverage_floor=80` stores `80` as int; `flag=true` stores `True` as bool). Lists and mappings are rejected — hand-edit `.kanon/config.yaml` for structured values. Atomic write under the standard `.kanon/.pending` sentinel (ADR-0024).
- **`--config <key>=<value>` (repeatable) on `kanon aspect add`** — populate aspect-config keys at enable time. Same parsing rules as `set-config`.
- **Optional `config-schema:` per aspect** — aspects may now declare a typed config schema in their sub-manifest (`src/kanon/kit/aspects/<name>/manifest.yaml`). When present, `set-config` and `--config` reject unknown keys and type mismatches. Permitted `type:` values: `string`, `integer`, `boolean`, `number`. The `testing` aspect declares `coverage_floor: integer` as the first lived example.
- **`kanon aspect info` surfaces the schema** — when an aspect declares a `config-schema:` block, `aspect info <name>` prints each key with its type, default (when set), and description (when set). See [ADR-0025](docs/decisions/0025-aspect-config-parsing.md) and [`docs/specs/aspect-config.md`](docs/specs/aspect-config.md).

### Fixed

- **AGENTS.md marker matching is now line-anchored and fenced-block-aware.** Quoting a `<!-- kanon:begin:... -->` or `<!-- kanon:end:... -->` marker inside user prose, an inline-code span, a blockquote, or a fenced code block (``` or `~~~`) no longer risks corruption on `kanon upgrade` or `kanon aspect set-depth`. The matcher requires the marker to occupy a line by itself (leading or trailing tabs/spaces tolerated). Behaviour for well-formed kit markers is unchanged. The same matcher now backs `_scaffold` merge logic, `kanon verify`'s marker-balance check, and `ci/check_kit_consistency.py`.
- **`ci/check_deps.py` no longer false-positives on `requires-python`.** The pyproject scanner used to flip `in_deps` on the `[project]` section header itself, so any scalar field whose value started with a range operator — most commonly `requires-python = ">=3.10"` — was reported as an unpinned dependency. The state machine now activates only inside `<name> = [...]` arrays (covering `dependencies` and the `[project.optional-dependencies]` group bodies). Same fix applied to the consumer-facing copy at `src/kanon/kit/aspects/deps/files/ci/check_deps.py` (byte-equality preserved).
- **`ci/check_test_quality.py` no longer walks `.venv/` and other vendored directories.** A `_SKIP_DIRS` set (mirrored from `check_deps.py`: `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`) now filters `_find_test_files`. Pre-fix runs reported 11 spurious "test file with zero test functions" warnings on `.venv/lib/.../mypy*` files. Same fix applied to the consumer-facing copy at `src/kanon/kit/aspects/testing/files/ci/check_test_quality.py`.
- **`ci/check_package_contents.py` docstring** no longer references nonexistent specs (`docs/specs/release-process.md`, `docs/specs/release-communication.md`) or sibling-project symbols (`sensei/__init__.py.__version__`, `prompts/`/`schemas/`/`profiles/`). Rewritten to describe what the validator actually asserts about a kanon-kit wheel.
- **`tests/test_e2e_installed.py::test_installed_worktrees_aspect`** now exercises `verify` directly at `worktrees=2` instead of pre-demoting to depth 0; the original hedge was stale (matched the in-process lifecycle test which has been passing at depth 2 since the cross-aspect injection fix).

### Changed

- **kanon is now declared POSIX-only** (Linux, macOS); Windows support is not promised. `pyproject.toml` carries explicit `Operating System :: POSIX/Linux/MacOS` classifiers; `README.md` quickstart documents the constraint; `docs/specs/cli.md` adds an `INV-cli-posix-only` invariant; `tests/test_atomic.py::test_fsyncs_parent_directory` no longer carries a non-POSIX skip.

### Fixed

- **`kanon upgrade` re-renders AGENTS.md marker sections** even when `kit_version` is unchanged, healing hand-edited or accidentally clobbered marker bodies. User content outside markers is untouched. The `aspects.<name>.enabled_at` timestamp is no longer rewritten on a no-op upgrade (`_write_config` and the `Upgraded ... → ...` echo are gated on a real version change).
- **`kanon verify` now warns (does not fail) on config-named aspects absent from the installed kit**, matching `docs/specs/aspects.md` invariant 4. The verify report's human-readable tail gains a `warnings:` block when warnings are present. Out-of-range depth on a *known* aspect remains a hard failure.

## [0.2.0a5] — 2026-04-24

### Added

- **Testing aspect** (`stability: experimental`, depth 0–3) — test discipline, AC-first TDD, automated enforcement. Language-agnostic. First aspect to use `config:` block (`coverage_floor`) and `suggests:` field.
- **Security aspect** (`stability: experimental`, depth 0–2) — secure-by-default discipline: no hardcoded secrets, parameterized queries, input validation, least-privilege. CI pattern scanner at depth 2.
- **Deps aspect** (`stability: experimental`, depth 0–2) — dependency hygiene: pin versions, check before adding, justify additions. CI validator at depth 2.
- **Invariant IDs** — 102 `INV-*` anchors across 13 specs. CI validator (`ci/check_invariant_ids.py`) enforces uniqueness and cross-reference resolution.
- **Verified-by** — `invariant_coverage:` frontmatter mapping in specs linking invariants to tests. CI validator (`ci/check_verified_by.py`).
- **Fidelity lock Phase 1 + 2** — `.kanon/fidelity.lock` tracks spec-SHA and fixture-SHA. `kanon fidelity update` generates the lock. `kanon verify` warns on drift at depth ≥ 2.
- **`scope-check` protocol** (sdd, depth 1) — fires when agent discovers work outside the approved plan.
- **`error-diagnosis` protocol** (testing, depth 1) — structured debugging: reproduce → hypothesize → fix root cause.
- **`completion-checklist` protocol** (sdd, depth 1) — 7-item checklist before declaring work complete.
- **Documentation Impact section** in plan template — plans must list which docs need updating.

### Changed

- **Aspect decoupling** (7 phases) — AGENTS.md base template is aspect-neutral, `kanon init --aspects` flag, `kanon aspect add/remove` commands, `requires:` enforcement, generic `${sdd_depth}` placeholders, manifest-driven CI.
- **Spec template** updated with `INV-*` anchor convention.

## [0.2.0a4] — 2026-04-24

### Added

- **`kanon aspect add` / `kanon aspect remove`** — new CLI commands for adding and removing aspects. `add` enables at default depth with dependency enforcement. `remove` deletes config entry and AGENTS.md markers, leaves files on disk (non-destructive).
- **`kanon init --aspects`** — new flag accepting comma-separated `name:depth` pairs (e.g., `--aspects sdd:1,worktrees:2`). `--tier N` preserved as sugar for `--aspects sdd:N`. When neither flag is provided, defaults read from manifest.
- **`requires:` enforcement** — aspect dependency predicates (e.g., `"sdd >= 1"`) are now checked at runtime in `aspect add`, `aspect remove`, and `aspect set-depth`.

### Changed

- **Aspect-neutral AGENTS.md base template** — `src/kanon/kit/agents-md-base.md` replaces sdd-owned depth templates as the document skeleton. Each aspect injects its body content via markers. No aspect owns the skeleton.
- **Generic placeholders** — `${sdd_depth}` replaces `${tier}` in kit templates. Generic vocabulary: `${project_name}`, `${<aspect>_depth}`. `${tier}` preserved as backward-compat alias.
- **Manifest-driven CI** — `check_package_contents.py` and `check_kit_consistency.py` read from YAML manifests instead of hardcoding sdd file paths. Per-aspect `byte-equality:` key in sub-manifests replaces the hardcoded whitelist.
- **`defaults:` manifest key** — top-level `manifest.yaml` declares default aspects for `kanon init` when no flags are provided.

## [0.2.0a3] — 2026-04-24

### Added

- **Worktrees aspect** (`stability: experimental`, depth 0–2) — isolated parallel execution via git worktrees. Depth 1 ships prose guidance (protocol + AGENTS.md section); depth 2 adds shell helper scripts. See [ADR-0014](docs/decisions/0014-worktrees-aspect.md) and [spec](docs/specs/worktrees.md).
- **True E2E tests** — subprocess-based tests that build the wheel, install in an isolated venv, and run `kanon` as a real CLI. Run with `pytest -m e2e`.
- **E2E lifecycle tests** — multi-step integration tests chaining init → tier set → upgrade → verify → aspect set-depth.
- **CI script tests** — test coverage for `check_foundations.py`, `check_links.py`, `check_package_contents.py`.

### Changed

- **cli.py decomposed** into three modules: `_manifest.py` (kit manifest loading), `_scaffold.py` (AGENTS.md assembly, config I/O), `cli.py` (click commands). No public API change.
- **Vision doc updated** (ADR-0015) — "Tiered" property replaced with "Aspect-oriented"; success criteria split into v0.1 (achieved) and v0.2 (in progress).
- **README rewritten** around the aspect model — aspects as primary concept, worktrees documented, Codex removed from harness list.
- **AGENTS.md updated** — project layout reflects decomposed modules, tier language replaced with aspect/depth language throughout.
- **Kit templates updated** — all sdd depth templates, kit.md, and tier-up-advisor protocol use aspect/depth language instead of tier language.
- **Coverage floor raised** from 70% to 90% (actual: 95.6%, 163 tests).

### Fixed

- **Cross-aspect section injection** — `_assemble_agents_md()` now calls `_insert_section()` for markers that don't exist in the base template, fixing silent data loss when adding non-sdd aspects.
- **Dead code removed** — `_fsync_dir` function and unused `os` import.

## [0.2.0a2] — 2026-04-23

### Changed

- **PyPI distribution name** is now published correctly as `kanon-kit` (the short name `kanon` was unavailable on PyPI). The CLI entry point and import path remain `kanon`. `pipx install kanon-kit` is the install command from 0.2.0a2 onward.

### Notes

- 0.2.0a1 was published on PyPI with the same source tree as this release. 0.2.0a2 is a minimal version roll to exercise the now-working release pipeline end-to-end (the 0.2.0a1 publish job succeeded on retry but several earlier tag-move iterations failed against the registry during initial trusted-publisher configuration).

## [0.2.0a1] — 2026-04-23

### Added

- **Aspect model** — aspects are first-class opt-in discipline units per ADR-0012 + ADR-0013. SDD becomes the first shipping aspect (`sdd`); the kit gains a `kanon aspect` subgroup (`list`, `info`, `set-depth`); per-aspect opt-in recorded in `.kanon/config.yaml`. See [`docs/specs/aspects.md`](docs/specs/aspects.md) and [`docs/design/aspect-model.md`](docs/design/aspect-model.md).
- **`solo-with-agents` persona** — kanon's agent-first default user (one human, N concurrent LLM agents). See [`docs/foundations/personas/solo-with-agents.md`](docs/foundations/personas/solo-with-agents.md).
- **Namespaced protocols and AGENTS.md markers** — protocols live at `.kanon/protocols/<aspect>/<name>.md`; AGENTS.md marker sections use `<!-- kanon:begin:<aspect>/<section> -->` with `protocols-index` unprefixed as the cross-aspect catalog.
- **Protocol layer** at `.kanon/protocols/` — three prose-as-code judgment procedures scaffolded into consumer repos (under the `sdd/` namespace in the v0.2 layout):
  - `tier-up-advisor.md` (depth-min 1): signals collection → per-depth fit → tiebreaker ("prefer lower when in doubt; tier-up is cheap") → recommendation with rationale → halt if inconsistent with user intent.
  - `verify-triage.md` (depth-min 1): parse `kanon verify` JSON report → classify → prioritization tree → propose fix with confidence level → never mutate without approval.
  - `spec-review.md` (depth-min 2): structural checks → invariant falsifiability → ambiguity pass → steelman → three-tier feedback → readiness verdict.
  - See [docs/specs/protocols.md](docs/specs/protocols.md) and [ADR-0010](docs/decisions/0010-protocol-layer.md).
- **AGENTS.md marker section `protocols-index`** — unified cross-aspect table listing every active protocol grouped by aspect with name, depth-min, and invoke-when trigger. Regenerated dynamically at init/upgrade/set-depth.
- **Kit kernel doc** at `.kanon/kit.md` — scaffolded at every depth. Describes tier identity, boot chain, rules in force, protocol catalog, and migration pointer.
- **Reference automation snippets** carve-out in vision non-goals per ADR-0013 — aspects with cryptographic, irreversible, or stateful tails may ship CI templates (GitHub Actions YAML, pre-commit configs, Makefile targets) the consumer executes. Agent-behavior gating stays strictly prose-only.
- **80 total tests** (up from 41 at v0.1.0a1) covering the aspect model, the protocol layer, kit.md scaffolding, manifest resolution, tier-migration round-trip, and legacy-config auto-migration.

### Changed

- **Kit layout restructured** from `src/kanon/kit/{agents-md,sections,protocols,files}/` to `src/kanon/kit/aspects/sdd/{agents-md,sections,protocols,files}/` per ADR-0012. Top-level `src/kanon/kit/manifest.yaml` is now an aspect registry (`aspects: {sdd: {...}}`); per-aspect content moves into `aspects/sdd/manifest.yaml`. Strict-superset `depth-0..depth-3` replaces `tier-0..tier-3`; `tier-N.md` → `depth-N.md`.
- **`.kanon/config.yaml` schema v2** — `aspects: {name: {depth, enabled_at, config}}` replaces top-level `tier:` + `tier_set_at:`. Auto-migration runs transparently on first `kanon upgrade`.
- **Protocol frontmatter** — `tier-min:` → `depth-min:`.
- **CLI** — generalised to iterate aspects; `kanon init --tier N` and `kanon tier set <target> <N>` preserved as backwards-compat sugar routing to the `sdd` aspect.
- **Protocols spec** (`docs/specs/protocols.md`) — invariants carry aspect-prefix clauses for the namespaced layout.
- **Vision** (`docs/foundations/vision.md`) — § Non-Goals item #2 narrowed in place per ADR-0013; ADR-0013 is the archaeological trail for the wording change.
- **Initial pre-v0.2 kit-refactor work**: `src/kanon/templates/` → `src/kanon/kit/` with a manifest-driven layout per ADR-0011 (~4× duplication of shared files eliminated; byte-equality enforcement narrowed to a whitelist; hardcoded `_TIER_FILES` / `_TIER_SECTIONS` dicts gone).
- **CI validator renamed and rewritten**: `ci/check_template_consistency.py` → `ci/check_kit_consistency.py`. Walks aspect registry + per-aspect sub-manifests; enforces cross-aspect file-ownership exclusivity; per-aspect byte-equality whitelist; namespace discipline on marker sections.
- **Design doc renamed**: `docs/design/template-bundle.md` → `docs/design/kit-bundle.md`; new `docs/design/aspect-model.md` added for the aspect layer.

### Migration (from v0.1.0a1)

- **v1 config → v2**: `kanon upgrade` auto-migrates `tier: N` + `tier_set_at:` to `aspects: {sdd: {depth: N, enabled_at: ..., config: {}}}`. One-way; older kanon CLIs cannot parse v2 config.
- **Flat protocols → namespaced**: `kanon upgrade` relocates `.kanon/protocols/*.md` under `.kanon/protocols/kanon-sdd/`.
- **AGENTS.md markers**: unprefixed v1 markers (`plan-before-build`, `spec-before-design`) are rewritten to namespaced v2 form (`sdd/plan-before-build`, `sdd/spec-before-design`) during `upgrade`. `protocols-index` stays unprefixed (cross-aspect).

## [0.1.0a1] — 2026-04-22

First public alpha under the name `kanon`. The project was previously developed internally under the name `agent-sdd`; per ADR-0009, the rename happened before first external release. Architecture-validation release — the kit works end-to-end for the author's company's future projects; public adoption is not yet a goal.

### Added

- **Repo skeleton** at tier-3 self-hosting: `AGENTS.md` with HTML-comment-delimited kit-managed sections, `CLAUDE.md` shim, `docs/development-process.md` (project-agnostic SDD method, ported from the Sensei reference implementation), Apache-2.0 `LICENSE`, `pyproject.toml`, `README.md`.
- **Foundations** — six principles (prose-is-code, specs-are-source, tiers-insulate, self-hosted-bootstrap, cross-link-dont-duplicate, verification-co-authored) and three personas (solo-engineer, platform-team, onboarding-agent).
- **Six core specs** — cli, template-bundle, cross-harness-shims, tiers, tier-migration, verification-contract.
- **Six deferred specs** (status: deferred) for v0.2+ capabilities: fidelity-lock, spec-graph-tooling, ambiguity-budget, multi-agent-coordination, expand-and-contract-lifecycle, invariant-ids. Indexed from `docs/plans/roadmap.md`.
- **Design doc** — `docs/design/template-bundle.md` covering the four-tier bundle construction.
- **Eight critical ADRs**:
  - 0001 Distribution as pip package.
  - 0002 Self-hosted bootstrap — commits 1–3 are pre-SDD.
  - 0003 AGENTS.md as canonical root; shims are pointers.
  - 0004 Verification is a co-authoritative source, not compiled output.
  - 0005 Model-version compatibility contract (`validated-against:`).
  - 0006 Tier model semantics.
  - 0007 Status taxonomy — adds `deferred` as a first-class value.
  - 0008 Tier migration is mutable, idempotent, non-destructive.
- **CLI** — `kanon init|upgrade|verify|tier|--version`.
  - `init <target> --tier {0,1,2,3}` scaffolds any tier with cross-harness shims and atomic writes.
  - `tier set <target> <N>` migrates between any two tiers: additive tier-up, non-destructive tier-down, AGENTS.md marker-delimited rewrite never touching user content outside markers.
  - `upgrade` refreshes the kit-managed AGENTS.md sections and `.kanon/config.yaml`.
  - `verify` validates a consumer project against its declared tier.
- **Four tier templates** at `src/kanon/templates/tier-{0,1,2,3}/`. Tier-3 shares source of truth (byte-equality) with the kit's own `docs/` and `AGENTS.md` marker sections — CI enforces this via `check_template_consistency.py`.
- **Cross-harness shim registry** at `src/kanon/templates/harnesses.yaml` covering Claude Code, Kiro, Cursor, GitHub Copilot, Windsurf, Cline, Roo Code, and JetBrains AI. Pointers only, never duplicates.
- **Four CI validators** — `check_foundations.py`, `check_links.py`, `check_package_contents.py` (ported from Sensei), and `check_template_consistency.py` (new: enforces byte-equality between repo canonical artifacts and tier-3 template).
- **39-test pytest suite** — atomic-write, CLI happy/unhappy paths, tier-migration round-trips (0→1→2→3→2→1→0 and arbitrary hops preserving user-authored files), template integrity across all four tiers. Coverage 77% (floor 70% for v0.1; will ratchet upward).
- **GitHub Actions** — `verify.yml` (py3.10-3.13 matrix, ruff, mypy --strict, all four validators) and `release.yml` (tag-triggered, OIDC trusted publishing, human-approval gate via `pypi` environment).
- **Self-hosting property.** This repo itself is a tier-3 `kanon` project. `kanon verify .` against the repo returns `status: ok`.

### Known limitations

- Python tests can't be mechanically derived from specs (addressed by ADR-0004 — tests are a co-authoritative source alongside specs).
- `kanon verify` emits warning-level (not hard-fail) signals for model-version compatibility per ADR-0005. Automated fixture re-running is deferred to v0.3+.
- Spec-graph tooling (rename, orphan detection, spec-diff rendering) is deferred to v0.2. See `docs/specs/spec-graph-tooling.md`.
- Multi-agent coordination primitives (reservations ledger, plan-SHA pins, decision handshake) deferred to v0.2. See `docs/specs/multi-agent-coordination.md`.

[Unreleased]: https://github.com/altakleos/kanon/compare/v0.3.0a9...HEAD
[0.3.0a9]: https://github.com/altakleos/kanon/compare/v0.3.0a8...v0.3.0a9
[0.3.0a8]: https://github.com/altakleos/kanon/compare/v0.3.0a7...v0.3.0a8
[0.3.0a7]: https://github.com/altakleos/kanon/compare/v0.3.0a6...v0.3.0a7
[0.3.0a6]: https://github.com/altakleos/kanon/compare/v0.3.0a5...v0.3.0a6
[0.3.0a5]: https://github.com/altakleos/kanon/compare/v0.3.0a4...v0.3.0a5
[0.3.0a4]: https://github.com/altakleos/kanon/compare/v0.3.0a3...v0.3.0a4
[0.3.0a3]: https://github.com/altakleos/kanon/compare/v0.3.0a2...v0.3.0a3
[0.3.0a2]: https://github.com/altakleos/kanon/compare/v0.3.0a1...v0.3.0a2
[0.3.0a1]: https://github.com/altakleos/kanon/compare/v0.2.0a11...v0.3.0a1
[0.2.0a11]: https://github.com/altakleos/kanon/compare/v0.2.0a10...v0.2.0a11
[0.2.0a10]: https://github.com/altakleos/kanon/compare/v0.2.0a9...v0.2.0a10
[0.2.0a9]: https://github.com/altakleos/kanon/compare/v0.2.0a8...v0.2.0a9
[0.2.0a8]: https://github.com/altakleos/kanon/compare/v0.2.0a7...v0.2.0a8
[0.2.0a7]: https://github.com/altakleos/kanon/compare/v0.2.0a6...v0.2.0a7
[0.2.0a6]: https://github.com/altakleos/kanon/compare/v0.2.0a5...v0.2.0a6
[0.2.0a5]: https://github.com/altakleos/kanon/compare/v0.2.0a4...v0.2.0a5
[0.2.0a4]: https://github.com/altakleos/kanon/compare/v0.2.0a3...v0.2.0a4
[0.2.0a3]: https://github.com/altakleos/kanon/compare/v0.2.0a2...v0.2.0a3
[0.2.0a2]: https://github.com/altakleos/kanon/releases/tag/v0.2.0a2
[0.2.0a1]: https://github.com/altakleos/kanon/releases/tag/v0.2.0a1
[0.1.0a1]: https://github.com/makutaku/kanon/releases/tag/v0.1.0a1
<!-- v0.1.0a1 was published on the `makutaku` org before the project moved to `altakleos`; see ADR-0009. -->
