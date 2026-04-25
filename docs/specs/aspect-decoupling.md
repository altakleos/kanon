---
status: accepted
date: 2026-04-24
realizes:
  - P-prose-is-code
  - P-tiers-insulate
stressed_by:
  - solo-with-agents
  - platform-team
fixtures:
  - tests/test_cli.py
  - tests/test_kit_integrity.py
  - tests/ci/test_check_kit_consistency.py
invariant_coverage:
  INV-aspect-decoupling-no-literal-aspect-names:
    - tests/ci/test_check_kit_consistency.py::test_real_repo_passes
  INV-aspect-decoupling-init-accepts-aspects:
    - tests/test_cli.py::test_init_with_aspects_flag
    - tests/test_cli.py::test_init_aspects_and_tier_mutual_exclusion
  INV-aspect-decoupling-agents-md-base-neutral:
    - tests/test_kit_integrity.py::test_depth_agents_md_has_no_section_markers
  INV-aspect-decoupling-aspect-add-remove:
    - tests/test_cli.py::test_aspect_add
    - tests/test_cli.py::test_aspect_remove
  INV-aspect-decoupling-requires-enforced:
    - tests/test_cli.py::test_aspect_add_requires_unmet
    - tests/test_cli.py::test_aspect_remove_blocked_by_dependent
  INV-aspect-decoupling-ci-manifest-driven:
    - tests/ci/test_check_kit_consistency.py::test_real_repo_passes
  INV-aspect-decoupling-tier-placeholder-replaced:
    - tests/test_kit_integrity.py::test_kit_md_has_placeholders
---
# Spec: Aspect Decoupling — remove sdd as a structurally privileged aspect

## Intent

Eliminate the hardcoded coupling between the kanon orchestration layer and the `sdd` aspect, so that any aspect can serve as the primary discipline and new aspects require zero Python changes to add. Today, `sdd` owns the AGENTS.md base template, `kanon init` only enables `sdd`, the `${tier}` placeholder is an sdd alias, and CI validation hardcodes sdd file paths. This spec defines the target state where aspects are truly equal participants in a data-driven registry.

The primary user is a kit contributor adding a third or fourth aspect. The secondary user is a consumer who wants a non-SDD-primary project (e.g., worktrees-only, or a future `release` aspect without full SDD ceremony).

## Invariants

<!-- INV-aspect-decoupling-no-literal-aspect-names -->
1. **No aspect name appears as a literal in Python source.** After this work, `grep -rE "'sdd'|\"sdd\"" src/kanon/ ci/` returns zero results outside of legacy-migration code guarded by a config format version check (e.g., `if config.get("format_version", 1) < 2:`). Aspect names live exclusively in YAML manifests and markdown templates.

<!-- INV-aspect-decoupling-init-accepts-aspects -->
2. **`kanon init` accepts `--aspects`.** The `--aspects` flag takes a comma-separated list of `name:depth` pairs (e.g., `--aspects sdd:1,worktrees:2`). The existing `--tier N` flag is preserved as sugar for `--aspects sdd:N`. When neither flag is provided, the kit's default aspect set is read from the top-level manifest under a `defaults:` key:
   ```yaml
   defaults:
     - sdd
     - worktrees
   ```
   Each listed aspect is enabled at its `default-depth` from the aspect registry. Aspects not in `defaults:` are opt-in only.

<!-- INV-aspect-decoupling-agents-md-base-neutral -->
3. **AGENTS.md base template is aspect-neutral.** A kit-level base template at `src/kanon/kit/agents-md-base.md` provides the document skeleton (heading, boot chain, project layout, key constraints, contribution conventions, references). Aspects inject sections into this skeleton via `<!-- kanon:begin:<aspect>/<section> -->` markers. No aspect owns the skeleton.

<!-- INV-aspect-decoupling-aspect-add-remove -->
4. **`kanon aspect add` and `kanon aspect remove` exist.** `add` enables an aspect at its default depth, enforcing `requires:` dependencies. `remove` deletes the aspect's AGENTS.md marker sections and its `.kanon/config.yaml` entry. Scaffolded files are left on disk (non-destructive, per ADR-0008).

<!-- INV-aspect-decoupling-requires-enforced -->
5. **`requires:` is enforced at runtime.** `_set_aspect_depth`, `aspect add`, and `aspect remove` parse the dependency predicate in `requires:` and fail with a clear error if dependencies are unmet. The predicate grammar is `<aspect> <op> <depth>` where `op` ∈ {`>=`, `>`, `==`, `<`, `<=`} and `depth` is an integer. Examples: `"sdd >= 1"`, `"worktrees == 2"`. `aspect remove` fails if other enabled aspects depend on the one being removed.

<!-- INV-aspect-decoupling-ci-manifest-driven -->
6. **CI validation is manifest-driven.** `check_package_contents.py` reads the top-level manifest to determine required files and directories instead of hardcoding paths. `check_kit_consistency.py` reads a `byte-equality:` key in per-aspect sub-manifests instead of a hardcoded whitelist:
   ```yaml
   byte-equality:
     - kit: docs/development-process.md
       repo: docs/development-process.md
     - kit: docs/decisions/_template.md
       repo: docs/decisions/_template.md
   ```
   Each entry maps a kit-relative path to a repo-relative path. The CI script walks all aspects and unions their byte-equality entries.

<!-- INV-aspect-decoupling-tier-placeholder-replaced -->
7. **`${tier}` placeholder is replaced with `${sdd_depth}`.** The generic placeholder vocabulary is `${project_name}` and `${<aspect>_depth}` for any enabled aspect. kit.md and AGENTS.md templates use these. The bare `${tier}` alias is preserved in rendering for backward compatibility with existing consumer kit.md files but is not used in new templates.

## Rationale

**Why now.** The project just shipped its second aspect (`worktrees`). An audit found hardcoded `sdd` string literals in `cli.py` (4 dependencies), `_scaffold.py` (12 dependencies), and CI scripts (19 dependencies). At 2 aspects this is manageable; at 5 it becomes a maintenance burden; at 10 it's an architecture change under pressure. More aspects are planned imminently. Decoupling while the aspect count is low and the contributor count is one minimizes risk.

**Why a spec, not just a refactor.** This changes user-visible behavior: new CLI flags (`--aspects`, `aspect add`, `aspect remove`), new manifest keys (`defaults:`, `byte-equality:`), new error messages (dependency enforcement). These are promises to users that must survive implementation changes.

**Why not split into multiple specs.** The invariants are interdependent. You can't make init generic without a base template; you can't enforce requires without add/remove; you can't make CI data-driven without the manifest keys. Splitting would create specs that can't be implemented independently.

## Out of Scope

- **Section ordering metadata** (e.g., `weight:` or `after:` in sub-manifests). Alphabetical-by-aspect-name is sufficient for ≤5 aspects. Revisit when ordering becomes a user complaint.
- **Third-party / external aspect packages.** Aspects ship in the kit wheel. Community aspect registries are deferred per the aspects spec.
- **AGENTS.md splitting** (e.g., one file per aspect). Single-file AGENTS.md is the contract. Revisit if document length becomes a problem.
- **Removing the `kanon tier set` command.** It stays as sugar for backward compatibility.
- **Runtime file-conflict detection in `_build_bundle`.** CI catches conflicts; runtime detection is a nice-to-have.

## Decisions

See:
- **ADR-0016** — aspect decoupling (base template, generic init, requires enforcement, manifest-driven CI).

ADR number is provisional until authored alongside this spec's promotion from `draft` to `accepted`.
