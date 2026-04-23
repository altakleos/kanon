---
status: accepted
date: 2026-04-22
---
# ADR-0011: Kit bundle refactor — `templates/` → `kit/` with manifest-driven tier membership

## Context

The v0.1 kit ships four per-tier directories at `src/kanon/templates/tier-{0,1,2,3}/`. Each holds a full copy of that tier's scaffolds: `AGENTS.md`, `CLAUDE.md`, `docs/*` subtrees. Strict-subset invariants (ADR-0006, `template-bundle.md` invariant 2) require every file in tier-N to be byte-identical to its counterpart in tier-(N+1). The `ci/check_template_consistency.py` validator enforces this by cross-tier byte comparison.

Two problems with that shape:

1. **~4× duplication of shared files.** `docs/development-process.md`, `docs/decisions/_template.md`, `docs/plans/_template.md`, and the shared `CLAUDE.md` each exist four times. Every edit to the repo-root canonical version must be replicated across the copies, policed by a byte-equality watchdog. Real maintenance cost; zero design benefit.
2. **Adding a new layer compounds the duplication.** The protocol layer (ADR-0010) would add `.kanon/protocols/*.md` files at multiple tiers. Under the current shape, each protocol file would exist 1–3× across tier directories, growing the problem.

Additionally, the sibling project Sensei (`src/sensei/engine/`) bundles its runtime under a single folder with a kernel doc (`engine.md`), tunables YAML (`defaults.yaml`), and sub-buckets (`protocols/`, `scripts/`, `schemas/`, `templates/`). That shape is more coherent for future readers and maps well onto the kanon kit.

The refactor landing point: pre-release v0.1.0a1, not pushed, zero external consumers. Cost of the change is just internal churn.

## Decision

Rename `src/kanon/templates/` → `src/kanon/kit/` and restructure as follows:

```
src/kanon/kit/
├── kit.md                 # kernel doc, scaffolded to consumer's .kanon/kit.md
├── manifest.yaml          # tier → file/protocol/section membership
├── harnesses.yaml         # shim registry (unchanged contents)
├── agents-md/             # per-tier AGENTS.md base preambles
│   └── tier-{0,1,2,3}.md
├── sections/              # reusable AGENTS.md marker sections
│   ├── plan-before-build.md
│   ├── spec-before-design.md
│   └── protocols-index.md
├── protocols/             # prose-as-code protocols (mirrored to .kanon/protocols/)
│   ├── tier-up-advisor.md
│   ├── verify-triage.md
│   └── spec-review.md
└── files/                 # flat scaffold tree — one copy per file
    ├── CLAUDE.md
    └── docs/
        ├── development-process.md
        ├── decisions/{README,_template}.md
        ├── plans/{README,_template}.md
        ├── specs/{README,_template}.md
        ├── design/{README,_template}.md
        └── foundations/{README,vision,principles/README,personas/README}.md
```

Tier membership becomes data in `manifest.yaml`:

```yaml
tier-0:
  files: [CLAUDE.md]
  protocols: []
tier-1:
  files: [docs/development-process.md, docs/decisions/README.md, …]
  protocols: [tier-up-advisor.md, verify-triage.md]
tier-2:
  files: [docs/specs/README.md, docs/specs/_template.md]
  protocols: [spec-review.md]
tier-3:
  files: [docs/design/README.md, …, docs/foundations/…]
  protocols: []
agents-md-sections:
  tier-0: []
  tier-1: [plan-before-build, protocols-index]
  tier-2: [plan-before-build, spec-before-design, protocols-index]
  tier-3: [plan-before-build, spec-before-design, protocols-index]
```

The CLI's `_build_bundle(tier, …)` reads the manifest and unions entries for tiers 0..tier inclusive; `_expected_files(tier)` uses the same union. The hardcoded `_TIER_FILES` and `_TIER_SECTIONS` dicts in `src/kanon/cli.py` are deleted.

Byte-equality enforcement narrows to a whitelist of files that have a repo-root counterpart:

- `kit/files/docs/development-process.md` ↔ `docs/development-process.md`
- `kit/files/docs/{decisions,plans,specs,design}/_template.md` ↔ repo equivalents
- `kit/protocols/*.md` ↔ repo's `.kanon/protocols/*.md`

Files without a repo counterpart (tier-stub READMEs, `foundations/vision.md`) are template-only and are not byte-checked.

The cross-tier subset check disappears — it is tautological under manifest union. `_build_bundle(tier=2)` literally cannot emit a file that isn't also in `_build_bundle(tier=3)` because it walks the same manifest keys.

## Alternatives Considered

1. **Force-include from repo root at install time.** Have the kit store only `src/kanon/kit/files/` as a thin skeleton and pull canonical copies from the repo's own `docs/` at build/install time. Rejected: breaks editable installs (the "canonical copy" depends on which repo is current); complicates wheel packaging (would need a pre-build hook to stage files).
2. **Whole-repo-as-template.** Treat the entire kanon repo (minus `src/`, `tests/`, `ci/`) as the tier-3 template. Rejected: some files legitimately differ between kit-side and repo-side. Tier-stub `docs/specs/README.md` in the kit is a *template* with a TODO comment; the kit's own repo-root `docs/specs/README.md` is a *populated index*. Byte-equality would be false.
3. **Keep `templates/` name, add `manifest.yaml`.** Rejected: the rename communicates the refactor; `templates/` implies per-tier subdirectories. `kit/` aligns with Sensei's `engine/` and makes the pattern match legible across sibling projects.
4. **Mimic Sensei exactly — call it `engine/`.** Rejected: Sensei's `engine/` ships an LLM *runtime* (personality, modes, dispatch). Kanon's bundle is a *scaffolder* that copies files selectively per tier. "Kit" captures the selection semantics better than "engine" without sacrificing the structural mimicry.
5. **Do nothing — live with duplication.** Rejected: adding the protocol layer (ADR-0010) would compound duplication. The only "do nothing" cost that looks low is the one where nothing else changes.

## Consequences

- **Eliminates the ~4× duplication watchdog.** `CLAUDE.md`, `development-process.md`, the four `_template.md` files, and future shared files have one copy each.
- **Tier-subset check becomes tautological and is removed.** CI surface shrinks; remaining byte-equality check is a narrow whitelist against repo canonicals.
- **CLI becomes manifest-driven.** `_TIER_FILES`/`_TIER_SECTIONS` hardcoded dicts disappear; adding a new file to tier-2 becomes a one-line manifest edit.
- **Protocol layer drops in without duplication.** A protocol listed under `tier-1.protocols` in the manifest is present at tier-1, 2, 3 via union semantics. Zero file copies.
- **Adds `kit.md` kernel doc** scaffolded to consumer's `.kanon/kit.md`. Mirrors Sensei's AGENTS.md → engine.md handoff for protocol discovery; not a replacement for AGENTS.md marker rules (which stay for enforcement proximity).
- **`ci/check_template_consistency.py` → `ci/check_kit_consistency.py`.** Rename matches the bundle name; pre-release is the right time for the rename.
- **Does not alter migration semantics (ADR-0008).** Tier-up/down, atomicity, non-destructiveness, and marker-delimited AGENTS.md rewriting are preserved; the refactor changes the *source* of tier membership data (manifest vs hardcoded dict), not the *semantics* of using it.

## Config Impact

None. `.kanon/config.yaml` is unchanged. `kit_version` in the config continues to track the installed kit.

## References

- ADR-0006 — tier model (still in force; this refactor changes the implementation, not the tier semantics).
- ADR-0008 — tier migration (unchanged).
- `docs/specs/template-bundle.md` — spec text updated in place to describe manifest-driven tier membership; filename retained (the spec describes *what bundle ships*; "template-bundle" remains accurate terminology).
- `docs/design/template-bundle.md` → renamed to `docs/design/kit-bundle.md` and rewritten to describe the manifest-driven layout (design doc name tracks the source directory `kit/`).
- Sensei's `src/sensei/engine/` — structural inspiration.
