# Contributing to kanon

A navigation map for human contributors. If you are an LLM agent, read [`AGENTS.md`](../AGENTS.md) instead — it routes by trigger, not by intent.

This doc answers four questions:

1. Where does the code live, and what touches what?
2. Where does my change go?
3. What gates will fire on my PR, and how do I run them locally?
4. What can I not do?

For *why* the kit is shaped this way, follow links to ADRs in `docs/decisions/` — they hold the reasoning. This doc is a router, not a re-explanation.

## 1. Module map

Source lives under [`src/kanon/`](../src/kanon/). The dispatcher is [`cli.py`](../src/kanon/cli.py); everything else is a leaf module it composes.

| Module | LOC | Role | Primary tests | Governing ADR |
|---|---:|---|---|---|
| [`cli.py`](../src/kanon/cli.py) | 1,121 | Click dispatcher; 9 commands, 11 subcommands | `test_cli.py`, `test_cli_aspect.py`, `test_cli_verify.py`, `test_cli_fidelity.py` | — |
| [`_cli_helpers.py`](../src/kanon/_cli_helpers.py) | 321 | Pure-logic CLI helpers (parse, validate, recover) | `test_cli_helpers.py` | — |
| [`_cli_aspect.py`](../src/kanon/_cli_aspect.py) | 194 | `aspect set-depth` engine | `test_set_aspect_depth_helpers.py`, `test_cli_aspect.py` | [ADR-0012](decisions/0012-aspect-model.md) |
| [`_manifest.py`](../src/kanon/_manifest.py) | 662 | Loads kit + project aspect registry; placeholder rendering | `test_kit_integrity.py`, `test_aspect_provides.py` | [ADR-0011](decisions/0011-kit-bundle-refactor.md), [ADR-0028](decisions/0028-project-aspects.md) |
| [`_scaffold.py`](../src/kanon/_scaffold.py) | 636 | AGENTS.md assembly, marker rewrite, harness shim render, atomic tree write | `test_scaffold_marker_hardening.py`, `test_scaffold_symlink.py`, `test_cli.py` | [ADR-0034](decisions/0034-routing-index-agents-md.md) |
| [`_verify.py`](../src/kanon/_verify.py) | 374 | Validation orchestration; runs structural checks then validators | `test_cli_verify.py`, `test_verify_validators.py` | [ADR-0004](decisions/0004-verification-co-authoritative-source.md) |
| [`_fidelity.py`](../src/kanon/_fidelity.py) | 482 | Lexical assertion engine over `.dogfood.md` captures (text-only) | `test_fidelity.py`, `test_cli_fidelity.py` | [ADR-0029](decisions/0029-verification-fidelity-replay-carveout.md), [ADR-0031](decisions/0031-fidelity-aspect.md), [ADR-0033](decisions/0033-fidelity-quantitative-families.md) |
| [`_graph.py`](../src/kanon/_graph.py) | 733 | Cross-link graph (principles, personas, specs, capabilities); powers `graph orphans` and `graph rename` | `test_graph.py`, `test_graph_orphans.py`, `test_graph_rename.py` | — |
| [`_rename.py`](../src/kanon/_rename.py) | 517 | Crash-consistent ops-manifest replay for `graph rename` | `test_graph_rename.py` | [ADR-0027](decisions/0027-graph-rename-ops-manifest.md), [ADR-0030](decisions/0030-recovery-model.md) |
| [`_preflight.py`](../src/kanon/_preflight.py) | 124 | Staged check runner (commit ⊂ push ⊂ release) | `test_preflight.py` | [ADR-0036](decisions/0036-secure-defaults-config-trust-carveout.md) |
| [`_detect.py`](../src/kanon/_detect.py) | 71 | Project-type detection (pyproject / package.json / Cargo / go.mod) | `test_detect.py` | — |
| [`_atomic.py`](../src/kanon/_atomic.py) | 71 | `atomic_write_text` + `.pending` sentinel | `test_atomic.py` | [ADR-0024](decisions/0024-crash-consistent-atomicity.md) |
| [`_banner.py`](../src/kanon/_banner.py) | 31 | Brand banner — single source of truth, bytes asserted | `test_banner.py` | — |
| [`__init__.py`](../src/kanon/__init__.py) | 3 | `__version__` only | `test_kit_integrity.py` | — |

In-process kit validators in [`src/kanon/_validators/`](../src/kanon/_validators/) — called by `_verify.py`, never directly by `cli.py`:

| Validator | LOC | Fires at | Tests |
|---|---:|---|---|
| [`plan_completion.py`](../src/kanon/_validators/plan_completion.py) | 43 | `kanon-sdd >= 1` | `test_validators.py` |
| [`link_check.py`](../src/kanon/_validators/link_check.py) | 44 | `kanon-sdd >= 2` | `test_validators.py` |
| [`adr_immutability.py`](../src/kanon/_validators/adr_immutability.py) | 126 | `kanon-sdd >= 2` | `test_validators.py` |
| [`index_consistency.py`](../src/kanon/_validators/index_consistency.py) | 45 | `kanon-sdd >= 1` | `test_index_consistency.py` |
| [`test_import_check.py`](../src/kanon/_validators/test_import_check.py) | 32 | `kanon-testing >= 2` | `test_import_check.py` |
| [`spec_design_parity.py`](../src/kanon/_validators/spec_design_parity.py) | 59 | `kanon-sdd >= 2` | `test_spec_design_parity.py` |

Bundle source-of-truth lives under [`src/kanon/kit/`](../src/kanon/kit/) — one directory per kit-shipped aspect (`aspects/kanon-<local>/`), plus the kit-global files (`manifest.yaml`, `agents-md-base.md`, `kit.md`, `harnesses.yaml`).

## 2. Where does my change go?

| If your change is… | It belongs in… | Spec / plan needed? |
|---|---|---|
| New CLI command, flag, or subcommand | [`src/kanon/cli.py`](../src/kanon/cli.py) + spec amendment in [`docs/specs/cli.md`](specs/cli.md) | Spec amendment + plan |
| New protocol that gates agent behaviour | `src/kanon/kit/aspects/<aspect>/protocols/<name>.md` + sub-manifest entry | Plan; usually no spec (protocols are aspect-scoped) |
| New aspect | New directory `src/kanon/kit/aspects/kanon-<local>/` + entry in [`src/kanon/kit/manifest.yaml`](../src/kanon/kit/manifest.yaml) + spec | **Spec required** + ADR + plan |
| Add a check that runs in CI | `ci/check_<name>.py` + wire into [`.github/workflows/checks.yml`](../.github/workflows/checks.yml) + test in `tests/ci/` | Plan |
| Add an in-process kit validator | `src/kanon/_validators/<name>.py` + register in target aspect's `manifest.yaml` `validators:` list | Plan; usually no spec |
| Bundle file change (template, scaffolded README, kit.md text) | `src/kanon/kit/aspects/<aspect>/files/...` or `src/kanon/kit/<file>` | Plan |
| Bug fix (single function, single test) | Direct fix; no plan iff truly trivial per `plan-before-build` § 1 | Trivial path: no plan |
| New ADR | `docs/decisions/NNNN-<slug>.md` (next number) + entry in `docs/decisions/README.md` | No plan; ADR *is* the artifact |

If unsure: read [`plan-before-build`](../.kanon/protocols/kanon-sdd/plan-before-build.md) § 1 ("Classify the change") and [`spec-before-design`](../.kanon/protocols/kanon-sdd/spec-before-design.md) § 1.

## 3. The gate matrix

Every check that can block your PR. CI orchestration: [`verify.yml`](../.github/workflows/verify.yml) and [`release.yml`](../.github/workflows/release.yml) both call [`checks.yml`](../.github/workflows/checks.yml) (a `workflow_call` reusable job). For local runs, use [`Makefile`](../Makefile) (`make check`).

| Gate | Hard / soft | What it enforces | Local fix |
|---|---|---|---|
| `pytest -v` | Hard | All non-e2e tests pass on py3.10–3.13 | `make test` |
| `ruff check src/ tests/ ci/` | Hard | Lint clean | `make lint` |
| `mypy src/kanon` | Hard | `--strict` type check | `make typecheck` |
| `ci/check_foundations.py` | Hard | Principles + personas have required frontmatter; no orphans | `python ci/check_foundations.py` |
| `ci/check_links.py` | Hard | Every relative markdown link resolves | `python ci/check_links.py` |
| `ci/check_kit_consistency.py` | Hard | Kit-side aspect manifests + bundle file ownership are internally consistent | `python ci/check_kit_consistency.py` |
| `ci/check_adr_immutability.py` | Hard | Accepted ADR bodies unchanged unless `Allow-ADR-edit:` trailer used ([ADR-0032](decisions/0032-adr-immutability-gate.md)) | Read [`adr-immutability`](../.kanon/protocols/kanon-sdd/adr-immutability.md); add a `Historical Note` section instead |
| `ci/check_process_gates.py` | Hard | Plan-before-build + spec-before-design gates honoured by the diff | Write the missing plan/spec |
| `ci/check_test_quality.py` | Hard | No empty test files, no zero-test-function files | Add a real assertion |
| `ci/check_verified_by.py` | Hard | Spec invariants reference real tests | Add `verified-by:` mapping in spec frontmatter |
| `ci/check_invariant_ids.py` | Hard | `INV-*` anchors are unique and resolved | Renumber or fix the dangling reference |
| `ci/check_package_contents.py` | Hard | Wheel manifest matches source-of-truth | Re-check `MANIFEST.in` / `pyproject.toml` build targets |
| `ci/check_security_patterns.py` | Soft (warn) | No `shell=True`, `eval(`, hard-coded creds, etc. unless `# nosec` annotated | Either fix or annotate per [ADR-0036](decisions/0036-secure-defaults-config-trust-carveout.md) |
| `ci/check_deps.py` | Soft (warn) | No unpinned or duplicate-purpose deps | Pin or justify |
| `ci/check_status_consistency.py` | Soft (warn) | ADR / spec / plan `status:` frontmatter is internally coherent | Fix the status |
| `ci/check_commit_messages.py` | Soft (warn) | Conventional Commits prefix on each commit | Reword via interactive rebase |
| `kanon verify .` | Hard | Self-hosting structural checks pass | Read [`verify-triage`](../.kanon/protocols/kanon-sdd/verify-triage.md) |

A typical local pre-push: `make check && python ci/check_links.py && python ci/check_kit_consistency.py && kanon verify .`

## 4. Hot-path callouts

Things that look load-bearing because they are.

- **[`cli.py`](../src/kanon/cli.py) is large by design, not by accident.** The kit shipped a 32%-reduction refactor in v0.3.0a7 (1,589 → 1,084 LOC) by extracting `_cli_helpers.py` and `_cli_aspect.py`. Further extractions are welcome but should keep the *dispatch* in `cli.py` and push *logic* outward.
- **[`_scaffold.py`](../src/kanon/_scaffold.py) + [`_manifest.py`](../src/kanon/_manifest.py) own all I/O.** If you are touching the filesystem from anywhere else, ask why. New file writes flow through `_write_tree_atomically()` so `.pending` sentinel discipline is preserved.
- **[`_atomic.py`](../src/kanon/_atomic.py) is sacrosanct.** Don't bypass `atomic_write_text()` for kit-managed files. The fsync + rename + parent-fsync sequence is what makes `kanon` survive `kill -9` mid-write. See [ADR-0024](decisions/0024-crash-consistent-atomicity.md).
- **The `.pending` sentinel is the recovery mechanism.** Multi-file mutations write the sentinel before the first byte and clear it after the last byte. The next `kanon` invocation reads it and replays. Don't add a multi-file mutation without using `write_sentinel(...)` / `clear_sentinel(...)` from `_atomic.py`. See [ADR-0030](decisions/0030-recovery-model.md).
- **Aspect manifests drive scaffolding, not Python code.** Adding a file to a kit-aspect's bundle = new entry in `src/kanon/kit/aspects/<name>/manifest.yaml`, not new code in `_scaffold.py`. The data-driven pattern is what enables project-aspects ([ADR-0028](decisions/0028-project-aspects.md)).
- **The fidelity engine is text-only by carve-out, not by accident.** [`_fidelity.py`](../src/kanon/_fidelity.py) is forbidden from importing `subprocess`, calling LLMs, or executing test runners — see the module docstring and [ADR-0029](decisions/0029-verification-fidelity-replay-carveout.md). Any "we should just call out to X" instinct is a smell.

## 5. Worktree workflow recap

Every file modification — including docs and tests — happens on a `wt/<slug>` branch in a `.worktrees/<slug>/` directory. Full rules in [`branch-hygiene`](../.kanon/protocols/kanon-worktrees/branch-hygiene.md) and [`worktree-lifecycle`](../.kanon/protocols/kanon-worktrees/worktree-lifecycle.md).

```bash
git worktree add .worktrees/<slug> -b wt/<slug>
cd .worktrees/<slug>
# ... edit, test, commit ...
git push -u origin wt/<slug>
gh pr create --fill --base main
```

After merge, tear down:

```bash
git worktree remove .worktrees/<slug>
git branch -d wt/<slug>   # only after merge
```

## 6. The 5 things you can't do

1. **Modify accepted ADR bodies.** Append a `## Historical Note` instead, or use the `Allow-ADR-edit: NNNN — <reason>` commit trailer. [ADR-0032](decisions/0032-adr-immutability-gate.md) is enforced in CI.
2. **Weaken a fidelity assertion to make a fixture pass.** Fix the prose, fix the agent's prompt, or remove the assertion deliberately with a note. See [`fidelity-discipline`](../.kanon/protocols/kanon-fidelity/fidelity-discipline.md) § 3.
3. **Bypass `_atomic.py` for kit-managed files.** Use `atomic_write_text()` and the sentinel pattern. The crash-consistency contract is non-negotiable.
4. **Add `subprocess.run(..., shell=True)` without an `# nosec — see ADR-0036` annotation and a same-repo trust-boundary justification.** [`secure-defaults`](../.kanon/protocols/kanon-security/secure-defaults.md) § Injection spells out the carve-out exactly.
5. **Edit kit-rendered marker bodies in consumer trees.** Anything between `<!-- kanon:begin:... -->` and `<!-- kanon:end:... -->` is owned by `kanon upgrade`; hand-edits will be silently overwritten on next refresh. Edit the source under `src/kanon/kit/` instead.

## See also

- [`AGENTS.md`](../AGENTS.md) — the agent-facing routing index
- [`docs/sdd-method.md`](sdd-method.md) — the SDD layer stack and document authority
- [`docs/design/aspect-model.md`](design/aspect-model.md) — why aspects are the unit of opt-in discipline
- [`docs/design/scaffold-v2.md`](design/scaffold-v2.md) — how the bundle is assembled
- [`docs/decisions/README.md`](decisions/README.md) — ADR index, tagged by category
