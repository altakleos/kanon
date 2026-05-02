---
status: draft
date: 2026-05-02
---
# ADR-0049: Monorepo layout for the protocol substrate

## Context

[ADR-0048](0048-kanon-as-protocol-substrate.md) committed kanon to a protocol-substrate shape. [ADR-0043](0043-distribution-boundary-and-cadence.md) committed to a three-distribution split (`kanon-substrate` + `kanon-reference` + `kanon-kit`). [ADR-0044](0044-substrate-self-conformance.md) committed to substrate-independence + self-host conformance. The Phase A implementation (PRs #61–85, v0.4.0a1–v0.4.0a3) carried each commitment into running code.

What none of those ADRs ratified is the **filesystem layout** by which the substrate, the reference aspects, the meta-package, and the substrate's own self-host opt-in coexist in a single git repository. The layout was chosen incrementally during Phase A.7's substrate-content-move sub-plan: substrate at `src/kanon/`; reference data extracted to `src/kanon_reference/data/`; reference loader stubs at `src/kanon_reference/aspects/kanon_<slug>.py`; per-wheel pyprojects schematised at `packaging/{substrate,reference,kit}/pyproject.toml` (schema-of-record only — top-level `pyproject.toml` is the active build); standalone CI gates at top-level `ci/`; `.kanon/` at the repo root holding the substrate's own self-host opt-in (a byte-for-byte mirror of `src/kanon_reference/data/<slug>/protocols/`, enforced by `ci/check_kit_consistency.py`).

By v0.4.0a3 this layout had revealed several friction points the project's lead surfaced as confusion:

1. **Two top-level packages, two "data" homes.** `src/kanon/kit/` (substrate-level data) and `src/kanon_reference/data/` (per-aspect data) are both inside `src/`, both contain manifest YAML, and the distinction is not self-explanatory.
2. **Three pyprojects, one active.** `packaging/{substrate,reference,kit}/pyproject.toml` are schema-of-record (planned future build paths) but the top-level `pyproject.toml` is the actual build path for v0.4.x. The arrangement is honest about future intent but confusing today; the `packaging/` directory has zero entries in the top-10 most-touched files (per the panel's archaeology — see References) despite being the supposed canonical authority.
3. **Self-host duplication.** `.kanon/protocols/<aspect>/<file>.md` and `src/kanon_reference/data/<aspect>/protocols/<file>.md` exist as byte-equal copies, validated against each other by a CI gate. Every protocol prose edit touches two paths.
4. **Two validator homes.** `ci/check_*.py` (standalone gate scripts; not a Python package) vs `src/kanon/_validators/` (in-process project validators imported at verify time). Two homes for similar work; tests of the standalone gates use `importlib.util.spec_from_file_location` because `ci/` is not a package — a known fragility surfaced by PRs #80–82.
5. **`docs/` mixes immutable ADRs with active prose.** `docs/decisions/` (50 ADRs, mostly immutable) sits at the same depth as `docs/plans/` (100+ files, one created per task; growing 112%/100 commits). Flat-listing both is unusable.
6. **Six top-level concerns competing for attention.** `src/`, `packaging/`, `ci/`, `docs/`, `tests/`, `.kanon/` all at the top level — nothing rises to the top; a newcomer cannot read the architecture from `ls`.

A 7-panelist 3-round redesign panel (synthesis materials at `/tmp/kanon-panel/`, with full proposals + debates + votes preserved) produced unanimous-or-near-unanimous resolution on six convergent structural themes plus three previously-unresolved binary decisions. ADR-0049 ratifies the panel's resolution as the substrate's filesystem-layout commitment.

## Decision

The kanon monorepo's filesystem layout commits to nine structural rules, in two groups: six **convergent rules** (panelists agreed unanimously or near-unanimously) and three **resolved decisions** (panel voted; tally cited).

### Convergent rules (unanimous or 6+/7 panel agreement)

1. **One pyproject per distribution, co-located with its source.** The `packaging/{substrate,reference,kit}/pyproject.toml` parallel-tree is eliminated. Each distribution's `pyproject.toml` lives in the directory holding its source. The repo-root `pyproject.toml` carries only `[tool.uv.workspace]` (workspace coordinator); no `[project]` table.

2. **Substrate kernel does not co-locate with aspect data.** `src/kanon/kit/` (substrate-level YAML data) and any temptation to re-introduce aspect prose under the substrate package are forbidden. Substrate code: `.py` only. Substrate-only data (top manifest, harnesses config, AGENTS.md base) lives at `kernel/kit-base/` (renamed from `kit/` for disambiguation). A CI gate (`scripts/check_substrate_independence.py`, already present) enforces this.

3. **Per-aspect bundles.** Each reference aspect is one self-contained directory: `aspects/kanon-<slug>/{__init__.py, loader.py, manifest.yaml, protocols/, files/, sections/, agents-md/}`. The current split between `src/kanon_reference/aspects/kanon_<slug>.py` (LOADER stub) and `src/kanon_reference/data/kanon-<slug>/` (data) is collapsed. `__init__.py` at bundle level makes each bundle `importlib.resources`-accessible.

4. **`docs/plans/` is partitioned.** `docs/plans/active/` (status:draft, status:approved) vs `docs/plans/archive/` (status:done). Same partition for `docs/decisions/recent/` vs `docs/decisions/archive/` once ADR count exceeds a future-set threshold (deferred).

5. **`ci/` becomes `scripts/` as a proper Python package.** `scripts/__init__.py` is added; gate scripts move under it; `tests/scripts/` replaces `tests/ci/`. The `importlib.util.spec_from_file_location` test-infrastructure fragility (a real source of confusion in PRs #80–82) goes away — gates are invoked as `python -m scripts.check_kit_consistency`.

6. **The hard substrate-vs-data physical boundary is normative.** Every mega-restructuring event in kanon's history (per the panel's archaeology: 4 events, ~310 file relocations, 9 confessional plans = 20% of all plans) was caused by conflating substrate machinery with aspect content in the same directory tree. The boundary is a permanent invariant; CI enforces it.

### Resolved decisions (Round-3 panel vote)

7. **Decision D1 — `.kanon/` at the kanon repo root: COMMITTED (vote 5–2).** The substrate's own self-host opt-in stays in git. Contributor discoverability (cold-start `git clone` is fully functional with no `make` step), zero historical churn (24 files stable across 100 commits per panel archaeology), and the principle that committed config is the Python ecosystem norm (`pyproject.toml`, `uv.lock`, `AGENTS.md` all committed) outweigh the duplication-with-`aspects/<slug>/protocols/`-files objection. The duplication itself is addressed: `ci/check_kit_consistency.py`'s byte-equality clause is loosened to a behavioural conformance test (ADR-0044 §2's self-host probe is satisfied by `kanon verify .` exit-0, not by filesystem byte-equality). Dissenting panelists (P1 + P2) advocated `var/selfhost-tree/` materialised by `make selfhost` — the deliberation is preserved in the synthesis materials and may revisit if a future use-case (e.g., a publisher wanting to validate against multiple recipe-pin variants) demands it.

8. **Decision D2 — Top-level naming: SEMANTIC (vote 6–1).** The substrate kernel directory is `kernel/` (not `src/kanon/`, not `packages/substrate/src/kanon/`); the reference aspects directory is `aspects/` (not `packages/reference/src/kanon_reference/`). Two named top-level dirs teach the architecture from `ls`; workspace-conventional names (`packages/<dist>/`) describe the build graph but not the navigation graph. The dissenting panelist (P6, convention-conservative) preferred Python-monorepo workspace conventions (Hatch, uv); their argument is preserved but the panel's empirical lens (P7: workspace-rename has the same restructuring cost as the namespace-prefix mega-event) and ergonomic lens (P5: `kernel/cli.py` at depth 2 vs `packages/substrate/src/kanon/cli.py` at depth 4 for the most-edited file) carried 6–1.

9. **Decision D3 — Reference bundle directory name: `aspects/` (vote 5–2).** The seven reference bundles live under `aspects/kanon-<slug>/`, not `disciplines/kanon-<slug>/`. The vocabulary `aspect` is already baked into the runtime (`kanon aspect ...` CLI verbs, `kanon.aspects` Python entry-point group, `aspects:` config-file key, ADR-0012's foundational naming) and renaming would pay a fourth rename tax on a concept that has already stabilised through three prior renames (per panel archaeology). Dissenting panelists (P3 + P5) preferred `disciplines/` for newcomer-pedagogical reasons + AOP-collision avoidance; the deliberation is preserved.

### Implementation roadmap (NOT BINDING; sequencing guidance)

The migration is sketched as 6 sequential PRs, ordered by P7's empirical cost-ranking (lowest risk first, so each PR lands against a green baseline). Each PR is a separate plan with its own user approval gate; this ADR commits to the destination, not to the path.

1. **PR A — Bundle collapse.** ~14 files moved (`aspects/<slug>.py` + `data/<slug>/` → `aspects/kanon-<slug>/`). Add `__init__.py` per bundle. Update entry-points + `_manifest.py:_load_aspect_registry()`. **Low cost.**
2. **PR B — Kill `packaging/`.** Co-locate per-wheel pyprojects (`kernel/pyproject.toml`, `aspects/pyproject.toml`, `kit-meta/pyproject.toml`); top-level `pyproject.toml` becomes workspace coordinator (`[tool.uv.workspace]`, no `[project]`). **Medium cost.**
3. **PR C — `ci/` → `scripts/`.** Rename + add `__init__.py`; update `tests/ci/conftest.py` to import directly. **Low cost.**
4. **PR D — `docs/plans/active/` + `archive/`.** Script-driven move keyed by frontmatter `status:`. Update `ci/check_process_gates.py` to scan both subdirs. **Low cost.**
5. **PR E — `src/kanon/` → `kernel/`.** Drop `src/`; preserve `from kanon.x import y` imports via `pyproject.toml` `package-dir = {"kanon" = "kernel"}`. The most contested move; sequenced last so prior PRs' CI is stable. **Medium cost** (P7 estimates 2–4 hours of grep-and-replace across ~15 path-referencing files).
6. **PR F — Loosen `check_kit_consistency.py` byte-mirror clause.** Convert to behavioural conformance test per Decision §7. `.kanon/` stays committed. **Low cost.**

Each PR is independently green-able and `git revert`-able. Total estimated effort: 1–2 developer-weeks.

## Alternatives Considered

1. **Don't ratify the layout; let it evolve incrementally as Phase B unfolds.** Rejected. The lead surfaced the layout as a source of confusion explicitly. The panel's archaeology confirms that incremental-evolution-of-layout has been the historical pattern and has cost ~20% of all plans as confessional restructuring corrections. Continued incrementalism is expected to keep paying that tax. A ratified layout commitment with CI-enforced invariants (per Decision §2 + §6) breaks the cycle.

2. **Adopt the workspace-conventional layout (`packages/{substrate,reference,kit}/src/<pkg>/`) — P6's Round-1 proposal.** Rejected per Decision D2. The convention argument is real (Hatch and uv use this shape) but P7's archaeology argues the convention's structural cost in this repo is high (workspace-rename = mega-event-class restructuring) and the convention's payoff is low (the `[tool.uv.workspace]` table at the repo root indexes the workspace members regardless of directory naming). Semantic naming wins on directory ergonomics + newcomer discoverability; the workspace-conventional layout is preserved as P6's defended position in `/tmp/kanon-panel/round3/agent-6.md`.

3. **`var/selfhost-tree/` as gitignored generated artifact materialised by `make selfhost` — P1 + P2's Round-2 proposal.** Rejected per Decision D1. The structural argument (substrate-as-publisher symmetry: the substrate's own self-host loop should mirror what an `acme-` consumer does, not be a peer source of truth) is intellectually compelling but the empirical case against (zero-churn directory; bootstrap-step prerequisite invisible to `git status` and `grep`; no analogue of generated-config in mature Python projects) carried 5–2. The proposal is preserved verbatim in the panel materials and may revisit if a future use-case demonstrates the symmetry argument's practical payoff.

4. **`disciplines/` instead of `aspects/` — P3's Round-1 + P5's Round-3 proposal.** Rejected per Decision D3. The newcomer-pedagogical argument (`disciplines/` reads as "coherent bodies of practice" rather than AOP-style "cross-cutting concerns") is real, but the rename tax on already-stabilised vocabulary (`kanon aspect` CLI verb, `kanon.aspects` entry-point group, ADR-0012, `aspects:` config key, 50+ ADR + plan citations) outweighs the pedagogy gain. Preserved as the dissenting position.

5. **Defer the layout commitment until Phase B (`acme-` publisher onboarding) demands it.** Rejected. Phase B's onboarding-template proposal will be `aspects/kanon-<slug>/` as a literal copy-template (per P4's lens). Deferring the layout commitment forces Phase B to either copy a layout that's still in flux or block on this ADR. Ratifying now removes the dependency.

## Consequences

### Repo-level

- **Six convergent rules become normative invariants.** Each is enforceable by an existing or trivially-added CI gate. The substrate-vs-data boundary (rule §6) is the single most important invariant; its violation has historically cost mega-events.
- **The repo grows a `kernel/` directory and an `aspects/` directory at depth 1.** Newcomers' first-30-seconds reading of the file tree will encounter the architectural primitives (kernel + aspects) named explicitly, not inferred from `src/<pkg>/` packaging convention.
- **The `packaging/` directory is deleted.** Per-wheel `pyproject.toml` files relocate. Three pyprojects collapse to three pyprojects, but each lives next to its source.
- **`docs/plans/` partitions.** Active vs archive split; consumers' scaffolded `docs/plans/` mirrors this from `kanon init` onward.

### Migration-level

- **Six PRs sequence the migration**, low-cost-first, each independently green-able.
- **No ADR or accepted-spec text changes.** The body of every prior ADR is preserved verbatim; ADR-0049 supersedes nothing — it implements decisions made in ADR-0043 + 0044 + 0048 at the filesystem layer.
- **Self-host conformance (ADR-0044) is reframed at filesystem layer.** ADR-0044's "substrate runs `kanon verify .` against itself" survives intact; the *mechanism* by which the kanon repo opts into reference aspects shifts from byte-mirror enforcement to behavioural conformance probe. The committed `.kanon/` directory + loosened byte-mirror clause achieves both.

### Substrate-independence (ADR-0044)

- **Rule §2 (substrate code: `.py` only) is the filesystem expression of ADR-0044's substrate-independence invariant.** `scripts/check_substrate_independence.py` already enforces the runtime invariant (substrate doesn't import `kanon_reference`); rule §2 extends the invariant to the filesystem (substrate package contains no aspect data). Both invariants are CI-gated.
- **The `kernel/kit-base/` directory holds substrate-only data** (top manifest registry, harnesses config, AGENTS.md base). This is NOT aspect data; it's substrate-level configuration that the kernel needs at runtime regardless of which aspects are installed. The disambiguating rename from `kit/` to `kit-base/` is a one-time cost that prevents future "what's in `kit/` vs `data/`" confusion.

### Distribution boundary (ADR-0043)

- **The three-wheel split (kanon-substrate / kanon-reference / kanon-kit) ratified in ADR-0043 maps to three top-level directories: `kernel/` / `aspects/` / `kit-meta/`.** Each carries its own `pyproject.toml`. This makes ADR-0043's distribution boundary structurally visible — a contributor doesn't need to read three `pyproject.toml` headers to know which wheel a file ships in; the directory tells them.
- **Schema-of-record is eliminated.** Today's `packaging/{substrate,reference,kit}/pyproject.toml` are "future canonical" but inert. Moving them into the actual build path makes the canonical pyprojects also the active ones.

### CI + tests

- **`scripts/` as a proper package** removes the `importlib.util.spec_from_file_location` fragility surfaced by PRs #80–82. Gate scripts become importable as `python -m scripts.check_kit_consistency`.
- **`tests/ci/` → `tests/scripts/`** mirrors the rename.
- **`scripts/check_substrate_independence.py` and `scripts/check_kit_consistency.py`** become the two CI gates that protect the structural invariants (rules §2 + §6); both have to stay green on every commit.

### What this ADR does NOT change

- **Any ratified ADR or accepted spec body.** ADR-0049 cites and implements; it does not amend.
- **The consumer-side `kanon init` scaffold shape.** Consumers' `.kanon/` + scaffolded `docs/` + `AGENTS.md` are unchanged in structure (consumers see `docs/plans/active/` + `archive/` from PR D onward — that IS a scaffold change, but it's additive, not breaking).
- **The `kanon.aspects` Python entry-point group, `kanon-<slug>` aspect naming, or any runtime contract.** Publisher symmetry survives intact.
- **Any consumer-visible CLI behavior.** `kanon init`, `kanon verify`, `kanon migrate` semantics are unchanged.

## Config Impact

- **No `.kanon/config.yaml` schema change.** The v4 schema (per ADR-0040 + Phase 0.5 + PR #82) is unaffected by repo-internal directory rearrangement.
- **`pyproject.toml` shape changes** at repo level (root becomes workspace coordinator; per-wheel pyprojects co-locate). This is internal to the kanon repo build process; no consumer-visible effect.
- **`ci/check_kit_consistency.py` byte-equality clause is loosened** (per Decision D1 + PR F). Behavioural conformance test replaces filesystem invariant. The CI gate stays; its semantics shift.

## References

- [ADR-0043](0043-distribution-boundary-and-cadence.md) — distribution boundary; ADR-0049 implements it at the filesystem layer.
- [ADR-0044](0044-substrate-self-conformance.md) — substrate-self-conformance; ADR-0049 reframes the self-host probe (rule §7).
- [ADR-0048](0048-kanon-as-protocol-substrate.md) — protocol-substrate commitment; ADR-0049 implements its publisher-symmetry principle at the filesystem layer (per-aspect bundles mirror across `kanon-`/`acme-` namespaces).
- [ADR-0040](0040-kernel-reference-runtime-interface.md) — entry-point discovery; ADR-0049's per-aspect bundles preserve the entry-point shape.
- [`docs/specs/substrate-self-conformance.md`](../specs/substrate-self-conformance.md) — INV body (unchanged); ADR-0049 reframes how the kanon repo satisfies it.
- **Panel deliberation materials (recoverable, not committed):**
  - `/tmp/kanon-panel/round1/agent-{1..7}-*.md` — 7 independent proposals.
  - `/tmp/kanon-panel/round2/agent-{1..7}-round2.md` — 7 debates with cross-citations.
  - `/tmp/kanon-panel/round3/agent-{1..7}.md` — 7 votes on the three resolved decisions.
- **Empirical archaeology (Panelist 7):** 4 mega-restructuring events in 2 years totaling ~310 file relocations; 9 of ~45 plans (20%) are confessional rename/move plans; `packaging/` has 0 entries in top-10 most-touched files; `.kanon/` has 0 churn across 100 commits.
