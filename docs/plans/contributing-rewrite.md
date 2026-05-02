---
status: done
slug: contributing-rewrite
date: 2026-05-01
design: "Follows ADR-0010 (protocol layer) and ADR-0034 (routing-index AGENTS.md); navigation doc for human contributors, no new design surface."
---

# Plan: Rewrite contributor guide as didactic walk-through with diagrams

## Goal

Restructure `docs/contributing.md` (initially shipped in PR #47 as a flat reference) into a didactic guide that walks abstract → concrete: mental model → aspect model → runtime behaviour → source layout → "where does my change go?" → CI gates → workflow → prohibitions. Add 6 mermaid diagrams to anchor at-a-glance comprehension.

## Motivation

The first version of `docs/contributing.md` (PR #47) was a flat reference: module map, gate matrix, 5 don'ts. Useful, but assumed the reader already had a mental model of what kanon is and how aspects compose. A new SWE arriving from a different domain bounces off the module-map table because the names (`_scaffold`, `_manifest`, `_atomic`) only make sense once you understand kanon is *a kit that templates other repos and self-hosts on its own templates*.

The reshape orders sections **concept → context → location → action**, mirroring how an unfamiliar codebase is best learned. Diagrams land the high-level shape before the prose drills down.

## Scope

### In scope

1. **Rewrite `docs/contributing.md`** — 8 numbered sections plus intro and closer:
   - Intro + mental-model triangle diagram
   - § 1 What kanon is, in one screen
   - § 2 The aspect model in 90 seconds (+ aspect-model diagram + table of all 7 aspects)
   - § 3 What happens when you run kanon (+ `kanon init` sequence diagram)
   - § 4 The source tree (+ module dependency graph + module table + validator table)
   - § 5 Where does my change go? (+ decision table)
   - § 6 The gate matrix (+ CI workflow chain diagram + verify pipeline sequence diagram + gate matrix table)
   - § 7 Contribution workflow end-to-end
   - § 8 Five things you cannot do
   - Closer (See also)
2. **6 mermaid diagrams** total: mental model triangle, aspect model, init sequence, source-layout dependency graph, CI workflow chain, verify pipeline sequence.
3. **Length budget** ≤ 400 lines; final landed at 365.

### Out of scope

- Changes to source under `src/`, `scripts/`, `tests/`, `scripts/`.
- New ADRs, specs, design docs.
- Changes to existing design docs in `docs/design/` (cross-link only).
- Changes to protocol prose under `.kanon/protocols/` or `src/kanon/kit/aspects/*/protocols/`.
- A separate `docs/design/architecture.md`.

## Approach

Three-agent panel produced intermediate artifacts in parallel; main agent synthesized:

1. **Architect** (Opus, read-only) — produced section-by-section outline, reader-journey rationale, cross-link policy, what-not-to-include list.
2. **Code-explorer** — produced the truth dump (verified `path:line` citations for the 7 aspects, `kanon init` 20-step call graph, `kanon verify` orchestration, all 13 `scripts/check_*.py` scripts, CI workflow chain). Caught two factual errors in the original doc: `_check_pending_recovery` is NOT called from `init`; `release-preflight.py` is NOT in `checks.yml`.
3. **Designer** — produced 6 mermaid diagrams, syntax-checked.

Synthesis lifted the architect's spine, embedded the designer's diagrams at specified anchors, used the explorer's citations for every factual claim.

## Acceptance criteria

- [x] AC1: `docs/contributing.md` reorganised into 8 sections + intro + closer matching the architect's outline.
- [x] AC2: 6 mermaid code fences embedded at the specified section anchors.
- [x] AC3: All 7 kit-shipped aspects listed in §2 with verbatim manifest data; 5-of-7 default-set fact called out.
- [x] AC4: All 14 source modules + 6 validators in §4 module + validator tables.
- [x] AC5: All 13 `scripts/check_*.py` scripts + workflow chain in §6 gate matrix; release-only `check_package_contents.py` distinguished.
- [x] AC6: Length ≤ 400 lines (final: 365).
- [x] AC7: `kanon verify .` returns `status: ok` (one pre-existing fidelity warning unrelated to this change).
- [x] AC8: `python scripts/check_links.py` passes.
- [x] AC9: No CHANGELOG entry needed (docs-only).
- [x] AC10: No source code, spec, ADR, or design-doc change.

## Documentation impact

- Touched: `docs/contributing.md` (full rewrite, additive in content, restructured in layout).
- No spec / design / ADR change.
- README.md and AGENTS.md cross-links from PR #47 remain valid.
