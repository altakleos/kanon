# Changelog

All notable user-visible changes to `kanon` are recorded in this file.

The format is based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/altakleos/kanon/compare/v0.2.0a8...HEAD
[0.2.0a8]: https://github.com/altakleos/kanon/compare/v0.2.0a7...v0.2.0a8
[0.2.0a7]: https://github.com/altakleos/kanon/compare/v0.2.0a6...v0.2.0a7
[0.2.0a5]: https://github.com/altakleos/kanon/compare/v0.2.0a4...v0.2.0a5
[0.2.0a4]: https://github.com/altakleos/kanon/compare/v0.2.0a3...v0.2.0a4
[0.2.0a3]: https://github.com/altakleos/kanon/compare/v0.2.0a2...v0.2.0a3
[0.2.0a2]: https://github.com/altakleos/kanon/releases/tag/v0.2.0a2
[0.2.0a1]: https://github.com/altakleos/kanon/releases/tag/v0.2.0a1
[0.1.0a1]: https://github.com/makutaku/kanon/releases/tag/v0.1.0a1
