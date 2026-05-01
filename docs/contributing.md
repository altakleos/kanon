# Contributing to kanon

A guide for new human contributors. Reads top-to-bottom; you can stop at any section once you have what you need. If you are an LLM agent, read [`AGENTS.md`](../AGENTS.md) instead — it routes by trigger, not by intent.

This doc walks **abstract → concrete**: mental model first, then the aspect model, then runtime behaviour, then the source tree, then where your change goes, then CI gates, then the workflow end-to-end, then prohibitions.

For *why* the kit is shaped this way, follow links to ADRs in [`docs/decisions/`](decisions/) and design docs in [`docs/design/`](design/). This doc is a router, not a re-derivation.

```mermaid
flowchart TB
    subgraph consumer["Consumer repo"]
        AM["AGENTS.md"]
        KC[".kanon/ config"]
        DD["docs/ plans/ specs/"]
    end
    subgraph agent["LLM agent"]
        RP["reads protocols"]
        EA["emits audit sentences"]
    end
    subgraph kit["kanon-kit"]
        CLI["CLI<br/>(kanon init/upgrade)"]
        SRC["src/kanon/kit/"]
    end
    CLI -->|"scaffold prose"| AM
    CLI -->|"scaffold prose"| KC
    AM -->|"instructs"| RP
    RP --> EA
    EA -->|"audit trail in transcript"| DD
    DD -->|"kanon verify reads"| CLI
    SRC -->|"ships protocols"| AM
    style consumer fill:#f5f5f0,stroke:#999
    style agent fill:#f0f5ff,stroke:#6699cc
    style kit fill:#f0fff4,stroke:#66aa88
```

## 1. What kanon is, in one screen

kanon is a **portable, self-hosting kit** that packages development disciplines (Spec-Driven Development, worktree isolation, release discipline, …) as **prose an LLM agent reads and obeys**. A consumer runs `kanon init`, opens the project in Claude Code / Cursor / Codex / etc., and the agent reads the scaffolded `AGENTS.md` and follows the protocols it routes to.

Three properties define the kit ([vision.md](foundations/vision.md)):

- **Portable.** Same `AGENTS.md` works across nine harnesses via shim files. New harnesses are a data-file edit.
- **Aspect-oriented.** Disciplines are opt-in *aspects* with depth dials. Enable only what you need; grow without ceremony you don't need yet.
- **Self-hosting.** This repo is itself a kanon project at `kanon-sdd:3` + `kanon-worktrees:2` + others. `src/kanon/kit/` (the bundle the kit ships) and `docs/` (the kit's own SDD artifacts) share source-of-truth, CI-enforced. *If you can't use the kit to develop the kit, the kit isn't good enough.*

That self-hosting twist is the most surprising thing about the codebase: **the same code that templates consumer repos templates this repo**. `src/kanon/kit/aspects/<aspect>/` and `docs/` + `.kanon/` look duplicative until you realize the former is the source-of-truth and the latter is an instance of it.

For more: [`README.md`](../README.md) (install + quickstart), [`docs/foundations/vision.md`](foundations/vision.md) (the long form), [`docs/foundations/principles/README.md`](foundations/principles/README.md) (the *why*).

## 2. The aspect model in 90 seconds

An **aspect** is an opt-in bundle of (prose rules + protocols + AGENTS.md sections + scaffolded files), each with a **depth dial** (0–N). Most new behaviour lands inside *one aspect*, not across the kit. Knowing which aspect your change belongs to is half the navigation work.

```mermaid
flowchart LR
    subgraph shipped["Kit-shipped aspects"]
        SDD["kanon-sdd<br/>(stable)<br/>provides: planning-discipline,<br/>spec-discipline"]
        WT["kanon-worktrees<br/>provides: worktree-isolation"]
        REL["kanon-release<br/>provides: release-discipline"]
        TST["kanon-testing<br/>provides: test-discipline"]
        SEC["kanon-security<br/>provides: security-discipline"]
        DEP["kanon-deps<br/>provides: dependency-hygiene"]
        FID["kanon-fidelity<br/>provides: behavioural-verification"]
    end
    subgraph project["Project aspects"]
        PA["project-&lt;local&gt;"]
    end
    REG["_load_aspect_registry()"]
    subgraph cli["CLI surface"]
        AL["aspect list/info"]
        AA["aspect add/remove"]
        AD["aspect set-depth<br/>set-config"]
        VR["verify"]
    end
    shipped --> REG
    project --> REG
    REG --> AL
    REG --> AA
    REG --> AD
    REG --> VR
    style SDD fill:#e8f5e9,stroke:#4caf50
```

The 7 kit-shipped aspects (verbatim from [`src/kanon/kit/manifest.yaml:35-108`](../src/kanon/kit/manifest.yaml)):

| Aspect | Stability | Depth range | Default | What it gives you |
|---|---|---|---:|---|
| `kanon-sdd` | **stable** | 0–3 | 1 | Plans, specs, design docs, foundations |
| `kanon-worktrees` | experimental | 0–2 | 1 | Worktree isolation prose + shell helpers |
| `kanon-release` | experimental | 0–2 | 1 | Release checklist, preflight, `kanon release` gate |
| `kanon-testing` | experimental | 0–3 | 1 | Test discipline, AC-first TDD, error diagnosis |
| `kanon-security` | experimental | 0–2 | 1 | Secure-defaults protocol + CI scanner |
| `kanon-deps` | experimental | 0–2 | 1 | Dependency hygiene + CI scanner |
| `kanon-fidelity` | experimental | 0–1 | 1 | Behavioural conformance via lexical assertions |

Default `kanon init` enables 5 of the 7 (`kanon-sdd`, `kanon-testing`, `kanon-security`, `kanon-deps`, `kanon-worktrees`); `kanon-release` and `kanon-fidelity` are opt-in ([`manifest.yaml:24-29`](../src/kanon/kit/manifest.yaml)). Aspects compose via a `provides:` capability registry — a dependent's `requires: ["planning-discipline"]` is satisfied by *any* enabled aspect that declares the capability, kit-shipped or project-defined ([ADR-0026](decisions/0026-aspect-provides-and-generalised-requires.md)).

For mechanism (sub-manifest shape, depth resolution, marker namespacing): [`docs/design/aspect-model.md`](design/aspect-model.md). Not re-explained here.

## 3. What happens when you run `kanon`

The same machinery powers `init`, `upgrade`, `verify`, and `aspect set-depth`: load the aspect registry, build a bundle, write it atomically with a `.pending` sentinel, clear the sentinel. The canonical example is `kanon init`.

```mermaid
sequenceDiagram
    actor User
    participant CLI as cli.py
    participant M as _manifest
    participant S as _scaffold
    participant A as _atomic
    participant FS as filesystem

    User->>CLI: kanon init [--profile all]
    CLI->>M: _load_aspect_registry(target)
    M-->>CLI: kit + project aspect registry
    CLI->>S: _build_bundle(aspects, context)
    S-->>CLI: {path: rendered_content}
    CLI->>S: _assemble_agents_md(aspects)
    Note over S: hard-gates table + protocols-index<br/>+ marker bodies (dynamic)
    CLI->>A: write_sentinel(_OP_INIT)
    A->>FS: .kanon/.pending
    CLI->>S: _write_tree_atomically(target, bundle)
    S->>A: atomic_write_text per file
    Note over A,FS: tmp → fsync → rename → fsync parent
    A->>FS: files
    CLI->>A: atomic_write_text(AGENTS.md)
    Note over CLI,A: AGENTS.md written out-of-band<br/>so init always refreshes (ADR-0038)
    CLI->>A: clear_sentinel()
    CLI-->>User: "Next steps:" hints
```

Three things to internalize:

1. **The I/O surface is small.** Only [`_scaffold.py`](../src/kanon/_scaffold.py) and [`_manifest.py`](../src/kanon/_manifest.py) touch the filesystem; everything else is pure-ish. New filesystem writes flow through `_write_tree_atomically()` so the sentinel discipline is preserved.
2. **Atomic writes + sentinels = crash consistency.** Every multi-file mutation writes `.kanon/.pending` *before* the first byte and clears it *after* the last. The next `kanon` invocation reads the sentinel and replays. See [ADR-0024](decisions/0024-crash-consistent-atomicity.md) and [ADR-0030](decisions/0030-recovery-model.md). Don't bypass this.
3. **`init`, `upgrade`, `verify`, `aspect set-depth` share the same skeleton.** `init` is the only one that doesn't call `_check_pending_recovery` first (greenfield: nothing to recover); the others do.

`kanon verify .` is the inverse — instead of writing, it inspects what's there. The verify pipeline is in §6 alongside the gate matrix.

## 4. The source tree: where things live

The codebase has four layers, top-down: dispatcher → CLI-support → domain core → kernel + validators.

```mermaid
graph TB
    subgraph entry["Entry point"]
        CLIP["cli.py"]
    end
    subgraph support["CLI-support layer"]
        CLH["_cli_helpers.py"]
        CLA["_cli_aspect.py"]
    end
    subgraph domain["Domain core"]
        MAN["_manifest.py"]
        SCA["_scaffold.py"]
        VER["_verify.py"]
        FID["_fidelity.py"]
        GR["_graph.py"]
        PF["_preflight.py"]
        DT["_detect.py"]
    end
    subgraph leaf["Kernel + validators"]
        AT["_atomic.py"]
        BN["_banner.py"]
        VAL["_validators/*"]
    end
    CLIP --> CLH & CLA & MAN & SCA & VER & FID & GR
    CLH --> MAN
    CLA --> MAN
    SCA --> MAN & AT
    VER --> MAN & FID & VAL
    FID --> MAN
    PF --> DT
    AT --> BN
    style entry fill:#e3f2fd,stroke:#1976d2
    style support fill:#e8f5e9,stroke:#388e3c
    style domain fill:#fff3e0,stroke:#f57c00
    style leaf fill:#fce4ec,stroke:#c62828
```

| Module | LOC | Role | Primary tests | Governing ADR |
|---|---:|---|---|---|
| [`cli.py`](../src/kanon/cli.py) | 1,121 | Click dispatcher; 9 commands, 11 subcommands | `test_cli.py`, `test_cli_aspect.py`, `test_cli_verify.py`, `test_cli_fidelity.py` | — |
| [`_cli_helpers.py`](../src/kanon/_cli_helpers.py) | 321 | Pure-logic CLI helpers (parse, validate, recover) | `test_cli_helpers.py` | — |
| [`_cli_aspect.py`](../src/kanon/_cli_aspect.py) | 194 | `aspect set-depth` engine | `test_set_aspect_depth_helpers.py`, `test_cli_aspect.py` | [ADR-0012](decisions/0012-aspect-model.md) |
| [`_manifest.py`](../src/kanon/_manifest.py) | 662 | Loads kit + project aspect registry; placeholder rendering | `test_kit_integrity.py`, `test_aspect_provides.py` | [ADR-0011](decisions/0011-kit-bundle-refactor.md), [ADR-0028](decisions/0028-project-aspects.md) |
| [`_scaffold.py`](../src/kanon/_scaffold.py) | 636 | AGENTS.md assembly, marker rewrite, harness shim render, atomic tree write | `test_scaffold_marker_hardening.py`, `test_scaffold_symlink.py`, `test_cli.py` | [ADR-0034](decisions/0034-routing-index-agents-md.md) |
| [`_verify.py`](../src/kanon/_verify.py) | 374 | Validation orchestration; structural checks → validators | `test_cli_verify.py`, `test_verify_validators.py` | [ADR-0004](decisions/0004-verification-co-authoritative-source.md) |
| [`_fidelity.py`](../src/kanon/_fidelity.py) | 482 | Lexical assertion engine over `.dogfood.md` captures (text-only) | `test_fidelity.py`, `test_cli_fidelity.py` | [ADR-0029](decisions/0029-verification-fidelity-replay-carveout.md), [ADR-0031](decisions/0031-fidelity-aspect.md) |
| [`_graph.py`](../src/kanon/_graph.py) | 733 | Cross-link graph; powers `graph orphans` and `graph rename` | `test_graph.py`, `test_graph_orphans.py`, `test_graph_rename.py` | — |
| [`_rename.py`](../src/kanon/_rename.py) | 517 | Crash-consistent ops-manifest replay for `graph rename` | `test_graph_rename.py` | [ADR-0027](decisions/0027-graph-rename-ops-manifest.md), [ADR-0030](decisions/0030-recovery-model.md) |
| [`_preflight.py`](../src/kanon/_preflight.py) | 124 | Staged check runner (commit ⊂ push ⊂ release) | `test_preflight.py` | [ADR-0036](decisions/0036-secure-defaults-config-trust-carveout.md) |
| [`_detect.py`](../src/kanon/_detect.py) | 71 | Project-type detection (pyproject / package.json / Cargo / go.mod) | `test_detect.py` | — |
| [`_atomic.py`](../src/kanon/_atomic.py) | 71 | `atomic_write_text` + `.pending` sentinel | `test_atomic.py` | [ADR-0024](decisions/0024-crash-consistent-atomicity.md) |
| [`_banner.py`](../src/kanon/_banner.py) | 31 | Brand banner — single source of truth, bytes asserted | `test_banner.py` | — |

In-process kit validators in [`src/kanon/_validators/`](../src/kanon/_validators/) — called by `_verify.py` only:

| Validator | Aspect | Depth-min | Purpose |
|---|---|---:|---|
| [`plan_completion.py`](../src/kanon/_validators/plan_completion.py) | `kanon-sdd` | 1 | Flag plans `status: done` with unchecked tasks |
| [`index_consistency.py`](../src/kanon/_validators/index_consistency.py) | `kanon-sdd` | 1 | Flag duplicate link targets in `docs/*/README.md` |
| [`link_check.py`](../src/kanon/_validators/link_check.py) | `kanon-sdd` | 2 | Flag broken relative markdown links under `docs/` |
| [`adr_immutability.py`](../src/kanon/_validators/adr_immutability.py) | `kanon-sdd` | 2 | Flag body changes to accepted ADRs in HEAD commit |
| [`spec_design_parity.py`](../src/kanon/_validators/spec_design_parity.py) | `kanon-sdd` | 3 | Warn on accepted specs without companion design doc |
| [`test_import_check.py`](../src/kanon/_validators/test_import_check.py) | `kanon-testing` | 2 | Flag `tests/ci/test_*.py` referencing missing CI scripts |

Other trees, one sentence each:

- [`src/kanon/kit/`](../src/kanon/kit/) — the bundle the kit ships; one directory per aspect (`aspects/kanon-<local>/`), plus kit-global files (`manifest.yaml`, `agents-md-base.md`, `kit.md`, `harnesses.yaml`).
- [`tests/`](../tests/) — 800 tests; `test_e2e_*.py` deselected by default (`e2e` marker); `tests/ci/test_check_*.py` covers the CI scripts.
- [`ci/`](../ci/) — 13 standalone validators (kit-internal); some have consumer-facing copies under `src/kanon/kit/aspects/<name>/files/ci/`.
- [`docs/decisions/`](decisions/) — 39 ADRs; index in [`README.md`](decisions/README.md), category-tagged.
- [`docs/specs/`](specs/) — 33 specs; invariants carry `INV-*` anchors with `verified-by:` mappings.
- [`docs/plans/`](.) — execution plans; one per non-trivial change, named by slug.

## 5. Where does my change go?

First: which aspect (if any) does this belong to? Then: do I need a spec, a plan, both, or neither? Read [`plan-before-build`](../.kanon/protocols/kanon-sdd/plan-before-build.md) § 1 and [`spec-before-design`](../.kanon/protocols/kanon-sdd/spec-before-design.md) § 1 for the trivial-vs-non-trivial classifications.

| If your change is… | It belongs in… | Spec / plan needed? |
|---|---|---|
| New CLI command, flag, or subcommand | [`src/kanon/cli.py`](../src/kanon/cli.py) + spec amendment in [`docs/specs/cli.md`](specs/cli.md) | **Spec** + plan |
| New protocol that gates agent behaviour | `src/kanon/kit/aspects/<aspect>/protocols/<name>.md` + sub-manifest entry | Plan |
| Edit existing protocol prose | `src/kanon/kit/aspects/<aspect>/protocols/<name>.md` + recapture fidelity fixtures per [`fidelity-discipline`](../.kanon/protocols/kanon-fidelity/fidelity-discipline.md) | Plan |
| New aspect | New dir `src/kanon/kit/aspects/kanon-<local>/` + entry in [`src/kanon/kit/manifest.yaml`](../src/kanon/kit/manifest.yaml) + spec | **Spec** + ADR + plan |
| Add a CI check | `ci/check_<name>.py` + wire into [`.github/workflows/checks.yml`](../.github/workflows/checks.yml) + test in `tests/ci/` | Plan |
| Add an in-process kit validator | `src/kanon/_validators/<name>.py` + register in target aspect's `manifest.yaml` `validators:` | Plan |
| Bundle file change (template, scaffolded README) | `src/kanon/kit/aspects/<aspect>/files/...` or `src/kanon/kit/<file>` | Plan |
| Bug fix (single function, single test) | Direct fix; no plan iff truly trivial per `plan-before-build` § 1 | Trivial path: no plan |
| New ADR | `docs/decisions/NNNN-<slug>.md` + entry in [`docs/decisions/README.md`](decisions/README.md) | No plan; the ADR *is* the artifact |

## 6. The gate matrix: what will block your PR

Three layers fire when you push:

1. **CI workflow chain.** [`verify.yml`](../.github/workflows/verify.yml) (on push/PR) and [`release.yml`](../.github/workflows/release.yml) (on `v*` tag) both `workflow_call` into the reusable [`checks.yml`](../.github/workflows/checks.yml).
2. **`ci/check_*.py` scripts** (one process per check). 13 scripts; 4 are soft (warn but don't block).
3. **In-process kit validators** wired by aspect manifests, run by `kanon verify .`.

```mermaid
flowchart TB
    PUSH["git push / pull_request"]
    TAG["git push v* tag"]
    subgraph checks_yml["checks.yml (reusable)"]
        MAT["matrix: py3.10-3.13<br/>x ubuntu + macos"]
        PT["pytest"]
        LN["ruff + mypy"]
        CI["13 ci/check_*.py validators"]
        MAT --> PT & LN & CI
    end
    PUSH --> verify_yml["verify.yml"]
    TAG --> release_yml["release.yml"]
    verify_yml --> checks_yml
    verify_yml --> e2e["e2e job<br/>(pytest -m e2e)"]
    release_yml --> checks_yml
    release_yml --> bld["build wheel<br/>+ check_package_contents.py"]
    bld --> pub["publish<br/>(OIDC trusted publisher)"]
```

The verify pipeline (run by both CI and local `kanon verify .`):

```mermaid
sequenceDiagram
    actor User
    participant CLI as cli.py
    participant V as _verify
    participant PV as project-validators
    participant KV as kit-validators
    participant F as _fidelity

    User->>CLI: kanon verify [path]
    CLI->>V: run_verify(path)
    V->>V: structural checks<br/>(config, manifest, links)
    V->>PV: import & run<br/>project validators
    PV-->>V: findings[]
    V->>KV: import & run<br/>kit validators
    Note over KV,V: kit results OVERWRITE<br/>project clears (ADR-0028)
    KV-->>V: findings[]
    V->>V: has behavioural-verification<br/>capability? (ADR-0029)
    alt capability present
        V->>F: fidelity_replay(fixtures)
        F-->>V: replay results
    end
    V-->>CLI: JSON report
    CLI-->>User: status: ok | warn | fail
```

The full gate matrix:

| Gate | Hard / soft | What it enforces | Local fix |
|---|---|---|---|
| `pytest -v` | Hard | All non-e2e tests pass on py3.10–3.13 | `make test` |
| `ruff check src/ tests/ ci/` | Hard | Lint clean | `make lint` |
| `mypy src/kanon` | Hard | `--strict` type check | `make typecheck` |
| `ci/check_foundations.py` | Hard | Principles + personas frontmatter; no orphans | `python ci/check_foundations.py` |
| `ci/check_links.py` | Hard | Every relative markdown link resolves | `python ci/check_links.py` |
| `ci/check_kit_consistency.py` | Hard | Bundle byte-equality + manifest validity | `python ci/check_kit_consistency.py` |
| `ci/check_adr_immutability.py` | Hard | Accepted ADR bodies unchanged unless `Allow-ADR-edit:` trailer ([ADR-0032](decisions/0032-adr-immutability-gate.md)) | Append a `Historical Note` instead |
| `ci/check_process_gates.py` | Hard | Plan-before-build + spec-before-design honoured by the diff | Write the missing plan/spec |
| `ci/check_test_quality.py` | Hard | No empty test files, no zero-test-function files | Add a real assertion |
| `ci/check_verified_by.py` | Hard | Spec invariants reference real tests | Add `verified-by:` in spec frontmatter |
| `ci/check_invariant_ids.py` | Hard | `INV-*` anchors unique and resolved | Renumber or fix the dangling reference |
| `ci/check_security_patterns.py` | Soft (warn) | No `shell=True`, `eval`, hardcoded creds without `# nosec` | Fix or annotate per [ADR-0036](decisions/0036-secure-defaults-config-trust-carveout.md) |
| `ci/check_deps.py` | Soft (warn) | No unpinned or duplicate-purpose deps | Pin or justify |
| `ci/check_status_consistency.py` | Soft (warn) | ADR/spec/plan status frontmatter is coherent | Fix the status |
| `ci/check_commit_messages.py` | Soft (script always exits 0) | Conventional Commits prefix on each commit | Reword via interactive rebase |
| `ci/check_package_contents.py` | Hard (release-only) | Wheel matches source-of-truth + version concordance with tag | `python ci/check_package_contents.py --wheel <path> --tag <tag>` |
| `kanon verify .` | Hard | Self-hosting structural + validator + fidelity checks pass | Read [`verify-triage`](../.kanon/protocols/kanon-sdd/verify-triage.md) |

A typical local pre-push: `make check && python ci/check_links.py && python ci/check_kit_consistency.py && kanon verify .`

Soft gates surface as warnings in the workflow log but do not block the PR. If a soft gate is firing on something you can't fix immediately, add a justification in the PR description rather than ignoring it.

## 7. The contribution workflow, end to end

```bash
# 1. Open a worktree (every file modification, including docs and tests)
git worktree add .worktrees/<slug> -b wt/<slug>
cd .worktrees/<slug>

# 2. If non-trivial, write the plan first; get user approval
$EDITOR docs/plans/<slug>.md
# State the audit sentence: "Plan at docs/plans/<slug>.md has been approved."

# 3. Edit, then run gates locally
make check
python ci/check_links.py
kanon verify .

# 4. Commit (Conventional Commits; reference plan slug)
git add <specific-files>
git commit -m "feat: <summary> (plan: <slug>)"

# 5. Push and open PR
git push -u origin wt/<slug>
gh pr create --fill --base main

# 6. After merge, tear down
git worktree remove .worktrees/<slug>
git branch -d wt/<slug>
```

Rules for steps 1, 2, 4, 5: [`branch-hygiene`](../.kanon/protocols/kanon-worktrees/branch-hygiene.md) and [`worktree-lifecycle`](../.kanon/protocols/kanon-worktrees/worktree-lifecycle.md). Pre-merge sweep: [`completion-checklist`](../.kanon/protocols/kanon-sdd/completion-checklist.md).

Changelog: append every user-visible change to `## [Unreleased]` in [`CHANGELOG.md`](../CHANGELOG.md) in the same commit. Refactors, internal tests, and docs-only edits don't need an entry. Full convention in [`AGENTS.md § Contribution Conventions`](../AGENTS.md).

## 8. Five things you cannot do

These are non-negotiable contracts. CI catches most but not all of them.

1. **Modify accepted ADR bodies.** Append a `## Historical Note` instead, or use the `Allow-ADR-edit: NNNN — <reason>` commit trailer. Carve-out: [ADR-0032](decisions/0032-adr-immutability-gate.md); enforced by `ci/check_adr_immutability.py`.
2. **Weaken a fidelity assertion to make a fixture pass.** Fix the prose, fix the agent's prompt, or remove the assertion deliberately with a note. See [`fidelity-discipline`](../.kanon/protocols/kanon-fidelity/fidelity-discipline.md) § 3.
3. **Bypass `_atomic.py` for kit-managed files.** Use `atomic_write_text()` and the `.pending` sentinel pattern. The crash-consistency contract is non-negotiable. See [ADR-0024](decisions/0024-crash-consistent-atomicity.md).
4. **Add `subprocess.run(..., shell=True)` without an `# nosec — see ADR-0036` annotation and a same-repo trust-boundary justification.** Carve-out grammar: [`secure-defaults`](../.kanon/protocols/kanon-security/secure-defaults.md) § Injection.
5. **Edit kit-rendered marker bodies in consumer trees.** Anything between `<!-- kanon:begin:... -->` and `<!-- kanon:end:... -->` is owned by `kanon upgrade`; hand-edits are silently overwritten on next refresh. Edit the source under `src/kanon/kit/` instead.

## See also

- [`AGENTS.md`](../AGENTS.md) — the agent-facing complement of this doc
- [`docs/sdd-method.md`](sdd-method.md) — the SDD layer stack and document authority
- [`docs/design/aspect-model.md`](design/aspect-model.md) — the mechanism behind §§ 2–3
- [`docs/design/scaffold-v2.md`](design/scaffold-v2.md) — how `_scaffold.py` assembles the bundle
- [`docs/decisions/README.md`](decisions/README.md) — ADR index, category-tagged
- [`docs/foundations/vision.md`](foundations/vision.md) and [`docs/foundations/principles/README.md`](foundations/principles/README.md) — the *why*
