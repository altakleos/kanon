# `kanon`'s Instantiation of the SDD Stack

The development process in [`sdd-method.md`](sdd-method.md) describes Spec-Driven Development as a method: six generic layers (Foundations above Specs → Design → ADRs → Plans → Implementation → Verification). This document describes how `kanon` specifically instantiates the bottom two layers — **Implementation** and **Verification** — and carries the load-bearing principles that make `kanon`'s instantiation distinctive.

For the generic method, read [`sdd-method.md`](sdd-method.md). For `kanon`'s artifact choices, read this doc.

> **Status: current.** This file describes `kanon`'s instantiation as of v0.3 work-in-progress (post project-aspects, ADR-0028; recovery-model hybrid, ADR-0030).

## Implementation Layer

Implementation in `kanon` is realized across three artifact families. The Python code is decomposed by responsibility, with `cli.py` as the orchestrator that imports from the others — never the reverse:

| Artifact type | Location | Executor | Role |
|---|---|---|---|
| Python — manifest loaders | `src/kanon/_manifest.py` | CPython | The dependency root: cached YAML reads of the kit + project-aspect registries (`_load_top_manifest`, `_load_aspect_registry`, `_discover_project_aspects`), aspect-name grammar (`_normalise_aspect_name`, `_split_aspect_name`), marker regex + fenced-code-block awareness (`_iter_markers`). Pure reads with `lru_cache`/`@cache`; no side effects. |
| Python — content construction | `src/kanon/_scaffold.py` | CPython | AGENTS.md assembly + merge (`_assemble_agents_md`, `_merge_agents_md`); bundle construction with cross-source path-collision check (`_build_bundle`); per-aspect protocols-index rendering; v1→v3 / v2→v3 / flat-protocols migration; harness shim rendering. |
| Python — durability primitive | `src/kanon/_atomic.py` | CPython | `atomic_write_text` (write-tmp + fsync + `os.replace` + parent-dir fsync); sentinel write/read/clear for the recovery model in ADR-0024 + ADR-0030. |
| Python — verify checks | `src/kanon/_verify.py` | CPython | Structural checks (`check_aspects_known`, `check_required_files`, `check_agents_md_markers`, `check_fidelity_lock`, `check_verified_by`); in-process invocation of project-aspect declared `validators:` (`run_project_validators`, ADR-0028 INV-7/9). |
| Python — graph + rename | `src/kanon/_graph.py`, `src/kanon/_rename.py` | CPython | Typed cross-link graph load (nodes: principle, persona, spec, aspect, capability, vision; edges: realizes, serves, stressed_by, requires, …) for `kanon graph orphans`. Atomic slug rename with ops-manifest (`recover_pending_rename`, ADR-0027 + ADR-0030). |
| Python — Click CLI | `src/kanon/cli.py` | CPython via `kanon` entry point | The orchestrator. Subcommands: `init`, `upgrade`, `verify`, `tier set` (sugar), `aspect list/info/add/remove/set-depth/set-config`, `fidelity update`, `graph orphans`, `graph rename`. Hard-fails on namespace-ownership violations; applies bare-name sugar at every input surface; routes interrupted operations through `_check_pending_recovery`. |
| Kit bundle | `src/kanon/kit/` | Filtered by `init` / `upgrade` / `aspect set-depth` using manifest membership at the requested depth | Prose-as-code SDD rules and protocols the consumer's LLM reads. Layout: top `manifest.yaml` (aspect registry), per-aspect `aspects/kanon-<local>/manifest.yaml` (depth-N membership), `aspects/kanon-<local>/{files,protocols,sections,agents-md}/`, the kernel doc `kit.md`, the cross-harness shim registry `harnesses.yaml`, and the AGENTS.md skeleton `agents-md-base.md`. |
| Harness registry | `src/kanon/kit/harnesses.yaml` | Loader inside CLI | Per-harness shim paths + frontmatter (Claude Code, Cursor, GitHub Copilot, Windsurf, Cline, Roo Code, JetBrains AI, Kiro). New harness support: data-only addition. |

### Decomposition discipline

`cli.py` imports from `_manifest`, `_scaffold`, `_atomic`, `_verify`, `_graph`, `_rename`. The reverse never holds. `_manifest.py` is the dependency root — no internal imports outside `kanon` itself. `_scaffold.py` imports from `_manifest` for marker grammar and registry queries. The decomposition is enforced by code review, not a CI check; the smoke test is "does `cli.py` stay under the ~1500 LOC cap from ADR-0012." (Currently ~1200 LOC.)

### Manifest-driven membership

The kit ships **no hardcoded path lists**. What gets scaffolded at `init`/`upgrade`/`aspect set-depth` is data in `manifest.yaml` (which aspects exist, their depth ranges, default depths, `requires:`/`provides:`) and per-aspect `manifest.yaml` (depth-N file/protocol/section lists). Strict-superset semantics are preserved by manifest-union: `_aspect_items(aspect, depth, key)` walks `depth-0..depth-N` and concatenates. ADR-0011 retired the cross-tier byte-equality check that this design made tautological.

## Verification Layer

Verification asserts both that the kit's own Python behaves correctly *and* that the kit's own SDD artifacts (specs, ADRs, principles, plans, fidelity lock) remain internally consistent across edits. The split between "code that runs" and "data that's checked" is the unit of decomposition:

| Artifact type | Location | Role |
|---|---|---|
| Pytest suite | `tests/` | CLI atomicity, project-aspect lifecycle, marker hardening (fence-aware), v1→v3 / v2→v3 migration round-trips, capability substitutability across kit/project sources, recovery integration (graph-rename auto-replay), e2e installed-package smoke (`tests/test_e2e_installed.py`), e2e in-process lifecycle (`tests/test_e2e_lifecycle.py`). 480+ tests; coverage floor enforced via `pytest --cov-fail-under=90` in `pyproject.toml`. |
| Kit-internal CI validators | `scripts/check_kit_consistency.py` | Byte-equality between repo-canonical and kit-mirror files (per-aspect whitelist), kit-side aspect-name namespace ownership (`^kanon-`), cross-aspect file-path exclusivity, AGENTS.md marker-grammar discipline in `agents-md/depth-*.md`, harness-registry shape, `requires:` predicate resolution including capability presence per ADR-0026. |
| SDD-artifact CI validators | `scripts/check_foundations.py`, `scripts/check_links.py`, `scripts/check_invariant_ids.py`, `scripts/check_verified_by.py`, `scripts/check_status_consistency.py`, `scripts/check_package_contents.py` | Frontmatter cross-reference resolution (specs ↔ principles ↔ personas), markdown-link reachability, `INV-*` anchor uniqueness + grammar, spec-anchor → fixture mapping coverage, status-taxonomy + plan checkbox consistency, wheel-content sanity. |
| Code-quality CI validators | `scripts/check_test_quality.py`, `scripts/check_security_patterns.py`, `scripts/check_deps.py` | The kit-shipped scanners that consumers also receive at the relevant aspect depth. Test-quality flags trivial bodies; security flags TLS-disable, 0o777, wildcard CORS, high-entropy literals; deps flags unpinned versions and duplicate-purpose packages. Best-effort safety nets, not SAST/audit replacements. |
| Release validator | `scripts/release-preflight.py` | Tag/version/CHANGELOG consistency before publish, gated by the `release-checklist` protocol. |
| Top-level CLI runner | `kanon verify <target>` | Entry point for consumer repos. Runs the structural checks, the fidelity-lock drift report (when `kanon-sdd` depth ≥ 2), the `verified-by` invariant-coverage report, and (per ADR-0028 INV-7) any project-aspect-declared `validators:`. |
| Fidelity lock | `.kanon/fidelity.lock`, generated by `kanon fidelity update` | Spec-SHA + fixture-SHA drift detection (ADR-0019). `kanon verify` warns when an accepted/draft spec has changed since the last `fidelity update`. |
| Recovery model | `.kanon/.pending` sentinel + `.kanon/graph-rename.ops` ops-manifest | Per-file atomic writes + sentinel covers crash-consistent recovery (ADR-0024); `graph-rename` auto-replays via `recover_pending_rename` (ADR-0030); other sentinels emit a warning naming the idempotent command to re-run via `_PENDING_OP_TO_COMMAND`. |

### Verify is co-authoritative, not derived

Per `P-verification-co-authored.md` and ADR-0004, fixtures and tests are not generated from specs — they are co-authored. A spec is authoritative for *intent*; fixtures are authoritative for *behaviour*. When they disagree, both are inspected; neither auto-wins.

## Load-Bearing Principles

Six principles live at [`docs/foundations/principles/`](foundations/principles/). Each shapes a specific design decision in this kit; each is cited by frontmatter `realizes:` from the specs that depend on it.

| Principle | What it commits the kit to | Where it shows up in this instantiation |
|---|---|---|
| [`P-prose-is-code`](foundations/principles/P-prose-is-code.md) | Prose consumed by an LLM as instructions is code: reviewed, versioned, tested for unambiguity. | Audit-trail sentences in AGENTS.md gate sections ("Plan at `<path>` has been approved", "Working in worktree …"). Marker-delimited sections kept small (instructions buried past ~600 lines attract less attention). Fixture-author convention for `validated-against:` per ADR-0005. |
| [`P-specs-are-source`](foundations/principles/P-specs-are-source.md) | SDD artifacts (specs, ADRs, plans, foundations) are authoritative; code is downstream. | The fidelity lock (ADR-0019) tracks spec SHAs as the canonical artifact. `INV-*` anchors + `invariant_coverage:` (ADR-0018, ADR-0020) make every spec invariant addressable from a test. `scripts/check_kit_consistency.py` enforces byte-equality between the repo's canonical SDD docs and the kit's templates. |
| [`P-self-hosted-bootstrap`](foundations/principles/P-self-hosted-bootstrap.md) | The kit is developed using the kit. | This repo runs `kanon-sdd:3`, `kanon-worktrees:2`, `kanon-release:2`, `kanon-testing:3`, `kanon-security:2`, `kanon-deps:2`. Kit-side `aspects/kanon-sdd/files/docs/sdd-method.md` and the per-aspect protocol files are byte-equal to their repo-canonical counterparts. Bootstrap paradox (commits 1–3 pre-method) resolved by ADR-0002. |
| [`P-tiers-insulate`](foundations/principles/P-tiers-insulate.md) | Consumers move at the depth that fits their project; growing depth is non-destructive. | Per-aspect depth dials in the manifest registry; tier-up is additive, tier-down is non-destructive (existing files reported "beyond required" rather than deleted). ADR-0008 gives the contract; `_apply_tier_up` / `_apply_tier_down` in `cli.py` are the implementations. |
| [`P-cross-link-dont-duplicate`](foundations/principles/P-cross-link-dont-duplicate.md) | If a fact has one source, link to it; do not maintain two copies. | The byte-equality whitelist in `scripts/check_kit_consistency.py` catches when an editor forgets that `docs/sdd-method.md` (canonical) and `kit/aspects/kanon-sdd/files/docs/sdd-method.md` (template) are the same file. Aspect manifests and the cross-link graph (`_graph.py`) make spec ↔ principle ↔ persona references queryable. |
| [`P-verification-co-authored`](foundations/principles/P-verification-co-authored.md) | Fixtures + tests are authoritative alongside specs, not derived from them. | `tests/` is treated as a co-authoritative source. The fidelity lock tracks fixture SHAs alongside spec SHAs. Project-aspect `validators:` (ADR-0028) extend the verification surface without compromising kit authority (kit checks run after, can't be suppressed). |

A future principle, `P-agent-first` (drafted but not yet authored), captures the kit's stance that the default user is a solo developer running multiple LLM agents — not a traditional human team. The `solo-with-agents` persona stress-tests this; the `kanon-worktrees` aspect's "any file modification triggers a worktree, not concurrency detection" rule is the design move it shapes.

## Distinctive Instantiation Choices

The decisions that make kanon's SDD shape *this kit* and not generic SDD:

- **Aspects subsume tiers** (ADR-0012). Each aspect has its own depth dial. The `tier` vocabulary survives only as backward-compat sugar (`kanon tier set` aliases `aspect set-depth ... kanon-sdd N`).
- **Aspects are source-namespaced** (ADR-0028). `kanon-<local>` for kit-shipped, `project-<local>` for consumer-defined; bare names sugar to `kanon-` at every CLI input surface so existing invocations continue to work. Project-aspects live at `.kanon/aspects/project-<local>/` and participate in every aspect-management command.
- **Capabilities decouple identity from substitution** (ADR-0026). A `requires: ["kanon-sdd >= 1"]` predicate is a depth predicate; `requires: ["planning-discipline"]` is a 1-token capability-presence predicate that any aspect (kit or project) declaring `provides: [planning-discipline]` at depth ≥ 1 satisfies.
- **Crash-consistent atomicity, hybrid recovery** (ADR-0024 + ADR-0030). Per-file atomic writes are uniform; cross-file recovery is hybrid — `graph-rename` auto-replays via its ops-manifest; other sentinels rely on idempotent re-run with a sentinel-named warning telling the user which command to re-run.
- **Verification as a first-class layer** (ADR-0004). `kanon verify` is a CLI command, not a one-off script. The CI validators are designed to be runnable individually for triage. Project-aspects can extend the surface in-process via `validators:` (ADR-0028 INV-7) — non-overriding by ordering (kit checks run after).
- **Cross-harness shims, single canonical AGENTS.md** (ADR-0003). New harness support is a YAML entry, not a Python change. Marker-delimited sections in AGENTS.md let `kanon upgrade` heal kit content without touching consumer prose outside the markers.
- **Reference automation snippets are kit-shippable** (ADR-0013, ADR-0015). The vision's "no harness adapters / no runtime hooks" non-goal is preserved; what's narrowed is whether *deterministic copy-in templates* (release-pipeline GitHub Actions, pre-commit configs, Makefile snippets) ship in aspects. They do, when the operation is cryptographic / irreversible / persistent-state and an LLM agent cannot meaningfully gate it.
- **Cross-link graph as kit primitive** (ADR-0027 + spec-graph-orphans + spec-graph-rename). `_graph.py` exposes nodes + edges + inbound indices; `kanon graph orphans` is read-only; `kanon graph rename` is atomic via ops-manifest. Future `consumers-of <slug>` and `kanon graph diff` capabilities ride on the same primitive.
- **Status taxonomy includes `deferred`** (ADR-0007). A real spec file with intent + sketched invariants but no implementation, listed in `docs/plans/roadmap.md`. Distinguishes "scheduled for later" from "under discussion now."

## Where to read next

- For the generic SDD method, [`sdd-method.md`](sdd-method.md).
- For "what the kit promises consumers", [`docs/specs/README.md`](specs/README.md) (and especially [`aspects.md`](specs/aspects.md), [`project-aspects.md`](specs/project-aspects.md), [`cli.md`](specs/cli.md)).
- For "how kanon makes its decisions", [`docs/decisions/README.md`](decisions/README.md). ADR-0011, ADR-0012, ADR-0024, ADR-0026, ADR-0028, ADR-0030 are the load-bearing ones.
- For "what's coming", [`docs/plans/roadmap.md`](plans/roadmap.md).
