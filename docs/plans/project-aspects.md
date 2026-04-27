---
feature: project-aspects
serves:
  - docs/specs/project-aspects.md
status: in-progress
date: 2026-04-26
target-release: v0.3
---
# Plan: Project-defined aspects — namespace grammar, loader, migration, validator extension

## Context

`docs/specs/project-aspects.md` (PR #23, status `draft`) introduces source-namespacing for aspects: `kanon-<local>` for kit-shipped, `project-<local>` for consumer-defined. Bare names at every input surface sugar to `kanon-`. A new `.kanon/aspects/<name>/` discovery path lets consumers compose project-specific aspects alongside kit ones; project-aspects can declare `validators:` that `kanon verify` runs in-process.

The change is mechanically sweeping (every aspect-name reference moves to the namespaced form) but observably backwards-compatible at the CLI surface (bare-name sugar). The dominant risks are: (a) the v2→v3 auto-migration of consumer configs and AGENTS.md markers must be one-way, idempotent, and complete; (b) runtime cross-source collision detection must move from CI-only to in-process; (c) project-validators run with kit privileges, so the trust boundary is documented and ratified by ADR-0028 before any code lands.

Sequencing: ADR first; then the rename-and-sugar pass (mechanical, big patch, no new capabilities); then migration; then the new discovery-and-exclusivity capability; then the validator-extension capability. Each phase ships as its own PR and ends with `kanon verify .` clean.

## Tasks

### Phase 0 — ADR

- [x] T1: Write ADR-0028 — full ADR (the model changes: aspect identity gains a namespace prefix). Captures (a) the namespace grammar `(kanon|project)-<local>`, (b) bare-name sugar resolves to `kanon-`, (c) discovery location `.kanon/aspects/<project-*>/`, (d) runtime ownership exclusivity, (e) in-process validator trust boundary, (f) v2→v3 migration discipline mirroring v1→v2 → `docs/decisions/0028-project-aspects.md`. (depends: spec approval — done via PR #23)

### Phase 1 — Namespace grammar + kit rename + bare-name sugar

- [x] T2: Add namespace-grammar regex and helpers — `_ASPECT_NAME_RE = r"^(kanon|project)-[a-z][a-z0-9-]*$"`, `_normalise_aspect_name(raw) -> str` (bare → `kanon-` sugar), `_split_aspect_name(name) -> (namespace, local)` → `src/kanon/_manifest.py`. (depends: T1)
- [x] T3: Update `_load_top_manifest` to require namespaced aspect keys in `src/kanon/kit/manifest.yaml`; raise ClickException naming the offender on bare keys → `src/kanon/_manifest.py`. (depends: T2)
- [x] T4: Update `_classify_predicate` — depth predicates accept namespaced names (or bare with sugar); capability names stay namespace-free → `src/kanon/cli.py`. (depends: T3)
- [x] T5: Rename kit-side aspects in the manifest registry: `sdd → kanon-sdd`, `worktrees → kanon-worktrees`, `release → kanon-release`, `testing → kanon-testing`, `security → kanon-security`, `deps → kanon-deps` → `src/kanon/kit/manifest.yaml`. (depends: T3)
- [x] T6: Move kit-side aspect directories to namespaced names: `src/kanon/kit/aspects/sdd/ → kanon-sdd/`, etc. Update all per-aspect `byte-equality:` entries to reflect new paths → `src/kanon/kit/aspects/*/manifest.yaml`. (depends: T5)
- [x] T7: Update kit-side `requires:` predicates to namespaced form: `kanon-worktrees` requires `["kanon-sdd >= 1"]`; `kanon-testing` `suggests: ["kanon-sdd >= 1"]` → `src/kanon/kit/manifest.yaml`. (depends: T5)
- [x] T8: Update AGENTS.md marker rendering — `_namespaced_section`, `_assemble_agents_md`, `_merge_agents_md`, `_remove_section` all operate on namespaced names; markers become `<!-- kanon:begin:kanon-sdd/plan-before-build -->` etc. The `_MARKER_RE` regex already accepts hyphens; no regex change → `src/kanon/_scaffold.py`, `src/kanon/_manifest.py`. (depends: T5)
- [x] T9: Update `--aspects` flag parser (`_parse_aspects_flag`) and every Click argument that names an aspect (`aspect set-depth`, `aspect set-config`, `aspect add`, `aspect remove`, `aspect info`) to apply `_normalise_aspect_name` to user input — bare names sugar to `kanon-`, prefixed names pass through unchanged → `src/kanon/cli.py`. (depends: T4)
- [x] T10: Update CI `check_kit_consistency.py` — assert all kit-side aspect names match `^kanon-[a-z][a-z0-9-]*$`; fold the existing `_check_cross_aspect_exclusivity` into the new namespaced-paths shape → `ci/check_kit_consistency.py`. (depends: T6)
- [x] T11: Update kit's own consumer state in this repo — `.kanon/config.yaml` keys (`sdd → kanon-sdd`, etc.); `AGENTS.md` marker prefixes (re-render via `kanon upgrade .` after T2–T10 land); rename `.kanon/protocols/<bare>/ → kanon-<bare>/` directories → `.kanon/config.yaml`, `AGENTS.md`, `.kanon/protocols/`. (depends: T10)
- [x] T12: Tests: bare-name sugar resolves at every input surface (CLI flags, `--aspects`, `aspect set-*` arguments, `requires:` predicates); namespaced and bare forms produce identical state → `tests/test_cli.py`, `tests/test_aspect_provides.py`. (depends: T9)
- [x] T13: Tests: `check_kit_consistency.py` rejects a kit-side directory named `project-foo`; rejects a top-manifest entry without the `kanon-` prefix → `tests/ci/test_check_kit_consistency.py`. (depends: T10)

### Phase 2 — v2→v3 auto-migration

- [x] T14: Extend `_migrate_legacy_config` to detect bare aspect keys (v2 shape: `aspects: {sdd: {...}}`) and rewrite to namespaced (`aspects: {kanon-sdd: {...}}`); emit `Migrated v2 (bare) → v3 (namespaced) aspect names.` once on the migration cycle. v1 (`tier:`) → v3 path still goes via the existing v1→v2 transformer first → `src/kanon/_scaffold.py`. (depends: T9)
- [x] T15: Extend `_rewrite_legacy_markers` (currently rewrites flat → `sdd/`-prefixed markers) to also rewrite bare-aspect markers to `kanon-`-prefixed: `<!-- kanon:begin:sdd/plan-before-build -->` → `<!-- kanon:begin:kanon-sdd/plan-before-build -->`. Idempotent on already-namespaced markers → `src/kanon/_scaffold.py`. (depends: T8)
- [x] T16: Add a one-time `.kanon/protocols/<bare>/ → kanon-<bare>/` directory migration in `upgrade` (mirrors the v0.2 flat-protocols migration `_migrate_flat_protocols`) → `src/kanon/_scaffold.py`. (depends: T15)
- [x] T17: Tests: v1 → v3 round-trip preserves user content; v2 → v3 round-trip preserves user content; v3 → v3 is a no-op (idempotent); mixed-state config (some bare, some namespaced — should not occur but is defensively handled) hard-fails with a clear error → `tests/test_e2e_lifecycle.py`. (depends: T16)
- [x] T18: Tests: AGENTS.md marker migration preserves user prose outside markers; preserves balance; works across all six bare aspect names → `tests/test_scaffold_marker_hardening.py`. (depends: T15)

### Phase 3 — Project-aspect loader + runtime exclusivity

- [x] T19: Add `_discover_project_aspects(target: Path) -> dict[str, dict[str, Any]]` — walks `.kanon/aspects/project-*/manifest.yaml` and returns the same shape as kit aspect-registry entries (with `path` resolving relative to `target`) → `src/kanon/_manifest.py`. (depends: T2)
- [x] T20: Add `_load_aspect_registry(target: Path) -> dict[str, Any]` — unions kit-aspects (from `_kit_root()`) and project-aspects (from `target/.kanon/aspects/`); namespace-ownership hard-fails on `.kanon/aspects/kanon-*/` (kit-namespace claimed by project source) → `src/kanon/_manifest.py`. (depends: T19)
- [x] T21: Update every CLI command that calls `_load_top_manifest` to use `_load_aspect_registry(target)` instead — so project-aspects participate in `aspect list`, `aspect info`, `aspect add`, `aspect set-depth`, `aspect set-config`, `aspect remove`, `verify` → `src/kanon/cli.py`. (depends: T20)
- [x] T22: Lift `_check_cross_aspect_exclusivity` from CI-only into `_build_bundle` runtime — raises `ClickException` if any two aspects (kit or project, any combination) declare the same `files:`/`protocols:` consumer-relative path. Error names both aspects and the colliding path. Per spec INV-6 → `src/kanon/_scaffold.py`. (depends: T21)
- [x] T23: Tests: a project-aspect at `.kanon/aspects/project-auth-policy/manifest.yaml` is listed by `kanon aspect list`, queried by `kanon aspect info project-auth-policy`, enabled by `kanon aspect add . project-auth-policy`, and removed by `kanon aspect remove . project-auth-policy` → `tests/test_cli.py`. (depends: T21)
- [x] T24: Tests: namespace-ownership violation — `.kanon/aspects/kanon-foo/` is rejected at load with single-line error naming the path and the rule → `tests/test_cli.py`. (depends: T20)
- [x] T25: Tests: cross-source path collision (a kit-aspect and a project-aspect both scaffolding `docs/specs/_template.md`) raises `ClickException` at `kanon init` / `kanon upgrade` time, naming both aspects and the path → `tests/test_cli.py`. (depends: T22)
- [x] T26: Tests: capability substitutability — a `project-lean-sdd` declaring `provides: [planning-discipline]` satisfies `kanon-worktrees`'s capability requirement even when `kanon-sdd` is at depth 0 → `tests/test_aspect_provides.py`. (depends: T21)

### Phase 4 — Validators-as-extensions

- [ ] T27: Add `validators:` field to the per-aspect sub-manifest schema (kit-side validator already covers schema; extend `_load_aspect_manifest` to validate the new field as a list of strings) → `src/kanon/_manifest.py`. (depends: T20)
- [ ] T28: In `_verify.py`, after kit structural checks complete, walk each enabled project-aspect's `validators:`, `importlib.import_module(...)` each, call `check(target, errors, warnings)`. Findings flow into the same JSON report → `src/kanon/_verify.py`, `src/kanon/cli.py`. (depends: T27)
- [ ] T29: Tests: a project-aspect with `validators: [project_aspects.checks.greenlight]` runs the named function during `kanon verify`; findings appear in the JSON report's `errors`/`warnings` → `tests/test_cli.py`. (depends: T28)
- [ ] T30: Tests: a project-validator cannot suppress kit-emitted errors. Implementation enforces this by ordering — kit structural checks run *after* project-validators, so any clearing the project-validator attempts is overwritten. Test asserts that when a project-validator's `check()` body calls `errors.clear()`, the kit's subsequent error append still produces a non-empty `errors` list. Per spec INV-9 → `tests/test_cli.py`. (depends: T29)
- [ ] T31: Tests: project-validator import failure (module not on path) emits a single error naming the missing module; verify continues with the remaining checks → `tests/test_cli.py`. (depends: T29)

### Phase 5 — Documentation, spec promotion, release wiring

- [ ] T32: Promote `docs/specs/project-aspects.md` from `status: draft` to `status: accepted`; populate `invariant_coverage:` mapping each INV anchor to the test that exercises it. Remove `fixtures_deferred:` since fixtures now exist → `docs/specs/project-aspects.md`. (depends: T26, T30)
- [ ] T33: Add CHANGELOG entry under `## [Unreleased]` — `feat: project-defined aspects` with one-paragraph summary referencing ADR-0028 and spec → `CHANGELOG.md`. (depends: T32)
- [ ] T34: Update README aspect-model section to describe project-aspects + the namespace grammar → `README.md`. (depends: T32)
- [ ] T35: Run `kanon fidelity update .` on this repo to track the promoted spec → `.kanon/fidelity.lock`. (depends: T32)
- [ ] T36: Update `docs/plans/roadmap.md` only if a deferred capability moves status as a result; otherwise None → `docs/plans/roadmap.md`. (depends: T32)

## Acceptance Criteria

- [ ] AC1: Every invariant in `docs/specs/project-aspects.md` (INV-1..INV-10) is exercised by at least one test in `tests/` and recorded in the spec's `invariant_coverage:`.
- [ ] AC2: Every existing CLI invocation that uses bare aspect names (`kanon aspect set-depth . sdd 2`, `kanon init . --aspects sdd:1,worktrees:2`, etc.) continues to work and resolves to the `kanon-` namespace.
- [ ] AC3: A project-aspect declared at `.kanon/aspects/project-foo/manifest.yaml` is discovered and listed by `kanon aspect list`, with the same metadata surface kit-aspects show.
- [ ] AC4: A v2 consumer config (`aspects: {sdd: {...}}`) auto-migrates to v3 (`aspects: {kanon-sdd: {...}}`) on first `kanon upgrade` after this lands; AGENTS.md markers migrate in the same operation; the migration is one-way, idempotent, and emits a single console line acknowledging it.
- [ ] AC5: `kanon init`, `kanon upgrade`, `kanon aspect set-depth` raise `ClickException` naming both aspects and the path when a kit-aspect and a project-aspect declare the same consumer-relative scaffold path.
- [ ] AC6: `.kanon/aspects/kanon-foo/manifest.yaml` is rejected at load with a single-line error naming the offending path and the namespace-ownership rule.
- [ ] AC7: `kanon verify .` invokes every enabled project-aspect's declared `validators:` modules; their findings appear in the JSON report. A project-validator cannot suppress a kit-emitted error.
- [ ] AC8: This repo's own `.kanon/config.yaml` and AGENTS.md markers use namespaced aspect names after Phase 1 lands; `kanon verify .` is `status: ok` with zero warnings.
- [ ] AC9: `pytest -q`, `ruff check src/ tests/ ci/`, and `mypy src/kanon` pass on every PR. Coverage stays at or above the configured floor.
- [ ] AC10: `kanon verify .` returns ok against post-merge `main` after each phase's PR.

## Out of Scope (deferred)

- **Third-party aspect publishing via pip** — `acme-<local>` namespace reserved by the spec but not defined here.
- **Subprocess isolation for project-validators** — in-process is the v0.3 trust model.
- **Per-project-aspect CLI subcommands** (`kanon project-foo report`) — verify-extension entrypoint is the only programmatic surface.
- **Project-aspect schema versioning** independent of the kit's manifest schema.
- **Project-aspect-to-project-aspect `requires:` cycles** — acyclic only; deep cross-aspect graphs deferred.
- **`kanon aspect remove kanon-<local>` consumer-side migration tooling** — removal of kit-shipped aspects already supported, unchanged by this plan.

## Documentation Impact

- README aspect-model section: add project-aspects + namespace grammar (T34).
- AGENTS.md markers in this repo migrate to namespaced form (T11) — visible diff but no behaviour change for contributors.
- CHANGELOG `[Unreleased]` gains a `feat: project-defined aspects` entry (T33).
- Migration guide: a short `docs/plans/v0.3-migration-notes.md` may be warranted before tagging v0.3 — flagged here, drafted only if Phase 2 surfaces edge cases worth documenting.
