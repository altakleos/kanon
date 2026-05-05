---
status: accepted
design: "Follows ADR-0028"
date: 2026-04-26
target-release: v0.3
realizes:
  - P-self-hosted-bootstrap
  - P-cross-link-dont-duplicate
serves:
  - vision
stressed_by:
  - solo-with-agents
fixtures:
  - tests/test_cli.py
  - tests/test_aspect_provides.py
  - tests/test_scaffold_marker_hardening.py
  - tests/scripts/test_check_kit_consistency.py
invariant_coverage:
  INV-project-aspects-discovery-location:
    - tests/test_cli_aspect.py::test_project_aspect_lifecycle_list_info_add_remove
  INV-project-aspects-manifest-shape-mirrors-kit:
    - tests/test_cli_aspect.py::test_project_aspect_lifecycle_list_info_add_remove
  INV-project-aspects-namespace-grammar:
    - tests/test_aspect_provides.py::test_normalise_aspect_name_bare_sugars_to_kanon
    - tests/test_aspect_provides.py::test_normalise_aspect_name_namespaced_passes_through
    - tests/test_aspect_provides.py::test_normalise_aspect_name_invalid_rejected
    - tests/test_aspect_provides.py::test_split_aspect_name
    - tests/test_aspect_provides.py::test_classify_predicate_bare_aspect_name_sugars
    - tests/test_aspect_provides.py::test_classify_predicate_namespaced_aspect_name_unchanged
  INV-project-aspects-namespace-ownership:
    - tests/test_cli_aspect.py::test_project_aspect_kanon_namespace_in_consumer_dir_rejected
    - tests/scripts/test_check_kit_consistency.py::test_kit_aspect_with_project_prefix_rejected
    - tests/scripts/test_check_kit_consistency.py::test_kit_aspect_with_bare_name_rejected
  INV-project-aspects-namespace-migration:
    - tests/test_cli_helpers.py::test_migrate_legacy_config_v1_to_v3_produces_namespaced_key
    - tests/test_cli_helpers.py::test_migrate_legacy_config_v3_is_idempotent_no_op
    - tests/test_cli_helpers.py::test_migrate_legacy_config_v2_all_six_aspects_round_trip
    - tests/test_cli_helpers.py::test_migrate_legacy_config_mixed_state_hard_fails
    - tests/test_cli.py::test_upgrade_v1_legacy_round_trip_preserves_user_content
    - tests/test_cli_aspect.py::test_cli_legacy_v2_config_auto_migrates_to_v3
    - tests/test_scaffold_marker_hardening.py::test_rewrite_legacy_markers_handles_all_six_bare_aspects
    - tests/test_scaffold_marker_hardening.py::test_rewrite_legacy_markers_idempotent_on_already_namespaced
    - tests/test_scaffold_marker_hardening.py::test_rewrite_legacy_markers_preserves_user_prose_outside_markers
    - tests/test_scaffold_marker_hardening.py::test_rewrite_legacy_markers_preserves_balance
  INV-project-aspects-runtime-ownership-exclusivity:
    - tests/test_cli_aspect.py::test_project_aspect_cross_source_path_collision_raises
  INV-project-aspects-trust-boundary-in-process:
    - tests/test_cli_aspect.py::test_project_aspect_validator_emits_findings_in_verify_report
    - tests/test_cli_aspect.py::test_project_aspect_validator_import_failure_recorded
  INV-project-aspects-requires-and-substitutability:
    - tests/test_cli_aspect.py::test_project_aspect_capability_substitutes_kit_capability_requirement
  INV-project-aspects-validators-non-overriding:
    - tests/test_cli_aspect.py::test_project_aspect_validator_cannot_suppress_kit_errors
  INV-project-aspects-upgrade-source-routing:
    - tests/test_cli.py::test_upgrade_does_not_modify_project_aspect_files
---
# Spec: Project-defined aspects — composition for consumer-specific discipline

## Intent

Let a consumer repo declare its own aspects alongside kit-shipped ones. A project-aspect lives at `.kanon/aspects/<name>/` with the same shape as a kit-side aspect (`src/kanon_reference/aspects/kanon_<name>/`): a sub-manifest, optional `byte-equality:` and `config-schema:` blocks, optional `files/`, `protocols/`, `sections/`, `agents-md/` directories, optional `validators:` declaration. The CLI discovers project-aspects on the same code paths it uses for kit-aspects, with two namespacing rules that keep the two sources distinguishable forever.

This spec realises composition without re-opening the deferred third-party-aspect-publishing question (ADR-0012 § Alternatives #5). Project-aspects are not pip packages; they live in the consumer's own git tree and version with the consumer.

## Slug namespace grammar

To prevent silent collision between kit-shipped and project-defined aspects, **all aspect names carry a source-namespace prefix**:

- `kanon-<local>` — declared by the kit (`src/kanon_reference/aspects/kanon_<local>/`).
- `project-<local>` — declared by the consumer (`.kanon/aspects/<local>/`).

Bare names at every input surface (CLI flags, `requires:` predicates, `--aspects` parsing, `aspect set-depth`/`set-config` arguments) resolve to the `kanon-` namespace. This preserves backward-compatibility for every existing usage; the prefix is mandatory only for project-aspects, which have no shorthand.

Future namespaces (`acme-<local>` for a hypothetical published third-party kit) are reserved by this grammar without being defined by this spec.

## Invariants

<!-- INV-project-aspects-discovery-location -->
1. **Discovery location.** Project-aspects live at `.kanon/aspects/<local-name>/`. The directory layout mirrors the kit-side `src/kanon_reference/aspects/kanon_<local-name>/` exactly: `manifest.yaml`, optional `agents-md/depth-N.md`, optional `files/`, `protocols/`, `sections/`. The CLI discovers project-aspects after kit-aspects on every load that calls `_load_top_manifest`; project-aspect entries are unioned into the same in-memory aspect registry the kit-aspects populate.

<!-- INV-project-aspects-manifest-shape-mirrors-kit -->
2. **Manifest shape mirrors kit.** A project-aspect's `manifest.yaml` carries the same fields as a kit-side sub-manifest: `depth-N: {files, protocols, sections}`, optional `byte-equality:`, optional `config-schema:`. The top-level registry entry for a project-aspect carries `stability` (always `experimental` for project-aspects in v0.3 — the `stable` label is reserved for the kit), `depth-range`, `default-depth`, optional `requires`, optional `provides`. Validators by `_load_aspect_manifest`'s existing schema enforce both sources identically.

<!-- INV-project-aspects-namespace-grammar -->
3. **Namespace grammar.** Aspect names match `^(kanon|project)-[a-z][a-z0-9-]*$` everywhere they appear in canonical form (manifest keys, config keys, `requires:` predicates, AGENTS.md marker `<section>` field). At input surfaces (CLI arguments, `--aspects` flag tokens, `requires:` predicate parsing), an unprefixed name is sugar for the `kanon-` namespace. The first dash separates namespace from local name; subsequent dashes are part of the local name (e.g., `kanon-graph-rename` is namespace `kanon`, local `graph-rename`).

<!-- INV-project-aspects-namespace-ownership -->
4. **Namespace ownership is source-bounded.** A kit-side directory may only declare aspects in the `kanon-` namespace; a project-side directory may only declare aspects in the `project-` namespace. `_load_top_manifest` and the project-aspect loader hard-fail at load time on a violation (e.g., `.kanon/aspects/kanon-foo/manifest.yaml` is rejected with a single-line error naming the offending path and the rule).

<!-- INV-project-aspects-namespace-migration -->
5. **Auto-migration on first upgrade.** A pre-namespace consumer config (`.kanon/config.yaml` v2 with bare aspect keys: `aspects: {sdd: {...}}`) auto-migrates to v3 with `kanon-` prefixed keys (`aspects: {kanon-sdd: {...}}`) on first `kanon upgrade` after this lands. AGENTS.md markers with bare aspect prefixes (`<!-- kanon:begin:sdd/plan-before-build -->`) similarly migrate to the namespaced form (`<!-- kanon:begin:kanon-sdd/plan-before-build -->`) via the existing `_rewrite_legacy_markers` pattern (`_scaffold.py:308`). Migration is one-way and emits `Migrated v2 (bare) → v3 (namespaced) aspect names.` Older kanon CLIs reading a v3 config produce undefined behaviour; this is the same migration discipline applied to the v1 → v2 transition (ADR-0012).

<!-- INV-project-aspects-runtime-ownership-exclusivity -->
6. **Runtime ownership exclusivity.** `_build_bundle` (`_scaffold.py:126`) raises a `ClickException` if any two aspects (kit or project, any combination) declare the same consumer-relative path under their `files:` or `protocols:` lists. This generalises the existing CI-only check (`scripts/check_kit_consistency.py:218`) to runtime, because project-aspects can introduce collisions the kit's CI cannot see. The error names both aspects and the colliding path.

<!-- INV-project-aspects-trust-boundary-in-process -->
7. **Validators run in-process.** A project-aspect's `manifest.yaml` may declare a `validators:` list of importable Python module paths (resolved relative to the project's working directory and `sys.path`). `kanon verify` imports each and calls a known entrypoint — `def check(target: Path, errors: list[str], warnings: list[str]) -> None`. Findings flow into the same JSON report the kit's structural checks populate. Project-validator code runs with the same privileges as the CLI; this trust boundary is documented and not sandboxed.

<!-- INV-project-aspects-requires-and-substitutability -->
8. **`requires:` direction and capability substitutability.** A project-aspect may declare `requires:` predicates against any other aspect (kit or project) and against any capability declared in any aspect's `provides:` list. A kit-aspect's `requires:` list may NOT reference a project-aspect by name (kit cannot depend on consumer-specific structure). However, a project-aspect's `provides:` capability **may** satisfy a kit-aspect's capability-presence predicate (e.g., a `project-lean-sdd` declaring `provides: [planning-discipline]` satisfies `kanon-worktrees`'s implicit `planning-discipline` requirement); ADR-0026's substitutability is source-neutral.

<!-- INV-project-aspects-validators-non-overriding -->
9. **Project validators do not override kit structural checks.** The kit's built-in `kanon verify` checks (`check_aspects_known`, `check_required_files`, `check_agents_md_markers`, `check_fidelity_lock`, `check_verified_by`) are authoritative. Project-aspect validators run additively; they cannot suppress, mutate, or short-circuit a kit-emitted error or warning. Verify report's `status` is `fail` if either source emits an error; `ok` only when both are clean.

<!-- INV-project-aspects-upgrade-source-routing -->
10. **Upgrade routes by source.** `kanon upgrade` re-renders kit-aspect content from the installed pip kit's `src/kanon_reference/aspects/kanon_<name>/` and project-aspect content from `.kanon/aspects/<name>/`. The `kit_version` pin in config governs only kit-aspect content; project-aspects have no version pin (they version with the consumer's git history). Upgrade does NOT delete or modify files under `.kanon/aspects/` — those are consumer-authored.

## Rationale

**Why mirror the kit's directory shape exactly.** Composition that uses a different shape doubles the cognitive surface (kit authors and project authors learn two layouts) and forks the validator surface (CI checks against kit-shape don't catch project-shape errors and vice versa). Reusing the kit's shape — same `depth-N` keys, same `byte-equality:`, same `config-schema:` — means every existing validator and the same `_load_aspect_manifest` code path serve both sources. This is the cheapest path to composition that doesn't accumulate technical debt.

**Why namespace prefixes everywhere instead of collision-detection.** Namespace prefixing is more verbose but eliminates an entire class of failure mode: a project-aspect can never silently shadow a kit-aspect, and a future kit rename of `kanon-testing` cannot collide with an existing `project-testing`. The verbosity cost is mitigated by the bare-name shorthand (which preserves CLI ergonomics for the 95% of usage that targets kit-aspects). Hard-fail-on-collision was the alternative; it would force consumers to rename their project-aspect any time the kit added one, which inverts the cost the kit should be absorbing.

**Why bare-name shorthand maps to `kanon-`, not "any unique aspect."** The natural extension would be: bare names resolve to whatever aspect (kit or project) currently uniquely owns the local name. That re-introduces the ambiguity the prefix was supposed to eliminate — the same input changes meaning when a project-aspect appears or disappears. Mapping bare names to `kanon-` exclusively makes the resolution stable across every consumer's tree.

**Why in-process validators.** Subprocess isolation would force project-validators to re-import the kit's verify protocol (path argument, error/warning shape, JSON schema) over an IPC boundary. The kit's verify protocol is a Python function signature; the natural way to extend it is another Python function with the same signature. Consumers already trust the kit's CLI to run inside their working directory; trusting project-aspect validators with the same privilege is a smaller increment than the subprocess boundary's complexity buys.

**Why project-aspects can substitute kit capabilities, but kit cannot require project structure.** Capability substitutability (ADR-0026) is the entire reason `provides:` exists — it lets the kit ship `kanon-worktrees` requiring `planning-discipline` without binding to `kanon-sdd` specifically. A consumer who ships `project-lean-sdd` providing the same capability should satisfy that requirement. The reverse — kit requiring project-named structure — would couple the kit to consumer-specific shapes, which is the opposite of why aspects exist.

## Out of Scope

- **Third-party aspect publishing via pip.** Project-aspects are git-tracked in the consumer repo; published third-party kits remain deferred per ADR-0012 § Alternatives #5. The `acme-<local>` namespace is reserved by this spec but not defined.
- **AGENTS.md base-template overrides.** Project-aspects may add new marker sections to AGENTS.md (via the same `agents-md/depth-N.md` mechanism kit-aspects use), but cannot modify the kit-rendered skeleton.
- **Subprocess isolation for project-validators.** In-process is the v0.3 trust model; subprocess sandboxing is a future spec if a consumer demands it.
- **Project-aspect-to-project-aspect `requires:` cycles.** Acyclic only; the loader hard-fails on cycles. Deep cross-aspect dependency graphs are deferred.
- **Schema versioning for project-aspect manifests.** Project-aspects share the kit's manifest schema; no independent versioning. A future kit migration that breaks the manifest shape will require a coordinated consumer migration.
- **Per-project-aspect CLI subcommands.** A project-aspect cannot register its own `kanon <projaspect> ...` subcommand. The verify-extension entrypoint is the only programmatic surface.
- **`kanon aspect remove kanon-<local>` from the consumer side.** Removal of a kit-shipped aspect remains supported; this spec does not change that surface.

## Decisions

- **ADR-0028** (to be authored alongside this spec's promotion to `accepted`) — Project-defined aspects: namespace grammar, discovery location, runtime ownership exclusivity, and the v2→v3 config migration.
- Pattern instantiation under ADR-0012 (aspect model), ADR-0024 (atomic writes for migration), and ADR-0026 (`provides:` capability registry).
- Specifies INV-5 in terms of the existing `_rewrite_legacy_markers` and `_migrate_legacy_config` patterns — does not invent a parallel migration mechanism.

## Protocol-substrate composition (added per ADR-0040)

Under [ADR-0048](../decisions/0048-kanon-as-protocol-substrate.md)'s protocol-substrate commitment, project-aspects compose with the kernel/reference runtime interface ratified by [ADR-0040](../decisions/0040-kernel-reference-runtime-interface.md).

- **Project-aspects retain filesystem discovery**: `<target>/.kanon/aspects/project-*/manifest.yaml` is the canonical location; this spec's INVs survive verbatim.
- **Entry-point publishers compose alongside**: kit-shipped (`kanon-`) and third-party (`acme-`) aspects discovered via Python entry-points (group `kanon.aspects`) per ADR-0040 union with project-aspects in `_load_aspect_registry()`. The three sources have equal status under [`P-publisher-symmetry`](../foundations/principles/P-publisher-symmetry.md).
- **Project-aspects MUST NOT register via entry-points**: namespace ownership is source-bounded (per this spec's `INV-project-aspects-namespace-ownership` invariant). The kernel rejects entry-point registrations under the `project-` namespace.
- **Project-validators retain their in-process trust boundary**: ADR-0028's `validators:` field semantics survive; the trust model is unchanged by ADR-0040's runtime-interface commitment.

The existing INVs in this spec (namespace grammar, discovery location, runtime ownership exclusivity, validators-as-extensions, capability substitutability) survive verbatim. ADR-0040 specifies how the kernel composes project-aspects with entry-point publishers in a unified registry without privileging either.
