---
feature: scaffold-v2-status-update
status: done
date: 2026-05-05
---
# Plan: Promote scaffold-v2 design from draft to accepted, with ADR-0048/0062 status section

## Context

`docs/design/scaffold-v2.md` is `status: draft` (frontmatter line 2) but its core proposals are in production: AGENTS.md is a slim routing index, sdd is de-privileged (`worktrees suggests` not `requires`, CLAUDE.md is a harness shim), the new protocol files (plan-before-build.md, spec-before-design.md, branch-hygiene.md, etc.) are scaffolded by `kanon-sdd`/`kanon-worktrees`/etc., and `_assemble_agents_md` matches the design's simplified shape.

The implementing spec at `docs/specs/scaffold-v2.md` is already `accepted`; the design doc lagging at `draft` understates what shipped.

The de-opinionation transition (ADR-0048, Phase A.3) and the declarative-hard-gates landing (ADR-0062) went **further** than scaffold-v2 anticipated in three specific places. The design doc's body still describes the pre-ADR-0048 plan in prose form, so a top-down reader hits inaccurate text. Following the project's existing convention (`docs/design/aspect-model.md` ends with a "Status under ADR-0048" section), this plan appends an analogous status section noting what shipped, what was superseded, and what was amended — without editing the historical body.

## Tasks

- [x] T1: Bump frontmatter `status: draft` → `status: accepted` at `docs/design/scaffold-v2.md:2`. → `docs/design/scaffold-v2.md`
- [x] T2: Append a `## Status under ADR-0048 + ADR-0062` section at the end of `docs/design/scaffold-v2.md`, mirroring the structure used in `docs/design/aspect-model.md` (Survives / Superseded / Amended). Specifically: (a) Survives — slim AGENTS.md shape, sdd de-privileging (CLAUDE.md as shim, `worktrees: suggests` over `requires`, removal of structural `kanon-sdd >= 1`), new protocol files, simplified `_assemble_agents_md`. (b) Superseded — top-level kit-global `files:` field (ADR-0048 Phase A.3 retired all kit-global file scaffolding); `defaults: [kanon-sdd]` (ADR-0048 Phase A.3 deleted the `defaults:` block entirely; `kanon init` with no flags now scaffolds an empty project, see `cli.py:272-276`); `${active_aspects_summary}` placeholder for `kit.md` (`kit.md` itself was retired with kit-global files). (c) Amended — hard-gates rendering: design proposed a static template-with-conditional rows; ADR-0062 made it dynamic, generated from protocol frontmatter `gate: hard` declarations via `_render_hard_gates` in `_scaffold.py`. → `docs/design/scaffold-v2.md`

## Acceptance Criteria

- [x] AC1: `status: accepted` in frontmatter of `docs/design/scaffold-v2.md`.
- [x] AC2: A `## Status under ADR-0048 + ADR-0062` section exists at the end of the file, with three labeled subsections (Survives / Superseded / Amended) and citations to the relevant ADRs and code paths.
- [x] AC3: The historical body (Context, Architecture, sdd de-privileging, Upgrade path, Alternatives, Risks) is preserved unchanged — archaeological integrity is the design-doc convention used by `aspect-model.md`.
- [x] AC4: `kanon verify .` still passes.
- [x] AC5: `python scripts/check_links.py` still passes (the new section adds links to ADR-0048, ADR-0062, `aspect-model.md`, and code paths).
- [x] AC6: `python scripts/check_status_consistency.py` doesn't flag this change (the spec-vs-design `status` skew goes from "spec accepted, design draft" — currently a clean skew per the validator's rules — to "both accepted", which is the resting state).

## Documentation Impact

CHANGELOG entry not added — per AGENTS.md "Refactors, internal tests, and docs-only edits don't need a changelog entry," and this is a docs-only design-doc status promotion that records what already shipped. No README or CLI-help changes; the design doc is internal architecture documentation, not consumer-facing.

## Notes

- **Why preserve the body unchanged.** Following `aspect-model.md`'s precedent (`docs/design/aspect-model.md:262-270` — "Status under ADR-0048" appended after the body, body left intact). Design docs are archaeology of intent; rewriting them in place loses the "what did we think before?" record. The status section is the canonical place to bridge then-vs-now.
- **Why no spec/design/ADR.** No new code, no new mechanism, no new component boundary. ADR-0048 and ADR-0062 already ratified the changes that diverged from the design's draft body; this PR records that they shipped.
- **Why borderline trivial but plan-gated.** The change is small (one frontmatter line + ~30 lines of new prose), but adding a section that re-asserts which parts of a design doc are authoritative is high-leverage prose work — exactly the class AGENTS.md gates a plan around. The plan exists in part to surface the editorial choice (preserve body vs. rewrite) for review.
