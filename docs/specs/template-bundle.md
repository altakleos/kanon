---
status: superseded
superseded-by: 0048
design: "docs/design/kit-bundle.md"
date: 2026-04-22
realizes:
  - P-self-hosted-bootstrap
  - P-cross-link-dont-duplicate
stressed_by:
  - solo-engineer
  - onboarding-agent
fixtures: [tests/test_kit_integrity.py]
invariant_coverage:
  INV-template-bundle-four-tiers:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli.py::test_init_scaffolds_all_required_files
    - tests/test_kit_integrity.py::test_sdd_sub_manifest_has_expected_depths
  INV-template-bundle-strict-subset:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_manifest_paths_resolve
  INV-template-bundle-tier3-canonical-with-repo:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_dev_process_byte_equal_to_canonical
    - ci/check_kit_consistency.py
  INV-template-bundle-shims-are-pointers:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_cli.py::test_shims_are_pointers_not_duplicates
    - tests/test_cli.py::test_init_writes_all_shims
  INV-template-bundle-html-comment-markers:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
  INV-template-bundle-config-and-kit-md-seed:
    - tests/test_cli.py::test_kit_md_scaffolded_at_all_tiers
    - tests/test_cli.py::test_init_rejects_existing_without_force
  INV-template-bundle-no-consumer-state-leaks:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - ci/check_package_contents.py
  INV-template-bundle-placeholders-replaced:
    - tests/test_scaffold_marker_hardening.py::test_repo_agents_md_round_trips
    - tests/test_kit_integrity.py::test_kit_md_has_placeholders
    - tests/test_kit_integrity.py::test_kit_md_renders_with_placeholders
---
# Spec: Template bundle — what `init` scaffolds

## Intent

Define the exact file tree written by `kanon init --tier <N>` for each of N ∈ {0, 1, 2, 3}. The bundle contents are the consumer's starting point; every file either comes from the kit or is a placeholder the consumer replaces.

## Invariants

<!-- INV-template-bundle-four-tiers -->
1. **Four tiers ship in v0.1.** Tier membership is declared in `src/kanon/kit/manifest.yaml`; each tier is a union of the files/protocols listed for itself and all lower tiers.
   - **tier-0** — minimal: `AGENTS.md`, `CLAUDE.md`, `.kanon/config.yaml`, `.kanon/kit.md`. No `docs/` structure.
   - **tier-1** — adds `docs/sdd-method.md` (byte-identical to the kit's own), `docs/decisions/{README,_template}.md`, `docs/plans/{README,_template}.md`, and protocols `.kanon/protocols/tier-up-advisor.md` and `.kanon/protocols/verify-triage.md`.
   - **tier-2** — adds `docs/specs/{README,_template}.md` and `.kanon/protocols/spec-review.md`.
   - **tier-3** — adds `docs/design/{README,_template}.md` and `docs/foundations/{README.md, vision.md, principles/README.md, personas/README.md}`.
<!-- INV-template-bundle-strict-subset -->
2. **Strict-subset invariant (tautological).** Every file scaffolded at tier-N is also scaffolded at tier-(N+1) because `_build_bundle(tier=N)` unions manifest entries for tiers 0..N. There is no independent authoring of tier-N content; `manifest.yaml` is the single source.
<!-- INV-template-bundle-tier3-canonical-with-repo -->
3. **Tier-3 canonical with repo.** Files in `src/kanon/kit/files/` and `src/kanon/kit/protocols/` that have a repo-root counterpart (e.g., `docs/sdd-method.md`, the `_template.md` files, the kit's own `.kanon/protocols/*.md`) are byte-identical to those counterparts. Enforced by `ci/check_kit_consistency.py` against a narrow whitelist.
<!-- INV-template-bundle-shims-are-pointers -->
4. **Shims are pointers.** `CLAUDE.md` is always a single-line `See @AGENTS.md\n` file. Harness-specific shims (Cursor, Windsurf, etc.) are generated at `init` time from `kit/harnesses.yaml` and are also single-file pointers (with any frontmatter each harness requires).
<!-- INV-template-bundle-html-comment-markers -->
5. **HTML-comment markers.** Every AGENTS.md base in `kit/agents-md/` has its kit-managed sections wrapped in `<!-- kanon:begin:<section> -->` / `<!-- kanon:end:<section> -->` comment pairs. The active section list per tier is in `manifest.yaml` under `agents-md-sections`; fragments in `kit/sections/<name>.md` supply the content.
<!-- INV-template-bundle-config-and-kit-md-seed -->
6. **`.kanon/config.yaml` and `.kanon/kit.md` seed.** Every tier writes `.kanon/config.yaml` with `{kit_version, tier, tier_set_at}` and `.kanon/kit.md` rendered from `kit/kit.md` with placeholder substitution. `init` errors out if `.kanon/` already exists and `--force` wasn't given.
<!-- INV-template-bundle-no-consumer-state-leaks -->
7. **No consumer state leaks into the wheel.** `ci/check_package_contents.py` hard-fails on any file under paths that look like consumer output (e.g., `.kanon/config.yaml`, `.kit/fidelity.lock`, test-only artifacts).
<!-- INV-template-bundle-placeholders-replaced -->
8. **Placeholders are replaced at init.** Files containing `${...}`-style placeholders (`string.Template` with safe substitution per Sensei's learner-id pattern) are rendered at `init` time against `{project_name, tier, kit_version, iso_timestamp}`.

## Rationale

Manifest-driven tier membership (INV-template-bundle-strict-subset) collapses the old per-tier directory structure into one flat `kit/files/` and `kit/protocols/` tree, eliminating ~4× duplication of shared files. Byte-equality against repo canonical (INV-template-bundle-tier3-canonical-with-repo) remains the only reliable mechanism preventing drift, but applies to a narrow whitelist now that shared files live once.

Shims as pointers (per `P-cross-link-dont-duplicate`) is the only approach that scales across 8+ harnesses without forcing each new harness to duplicate AGENTS.md content.

## Out of Scope

- Rendering templates via a full templating engine (Jinja, etc.). `string.Template` with a small placeholder vocabulary is sufficient.
- Per-harness opt-out at init time (`--skip-harness cursor`). v0.1 writes all shims; opt-out deferred.

## Decisions

See ADR-0003 (shims-as-pointers), ADR-0006 (tier content), ADR-0008 (section markers + tier migration), ADR-0010 (protocol layer), ADR-0011 (`kit/` bundle refactor).
