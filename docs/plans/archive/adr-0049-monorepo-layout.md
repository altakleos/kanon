---
status: done
shipped-in: PR #86
slug: adr-0049-monorepo-layout
date: 2026-05-02
---

# Plan: ADR-0049 — Monorepo layout for the protocol substrate

## Goal

Author ADR-0049 codifying the panel-resolved repository layout for the `kanon` monorepo: substrate kernel + reference aspects + meta-package, with all six panel-converged structural decisions and the three Round-3-resolved binary decisions baked into the ADR text. Ships as `status: draft` for user review; user promotes to `accepted` via a separate commit if approved.

## Background

A 7-panelist 3-round redesign panel (synthesis at `/tmp/kanon-panel/`) produced unanimous-or-near-unanimous resolution on six convergent themes (kill `packaging/`, per-aspect bundle collapse, drop `src/` for substrate, `docs/plans/active+archive`, `scripts/` → `scripts/`, hard substrate-vs-data physical boundary) plus three binary decisions (D1: `.kanon/` committed; D2: semantic top-level naming; D3: `aspects/` directory name). The panel's resolution lacks a normative artifact in the repo. ADR-0049 supplies it so the eventual migration PRs (the panel's 6-PR sequence) cite a ratified decision rather than re-litigating each PR.

## Scope

In scope:
- Author `docs/decisions/0049-monorepo-layout.md` with `status: draft`.
- Document the 6 convergent + 3 resolved decisions.
- Reference ADR-0043 (distribution-boundary) and ADR-0044 (substrate-self-conformance) — the decisions ADR-0049 implements at the filesystem layer.
- CHANGELOG entry under `## [Unreleased]` flagging the draft ADR.

Out of scope (deferred):
- The migration PRs themselves (the 6-PR sequence the panel sketched). Each will be its own plan + PR after ADR-0049 is accepted.
- Promoting ADR-0049 from `draft` to `accepted` — the user does that after reviewing.
- Updating ADR-0043 / ADR-0044 to cite ADR-0049 — deferred until acceptance (ADR-immutability allows references-out from the citing side, but cleaner to wait).

## Acceptance criteria

- AC1: `docs/decisions/0049-monorepo-layout.md` exists with `status: draft`, dated, structured per the kit's ADR template (Context / Decision / Alternatives Considered / Consequences / Config Impact / References).
- AC2: ADR body cites the panel synthesis location (`/tmp/kanon-panel/`) explicitly so the deliberation trail is recoverable.
- AC3: All 6 convergent themes named with the panelists who endorsed them.
- AC4: All 3 binary decisions (D1/D2/D3) explicitly marked with vote tally and resolution.
- AC5: Migration sequence (6 PRs, P7's cost-ranked low-risk-first ordering) appears as an "Implementation roadmap" section.
- AC6: ADR cross-links ADR-0043 + ADR-0044 + ADR-0048 (the parent decisions ADR-0049 implements at the filesystem layer).
- AC7: CHANGELOG entry noting the draft ADR.
- AC8: 8 gates green; full pytest passes (no source changes; should be no-op).

## Steps

1. Read ADR-0048 + ADR-0043 + ADR-0044 to ensure ADR-0049's framing aligns.
2. Read `docs/decisions/_template.md` if it exists; otherwise mirror ADR-0048's shape.
3. Author `docs/decisions/0049-monorepo-layout.md` with `status: draft`.
4. CHANGELOG entry.
5. Run gates (verify, link-check, foundation, packaging-split, etc.) — confirm `check_adr_immutability.py` doesn't reject a draft ADR (it shouldn't — it only protects accepted ADRs).
6. Run full pytest (no source changes; should pass).
7. Commit + push + open PR.

## Verification

- `kanon verify .` → ok
- `python scripts/check_links.py` → ok (ADR cross-links resolve)
- `python scripts/check_adr_immutability.py` → ok (draft ADRs aren't subject to immutability gate)
- `pytest --no-cov -q` → 978 passed (no change)

## Out of scope, deferred

The 6-PR migration sequence outlined in ADR-0049's Implementation Roadmap is NOT executed in this PR. Each step gets its own plan + PR after ADR-0049 is accepted.
