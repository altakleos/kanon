---
status: draft
slug: contributor-arch-doc
date: 2026-05-01
design: "Follows ADR-0010 (protocol layer) and ADR-0034 (routing-index AGENTS.md) — no new design surface; this is a navigation doc for human contributors."
---

# Plan: Contributor architecture doc

## Goal

Add a single, terse contributor-facing document that gives a new human contributor a working mental model of kanon's source layout, how a CLI command flows, where each piece of behaviour is enforced, and where their change probably belongs. Doc is navigation-oriented (where do I edit X?, what tests guard Y?, what gate fires when?), distinct from the decision-oriented `docs/design/` material.

## Motivation

`AGENTS.md` is a router for LLM agents (per ADR-0034); it tells the runtime *what protocol fires when*. A new human contributor opening a PR needs the inverse: a map from intent ("change `kanon init` behaviour") to location ("`cli.py` + spec amendment + test in `test_cli.py`") to gates that will block the PR. The 14 ci/check_*.py + 6 in-process validators are opaque from outside; surfacing them in one table prevents the "why did my PR fail?" cycle.

This is also what the `onboarding-agent` persona (`docs/foundations/personas/onboarding-agent.md`) implies should exist — a persona without a corresponding entry document is a planning gap.

## Scope

### In scope

1. **One new file**: `docs/contributing.md` (~150–200 lines).
2. **Two cross-links** added:
   - `README.md § Development` — one line linking to the contributor doc.
   - `AGENTS.md` — one line under "Contribution Conventions" linking to the contributor doc.
3. Doc contents (six sections):
   - **Module map** — table of `src/kanon/*.py` modules → role → primary tests → governing ADR.
   - **"Where does my change go?"** — short decision flow for the aspect-vs-CLI-vs-protocol question.
   - **The gate matrix** — every CI check (workflow + script), what it enforces, the local fix command.
   - **Hot-path callouts** — `cli.py` is large by design; `_scaffold.py` + `_manifest.py` are the I/O surface; `_atomic.py` is sacrosanct.
   - **Worktree workflow recap** — link to `branch-hygiene` protocol; show the one-liner.
   - **The 5 things you can't do** — modify accepted ADR bodies, weaken fidelity assertions, bypass `_atomic.py`, add `shell=True` without ADR-0036 marker, edit kit-rendered marker bodies in consumer trees.

### Out of scope

- New ADRs, specs, or design docs.
- Any source code changes under `src/`, `ci/`, `tests/`, `scripts/`.
- Changes to existing design docs in `docs/design/` (cross-link only).
- Changes to protocol prose under `.kanon/protocols/` or `src/kanon/kit/aspects/*/protocols/`.
- New CI checks. (A future plan can add a `check_contributor_doc_freshness.py` that fails when a new `src/kanon/*.py` lands without a row in the module map.)
- A separate `docs/design/architecture.md` — that was a different doc the user weighed and rejected.

## Acceptance criteria

- [ ] `docs/contributing.md` exists with the six sections above, ≤ 250 lines.
- [ ] Module map table covers every file currently in `src/kanon/*.py` and `src/kanon/_validators/*.py`.
- [ ] Gate matrix covers every script in `ci/check_*.py` and every workflow in `.github/workflows/*.yml`.
- [ ] Cross-links added to `README.md` and `AGENTS.md`; both link forms render correctly.
- [ ] No emoji unless explicitly requested by the user.
- [ ] No CHANGELOG entry needed (docs-only — per `AGENTS.md § Contribution Conventions`).
- [ ] `kanon verify .` returns `status: ok` after the change.
- [ ] No existing markdown link is broken (`ci/check_links.py` passes).

## Approach (sequencing)

1. Author `docs/contributing.md` as the body of work.
2. Add the two cross-links last (small, mechanical).
3. Run `python ci/check_links.py` and `kanon verify .` from the worktree.
4. Commit with a Conventional-Commit message (`docs: add contributor architecture doc (plan: contributor-arch-doc)`).
5. Push branch, open PR, link the plan.

## Risks / concerns

- **Doc rot risk**: at the project's release cadence, an unmaintained module map will drift within a release or two. Mitigated by keeping the doc terse (link to ADRs, don't restate them) and by leaving a TODO at the bottom of this plan to consider a `check_contributor_doc_freshness.py` later.
- **Overlap with `docs/design/aspect-model.md`**: the contributor doc cites the aspect model but does not re-explain it. Cross-link, don't duplicate (`P-cross-link-dont-duplicate`).

## Documentation impact

- New: `docs/contributing.md`
- Touched: `README.md` (+1 line), `AGENTS.md` (+1 line)
- No spec, design, or ADR change.
